"""Las personas simuladas (events/synth.py): la asiática y la parte que le deja el carrete.

Sin base de datos: el catálogo se arma a mano con los ítems que cada persona podría comprar.
"""

import io
import random
from collections import Counter
from datetime import datetime, timedelta

import pytest

from rappi_ia.concepts.taxonomy import load_taxonomy
from rappi_ia.events import synth

ASIAN_CONCEPTS = {"sushi", "asiatica", "despensa-asiatica", "bebidas-asiaticas", "snacks-asiaticos"}
ASIAN_VERTICALS = {"restaurantes", "supermercado", "turbo", "conveniencia"}
ALL_GROUPS = "rest+turbo+retail"  # el arquetipo que deja a la persona con todos sus verticales
START = datetime(2026, 4, 1, tzinfo=synth.CHILE)
END = START + timedelta(weeks=26)


def _persona(persona_id: str) -> synth.Persona:
    return next(p for p in synth.PERSONAS if p.id == persona_id)


def _catalog(persona: synth.Persona) -> synth.Catalog:
    """Tres ítems por cada (vertical, concepto) que la persona compra: no falta nada que comprar."""
    items = {
        (vertical, concept): [("catalog_item", f"{vertical}-{concept}-{n}", 4000.0 + 500 * n) for n in range(3)]
        for vertical, concepts in persona.interests.items()
        for concept in concepts
    }
    return synth.Catalog(items=items, edges={}, names={}, ranked={})


def _simulate(persona: synth.Persona, users: int = 60, seed: int = 7) -> dict[str, str]:
    """Corre a `users` personas con el generador con semilla y devuelve lo que escribió (pedidos, líneas y eventos)."""
    rng = random.Random(seed)
    catalog = _catalog(persona)
    buffers = {key: io.StringIO() for key in ("users", "events", "orders", "lines")}
    counts = {"usuarios": 0, "eventos": 0, "pedidos": 0}
    for n in range(users):
        state = synth.UserState(
            f"syn-{seed}-{n:05d}",
            persona,
            "Santiago",
            8.0,
            ALL_GROUPS,
            synth.effective_interests(persona, ALL_GROUPS),
        )
        synth._simulate_user(rng, catalog, state, START + timedelta(days=n % 40), END, START, buffers, counts)
    return {key: buffer.getvalue() for key, buffer in buffers.items()}


def test_there_is_an_asian_persona_that_buys_in_the_four_verticals():
    persona = _persona("asiatico")

    assert set(persona.interests) == ASIAN_VERTICALS
    assert set().union(*persona.interests.values()) == ASIAN_CONCEPTS
    assert persona.interests["restaurantes"].keys() == {"sushi", "asiatica"}  # lo que se pide hecho


def test_every_concept_of_the_asian_persona_exists_in_the_taxonomy():
    concepts = load_taxonomy().concepts

    assert concepts.keys() >= ASIAN_CONCEPTS


def test_its_share_comes_out_of_the_party_persona():
    """El usuario pidió achicar el carrete y sumar al asiático: lo que gana uno lo pierde el otro."""
    asian, party = _persona("asiatico"), _persona("carrete")

    assert asian.share == pytest.approx(0.08)
    assert party.share == pytest.approx(0.14)
    assert asian.share + party.share == pytest.approx(0.22)  # el carrete tenía 0,22 solo


def test_the_party_persona_still_exists_and_keeps_its_interests():
    party = _persona("carrete")

    assert set(party.interests) == {"licores", "conveniencia", "restaurantes"}


def test_the_asian_persona_orders_sushi_and_the_new_concepts():
    """Con la semilla fija, sus pedidos pasan por sushi, comida asiática y los tres conceptos nuevos."""
    out = _simulate(_persona("asiatico"))

    ordered = {line.split("\t")[4] for line in out["lines"].splitlines()}  # concept_id de cada línea de pedido

    assert ordered == ASIAN_CONCEPTS


def test_its_orders_come_from_restaurants_supermarket_turbo_and_express():
    out = _simulate(_persona("asiatico"))

    verticals = {line.split("\t")[5] for line in out["orders"].splitlines()}

    assert verticals == ASIAN_VERTICALS


def test_the_generator_is_deterministic_with_the_same_seed():
    persona = _persona("asiatico")

    assert _simulate(persona, seed=11) == _simulate(persona, seed=11)
    assert _simulate(persona, seed=11) != _simulate(persona, seed=12)


def test_archetypes_follow_rappi_shares():
    rng = random.Random(1)
    n = 20000
    counts = Counter(synth.draw_archetype(rng) for _ in range(n))
    assert counts["rest"] / n == pytest.approx(62.6 / 93.4, abs=0.015)  # 93.4 = suma de las 7 filas sin favor
    assert set(counts) == {"rest", "turbo", "rest+turbo", "retail", "rest+retail", "rest+turbo+retail", "turbo+retail"}
    assert sum(synth.ARCHETYPES.values()) == pytest.approx(1)


def test_effective_interests_stay_in_the_archetype_groups():
    familia = _persona("familia")
    eff = synth.effective_interests(familia, "rest+turbo")
    assert set(eff) <= {"restaurantes", "turbo"} and eff["turbo"]  # turbo sale del súper de la familia
    assert "panales" not in eff["turbo"] and "alimentacion-bebe" not in eff["turbo"]  # sin bebé fuera del súper
    assert eff["restaurantes"] == familia.interests["restaurantes"]


def test_what_goes_to_turbo_has_no_alcohol_baby_health_or_sensitive_concepts():
    concepts = load_taxonomy().concepts
    for persona in synth.PERSONAS:
        for archetype in synth.ARCHETYPES:
            eff = synth.effective_interests(persona, archetype)
            copied = set(eff.get("turbo", {})) - set(persona.interests.get("turbo", {}))
            for concept in copied:
                c = concepts[concept]
                assert not (c.sensitive or c.age_restricted or c.parent in ("bebe", "salud")), (persona.id, concept)


def test_missing_groups_use_the_generic_interests():
    delivery = _persona("delivery")  # solo restaurantes
    eff = synth.effective_interests(delivery, "turbo+retail")
    assert eff == {"turbo": synth.GENERIC_INTERESTS["turbo"], "supermercado": synth.GENERIC_INTERESTS["supermercado"]}
    rutina = _persona("rutina")  # solo súper
    assert synth.effective_interests(rutina, "rest")["restaurantes"] == synth.GENERIC_INTERESTS["restaurantes"]


def test_generic_interests_have_no_alcohol_baby_health_or_sensitive_concepts():
    concepts = load_taxonomy().concepts
    for interests in synth.GENERIC_INTERESTS.values():
        for concept in interests:
            c = concepts[concept]
            assert not (c.sensitive or c.age_restricted or c.parent in ("bebe", "salud")), concept


def test_fallback_concepts_prefer_what_the_catalog_has():
    """Con un catálogo, lo que se copia a un grupo vacío se queda con lo que ese vertical vende: sin eso, toda la
    persona del arquetipo terminaría en búsquedas sin resultado."""
    familia = _persona("familia")
    catalog = synth.Catalog(
        items={("turbo", "gaseosas"): [("catalog_item", "t-1", 990.0)]}, edges={}, names={}, ranked={}
    )
    assert synth.effective_interests(familia, "turbo", catalog) == {"turbo": {"gaseosas": 2}}


def test_cadence_follows_orders_per_user():
    assert synth.archetype_cadence("rest+turbo+retail") < synth.archetype_cadence("rest+turbo")
    assert synth.archetype_cadence("rest+turbo") < synth.archetype_cadence("rest")
    assert synth.archetype_cadence("rest") == pytest.approx(30 / (1.9 * synth.SESSIONS_PER_ORDER))


def _state(archetype: str, orders_by_vertical: dict) -> synth.UserState:
    persona = _persona("delivery")
    return synth.UserState(
        "syn-x",
        persona,
        "Santiago",
        8.0,
        archetype,
        synth.effective_interests(persona, archetype),
        True,
        orders_by_vertical,
    )


def test_the_combination_of_the_last_30_days_sets_the_retention():
    """El supuesto explícito: pedir en otro grupo cambia la combinación y con ella la retención (0,76 de rest+retail
    en vez de 0,47 de rest, su arquetipo)."""
    now = END - timedelta(days=1)
    moved = _state("rest", {"restaurantes": [now - timedelta(days=5)], "supermercado": [now - timedelta(days=3)]})
    assert synth._stay_probability(moved, now, 30) == pytest.approx(0.76)
    assert synth._stay_probability(moved, now, 15) == pytest.approx(0.76**0.5)


def test_without_recent_orders_the_retention_is_the_archetype_one():
    now = END - timedelta(days=1)
    assert synth._stay_probability(_state("rest", {}), now, 30) == pytest.approx(0.47)
    old = _state("rest", {"supermercado": [now - timedelta(days=45)]})  # fuera de los 30 días
    assert synth._stay_probability(old, now, 30) == pytest.approx(0.47)


def test_simulated_suggestions_follow_the_offer_guards():
    """El agente real nunca ofrece alcohol ni productos de Farmacia o Licores: el simulado tampoco."""
    item = [("catalog_item", "x", 990.0)]
    catalog = synth.Catalog(
        items={("licores", "cerveza"): item, ("farmacia", "gaseosas"): item, ("supermercado", "gaseosas"): item},
        edges={"pizza": [("cerveza", 0.7), ("gaseosas", 0.6)], "frutas": [("vitaminas", 0.9)]},
        names={},
        ranked={"cerveza": ["licores"], "gaseosas": ["farmacia", "supermercado"], "vitaminas": ["supermercado"]},
    )
    assert synth._suggestion(catalog, "pizza", "restaurantes") == ("gaseosas", "supermercado", 0.6)
    assert synth._suggestion(catalog, "frutas", "supermercado") is None  # salud


def test_signups_spread_over_the_whole_period():
    """Las altas llegan parejas, como cohortes mensuales: el último cuarto del período recibe cerca de un cuarto."""
    rng = random.Random(1)
    signups = [synth.draw_signup(rng, START, 26) for _ in range(2000)]
    assert all(START <= s < END for s in signups)
    last_quarter = sum(1 for s in signups if s >= START + (END - START) * 0.75)
    assert 0.20 <= last_quarter / len(signups) <= 0.30, last_quarter

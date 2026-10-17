from itertools import combinations

import pytest

from rappi_ia.motor.combos import (
    FINE_ORDER,
    GROUP_ORDER,
    Step,
    combo_key,
    combo_of_verticals,
    expected_fine_retention,
    expected_retention,
    fine_bonus,
    fine_key,
    fine_of,
    group_counts,
    load_combos,
    next_fine_step,
    next_step,
)


def test_every_vertical_has_one_group():
    c = load_combos()
    assert sorted(c.group_of) == sorted(
        ["restaurantes", "turbo", "supermercado", "conveniencia", "farmacia", "licores", "mall", "chocolateria"]
    )
    assert c.group_of["mall"] == "retail" and c.group_of["turbo"] == "turbo"
    assert GROUP_ORDER == ("rest", "turbo", "retail")


def test_combo_key_is_canonical():
    assert combo_key(["retail", "rest", "turbo"]) == "rest+turbo+retail"
    assert combo_key([]) == "ninguna"
    assert combo_of_verticals(["mall", "restaurantes", "farmacia"]) == "rest+retail"
    assert combo_of_verticals([]) == "ninguna"


def test_rappi_table_is_loaded_verbatim():
    c = load_combos()
    r = c.rappi["rest+turbo+retail"]
    assert (r.users, r.pct_users, r.orders_per_user, r.retention_m1, r.spend_per_user) == (56000, 4.7, 10.5, 0.93, 257)
    assert set(c.rappi) == {
        "rest",
        "turbo",
        "rest+turbo",
        "retail",
        "rest+retail",
        "rest+turbo+retail",
        "turbo+retail",
        "favor",
    }
    assert (c.rappi_total.users, c.rappi_total.retention_m1, c.rappi_total.spend_per_user) == (1180000, 0.55, 68)
    assert "correlación, no un efecto" in c.source_note


def test_next_step_follows_the_retention_ladder():
    assert next_step("rest")[:2] == ("turbo", "rest+turbo")  # 0.82 > 0.76
    assert next_step("rest+turbo")[:2] == ("retail", "rest+turbo+retail")
    assert next_step("retail")[:2] == ("turbo", "turbo+retail")  # 0.80 > 0.76
    assert next_step("turbo")[:2] == ("rest", "rest+turbo")  # 0.82 > 0.80
    assert next_step("rest")[2] == pytest.approx(0.82 - 0.47)
    assert next_step("rest+turbo+retail") is None and next_step("ninguna") is None


def test_learned_retention_needs_enough_people_and_blends():
    assert expected_retention("rest", {"rest": (10, 0.9)}) == 0.47
    assert expected_retention("rest", {"rest": (100, 0.67)}) == pytest.approx((0.47 * 100 + 0.67 * 100) / 200)
    assert expected_retention("ninguna") is None
    assert expected_retention("ninguna", {"ninguna": (50, 0.3)}) == 0.3  # Rappi no tiene la fila: solo la aprendida
    assert expected_retention("ninguna", {"ninguna": (5, 0.3)}) is None


def test_next_step_uses_learned_retention():
    learned = {"rest+turbo": (400, 0.40), "rest+retail": (400, 0.95)}  # lo aprendido invierte el orden
    assert next_step("rest", learned)[:2] == ("retail", "rest+retail")


def test_next_step_skips_combos_not_built_from_the_groups():
    """Favor tiene fila en la tabla de Rappi pero no es un grupo: no hay paso siguiente (antes lanzaba ValueError)."""
    assert next_step("favor") is None
    assert next_step("otra+rest") is None


def test_combo_of_verticals_accepts_a_generator():
    """Recorre su argumento dos veces: con un generador devolvía siempre «ninguna»."""
    assert combo_of_verticals(v for v in ["restaurantes", "supermercado"]) == "rest+retail"


# --- Combinaciones finas: verticales del catálogo más RappiFavor y RappiTravel ---

REST_TURBO_SUPER = "restaurantes+turbo+supermercado"
ALL_OFFERABLE = "restaurantes+turbo+supermercado+conveniencia+mall+chocolateria"
# Lo que se le puede ofrecer a alguien que lo usa todo: Farmacia y Licores van igual, para probar que se saltan.
EVERY_CANDIDATE = ["farmacia", "licores", "conveniencia", "mall", "chocolateria", "favor", "travel"]


def test_fine_order_and_keys():
    expected = "restaurantes turbo supermercado conveniencia mall chocolateria farmacia licores favor travel"
    assert expected.split() == list(FINE_ORDER)
    assert fine_key(["travel", "supermercado", "restaurantes", "favor"]) == "restaurantes+supermercado+favor+travel"
    assert fine_key([]) == "ninguna"
    assert fine_of(["mall", "restaurantes", "mall"], ["travel"]) == "restaurantes+mall+travel"
    assert fine_of(v for v in ["turbo"]) == "turbo"
    assert fine_of([]) == "ninguna"
    with pytest.raises(ValueError):
        fine_key(["otra"])
    with pytest.raises(ValueError):
        fine_of(["favor"])  # un servicio no es un vertical del catálogo
    with pytest.raises(ValueError):
        fine_of([], ["turbo"])  # ni un vertical es un servicio


def test_services_and_assumption_come_from_the_toml():
    c = load_combos()
    assert c.services == {"favor": "rappifavor", "travel": "rappitravel"}
    a = c.diminishing
    assert (a.base, a.decay, a.service, a.cap) == (0.04, 0.5, 0.02, 0.97)
    assert "supuesto propio" in a.note


def test_group_counts_count_catalog_verticals_only():
    assert group_counts("restaurantes+supermercado+conveniencia+farmacia+favor") == {"rest": 1, "retail": 3}
    assert group_counts("favor+travel") == {}
    assert group_counts("ninguna") == {}


def test_bonus_diminishes_within_a_group():
    assert fine_bonus("restaurantes+supermercado") == 0
    assert fine_bonus("restaurantes+supermercado+conveniencia") == pytest.approx(0.04)
    assert fine_bonus("restaurantes+supermercado+conveniencia+mall") == pytest.approx(0.04 + 0.02)
    assert fine_bonus("supermercado+conveniencia+mall+chocolateria") == pytest.approx(0.04 + 0.02 + 0.01)
    assert fine_bonus("restaurantes+favor") == pytest.approx(0.02)  # cada servicio usado suma 0,02
    assert fine_bonus("restaurantes+favor+travel") == pytest.approx(0.04)
    assert fine_bonus("favor") == 0  # solo Favor: es la base (la fila «favor» de Rappi), no un bono
    assert fine_bonus("favor+travel") == pytest.approx(0.02)


def test_expected_fine_retention_adds_the_bonus_to_the_coarse_one():
    assert expected_fine_retention("restaurantes") == 0.47
    assert expected_fine_retention("restaurantes+supermercado+conveniencia") == pytest.approx(0.76 + 0.04)
    assert expected_fine_retention("restaurantes+favor") == pytest.approx(0.47 + 0.02)
    assert expected_fine_retention("ninguna") is None


def test_expected_fine_retention_of_services_only():
    assert expected_fine_retention("favor") == 0.44
    assert expected_fine_retention("favor+travel") == pytest.approx(0.44 + 0.02)
    assert expected_fine_retention("travel") is None
    assert expected_fine_retention("favor", {"favor": (100, 0.64)}) == pytest.approx(0.54)


def test_cap_holds_for_every_fine_combo():
    assert expected_fine_retention("restaurantes+turbo+supermercado+conveniencia+mall") == 0.97
    for k in range(1, len(FINE_ORDER) + 1):
        for members in combinations(FINE_ORDER, k):
            value = expected_fine_retention(fine_key(members))
            assert value is None or value <= 0.97, members


def test_cap_never_lowers_a_learned_coarse_retention():
    learned = {"rest+turbo+retail": (900, 0.99)}  # (0,93·100 + 0,99·900) / 1000 = 0,984
    assert expected_fine_retention(REST_TURBO_SUPER, learned) == pytest.approx(0.984)
    assert expected_fine_retention(REST_TURBO_SUPER + "+conveniencia", learned) == pytest.approx(0.984)


def test_expected_fine_retention_blends_learned_values():
    fine = "restaurantes+supermercado+conveniencia"
    assert expected_fine_retention(fine, learned_fine={fine: (10, 0.6)}) == pytest.approx(0.80)
    assert expected_fine_retention(fine, learned_fine={fine: (100, 0.6)}) == pytest.approx(
        (0.80 * 100 + 0.6 * 100) / 200
    )
    # La gruesa aprendida mueve la base: (0,76·100 + 0,56·100) / 200 = 0,66, más el bono
    assert expected_fine_retention(fine, {"rest+retail": (100, 0.56)}) == pytest.approx(0.66 + 0.04)
    assert expected_fine_retention("travel", learned_fine={"travel": (40, 0.5)}) == 0.5  # sin base: solo lo aprendido


# Los cinco casos de la Review Focus, con candidatos armados a mano.


def test_review_retail_continues_inside_retail_never_pharmacy_or_liquor():
    step = next_fine_step(REST_TURBO_SUPER, EVERY_CANDIDATE)
    assert step == Step(
        vertical="conveniencia",
        current=REST_TURBO_SUPER,
        target=REST_TURBO_SUPER.replace("supermercado", "supermercado+conveniencia"),
        gain=pytest.approx(0.04),
        used_assumption=True,
    )
    assert next_fine_step(REST_TURBO_SUPER, ["farmacia", "licores"]) is None
    assert (
        next_fine_step(REST_TURBO_SUPER, ["mall", "conveniencia"]).vertical == "mall"
    )  # empate: el orden de la persona


def test_review_services_come_after_the_catalog():
    # Ya no queda ninguna vertical del catálogo que se le pueda ofrecer: el paso es un servicio.
    step = next_fine_step(REST_TURBO_SUPER, ["farmacia", "favor", "travel"])
    assert (step.vertical, step.target, step.used_assumption) == ("favor", REST_TURBO_SUPER + "+favor", True)
    assert step.gain == pytest.approx(0.02)
    assert next_fine_step(REST_TURBO_SUPER, ["travel", "favor"]).vertical == "travel"
    assert next_fine_step(REST_TURBO_SUPER + "+favor+travel", ["favor", "travel"]) is None
    # Una vertical del catálogo que gana algo, aunque sea menos que un servicio, va primero.
    fine = "turbo+supermercado+conveniencia+mall"
    step = next_fine_step(fine, ["favor", "chocolateria"])
    assert (step.vertical, step.gain) == ("chocolateria", pytest.approx(0.01))


def test_review_everything_offerable_saturates_at_the_cap():
    """Con las retenciones de Rappi, quien usa todo lo que se puede ofrecer ya está en el tope (0,93 + 0,07 → 0,97):
    un servicio no suma nada y no hay paso."""
    assert expected_fine_retention(ALL_OFFERABLE) == 0.97
    assert next_fine_step(ALL_OFFERABLE, EVERY_CANDIDATE) is None


def test_review_no_orders_means_no_step():
    assert next_fine_step("ninguna", EVERY_CANDIDATE) is None
    assert next_fine_step("travel", ["restaurantes"]) is None  # sin retención esperada de partida


def test_review_coarse_ladder_still_leads():
    step = next_fine_step("restaurantes", ["supermercado", "conveniencia", "turbo", "favor"])
    assert step == Step("turbo", "restaurantes", "restaurantes+turbo", pytest.approx(0.82 - 0.47), False)


def test_next_fine_step_uses_learned_values():
    learned_fine = {"restaurantes+turbo": (400, 0.40)}  # lo aprendido le baja la ganancia a Turbo
    step = next_fine_step("restaurantes", ["turbo", "supermercado"], learned_fine=learned_fine)
    assert step.vertical == "supermercado"

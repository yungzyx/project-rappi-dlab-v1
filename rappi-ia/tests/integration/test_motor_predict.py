"""La predicción del motor (motor/predict.py): el próximo vertical de una persona, su combinación de este mes y el
paso de combinación que más retención suma."""

from datetime import UTC, datetime, timedelta

import pytest

from rappi_ia.events import store as events
from rappi_ia.layers.runs import finish_layer_run, start_layer_run
from rappi_ia.motor.model import DEFAULT_ORDER, DEFAULT_WEIGHTS
from rappi_ia.motor.predict import current_combo, latest_weights, next_verticals, target_step

NOW = datetime(2026, 10, 10, 15, tzinfo=UTC)


def _order(db, user, vertical, days_ago, now=NOW):
    events.record_order(
        db,
        user,
        f"s-{vertical}-{days_ago}",
        f"c-{vertical}-{days_ago}",
        vertical,
        [{"entity_type": "catalog_item", "entity_id": "1", "concept_id": None, "unit_price": 1000}],
        ts=now - timedelta(days=days_ago),
    )


def test_next_verticals_puts_the_most_used_first(db):
    for days_ago in (2, 9, 16):
        _order(db, "u1", "farmacia", days_ago)
    _order(db, "u1", "restaurantes", 20)
    db.commit()

    ranked = next_verticals(db, "u1", now=NOW)

    assert [s.vertical for s in ranked][:2] == ["farmacia", "restaurantes"]
    assert sorted(s.vertical for s in ranked) == sorted(DEFAULT_ORDER)
    top = ranked[0]
    assert top.affinity > 0.5 and top.transition == 0 and top.popularity == 0  # Farmacia: solo lo propio
    assert ranked == sorted(ranked, key=lambda s: -s.score)


def test_next_verticals_uses_the_population_tables(db):
    """Sin historia propia (pero con un último pedido), mandan la transición y la popularidad de la población."""
    _order(db, "u1", "restaurantes", 40)
    db.commit()
    db.execute(
        """INSERT INTO vertical_transitions (data_source, from_vertical, to_vertical, n, prob)
           VALUES ('synthetic', 'restaurantes', 'mall', 9, 0.9), ('synthetic', 'restaurantes', 'licores', 1, 0.1)"""
    )

    ranked = next_verticals(db, "u1", now=NOW, population="synthetic")

    mall = next(s for s in ranked if s.vertical == "mall")
    licores = next(s for s in ranked if s.vertical == "licores")
    assert ranked[1].vertical == "mall"  # la afinidad propia (restaurantes) va primero
    assert mall.transition == pytest.approx(0.9)
    assert licores.transition == 0  # Licores nunca sube por datos de otros


def test_next_verticals_without_history_is_the_default_order(db):
    assert [s.vertical for s in next_verticals(db, "nadie", now=NOW)] == list(DEFAULT_ORDER)
    assert [s.vertical for s in next_verticals(db, None, now=NOW)] == list(DEFAULT_ORDER)


def test_current_combo_counts_the_last_30_days(db):
    _order(db, "u1", "restaurantes", 3)
    _order(db, "u1", "supermercado", 10)
    _order(db, "u1", "turbo", 45)  # fuera de la ventana
    db.commit()

    assert current_combo(db, "u1", now=NOW) == "rest+retail"
    assert current_combo(db, "nadie", now=NOW) == "ninguna"


def test_target_step_for_a_restaurant_only_person_is_turbo(db):
    now = datetime.now(UTC)
    _order(db, "u1", "restaurantes", 2, now=now)
    _order(db, "u1", "restaurantes", 5, now=now)
    db.commit()

    group, target, gain = target_step(db, "u1")

    assert (group, target) == ("turbo", "rest+turbo")
    assert gain > 0
    assert target_step(db, "nadie") is None


def test_latest_weights_default_without_runs(db):
    assert latest_weights(db, "synthetic") == DEFAULT_WEIGHTS

    tuned = {"afinidad": 1.0, "transicion": 0.5, "popularidad": 0.05}
    run = start_layer_run(db, "motor", "v")
    finish_layer_run(db, run, {"fuente": "prototype", "pesos": tuned})
    running = start_layer_run(db, "motor", "v")  # todavía corriendo: no cuenta
    assert running

    assert latest_weights(db, "prototype") == tuned
    assert latest_weights(db, "synthetic") == DEFAULT_WEIGHTS

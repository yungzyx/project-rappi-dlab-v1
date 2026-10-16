"""La evaluación del motor por fechas (motor/evaluate.py), con pedidos armados a mano."""

import json
from datetime import UTC, datetime, timedelta

import pytest

from rappi_ia.motor.data import Line, Order, Signal
from rappi_ia.motor.evaluate import (
    GRID_B,
    GRID_C,
    evaluate,
    evaluate_cross_sell,
    evaluate_next_vertical,
    evaluate_replenishment,
    make_split,
    rank_metrics,
    report,
    tune,
)

T0 = datetime(2026, 5, 1, 15, 0, tzinfo=UTC)
_seq = iter(range(1, 1_000_000))


def order(user, days, vertical, *concepts):
    lines = tuple(Line(c, "catalog_item", c, False) for c in concepts)
    return Order(user, f"o{next(_seq)}", None, T0 + timedelta(days=days), vertical, 1000.0, lines)


def signals_of(orders):
    return [Signal(o.user_id, o.ts, "order", o.vertical) for o in orders]


def test_rank_metrics_values():
    m = rank_metrics(["a", "b", "c"], {"b"})
    assert (m["hit1"], m["hit3"], m["mrr"]) == (0, 1, 0.5)
    assert m["ndcg"] == pytest.approx(1 / 1.5849625, rel=1e-6)
    assert rank_metrics(["a", "b", "c"], {"a", "b"})["ndcg"] == pytest.approx(1.0)
    assert rank_metrics(["a", "b"], set()) == {"hit1": 0, "hit3": 0, "mrr": 0.0, "ndcg": 0.0}


def test_split_needs_84_days():
    short = [order("u1", 0, "turbo"), order("u1", 83, "turbo")]
    assert make_split(short) is None
    assert make_split([]) is None

    orders = [order("u1", 0, "turbo"), order("u1", 84, "turbo")]
    split = make_split(orders)
    assert split.test_end > orders[-1].ts  # el último pedido entra en la prueba
    assert split.test_end - split.valid_end == timedelta(days=28)
    assert split.valid_end - split.train_end == timedelta(days=28)


def _graduates(n=60):
    """Personas que piden tres veces en Supermercado y después pasan a Mall, empezando en días escalonados: la afinidad
    no ve venir Mall (nunca lo pidieron) y las transiciones de quienes pasaron antes, sí. Los clientes fijos de
    Restaurantes hacen que lo popular no sea Mall (la popularidad sola no lo adivina)."""
    orders = []
    for i in range(n):
        start = 2 * i
        orders += [order(f"u{i}", start + d, "supermercado") for d in (0, 7, 14)]
        orders.append(order(f"u{i}", start + 21, "mall"))
    orders += [order(f"r{i}", d + i % 4, "restaurantes") for i in range(20) for d in range(0, 140, 4)]
    return sorted(orders, key=lambda o: o.ts)


def test_tune_picks_transitions_when_people_alternate():
    orders = _graduates()
    signals = signals_of(orders)
    split = make_split(orders)

    weights = tune(orders, signals, split)
    assert weights["afinidad"] == 1
    assert weights["transicion"] > 0
    assert weights["transicion"] in GRID_B and weights["popularidad"] in GRID_C

    test = evaluate_next_vertical(orders, signals, split.valid_end, split.test_end, weights)
    assert set(test) >= {"orden_fijo", "popularidad", "afinidad", "transicion", "combinado"}
    assert test["combinado"]["ndcg"] > test["afinidad"]["ndcg"]
    assert test["combinado"]["personas"] == test["afinidad"]["personas"] > 0


def test_tune_ties_go_to_the_smallest_weights():
    # Todos piden siempre lo mismo: cualquier peso da el mismo nDCG y gana (b, c) = (0, 0).
    orders = sorted((order(f"u{i}", d + i, "turbo") for i in range(10) for d in range(0, 120, 10)), key=lambda o: o.ts)
    weights = tune(orders, signals_of(orders), make_split(orders))
    assert weights == {"afinidad": 1.0, "transicion": 0.0, "popularidad": 0.0}


def test_evaluate_cross_sell_precision_and_coverage():
    cut = T0 + timedelta(days=100)
    orders = []
    # 12 personas aprenden la regla: sushi en Restaurantes → salsa de soya en Turbo.
    for i in range(12):
        orders += [order(f"a{i}", 10 + i, "restaurantes", "sushi"), order(f"a{i}", 12 + i, "turbo", "salsa-soya")]
    # Otras 12 piden pan en Supermercado (lo más pedido de los últimos 28 días, sin relación con sushi).
    orders += [order(f"b{i}", 80 + i, "supermercado", "pan") for i in range(12)]
    # Dos personas a evaluar: pidieron sushi hace poco; una compra la soya después del corte y la otra no.
    orders += [order("x", 95, "restaurantes", "sushi"), order("x", 103, "turbo", "salsa-soya")]
    orders += [order("y", 96, "restaurantes", "sushi"), order("y", 104, "restaurantes", "sushi")]
    orders.sort(key=lambda o: o.ts)

    out = evaluate_cross_sell(orders, frozenset(), cut, cut + timedelta(days=28))
    # Solo x e y tienen predicción (la soya); los demás ya la pidieron o no pidieron sushi en los últimos 30 días.
    assert out["precision3"] == pytest.approx(0.5)
    assert out["personas_con_prediccion"] == 2
    assert out["cobertura"] == pytest.approx(2 / 26)
    baseline = out["lo_mas_pedido"]
    assert baseline["precision3"] < out["precision3"]
    assert baseline["cobertura"] == pytest.approx(1.0)


def test_evaluate_replenishment_error_in_days():
    cut = T0 + timedelta(days=100)
    orders = [order("u1", d, "supermercado", "leche") for d in (70, 80, 90)]  # le toca el día 100
    orders.append(order("u1", 103, "supermercado", "leche"))  # la compra 3 días tarde
    orders += [order("u2", d, "turbo", "pan") for d in (80, 87, 94)]  # le toca el día 101 y no vuelve
    orders += [order("u3", d, "turbo", "cafe") for d in (10, 20, 30)]  # le tocaba el día 40: fuera de la ventana
    orders.sort(key=lambda o: o.ts)

    out = evaluate_replenishment(orders, frozenset(), cut, cut + timedelta(days=28))
    assert out["n"] == 2
    assert out["error_mediano_dias"] == 3
    assert out["acierto_7_dias"] == pytest.approx(0.5)


def test_report_warns_on_synthetic():
    orders = _graduates()
    results = evaluate(orders, signals_of(orders), frozenset())
    json.dumps(results)  # va a `counts` de la corrida

    text = report(results, "synthetic")
    assert "Datos simulados: esto prueba la mecánica del motor, no su efecto" in text
    assert "combinado" in text and "orden_fijo" in text
    assert "Datos simulados" not in report(results, "prototype")


def test_evaluate_without_enough_data_is_none():
    orders = [order("u1", 0, "turbo"), order("u1", 10, "turbo")]
    assert evaluate(orders, signals_of(orders), frozenset()) is None

"""Métricas del panel del motor: las combinaciones de verticales, la evaluación y los toques de accesos de la Home."""

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from psycopg.types.json import Jsonb

from rappi_ia.analytics import queries
from rappi_ia.api import app as api
from rappi_ia.events import store as events
from rappi_ia.layers.runs import finish_layer_run, start_layer_run
from rappi_ia.motor.combos import load_combos

NOW = datetime(2026, 10, 11, 12, tzinfo=UTC)
RAPPI_ORDER = ["rest", "turbo", "rest+turbo", "retail", "rest+retail", "rest+turbo+retail", "turbo+retail", "favor"]


def _combo(db, source, combo, months, retention_n, retention=0.8, run_id=None):
    db.execute(
        """INSERT INTO combo_stats (data_source, combo, user_months, pct_users, pct_orders, orders_per_user,
                                    retention_m1, retention_n, spend_per_user, run_id)
           VALUES (%s, %s, %s, 50, 40, 2.5, %s, %s, 12000, %s)""",
        (source, combo, months, retention, retention_n, run_id),
    )


def _run(db, source, counts=None, status="done", finished_at="2026-10-11 12:00+00"):
    run = start_layer_run(db, "motor", "test")
    finish_layer_run(db, run, {"fuente": source, **(counts or {})}, status)
    db.execute("UPDATE layer_runs SET finished_at = %s WHERE run_id = %s", (finished_at, run))
    return run


def _tap(user, vertical, mode=None, kind="vertical_open"):
    payload = {} if mode is None else {"mode": mode}
    return events.Event(user, "s1", kind, ts=NOW, vertical=vertical, payload=payload)


def test_combos_without_own_data_still_carry_the_rappi_table(db):
    data = queries.combos(db, "prototype")

    assert list(data) == ["rappi", "propio", "nota"]
    assert data["propio"] == []
    assert [row["combo"] for row in data["rappi"]["filas"]] == RAPPI_ORDER
    rest_turbo = data["rappi"]["filas"][2]
    assert rest_turbo == {
        "combo": "rest+turbo",
        "usuarios": 78000,
        "pct_usuarios": 6.6,
        "pct_pedidos": 12.2,
        "pedidos_por_usuario": 5.5,
        "retencion_m1": 0.82,
        "gasto_por_usuario": 123,
    }
    assert data["rappi"]["total"]["combo"] == "total"
    assert data["rappi"]["total"]["usuarios"] == 1180000
    assert data["rappi"]["nota"] == load_combos().source_note
    assert "Es una correlación, no un efecto" in data["rappi"]["nota"]


def test_combos_own_rows_are_the_sources_only_ordered_by_user_months(db):
    _combo(db, "synthetic", "rest", 50, 40)
    _combo(db, "synthetic", "rest+turbo", 120, 100, retention=0.9)
    _combo(db, "prototype", "turbo", 3, 0)

    synthetic = queries.combos(db, "synthetic")
    prototype = queries.combos(db, "prototype")

    assert [row["combo"] for row in synthetic["propio"]] == ["rest+turbo", "rest"]
    assert [row["combo"] for row in prototype["propio"]] == ["turbo"]
    assert synthetic["propio"][0] == {
        "combo": "rest+turbo",
        "meses_usuario": 120,
        "pct_usuarios": 50.0,
        "pct_pedidos": 40.0,
        "pedidos_por_usuario": 2.5,
        "retencion_m1": pytest.approx(0.9),
        "retencion_n": 100,
        "gasto_por_usuario": 12000.0,
    }
    # La tabla de Rappi es la misma con cualquier fuente.
    assert synthetic["rappi"] == prototype["rappi"]


def test_combos_retention_needs_thirty_months_with_a_next_month(db):
    _combo(db, "synthetic", "rest", 100, 30)
    _combo(db, "synthetic", "turbo", 90, 29)
    _combo(db, "synthetic", "retail", 80, 0, retention=None)

    rows = {row["combo"]: row for row in queries.combos(db, "synthetic")["propio"]}

    assert rows["rest"]["retencion_m1"] == pytest.approx(0.8)
    assert rows["turbo"]["retencion_m1"] is None
    assert rows["retail"]["retencion_m1"] is None


def test_combos_label_each_source_and_never_present_simulated_as_evidence(db):
    assert queries.combos(db, "synthetic")["nota"] == "Simulado: no es evidencia"
    assert queries.combos(db, "prototype")["nota"] == "uso del MVP, pocas personas: no es evidencia"
    with pytest.raises(ValueError):
        queries.combos(db, "real")


def test_motor_is_null_until_a_run_is_done_for_that_source(db):
    assert queries.motor(db, "synthetic") is None
    _run(db, "synthetic", {"pesos": {"afinidad": 1.0}}, status="failed")
    _run(db, "synthetic", status="running")
    _run(db, "prototype", {"pesos": {"afinidad": 1.0}})

    assert queries.motor(db, "synthetic") is None


def test_motor_reads_the_latest_done_run_of_the_source(db):
    old = {"pesos": {"afinidad": 1.0, "transicion": 0.1, "popularidad": 0.1}, "lambda_cruzada": 1.0, "evaluacion": None}
    new = {
        "pesos": {"afinidad": 1.0, "transicion": 0.5, "popularidad": 0.3},
        "lambda_cruzada": 2.0,
        "evaluacion": {"proximo_vertical": {"combinado": {"ndcg": 0.8}}},
        "pedidos": 999,
    }
    _run(db, "synthetic", old, finished_at="2026-10-10 12:00+00")
    _run(db, "synthetic", new, finished_at="2026-10-11 12:00+00")
    _run(db, "prototype", {"pesos": {"afinidad": 1.0, "transicion": 0, "popularidad": 0}, "lambda_cruzada": 0.5})
    _run(db, "synthetic", {"pesos": {"afinidad": 9.0}}, status="failed")

    data = queries.motor(db, "synthetic")

    assert data == {
        "pesos": new["pesos"],
        "lambda_cruzada": 2.0,
        "evaluacion": new["evaluacion"],
        "fecha": "2026-10-11T12:00:00+00:00",
    }
    assert queries.motor(db, "prototype")["lambda_cruzada"] == 0.5
    assert queries.motor(db, "prototype")["evaluacion"] is None


def test_motor_keeps_the_stored_evaluation_untouched(db):
    evaluation = {"pesos": {"afinidad": 1.0}, "recompra": {"n": 4, "error_mediano_dias": None}}
    run = start_layer_run(db, "motor", "test")
    db.execute(
        "UPDATE layer_runs SET status = 'done', finished_at = now(), counts = %s WHERE run_id = %s",
        (Jsonb({"fuente": "prototype", "pesos": {}, "evaluacion": evaluation}), run),
    )

    assert queries.motor(db, "prototype")["evaluacion"] == evaluation


def test_home_counts_people_and_taps_per_vertical_without_rappi_hoy(db):
    events.record(
        db,
        [
            _tap("p1", "farmacia"),
            _tap("p1", "farmacia"),
            _tap("p2", "farmacia"),
            _tap("p1", "mall"),
            _tap("p1", "licores", mode="actual"),  # «Rappi hoy» no enseña
            _tap("p3", "turbo", kind="app_open"),  # no es un toque de acceso
        ],
    )
    events.record(db, [_tap("s1", "supermercado")], source="synthetic")

    data = queries.home(db, "prototype")

    assert data == {
        "personas": 2,
        "toques": 4,
        "verticales": [
            {"vertical": "farmacia", "personas": 2, "toques": 3},
            {"vertical": "mall", "personas": 1, "toques": 1},
        ],
    }
    assert queries.home(db, "synthetic") == {
        "personas": 1,
        "toques": 1,
        "verticales": [{"vertical": "supermercado", "personas": 1, "toques": 1}],
    }


def test_home_without_taps_is_empty(db):
    for source in ("prototype", "synthetic"):
        assert queries.home(db, source) == {"personas": 0, "toques": 0, "verticales": []}
    with pytest.raises(ValueError):
        queries.home(db, "real")


def test_the_three_metrics_are_served_by_the_panel_api(db):
    def conn_override():
        yield db

    api.app.dependency_overrides[api.get_conn] = conn_override
    try:
        client = TestClient(api.app)
        for name in ("combos", "motor", "home"):
            for source in ("prototype", "synthetic"):
                reply = client.get(f"/analytics/{name}", params={"source": source})
                assert reply.status_code == 200, name
                assert reply.json()["source"] == source
            assert client.get(f"/analytics/{name}", params={"source": "real"}).status_code == 422
        assert client.get("/analytics/motor", params={"source": "prototype"}).json()["data"] is None
        assert client.get("/analytics/combos", params={"source": "prototype"}).json()["data"]["propio"] == []
    finally:
        api.app.dependency_overrides.clear()

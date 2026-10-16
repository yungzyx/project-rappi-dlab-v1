"""`rappi-ia motor`: arma las tablas del motor de una fuente (población y cada persona) y recalcula a una persona
después de su pedido o de «Olvidar».

Las tablas de población (transiciones, combinaciones, compra cruzada, tendencias) se reemplazan enteras por fuente;
las de cada persona (afinidad, recompra), por persona. El modelo vive en `model.py` (funciones puras) y lo que se lee de
la base, en `data.py`.
"""

import logging
import time
from collections import defaultdict
from collections.abc import Callable, Iterable
from contextlib import AbstractContextManager
from datetime import UTC, datetime
from pathlib import Path

import psycopg
from psycopg import Connection

from ..layers.runs import finish_layer_run, rules_version, start_layer_run
from ..layers.segments import lock_user_segments
from . import model
from .combos import FILE as COMBOS_FILE
from .combos import load_combos
from .data import Order, Signal, load_orders, load_signals, sensitive_concepts
from .model import (
    AFFINITY_WINDOW_DAYS,
    DEFAULT_ORDER,
    DEFAULT_WEIGHTS,
    TZ,
    affinity,
    combo_months,
    combo_stats,
    combo_steps,
    cross_sell,
    replenishment,
    transition_counts,
    transitions,
    trends,
)

log = logging.getLogger(__name__)


def build_motor(conn: Connection, source: str) -> dict:
    """Recalcula el motor de una fuente en una sola transacción: las 5 tablas de población y la afinidad y la recompra
    de todas sus personas. `now` es el último pedido de la fuente (los simulados terminan en una fecha pasada). La
    corrida queda en `layer_runs` (capa `motor`, con la fuente y los pesos en `counts`); si algo falla, queda `failed`
    y no se escribe nada."""
    run = start_layer_run(conn, "motor", rules_version(load_combos().version, COMBOS_FILE, Path(model.__file__)))
    conn.commit()  # la corrida se ve aunque lo demás falle
    start = time.perf_counter()
    try:
        counts = _build(conn, source, run)
    except Exception as exc:
        conn.rollback()
        finish_layer_run(conn, run, {"fuente": source, "error": type(exc).__name__}, "failed")
        conn.commit()
        raise
    finish_layer_run(conn, run, counts)
    conn.commit()
    log.info("Motor (%s) en %.1f s: %s", source, time.perf_counter() - start, counts)
    return counts


def _build(conn: Connection, source: str, run: int) -> dict:
    for table in ("vertical_transitions", "combo_stats", "combo_steps", "cross_sell_rules", "trends"):
        conn.execute(f"DELETE FROM {table} WHERE data_source = %s", (source,))
    _delete_personal(conn, "user_id IN (SELECT user_id FROM app_users WHERE source = %s)", source)
    counts = {
        "fuente": source,
        "transiciones": 0,
        "combinaciones": 0,
        "pasos": 0,
        "reglas": 0,
        "tendencias": 0,
        "afinidad": 0,
        "recompra": 0,
        "pesos": dict(DEFAULT_WEIGHTS),
    }
    orders = load_orders(conn, source)
    if not orders:
        return counts
    now = max(o.ts for o in orders)
    sensitive = sensitive_concepts(conn)

    probs = transitions(orders)
    rows = [
        (source, start, to, row[to], probs[start][to], run)
        for start, row in transition_counts(orders).items()
        for to in DEFAULT_ORDER
    ]
    counts["transiciones"] = _copy(
        conn, "vertical_transitions", "data_source, from_vertical, to_vertical, n, prob, run_id", rows
    )

    months = combo_months(orders)
    rows = [
        (source, combo, s["user_months"], s["pct_users"], s["pct_orders"], s["orders_per_user"], s["retention_m1"],
         s["retention_n"], s["spend_per_user"], run)
        for combo, s in combo_stats(months).items()
    ]  # fmt: skip
    counts["combinaciones"] = _copy(
        conn,
        "combo_stats",
        "data_source, combo, user_months, pct_users, pct_orders, orders_per_user, retention_m1, retention_n, "
        "spend_per_user, run_id",
        rows,
    )
    rows = [(source, a, b, users, prob, run) for (a, b), (users, prob) in combo_steps(months).items()]
    counts["pasos"] = _copy(conn, "combo_steps", "data_source, from_combo, to_combo, users, prob, run_id", rows)

    rows = [
        (source, r.from_concept, r.from_vertical, r.to_concept, r.to_vertical, r.users_from, r.users_both,
         r.confidence, r.lift, run)
        for r in cross_sell(orders, sensitive)
    ]  # fmt: skip
    counts["reglas"] = _copy(
        conn,
        "cross_sell_rules",
        "data_source, from_concept, from_vertical, to_concept, to_vertical, users_from, users_both, confidence, lift, "
        "run_id",
        rows,
    )

    window_end = now.astimezone(TZ).date()
    rows = [
        (source, t.scope, t.vertical, t.item_key, t.concept_id, t.entity_type, t.entity_id, t.orders_now,
         t.orders_prev, t.users_now, t.growth, t.rank, window_end, run)
        for t in trends(orders, window_end, sensitive)
    ]  # fmt: skip
    counts["tendencias"] = _copy(
        conn,
        "trends",
        "data_source, scope, vertical, item_key, concept_id, entity_type, entity_id, orders_now, orders_prev, "
        "users_now, growth, rank, window_end, run_id",
        rows,
    )

    affinity_rows, replenish_rows = _personal_rows(load_signals(conn, source), orders, now, sensitive)
    counts["afinidad"], counts["recompra"] = _write_personal(conn, affinity_rows, replenish_rows)
    return counts


def _personal_rows(
    signals: Iterable[Signal], orders: list[Order], now: datetime, sensitive: frozenset[str]
) -> tuple[list[tuple], list[tuple]]:
    """Las filas de afinidad (con pedidos, señales y la última, dentro de la misma ventana que el puntaje) y de
    recompra de las personas de `signals` y `orders`."""
    signals = list(signals)
    scores = affinity(signals, now)
    seen: dict[tuple[str, str], list] = defaultdict(lambda: [0, 0, None])  # pedidos, señales, última
    for s in signals:
        age = (now - s.ts).total_seconds() / 86400
        if age < 0 or age > AFFINITY_WINDOW_DAYS:  # la ventana de `model.affinity`
            continue
        row = seen[s.user_id, s.vertical]
        row[0] += s.kind == "order"
        row[1] += 1
        row[2] = s.ts if row[2] is None or s.ts > row[2] else row[2]
    affinity_rows = [
        (user, vertical, score, *seen[user, vertical])
        for user, by_vertical in scores.items()
        for vertical, score in by_vertical.items()
    ]
    replenish_rows = [
        (r.user_id, r.concept_id, r.vertical, r.orders, r.interval_days, r.cv, r.last_ts, r.due_on)
        for r in replenishment(orders, sensitive)
    ]
    return affinity_rows, replenish_rows


def _write_personal(conn: Connection, affinity_rows: list[tuple], replenish_rows: list[tuple]) -> tuple[int, int]:
    """Con `ON CONFLICT`, no COPY: el recálculo de una persona después de su pedido puede guardar sus filas mientras
    corre `build_motor` de su fuente; ninguno de los dos falla y queda el último en confirmar. Las filas van en orden
    de llave: los dos toman los candados de fila en el mismo orden y no se bloquean en cruz."""
    affinity_rows = sorted(affinity_rows, key=lambda r: (r[0], r[1]))
    replenish_rows = sorted(replenish_rows, key=lambda r: (r[0], r[1]))
    with conn.cursor() as cur:
        cur.executemany(
            """INSERT INTO user_vertical_affinity (user_id, vertical, score, orders, signals, last_ts)
               VALUES (%s, %s, %s, %s, %s, %s)
               ON CONFLICT (user_id, vertical) DO UPDATE SET score = EXCLUDED.score, orders = EXCLUDED.orders,
                 signals = EXCLUDED.signals, last_ts = EXCLUDED.last_ts, updated_at = now()""",
            affinity_rows,
        )
        cur.executemany(
            """INSERT INTO replenishment (user_id, concept_id, vertical, orders, interval_days, cv, last_ts, due_on)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (user_id, concept_id) DO UPDATE SET vertical = EXCLUDED.vertical,
                 orders = EXCLUDED.orders, interval_days = EXCLUDED.interval_days, cv = EXCLUDED.cv,
                 last_ts = EXCLUDED.last_ts, due_on = EXCLUDED.due_on, updated_at = now()""",
            replenish_rows,
        )
    return len(affinity_rows), len(replenish_rows)


def _delete_personal(conn: Connection, where: str, param: str) -> None:
    for table in ("user_vertical_affinity", "replenishment"):
        conn.execute(f"DELETE FROM {table} WHERE {where}", (param,))


def _copy(conn: Connection, table: str, columns: str, rows: list[tuple]) -> int:
    """Carga `rows` con COPY (las tablas de población, que solo escribe `build_motor`); devuelve cuántas."""
    if rows:
        with conn.cursor() as cur, cur.copy(f"COPY {table} ({columns}) FROM STDIN") as copy:
            for row in rows:
                copy.write_row(row)
    return len(rows)


# Una persona


def refresh_user_conn(conn: Connection, user_id: str, now: datetime | None = None) -> None:
    """La afinidad y la recompra de una persona del prototipo, recalculadas con sus propios datos en la transacción de
    `conn`, sin confirmarla. Si la persona ya no está («Olvidar» entero), solo borra lo suyo; a una simulada no la toca
    (sus filas las arma `build_motor`, con el `now` de su fuente). Toma el candado por persona que comparten el
    recálculo de segmentos y «Olvidar»."""
    lock_user_segments(conn, user_id)
    row = conn.execute("SELECT source FROM app_users WHERE user_id = %s", (user_id,)).fetchone()
    if row is not None and row[0] != "prototype":
        return
    _delete_personal(conn, "user_id = %s", user_id)
    if row is None:
        return
    source = row[0]
    orders = load_orders(conn, source, user_id)
    affinity_rows, replenish_rows = _personal_rows(
        load_signals(conn, source, user_id), orders, now or datetime.now(UTC), sensitive_concepts(conn)
    )
    _write_personal(conn, affinity_rows, replenish_rows)


def refresh_user(connector: Callable[[], AbstractContextManager[Connection]], user_id: str) -> None:
    """Lo mismo, después de un pedido: en segundo plano, con su propia conexión, y sin levantar nunca una excepción
    (queda en el log, sin el id de la persona; quien pidió ya tiene su respuesta)."""
    start = time.perf_counter()
    try:
        with connector() as conn:
            refresh_user_conn(conn, user_id)
            conn.commit()
    except psycopg.Error as exc:
        # El texto de Postgres puede traer la fila (`Key (user_id)=(…)`): solo la clase y el sqlstate, sin traza.
        log.warning(
            "No se pudo recalcular el motor de la persona después de un pedido: %s (sqlstate %s)",
            type(exc).__name__,
            exc.sqlstate,
        )
        return
    except Exception:
        log.warning("No se pudo recalcular el motor de la persona después de un pedido", exc_info=True)
        return
    log.info("Motor de una persona recalculado en %.0f ms", (time.perf_counter() - start) * 1000)

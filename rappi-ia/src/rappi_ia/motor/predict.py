"""La predicción del motor para una persona: el próximo vertical, su combinación de grupos de este mes y el paso que más
retención suma.

Lee solo las filas de la persona y las tablas chicas de la población (transiciones, tendencias por vertical,
combinaciones, la última corrida); nunca recorre todos los pedidos en el momento de responder. La afinidad se calcula en
vivo con las señales de la propia persona, así que siempre está al día.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from psycopg import Connection

from .. import config
from .combos import combo_of_verticals, next_step
from .data import load_signals
from .model import DEFAULT_WEIGHTS, OWN_SIGNALS_ONLY, affinity, rank_verticals

CURRENT_COMBO_DAYS = 30


@dataclass(frozen=True)
class VerticalScore:
    """El puntaje de un vertical y sus tres piezas, antes de los pesos: afinidad normalizada (suma 1 entre los
    verticales de la persona), P(vertical | último vertical) y cuota de pedidos recientes de la población. Farmacia y
    Licores llevan 0 en las dos últimas: solo suben por lo propio."""

    vertical: str
    score: float
    affinity: float
    transition: float
    popularity: float


def latest_weights(conn: Connection, source: str) -> dict[str, float]:
    """Los pesos de la última corrida `motor` terminada de esa fuente; `DEFAULT_WEIGHTS` si no hay."""
    row = conn.execute(
        """SELECT counts->'pesos' FROM layer_runs
           WHERE layer = 'motor' AND status = 'done' AND counts->>'fuente' = %s AND counts ? 'pesos'
           ORDER BY run_id DESC LIMIT 1""",
        (source,),
    ).fetchone()
    return {k: float(v) for k, v in row[0].items()} if row else dict(DEFAULT_WEIGHTS)


def next_verticals(
    conn: Connection, user_id: str | None, population: str | None = None, now: datetime | None = None
) -> list[VerticalScore]:
    """Los 8 verticales en el orden en que conviene ofrecérselos a la persona (`model.rank_verticals`). `population`
    por defecto es `config.MOTOR_POBLACION`, leída al llamar."""
    population = population or config.MOTOR_POBLACION
    now = now or datetime.now(UTC)
    aff: dict[str, float] = {}
    last_vertical = None
    source = _source_of(conn, user_id) if user_id else None
    if source is not None:
        signals = [s for s in load_signals(conn, source, user_id) if s.ts <= now]
        aff = affinity(signals, now).get(user_id, {})
        last_vertical = next((s.vertical for s in reversed(signals) if s.kind == "order"), None)
    trans = {}
    if last_vertical is not None:
        rows = conn.execute(
            "SELECT to_vertical, prob FROM vertical_transitions WHERE data_source = %s AND from_vertical = %s",
            (population, last_vertical),
        ).fetchall()
        trans = {last_vertical: {to: float(prob) for to, prob in rows}}
    recent = dict(
        conn.execute(
            "SELECT vertical, orders_now FROM trends WHERE data_source = %s AND scope = 'vertical'", (population,)
        ).fetchall()
    )
    total_recent = sum(recent.values())
    pop = {v: n / total_recent for v, n in recent.items()} if total_recent else {}
    total_aff = sum(aff.values())
    out = []
    for vertical, score in rank_verticals(aff, last_vertical, trans, pop, latest_weights(conn, population)):
        own_only = vertical in OWN_SIGNALS_ONLY
        out.append(
            VerticalScore(
                vertical=vertical,
                score=score,
                affinity=aff.get(vertical, 0.0) / total_aff if total_aff else 0.0,
                transition=0.0 if own_only else trans.get(last_vertical, {}).get(vertical, 0.0),
                popularity=0.0 if own_only else pop.get(vertical, 0.0),
            )
        )
    return out


def current_combo(conn: Connection, user_id: str, now: datetime | None = None) -> str:
    """La combinación de grupos de los pedidos `propuesta` de la persona en los últimos 30 días («ninguna» sin
    pedidos)."""
    now = now or datetime.now(UTC)
    rows = conn.execute(
        """SELECT DISTINCT vertical FROM app_orders
           WHERE user_id = %s AND mode = 'propuesta' AND ts > %s AND ts <= %s""",
        (user_id, now - timedelta(days=CURRENT_COMBO_DAYS), now),
    ).fetchall()
    return combo_of_verticals(r[0] for r in rows)


def target_step(conn: Connection, user_id: str, population: str | None = None) -> tuple[str, str, float] | None:
    """El grupo que más retención le suma a la persona: `(grupo, combinación_objetivo, ganancia)`, con la retención de
    Rappi mezclada con la aprendida en `combo_stats` de la población; `None` si no hay paso."""
    population = population or config.MOTOR_POBLACION
    learned = {
        combo: (n, float(retention))
        for combo, n, retention in conn.execute(
            """SELECT combo, retention_n, retention_m1 FROM combo_stats
               WHERE data_source = %s AND retention_m1 IS NOT NULL""",
            (population,),
        )
    }
    return next_step(current_combo(conn, user_id), learned)


def _source_of(conn: Connection, user_id: str) -> str | None:
    row = conn.execute("SELECT source FROM app_users WHERE user_id = %s", (user_id,)).fetchone()
    return row[0] if row else None

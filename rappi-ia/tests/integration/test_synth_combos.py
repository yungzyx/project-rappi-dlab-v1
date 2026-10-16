"""Los simulados con la mezcla de combinaciones de Rappi (events/synth.py), medidos con SQL sobre app_orders.

Sobre el catálogo inventado de la demo: prueba la mecánica, no un efecto.
"""

from collections import Counter
from datetime import date

import pytest

from rappi_ia.demo.seed import seed_demo
from rappi_ia.events.synth import generate
from rappi_ia.motor.combos import combo_of_verticals

LAST_MONTH = date(2026, 10, 1)  # `until` cae en octubre: septiembre no tiene su M+1 completo


@pytest.fixture
def simulated(db):
    seed_demo(db)
    generate(db, users=1200, weeks=26, seed=3, until=date(2026, 10, 4))  # con 600, rest+turbo+retail no llega a 20
    return db


def _user_months(db) -> dict[tuple[str, date], str]:
    """La combinación de cada persona en cada mes calendario con pedidos."""
    verticals: dict[tuple[str, date], set[str]] = {}
    for user, month, vertical in db.execute(
        """SELECT DISTINCT user_id, date_trunc('month', ts AT TIME ZONE 'America/Santiago')::date, vertical
           FROM app_orders WHERE source = 'synthetic'"""
    ):
        verticals.setdefault((user, month), set()).add(vertical)
    return {key: combo_of_verticals(found) for key, found in verticals.items()}


def test_synthetic_users_mostly_order_only_restaurants(simulated):
    combos = Counter(_user_months(simulated).values())
    assert combos.most_common(1)[0][0] == "rest", combos


def test_more_groups_retain_more_in_the_simulation(simulated):
    months = _user_months(simulated)
    kept: dict[str, list[bool]] = {}
    for (user, month), combo in months.items():
        following = date(month.year + month.month // 12, month.month % 12 + 1, 1)
        if following >= LAST_MONTH:
            continue
        kept.setdefault(combo, []).append((user, following) in months)
    retention = {combo: sum(flags) / len(flags) for combo, flags in kept.items()}
    assert len(kept["rest+turbo+retail"]) >= 20, kept.keys()
    assert retention["rest+turbo+retail"] > retention["rest"], retention

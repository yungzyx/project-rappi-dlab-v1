"""El juego y el pasaporte salieron del proyecto: la base (migración 035) y la API ya no los conocen."""

import psycopg
import pytest

from owner_client import OwnerClient
from rappi_ia.api import app as api


@pytest.fixture
def client(db):
    def conn_override():
        yield db

    api.app.dependency_overrides[api.get_conn] = conn_override
    yield OwnerClient(api.app)
    api.app.dependency_overrides.clear()


def test_migration_035_drops_game_tables(db):
    rows = db.execute(
        "select table_name from information_schema.tables where table_schema='public' "
        "and table_name in ('knowledge_cards','knowledge_card_concepts','game_state')"
    ).fetchall()
    assert rows == []


def test_game_event_types_are_rejected(db):
    db.execute("insert into app_users(user_id, source) values ('u1','prototype')")
    with pytest.raises(psycopg.errors.CheckViolation):
        db.execute(
            "insert into app_events(user_id, session_id, type, source) "
            "values ('u1','s','game_round_finished','prototype')"
        )


def test_game_routes_are_gone(client):
    assert client.get("/game/cards").status_code == 404


def test_analytics_has_no_game():
    assert "game" not in api.ANALYTICS


def test_event_types_have_no_game():
    from rappi_ia.events.store import EVENT_TYPES

    assert not {t for t in EVENT_TYPES if t.startswith("game_")}

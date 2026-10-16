import pytest

from rappi_ia.motor.combos import (
    GROUP_ORDER,
    combo_key,
    combo_of_verticals,
    expected_retention,
    load_combos,
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

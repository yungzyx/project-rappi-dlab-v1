"""Lo destacado (offers/featured.py y offers/destacado.toml): las reglas de lo que la app muestra sin que la persona lo
pida, y su validación."""

import pytest

from rappi_ia.concepts.taxonomy import load_taxonomy
from rappi_ia.offers.featured import load_rules, main_dish, one_per_concept, side_dish


def test_the_rules_load_and_name_real_concepts():
    rules = load_rules()
    concepts = load_taxonomy().concepts
    assert rules.min_main_price > 0
    assert rules.not_main and rules.not_main <= set(concepts)
    assert rules.side_sections and rules.side_names


def rules_toml(price="3000", out="[]", sections="['x']", names="['y']") -> str:
    return (
        f"[plato_principal]\nprecio_minimo = {price}\nconceptos_fuera = {out}\n"
        f"[relleno]\nsecciones = {sections}\nnombres = {names}\n"
    )


@pytest.mark.parametrize(
    "content, message",
    [
        (rules_toml(price="0"), "precio_minimo"),
        (rules_toml(out="['no-existe']"), "no-existe"),
        (rules_toml(sections="[]"), "secciones"),
        (rules_toml(names="['']"), "nombres"),
    ],
)
def test_bad_rules_are_rejected(tmp_path, content, message):
    path = tmp_path / "destacado.toml"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        load_rules.__wrapped__(path)


@pytest.mark.parametrize(
    "name, section",
    [
        ("Bigtime refrescante celeste", "Para llevar"),  # el chicle de una pizzería, en su sección de caja
        ("Choclo", "Agregados"),
        ("Papas Trufadas Grandes", "Appetizer"),
        ("Coca-Cola 350 cc", "Bebidas y jugos"),
        ("Salsa de ajo", "Pizzas"),  # el nombre lo dice aunque la sección sea de platos
        ("BOLSA", None),
        ("Cubiertos desechables", "Otros"),
        ("Extra queso", "Pizzas"),
    ],
)
def test_side_dishes(name, section):
    assert side_dish(name, section)


@pytest.mark.parametrize(
    "name, section",
    [
        ("Tropical", "Pizzas"),
        ("Pizza con salsa pomodoro", "Pizzas"),  # «salsa» no es la primera palabra
        ("Promo pizza + bebida", "Pizzas y bebidas"),  # la sección no empieza con «bebidas»
        ("Rollo Sake Especial", "Panko Rolls"),
        ("Empanada de pino", None),
    ],
)
def test_main_dishes_are_not_side_dishes(name, section):
    assert not side_dish(name, section)


def test_a_main_dish_costs_at_least_the_minimum_and_is_not_a_dessert():
    rules = load_rules()
    assert main_dish(rules.min_main_price, "pizza")
    assert not main_dish(rules.min_main_price - 1, "pizza")
    assert not main_dish(None, "pizza")  # sin precio no se destaca
    assert not main_dish(9990, "postres")
    assert main_dish(9990, None)  # sin concepto, el precio decide


def test_one_per_concept_first_and_then_the_rest_in_order():
    products = [
        {"id": "a", "concept": "pizza"},
        {"id": "b", "concept": "pizza"},
        {"id": "c", "concept": "sushi"},
        {"id": "d", "concept": None},
        {"id": "e", "concept": "pizza"},
        {"id": "f", "concept": "pollo-preparado"},
    ]
    assert [p["id"] for p in one_per_concept(products, 3)] == ["a", "c", "d"]
    assert [p["id"] for p in one_per_concept(products, 5)] == ["a", "c", "d", "f", "b"]
    assert [p["id"] for p in one_per_concept(products[:2], 3)] == ["a", "b"]  # si no alcanzan, se repite

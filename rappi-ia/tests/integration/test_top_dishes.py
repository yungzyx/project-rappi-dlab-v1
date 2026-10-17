"""Lo más pedido de un restaurante (`offers.engine.top_dishes` y `with_top_dishes`): lo que dice su menú en Rappi (los
platos populares y una sección «Más vendidos»), con su último precio y las guardias de las ofertas, bajo los
restaurantes que propone el agente (`vertical_por_probar`, la escalera de `perfil`) y los del buscador."""

import pytest
from test_query_budget import CountingConnection

from conftest import add_dish
from owner_client import OwnerClient
from rappi_ia.agent.compose import TemplateComposer
from rappi_ia.agent.rappi_agent import RappiAgent
from rappi_ia.api import app as api
from rappi_ia.api.services import Services
from rappi_ia.catalog import cache
from rappi_ia.demo.seed import seed_demo
from rappi_ia.embeddings.base import HashEmbedder
from rappi_ia.embeddings.text_store import embed_search_documents
from rappi_ia.events import store as events
from rappi_ia.offers.engine import _TOP_SECTION, TOP_DISHES_LABEL, TOP_DISHES_SOURCE, top_dishes, with_top_dishes
from rappi_ia.text import normalize

# La pizzería de prueba tiene dos platos populares (margarita y tiramisú); la de sushi, ninguno.
PIZZA_STORE, SUSHI_STORE = 9801, 9802
PEPPERONI, MARGARITA, TIRAMISU = "menu-98001", "menu-98002", "menu-98004"


@pytest.fixture
def demo(db):
    seed_demo(db)
    embedder = HashEmbedder()
    embed_search_documents(db, embedder)
    return db, embedder


@pytest.fixture
def client(demo):
    db, embedder = demo

    def conn_override():
        yield db

    api.app.dependency_overrides[api.get_conn] = conn_override
    api.app.dependency_overrides[api.get_services] = lambda: Services(
        RappiAgent(embedder, TemplateComposer()), embedder
    )
    yield OwnerClient(api.app)
    api.app.dependency_overrides.clear()


def ids(dishes: list[dict]) -> list[str]:
    return [d["id"] for d in dishes]


def popular(db, *item_ids: int) -> None:
    db.execute("UPDATE menu_items SET is_popular = true WHERE item_id = ANY(%s)", (list(item_ids),))
    cache.clear()  # sin corrida nueva: como si la caché del catálogo hubiera vencido


def price(db, item_id: int, value: int | None) -> None:
    run_id = db.execute("SELECT max(run_id) FROM scrape_runs WHERE kind = 'restaurants'").fetchone()[0]
    db.execute(
        "INSERT INTO menu_price_snapshots (run_id, item_id, price, is_available) VALUES (%s, %s, %s, true)",
        (run_id, item_id, value),
    )


@pytest.mark.parametrize(
    "section",
    ["Más Vendidos", "Màs Vendidos", "LOS MAS PEDIDOS", "Lo más pedido", "Los 15 más pedidos de casa ohi", "Top 5"]
    + ["Mas Populares", "Populares", "Más Vendidos Rappi"],
)
def test_sections_that_say_most_ordered(section):
    assert _TOP_SECTION.search(normalize(section))


@pytest.mark.parametrize(
    "section",
    ["Recomendados", "Destacados", "Favoritos", "Big Bobas Populares", "Toppings", "TOP OFFERS", "Bebestibles"],
)
def test_sections_that_do_not(section):
    assert not _TOP_SECTION.search(normalize(section))


def test_popular_dishes_with_their_price_in_menu_order(demo):
    db, _ = demo
    found = top_dishes(db)
    # Margarita (sección Pizzas, la primera) antes que el tiramisú (Postres); los demás locales tienen uno o ninguno.
    assert ids(found[PIZZA_STORE]) == [MARGARITA, TIRAMISU]
    assert found[PIZZA_STORE][0]["price"] == "$8.990" and found[PIZZA_STORE][0]["store_id"] == PIZZA_STORE
    assert set(found) == {PIZZA_STORE}


def test_a_most_ordered_section_counts_and_popular_dishes_go_first(demo):
    db, _ = demo
    for item_id, name in ((98901, "Gyozas de cerdo (prueba)"), (98902, "Ramen shoyu (prueba)")):
        add_dish(db, item_id, name, SUSHI_STORE, "Los más pedidos")
        price(db, item_id, 5990)
    popular(db, 98007)  # la hamburguesa, popular en su propia sección

    assert ids(top_dishes(db)[SUSHI_STORE]) == ["menu-98007", "menu-98901", "menu-98902"]


def test_dishes_without_price_alcohol_or_a_drinks_section_are_left_out(demo):
    db, _ = demo
    add_dish(db, 98903, "Pisco sour de la casa (prueba)", SUSHI_STORE, "Más vendidos")
    add_dish(db, 98904, "Gyozas (prueba)", SUSHI_STORE, "Más vendidos")  # sin precio
    add_dish(db, 98905, "Udon de cerdo (prueba)", SUSHI_STORE, "Más vendidos")
    add_dish(db, 98906, "Ramen (prueba)", SUSHI_STORE, "Más vendidos")
    for item_id in (98903, 98905, 98906):
        price(db, item_id, 4990)
    price(db, 98904, None)
    popular(db, 98008)  # el jugo es popular...
    db.execute("UPDATE menu_sections SET name = 'Tragos' WHERE store_id = %s AND name = 'Bebidas'", (SUSHI_STORE,))

    assert ids(top_dishes(db)[SUSHI_STORE]) == ["menu-98905", "menu-98906"]  # ...pero está en una sección de tragos


def test_a_restaurant_with_a_single_most_ordered_dish_has_no_list(demo):
    db, _ = demo
    popular(db, 98002)
    db.execute("UPDATE menu_items SET is_popular = false WHERE item_id = 98004")
    cache.clear()
    assert PIZZA_STORE not in top_dishes(db)


def test_with_top_dishes_goes_on_the_first_dish_of_each_restaurant_without_itself(demo):
    db, _ = demo
    popular(db, 98001)  # tres populares en la pizzería
    cards = [
        {"id": MARGARITA, "entity_type": "menu_item", "store_id": PIZZA_STORE},
        {"id": PEPPERONI, "entity_type": "menu_item", "store_id": PIZZA_STORE},
        {"id": "menu-98005", "entity_type": "menu_item", "store_id": SUSHI_STORE},
    ]

    shown = with_top_dishes(db, cards)

    assert shown[0]["top_dishes"]["source"] == TOP_DISHES_SOURCE
    assert shown[0]["top_dishes"]["label"] == TOP_DISHES_LABEL
    assert ids(shown[0]["top_dishes"]["dishes"]) == [PEPPERONI, TIRAMISU]  # sin la margarita de la tarjeta
    assert "top_dishes" not in shown[1] and "top_dishes" not in shown[2]  # el mismo local, una vez; el otro no tiene
    assert all("top_dishes" not in card for card in cards)  # no modifica lo que recibe (puede ser de la caché)


def test_with_top_dishes_needs_two_besides_the_card(demo):
    db, _ = demo
    card = {"id": MARGARITA, "entity_type": "menu_item", "store_id": PIZZA_STORE}
    assert "top_dishes" not in with_top_dishes(db, [card])[0]  # solo queda el tiramisú
    other = {"id": PEPPERONI, "entity_type": "menu_item", "store_id": PIZZA_STORE}
    assert ids(with_top_dishes(db, [other])[0]["top_dishes"]["dishes"]) == [MARGARITA, TIRAMISU]


def test_top_dishes_come_from_the_catalog_cache(demo):
    db, _ = demo
    first = top_dishes(db)
    counting = CountingConnection(db)

    assert top_dishes(counting) == first
    assert not any("menu_items" in s for s in counting.statements)
    assert with_top_dishes(counting, [{"id": "cat-1", "entity_type": "catalog_item", "store_id": 9101}])
    assert not counting.statements  # sin platos no pregunta nada
    cache.clear()
    assert top_dishes(counting) == first
    assert any("is_popular" in s for s in counting.statements)


def test_search_brings_the_most_ordered_under_a_restaurant(client):
    body = client.get("/search", params={"q": "pizza"}).json()
    [group] = [g for g in body["groups"] if g["vertical"] == "restaurantes"]
    with_list = [p for p in group["products"] if "top_dishes" in p]

    assert len(with_list) == 1 and with_list[0]["store_id"] == PIZZA_STORE
    listed = with_list[0]["top_dishes"]
    assert listed["label"] == TOP_DISHES_LABEL and 2 <= len(listed["dishes"]) <= 3
    assert with_list[0]["id"] not in ids(listed["dishes"])


def test_vertical_to_try_in_restaurants_brings_the_most_ordered(client, demo):
    db, _ = demo
    popular(db, 98001)
    for vertical in ("supermercado", "conveniencia", "turbo", "chocolateria", "mall"):
        line = {"entity_type": "catalog_item", "entity_id": "91001", "unit_price": 1990}
        events.record_order(db, "u1", f"s-{vertical}", f"c-{vertical}", vertical, [line], mode="propuesta")

    body = client.post("/agent/offer", json={"moment": "vertical_por_probar", "user_id": "u1", "context": {}}).json()

    assert body["vertical"] == "restaurantes"
    pizza = [p for p in body["products"] if p["store_id"] == PIZZA_STORE]
    assert pizza and len(pizza[0]["top_dishes"]["dishes"]) == 2


def test_profile_ladder_brings_the_most_ordered_of_its_restaurant(client, demo):
    db, _ = demo
    popular(db, 98007, 98008)  # la hamburguesa y el jugo del local de sushi

    body = client.post("/agent/offer", json={"moment": "perfil", "context": {"perfil": "asiatico"}}).json()

    [step] = [s for s in body["escalera"] if s["vertical"] == "restaurantes"]
    assert step["products"][0]["store_id"] == SUSHI_STORE
    assert ids(step["products"][0]["top_dishes"]["dishes"]) == ["menu-98007", "menu-98008"]
    others = [p for s in body["escalera"] if s["vertical"] != "restaurantes" for p in s["products"]]
    assert others and all("top_dishes" not in p for p in others)

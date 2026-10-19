"""Búsqueda fuera de lugar: si la consulta nombra un concepto que el vertical no vende, ahí no se muestra nada (y la
búsqueda agrupada lo muestra donde sí lo venden). Sobre el catálogo de prueba (`seed_demo`) más los casos que marcaba
la revisión semanal (`make eval`: «La búsqueda las marca, pero se muestran productos»)."""

import pytest
from rappi_scraper.storage.search import build_search_documents

from conftest import add_dish, add_product
from rappi_ia.agent.grouped_search import search_grouped
from rappi_ia.agent.tools import search_products
from rappi_ia.concepts.pipeline import build_concepts
from rappi_ia.demo.seed import seed_demo
from rappi_ia.embeddings.base import HashEmbedder
from rappi_ia.embeddings.text_store import embed_search_documents

EXPRESS, TURBO, MALL, PASTRY = 9201, 9301, 9601, 9806  # tiendas de `seed_demo`


def _price(db, store_id: int, product_id: int, price: int) -> None:
    """En la corrida vigente de `seed_demo`: en la anterior, la tienda dejaría de tener sus otras ofertas vigentes."""
    db.execute(
        """INSERT INTO price_snapshots (run_id, store_id, sku, price, in_stock)
           SELECT max(run_id), %s, %s, %s, true FROM scrape_runs WHERE kind = 'stores'""",
        (store_id, f"sku-{product_id}", price),
    )


@pytest.fixture
def catalog(db):
    """El catálogo de prueba con los dos casos de la revisión semanal: un surtido testimonial del concepto pedido (un
    cable HDMI rotulado como televisores en Turbo, como en la base real) y una coincidencia del stemming en otro
    concepto («pañales» calza con un «panal» de pastelería). Los televisores de verdad están en el mall. Y un sándwich
    con la etiqueta de otro concepto, como los de la base real en Express."""
    seed_demo(db)
    # Turbo con más de cien productos: el cable queda bajo el 1 % del vertical (tools.TESTIMONIAL_SHARE), como en la
    # base real. En un vertical de diez productos, uno solo es surtido de verdad.
    for i in range(120):
        add_product(db, 98500 + i, f"Agua saborizada {i} (prueba)", TURBO, "Aguas saborizadas")
        _price(db, TURBO, 98500 + i, 990)
    add_product(db, 99001, "Cable HDMI 1,8 m (prueba)", TURBO, "Televisores")
    _price(db, TURBO, 99001, 2990)
    for pid, name in [
        (99002, "Televisor smart 55 pulgadas (prueba)"),
        (99003, "Televisor QLED 55 pulgadas (prueba)"),
        (99004, "Televisor LED 43 pulgadas (prueba)"),
    ]:
        add_product(db, pid, name, MALL, "Televisores")
        _price(db, MALL, pid, 299990)
    # La categoría de Rappi «Sandwiches y empanadas» va al concepto empanadas: Express no tiene sándwiches rotulados.
    add_product(db, 99005, "Sándwich de jamón y queso (prueba)", EXPRESS, "Sandwiches y empanadas")
    _price(db, EXPRESS, 99005, 2490)
    add_dish(db, 99101, "Panal de miel con crema (prueba)", PASTRY, "Postres")
    db.execute(
        """INSERT INTO menu_price_snapshots (run_id, item_id, price)
           SELECT max(run_id), 99101, 4990 FROM scrape_runs WHERE kind = 'restaurants'"""
    )
    db.commit()
    build_search_documents(db)
    build_concepts(db)
    embedder = HashEmbedder()
    embed_search_documents(db, embedder)
    return db, embedder


def test_testimonial_items_of_the_named_concept_are_not_shown(catalog):
    """«televisor 55 pulgadas» en Turbo: «sin resultado» (un solo ítem del concepto, bajo MIN_CONCEPT_ITEMS), pero se
    mostraba el cable HDMI con la etiqueta del concepto."""
    db, embedder = catalog

    outcome = search_products(db, "turbo", "televisor 55 pulgadas", None, embedder)

    assert outcome.result.query_concepts == ["tv-video"] and not outcome.result.concept_in_vertical
    assert outcome.result.unmet and outcome.products == []


def test_word_matches_of_another_concept_are_not_shown_where_the_concept_is_not_sold(catalog):
    """«pañales» en restaurantes: el stemming junta «pañales» con «panal» y la coincidencia estricta impedía «sin
    resultado»; como nada era del concepto pedido, se mostraba el postre."""
    db, embedder = catalog

    outcome = search_products(db, "restaurantes", "pañales", None, embedder)

    assert outcome.result.query_concepts == ["panales"] and outcome.result.strict_lexical_matches > 0
    assert outcome.products == []


def test_what_says_it_in_its_name_is_shown_even_with_another_concept(catalog):
    """Express no vende el concepto sándwiches, pero su sándwich (rotulado empanadas por su categoría) lo dice en el
    nombre: es lo pedido y se muestra. Lo demás que encuentra la búsqueda, no."""
    db, embedder = catalog

    outcome = search_products(db, "conveniencia", "sándwich", None, embedder)

    assert outcome.result.query_concepts == ["sandwiches"] and not outcome.result.concept_in_vertical
    assert [p.entity_id for p in outcome.products] == ["99005"]


def test_grouped_search_shows_it_where_it_is_sold_and_not_in_the_current_vertical(catalog):
    db, embedder = catalog

    tv = search_grouped(db, "televisor 55 pulgadas", embedder, current="turbo", limit=6)
    diapers = search_grouped(db, "pañales", embedder, current="restaurantes", limit=6)

    assert [g.vertical for g in tv.groups] == ["mall"] and not tv.unmet
    assert {p.concept for p in tv.groups[0].products} == {"tv-video"}
    assert "restaurantes" not in [g.vertical for g in diapers.groups]
    assert {"supermercado", "farmacia"} <= {g.vertical for g in diapers.groups}


def test_vertical_endpoint_says_there_is_nothing(catalog):
    from fastapi.testclient import TestClient

    from rappi_ia.agent.compose import TemplateComposer
    from rappi_ia.agent.rappi_agent import RappiAgent
    from rappi_ia.api import app as api
    from rappi_ia.api.services import Services

    db, embedder = catalog

    def conn_override():
        yield db

    api.app.dependency_overrides[api.get_conn] = conn_override
    api.app.dependency_overrides[api.get_services] = lambda: Services(
        RappiAgent(embedder, TemplateComposer()), embedder
    )
    try:
        body = TestClient(api.app).get("/search", params={"q": "televisor 55 pulgadas", "vertical": "turbo"}).json()
    finally:
        api.app.dependency_overrides.clear()

    assert body["products"] == [] and body["unmet"] is True


@pytest.mark.parametrize(
    ("query", "verticals", "concept"),
    [
        ("papas fritas", {"supermercado", "conveniencia", "turbo"}, "snacks-salados"),
        ("helado", {"turbo", "chocolateria"}, "helados"),
        ("café", {"supermercado", "restaurantes"}, "cafe"),
        ("cerveza", {"licores", "supermercado", "conveniencia", "turbo"}, "cerveza"),
    ],
)
def test_legit_cross_matches_stay_in_every_vertical_that_sells_them(catalog, query, verticals, concept):
    """Lo que se vende en varias verticales sigue saliendo en cada una y, en el buscador, encabeza en la de la
    pantalla."""
    db, embedder = catalog

    for vertical in verticals:
        outcome = search_products(db, vertical, query, None, embedder)
        grouped = search_grouped(db, query, embedder, current=vertical, limit=6)
        assert outcome.products and {p.concept for p in outcome.products} == {concept}, (query, vertical)
        assert grouped.groups[0].vertical == vertical, (query, vertical)

import pytest

from rappi_ia.concepts.assign import MappedName, assign_catalog_item, assign_menu_item, concept_matcher
from rappi_ia.concepts.store import read_category_map_csv
from rappi_ia.concepts.taxonomy import load_taxonomy


@pytest.fixture(scope="module")
def matcher():
    return concept_matcher(load_taxonomy())


CATEGORIES = {
    "gaseosas": MappedName("gaseosas", "llm", 0.95, "v1"),
    "otros": MappedName("platos-listos", "llm", 0.4, "v1"),
}


def test_catalog_item_prefers_confident_category(matcher):
    a = assign_catalog_item("1", "Fanta Naranja 1,5 L", "Gaseosas", CATEGORIES, matcher)
    assert (a.concept_id, a.method, a.source) == ("gaseosas", "llm", "categoria:Gaseosas")


def test_catalog_item_falls_back_to_rules_when_category_is_doubtful(matcher):
    a = assign_catalog_item("2", "Cerveza Kunstmann Torobayo 470 cc", "Otros", CATEGORIES, matcher)
    assert (a.concept_id, a.method) == ("cerveza", "regla")


def test_catalog_item_keeps_doubtful_category_if_no_rule_matches(matcher):
    a = assign_catalog_item("3", "Producto XYZ", "Otros", CATEGORIES, matcher)
    assert (a.concept_id, a.confidence) == ("platos-listos", 0.4)


def test_catalog_item_without_anything_is_unassigned(matcher):
    assert assign_catalog_item("4", "Producto XYZ", None, CATEGORIES, matcher) is None


SECTIONS = {"bebidas": MappedName("gaseosas", "llm", 0.9), "promos": MappedName("pizza", "llm", 0.3)}
CUISINES = {"italiana": MappedName("pizza", "llm", 0.9), "americana": MappedName("pizza", "llm", 0.6)}


def test_menu_item_name_wins_over_section(matcher):
    a = assign_menu_item("10", "Pizza napolitana", "Bebidas", [], SECTIONS, CUISINES, matcher)
    assert (a.concept_id, a.method) == ("pizza", "regla")


def test_menu_item_uses_section_then_cuisine(matcher):
    by_section = assign_menu_item("11", "Limonada menta jengibre", "Bebidas", ["Italiana"], SECTIONS, CUISINES, matcher)
    assert by_section.concept_id == "jugos"  # "limonada" es regla de nombre
    by_section = assign_menu_item("12", "Maracuyá sour sin alcohol", "Bebidas", [], SECTIONS, CUISINES, matcher)
    assert (by_section.concept_id, by_section.source) == ("gaseosas", "seccion:Bebidas")
    by_cuisine = assign_menu_item("13", "Especial de la casa", "Promos", ["Italiana"], SECTIONS, CUISINES, matcher)
    assert (by_cuisine.concept_id, by_cuisine.confidence) == ("pizza", 0.72)  # 0.9 × 0.8: la cocina es pista débil


def test_a_doubtful_cuisine_gives_no_concept(matcher):
    """La cocina dice qué local es, no qué es cada plato: con un mapeo dudoso (Americana → pizza) acertaba el 62 %."""
    assert assign_menu_item("14", "Especial de la casa", "Promos", ["Americana"], SECTIONS, CUISINES, matcher) is None


def test_the_most_confident_cuisine_of_the_place_wins(matcher):
    """Las cocinas llegan por orden alfabético: en un local «Asiática, Sushi», Asiática (0,85) ganaba a Sushi (0,97) y
    13.605 platos de la base real (21-10-2026; 5.933 después del kNN), casi todos rolls y piezas, quedaban como comida
    asiática."""
    cuisines = {"asiática": MappedName("asiatica", "curado", 0.85), "sushi": MappedName("sushi", "llm", 0.97)}
    a = assign_menu_item("17", "70 Piezas Mixtas", "Promociones", ["Asiática", "Sushi"], {}, cuisines, matcher)
    assert (a.concept_id, a.source) == ("sushi", "cocina:Sushi")


def test_an_ingredient_in_a_dish_name_does_not_beat_the_section(matcher):
    """«Mechada palta mayo» es un sándwich aunque diga palta; «Phad Kee Maoo Vacuno», un plato asiático."""
    sections = {"sandwiches": MappedName("sandwiches", "llm", 0.9), "wok": MappedName("asiatica", "llm", 0.9)}
    assert (
        assign_menu_item("15", "Mechada Palta Mayo", "Sandwiches", [], sections, {}, matcher).concept_id == "sandwiches"
    )
    assert assign_menu_item("16", "Phad Kee Maoo Vacuno", "Wok", [], sections, {}, matcher).concept_id == "asiatica"


DISH_SECTIONS = {
    "perros calientes": MappedName("sandwiches", "llm", 0.9),
    "bebidas": MappedName("gaseosas", "llm", 0.9),
}
DISH_CUISINES = {"pescados y mariscos": MappedName("pescados-mariscos", "llm", 0.8)}


def test_menu_item_section_wins_over_a_non_food_name_rule(matcher):
    """En un menú, «Perro», «Aros» o «Proteína» sueltos no son comida de perro, joyas ni suplementos."""
    by_section = assign_menu_item("20", "Perro Italiano XL", "Perros Calientes", [], DISH_SECTIONS, {}, matcher)
    assert (by_section.concept_id, by_section.source) == ("sandwiches", "seccion:Perros Calientes")
    seafood = ["Pescados y Mariscos"]
    by_cuisine = assign_menu_item("21", "Aros de Calamar", "Piqueos", seafood, {}, DISH_CUISINES, matcher)
    assert (by_cuisine.concept_id, by_cuisine.source) == ("pescados-mariscos", "cocina:Pescados y Mariscos")


def test_menu_item_keeps_a_non_food_name_rule_without_a_confident_mapping(matcher):
    a = assign_menu_item("22", "Perro Italiano XL", "Promos", [], DISH_SECTIONS, {}, matcher)
    assert (a.concept_id, a.method) == ("alimento-perro", "regla")


def test_menu_item_sensitive_name_rule_still_wins_over_the_section(matcher):
    """Un local que vende cigarrillos en «Bebidas»: el nombre sensible manda (no se ofrecen como gaseosa)."""
    a = assign_menu_item("23", "Cigarrillos Marlboro Rojo", "Bebidas", [], DISH_SECTIONS, {}, matcher)
    assert (a.concept_id, a.method) == ("cigarrillos", "regla")


@pytest.fixture(scope="module")
def csv_maps():
    """Los mapeos versionados en category_map.csv, con la clave en minúsculas como los carga `rappi-ia concepts`."""
    maps = {"categoria": {}, "seccion_menu": {}, "cocina": {}}
    for row in read_category_map_csv():
        maps[row["tipo"]][row["nombre"].strip().lower()] = MappedName(
            row["concept_id"], row["metodo"], float(row["confianza"])
        )
    return maps


@pytest.mark.parametrize(
    ("name", "section", "cuisines"),
    [
        ("Perro Italiano", "Perros Calientes", ["Hamburguesa"]),
        ("Perro tradicional", "Perros Calientes", []),
        ("Perro Jumbo Gigante", "PERROS CALIENTES", ["Americana"]),
        ("Perro Especial", "Perro Caliente", ["Hamburguesa"]),
        ("Perro chilango", "Perros", []),
        ("Completo", "Completos", ["Americana"]),
        ("Perro Sencillo", "Completos Venezolanos", []),
        ("Perro Venezolano Xl", "Vienesas", []),
        ("Completo Aleman", "Completos y Perros Calientes", ["Americana"]),
        ("As Italiano", "Hot Dogs", ["Pastelería y Postres"]),
        ("Italiano", "Hot Dog", []),
    ],
)
def test_hot_dog_sections_of_the_real_map_make_the_dish_a_sandwich(matcher, csv_maps, name, section, cuisines):
    """Sin la sección mapeada, un perro caliente sin esa frase en el nombre quedaba como alimento para perros o
    tomaba la cocina del local (pizza, hamburguesa, pastelería)."""
    a = assign_menu_item("24", name, section, cuisines, csv_maps["seccion_menu"], csv_maps["cocina"], matcher)
    assert (a.concept_id, a.source) == ("sandwiches", f"seccion:{section}"), a


def test_pastry_as_the_cuisine_of_the_place_does_not_label_its_dishes(matcher, csv_maps):
    """Cafeterías, juguerías y heladerías también se rotulan «Pastelería y Postres»: como cocina del local, mandaba a
    pastelería las milanesas de «Milas - El Golf» («Just Mila Xl»), té, papas fritas y batidos; en dos muestras de la
    base real (21-10-2026) acertaba unos 4 de cada 10. Sin otra pista el plato queda sin concepto (decide el kNN), y la
    sección, si nombra un plato, manda."""
    sections, cuisine_map = csv_maps["seccion_menu"], csv_maps["cocina"]
    milas = ["Desayunos", "Internacional", "Pastelería y Postres"]
    assert assign_menu_item("25", "Just Mila Xl", "+ Milanesas Xl", milas, sections, cuisine_map, matcher) is None
    pastry = ["Pastelería y Postres"]
    ice = assign_menu_item("26", "Frutilla Sin Azúcar", "Helados", pastry, sections, cuisine_map, matcher)
    assert (ice.concept_id, ice.source) == ("helados", "seccion-nombre:Helados")


TOBACCO = {"cigarrillos": MappedName("cigarrillos", "llm", 0.8, "v1")}


@pytest.mark.parametrize(
    ("name", "concept"),
    [
        ("Vookbar 30000 Strawberry Banana", "cigarrillos"),  # sin palabra que lo delate, queda donde la categoría
        ("Fume X Nicky Jam El Ganador 15000 Puff 4.5%", "vapeo"),
        ("E-liquid King Crest Don Juan Tabaco Dulce 120ml 6mg", "vapeo"),
        ("Blunt Wrap Watermelon", "accesorios-fumador"),
        ("Tabaquera De Eco Cuero Con Amarre", "accesorios-fumador"),
        ("Tabaco Ross Maracuya 45g", "cigarrillos"),
        ("Marlboro Cigarrillos Red Box 20 u", "cigarrillos"),
    ],
)
def test_the_tobacconist_category_is_split_by_name(matcher, name, concept):
    """Rappi Mall lista vapers, líquidos y papelillos en la categoría «Cigarrillos»: 738 «cigarrillos» que dejaban a
    Licores fuera de competencia («cigarros» mostraba puritos del Mall)."""
    assert assign_catalog_item("1", name, "Cigarrillos", TOBACCO, matcher).concept_id == concept


def test_tobacconist_words_mean_nothing_outside_that_category(matcher):
    a = assign_catalog_item(
        "1", "Cereal Puffs Plátano Zapallo", "Cereales", {"cereales": MappedName("cereales", "llm", 0.9)}, matcher
    )
    assert a.concept_id == "cereales"


@pytest.mark.parametrize("name", ["Macarrón Frutilla", "Papas Familiar", "Queso", "Yogurt mango s/a"])
def test_a_dish_is_not_the_raw_ingredient_its_name_mentions(matcher, name):
    """Frutas, verduras, lácteos y quesos por el nombre de un plato acertaban 1 de cada 3 (juicio del 06-10)."""
    a = assign_menu_item("30", name, "Sin mapeo", [], {}, {}, matcher)
    assert a is None or a.concept_id not in {"frutas", "verduras", "lacteos", "quesos", "fiambres", "huevos"}


@pytest.mark.parametrize(
    ("name", "concept"), [("Ceviche de Camarones", "pescados-mariscos"), ("Pollo Chiten", "pollo")]
)
def test_a_dish_named_for_its_protein_keeps_it(matcher, name, concept):
    assert assign_menu_item("31", name, "Sin mapeo", [], {}, {}, matcher).concept_id == concept


@pytest.mark.parametrize(
    ("name", "concept"),
    [("Combo pollo para 1", "pollo"), ("Combo Ceviche Mixto", "pescados-mariscos")],
)
def test_a_protein_in_the_dish_name_beats_a_generic_section(matcher, name, concept):
    """La sección «Combos» estaba mapeada a sushi: «Combo pollo para 1» quedaba como sushi y no salía al pedir pollo."""
    combos = {"combos": MappedName("sushi", "llm", 0.85)}
    assert assign_menu_item("40", name, "Combos", [], combos, {}, matcher).concept_id == concept


@pytest.mark.parametrize(("section", "concept"), [("Empanadas de Horno", "empanadas"), ("Pizzas Familiares", "pizza")])
def test_an_unmapped_section_that_names_a_dish_gives_the_concept(matcher, section, concept):
    a = assign_menu_item("41", "La especial de la casa", section, [], {}, {}, matcher)
    assert (a.concept_id, a.source) == (concept, f"seccion-nombre:{section}")


def test_an_unmapped_section_that_names_an_ingredient_gives_nothing(matcher):
    assert assign_menu_item("42", "La especial de la casa", "Quesos", [], {}, {}, matcher) is None


def test_the_real_combos_section_is_no_longer_sushi(csv_maps):
    assert "combos" not in csv_maps["seccion_menu"] or csv_maps["seccion_menu"]["combos"].concept_id != "sushi"


# Categorías reales de los productos asiáticos (base real, 14-10-2026): Rappi los pone junto a lo genérico.
ASIAN_CATEGORIES = {
    "otras salsas": MappedName("salsas", "llm", 0.95),
    "arroz": MappedName("arroz-legumbres", "llm", 0.95),
    "galletas": MappedName("galletas", "llm", 0.95),
    "sopas y cremas": MappedName("sopas", "llm", 0.95),
    "helados": MappedName("helados", "llm", 0.95),
    "tés": MappedName("te", "llm", 0.95),
    "chocolates": MappedName("chocolates", "llm", 0.97),
    "shampoo": MappedName("cuidado-cabello", "llm", 0.95),
    "vajilla y cubertería": MappedName("cocina-menaje", "llm", 0.9),
    "otros licores": MappedName("licores", "llm", 0.9),
    "frutas": MappedName("frutas", "llm", 0.9),
    "sushi": MappedName("sushi", "llm", 0.95),
    "verduras": MappedName("verduras", "llm", 0.9),
    "otros": MappedName("platos-listos", "llm", 0.4),  # dudoso: bajo MIN_MAP_CONFIDENCE
}


@pytest.mark.parametrize(
    ("name", "category", "concept"),
    [
        ("Kikkoman Salsa de Soya", "Otras salsas", "despensa-asiatica"),
        ("Tucapel Arroz para Sushi", "Arroz", "despensa-asiatica"),
        ("Pepero Crunchy", "Galletas", "snacks-asiaticos"),
        ("Maruchan Sopa Instantánea Sabor a Pollo", "Sopas y cremas", "snacks-asiaticos"),
        ("Kai Mochi Helado Mochi Mango", "Helados", "snacks-asiaticos"),
        ("Bebida Bubble Tea, Taro", "Tés", "bebidas-asiaticas"),
        ("Tostani Arroz Sushi", "Sushi", "despensa-asiatica"),  # una categoría de comida preparada
        ("Alga Nori Yumart 10 Uds", "Verduras", "despensa-asiatica"),  # una de frescos
        ("Kikkoman Salsa de Soya", "Importados", "despensa-asiatica"),  # una categoría sin mapeo
        ("Pepero Crunchy", "Otros", "snacks-asiaticos"),  # una con mapeo dudoso
    ],
)
def test_an_asian_name_refines_a_generic_food_category(matcher, name, category, concept):
    """«Kikkoman Salsa de Soya» está en «Otras salsas» y «Pepero» en «Galletas»: sin esto, la despensa, los snacks y
    las bebidas asiáticas quedaban casi vacíos (la categoría manda sobre el nombre)."""
    a = assign_catalog_item("50", name, category, ASIAN_CATEGORIES, matcher)
    assert (a.concept_id, a.method) == (concept, "regla"), a


@pytest.mark.parametrize(
    ("name", "category", "concept"),
    [
        ("Salsa de Tomate Pomarola", "Otras salsas", "salsas"),  # lo demás sigue en su categoría
        ("Lindor Matcha", "Tés", "te"),  # su categoría real: el matcha a secas sigue siendo té
        ("Shampoo Líquido Wasabi Shan Kui Lush", "Shampoo", "cuidado-cabello"),
        ("Mug Matcha Travel Verde Adagio Teas", "Vajilla y Cubertería", "cocina-menaje"),  # no es comida ni bebida
        ("Umeshu Matcha 500 ml", "Otros licores", "licores"),  # el alcohol nunca pasa a un concepto que se ofrece
        ("Sushi Box con Salsa Soya y Wasabi", "Sushi", "sushi"),  # un plato preparado no es despensa
        ("Panko Roll Salmón", "Sushi", "sushi"),
    ],
)
def test_an_asian_name_never_takes_a_product_out_of_other_groups_or_alcohol(matcher, name, category, concept):
    assert assign_catalog_item("51", name, category, ASIAN_CATEGORIES, matcher).concept_id == concept


def test_only_a_name_that_refined_a_food_category_is_marked_for_the_neighbors(matcher):
    """El kNN respeta la regla solo si afinó una categoría de comida (`refines`, que no se guarda en la base)."""
    refined = assign_catalog_item("53", "Kikkoman Salsa de Soya", "Otras salsas", ASIAN_CATEGORIES, matcher)
    plain = assign_catalog_item("54", "Kikkoman Salsa de Soya", "Importados", ASIAN_CATEGORIES, matcher)
    assert (refined.refines, plain.refines) == ("salsas", None)


def test_a_mis_categorised_alcohol_with_an_asian_word_is_not_asian_and_is_never_offered(matcher):
    """En la base real «Soju Uva Verde 13.0» está en «Frutas», sin marca de alcohol ni +18. Un soju con nombre asiático
    no pasa a bebidas asiáticas (`avoid`); queda en su categoría, y la guardia de ofertas lo bloquea por el nombre."""
    from rappi_ia.offers.guards import alcohol_in_name

    for name in ("Soju Bubble Tea 360 ml", "Soju Uva Verde 13.0"):
        assert assign_catalog_item("52", name, "Frutas", ASIAN_CATEGORIES, matcher).concept_id == "frutas"
        assert alcohol_in_name("catalog_item", name)


@pytest.mark.parametrize(
    ("name", "section", "concept"),
    [
        ("55 Tori Panko", "Cuarto Caliente", "sushi"),  # un roll en panko o con nori sigue siendo sushi
        ("Alaska Especial con Wakame", "Rolls con Topping", "sushi"),
        ("Salsa Soya", "Sin mapeo", "salsas"),  # el agregado de soya de un local, como antes
        ("Mochi de Maracuyá", "Postres", "postres"),  # el postre de un local no deja de serlo
    ],
)
def test_asian_specialty_concepts_do_not_count_in_menus(matcher, name, section, concept):
    """Son productos de tienda (ninguno se pide hecho): en un menú, «panko», «nori» o «mochi» sacaban de sushi y de
    postres a ~1.000 platos de la base real, que dejaban de salir en restaurantes."""
    sections = {
        "cuarto caliente": MappedName("sushi", "llm", 0.9),
        "rolls con topping": MappedName("sushi", "llm", 0.9),
    }
    sections["postres"] = MappedName("postres", "llm", 0.9)
    assert assign_menu_item("60", name, section, [], sections, {}, matcher).concept_id == concept


# Productos mal asignados en la base real del 14-10-2026 (juicio de precisión del 17-10-2026, muestras fijas).
STORE_CATEGORIES = {
    "otras salsas": MappedName("salsas", "llm", 0.88),
    "sopas y cremas": MappedName("sopas", "llm", 0.95),
    "energizantes": MappedName("energizantes", "llm", 0.95),
    "jugos": MappedName("jugos", "llm", 0.98),
    "té listo": MappedName("te", "llm", 0.9),
    "tés": MappedName("te", "llm", 0.95),
    "café": MappedName("cafe", "llm", 0.98),
    "hielo": MappedName("hielo", "llm", 0.95),
    "otras aguas": MappedName("gaseosas", "llm", 0.8),
    "gaseosas": MappedName("gaseosas", "llm", 0.98),
    "agua saborizada": MappedName("agua", "llm", 0.9),
    "pescados": MappedName("pescados-mariscos", "llm", 0.95),
    "mermeladas": MappedName("untables-dulces", "llm", 0.95),
    "frutos secos y semillas": MappedName("frutos-secos", "llm", 0.9),
    "postres refrigerados": MappedName("postres", "llm", 0.9),
    "cereales": MappedName("cereales", "llm", 0.95),
    "otros accesorios de belleza": MappedName("maquillaje", "llm", 0.8),
    "gomitas y caramelos": MappedName("golosinas", "llm", 0.85),
    "herramientas": MappedName("ferreteria", "llm", 0.9),
    "cartones": MappedName("utiles", "llm", 0.9),
    "paños multiusos": MappedName("limpieza", "llm", 0.9),
    "quesos maduros": MappedName("quesos", "llm", 0.95),
    "juguetes didácticos": MappedName("juguetes-infantiles", "llm", 0.95),
    "pañales y forros para mascotas": MappedName("accesorios-mascota", "curado", 0.85),
    "productos naturales": MappedName("vitaminas", "llm", 0.5),  # dudoso: bajo MIN_MAP_CONFIDENCE
}


@pytest.mark.parametrize(
    ("name", "category"),
    [
        ("Ramen Muy Picante Buldak Original", "Otras salsas"),
        ("Ramen Muy Picante Carbo Buldak", "Sopas y cremas"),
        ("Ramen Muy Picante Buldak Rosé, Servir", "Sopas y cremas"),
    ],
)
def test_a_buldak_ramen_is_instant_ramen_not_a_sauce(matcher, name, category):
    """«ramen» (comida asiática, de restaurante) calzaba antes que «buldak» y no afinaba: el ramen quedaba en salsas."""
    a = assign_catalog_item("70", name, category, STORE_CATEGORIES, matcher)
    assert (a.concept_id, a.method, a.source) == ("snacks-asiaticos", "regla", "nombre:buldak"), a
    assert a.refines == STORE_CATEGORIES[category.lower()].concept_id


@pytest.mark.parametrize(
    ("name", "concept"), [("Salsa Gochujang 500g", "despensa-asiatica"), ("Salsa Wasabi", "despensa-asiatica")]
)
def test_an_asian_word_refines_even_after_a_generic_one(matcher, name, concept):
    """«Salsa» calza primero (salsas); «gochujang» o «wasabi» dicen qué salsa es."""
    assert assign_catalog_item("71", name, "Otras salsas", STORE_CATEGORIES, matcher).concept_id == concept


@pytest.mark.parametrize("name", ["Salsa Wasabi Sabor Whisky", "Soju Salsa Gochujang"])
def test_a_name_that_also_says_alcohol_is_never_refined_into_an_offered_concept(matcher, name):
    """Basta una regla de alcohol (o sensible, o de bebé) en cualquier parte del nombre: la categoría queda como está y
    la guardia de ofertas lo bloquea por el nombre."""
    from rappi_ia.offers.guards import alcohol_in_name

    a = assign_catalog_item("80", name, "Otras salsas", STORE_CATEGORIES, matcher)
    assert (a.concept_id, a.refines) == ("salsas", None), a
    assert alcohol_in_name("catalog_item", name)


def test_a_sensitive_name_is_never_refined_into_an_asian_concept(matcher):
    categories = {"agua saborizada": MappedName("agua", "llm", 0.85)}
    a = assign_catalog_item("72", "Lubricante Íntimo Sabor Té Matcha", "Agua saborizada", categories, matcher)
    assert a.concept_id == "bienestar-sexual", a


@pytest.mark.parametrize(
    ("name", "category", "concept"),
    [
        ("Mistral Ice Energy Lata 355", "Energizantes", "pisco"),
        ("Gin Santos + 2 Red Bull Yellow + Sprite Zero 1.5lts + Hielo 2kg", "Energizantes", "gin"),
        ("Johnnie Red 700 Cc Con Bebida 1.5lt", "Jugos", "whisky"),
        ("Campanario Mango Sour", "Jugos", "pisco"),
        ("La Pizca Cóctel Natural Martini Manzana", "Jugos", "cocteles"),
        ("Bauza 35º 750cc + Bebida 1.5lt", "Jugos", "licores"),
        ("Republicano Manzana 35° 750ml", "Jugos", "licores"),
        ("Coc Vin Export Selecto Tropical 8°", "Té listo", "licores"),
        ("3R Pisco 35 + Coca-Cola Gaseosa + Hielo Líquidos", "Gaseosas", "pisco"),
        ("Promo Tres Erres Transparente 1l + Coca Normal 3l + Hielo 1kg", "Hielo", "pisco"),
        ("Makgeolli Milkis Durazno 6°", "Gaseosas", "licores"),  # el alcohol antes que lo asiático («milkis»)
    ],
)
def test_a_drink_with_alcohol_leaves_a_soft_drink_category_and_is_never_offered(matcher, name, category, concept):
    """Sin marca de alcohol de la tienda y sin palabra genérica de trago, el agente los ofrecía como bebida o jugo."""
    from rappi_ia.offers.guards import is_offerable

    a = assign_catalog_item("73", name, category, STORE_CATEGORIES, matcher)
    assert (a.concept_id, a.method) == (concept, "regla"), a
    assert not is_offerable(load_taxonomy().concepts[a.concept_id])


@pytest.mark.parametrize(
    ("name", "category", "concept"),
    [
        ("Fentimans Cerveza de Jengibre", "Otras aguas", "gaseosas"),  # la ginger beer es una gaseosa
        ("Corteza Jesuita Cerveza Ginger Beer Zero", "Otras aguas", "gaseosas"),
        ("Score Bebida Energética Mojito", "Energizantes", "energizantes"),  # Score es una marca de energéticas
        ("Café Amaretto Almond (50g) Beanies", "Café", "cafe"),  # en café y té, un trago es un sabor
        ("Dosha. Caramel & Whisky", "Tés", "te"),
        ("Coca-Cola Sin Azúcar 1,5 L", "Gaseosas", "gaseosas"),
        ("Agua Mineral 0° Sin Gas", "Agua saborizada", "agua"),
        ("Filete De Merluza Austral", "Pescados", "pescados-mariscos"),  # fuera de las bebidas, la categoría manda
        ("Mermelada De Cebolla Al Vino Tinto", "Mermeladas", "untables-dulces"),
    ],
)
def test_a_soft_drink_or_a_food_that_names_a_drink_keeps_its_category(matcher, name, category, concept):
    assert assign_catalog_item("74", name, category, STORE_CATEGORIES, matcher).concept_id == concept


@pytest.mark.parametrize(
    ("name", "category", "concept"),
    [
        ("Philips Mamadera Natural Response 125 mL", "Frutos secos y semillas", "articulos-bebe"),
        ("Philips Tetina Natural Flujo Variable", "Otros accesorios de belleza", "articulos-bebe"),
        ("Nestlé Compota Sabor a Pera", "Postres refrigerados", "alimentacion-bebe"),
        ("Nestum Cereal Infantil de Avena y Arroz", "Cereales", "alimentacion-bebe"),
    ],
)
def test_a_baby_name_wins_over_a_common_category(matcher, name, category, concept):
    """Guardia simétrica, como la de los sensibles: una mamadera en «Frutos secos y semillas» se ofrecía como snack."""
    from rappi_ia.offers.guards import is_offerable

    a = assign_catalog_item("75", name, category, STORE_CATEGORIES, matcher)
    assert (a.concept_id, a.method) == (concept, "regla"), a
    assert not is_offerable(load_taxonomy().concepts[a.concept_id])


@pytest.mark.parametrize(
    ("name", "category", "concept"),
    [
        ("Bon Bon Bum Chupete Sabor a Fresa", "Gomitas y caramelos", "golosinas"),  # un chupete con sabor es un dulce
        ("Yogueta Chupete Surtida", "Gomitas y caramelos", "golosinas"),
        ("Cuña Niveladora Para Cerámicas 100unds", "Herramientas", "ferreteria"),  # sin ñ, «cuña» es «cuna»
        ("Ferrari Queso Cuña Pecorino Romano", "Quesos maduros", "quesos"),
        ("Carton Panal 10Mm 77X110Cm", "Cartones", "utiles"),  # sin ñ, «pañal» es «panal»
        ("Virutex Toallitas Húmedas Desinfectantes Multiuso Aroma Limón", "Paños multiusos", "limpieza"),
        ("Dog It Pañal Desechable para Perro Talla M", "Pañales y forros para Mascotas", "accesorios-mascota"),
        ("Mordedor Para Bebe 2 Piezas", "Juguetes didácticos", "juguetes-infantiles"),  # juguetes: manda la categoría
    ],
)
def test_the_baby_guard_does_not_take_look_alikes(matcher, name, category, concept):
    assert assign_catalog_item("76", name, category, STORE_CATEGORIES, matcher).concept_id == concept


@pytest.mark.parametrize(
    ("name", "concept"),
    [
        ("Compota Casera de Manzana", "postres"),
        ("Compota de Ciruelas", "postres"),
        ("Compota Para Adultos Sabor Pera", "postres"),
        ("Chupete Avent Ultra Air 6-18m Surtido", "articulos-bebe"),  # «surtido» suelto no lo saca de bebé
    ],
)
def test_an_adult_compote_is_dessert_and_a_real_baby_item_keeps_the_guard(matcher, name, concept):
    assert assign_catalog_item("81", name, "Postres refrigerados", STORE_CATEGORIES, matcher).concept_id == concept


@pytest.mark.parametrize(
    ("name", "strength"),
    [
        ("Bauza 35º 750cc + Bebida 1.5lt", "35º"),
        ("Mistral Ice Energy 7°G 355 cc", "7°"),
        ("Cóctel Mistral Ice Low Blend 2.5° Botella 275cc", "2.5°"),
        ("Coc Vin Export Selecto Tropical 8°", "8°"),
        ("Hielo Nórdico Conservar a -18°", None),
        ("Té Helado Servir a 4°C", None),
        ("Té Helado Servir a 4 °C", None),
        ("Kombucha 4° Celsius", None),
        ("Jugo de Naranja 12° Brix", None),
        ("Libro de Cócteles 2° Edición", None),
        ("Cerveza Sin Alcohol Heineken 0.0", None),
        ("Espumante Sin Alcohol 5°", None),
        ("Cerveza Royal 0,0 4.5°", None),
        ("Spaghetti N°5", None),
        ("Agua Mineral 0°", None),
    ],
)
def test_alcohol_strength_in_a_name(name, strength):
    from rappi_ia.concepts.assign import alcohol_strength

    assert alcohol_strength(name) == strength


@pytest.mark.parametrize(
    "name",
    [
        "Oregano Oil 60 Softgels Marca Laboratorio Fnl",
        "Cola De Pavo 500mg 120 Caps Swanson",
        "Vinagre De Manzana 60 Capsulas Marca Laboratorio Fnl",
        "Propoleo Spray Miel Jengibre",
        "Minigummies Calm 30 Gomitas",
        "FNL Cetona De Frambuesa 300Mg 60 Capsulas",
        "Carbon Activado 500mg 60 Cápsulas - Fnl",  # «activado»: no es carbón para la parrilla
        "Bach Flores Rescue Gotas",
    ],
)
def test_a_supplement_named_for_a_food_stays_a_supplement(matcher, name):
    """En «Productos naturales» (vitaminas, mapeo dudoso) la regla del nombre ganaba: orégano, pavo, miel o frambuesa
    pasaban a condimentos, pollo, untables o frutas, conceptos que el agente ofrece."""
    a = assign_catalog_item("77", name, "Productos naturales", STORE_CATEGORIES, matcher)
    assert (a.concept_id, a.method) == ("vitaminas", "llm"), a


def test_a_doubtful_supplement_category_still_gives_way_to_a_name_that_is_not_food(matcher):
    """Las velas y los difusores de «Productos naturales» siguen siendo decoración."""
    a = assign_catalog_item(
        "78", "Mood Vela Aromaterapia Bosque Nativo", "Productos naturales", STORE_CATEGORIES, matcher
    )
    assert (a.concept_id, a.method) == ("decoracion", "regla")


@pytest.mark.parametrize(
    ("name", "category", "concept"),
    [
        ("Wool - Mostaza 100 Gr", "Hilos", "manualidades"),
        ("Warm Mix - Verde Pistacho 100 Gr", "Hilos", "manualidades"),
        ("Skinny - Sandía 0425 100 Gr", "Hilos", "manualidades"),
        ("Alfombra de Baño Boro Rectangular Poliéster U Casaideas", "Tapetes y Alfombras", "textil-hogar"),
    ],
)
def test_the_real_map_keeps_yarn_and_rugs_out_of_food_and_baby(matcher, csv_maps, name, category, concept):
    """«Hilos» tenía un mapeo dudoso (útiles, 0,55) y el color del ovillo («Mostaza», «Verde Pistacho») lo mandaba a
    salsas o frutos secos; «Tapetes y Alfombras» (artículos de bebé) son sobre todo alfombras de baño."""
    assert assign_catalog_item("79", name, category, csv_maps["categoria"], matcher).concept_id == concept

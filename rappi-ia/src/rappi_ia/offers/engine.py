"""El motor de ofertas del agente: qué propone en cada momento de la app, siempre desde la base (productos reales,
con su precio vigente) y pasando por las guardias de `offers/guards.py`.

Momentos (`POST /agent/offer`): `plan` (el kit de una ocasión que la persona eligió), `carrito` (un complemento de
otra tienda), `checkout`, `proximo_pedido`, `sin_resultado` (dónde sí está lo que buscó), `vertical_por_probar` (la
vertical del grupo que completa la combinación de verticales que más retiene, según el motor; sin ese paso, la vertical
donde la persona aún no ha pedido y más le gusta, y sin historia, la primera) y `perfil` (la escalera de
un perfil de gusto, `offers/profiles.py`, con su forma propia: `ProfileOffer`). Si no hay una buena oferta, no hay
oferta (`None`: 204): el agente no dice nada.

Los textos son plantillas en español. Una oferta nunca nombra un concepto que el agente no puede proponer (el origen
de un complemento puede ser cerveza o pañales, y el texto no lo repite).

Cada oferta dice por qué (`Offer.reason`): las claves de siempre (`occasion`, `concept`, `from_concept`), el `text`
(«Porque…») y la `basis`: las señales del contexto que la motivan (`kind` carrito, pedido, busqueda, ocasion,
sin_pedidos o perfil, este último en el momento `perfil` sin persona; e `id`; `source` «contexto» y sin `score`, que es
de las señales de una persona en `offers/personal.py`). Lo que el agente no propone no entra a la base. Cuando la oferta
se ordena por lo que le gusta a la persona (`vertical_por_probar` y las ocasiones de la Home), la `basis` son sus
señales (`kind` concepto, con `score` y `source`) de los conceptos que más aportan. Cuando `vertical_por_probar` sigue
el paso del motor, la `basis` parte con `combinacion` («<actual>→<objetivo>», `source` «rappi»: la tabla de Rappi) y
suma de dónde salen los productos: `compra_cruzada` («<A>→<B>@<vertical>») o `lo_mas_pedido` («<vertical>»), con
`source` «poblacion:<fuente>»; el texto habla de la persona, nunca de cifras de retención. Un complemento cuyo primer
producto es de una marca que la persona compra lo dice en el `text` y suma esa señal (`marca`, con los pedidos como
`score`). En el momento `perfil` de una persona, el porqué es el «por qué» de su perfil y la `basis`, la suya
(`offers/profiles.py`):
la evidencia de sus segmentos (`source` «segmento:<id>», el peso de su nivel como `score`) y lo que pidió y buscó
(`source` «pedidos» o «busquedas», cuántas veces como `score`).
"""

from dataclasses import dataclass, field

from psycopg import Connection
from rappi_scraper.storage.search import MIN_PRICE

from .. import config
from ..agent.grouped_search import SCREEN_VERTICALS
from ..agent.tools import VERTICAL_LABELS, Product, search_products, suggest_complement
from ..agent.verticals import contending_verticals, ranked_verticals, typical_verticals
from ..catalog.deals import deals
from ..catalog.stores import BIGINT_MAX, _product, product_detail
from ..concepts.taxonomy import Concept, Service, load_taxonomy
from ..embeddings.base import MemoizedQueryEmbedder, TextEmbedder
from ..motor.combos import combo_key, load_combos
from ..motor.predict import next_verticals, target_step
from ..motor.recommend import CrossPick, cross_picks, latest_lambda
from ..retrieval.hybrid import _concepts_of, detect_concepts
from ..text import contract_articles, normalize, tokens
from .guards import (
    alcohol_in_name,
    alcohol_section,
    baby_in_name,
    is_offerable,
    is_plannable,
    offerable_vertical,
    plannable_occasion,
    plannable_vertical,
    unofferable_subverticals,
)
from .personal import Interests, Signal, bought_brands, user_interests
from .profiles import (
    ActiveProfile,
    Destination,
    Profile,
    active_profiles,
    ladder,
    load_destinations,
    load_profiles,
    ordered_restaurants,
    person_city,
)

KIT_SIZE = 4  # productos del kit de una ocasión
# El concepto ya está elegido: la búsqueda léxica de su nombre (miles de platos «pizza») costaba ~140 ms por búsqueda en
# restaurantes y la vectorial ~11 ms. Se prueba primero la vectorial y, si no trae nada (sin modelo, o documentos sin
# embeddings), la de siempre.
KIT_VERTICALS = 3  # verticales que se prueban por concepto del kit (las más típicas)
KIT_CANDIDATES = 6  # productos que se piden por concepto y vertical: se saltan los de nombre pelado
ARTICLES = frozenset({"el", "la", "los", "las", "un", "una", "unos", "unas"})  # normalizados
SHOWN_PRODUCTS = 3  # productos de una oferta que no es un kit
FALLBACK_VERTICALS = 3  # verticales que se prueban para decir dónde sí está lo que no se encontró
# Ofertas que se piden por vertical antes de quitar las que el agente no propone y de poner primero las típicas de la
# vertical. Con 12, en la base real las más rebajadas del súper eran mantas y accesorios de auto, y ninguna típica; con
# 60 había 4 típicas y con 200, 28. El costo de `deals()` no depende del tope.
DEAL_POOL = 200
# Las verticales donde se compra comida (el súper, Express y Turbo) y los grupos de la taxonomía que se comen o se
# beben: en ellas, una oferta de otro grupo (cera para auto, papel higiénico) va después de la comida.
FOOD_VERTICALS = ("supermercado", "conveniencia", "turbo")
FOOD_GROUPS = ("bebidas", "snacks", "dulces", "despensa", "frescos", "comida")

# El orden de la Home: lo que ya muestra hoy (la app tiene «Película» para panorama); después, el resto de la taxonomía.
HOME_OCCASIONS = ("once", "carrete", "asado", "panorama", "regalo")

# El orden en que se propone una vertical por probar cuando nada le gusta más a la persona (Viajes no tiene catálogo).
TO_TRY_ORDER = (
    "supermercado",
    "conveniencia",
    "turbo",
    "licores",
    "chocolateria",
    "restaurantes",
    "farmacia",
    "mall",
)

# Plantillas. {origen} es el concepto de lo que ya lleva (solo si el agente puede proponerlo), {destino} el que se
# ofrece.
PLAN_TEXT = "Tu kit «{occasion}»: {concepts}, de {verticals}."  # el nombre de la ocasión va tal cual, sin gramática
PLAN_ACTION = "Más ideas"
CART_TEXT = "Para acompañar {origen}: {destino}, en {vertical}."
CART_TEXT_ANONYMOUS = "Para completar tu pedido: {destino}, en {vertical}."
CHECKOUT_TEXT = "Antes de pagar: {destino}, en {vertical}. Combina con lo que llevas."
NEXT_ORDER_TEXT = "Para tu próximo pedido: {destino}, en {vertical}. Combina con lo que pediste."
NO_RESULT_TEXT = "No encontré «{query}», pero {destino} sí hay en {vertical}."
TO_TRY_TEXT = "Aún no pides en {vertical}: mira {what}."
TO_TRY_DEALS = "estas ofertas"
TO_TRY_DISHES = "lo que más piden"
# Por qué se ofrece (`reason.text`). {emoji} {name} es el concepto de lo que ya hay en el carrito o en el pedido.
REASON_PLAN = "Porque elegiste «{occasion}»."
REASON_CART = "Porque llevas {emoji} {name}."
REASON_CART_ANONYMOUS = "Porque combina con lo que llevas."
REASON_NEXT = "Porque pediste {emoji} {name}."
REASON_NEXT_ANONYMOUS = "Porque combina con lo que pediste."
REASON_NO_RESULT = "Porque buscaste «{query}» y aquí sí hay."
REASON_TO_TRY = "Porque aún no pides en {vertical}."
# La vertical por probar del paso del motor: con compra cruzada, {origen} es el concepto de la persona que dispara la
# regla y {destino} el que se ofrece; con lo más pedido de la población, la vertical.
TO_TRY_CROSS_TEXT = "Para acompañar tu {origen}: {destino} en {vertical}."
REASON_TO_TRY_CROSS = "Porque pides {emoji} {name} y quienes lo piden suelen sumar {destino} en {vertical}."
TO_TRY_TOP_TEXT = "Lo más pedido en {vertical}."
REASON_TO_TRY_TOP = "Porque aún no pides en {vertical}: esto es lo que más se pide."
# Una vertical del paso que la persona ya probó (pidió ahí hace más de un mes: no está en su combinación de 30 días).
BACK_TEXT = "Vuelve a {vertical}: mira {what}."
BACK_TOP = "lo más pedido"
REASON_BACK = "Porque hace más de un mes que no pides en {vertical}."
SEE_ACTION = "Ver {destino}"
OPEN_ACTION = "Abrir {vertical}"
REASON_LIKES_VERTICAL = "Porque te gusta {emoji} {name}, y en {vertical} hay más."
REASON_LIKES_OCCASION = "Porque te gusta {emoji} {name}."
REASON_BRAND = " Es {brand}, la marca que compras."  # se suma al porqué de un complemento de su marca
# El momento `perfil`: «Como te gusta» y el `gusto` del perfil (offers/perfiles.toml); sin él, el nombre del perfil.
PROFILE_TEXT = "Como te gusta {likes}, mira esto en otras verticales."
PROFILE_TEXT_NAMED = "Para tu perfil {emoji} {name}: mira esto en otras verticales."
REASON_PROFILE = "Porque elegiste «{name}»."  # sin persona, o con un perfil que no es suyo
TRIP_SERVICE = "rappitravel"  # el servicio de la taxonomía al que lleva el viaje (sin catálogo)
TRIP_LABEL = "Idea para {service}"
BASIS_CONCEPTS = 3  # conceptos que más aportan, de los que la `basis` de una oferta lleva las señales


class OfferError(ValueError):
    """La petición no tiene sentido (una ocasión o un perfil que no existe, o una ocasión que el agente no arma): un
    422, no un «sin oferta»."""


@dataclass
class Offer:
    moment: str
    text: str
    products: list[dict]  # `Product.to_dict()`
    vertical: str | None  # en el kit, la de su primer producto; cada producto trae la suya
    reason: dict = field(default_factory=dict)  # concept, from_concept u occasion, más text y basis
    actions: list[dict] = field(default_factory=list)  # label y, según el caso, route (pantalla) o query (búsqueda)

    def to_dict(self) -> dict:
        return {
            "moment": self.moment,
            "text": self.text,
            "products": self.products,
            "vertical": self.vertical,
            "prototype_vertical": SCREEN_VERTICALS.get(self.vertical),
            "reason": self.reason,
            "actions": self.actions,
        }


@dataclass
class ProfileOffer:
    """La oferta del momento `perfil`: la escalera de un perfil, de a un peldaño, y su viaje (una idea para
    RappiTravel)."""

    text: str
    profile: dict  # id, nombre y emoji; con persona, además su nivel y su «por qué»
    steps: list[dict]  # `LadderStep.to_dict()`
    trip: dict | None
    reason: dict
    actions: list[dict]

    def to_dict(self) -> dict:
        return {
            "moment": "perfil",
            "text": self.text,
            "perfil": self.profile,
            "escalera": self.steps,
            "viaje": self.trip,
            "reason": self.reason,
            "actions": self.actions,
        }


def home_occasions(conn: Connection, interests: Interests) -> list[dict]:
    """Las ocasiones que el agente arma como kit (guagua y enfermo no). Primero las que suman puntaje con lo que le
    gusta a la persona (la suma de sus conceptos ofrecibles), de más a menos y con su `reason`; el resto, en el orden de
    la Home (`HOME_OCCASIONS` y después la taxonomía), que también desempata."""
    occasions = load_taxonomy().occasions
    ids = [i for i in HOME_OCCASIONS if i in occasions] + [i for i in occasions if i not in HOME_OCCASIONS]
    home = [
        {"id": o.id, "name": o.name, "emoji": o.emoji} for o in (occasions[i] for i in ids) if plannable_occasion(o)
    ]
    scores: dict[str, float] = {}
    for item in home:
        contributions = {c: interests.concepts[c] for c in occasions[item["id"]].concepts if c in interests.concepts}
        scores[item["id"]] = sum(contributions.values())
        if contributions:
            item["reason"] = _likes_reason(REASON_LIKES_OCCASION, contributions, interests)
    return sorted(home, key=lambda o: -scores[o["id"]])  # estable: puntaje 0 y empates siguen el orden de la Home


def _likes_reason(template: str, contributions: dict[str, float], interests: Interests, **format_args: str) -> dict:
    """«Porque te gusta…»: el concepto que más aporta da el texto y la `basis`, las señales de los que más aportan."""
    top = sorted(contributions, key=lambda c: (-contributions[c], c))[:BASIS_CONCEPTS]
    concept = load_taxonomy().concepts[top[0]]
    text = template.format(emoji=concept.emoji, name=concept.name.lower(), **format_args)
    return _reason(text, [s.to_dict() for c in top for s in interests.basis[c]])


def make_offer(
    conn: Connection, embedder: TextEmbedder | None, moment: str, context: dict, user_id: str | None = None
) -> Offer | ProfileOffer | None:
    """La oferta de un momento, o None si no hay una buena. Con `user_id` de alguien del prototipo, los momentos que
    personalizan se ordenan por lo que le gusta (`vertical_por_probar`; sus intereses se calculan una sola vez),
    prefieren las marcas que compra (el complemento de `carrito`, `checkout` y `proximo_pedido`) o parten de sus
    perfiles de gusto (`perfil`)."""
    if moment == "plan":
        return plan(conn, embedder, context["occasion"])
    if moment == "carrito":
        return complement(conn, embedder, "carrito", [context["product"]], bought_brands(conn, user_id))
    if moment == "checkout":
        return complement(conn, embedder, "checkout", context["cart"], bought_brands(conn, user_id))
    if moment == "proximo_pedido":
        return complement(conn, embedder, "proximo_pedido", context["items"], bought_brands(conn, user_id))
    if moment == "sin_resultado":
        return where_is_it(conn, embedder, context["query"])
    if moment == "vertical_por_probar":
        return vertical_to_try(conn, embedder, tried_verticals(conn, user_id), user_interests(conn, user_id), user_id)
    if moment == "perfil":
        return profile_offer(conn, embedder, context.get("perfil"), user_id)
    raise OfferError(f"Momento desconocido: {moment}")


# ── plan ─────────────────────────────────────────────────────────────────────
def plan(conn: Connection, embedder: TextEmbedder | None, occasion_id: str) -> Offer | None:
    """El kit de una ocasión: un producto por concepto (hasta KIT_SIZE), de la vertical donde es típico y repartido
    entre verticales, salvo que la ocasión tenga una fija (`vertical` en la taxonomía: «Hambre ya» es pedir comida
    lista): entonces sale de ahí. Es lo único que el agente arma con alcohol, con su marca +18, porque la persona eligió
    la ocasión; nunca con lo sensible, farmacia, bebé ni salud."""
    taxonomy = load_taxonomy()
    occasion = taxonomy.occasions.get(occasion_id)
    if occasion is None or not plannable_occasion(occasion):
        raise OfferError(f"{config.AGENT_NAME} no arma un kit de «{occasion_id}»")
    concepts = [c for c in (taxonomy.concepts[i] for i in occasion.concepts) if is_plannable(c)]
    if embedder is not None:  # cada concepto se embebe una vez, en un solo lote, aunque se busque en varias verticales
        embedder = MemoizedQueryEmbedder(embedder)
        embedder.embed_queries([c.name for c in concepts])
    candidates = {c.id: _kit_verticals(conn, c, occasion.vertical) for c in concepts}
    found: dict[tuple[str, str], Product | None] = {}

    def pick(concept: Concept, avoid: set[str]) -> Product | None:
        for vertical in candidates[concept.id]:
            if vertical in avoid:
                continue
            if (concept.id, vertical) not in found:
                found[concept.id, vertical] = _kit_product(conn, embedder, concept, vertical)
            if found[concept.id, vertical]:
                return found[concept.id, vertical]
        return None

    kit: list[tuple[Concept, Product]] = []
    used: set[str] = set()
    left: list[Concept] = []
    for concept in concepts:  # primero cada concepto en su vertical típica, si nadie la usó todavía…
        if len(kit) >= KIT_SIZE:
            break
        typical = candidates[concept.id][:1]
        spread = occasion.vertical is None
        product = None if spread and typical and typical[0] in used else pick(concept, used if spread else set())
        if product:
            kit.append((concept, product))
            used.add(product.vertical)
        else:
            left.append(concept)
    for concept in left:  # …y lo que falte, de otra vertical si la hay y, si no, de una ya usada
        if len(kit) >= KIT_SIZE:
            break
        if product := pick(concept, used) or pick(concept, set()):
            kit.append((concept, product))
            used.add(product.vertical)
    if not kit:
        return None
    verticals = list(dict.fromkeys(p.vertical for _, p in kit))
    text = contract_articles(
        PLAN_TEXT.format(
            occasion=occasion.name,
            concepts=_join([c.name.lower() for c, _ in kit]),
            verticals=_join([VERTICAL_LABELS.get(v, v) for v in verticals]),
        )
    )
    # «Más ideas» busca lo que el agente busca para una ocasión: los nombres de sus primeros conceptos que arma
    query = " ".join(c.name for c in concepts[:4])
    return Offer(
        "plan",
        text,
        [p.to_dict() for _, p in kit],
        verticals[0],
        _reason(
            REASON_PLAN.format(occasion=occasion.name),
            [_context_signal("ocasion", occasion.id)],
            occasion=occasion.id,
        ),
        [{"label": PLAN_ACTION, "query": query}],
    )


def _kit_verticals(conn: Connection, concept: Concept, fixed: str | None) -> list[str]:
    """Dónde se busca el concepto de un kit: la vertical fija de la ocasión, si tiene, y las verticales donde el
    concepto compite (con masa mínima: unos pocos productos de otra no lo representan), las más típicas primero."""
    allowed = [v for v in contending_verticals(conn, [concept.id]) if plannable_vertical(v, concept)]
    if fixed and plannable_vertical(fixed, concept):
        allowed = [fixed] + [v for v in allowed if v != fixed]
    return allowed[:KIT_VERTICALS]


def _kit_product(conn: Connection, embedder: TextEmbedder | None, concept: Concept, vertical: str) -> Product | None:
    """El primer producto del concepto en la vertical que dice qué es: se saltan los de nombre pelado."""
    for mode in ("vector", "hibrido") if embedder is not None else ("hibrido",):
        outcome = search_products(
            conn,
            vertical,
            concept.name,
            [concept.id],
            embedder,
            k=KIT_CANDIDATES,
            mode=mode,
            offer=True,
            adult_ok=concept.age_restricted,
        )
        if product := next((p for p in outcome.products if p.concept == concept.id and not _bare(p, concept)), None):
            return product
    return None


def _bare(product: Product, concept: Concept) -> bool:
    """«POLLO», «Queso» o «el Pollo»: el nombre es una sola palabra (sin contar el artículo) o el del concepto mismo, y
    no dice qué producto es."""
    words = [w for w in tokens(product.name) if w not in ARTICLES]
    return len(words) <= 1 or normalize(product.name) == normalize(concept.name)


# ── carrito, checkout y próximo pedido ───────────────────────────────────────
def complement(
    conn: Connection,
    embedder: TextEmbedder | None,
    moment: str,
    entities: list[dict],
    brands: dict[str, int] | None = None,
) -> Offer | None:
    """Un complemento ofrecible (arista «complementa») de lo que hay en el carrito, el pedido o el producto, de otra
    vertical si la hay, y que no esté ya ahí. Lo que ya está puede ser cualquier cosa: solo se ofrece lo que el agente
    puede proponer. Con `brands` (las que la persona compra: brand_key → pedidos), si el primer producto es de una de
    ellas, el porqué la nombra."""
    keys = [(e["entity_type"], e["entity_id"]) for e in entities]
    known = _concepts_of(conn, keys)
    sources = list(dict.fromkeys(known[key] for key in keys if key in known))
    if not sources:
        return None
    current = (ranked_verticals(conn, [sources[0]]) or [None])[0]  # de dónde es lo primero que lleva
    suggestion = suggest_complement(conn, sources, current, embedder, set(sources), brands)
    if suggestion is None:
        return None
    products = [p.to_dict() for p in suggestion.products if (p.entity_type, p.entity_id) not in set(keys)]
    if not products:
        return None
    concepts = load_taxonomy().concepts
    target, origin = concepts[suggestion.concept], concepts[suggestion.source_concept]
    vertical = VERTICAL_LABELS.get(suggestion.vertical, suggestion.vertical)
    if moment == "carrito":
        template = CART_TEXT if is_offerable(origin) else CART_TEXT_ANONYMOUS
    else:
        template = CHECKOUT_TEXT if moment == "checkout" else NEXT_ORDER_TEXT
    text = template.format(origen=origin.name.lower(), destino=target.name.lower(), vertical=vertical)
    reason = complement_reason(moment, origin, target)
    if suggestion.brand and products[0]["id"] == suggestion.products[0].id:  # su marca sigue encabezando la oferta
        name = conn.execute("SELECT name FROM product_brands WHERE brand_key = %s", (suggestion.brand,)).fetchone()[0]
        reason["text"] += REASON_BRAND.format(brand=name)
        reason["basis"].append(Signal("marca", suggestion.brand, brands[suggestion.brand], "pedidos").to_dict())
    return Offer(moment, text, products, suggestion.vertical, reason, [_see_action(target, suggestion.vertical)])


def complement_reason(moment: str, origin: Concept, target: Concept) -> dict:
    """Por qué se ofrece `target` en `carrito`, `checkout` o `proximo_pedido`. Si el agente no propone el origen
    (cerveza, pañales), ni el texto ni la base lo nombran."""
    ordered = moment == "proximo_pedido"
    if is_offerable(origin):
        template = REASON_NEXT if ordered else REASON_CART
        text = template.format(emoji=origin.emoji, name=origin.name.lower())
        basis = [_context_signal("pedido" if ordered else "carrito", origin.id)]
    else:
        text, basis = REASON_NEXT_ANONYMOUS if ordered else REASON_CART_ANONYMOUS, []
    return _reason(text, basis, concept=target.id, from_concept=origin.id)


# ── sin resultado ────────────────────────────────────────────────────────────
def where_is_it(conn: Connection, embedder: TextEmbedder | None, query: str) -> Offer | None:
    """La vertical que el agente puede proponer y que sí tiene el concepto de la consulta, con hasta tres productos."""
    concepts = load_taxonomy().concepts
    for concept_id in detect_concepts(query):
        concept = concepts.get(concept_id)
        if concept is None or not is_offerable(concept):
            continue
        for vertical in [v for v in ranked_verticals(conn, [concept_id]) if offerable_vertical(v)][:FALLBACK_VERTICALS]:
            outcome = search_products(
                conn, vertical, concept.name, [concept_id], embedder, k=SHOWN_PRODUCTS, offer=True
            )
            products = [p.to_dict() for p in outcome.products if p.concept == concept_id]
            if products:
                text = NO_RESULT_TEXT.format(
                    query=query.strip(), destino=concept.name.lower(), vertical=VERTICAL_LABELS.get(vertical, vertical)
                )
                reason = _reason(
                    REASON_NO_RESULT.format(query=query.strip()),
                    [_context_signal("busqueda", query.strip())],
                    concept=concept_id,
                )
                return Offer("sin_resultado", text, products, vertical, reason, [_see_action(concept, vertical)])
    return None


# ── vertical por probar ──────────────────────────────────────────────────────
def tried_verticals(conn: Connection, user_id: str | None) -> set[str]:
    """Las verticales donde la persona ya pidió (pedidos del modo `propuesta`; «Rappi hoy» no cuenta). Vacío sin
    persona."""
    if user_id is None:
        return set()
    rows = conn.execute(
        "SELECT DISTINCT vertical FROM app_orders WHERE user_id = %s AND mode = 'propuesta'", (user_id,)
    ).fetchall()
    return {vertical for (vertical,) in rows}


def vertical_to_try(
    conn: Connection,
    embedder: TextEmbedder | None,
    tried: set[str],
    interests: Interests,
    user_id: str | None = None,
) -> Offer | None:
    """La vertical por probar. Si el motor tiene un paso para la persona (`motor.predict.target_step`: el grupo que
    más retención suma a su combinación de los últimos 30 días), una vertical de ese grupo (`_combo_offer`); si no lo
    tiene (sin pedidos, o ya usa los tres grupos) o el grupo no tiene nada que mostrar, la de siempre
    (`_usual_to_try`). `tried`: verticales del backend con algún pedido suyo (`tried_verticals`)."""
    step = target_step(conn, user_id) if user_id is not None else None
    if step is not None and (offer := _combo_offer(conn, embedder, tried, interests, user_id, step)):
        return offer
    return _usual_to_try(conn, tried, interests)


def _usual_to_try(conn: Connection, tried: set[str], interests: Interests) -> Offer | None:
    """La vertical donde la persona aún no pide (nunca farmacia ni Licores) que más le gusta, o la primera de
    `TO_TRY_ORDER` si no hay afinidad (ese orden desempata). Muestra hasta tres de sus ofertas o, en restaurantes (que
    no tiene ofertas), sus platos más pedidos; una vertical sin nada que mostrar se salta."""
    candidates = [v for v in TO_TRY_ORDER if v not in tried and offerable_vertical(v)]
    affinity = _vertical_affinity(conn, interests) if interests.concepts else {}
    for vertical in sorted(candidates, key=lambda v: -sum(affinity.get(v, {}).values())):
        if products := _deals_or_dishes(conn, vertical):
            return _usual_offer(vertical, products, interests, affinity)
    return None


def _deals_or_dishes(conn: Connection, vertical: str) -> list[dict]:
    return _popular_dishes(conn) if vertical == "restaurantes" else _offerable_deals(conn, vertical)


def _usual_offer(
    vertical: str,
    products: list[dict],
    interests: Interests,
    affinity: dict,
    basis: tuple[dict, ...] = (),
    back: bool = False,
) -> Offer:
    """La oferta de siempre de una vertical por probar: «Aún no pides en…» y, si algo de ahí le gusta, «Porque te
    gusta…»; `basis` va antes de sus señales. Con `back` (una vertical del paso donde ya pidió), «Vuelve a…»."""
    label = VERTICAL_LABELS.get(vertical, vertical)
    what = TO_TRY_DISHES if vertical == "restaurantes" else TO_TRY_DEALS
    if back:
        text = contract_articles(BACK_TEXT.format(vertical=label, what=what))
        reason = _back_reason(vertical, [])
    else:
        text = TO_TRY_TEXT.format(vertical=label, what=what)
        if likes := affinity.get(vertical):
            reason = _likes_reason(REASON_LIKES_VERTICAL, likes, interests, vertical=label)
        else:
            reason = _reason(
                contract_articles(REASON_TO_TRY.format(vertical=label)), [_context_signal("sin_pedidos", vertical)]
            )
    reason["basis"] = [*basis, *reason["basis"]]
    return Offer("vertical_por_probar", text, products, vertical, reason, [_open_action(vertical)])


def _back_reason(vertical: str, basis: list[dict]) -> dict:
    """«Porque hace más de un mes que no pides en…», con la señal `vuelta` (de sus pedidos) al final de `basis`."""
    label = VERTICAL_LABELS.get(vertical, vertical)
    signal = {"kind": "vuelta", "id": vertical, "source": "pedidos"}
    return _reason(contract_articles(REASON_BACK.format(vertical=label)), [*basis, signal])


def _combo_offer(
    conn: Connection,
    embedder: TextEmbedder | None,
    tried: set[str],
    interests: Interests,
    user_id: str,
    step: tuple[str, str, float],
) -> Offer | None:
    """Una vertical del grupo que completa la combinación: las que se pueden ofrecer, primero las que la persona no ha
    probado y, entre ellas, en el orden de `next_verticals`. Para la primera con algo que mostrar: los productos de su
    mejor compra cruzada (`cross_picks`), o lo más pedido ahí por la población (`trends`), o sus ofertas o platos de
    siempre. La `basis` parte con el paso (`combinacion`). Si ya pidió en esa vertical (hace más de un mes), lo más
    pedido y lo de siempre dicen «Vuelve a…»; la compra cruzada sigue siendo cierta y no cambia."""
    group, target, _gain = step
    population = config.MOTOR_POBLACION
    current = combo_key(set(target.split("+")) - {group})
    combo = {"kind": "combinacion", "id": f"{current}→{target}", "source": "rappi"}
    candidates = [v for v in load_combos().groups[group] if offerable_vertical(v)]
    if len(candidates) > 1:
        order = [s.vertical for s in next_verticals(conn, user_id, population)]
        candidates.sort(key=lambda v: (v in tried, order.index(v)))
    if not candidates:
        return None
    lam = latest_lambda(conn, population)
    best: dict[str, CrossPick] = {}  # la mejor compra cruzada de cada vertical
    for pick in cross_picks(conn, user_id, candidates, population, k=None, lam=lam):
        best.setdefault(pick.vertical, pick)
    affinity: dict | None = None
    for vertical in candidates:
        back = vertical in tried
        pick = best.get(vertical)
        if pick and (products := _pick_products(conn, embedder, pick)):
            concepts = load_taxonomy().concepts
            origin = concepts.get(pick.from_concept) if pick.from_concept else None
            # Solo si la regla empujó el par (λ > 0) y el agente puede nombrar lo que la persona pide.
            if origin is not None and is_offerable(origin) and lam > 0:
                return _cross_offer(vertical, products, pick, origin, combo, population)
            return _top_offer(vertical, products, combo, population, back)
        if products := _most_ordered(conn, vertical, population):
            return _top_offer(vertical, products, combo, population, back)
        if products := _deals_or_dishes(conn, vertical):
            if affinity is None:
                affinity = _vertical_affinity(conn, interests) if interests.concepts else {}
            return _usual_offer(vertical, products, interests, affinity, (combo,), back)
    return None


def _cross_offer(
    vertical: str, products: list[dict], pick: CrossPick, origin: Concept, combo: dict, population: str
) -> Offer:
    """«Para acompañar tu…»: la compra cruzada que la regla de la población empujó desde lo que pide la persona."""
    label = VERTICAL_LABELS.get(vertical, vertical)
    destino = load_taxonomy().concepts[pick.concept_id].name.lower()
    text = TO_TRY_CROSS_TEXT.format(origen=origin.name.lower(), destino=destino, vertical=label)
    why = REASON_TO_TRY_CROSS.format(emoji=origin.emoji, name=origin.name.lower(), destino=destino, vertical=label)
    signal = {
        "kind": "compra_cruzada",
        "id": f"{origin.id}→{pick.concept_id}@{vertical}",
        "source": f"poblacion:{population}",
    }
    reason = _reason(contract_articles(why), [combo, signal], concept=pick.concept_id, from_concept=origin.id)
    return Offer("vertical_por_probar", contract_articles(text), products, vertical, reason, [_open_action(vertical)])


def _top_offer(vertical: str, products: list[dict], combo: dict, population: str, back: bool = False) -> Offer:
    """«Lo más pedido en…»: lo que más pide la población en la vertical (o lo de un concepto que nadie empujó). Con
    `back`, «Vuelve a…»."""
    label = VERTICAL_LABELS.get(vertical, vertical)
    signal = {"kind": "lo_mas_pedido", "id": vertical, "source": f"poblacion:{population}"}
    if back:
        text = BACK_TEXT.format(vertical=label, what=BACK_TOP)
        reason = _back_reason(vertical, [combo, signal])
    else:
        text = TO_TRY_TOP_TEXT.format(vertical=label)
        reason = _reason(contract_articles(REASON_TO_TRY_TOP.format(vertical=label)), [combo, signal])
    return Offer("vertical_por_probar", contract_articles(text), products, vertical, reason, [_open_action(vertical)])


def _pick_products(conn: Connection, embedder: TextEmbedder | None, pick: CrossPick) -> list[dict]:
    """Hasta tres productos del concepto de una compra cruzada en su vertical, buscados como oferta."""
    concept = load_taxonomy().concepts[pick.concept_id]
    outcome = search_products(
        conn, pick.vertical, concept.name, [concept.id], embedder, k=SHOWN_PRODUCTS + 1, offer=True
    )
    found = [p.to_dict() for p in outcome.products if p.concept == concept.id]
    return _offerable_products(conn, found)[:SHOWN_PRODUCTS]


# Lo más pedido de una vertical, con el precio de esa vertical: la oferta vigente más barata (`v_latest_offers`, la
# única definición de oferta vigente) de una tienda de la vertical que lo tiene en un pasillo (la regla de
# `catalog.stores._CURRENT_OFFERS`). Una sola consulta para todos los candidatos.
_TOP_CATALOG = """
SELECT DISTINCT ON (sp.master_product_id)
       sp.master_product_id::text, ci.name, l.price, l.real_price, btrim(coalesce(b.name, s.name)), s.store_id,
       NULLIF(ci.image_url, ''), ci.presentation, ci.is_alcoholic OR ci.age_restricted, ic.concept_id
FROM store_products sp
JOIN v_latest_offers l ON l.store_id = sp.store_id AND l.sku = sp.sku
JOIN aisles a ON a.store_id = sp.store_id AND a.aisle_id = sp.aisle_id AND a.parent_aisle_id IS NULL
JOIN stores s ON s.store_id = sp.store_id
JOIN catalog_items ci ON ci.master_product_id = sp.master_product_id
LEFT JOIN brands b ON b.brand_id = s.brand_id
LEFT JOIN item_concepts ic ON ic.entity_type = 'catalog_item' AND ic.entity_id = ci.master_product_id::text
WHERE sp.master_product_id = ANY(%(ids)s) AND l.current AND l.in_stock IS NOT FALSE AND l.price >= %(min_price)s
  AND EXISTS (SELECT 1 FROM v_store_verticals v WHERE v.store_id = sp.store_id AND v.vertical = %(vertical)s)
ORDER BY sp.master_product_id, l.price, sp.store_id"""
# Los platos con su último precio (`latest_menu_prices`) y la sección del menú donde están.
_TOP_DISHES = """
SELECT mi.item_id::text, mi.name, mp.price, mp.real_price, s.name, s.store_id, NULLIF(mi.image_url, ''),
       ic.concept_id, ms.name
FROM menu_items mi
JOIN stores s ON s.store_id = mi.store_id
JOIN latest_menu_prices mp ON mp.item_id = mi.item_id
LEFT JOIN menu_sections ms ON ms.store_id = mi.store_id AND ms.section_id = mi.section_id
LEFT JOIN item_concepts ic ON ic.entity_type = 'menu_item' AND ic.entity_id = mi.item_id::text
WHERE mi.item_id = ANY(%(ids)s)"""


def _most_ordered(conn: Connection, vertical: str, population: str) -> list[dict]:
    """Hasta tres de los productos más pedidos por la población en la vertical (`trends`, alcance `producto`), en su
    orden, que siguen a la venta ahí: un producto del catálogo con su oferta vigente más barata en una tienda de esa
    vertical (`_TOP_CATALOG`), o en restaurantes un plato con precio que no es de una sección de tragos
    (`_TOP_DISHES`). Pasan las guardias de las ofertas (`_offerable_products`), también la de su tienda."""
    kind = "menu_item" if vertical == "restaurantes" else "catalog_item"
    rows = conn.execute(
        """SELECT entity_id FROM trends
           WHERE data_source = %s AND scope = 'producto' AND vertical = %s AND entity_type = %s
           ORDER BY rank, item_key""",
        (population, vertical, kind),
    ).fetchall()
    ids = [i for (i,) in rows if i.isascii() and i.isdigit() and int(i) <= BIGINT_MAX]
    if not ids:
        return []
    params = {"ids": [int(i) for i in ids], "vertical": vertical, "min_price": MIN_PRICE}
    taxonomy = load_taxonomy()
    found: dict[str, Product] = {}
    if kind == "catalog_item":
        for id_, name, price, real, store, store_id, image, presentation, adult, concept in conn.execute(
            _TOP_CATALOG, params
        ):
            row = (id_, name, price, real, image, presentation, adult, concept)
            found[id_] = _product(row, vertical, store, store_id, taxonomy)
    else:
        for id_, name, price, real, store, store_id, image, concept, section in conn.execute(_TOP_DISHES, params):
            if not alcohol_section(section):
                row = (id_, name, price, real, image, None, False, concept)
                found[id_] = _product(row, vertical, store, store_id, taxonomy, kind)
    ranked = [found[i].to_dict() for i in ids if i in found and found[i].price_value is not None]
    return _offerable_products(conn, ranked)[:SHOWN_PRODUCTS]


def _open_action(vertical: str) -> dict:
    label = OPEN_ACTION.format(vertical=VERTICAL_LABELS.get(vertical, vertical))
    return {"label": label, "route": [SCREEN_VERTICALS[vertical]]}


def _vertical_affinity(conn: Connection, interests: Interests) -> dict[str, dict[str, float]]:
    """vertical → {concepto: puntaje} de los conceptos que le gustan a la persona y cuya vertical típica es esa."""
    typical = typical_verticals(conn)
    affinity: dict[str, dict[str, float]] = {}
    for concept_id, score in interests.concepts.items():
        if vertical := typical.get(concept_id):
            affinity.setdefault(vertical, {})[concept_id] = score
    return affinity


# ── perfil ───────────────────────────────────────────────────────────────────
def profile_offer(
    conn: Connection, embedder: TextEmbedder | None, profile_id: str | None, user_id: str | None
) -> ProfileOffer | None:
    """La escalera de un perfil de gusto. Sin `profile_id`, el primero de los perfiles de la persona (el principal y
    después por puntaje); con él, ese perfil, y con su «por qué» solo si es uno de los suyos (si no, «Porque elegiste…»,
    como sin persona: lo que usan la demo y el contrato). El peldaño de restaurantes deja fuera los locales donde la
    persona ya pidió y muestra los de su ciudad (`person_city`). None (204) sin perfil o sin escalera; un perfil que
    no existe es un `OfferError` (422)."""
    profiles = load_profiles()
    if profile_id is not None and profile_id not in profiles:
        raise OfferError(f"Perfil desconocido: «{profile_id}»")
    mine = {active.profile.id: active for active in active_profiles(conn, user_id)}  # en su orden
    if profile_id is None and not mine:
        return None
    profile = profiles[profile_id] if profile_id is not None else next(iter(mine.values())).profile
    active = mine.get(profile.id)
    steps = ladder(conn, embedder, profile, ordered_restaurants(conn, user_id), person_city(conn, user_id))
    if not steps:
        return None
    shown = {"id": profile.id, "nombre": profile.name, "emoji": profile.emoji}
    if active:
        shown |= {"nivel": active.level, "por_que": active.reason}
    actions = [
        {
            "label": OPEN_ACTION.format(vertical=VERTICAL_LABELS[s.step.vertical]),
            "route": [SCREEN_VERTICALS[s.step.vertical]],
        }
        for s in steps
    ]
    trip = None
    if profile.trip:
        travel = load_taxonomy().services[TRIP_SERVICE]
        trip = _trip(load_destinations()[profile.trip], travel)
        actions.append(
            {"label": OPEN_ACTION.format(vertical=travel.name), "route": [travel.route], "service": travel.id}
        )
    return ProfileOffer(
        _profile_text(profile),
        shown,
        [s.to_dict() for s in steps],
        trip,
        _profile_reason(profile, active),
        actions,
    )


def _profile_text(profile: Profile) -> str:
    """«Como te gusta lo asiático…», con el `gusto` del perfil; sin él, el nombre del perfil con su emoji."""
    if profile.likes:
        return PROFILE_TEXT.format(likes=profile.likes)
    return PROFILE_TEXT_NAMED.format(emoji=profile.emoji, name=profile.name)


def _profile_reason(profile: Profile, active: ActiveProfile | None) -> dict:
    if active:
        return _reason(active.reason, list(active.basis))
    return _reason(REASON_PROFILE.format(name=profile.name), [_context_signal("perfil", profile.id)])


def _trip(destination: Destination, travel: Service) -> dict:
    """El último peldaño: un destino curado, rotulado como idea para RappiTravel (sin precios ni fechas)."""
    return {
        "id": destination.id,
        "nombre": destination.name,
        "texto": destination.text,
        "hechos": [{"texto": f.text, "fuente": f.source, "url": f.url} for f in destination.facts],
        "etiqueta": TRIP_LABEL.format(service=travel.name),
        "route": [travel.route],
    }


def _offerable_deals(conn: Connection, vertical: str) -> list[dict]:
    """Las ofertas de la vertical que el agente puede proponer: ni +18 (tampoco un nombre que dice alcohol), ni un
    nombre que dice bebé, ni de un concepto que no ofrece, ni de una tienda Farmacia, Sex shop o Smoking shop (`deals`
    ya quita lo sensible, pero con vertical no quita esas tiendas). Un producto que está dos veces con otro id (el
    catálogo repite nombres) sale una vez. Las de un concepto típico de la vertical van primero."""
    unique: dict[str, dict] = {}
    for deal in _offerable_products(conn, deals(conn, vertical, DEAL_POOL)):
        unique.setdefault(" ".join(deal["name"].lower().split()), deal)
    return _typical_first(list(unique.values()), vertical, typical_verticals(conn))[:SHOWN_PRODUCTS]


def _offerable_products(conn: Connection, products: list[dict]) -> list[dict]:
    """Los productos (`Product.to_dict()`) que el agente puede proponer por su cuenta: ni +18, ni un nombre que dice
    alcohol o bebé, ni de un concepto que no ofrece, ni de una tienda Farmacia, Sex shop o Smoking shop. Sin
    `entity_type` es del catálogo (las ofertas de `deals` lo son)."""
    concepts = load_taxonomy().concepts
    blocked = {
        store_id
        for (store_id,) in conn.execute(
            "SELECT store_id FROM store_verticals WHERE store_id = ANY(%s) AND subvertical = ANY(%s)",
            ([p["store_id"] for p in products if p["store_id"]], unofferable_subverticals()),
        )
    }
    return [
        p
        for p in products
        if not p["age_restricted"]
        and not alcohol_in_name(p.get("entity_type", "catalog_item"), p["name"], p["concept"])
        and not baby_in_name(p.get("entity_type", "catalog_item"), p["name"])
        and p["store_id"] not in blocked
        and (p["concept"] not in concepts or is_offerable(concepts[p["concept"]]))
    ]


def _typical_first(found: list[dict], vertical: str, typical: dict[str, str]) -> list[dict]:
    """Primero las ofertas de un concepto típico de la vertical (el súper ofrecía mantas y silicona para auto con 60 %
    de descuento), después las de cualquier otro concepto y al final las sin concepto. En las verticales de comida
    (`FOOD_VERTICALS`), lo que no es de un grupo de comida va después de la comida aunque sea típico (Express partía
    con una cera para auto: `automotriz` es típico de las tiendas de las bencineras). Dentro de cada grupo se mantiene
    el orden de llegada (el mayor descuento primero); si las primeras no alcanzan, completan las demás."""
    concepts = load_taxonomy().concepts

    def group(deal: dict) -> int:
        if not deal["concept"]:
            return 3
        concept = concepts.get(deal["concept"])
        if vertical in FOOD_VERTICALS and concept and (concept.parent or concept.id) not in FOOD_GROUPS:
            return 2
        return 0 if typical.get(deal["concept"]) == vertical else 1

    return sorted(found, key=group)


def _popular_dishes(conn: Connection) -> list[dict]:
    """Los platos populares (`is_popular`) de los conceptos que más se piden hechos en restaurantes, uno por concepto y
    solo de los que el agente puede proponer, sin un nombre que diga alcohol ni de una sección de tragos
    (`alcohol_in_name`, `alcohol_section`). Restaurantes no tiene ofertas ni otro dato de pedidos."""
    concepts = load_taxonomy().concepts
    ranked = [
        concept_id
        for (concept_id,) in conn.execute(
            """SELECT a.concept_id FROM concept_assortment a JOIN concepts c USING (concept_id)
               WHERE a.vertical = 'restaurantes' AND a.items > 0 AND c.prepared ORDER BY a.items DESC, a.concept_id"""
        )
        if concept_id in concepts and is_offerable(concepts[concept_id])
    ]
    dishes: dict[str, str] = {}
    for concept_id, item_id, name, section in conn.execute(
        """SELECT ic.concept_id, mi.item_id::text, mi.name, ms.name
           FROM menu_items mi
           JOIN item_concepts ic ON ic.entity_type = 'menu_item' AND ic.entity_id = mi.item_id::text
           LEFT JOIN menu_sections ms ON ms.store_id = mi.store_id AND ms.section_id = mi.section_id
           WHERE mi.is_popular AND ic.concept_id = ANY(%s)
           ORDER BY ic.concept_id, mi.item_id""",
        (ranked,),
    ):
        if concept_id in dishes or alcohol_in_name("menu_item", name, concept_id) or alcohol_section(section):
            continue
        dishes[concept_id] = item_id
    products: list[dict] = []
    for concept_id in ranked:
        if concept_id in dishes and (dish := product_detail(conn, "menu_item", dishes[concept_id])):
            products.append(dish)
        if len(products) >= SHOWN_PRODUCTS:
            break
    return products


def _context_signal(kind: str, signal_id: str) -> dict:
    return {"kind": kind, "id": signal_id, "source": "contexto"}


def _reason(text: str, basis: list[dict], **ids: str) -> dict:
    return {**ids, "text": text, "basis": basis}


def _see_action(concept: Concept, vertical: str) -> dict:
    return {
        "label": SEE_ACTION.format(destino=concept.name.lower()),
        "route": [SCREEN_VERTICALS.get(vertical)],
        "query": concept.name.lower(),
    }


def _join(items: list[str]) -> str:
    """«a, b y c»."""
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " y " + items[-1]

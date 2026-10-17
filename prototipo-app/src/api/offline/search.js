// `GET /search` y `POST /agent/ask` sin conexión: primero la respuesta grabada de la API real (las ideas del buscador,
// los chips de Mochi y búsquedas comunes); si no hay, una búsqueda simple por palabras sobre los productos de la
// muestra, sin tildes ni ñ (agent/grouped_search.py y agent/rappi_agent.py hacen la búsqueda híbrida de verdad).
import { offerableProduct } from './offers'
import { normalize } from './text'

const GROUPED_LIMIT = 6 // por grupo (api/app.py: GROUPED_SEARCH_LIMIT)
const VERTICAL_LIMIT = 10
const ASK_LIMIT = 6
const AGE_NOTICE = ' Recuerda: estos productos se venden solo a mayores de 18.'
const UNMET_REASON = 'sin coincidencias en la muestra de la demo sin conexión'
// Ids del prototipo → códigos del backend (api/deps.py: backend_vertical).
const FROM_PROTOTYPE = {
  grocery: 'supermercado',
  liquor: 'licores',
  pharmacy: 'farmacia',
  retail: 'mall',
  express: 'conveniencia',
  chocolates: 'chocolateria',
  restaurants: 'restaurantes',
}
const VERTICALS = [
  'restaurantes',
  'turbo',
  'supermercado',
  'farmacia',
  'mall',
  'licores',
  'conveniencia',
  'chocolateria',
]

/** El código del backend de una vertical (acepta el id del prototipo); null si no es del catálogo. */
export function backendVertical(vertical) {
  const code = FROM_PROTOTYPE[vertical] ?? vertical
  return VERTICALS.includes(code) ? code : null
}

// Una palabra de la consulta calza con una del nombre si es su comienzo (o el de su singular: «panales» → «panal»).
const stem = (word) =>
  word.length > 4 && word.endsWith('es')
    ? word.slice(0, -2)
    : word.length > 3 && word.endsWith('s')
      ? word.slice(0, -1)
      : word
const STOP = new Set([
  'de',
  'del',
  'la',
  'el',
  'los',
  'las',
  'un',
  'una',
  'para',
  'con',
  'en',
  'y',
  'mi',
  'algo',
  'quiero',
])

/** Los productos de la muestra que calzan con `q`, del mejor al peor (cada uno una vez por vertical). */
export function matchProducts(snapshot, q) {
  const words = normalize(q)
    .split(' ')
    .filter((w) => w && !STOP.has(w))
    .map(stem)
  if (!words.length) return []
  const conceptHits = new Set(
    Object.entries(snapshot.meta.concepts)
      .filter(([, c]) => words.every((w) => normalize(c.name).includes(w)))
      .map(([id]) => id),
  )
  const scored = []
  const seen = new Set()
  for (const p of snapshot.pool) {
    const name = ` ${normalize(p.name)}`
    const inName = words.filter((w) => name.includes(` ${w}`)).length
    const byConcept = conceptHits.has(p.concept)
    if (inName < words.length && !byConcept) continue
    const key = `${p.vertical}|${p.id}`
    if (seen.has(key)) continue
    seen.add(key)
    scored.push({ p, score: inName * 2 + (byConcept ? 1 : 0) + (name.startsWith(` ${words[0]}`) ? 1 : 0) })
  }
  return scored.sort((a, b) => b.score - a.score).map((s) => s.p)
}

/** Grupos por vertical: la de la pantalla primero, después las que más productos calzan (search_grouped). */
function groupsOf(snapshot, found, current, limit) {
  const byVertical = new Map()
  for (const p of found) byVertical.set(p.vertical, [...(byVertical.get(p.vertical) ?? []), p])
  const order = [...byVertical.keys()].sort(
    (a, b) => (b === current) - (a === current) || byVertical.get(b).length - byVertical.get(a).length,
  )
  return order.map((vertical) => ({
    vertical,
    prototype_vertical: snapshot.meta.screen_verticals[vertical] ?? null,
    products: byVertical.get(vertical).slice(0, limit),
  }))
}

/** `GET /search?q=&vertical=&current=&limit=`. */
export function search(snapshot, query) {
  const q = query.get('q') ?? ''
  const vertical = backendVertical(query.get('vertical'))
  const current = backendVertical(query.get('current'))
  const limit = Number(query.get('limit')) || null
  const recorded = snapshot.search[normalize(q)]
  if (query.get('vertical')) {
    const group = recorded?.groups.find((g) => g.vertical === vertical)
    const products = (group?.products ?? matchProducts(snapshot, q).filter((p) => p.vertical === vertical)).slice(
      0,
      limit ?? VERTICAL_LIMIT,
    )
    return { vertical, products, unmet: !products.length, unmet_reason: products.length ? null : UNMET_REASON }
  }
  if (recorded && !current) return recorded
  const groups = groupsOf(snapshot, matchProducts(snapshot, q), current, limit ?? GROUPED_LIMIT)
  return { groups, query: q, unmet: !groups.length, unmet_reason: groups.length ? null : UNMET_REASON }
}

/** El concepto más repetido entre los productos. */
function topConcept(products) {
  const counts = new Map()
  for (const p of products) if (p.concept) counts.set(p.concept, (counts.get(p.concept) ?? 0) + 1)
  return [...counts].sort((a, b) => b[1] - a[1])[0]?.[0] ?? null
}

/** La sugerencia cruzada de una respuesta (agent/tools.py: suggest_complement): el complemento grabado del concepto. */
function suggestionFor(snapshot, conceptId) {
  const { concepts } = snapshot.meta
  const origin = concepts[conceptId]
  const recorded = snapshot.complements[conceptId]
  if (!origin?.offerable || !recorded) return null
  const target = concepts[recorded.reason?.concept]
  const products = recorded.products.filter((p) => offerableProduct(p, concepts)).slice(0, 3)
  if (!target || !products.length) return null
  return {
    concept: recorded.reason.concept,
    vertical: recorded.vertical,
    prototype_vertical: recorded.prototype_vertical,
    question: `¿Te tinca sumar ${target.emoji} ${target.name.toLowerCase()}?`,
    reason: `Porque llevas ${origin.emoji} ${origin.name.toLowerCase()}`,
    products,
    basis: [],
  }
}

/** `POST /agent/ask`: la respuesta grabada de esa pregunta o, si no hay, lo que calza en la muestra. */
export function ask(snapshot, body) {
  const message = String(body?.message ?? '')
  const recorded = snapshot.ask[normalize(message)]
  if (recorded) return recorded
  const { vertical_labels: labels, screen_verticals: screens } = snapshot.meta
  const found = matchProducts(snapshot, message)
  const preferred = backendVertical(body?.vertical)
  const group = groupsOf(snapshot, found, preferred, ASK_LIMIT)[0]
  const products = group?.products ?? []
  const concept = topConcept(products)
  const ageNotice = products.some((p) => p.age_restricted)
  const suggestion = concept && body?.mode !== 'actual' ? suggestionFor(snapshot, concept) : null
  const text = group
    ? `Mira lo que encontré de «${message.trim()}» en ${labels[group.vertical] ?? group.vertical}.${ageNotice ? AGE_NOTICE : ''}`
    : `No encontré «${message.trim()}» en la muestra de esta demo. Prueba con otras palabras.`
  return {
    text,
    products,
    vertical: group?.vertical ?? null,
    prototype_vertical: group ? (screens[group.vertical] ?? null) : null,
    intent: {
      kind: 'buscar',
      query: message.trim(),
      concepts: concept ? [concept] : [],
      vertical: group?.vertical ?? null,
      confidence: 0.5,
      follow_up: false,
      occasion: null,
      price_max: null,
    },
    reason: suggestion?.reason ?? null,
    suggestion,
    actions: [],
    tags: concept ? [concept] : [],
    stores: [],
    unmet: !group,
    unmet_reason: group ? null : UNMET_REASON,
    age_notice: ageNotice,
  }
}

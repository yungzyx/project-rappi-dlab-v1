// Toma la muestra del catálogo para la demo sin conexión (npm run demo:snapshot): llama a una API real y escribe
// src/api/offline/snapshot.json, que la API simulada del navegador (src/api/offline/) responde sin red.
//
// La API debe correr sobre una COPIA de la base, nunca sobre `rappi`: el script crea personas de prueba, registra
// pedidos (para grabar la vertical que el motor propone en cada paso de la escalera) y después las borra («Olvidar»).
//   cd rappi-ia && DATABASE_URL=postgresql:///rappi_staging .venv/bin/python -m rappi_ia migrate
//   DATABASE_URL=postgresql:///rappi_staging HF_HUB_OFFLINE=1 API_PREWARM=0 \
//     .venv/bin/python -m uvicorn rappi_ia.api.app:app --host 127.0.0.1 --port 8020
//   SNAPSHOT_ALLOW_WRITES=1 DEMO_API_URL=http://127.0.0.1:8020 npm run demo:snapshot
// Las tablas que la API no expone (conceptos con sus guardias, combinaciones de Rappi, servicios) las da
// scripts/demo-snapshot-meta.py con el Python de rappi-ia.
import { execFileSync } from 'node:child_process'
import { writeFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

const ROOT = fileURLToPath(new URL('..', import.meta.url))
const OUT = `${ROOT}src/api/offline/snapshot.json`
const API = (process.env.DEMO_API_URL || 'http://127.0.0.1:8020').replace(/\/+$/, '')
const PYTHON = `${ROOT}../rappi-ia/.venv/bin/python`

// Cuánto se lleva la muestra: lo justo para recorrer la demo sin que el archivo pase de ~3 MB.
const STORE_VERTICALS = ['supermercado', 'farmacia', 'mall', 'licores', 'conveniencia', 'chocolateria', 'turbo']
const STORES_PER_VERTICAL = 3
const AISLES_PER_STORE = 6
const TURBO_AISLES = 14 // la tienda de la pantalla Turbo: más pasillos, es la que más se recorre
const RESTAURANTS = 16
const CUISINES = ['Pizzas', 'Hamburguesa', 'Experiencias Culinarias']
const DEAL_VERTICALS = ['supermercado', 'licores', 'conveniencia', 'mall', 'chocolateria', 'turbo', 'farmacia']
// Las ideas del buscador (SearchSections) y búsquedas comunes; cada una se graba tal cual responde la API.
const QUERIES = [
  ...['Plátano', 'Agua', 'Chocolate', 'Hamburguesa', 'Cerveza', 'Pizza'],
  ...['café', 'sushi', 'pan', 'leche', 'helado', 'papas fritas', 'vino', 'pañales', 'shampoo', 'perfume', 'té'],
  ...['empanadas', 'completo', 'pollo', 'ensalada', 'huevos', 'bebida', 'snacks', 'flores', 'carbón', 'hielo'],
  ...['queso', 'galletas', 'yogurt', 'fruta', 'detergente', 'audífonos', 'cargador', 'alfajores', 'bombones'],
  ...['tacos', 'ramen', 'sándwich', 'comida de perro', 'pasta', 'arroz', 'cafe molido', 'jugo', 'torta'],
]
// Los chips del buscador con Mochi (AssistantPanel) y preguntas comunes.
const ASKS = [
  ...['🍔 ¿Qué almuerzo hoy?', '🍻 Arma un carrete', '🔥 Ofertas de hoy', '🍫 Algo dulce', '🎁 Un regalo'],
  ...['Quiero sushi', 'Algo para el desayuno', 'Tengo hambre', 'Algo para la once', 'Quiero café', 'Pizza'],
  ...['Un regalo para mi mamá', 'Algo para el asado', 'Necesito pañales', 'Comida para mi perro'],
]
// Búsquedas sin resultado que la oferta `sin_resultado` sabe responder (se graban las que respondan).
const NO_RESULT = ['sushi de chocolate', 'helado de palta', 'pizza vegana sin gluten', 'xyzzy']
// La escalera: con estos pedidos, el motor propone esa vertical (se graba la oferta real de cada paso).
const RETAIL = ['supermercado', 'conveniencia', 'mall', 'chocolateria']
const LADDER = [
  ['turbo', ['restaurantes']],
  ['restaurantes', ['turbo']],
  ...RETAIL.map((target) => [target, ['restaurantes', 'turbo', ...RETAIL.filter((v) => v !== target)]]),
]

function requireWritesAllowed() {
  if (process.env.SNAPSHOT_ALLOW_WRITES === '1') return
  console.error(
    'La muestra crea personas y pedidos de prueba en la base de la API (y los borra al final).\n' +
      'Corre la API sobre una copia, nunca sobre `rappi` (ver el inicio de este archivo), y después:\n' +
      '  SNAPSHOT_ALLOW_WRITES=1 DEMO_API_URL=http://127.0.0.1:8020 npm run demo:snapshot',
  )
  process.exit(1)
}

async function call(path, { method = 'GET', body, token, allow = [] } = {}) {
  const response = await fetch(`${API}${path}`, {
    method,
    body: body ? JSON.stringify(body) : undefined,
    headers: { ...(body ? { 'content-type': 'application/json' } : {}), ...(token ? { 'X-User-Token': token } : {}) },
    signal: AbortSignal.timeout(60_000),
  })
  if (response.status === 204) return null
  if (!response.ok) {
    if (allow.includes(response.status)) return null
    throw new Error(`${method} ${path}: ${response.status} ${await response.text()}`)
  }
  return response.json()
}

const session = () => call('/session', { method: 'POST', body: {} })

/** Clave de una consulta o pregunta: sin tildes (salvo la ñ, que también se quita), emojis ni signos. */
export const normalize = (text) =>
  text
    .normalize('NFD')
    .replace(/\p{M}/gu, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, ' ')
    .trim()

async function catalog(token) {
  const get = (path, allow) => call(path, { token, allow })
  const out = { restaurants: {}, deals: {}, verticalStores: {}, stores: {}, menus: {} }
  out.home = await get('/catalog/home')

  // Restaurantes: las listas (por nota, por cocina, las de la Home) y el menú de cada uno de ellos.
  out.restaurants.rating = await get(`/catalog/restaurants?sort=rating&limit=${RESTAURANTS}`)
  for (const cuisine of CUISINES)
    out.restaurants[`rating|${cuisine}`] = await get(
      `/catalog/restaurants?sort=rating&limit=8&cuisine=${encodeURIComponent(cuisine)}`,
    )
  const restaurantIds = new Set(
    [...Object.values(out.restaurants).flat(), ...out.home.fast_restaurants, ...out.home.low_fee_restaurants].map(
      (r) => r.id,
    ),
  )
  for (const id of restaurantIds) {
    const menu = await get(`/catalog/restaurants/${id}/menu`, [404])
    if (menu) out.menus[id] = menu
  }

  out.deals[''] = await get('/catalog/deals')
  for (const vertical of DEAL_VERTICALS) out.deals[vertical] = await get(`/catalog/deals?vertical=${vertical}`)

  // Tiendas: las primeras de cada vertical y las de la Home, con la primera página de sus primeros pasillos.
  const storeIds = new Map() // id → cuántos pasillos
  for (const vertical of STORE_VERTICALS) {
    const reply = await get(`/catalog/verticals/${vertical}/stores`)
    out.verticalStores[vertical] = reply
    reply.stores
      .slice(0, STORES_PER_VERTICAL)
      .forEach((s, i) => storeIds.set(s.id, vertical === 'turbo' && i === 0 ? TURBO_AISLES : AISLES_PER_STORE))
  }
  for (const s of out.home.nearby_stores) if (!storeIds.has(s.id)) storeIds.set(s.id, AISLES_PER_STORE)
  for (const [id, aisles] of storeIds) {
    const first = await get(`/catalog/stores/${id}`, [404])
    if (!first) continue
    const pages = { [first.aisle.id]: { aisle: first.aisle, products: first.products } }
    for (const aisle of first.aisles.slice(0, aisles)) {
      if (pages[aisle.id]) continue
      const reply = await get(`/catalog/stores/${id}?aisle=${aisle.id}`, [404])
      if (reply?.products.length) pages[aisle.id] = { aisle: reply.aisle, products: reply.products }
    }
    // Solo los pasillos grabados: las pestañas de la tienda no ofrecen uno que la demo no tiene.
    out.stores[id] = { store: first.store, aisles: first.aisles.filter((a) => pages[a.id]), pages }
  }
  // Las listas de tiendas solo con las grabadas (abrir otra daría «no está en el catálogo»).
  for (const reply of Object.values(out.verticalStores)) reply.stores = reply.stores.filter((s) => out.stores[s.id])
  out.home.nearby_stores = out.home.nearby_stores.filter((s) => out.stores[s.id])
  for (const key of Object.keys(out.restaurants))
    out.restaurants[key] = out.restaurants[key].filter((r) => out.menus[r.id])
  out.home.fast_restaurants = out.home.fast_restaurants.filter((r) => out.menus[r.id])
  out.home.low_fee_restaurants = out.home.low_fee_restaurants.filter((r) => out.menus[r.id])
  return out
}

async function agent(token, userId) {
  const post = (path, body, allow) => call(path, { method: 'POST', body, token, allow })
  const search = {}
  for (const q of QUERIES) search[normalize(q)] = await call(`/search?q=${encodeURIComponent(q)}`, { token })
  const ask = {}
  for (const message of ASKS)
    ask[normalize(message)] = await post('/agent/ask', { message, user_id: userId, mode: 'propuesta' })
  const plans = await call(`/agent/plans?user_id=${userId}`, { token })
  const planOffers = {}
  for (const { id } of plans) {
    const reply = await post('/agent/offer', { moment: 'plan', context: { occasion: id } }, [422])
    if (reply) planOffers[id] = reply
  }
  const noResult = {}
  for (const query of NO_RESULT) {
    const reply = await post('/agent/offer', { moment: 'sin_resultado', context: { query } }, [422])
    if (reply) noResult[normalize(query)] = reply
  }
  const recommendations = await call(`/recommendations?user_id=${userId}`, { token })
  // Sin pedidos, la vertical por probar de siempre (el súper, si tiene ofertas).
  const usual = await post('/agent/offer', { moment: 'vertical_por_probar', user_id: userId, context: {} })
  return { search, ask, plans, planOffers, noResult, recommendations, toTry: { usual } }
}

/** Todos los productos de una respuesta (los objetos con entity_type, entity_id y precio). */
function productsIn(value, found = []) {
  if (Array.isArray(value)) value.forEach((v) => productsIn(v, found))
  else if (value && typeof value === 'object') {
    if (isProduct(value)) found.push(value)
    else Object.values(value).forEach((v) => productsIn(v, found))
  }
  return found
}
const isProduct = (value) => 'entity_type' in value && 'entity_id' in value && 'price_value' in value

/** El complemento de cada concepto (la oferta `carrito` real con un producto de ese concepto en el carro). */
async function complements(token, pool) {
  const byConcept = new Map()
  for (const p of pool) if (p.concept && !byConcept.has(p.concept)) byConcept.set(p.concept, p)
  const out = {}
  for (const [concept, p] of byConcept) {
    const reply = await call('/agent/offer', {
      method: 'POST',
      token,
      body: { moment: 'carrito', context: { product: { entity_type: p.entity_type, entity_id: p.entity_id } } },
      allow: [422],
    })
    if (reply?.products.length) out[concept] = reply
  }
  return out
}

/**
 * La oferta real de cada paso de la escalera: una persona de prueba pide en las verticales de `LADDER` (un producto de
 * la primera tienda grabada de cada una) y se le pide `vertical_por_probar`; después se la olvida (`DELETE /profile`).
 */
async function ladder(snapshot) {
  const out = {}
  const sample = (vertical) => {
    if (vertical === 'restaurantes') {
      const menu = Object.values(snapshot.catalog.menus)[0]
      const dish = menu.sections.flatMap((s) => s.items)[0]
      return { ...dish, store_id: menu.restaurant.id }
    }
    const store = snapshot.catalog.verticalStores[vertical]?.stores[0]
    const page = store && Object.values(snapshot.catalog.stores[store.id].pages)[0]
    return page?.products[0]
  }
  for (const [target, verticals] of LADDER) {
    const { user_id: userId, token } = await session()
    try {
      for (const vertical of verticals) {
        const p = sample(vertical)
        if (!p) throw new Error(`Sin producto grabado de ${vertical} para la escalera`)
        await call('/orders', {
          method: 'POST',
          token,
          body: {
            user_id: userId,
            session_id: 's-demo-snapshot',
            cart_id: `c-${vertical}`,
            vertical,
            mode: 'propuesta',
            lines: [{ entity_type: p.entity_type, entity_id: p.entity_id, store_id: p.store_id, qty: 1 }],
          },
        })
      }
      await new Promise((resolve) => setTimeout(resolve, 1500)) // el motor recalcula la persona después de responder
      const reply = await call('/agent/offer', {
        method: 'POST',
        token,
        body: { moment: 'vertical_por_probar', user_id: userId, context: {} },
      })
      if (reply?.vertical) out[reply.vertical] = reply
      console.log(`  escalera: ${verticals.join('+')} → ${reply?.vertical ?? 'nada'} (esperado ${target})`)
    } finally {
      await call(`/profile/${userId}`, { method: 'DELETE', token })
    }
  }
  return out
}

// Un producto va como una fila con estos campos, en este orden (src/api/offline/snapshot.js la vuelve a armar): sin
// las claves repetidas, sin `id` (es `cat-` o `menu-` más `entity_id`) y con las fotos de images.rappi.cl abreviadas.
const PRODUCT_FIELDS = [
  ...['entity_type', 'entity_id', 'name', 'vertical', 'concept', 'price', 'price_value', 'before', 'discount'],
  ...['store', 'store_id', 'img', 'age_restricted', 'presentation'],
]
const IMG_PREFIX = 'https://images.rappi.cl/products/'

/** Los productos repetidos van una sola vez en `products`; en las respuestas quedan como `{ "$p": índice }`. */
function intern(snapshot) {
  const products = []
  const index = new Map()
  const row = (p) =>
    PRODUCT_FIELDS.map((field) =>
      field === 'img' && p.img?.startsWith(IMG_PREFIX) ? `~${p.img.slice(IMG_PREFIX.length)}` : (p[field] ?? null),
    )
  const walk = (value) => {
    if (Array.isArray(value)) return value.map(walk)
    if (!value || typeof value !== 'object') return value
    if (isProduct(value)) {
      const key = JSON.stringify(row(value))
      if (!index.has(key)) {
        index.set(key, products.length)
        products.push(row(value))
      }
      return { $p: index.get(key) }
    }
    return Object.fromEntries(Object.entries(value).map(([k, v]) => [k, walk(v)]))
  }
  const interned = walk(snapshot)
  return { ...interned, productFields: PRODUCT_FIELDS, imgPrefix: IMG_PREFIX, products }
}

async function main() {
  requireWritesAllowed()
  const health = await call('/health')
  if (health?.ok !== true) throw new Error(`${API} no es la API de rappi-ia`)
  console.log(`Muestra desde ${API} (${health.documentos} documentos)`)
  const meta = JSON.parse(execFileSync(PYTHON, [`${ROOT}scripts/demo-snapshot-meta.py`], { encoding: 'utf8' }))
  const { user_id: userId, token } = await session()
  try {
    const snapshot = { version: 1, created: new Date().toISOString(), documents: health.documentos, meta }
    console.log('  catálogo…')
    snapshot.catalog = await catalog(token)
    console.log('  búsquedas, preguntas y ofertas…')
    Object.assign(snapshot, await agent(token, userId))
    console.log('  complementos…')
    snapshot.complements = await complements(token, productsIn(snapshot))
    console.log('  escalera…')
    Object.assign(snapshot.toTry, await ladder(snapshot))
    const out = intern(snapshot)
    // Una fila por producto: el archivo queda legible en un diff sin ser una sola línea gigante.
    const { products, ...rest } = out
    const text = JSON.stringify(rest).replace(
      /}$/,
      `,"products":[\n${products.map((p) => JSON.stringify(p)).join(',\n')}\n]}`,
    )
    writeFileSync(OUT, `${text}\n`)
    const kb = Math.round(JSON.stringify(out).length / 1024)
    console.log(`Listo: ${OUT} (${out.products.length} productos, ${kb} kB)`)
  } finally {
    await call(`/profile/${userId}`, { method: 'DELETE', token })
  }
}

main().catch((error) => {
  console.error(error)
  process.exitCode = 1
})

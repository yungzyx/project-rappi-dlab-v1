// La muestra del catálogo (snapshot.json, la escribe `npm run demo:snapshot`) lista para responder: los productos
// vuelven a ser objetos como los de la API y las respuestas grabadas los llevan en su lugar.

/** Arma la muestra a partir del JSON grabado: `{ ...respuestas, pool, byEntity }`. */
export function decodeSnapshot(raw) {
  const { products: rows, productFields: fields, imgPrefix, ...rest } = raw
  const pool = rows.map((row) => {
    const p = Object.fromEntries(fields.map((field, i) => [field, row[i]]))
    if (p.img?.startsWith('~')) p.img = `${imgPrefix}${p.img.slice(1)}`
    return { id: `${p.entity_type === 'menu_item' ? 'menu' : 'cat'}-${p.entity_id}`, ...p }
  })
  const revive = (value) => {
    if (Array.isArray(value)) return value.map(revive)
    if (!value || typeof value !== 'object') return value
    if ('$p' in value) return pool[value.$p]
    return Object.fromEntries(Object.entries(value).map(([key, v]) => [key, revive(v)]))
  }
  const byEntity = new Map()
  for (const p of pool) {
    const key = entityKey(p.entity_type, p.entity_id)
    if (!byEntity.has(key)) byEntity.set(key, p)
  }
  return { ...revive(rest), pool, byEntity }
}

export const entityKey = (type, id) => `${type === 'menu_item' ? 'menu_item' : 'catalog_item'}:${id}`

// La muestra no se sube a git (son datos descargados del catálogo): la escribe `npm run demo:snapshot`. Con un glob,
// que no falla si el archivo no está, el build normal y los tests no la necesitan.
const SNAPSHOT = import.meta.glob('./snapshot.json', { import: 'default' })
let loaded = null

/** La muestra de la demo (se arma una sola vez, al primer uso). */
export async function loadSnapshot() {
  const load = SNAPSHOT['./snapshot.json']
  if (!load) throw new Error('Falta src/api/offline/snapshot.json: corre `npm run demo:snapshot` (ver README).')
  loaded ??= load().then(decodeSnapshot)
  return loaded
}

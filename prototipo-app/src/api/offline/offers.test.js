import { describe, expect, test } from 'vitest'
import { makeOffer, offerableProduct } from './offers'
import { decodeSnapshot } from './snapshot'
import { CONCEPTS, META, product, recordedStep } from './testMeta'

const NOW = Date.UTC(2026, 9, 17, 15)
let n = 0
const order = (vertical, lines = [], mode = 'propuesta') => ({
  order_id: `o-${(n += 1)}`,
  ts: NOW - 60_000,
  vertical,
  mode,
  lines,
})
const line = (p) => ({
  entity_type: p.entity_type,
  entity_id: p.entity_id,
  concept_id: p.concept,
  store_id: p.store_id,
  qty: 1,
})
const state = ({ orders = [], events = [] } = {}) => ({ userId: 'proto-test', orders, events })
const ALL = ['restaurantes', 'turbo', 'supermercado', 'conveniencia', 'mall', 'chocolateria']

const coffee = product(1, { name: 'Café molido 250 g' })
const cookies = product(2, { name: 'Galletas de vainilla', concept: 'galletas', vertical: 'conveniencia' })
const turboSnack = product(3, { name: 'Galletas Turbo', concept: 'galletas', vertical: 'turbo' })
const beer = product(4, { name: 'Cerveza lata', concept: 'cerveza', vertical: 'licores', age_restricted: true })

function snapshotWith(fields = {}) {
  const pool = [coffee, cookies, turboSnack, beer]
  return {
    meta: META,
    pool,
    byEntity: new Map(pool.map((p) => [`${p.entity_type}:${p.entity_id}`, p])),
    toTry: {
      usual: { ...recordedStep('supermercado', [coffee]), reason: { text: '', basis: [] } },
      turbo: recordedStep('turbo', [turboSnack]),
      supermercado: recordedStep('supermercado', [coffee]),
    },
    complements: {
      cafe: {
        moment: 'carrito',
        text: 'Para acompañar café: galletas, en Express.',
        products: [cookies],
        vertical: 'conveniencia',
        prototype_vertical: 'express',
        reason: { concept: 'galletas', from_concept: 'cafe', text: 'Porque llevas ☕ café.', basis: [] },
        actions: [],
      },
    },
    planOffers: {},
    noResult: {},
    ...fields,
  }
}
const offer = (moment, s, context = {}, snapshot = snapshotWith()) => makeOffer(snapshot, s, NOW, { moment, context })

describe('guardias (offers/guards.py)', () => {
  test('nunca +18, Farmacia, Licores, conceptos que no se ofrecen ni nombres que dicen alcohol o bebé', () => {
    expect(offerableProduct(coffee, CONCEPTS)).toBe(true)
    expect(offerableProduct({ ...coffee, age_restricted: true }, CONCEPTS)).toBe(false)
    expect(offerableProduct({ ...coffee, vertical: 'farmacia' }, CONCEPTS)).toBe(false)
    expect(offerableProduct({ ...coffee, vertical: 'licores' }, CONCEPTS)).toBe(false)
    expect(offerableProduct({ ...coffee, concept: 'analgesicos' }, CONCEPTS)).toBe(false)
    expect(offerableProduct({ ...coffee, concept: 'panales' }, CONCEPTS)).toBe(false)
    expect(offerableProduct({ ...coffee, name: 'Soju uva verde' }, CONCEPTS)).toBe(false)
    expect(offerableProduct({ ...coffee, name: 'Galletas de Vino' }, CONCEPTS)).toBe(false)
    expect(offerableProduct({ ...coffee, name: 'Juguete para Bebés', concept: 'juguetes' }, CONCEPTS)).toBe(false)
    // Palabra entera: «ron» no está en «ronda», ni «gin» en «ginger».
    expect(offerableProduct({ ...coffee, name: 'Galletas Ronda ginger' }, CONCEPTS)).toBe(true)
  })

  test('una oferta grabada pierde los productos que no pasan las guardias; sin ninguno, no se ofrece nada', () => {
    const snapshot = snapshotWith({ toTry: { turbo: recordedStep('turbo', [beer, turboSnack]) } })
    const made = offer('vertical_por_probar', state({ orders: [order('restaurantes')] }), {}, snapshot)
    expect(made.products).toEqual([turboSnack])
    const empty = snapshotWith({ toTry: { turbo: recordedStep('turbo', [beer]) } })
    expect(offer('vertical_por_probar', state({ orders: [order('restaurantes')] }), {}, empty)).toBeNull()
  })
})

describe('vertical_por_probar', () => {
  test('sin pedidos: la de siempre (el súper), con «Aún no pides en…» y su basis', () => {
    const made = offer('vertical_por_probar', state())
    expect(made).toMatchObject({
      vertical: 'supermercado',
      text: 'Aún no pides en el súper: mira estas ofertas.',
      reason: {
        text: 'Porque aún no pides en el súper.',
        basis: [{ kind: 'sin_pedidos', id: 'supermercado', source: 'contexto' }],
      },
    })
  })

  test('la oferta grabada del paso lleva primero la combinación de esta persona', () => {
    const made = offer('vertical_por_probar', state({ orders: [order('restaurantes')] }))
    expect(made.vertical).toBe('turbo')
    expect(made.reason.basis).toEqual([
      { kind: 'combinacion', id: 'restaurantes→restaurantes+turbo', source: 'rappi' },
      { kind: 'lo_mas_pedido', id: 'turbo', source: 'poblacion:synthetic' },
    ])
  })

  test('con todo el catálogo: «¿Conoces RappiFavor?», sin productos y con una acción que lo abre', () => {
    const made = offer('vertical_por_probar', state({ orders: ALL.map((v) => order(v)) }))
    expect(made).toMatchObject({
      text: '¿Conoces RappiFavor? Un Rappitendero lleva lo que necesites.',
      products: [],
      vertical: null,
      reason: { text: 'Porque ya pides en 6 verticales: RappiFavor te ayuda con lo que no está en la app.' },
      actions: [{ label: 'Abrir RappiFavor', route: ['favor'], service: 'rappifavor' }],
    })
    expect(made.reason.basis[0]).toMatchObject({ kind: 'combinacion', source: 'rappi+supuesto' })
    expect(made.reason.basis[0].id).not.toMatch(/farmacia|licores/)
  })
})

describe('recompra', () => {
  test('un concepto en dos pedidos: «¿Repetimos…?» con el último producto comprado', () => {
    const s = state({ orders: [order('supermercado', [line(coffee)]), order('supermercado', [line(coffee)])] })
    const made = offer('recompra', s)
    expect(made).toMatchObject({
      moment: 'recompra',
      text: '¿Repetimos café? Lo pediste 2 veces.',
      products: [coffee],
      reason: { concept: 'cafe', basis: [{ kind: 'recompra', id: 'cafe', source: 'pedidos' }] },
      actions: [{ label: 'Ver producto', route: ['grocery'], store_id: 1 }],
    })
  })

  test('un pedido no basta; el alcohol y los pedidos de «Rappi hoy» nunca se repiten', () => {
    expect(offer('recompra', state({ orders: [order('supermercado', [line(coffee)])] }))).toBeNull()
    const beers = [order('licores', [line(beer)]), order('licores', [line(beer)])]
    expect(offer('recompra', state({ orders: beers }))).toBeNull()
    const today = [order('supermercado', [line(coffee)], 'actual'), order('supermercado', [line(coffee)], 'actual')]
    expect(offer('recompra', state({ orders: today }))).toBeNull()
  })
})

describe('complementos', () => {
  const entity = (p) => ({ entity_type: p.entity_type, entity_id: p.entity_id })

  test('carrito: el complemento grabado del concepto del producto', () => {
    const made = offer('carrito', state(), { product: entity(coffee) })
    expect(made).toMatchObject({ moment: 'carrito', products: [cookies], reason: { concept: 'galletas' } })
  })

  test('checkout y proximo_pedido cambian el texto; lo que ya está en el carro no se ofrece', () => {
    const checkout = offer('checkout', state(), { cart: [entity(coffee)] })
    expect(checkout.text).toBe('Para completar lo que llevas: galletas, en Express.')
    const next = offer('proximo_pedido', state(), { items: [entity(coffee)] })
    expect(next).toMatchObject({
      text: 'Para tu próximo pedido: galletas, en Express.',
      reason: { text: 'Porque pediste ☕ café.', basis: [{ kind: 'pedido', id: 'cafe', source: 'contexto' }] },
    })
    expect(offer('checkout', state(), { cart: [entity(coffee), entity(cookies)] })).toBeNull()
  })
})

test('decodeSnapshot arma los productos desde sus filas y los vuelve a poner en las respuestas', () => {
  const raw = {
    productFields: ['entity_type', 'entity_id', 'name', 'img'],
    imgPrefix: 'https://images.rappi.cl/products/',
    products: [['catalog_item', '7', 'Café', '~a.png']],
    search: { cafe: { groups: [{ products: [{ $p: 0 }] }] } },
  }
  const snapshot = decodeSnapshot(raw)
  expect(snapshot.search.cafe.groups[0].products[0]).toEqual({
    id: 'cat-7',
    entity_type: 'catalog_item',
    entity_id: '7',
    name: 'Café',
    img: 'https://images.rappi.cl/products/a.png',
  })
  expect(snapshot.byEntity.get('catalog_item:7').name).toBe('Café')
})

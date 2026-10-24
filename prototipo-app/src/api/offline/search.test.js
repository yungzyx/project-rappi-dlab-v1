import { describe, expect, test } from 'vitest'
import { ask, detectConcepts, matchProducts, namesQuery, search } from './search'
import { META, product } from './testMeta'

const coffee = product(1, { name: 'Café molido 250 g' })
const coffeeCookies = product(2, { name: 'Galletas sabor café', concept: 'galletas' })
const expressCookies = product(3, { name: 'Galletas de café', concept: 'galletas', vertical: 'conveniencia' })
const honey = product(4, {
  name: 'Panal de miel',
  concept: null,
  entity_type: 'menu_item',
  vertical: 'restaurantes',
})
const beer = product(5, { name: 'Cerveza lata', concept: 'cerveza', vertical: 'licores', age_restricted: true })
const pharmacyCookies = product(6, { name: 'Galletas sin azúcar', concept: 'galletas', vertical: 'farmacia' })
const teddy = product(7, { name: 'Peluche oso', concept: 'juguetes', vertical: 'mall' })
const pool = [coffee, coffeeCookies, expressCookies, honey, beer, pharmacyCookies, teddy]
const HELP = { text: 'Puedo buscarte lo que quieras: prueba con «sushi» o «algo para la once».', products: [] }
const snapshot = {
  meta: META,
  pool,
  byEntity: new Map(pool.map((p) => [`${p.entity_type}:${p.entity_id}`, p])),
  search: {},
  ask: {},
  complements: {},
  help: HELP,
}

describe('los conceptos de una consulta (concepts/matcher.py)', () => {
  test('por sus keywords, en singular o plural, sin las que lo impiden', () => {
    expect(detectConcepts(META, 'Quiero un café')).toEqual(['cafe'])
    expect(detectConcepts(META, 'una galleta')).toEqual(['galletas'])
    expect(detectConcepts(META, 'taza para café')).toEqual([])
  })

  test('una palabra que solo sirve para pedir algo cuenta si es todo el pedido', () => {
    expect(detectConcepts(META, 'hola, chela')).toEqual(['cerveza'])
    expect(detectConcepts(META, 'chela helada')).toEqual([])
  })

  test('el nombre dice lo pedido con palabras enteras y la ñ: «pañales» no es «panal»', () => {
    expect(namesQuery(META, 'Galletas de café', 'galleta')).toBe(true)
    expect(namesQuery(META, 'Panal de miel', 'pañales')).toBe(false)
  })
})

describe('el foco de la búsqueda (agent/tools.py: _focus)', () => {
  test('donde la vertical tiene el concepto, solo el concepto; donde no, lo que lo dice en el nombre', () => {
    const found = matchProducts(snapshot, 'café')
    expect(found).toContain(coffee)
    expect(found).not.toContain(coffeeCookies) // el súper vende café: unas galletas «sabor café» no son café
    expect(found).toContain(expressCookies) // Express no tiene café: muestra lo que dice «café»
  })

  test('«pañales» no trae el postre con «panal»', () => {
    expect(matchProducts(snapshot, 'pañales')).not.toContain(honey)
    expect(search(snapshot, new URLSearchParams('q=pañales')).groups).toEqual([])
  })
})

describe('«qué me recomiendas» (rappi_agent.py: _recommend)', () => {
  const recommend = (interests, body = {}) =>
    ask(snapshot, { message: '¿Qué me recomiendas?', mode: 'propuesta', ...body }, { interests, userId: 'proto-1' })

  test('busca su interés en la vertical más típica y lo dice', () => {
    const reply = recommend(['cafe'])
    expect(reply.text).toBe('Por tu interés en ☕ café 😉 Mira lo que encontré de «café» en el súper.')
    expect(reply.products).toEqual([coffee])
    expect(reply.vertical).toBe('supermercado')
  })

  test('desde Farmacia no busca ahí: va a una vertical que Mochi propone', () => {
    const reply = recommend(['galletas'], { vertical: 'pharmacy' })
    expect(reply.vertical).not.toBe('farmacia')
    expect(reply.products).not.toContain(pharmacyCookies)
  })

  test('si nombra algo, busca eso: «¿me recomiendas un café?» no es «qué me recomiendas»', () => {
    const reply = recommend(['juguetes'], { message: '¿Me recomiendas un café?' })
    expect(reply.text).toBe('Mira lo que encontré de «¿Me recomiendas un café?» en el súper.')
    expect(reply.products).toEqual([coffee])
  })

  test('prueba hasta tres intereses', () => {
    // Tres intereses que se pueden ofrecer pero no tienen productos en la muestra: el cuarto ya no se prueba.
    const empty = Object.fromEntries(['a', 'b', 'c'].map((id) => [id, { name: id, emoji: '·', offerable: true }]))
    const wider = { ...snapshot, meta: { ...META, concepts: { ...META.concepts, ...empty } } }
    const reply = (interests) =>
      ask(wider, { message: 'qué me recomiendas', mode: 'propuesta' }, { interests, userId: 'proto-1' })
    expect(reply(['a', 'b', 'cafe']).products).toEqual([coffee])
    expect(reply(['a', 'b', 'c', 'cafe'])).toBe(HELP)
  })

  test('sin productos que Mochi pueda ofrecer de un interés prueba el siguiente; sin nada, los ejemplos', () => {
    expect(recommend(['cerveza', 'juguetes']).text).toBe(
      'Por tu interés en 🧸 juguetes 😉 Mira lo que encontré de «juguetes» en Rappi Mall.',
    )
    expect(recommend(['cerveza'])).toBe(HELP)
    expect(recommend([])).toBe(HELP)
    expect(recommend(['cafe'], { mode: 'actual' })).toBe(HELP)
  })
})

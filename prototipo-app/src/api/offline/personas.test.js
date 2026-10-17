import { expect, test } from 'vitest'
import { homeVerticals, targetStep } from './motor'
import { ladderReadout, personaHistory, personas } from './personas'
import { profileOffer, tastesReply } from './tastes'
import { COMBOS, LABELS, META, product } from './testMeta'

const NOW = Date.UTC(2026, 9, 17, 15)
const VERTICALS = ['restaurantes', 'turbo', 'supermercado', 'conveniencia', 'mall', 'chocolateria', 'farmacia']
const sushi = product(9, {
  name: 'Roll de salmón',
  concept: 'sushi',
  vertical: 'restaurantes',
  entity_type: 'menu_item',
})
const snapshot = {
  meta: {
    ...META,
    concepts: { ...META.concepts, sushi: { name: 'Sushi', emoji: '🍣', group: 'comida', offerable: true } },
    profiles: { asiatico: { name: 'Amante de lo asiático', emoji: '🥢', main: true, concepts: ['sushi', 'asiatica'] } },
  },
  pool: VERTICALS.map((vertical, i) => product(i + 1, { vertical })),
  tastes: {
    asiatico: {
      gustos: { id: 'asiatico', nombre: 'Amante de lo asiático', emoji: '🥢', nivel: 'medio', principal: true },
      ladder: { moment: 'perfil', escalera: [] },
      seed: [sushi, sushi, sushi],
    },
  },
}
const persona = (id) => personas(snapshot).find((p) => p.id === id)
const stateOf = (id) => ({ userId: 'proto-test', ...personaHistory(snapshot, persona(id), NOW) })

test('las personas de la escalera están donde dice su nombre, y la línea del panel lo muestra', () => {
  expect(targetStep(COMBOS, stateOf('restaurantes'), NOW).vertical).toBe('turbo')
  expect(targetStep(COMBOS, stateOf('rest-turbo'), NOW).vertical).toBe('supermercado')
  expect(targetStep(COMBOS, stateOf('todo'), NOW).vertical).toBe('favor')
  expect(ladderReadout(snapshot, stateOf('rest-turbo'), NOW)).toBe('Hoy: restaurantes+turbo → siguiente: supermercado')
  expect(ladderReadout(snapshot, stateOf('todo'), NOW)).toMatch(/→ siguiente: RappiFavor$/)
  expect(ladderReadout(snapshot, stateOf('nueva'), NOW)).toMatch(/^Hoy: sin pedidos/)
})

test('«Usa mucho Farmacia» la sube primera en la Home y Mochi igual nunca la ofrece', () => {
  const state = stateOf('farmacia')
  expect(homeVerticals(state, NOW, LABELS).order[0].id).toBe('farmacia')
  expect(targetStep(COMBOS, state, NOW).vertical).toBe('turbo')
})

test('una persona de gusto activa su perfil (tres pedidos de sus conceptos) y recibe su escalera grabada', () => {
  const taste = persona('gusto-asiatico')
  expect(taste.label).toBe('🥢 Amante de lo asiático')
  const state = stateOf('gusto-asiatico')
  expect(tastesReply(snapshot, state).perfiles.map((p) => p.id)).toEqual(['asiatico'])
  expect(profileOffer(snapshot, state)).toEqual({ moment: 'perfil', escalera: [] })
  const two = { ...state, orders: state.orders.slice(1) }
  expect(tastesReply(snapshot, two).perfiles).toEqual([])
  expect(profileOffer(snapshot, two)).toBeNull()
})

test('una persona de la escalera pide un concepto distinto en cada vertical (sin «¿Repetimos?» por accidente)', () => {
  // El primer producto de Rappi Mall es del mismo concepto que el de Restaurantes: se elige el siguiente.
  const pool = VERTICALS.map((vertical, i) => product(i + 1, { vertical, concept: `c${i}` }))
  const clash = product(20, { vertical: 'mall', concept: 'c0' })
  const withClash = { ...snapshot, pool: [clash, ...pool] }
  const all = personas(withClash).find((p) => p.id === 'todo')
  const concepts = personaHistory(withClash, all, NOW).orders.map((o) => o.lines[0].concept_id)
  expect(concepts).toEqual(['c0', 'c1', 'c2', 'c3', 'c4', 'c5'])
})

import { describe, expect, test } from 'vitest'
import { currentFine, fineExpectation, homeVerticals, stepSignal, targetStep } from './motor'
import { COMBOS, LABELS } from './testMeta'

const NOW = Date.UTC(2026, 9, 17, 15)
const MIN = 60_000
let n = 0
const order = (vertical, { mode = 'propuesta', ago = 0 } = {}) => ({
  order_id: `o-${(n += 1)}`,
  ts: NOW - ago,
  vertical,
  mode,
  lines: [],
})
const open = (vertical, { mode, ago = MIN } = {}) => ({
  type: 'vertical_open',
  ts: NOW - ago,
  vertical,
  payload: mode ? { mode } : {},
})
const serviceOpened = (servicio) => ({ type: 'service_opened', ts: NOW - MIN, vertical: null, payload: { servicio } })
const state = ({ orders = [], events = [] } = {}) => ({ userId: 'proto-test', orders, events })
const home = (s) => homeVerticals(s, NOW, LABELS)
const ids = (reply) => reply.order.map((entry) => entry.id)
const step = (s) => targetStep(COMBOS, s, NOW)

describe('Home ordering (motor/home.py)', () => {
  test('without history keeps the fixed order, with no reason and not personalized', () => {
    const reply = home(state())
    expect(reply.fixed).toEqual(['restaurantes', 'turbo'])
    expect(ids(reply)).toEqual(['supermercado', 'farmacia', 'mall', 'licores', 'conveniencia', 'chocolateria'])
    expect(reply.personalized).toBe(false)
    expect(reply.order.every((entry) => entry.reason === null)).toBe(true)
  })

  test('taps on Farmacia move it first among the small tiles, with «Porque entras seguido a…»', () => {
    const reply = home(state({ events: [open('farmacia'), open('farmacia'), open('mall')] }))
    expect(ids(reply)).toEqual(['farmacia', 'mall', 'supermercado', 'licores', 'conveniencia', 'chocolateria'])
    expect(reply.personalized).toBe(true)
    expect(reply.order[0].reason).toEqual({
      text: 'Porque entras seguido a farmacia.',
      basis: [{ kind: 'afinidad_vertical', id: 'farmacia', source: 'eventos' }],
    })
    expect(reply.order[1].reason).toBeNull()
  })

  test('orders say «Porque pides seguido en…» and contract the article', () => {
    const reply = home(state({ orders: [order('supermercado')] }))
    expect(reply.order[0]).toMatchObject({ id: 'supermercado', reason: { text: 'Porque pides seguido en el súper.' } })
    const visits = home(state({ events: [open('supermercado')] }))
    expect(visits.order[0].reason.text).toBe('Porque entras seguido al súper.')
  })

  test('Restaurantes and Turbo stay fixed: using them does not move the small tiles', () => {
    const reply = home(state({ orders: [order('restaurantes'), order('turbo')], events: [open('turbo')] }))
    expect(reply.fixed).toEqual(['restaurantes', 'turbo'])
    expect(ids(reply)).toEqual(['supermercado', 'farmacia', 'mall', 'licores', 'conveniencia', 'chocolateria'])
    expect(reply.personalized).toBe(false)
  })

  test('«Rappi hoy» taps and orders do not teach', () => {
    const reply = home(
      state({
        orders: [order('chocolateria', { mode: 'actual' })],
        events: [open('chocolateria', { mode: 'actual' })],
      }),
    )
    expect(reply.personalized).toBe(false)
    expect(ids(reply)[0]).toBe('supermercado')
  })

  test('signals older than 180 days do not count', () => {
    const reply = home(state({ events: [open('mall', { ago: 181 * 86_400_000 })] }))
    expect(reply.personalized).toBe(false)
  })
})

describe('the fine ladder (motor/combos.py, predict.py)', () => {
  test('restaurantes → turbo', () => {
    const s = state({ orders: [order('restaurantes')] })
    expect(step(s)).toMatchObject({ vertical: 'turbo', current: 'restaurantes', target: 'restaurantes+turbo' })
    expect(stepSignal(COMBOS, step(s))).toEqual({
      kind: 'combinacion',
      id: 'restaurantes→restaurantes+turbo',
      source: 'rappi',
    })
  })

  test('turbo → restaurantes', () => {
    expect(step(state({ orders: [order('turbo')] })).vertical).toBe('restaurantes')
  })

  test('restaurantes + turbo → supermercado (the first retail vertical, by its tie-break order)', () => {
    const s = state({ orders: [order('restaurantes'), order('turbo')] })
    expect(step(s)).toMatchObject({ vertical: 'supermercado', target: 'restaurantes+turbo+supermercado' })
  })

  test('the person’s own use breaks the tie inside retail', () => {
    const s = state({ orders: [order('restaurantes'), order('turbo')], events: [open('chocolateria')] })
    expect(step(s).vertical).toBe('chocolateria')
  })

  test('within a group the diminishing assumption applies and the basis says so', () => {
    const s = state({ orders: [order('restaurantes'), order('turbo'), order('supermercado')] })
    const next = step(s)
    expect(next.vertical).toBe('mall') // sin afinidad, el orden de siempre desempata (mall antes que Express)
    expect(stepSignal(COMBOS, next).source).toBe('rappi+supuesto')
  })

  test('all the catalog → RappiFavor → RappiTravel, then nothing', () => {
    const all = ['restaurantes', 'turbo', 'supermercado', 'conveniencia', 'mall', 'chocolateria'].map((v) => order(v))
    expect(step(state({ orders: all })).vertical).toBe('favor')
    expect(step(state({ orders: all, events: [serviceOpened('rappifavor')] })).vertical).toBe('travel')
    expect(step(state({ orders: all, events: [serviceOpened('rappifavor'), serviceOpened('rappitravel')] }))).toBeNull()
  })

  test('never Farmacia or Licores, even when they are the most used', () => {
    const events = Array.from({ length: 20 }, () => [open('farmacia'), open('licores')]).flat()
    const s = state({ orders: [order('restaurantes'), order('turbo')], events })
    expect(step(s).vertical).toBe('supermercado')
    const all = ['restaurantes', 'turbo', 'supermercado', 'conveniencia', 'mall', 'chocolateria'].map((v) => order(v))
    expect(step(state({ orders: all, events })).vertical).toBe('favor')
  })

  test('the basis never names Farmacia or Licores, though they count in the combination', () => {
    const s = state({ orders: [order('restaurantes'), order('farmacia'), order('licores')] })
    expect(currentFine(COMBOS, s, NOW)).toBe('restaurantes+farmacia+licores')
    expect(stepSignal(COMBOS, step(s)).id).toBe('restaurantes→restaurantes+turbo')
  })

  test('without orders there is no step; «Rappi hoy» orders and services opened there do not count', () => {
    expect(step(state())).toBeNull()
    expect(step(state({ orders: [order('restaurantes', { mode: 'actual' })] }))).toBeNull()
    const all = ['restaurantes', 'turbo', 'supermercado', 'conveniencia', 'mall', 'chocolateria'].map((v) => order(v))
    const opened = { ...serviceOpened('rappifavor'), payload: { servicio: 'rappifavor', mode: 'actual' } }
    expect(step(state({ orders: all, events: [opened] })).vertical).toBe('favor')
  })

  test('orders older than 30 days count only when there are none in 30 (90-day window)', () => {
    const DAY = 86_400_000
    const s = state({ orders: [order('turbo', { ago: 45 * DAY })] })
    expect(currentFine(COMBOS, s, NOW)).toBe('turbo')
    expect(currentFine(COMBOS, state({ orders: [order('turbo', { ago: 120 * DAY })] }), NOW)).toBe('ninguna')
  })

  test('expected retention matches the Rappi table and never reaches 1', () => {
    expect(fineExpectation(COMBOS, 'restaurantes+turbo')).toEqual([0.82, false])
    const [value, used] = fineExpectation(COMBOS, 'restaurantes+turbo+supermercado+conveniencia+favor')
    expect(value).toBeCloseTo(1 - 0.07 * 0.9 * 0.95, 10)
    expect(used).toBe(true)
    expect(fineExpectation(COMBOS, 'travel')).toEqual([null, false])
  })
})

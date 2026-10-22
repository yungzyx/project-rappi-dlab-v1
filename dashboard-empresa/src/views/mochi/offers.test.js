import { describe, expect, test } from 'vitest'
import { momentExtremes, momentLabel, offerTotals, suggestionTotals, topSuggestion } from './offers.js'

const moment = (momento, mostradas, aceptadas, aceptacion_pct = null) => ({
  momento,
  mostradas,
  aceptadas,
  aceptacion_pct,
})

describe('offers', () => {
  test('totals carry a rate only from 10 shown', () => {
    expect(offerTotals([moment('plan', 6, 1), moment('carrito', 3, 0)])).toEqual({ shown: 9, accepted: 1, rate: null })
    expect(offerTotals([moment('plan', 8, 1), moment('pregunta', 12, 3, 25)])).toEqual({
      shown: 20,
      accepted: 4,
      rate: 20,
    })
  })

  test('the best and worst moment ignore «sin momento» and moments without a rate', () => {
    const moments = [
      moment('plan', 68, 0, 0),
      moment('carrito', 7, 0),
      moment('pregunta', 26, 2, 7.7),
      moment('para_ti', 101, 2, 2),
      moment('sin_momento', 300, 90, 30),
    ]

    const { best, worst } = momentExtremes(moments)
    expect(best.momento).toBe('pregunta')
    expect(worst.momento).toBe('plan')
  })

  test('with a single rated moment there is no worst', () => {
    expect(momentExtremes([moment('plan', 20, 5, 25)])).toEqual({ best: moment('plan', 20, 5, 25), worst: null })
    expect(momentExtremes([moment('sin_momento', 20, 5, 25)])).toEqual({ best: null, worst: null })
  })

  test('moments have Spanish labels and unknown ones keep their code', () => {
    expect(momentLabel('checkout')).toBe('Antes de pagar')
    expect(momentLabel('volver')).toBe('Volver a pedir')
    expect(momentLabel('nuevo')).toBe('nuevo')
  })

  test('suggestion totals: acceptance over shown, conversion over accepted', () => {
    const rows = [
      { mostradas: 30, aceptadas: 6, convertidas: 3, aceptacion_pct: 20 },
      { mostradas: 10, aceptadas: 4, convertidas: 1, aceptacion_pct: 40 },
    ]

    expect(suggestionTotals(rows)).toEqual({
      shown: 40,
      accepted: 10,
      converted: 4,
      acceptRate: 25,
      convertRate: 40,
    })
    expect(suggestionTotals([]).acceptRate).toBeNull()
    // 40 mostradas pero 4 aceptadas: la conversión no tiene tasa
    expect(suggestionTotals([{ mostradas: 40, aceptadas: 4, convertidas: 2 }]).convertRate).toBeNull()
  })

  test('the top suggestion needs 10 shown', () => {
    const rows = [
      { concepto: 'A', mostradas: 9, aceptacion_pct: 90 },
      { concepto: 'B', mostradas: 40, aceptacion_pct: 30 },
      { concepto: 'C', mostradas: 12, aceptacion_pct: 35 },
    ]

    expect(topSuggestion(rows).concepto).toBe('C')
    expect(topSuggestion([])).toBeNull()
  })
})

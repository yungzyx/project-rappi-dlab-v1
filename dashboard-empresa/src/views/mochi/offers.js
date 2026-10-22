// Cuentas de las ofertas de Mochi (/analytics/offers, por momento) y de sus sugerencias entre verticales
// (/analytics/suggestions, por concepto y vertical). Aceptada: la oferta se agregó al carro.

/** Con menos mostradas que esto (una demo en vivo) un % no dice nada: se muestran solo las cuentas. */
export const MIN_SHOWN_FOR_RATE = 10

const MOMENTS = {
  plan: 'Plan',
  carrito: 'Carro',
  checkout: 'Antes de pagar',
  proximo_pedido: 'Próximo pedido',
  sin_resultado: 'Sin resultado',
  vertical_por_probar: 'Vertical por probar',
  recompra: 'Recompra',
  volver: 'Volver a pedir',
  perfil: 'Perfil de gusto',
  pregunta: 'Pregunta',
  para_ti: 'Para ti',
  sin_momento: 'Sin momento',
}

export const momentLabel = (moment) => MOMENTS[moment] ?? moment

const sum = (rows, key) => rows.reduce((total, row) => total + (row[key] ?? 0), 0)

// Una tasa necesita el mínimo en su denominador: con 4 aceptadas, «50% llega a pedido» no dice nada.
const rate = (part, whole) => (whole >= MIN_SHOWN_FOR_RATE ? (part * 100) / whole : null)

/** Totales de las ofertas: `{ shown, accepted, rate }` (`rate` null bajo el mínimo de mostradas). */
export function offerTotals(moments) {
  const shown = sum(moments, 'mostradas')
  const accepted = sum(moments, 'aceptadas')
  return { shown, accepted, rate: rate(accepted, shown) }
}

/**
 * El momento que más acepta y el que menos, entre los que tienen tasa (10 o más mostradas). «Sin momento» no cuenta:
 * no dice dónde se hizo la oferta. `{ best, worst }`, cada uno null si no hay; `worst` es null si es el mismo que `best`.
 */
export function momentExtremes(moments) {
  const rated = moments
    .filter((row) => row.momento !== 'sin_momento' && row.aceptacion_pct !== null && row.aceptacion_pct !== undefined)
    .sort((a, b) => b.aceptacion_pct - a.aceptacion_pct)
  const best = rated[0] ?? null
  const worst = rated.length > 1 ? rated.at(-1) : null
  return { best, worst }
}

/**
 * Totales de las sugerencias entre verticales: mostradas, aceptadas, convertidas y sus tasas (la aceptación sobre las
 * mostradas, la conversión sobre las aceptadas; null bajo el mínimo).
 */
export function suggestionTotals(rows) {
  const shown = sum(rows, 'mostradas')
  const accepted = sum(rows, 'aceptadas')
  const converted = sum(rows, 'convertidas')
  return {
    shown,
    accepted,
    converted,
    acceptRate: rate(accepted, shown),
    convertRate: rate(converted, accepted),
  }
}

/** La sugerencia (concepto y vertical) que más se acepta entre las que tienen tasa, o null. */
export function topSuggestion(rows) {
  return (
    rows
      .filter((row) => row.mostradas >= MIN_SHOWN_FOR_RATE && row.aceptacion_pct !== null)
      .sort((a, b) => b.aceptacion_pct - a.aceptacion_pct || b.mostradas - a.mostradas)[0] ?? null
  )
}

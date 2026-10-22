// El motor contra una regla simple: las filas de la evaluación por fechas (/analytics/motor → evaluacion).

const pct = (fraction) => (fraction === null || fraction === undefined ? null : fraction * 100)

/**
 * Lo que decide el motor contra una regla simple, en el tramo de prueba de su evaluación por fechas: el próximo
 * vertical (acierto en el primero), la compra cruzada (precisión en 3, la mezcla que usa Mochi contra lo más pedido) y
 * el paso de la escalera (las corridas anteriores a la escalera fina no lo traen).
 */
export function motorRows(evaluation) {
  const next = evaluation.proximo_vertical
  const cross = evaluation.compra_cruzada
  const rows = [
    {
      key: 'proximo',
      decides: 'Qué vertical proponer primero',
      metric: 'la primera que propone es una que la persona pidió',
      motor: pct(next.combinado.hit1),
      base: pct(next.orden_fijo.hit1),
      baseLabel: 'Orden fijo',
    },
    {
      key: 'cruzada',
      decides: 'Qué producto de otra vertical ofrecer',
      metric: 'de 3 ofrecidos, los que pidió después sin que se los sugirieran',
      motor: pct(cross.mezcla.precision3),
      base: pct(cross.lo_mas_pedido.precision3),
      baseLabel: 'Lo más pedido',
    },
  ]
  if (evaluation.paso) {
    rows.push({
      key: 'paso',
      decides: 'Qué vertical sumar a su combinación',
      metric: 'la vertical que propone es una que sumó',
      motor: pct(evaluation.paso.escalera),
      base: pct(evaluation.paso.mas_sumada),
      baseLabel: 'La que más se suma',
    })
  }
  return rows.map((row) => ({ ...row, gap: row.motor === null || row.base === null ? null : row.motor - row.base }))
}

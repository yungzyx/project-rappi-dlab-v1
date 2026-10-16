// La forma de `evaluacion` que guarda `rappi-ia motor` (motor/evaluate.py) con cifras inventadas: la simulación chica
// del contrato (8 semanas) no llega a los 84 días que pide la evaluación.
export const evaluation = {
  tramos: { entrenar_hasta: '2026-08-07', validar_hasta: '2026-09-04', probar_hasta: '2026-10-02' },
  pesos: { afinidad: 1, transicion: 0.5, popularidad: 0.1 },
  lambda_cruzada: 2,
  validacion: { personas: 480, ndcg_combinado: 0.8123, precision3_mezcla: 0.2 },
  proximo_vertical: {
    orden_fijo: { personas: 500, hit1: 0.2, hit3: 0.5, mrr: 0.4, ndcg: 0.5 },
    popularidad: { personas: 500, hit1: 0.3, hit3: 0.6, mrr: 0.45, ndcg: 0.55 },
    afinidad: { personas: 500, hit1: 0.5, hit3: 0.8, mrr: 0.65, ndcg: 0.72 },
    transicion: { personas: 500, hit1: 0.4, hit3: 0.7, mrr: 0.55, ndcg: 0.65 },
    combinado: { personas: 500, hit1: 0.6, hit3: 0.85, mrr: 0.72, ndcg: 0.8123 },
  },
  compra_cruzada: {
    personas: 420,
    precision3: 0.18,
    aciertos_sobre_3: 0.12,
    cobertura: 0.7,
    personas_con_prediccion: 294,
    lo_mas_pedido: {
      precision3: 0.1,
      aciertos_sobre_3: 0.1,
      cobertura: 1,
      personas_con_prediccion: 420,
      precision3_mismas_personas: 0.09,
    },
    mezcla: {
      precision3: 0.2,
      aciertos_sobre_3: 0.2,
      cobertura: 1,
      personas_con_prediccion: 420,
      precision3_mismas_personas: 0.21,
    },
  },
  recompra: { n: 64, compraron: 0.4, error_mediano_dias: 3, acierto_7_dias: 0.31 },
}

export const motorBody = (source, overrides = {}) => ({
  source,
  data: {
    pesos: evaluation.pesos,
    lambda_cruzada: evaluation.lambda_cruzada,
    evaluacion: evaluation,
    fecha: '2026-10-11T12:00:00+00:00',
    ...overrides,
  },
})

import { DataTable } from '../../components/DataTable.jsx'
import { EmptyState } from '../../components/States.jsx'
import { Icon } from '../../components/Icon.jsx'
import { formatDate, formatNumber, formatPct } from '../../lib/format.js'
import { plural } from '../../lib/labels.js'
import { SourceNote } from '../mvp/SourceNote.jsx'
import { Stats } from '../mvp/Stats.jsx'

const NEXT_VERTICAL_METHODS = [
  ['orden_fijo', 'Orden fijo'],
  ['popularidad', 'Popularidad'],
  ['afinidad', 'Solo afinidad'],
  ['transicion', 'Solo transiciones'],
  ['combinado', 'Combinado'],
]

const CROSS_SELL_METHODS = [
  ['reglas', 'Reglas aprendidas'],
  ['lo_mas_pedido', 'Lo más pedido'],
  ['mezcla', 'Mezcla'],
]

const fraction = (value) => formatPct(value === null ? null : value * 100)

const NEXT_VERTICAL_COLUMNS = [
  { key: 'metodo', header: 'Método', primary: true, render: (row) => row.label },
  { key: 'ndcg', header: 'nDCG@8', numeric: true, render: (row) => formatNumber(row.ndcg, 3) },
  { key: 'hit1', header: 'Acierto@1', numeric: true, render: (row) => fraction(row.hit1) },
]

const CROSS_SELL_COLUMNS = [
  { key: 'metodo', header: 'Método', primary: true, render: (row) => row.label },
  { key: 'precision3', header: 'Precisión@3', numeric: true, render: (row) => fraction(row.precision3) },
  { key: 'cobertura', header: 'Cobertura', numeric: true, render: (row) => fraction(row.cobertura) },
  {
    key: 'personas',
    header: 'Personas con recomendación',
    numeric: true,
    render: (row) => formatNumber(row.personas_con_prediccion),
  },
]

const REPEAT_COLUMNS = [
  { key: 'n', header: 'Predicciones que vencen', numeric: true, render: (row) => formatNumber(row.n) },
  { key: 'compraron', header: 'Compraron', numeric: true, render: (row) => fraction(row.compraron) },
  {
    key: 'error',
    header: 'Error mediano (días)',
    numeric: true,
    render: (row) => formatNumber(row.error_mediano_dias, 0),
  },
  { key: 'acierto', header: 'Acierto ±7 días', numeric: true, render: (row) => fraction(row.acierto_7_dias) },
]

// Los pesos y el λ son valores de una grilla (1, 0,5, 0,05…): se muestran tal cual, sin ceros de relleno.
const plain = (value) => String(value).replace('.', ',')

const weightsText = ({ afinidad, transicion, popularidad }) =>
  `Afinidad ${plain(afinidad)} · Transición ${plain(transicion)} · Popularidad ${plain(popularidad)}`

function Evaluation({ evaluation }) {
  const next = evaluation.proximo_vertical
  const cross = evaluation.compra_cruzada
  const warning = evaluation.validacion.aviso
  return (
    <>
      {warning && (
        <p className="table-warning status status--warn">
          <Icon name="warn" />
          {warning}
        </p>
      )}
      <h3 className="motor-title">Próximo vertical</h3>
      <DataTable
        caption="Próximo vertical por método"
        columns={NEXT_VERTICAL_COLUMNS}
        rows={NEXT_VERTICAL_METHODS.map(([key, label]) => ({ ...next[key], label }))}
        rowKey={(row) => row.label}
      />
      <p className="card-note">
        Prueba de 28 días sobre {formatNumber(next.combinado.personas)} {plural(next.combinado.personas, 'persona')} con
        pedidos antes y durante la prueba; lo relevante son los verticales que pidió. nDCG@8 mide el orden completo de
        los 8 verticales; Acierto@1, que el primero sea uno que pidió.
      </p>
      <h3 className="motor-title">Compra cruzada</h3>
      <DataTable
        caption="Compra cruzada por método"
        columns={CROSS_SELL_COLUMNS}
        rows={CROSS_SELL_METHODS.map(([key, label]) => ({ ...(key === 'reglas' ? cross : cross[key]), label }))}
        rowKey={(row) => row.label}
      />
      <p className="card-note">
        Precisión@3: de lo que se recomienda (hasta 3 por persona), la parte que la persona pidió después sin que se lo
        sugirieran. {formatNumber(cross.personas)} {plural(cross.personas, 'persona')} en la prueba.
      </p>
      <h3 className="motor-title">Recompra</h3>
      <DataTable caption="Recompra" columns={REPEAT_COLUMNS} rows={[evaluation.recompra]} rowKey={() => 'recompra'} />
      <p className="card-note">
        «Compraron»: la parte en que la persona volvió a comprar el concepto en la prueba. El error mediano es solo
        sobre esas; el acierto ±7 días cuenta como fallo a quien no volvió a comprar.
      </p>
    </>
  )
}

/** Los pesos y el λ en uso, la fecha de la corrida y la evaluación por fechas del motor (`null` si no hay corrida). */
export function MotorEvaluation({ data, source }) {
  if (!data) {
    return (
      <EmptyState title="El motor todavía no corrió">
        Aparece cuando corre el motor sobre los pedidos de esta fuente (rappi-ia motor).
      </EmptyState>
    )
  }
  const { pesos, lambda_cruzada: lambda, evaluacion: evaluation, fecha } = data
  return (
    <>
      <SourceNote source={source} />
      <Stats
        items={[
          { label: 'Pesos del próximo vertical', value: weightsText(pesos) },
          { label: 'Compra cruzada', value: `λ = ${plain(lambda)}` },
          { label: 'Última corrida', value: formatDate(fecha) },
        ]}
      />
      {evaluation ? (
        <Evaluation evaluation={evaluation} />
      ) : (
        <EmptyState title="Sin evaluación">
          La evaluación por fechas pide al menos 84 días de pedidos; mientras tanto el motor usa los pesos de arriba.
        </EmptyState>
      )}
      {source === 'synthetic' && (
        <p className="card-note">
          <strong>Sobre datos simulados la evaluación prueba la mecánica del motor, no el efecto.</strong>
        </p>
      )}
    </>
  )
}

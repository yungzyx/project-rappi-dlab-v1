import { DataTable } from '../../components/DataTable.jsx'
import { EmptyState } from '../../components/States.jsx'
import { formatCLP, formatNumber, formatPct } from '../../lib/format.js'
import { comboLabel } from '../../lib/labels.js'

const RAPPI_LABEL = 'Dato compartido por Rappi (cohortes ene–jun 2026)'
const MIN_RETENTION_MONTHS = 30

// La retención llega como fracción (0,82); `null` si la combinación propia no tiene 30 meses con el siguiente completo.
const retention = (row) => formatPct(row.retencion_m1 === null ? null : row.retencion_m1 * 100, 0)

const RAPPI_COLUMNS = [
  { key: 'combo', header: 'Combinación', primary: true, render: (row) => comboLabel(row.combo) },
  { key: 'usuarios', header: 'Usuarios', numeric: true, render: (row) => formatNumber(row.usuarios) },
  { key: 'pct_usuarios', header: '% usuarios', numeric: true, render: (row) => formatPct(row.pct_usuarios) },
  { key: 'pct_pedidos', header: '% pedidos', numeric: true, render: (row) => formatPct(row.pct_pedidos) },
  { key: 'pedidos', header: 'Pedidos/usuario', numeric: true, render: (row) => formatNumber(row.pedidos_por_usuario, 1) },
  { key: 'retencion', header: 'Retención M+1', numeric: true, render: retention },
  { key: 'gasto', header: 'Gasto/usuario (moneda de la fuente)', numeric: true, render: (row) => formatNumber(row.gasto_por_usuario) },
]

const OWN_COLUMNS = [
  { key: 'combo', header: 'Combinación', primary: true, render: (row) => comboLabel(row.combo) },
  { key: 'meses', header: 'Personas-mes', numeric: true, render: (row) => formatNumber(row.meses_usuario) },
  { key: 'pct_usuarios', header: '% personas', numeric: true, render: (row) => formatPct(row.pct_usuarios) },
  { key: 'pct_pedidos', header: '% pedidos', numeric: true, render: (row) => formatPct(row.pct_pedidos) },
  { key: 'pedidos', header: 'Pedidos/persona', numeric: true, render: (row) => formatNumber(row.pedidos_por_usuario, 1) },
  { key: 'retencion', header: 'Retención M+1', numeric: true, render: retention },
  { key: 'gasto', header: 'Gasto/persona', numeric: true, render: (row) => formatCLP(row.gasto_por_usuario) },
]

/**
 * La tabla de Rappi (dato compartido) junto a la misma tabla medida con los datos de la fuente, cada una con su
 * rótulo. Lado a lado en pantallas anchas y apiladas en las angostas. Es una correlación, no un efecto.
 */
export function ComboTables({ data }) {
  const { rappi, propio, nota } = data
  const total = { ...rappi.total, combo: 'total' }
  return (
    <div className="combos">
      <div className="combos-side">
        <h3>{RAPPI_LABEL}</h3>
        <DataTable
          caption="Combinaciones de verticales de Rappi"
          columns={RAPPI_COLUMNS}
          rows={[...rappi.filas, total]}
          rowKey={(row) => row.combo}
          rowClassName={(row) => (row.combo === 'total' ? 'is-group-start' : undefined)}
        />
        <p className="card-note">{rappi.nota}</p>
      </div>
      <div className="combos-side">
        <h3>Reproducida con datos propios</h3>
        <p className="card-note combos-label">
          <strong>{nota}</strong>
        </p>
        {propio.length ? (
          <>
            <DataTable
              caption="Combinaciones de verticales con datos propios"
              columns={OWN_COLUMNS}
              rows={propio}
              rowKey={(row) => row.combo}
            />
            <p className="card-note">
              Una persona cuenta una vez por cada mes con pedidos. La retención aparece desde {MIN_RETENTION_MONTHS}{' '}
              meses con el siguiente completo; antes, —. El gasto va en pesos.
            </p>
          </>
        ) : (
          <EmptyState title="Sin pedidos propios todavía">
            Se arma cuando el motor corre sobre pedidos de esta fuente (rappi-ia motor).
          </EmptyState>
        )}
      </div>
    </div>
  )
}

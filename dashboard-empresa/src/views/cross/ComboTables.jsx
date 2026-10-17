import { DataTable } from '../../components/DataTable.jsx'
import { EmptyState } from '../../components/States.jsx'
import { formatCLP, formatNumber, formatPct } from '../../lib/format.js'
import { comboLabel, fineComboLabel } from '../../lib/labels.js'

const RAPPI_LABEL = 'Dato compartido por Rappi (cohortes ene–jun 2026)'
const MIN_RETENTION_MONTHS = 30

// La retención llega como fracción (0,82); `null` si la combinación propia no tiene 30 meses con el siguiente completo.
const retention = (row) => formatPct(row.retencion_m1 === null ? null : row.retencion_m1 * 100, 0)

const RAPPI_COLUMNS = [
  { key: 'combo', header: 'Combinación', primary: true, render: (row) => comboLabel(row.combo) },
  { key: 'usuarios', header: 'Usuarios', numeric: true, render: (row) => formatNumber(row.usuarios) },
  { key: 'pct_usuarios', header: '% usuarios', numeric: true, render: (row) => formatPct(row.pct_usuarios) },
  { key: 'pct_pedidos', header: '% pedidos', numeric: true, render: (row) => formatPct(row.pct_pedidos) },
  {
    key: 'pedidos',
    header: 'Pedidos/usuario',
    numeric: true,
    render: (row) => formatNumber(row.pedidos_por_usuario, 1),
  },
  { key: 'retencion', header: 'Retención M+1', numeric: true, render: retention },
  {
    key: 'gasto',
    header: 'Gasto/usuario (moneda de la fuente)',
    numeric: true,
    render: (row) => formatNumber(row.gasto_por_usuario),
  },
]

const OWN_COLUMNS = [
  { key: 'combo', header: 'Combinación', primary: true, render: (row) => comboLabel(row.combo) },
  { key: 'meses', header: 'Personas-mes', numeric: true, render: (row) => formatNumber(row.meses_usuario) },
  { key: 'pct_usuarios', header: '% personas', numeric: true, render: (row) => formatPct(row.pct_usuarios) },
  { key: 'pct_pedidos', header: '% pedidos', numeric: true, render: (row) => formatPct(row.pct_pedidos) },
  {
    key: 'pedidos',
    header: 'Pedidos/persona',
    numeric: true,
    render: (row) => formatNumber(row.pedidos_por_usuario, 1),
  },
  { key: 'retencion', header: 'Retención M+1', numeric: true, render: retention },
  { key: 'gasto', header: 'Gasto/persona', numeric: true, render: (row) => formatCLP(row.gasto_por_usuario) },
]

// Las retenciones finas difieren en décimas (el supuesto quita 10 %, 5 %, 2,5 %… de lo que no vuelve): un decimal.
const fineRetention = (value) => formatPct(value === null ? null : value * 100, 1)

const FINE_COLUMNS = [
  { key: 'combo', header: 'Combinación fina', primary: true, render: (row) => fineComboLabel(row.combo) },
  { key: 'meses', header: 'Personas-mes', numeric: true, render: (row) => formatNumber(row.meses_usuario) },
  {
    key: 'retencion',
    header: 'Retención M+1 aprendida',
    numeric: true,
    render: (row) => fineRetention(row.retencion_m1),
  },
  {
    key: 'esperada',
    header: 'Esperada (Rappi + supuesto)',
    numeric: true,
    render: (row) => fineRetention(row.esperada),
  },
]

// 0,1 → "10%", 0,025 → "2,5%".
const share = (value) => formatPct(value * 100, Number.isInteger(value * 100) ? 0 : 1)

function FineCombos({ fino, supuesto, nota, source }) {
  const { reduccion_base: base, decaimiento: decay, servicio } = supuesto
  return (
    <div className="combos-side combos-fine">
      <h3>Combinaciones finas: vertical por vertical</h3>
      <p className="card-note combos-label">
        <strong>{nota}</strong>
      </p>
      <p className="card-note">
        Supuesto propio, no es dato de Rappi: dentro de un grupo, cada vertical extra reduce la parte que no vuelve (la
        2.ª un {share(base)}, la 3.ª un {share(base * decay)}, la 4.ª un {share(base * decay * decay)}…) y cada servicio
        usado (RappiFavor, RappiTravel), un {share(servicio)}. Parte de la retención de la tabla de Rappi de sus grupos
        y nunca llega a 100%. Con al menos {MIN_RETENTION_MONTHS} meses aprendidos de una combinación, lo aprendido solo
        corrige la diferencia dentro del grupo (pesa n / (n + 100)); el nivel lo pone la combinación gruesa. La escalera
        propone la vertical que más sube esa retención; Farmacia y Licores nunca.
      </p>
      {fino.length ? (
        <>
          <DataTable
            caption="Combinaciones finas con datos propios"
            columns={FINE_COLUMNS}
            rows={fino}
            rowKey={(row) => row.combo}
          />
          <p className="card-note">
            Las {fino.length} combinaciones finas más frecuentes. La aprendida aparece desde {MIN_RETENTION_MONTHS}{' '}
            meses con el siguiente completo; antes, —. La esperada no usa lo aprendido.
            {source === 'synthetic' &&
              ' En los simulados la aprendida sale del mismo supuesto con que se simulan: coinciden por construcción.'}
          </p>
        </>
      ) : (
        <EmptyState title="Sin combinaciones finas todavía">
          Se arman cuando el motor corre sobre pedidos de esta fuente (rappi-ia motor).
        </EmptyState>
      )}
    </div>
  )
}

/**
 * La tabla de Rappi (dato compartido) junto a la misma tabla medida con los datos de la fuente, cada una con su
 * rótulo. Lado a lado en pantallas anchas y apiladas en las angostas. Es una correlación, no un efecto. Debajo, las
 * combinaciones finas de la fuente con su retención aprendida y la esperada con el supuesto propio.
 */
export function ComboTables({ data, source }) {
  const { rappi, propio, fino, supuesto, nota } = data
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
      <FineCombos fino={fino} supuesto={supuesto} nota={nota} source={source} />
    </div>
  )
}

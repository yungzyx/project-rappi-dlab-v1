import { DataTable } from '../../components/DataTable.jsx'
import { EmptyState } from '../../components/States.jsx'
import { formatNumber } from '../../lib/format.js'
import { plural, verticalLabel } from '../../lib/labels.js'
import { Stats } from './Stats.jsx'

const COLUMNS = [
  { key: 'vertical', header: 'Vertical', primary: true, render: (row) => verticalLabel(row.vertical) },
  { key: 'personas', header: 'Personas', numeric: true, render: (row) => formatNumber(row.personas) },
  { key: 'toques', header: 'Toques', numeric: true, render: (row) => formatNumber(row.toques) },
]

/** Toques de los accesos de la Home por vertical (personas y toques). «Rappi hoy» no cuenta. */
export function HomeTaps({ data, source }) {
  const { personas, toques, verticales: rows } = data
  if (!toques) {
    if (source === 'synthetic') {
      return (
        <EmptyState title="Los datos simulados no incluyen toques de accesos">
          Solo el prototipo registra cuando alguien toca un vertical en la Home.
        </EmptyState>
      )
    }
    return (
      <EmptyState title="Todavía no hay toques de accesos">Aparecen cuando alguien toca un vertical en la Home.</EmptyState>
    )
  }
  return (
    <>
      <Stats
        items={[
          { label: 'Personas', value: `${formatNumber(personas)} ${plural(personas, 'persona')}` },
          { label: 'Toques', value: `${formatNumber(toques)} ${plural(toques, 'toque')}` },
        ]}
      />
      <DataTable
        caption="Accesos de la Home por vertical"
        columns={COLUMNS}
        rows={rows}
        rowKey={(row) => row.vertical}
      />
      <p className="card-note">De más a menos toques. «Rappi hoy» y los servicios sin catálogo no cuentan.</p>
    </>
  )
}

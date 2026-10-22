import { useState } from 'react'
import { DataTable } from '../../components/DataTable.jsx'
import { Meter } from '../../components/Meter.jsx'
import { EmptyState } from '../../components/States.jsx'
import { formatNumber, formatPct } from '../../lib/format.js'
import { verticalLabel } from '../../lib/labels.js'

const PREVIEW_ROWS = 8

/**
 * Sugerencias entre verticales (al preguntarle a Mochi y en «Para ti») por concepto y vertical: cuántas se mostraron,
 * qué parte se aceptó y cuántas llegaron a un pedido. Primero las más mostradas; el resto, a pedido.
 */
export function SuggestionRanking({ rows }) {
  const [expanded, setExpanded] = useState(false)
  if (!rows.length) {
    return (
      <EmptyState title="Sin sugerencias entre verticales que evaluar">
        Aparecen cuando Mochi sugiere un producto de otra vertical.
      </EmptyState>
    )
  }
  const sorted = [...rows].sort((a, b) => b.mostradas - a.mostradas)
  const columns = [
    {
      key: 'sugerencia',
      header: 'Sugerencia',
      primary: true,
      render: (row) => (
        <span className="cell-stack">
          <strong>{row.concepto}</strong>
          <span className="cell-sub">en {verticalLabel(row.vertical)}</span>
        </span>
      ),
    },
    { key: 'mostradas', header: 'Mostradas', numeric: true, render: (row) => formatNumber(row.mostradas) },
    {
      key: 'aceptacion',
      header: 'Aceptación',
      numeric: true,
      render: (row) => (
        <span className="cell-bar">
          {row.aceptacion_pct === null ? <span /> : <Meter value={row.aceptacion_pct} max={100} />}
          {formatPct(row.aceptacion_pct)}
        </span>
      ),
    },
    { key: 'convertidas', header: 'Llegaron a pedido', numeric: true, render: (row) => formatNumber(row.convertidas) },
  ]
  return (
    <>
      <DataTable
        caption="Sugerencias entre verticales"
        columns={columns}
        rows={expanded ? sorted : sorted.slice(0, PREVIEW_ROWS)}
        rowKey={(row) => `${row.concepto}-${row.vertical}`}
      />
      {sorted.length > PREVIEW_ROWS && (
        <div className="view-switch">
          <button type="button" className="text-button" aria-expanded={expanded} onClick={() => setExpanded(!expanded)}>
            {expanded ? `Ver solo las ${PREVIEW_ROWS} más mostradas` : `Ver las ${formatNumber(sorted.length)}`}
          </button>
        </div>
      )}
    </>
  )
}

import { EmptyState } from '../../components/States.jsx'
import { formatDate, formatNumber, formatPct } from '../../lib/format.js'
import { plural } from '../../lib/labels.js'
import { Stats } from './Stats.jsx'

const count = (n) => `${formatNumber(n)} ${plural(n, 'persona')}`

/**
 * «¿Volvemos a…?»: a cuántas personas les toca (pedían algo con ritmo y lo dejaron), por el tipo de su primera
 * invitación, y a cuántas la recompra, para comparar. Es quién califica, no a quién se le mostró. Con datos simulados
 * la estimación es del último día simulado (`dia`) y no es evidencia.
 */
export function WinbackReach({ data, source }) {
  const { dia, personas, califican, por_concepto: concept, por_vertical: vertical, recompra } = data
  const simulated = source === 'synthetic'
  return (
    <>
      {simulated && (
        <p className="card-note mvp-note">
          <strong>Simulado: no es evidencia.</strong> Estimación al {formatDate(dia)}, el último día de los pedidos
          simulados.
        </p>
      )}
      {!personas ? (
        <EmptyState title="Todavía no hay pedidos">Aparece cuando alguien pide en la app.</EmptyState>
      ) : (
        <>
          <Stats
            items={[
              { label: 'Con pedidos', value: count(personas) },
              { label: 'Califican', value: `${count(califican)} (${formatPct((100 * califican) / personas)})` },
              { label: 'Por un concepto', value: count(concept) },
              { label: 'Por una vertical', value: count(vertical) },
              { label: 'Les toca la recompra', value: count(recompra) },
            ]}
          />
          <p className="card-note">
            Califica quien dejó de pedir algo que pedía con ritmo: un concepto atrasado más de un intervalo (desde 14
            días) o una vertical sin pedidos en más de un mes mientras pide en otra, hasta 90 días. Nunca alcohol,
            Farmacia, bebé, salud ni conceptos sensibles. Es quién califica, no a quién se le mostró.
          </p>
        </>
      )}
    </>
  )
}

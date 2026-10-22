import { Async } from '../../components/Async.jsx'
import { Delta } from '../../components/Delta.jsx'
import { Icon } from '../../components/Icon.jsx'
import { ProvenanceBadge } from '../../components/ProvenanceBadge.jsx'
import { SourceNote } from '../../components/SourceNote.jsx'
import { formatPoints } from '../../lib/format.js'

/** Lo que dice una decisión (`decisions.js`): cifra, contexto, cambio y acción sugerida. */
export function DecisionBody({ decision }) {
  if (!decision) return <p className="decision-context">Sin datos suficientes en esta fuente.</p>
  const { figure, unit, context, delta, action } = decision
  return (
    <>
      <p className="decision-figure">
        <strong>{figure}</strong>
        <span>{unit}</span>
      </p>
      {delta && <Delta value={delta.value} format={formatPoints} goodWhen={delta.goodWhen} suffix={delta.suffix} />}
      <p className="decision-context">{context}</p>
      {action && (
        <p className="decision-action">
          <span>Acción sugerida</span>
          {action}
        </p>
      )}
    </>
  )
}

/**
 * Una pregunta de negocio del Resumen. La pregunta, la procedencia (con el rótulo del prototipo, si lo es) y el enlace
 * al detalle se ven mientras cargan los datos; el cuerpo (`children`) lee la API dentro de su propio <Async>, así un
 * bloque caído no tumba a los otros.
 */
export function DecisionCard({ id, question, badge, linkLabel, onOpen, children }) {
  return (
    <article className="decision" aria-labelledby={id}>
      <header className="decision-head">
        <h3 id={id}>{question}</h3>
        <ProvenanceBadge kind={badge} />
      </header>
      <SourceNote source={badge} />
      <div className="decision-body">
        <Async>{children}</Async>
      </div>
      <button type="button" className="text-button decision-link" onClick={onOpen}>
        {linkLabel}
        <Icon name="arrowRight" />
      </button>
    </article>
  )
}

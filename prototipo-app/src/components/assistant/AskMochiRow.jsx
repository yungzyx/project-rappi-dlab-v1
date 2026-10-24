import { AGENT_NAME } from '../../agent/name'
import Mascot from './Mascot'

/**
 * Primera fila del buscador con el agente mientras se escribe: le pregunta lo escrito a Mochi. Resaltada si parece una
 * pregunta (`question`): entonces Enter también pregunta. No le quita el foco al campo (el blur registraría la búsqueda).
 */
export default function AskMochiRow({ query, question = false, onAsk }) {
  return (
    <button
      type="button"
      className={`agent-ask-row tap${question ? ' is-question' : ''}`}
      aria-label={`Pregúntale a ${AGENT_NAME}: «${query}»`}
      onMouseDown={(e) => e.preventDefault()}
      onClick={onAsk}
    >
      <span className="agent-ask-mascot" aria-hidden="true">
        <Mascot size={34} />
      </span>
      <span className="agent-ask-text">
        <strong>Pregúntale a {AGENT_NAME}</strong>
        <span className="agent-ask-query">«{query}»</span>
      </span>
      <span className="agent-ask-go" aria-hidden="true">
        ›
      </span>
    </button>
  )
}

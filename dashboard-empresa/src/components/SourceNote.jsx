/**
 * Rótulo de las secciones con datos del prototipo: es el uso de pocas personas, nunca evidencia. Con datos simulados no
 * pinta nada: la insignia de la sección y el aviso fijo de arriba ya lo dicen.
 */
export function SourceNote({ source }) {
  if (source !== 'prototype') return null
  return (
    <p className="mvp-note">
      <strong>uso del MVP, pocas personas: no es evidencia</strong>
    </p>
  )
}

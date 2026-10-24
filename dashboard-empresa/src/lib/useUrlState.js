import { useEffect, useState } from 'react'

// La vista y la fuente viven en la URL (?vista=clientes&fuente=prototipo) para compartir un enlace exacto.
const SOURCE_PARAMS = { synthetic: 'simulados', prototype: 'prototipo' }

/** Las vistas de antes del rediseño (22-10-2026) abren la vista nueva que tiene su contenido. */
const LEGACY_VIEWS = {
  oportunidades: 'mochi',
  frecuencia: 'clientes',
  verticales: 'clientes',
  catalogo: 'mochi',
  mvp: 'mochi',
}

function readUrlState(search, viewIds) {
  const params = new URLSearchParams(search)
  const asked = params.get('vista')
  const requested = LEGACY_VIEWS[asked] ?? asked
  const view = viewIds.includes(requested) ? requested : viewIds[0]
  const source = params.get('fuente') === SOURCE_PARAMS.prototype ? 'prototype' : 'synthetic'
  return { view, source }
}

export function useUrlState(viewIds) {
  const [state, setState] = useState(() => readUrlState(window.location.search, viewIds))

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    params.set('vista', state.view)
    params.set('fuente', SOURCE_PARAMS[state.source])
    window.history.replaceState(null, '', `?${params}${window.location.hash}`)
  }, [state])

  return [state, setState]
}

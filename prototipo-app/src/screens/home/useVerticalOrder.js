import { useEffect, useRef, useState } from 'react'
import { homeVerticals } from '../../api/client'
import { userId } from '../../api/user'
import { useApi } from '../../api/useApi'
import { useEvents } from '../../state/EventsContext'
import { useProfile } from '../../state/ProfileContext'

/**
 * El orden de los 6 verticales de la Home del prototipo final, según lo que más usa la persona (`GET /profile/{id}/verticales`).
 * Pide al montar, cuando cambian las `resets` («Olvidar») y cada vez que la Home vuelve a estar arriba (`active`: queda
 * montada bajo las pantallas que se abren encima). Al volver, antes de pedir manda los eventos en cola (los toques a
 * los accesos), para que el orden ya los cuente. La respuesta de una petición anterior no pisa a la última, y mientras
 * llega la nueva se mantiene el orden que había (salvo tras «Olvidar», que no muestra el de antes).
 * Sin API (o con error) `order` es null: la Home queda en el orden fijo y sin el texto.
 */
export function useVerticalOrder(active = true) {
  const { resets } = useProfile()
  const events = useEvents()
  const [returns, setReturns] = useState(0)
  const wasActive = useRef(active)

  useEffect(() => {
    const back = active && !wasActive.current
    wasActive.current = active
    if (!back) return undefined
    let current = true
    ;(async () => {
      await events.flush()
      await events.settled() // un lote que ya había salido (el envío cada 5 s) también debe llegar antes
      if (current) setReturns((n) => n + 1)
    })()
    return () => {
      current = false
    }
  }, [active, events])

  // Demo sin conexión: el «Panel de la demo» cambia el historial y la Home vuelve a pedir su orden (en los demás builds
  // la condición se pliega y esto no existe).
  useEffect(() => {
    if (import.meta.env.VITE_OFFLINE_DEMO !== '1') return undefined
    const again = () => setReturns((n) => n + 1)
    window.addEventListener('rappi-demo-history', again)
    return () => window.removeEventListener('rappi-demo-history', again)
  }, [])

  const { data } = useApi(async () => ({ resets, reply: await homeVerticals(userId()) }), [resets, returns], {
    keepPrevious: true,
  })
  if (data?.resets !== resets || !data.reply?.order) return { order: null, personalized: false }
  return { order: data.reply.order.map((entry) => entry.id), personalized: data.reply.personalized === true }
}

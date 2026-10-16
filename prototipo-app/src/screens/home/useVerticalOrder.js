import { homeVerticals } from '../../api/client'
import { userId } from '../../api/user'
import { useApi } from '../../api/useApi'
import { useProfile } from '../../state/ProfileContext'

/**
 * El orden de los 6 verticales de la Home del prototipo final, según lo que más pide la persona (`GET /profile/{id}/verticales`).
 * Pide al montar y cuando cambian las `resets` («Olvidar»); la respuesta de una petición anterior no pisa a la última.
 * Sin API (o con error) `order` es null: la Home queda en el orden fijo y sin el texto.
 */
export function useVerticalOrder() {
  const { resets } = useProfile()
  const { data } = useApi(() => homeVerticals(userId()), [resets])
  if (!data?.order) return { order: null, personalized: false }
  return { order: data.order.map((entry) => entry.id), personalized: data.personalized === true }
}

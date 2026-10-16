import catRestaurants from '../assets/cat-restaurants.webp'
import catTurbo from '../assets/cat-turbo.webp'
import creditsCoin from '../assets/credits-coin.webp'
import chipGrocery from '../assets/chip-grocery.webp'
import chipPharmacy from '../assets/chip-pharmacy.webp'
import chipRetail from '../assets/chip-retail.webp'
import chipLiquor from '../assets/chip-liquor.webp'
import chipExpress from '../assets/chip-express.webp'
import chipChocolates from '../assets/chip-chocolates.webp'
import chipRappiTravel from '../assets/chip-rappitravel.webp'
import chipLoyalty from '../assets/chip-loyalty.webp'
import chipBenefitsPro from '../assets/chip-benefitspro.webp'
import chipRappiFavorOff from '../assets/chip-rappifavor-off.webp'
import bannerDescuentos from '../assets/banner-descuentos.webp'
import bannerCena from '../assets/banner-cena.webp'

export const CREDITS = {
  logo: creditsCoin,
  title: '$1.900 Credits',
  subtitle: 'in Todofarma Market',
  expiresInMinutes: 116,
}

export const MAIN_TILES = [
  { id: 'restaurants', label: 'Restaurants', img: catRestaurants, screen: 'restaurants', vertical: 'restaurantes' },
  { id: 'turbo', label: 'Turbo', img: catTurbo, screen: 'turbo', vertical: 'turbo' },
]

// RappiFavor aparece deshabilitado como en la app (la imagen trae el sello "Unavailable"); en el prototipo final se habilita
// con su pantalla (`proposalRoute`).
// `route` dice a qué pantalla lleva cada acceso (ver HomeFeed).
export const SHORTCUTS = [
  {
    id: 'grocery',
    label: 'Grocery',
    img: chipGrocery,
    vertical: 'supermercado',
    route: ['vertical', { id: 'grocery' }],
  },
  {
    id: 'pharmacy',
    label: 'Pharmacy',
    img: chipPharmacy,
    vertical: 'farmacia',
    route: ['vertical', { id: 'pharmacy' }],
  },
  { id: 'retail', label: 'Retail', img: chipRetail, vertical: 'mall', route: ['vertical', { id: 'retail' }] },
  { id: 'liquor', label: 'Liquor', img: chipLiquor, vertical: 'licores', route: ['vertical', { id: 'liquor' }] },
  {
    id: 'express',
    label: 'Express',
    img: chipExpress,
    vertical: 'conveniencia',
    route: ['vertical', { id: 'express' }],
  },
  {
    id: 'chocolates',
    label: 'Chocolates',
    img: chipChocolates,
    vertical: 'chocolateria',
    route: ['vertical', { id: 'chocolates' }],
  },
  { id: 'rappitravel', label: 'RappiTravel', img: chipRappiTravel, route: ['travel'] },
  { id: 'loyalty', label: 'Loyalty', img: chipLoyalty, route: ['loyalty'] },
  { id: 'benefitspro', label: 'Benefits Pro', img: chipBenefitsPro },
  {
    id: 'rappifavor',
    label: 'RappiFavor',
    img: chipRappiFavorOff,
    unavailable: true,
    proposalRoute: ['favor'],
    emoji: '🛵',
  },
]

// Cola fija de la fila en el prototipo final: tras los 6 verticales (en el orden del motor), siempre en este orden y
// con Loyalty y Benefits Pro al final.
export const FINAL_TAIL = ['rappitravel', 'rappifavor', 'loyalty', 'benefitspro']

/**
 * La fila de accesos en cada modo. «Rappi hoy» (`final: false`) es la réplica de la app: tal cual. En el prototipo final,
 * los 6 verticales en el orden del motor (`order`: códigos del backend; ignora los desconocidos y los que falten
 * van después en su orden fijo; sin `order`, el orden fijo) y luego `FINAL_TAIL`.
 */
export function orderShortcuts(shortcuts, order, { final }) {
  if (!final) return shortcuts
  const verticals = shortcuts.filter((item) => item.vertical)
  const first = [...new Set(order ?? [])]
    .map((code) => verticals.find((item) => item.vertical === code))
    .filter(Boolean)
  const rest = verticals.filter((item) => !first.includes(item))
  const tail = FINAL_TAIL.map((id) => shortcuts.find((item) => item.id === id)).filter(Boolean)
  return [...first, ...rest, ...tail]
}

// La app muestra 6 banners; en capturas y video solo se ven completos estos dos.
export const PROMOS = [
  { id: 'descuentos', label: 'Descuentos en restaurantes', img: bannerDescuentos, fit: 'top', route: ['restaurants'] },
  { id: 'cena', label: 'Cena con descuento', img: bannerCena, fit: 'cover', route: ['restaurants'] },
]
export const PROMO_START_INDEX = 1

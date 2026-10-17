import { useDemo } from '../state/DemoContext'
import { useProductSheet } from '../state/ProductSheetContext'
import './top-dishes.css'

const MIN_DISHES = 2

/**
 * Lo más pedido de un restaurante bajo su tarjeta (`product.topDishes` de la API: `{ source, label, dishes }`), con el
 * rótulo que trae la API, que dice de dónde sale («según su menú en Rappi»). Solo en el prototipo final y con 2 platos
 * o más. Tocar un plato abre su hoja (de ahí se agrega al carro); con `onOpenStore`, la hoja ofrece «Ver tienda».
 * `compact` apila nombre y precio (la tarjeta angosta de las respuestas del agente).
 */
export default function TopDishes({ topDishes, onOpenStore, compact = false }) {
  const final = useDemo()?.isFinal === true
  const sheet = useProductSheet()
  if (!final || !topDishes || topDishes.dishes.length < MIN_DISHES) return null
  return (
    <div className={compact ? 'top-dishes top-dishes--compact' : 'top-dishes'}>
      <p className="top-dishes-label">{topDishes.label}</p>
      <ul className="top-dishes-list">
        {topDishes.dishes.map((dish) => (
          <li key={dish.id}>
            <button
              type="button"
              className="top-dishes-dish tap"
              onClick={() => sheet.open(dish, { onOpenStore: onOpenStore ? () => onOpenStore(dish) : undefined })}
            >
              <span className="top-dishes-name">{dish.name}</span>
              <b>{dish.price}</b>
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}

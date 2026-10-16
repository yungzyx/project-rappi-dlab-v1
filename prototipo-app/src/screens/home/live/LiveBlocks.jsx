import OfferWhy from '../../../components/assistant/OfferWhy'
import HScroll from '../../../components/HScroll'
import { ProductCard } from '../../../components/ProductCard'
import { storeOfProduct } from '../../../api/catalog'
import { formatPrice, parsePrice } from '../../../state/CartContext'
import { VERTICAL_NAMES } from '../../../data/verticals'

/** Abre la tienda de un producto o plato que el agente ofreció (por su id; sin él, con el nombre y el logo que trae). */
export function openItem(product, push) {
  return push('store', {
    store:
      product.storeId != null
        ? storeOfProduct(product)
        : { name: product.store, img: product.storeLogo ?? product.img, logo: true },
    item: product,
  })
}

/** «¿Qué plan tienes hoy?»: las ocasiones salen de la API y el agente arma, también con la API, un kit de varias verticales. */
export function PlanBlock({ plans, plan, kit, kitReason, added, onPick, onOpen, onAddKit, onCheckout }) {
  const total = (kit ?? []).reduce((sum, product) => sum + parsePrice(product.price), 0)
  const verticals = [...new Set((kit ?? []).map((product) => VERTICAL_NAMES[product.vertical] ?? product.vertical))]
  return (
    <section className="live-card live-card--plan">
      <h2 className="live-plan-title">¿Qué plan tienes hoy?</h2>
      <div className="live-plan-chips" role="radiogroup" aria-label="Plan de hoy">
        {plans.map((option) => (
          <button
            key={option.id}
            type="button"
            role="radio"
            aria-checked={plan === option.id}
            className={plan === option.id ? 'live-plan-chip is-active tap' : 'live-plan-chip tap'}
            onClick={() => onPick(option.id)}
          >
            <span aria-hidden="true">{option.emoji}</span>
            {option.name}
            {option.reason && <small className="live-plan-chip-tag">Para ti</small>}
          </button>
        ))}
      </div>
      {kit?.length ? (
        <div key={plan} className="live-kit">
          <p className="live-kit-meta">
            Tu kit en {verticals.length} {verticals.length === 1 ? 'vertical' : 'verticales'}: {verticals.join(', ')}
          </p>
          <OfferWhy reason={kitReason} />
          <HScroll className="live-items">
            {kit.map((product, i) => (
              <div key={product.id} className="live-item" style={{ '--i': i }}>
                <ProductCard product={product} onOpenStore={() => onOpen(product)} />
              </div>
            ))}
          </HScroll>
          {added ? (
            <button type="button" className="live-kit-add is-added tap" onClick={onCheckout}>
              ✓ En tu carro · Ir a pagar
            </button>
          ) : (
            <button type="button" className="live-kit-add tap" onClick={onAddKit}>
              Agregar el kit · {formatPrice(total)}
            </button>
          )}
        </div>
      ) : (
        <p className="live-plan-empty">Elige uno y te armo todo de una, de las tiendas que hagan falta.</p>
      )}
    </section>
  )
}

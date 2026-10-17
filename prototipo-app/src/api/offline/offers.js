// `POST /agent/offer` sin conexión (offers/engine.py simplificado): la vertical por probar con la escalera del motor,
// «¿Repetimos?», los complementos del carro, del checkout y del próximo pedido, y las respuestas grabadas (kits de una
// ocasión, sin resultado). Todo lo que se ofrece pasa por `offerableProduct` (offers/guards.py).
import { NONE_COMBO, OFFER_BLOCKED_VERTICALS, contractArticles, currentFine, stepSignal, targetStep } from './motor'
import { entityKey } from './snapshot'
import { normalize } from './text'

// offers/guards.py: palabras de un nombre que dicen alcohol o bebé aunque la tienda no lo marque (palabra entera, con
// su plural). La lista de los platos es más larga en el backend; aquí basta con la del catálogo más los tragos.
const ALCOHOL_WORDS = [
  ...['soju', 'makgeolli', 'umeshu', 'cerveza', 'vino', 'whisky', 'pisco', 'ron', 'vodka', 'gin', 'tequila'],
  ...['licor', 'aperitivo', 'espumante', 'champagne', 'sidra', 'sangria', 'michelada', 'schop', 'piscola'],
  ...['mojito', 'terremoto', 'spritz', 'negroni', 'caipirinha', 'daiquiri'],
]
const BABY_WORDS = ['bebe', 'guagua']
const wordsIn = (list) => new RegExp(`\\b(?:${list.join('|')})(?:s|es)?\\b`)
const ALCOHOL_NAME = wordsIn(ALCOHOL_WORDS)
const BABY_NAME = wordsIn(BABY_WORDS)

/**
 * Si el agente puede proponer este producto por su cuenta: ni +18, ni de Farmacia o Licores, ni de un concepto que no
 * ofrece (alcohol, salud, bebé, sensibles: `meta.concepts[…].offerable`), ni con un nombre que dice alcohol o bebé.
 */
export function offerableProduct(product, concepts) {
  if (!product || product.age_restricted) return false
  if (OFFER_BLOCKED_VERTICALS.includes(product.vertical)) return false
  if (product.concept && concepts[product.concept] && !concepts[product.concept].offerable) return false
  const name = normalize(product.name)
  if (ALCOHOL_NAME.test(name)) return false
  return !(product.entity_type !== 'menu_item' && BABY_NAME.test(name))
}

const TO_TRY_TEXT = 'Aún no pides en {vertical}: mira estas ofertas.'
const REASON_TO_TRY = 'Porque aún no pides en {vertical}.'
const REASON_SERVICE = {
  favor: 'Porque ya pides en {n} verticales: {servicio} te ayuda con lo que no está en la app.',
  travel: 'Porque ya pides en {n} verticales: con {servicio} planeas el viaje.',
}
const CHECKOUT_TEXT = 'Para completar lo que llevas: {destino}, en {vertical}.'
const NEXT_ORDER_TEXT = 'Para tu próximo pedido: {destino}, en {vertical}.'
const REASON_NEXT = 'Porque pediste {emoji} {name}.'
const REASON_NEXT_ANONYMOUS = 'Para acompañar lo que pediste.'
const fill = (template, values) => template.replace(/\{(\w+)\}/g, (_, key) => values[key])
const clone = (value) => structuredClone(value)

/** La oferta con solo los productos que pasan las guardias; sin productos (y sin ser un servicio), null. */
function guarded(offer, concepts) {
  if (!offer) return null
  const products = offer.products.filter((p) => offerableProduct(p, concepts))
  if (!products.length && !offer.actions?.some((a) => a.service)) return null
  return { ...offer, products }
}

/** «¿Conoces RappiFavor?»: el paso es un servicio, sin productos (engine.py: _service_offer). */
function serviceOffer(snapshot, step) {
  const { combos, services } = snapshot.meta
  const service = services[step.vertical]
  const pitch = service.pitch.trim().replace(/\.$/, '')
  const used = step.current.split('+').filter((m) => !combos.service_keys.includes(m)).length
  return {
    moment: 'vertical_por_probar',
    text: `¿Conoces ${service.name}? ${pitch[0].toUpperCase()}${pitch.slice(1)}.`,
    products: [],
    vertical: null,
    prototype_vertical: null,
    reason: {
      text: fill(REASON_SERVICE[step.vertical], { n: used, servicio: service.name }),
      basis: [stepSignal(combos, step)],
    },
    actions: [{ label: `Abrir ${service.name}`, route: [service.route], service: service.id }],
  }
}

/**
 * La vertical por probar (engine.py: vertical_to_try): el paso de la escalera del motor. Si es un servicio, su oferta;
 * si es una vertical, la oferta real grabada para ese paso (`toTry[vertical]`) con la señal `combinacion` de esta
 * persona. Sin pedidos, la de siempre (el súper, `toTry.usual`).
 */
export function verticalToTry(snapshot, state, now) {
  const { combos, vertical_labels: labels, concepts } = snapshot.meta
  const step = targetStep(combos, state, now)
  if (step && combos.service_keys.includes(step.vertical)) return serviceOffer(snapshot, step)
  if (step && snapshot.toTry[step.vertical]) {
    const offer = clone(snapshot.toTry[step.vertical])
    offer.reason.basis = [stepSignal(combos, step), ...offer.reason.basis.filter((b) => b.kind !== 'combinacion')]
    return guarded(offer, concepts)
  }
  if (currentFine(combos, state, now) !== NONE_COMBO) return null // ya usa todo lo que se ofrece
  const usual = snapshot.toTry.usual && clone(snapshot.toTry.usual)
  if (!usual) return null
  const label = labels[usual.vertical] ?? usual.vertical
  usual.text = TO_TRY_TEXT.replace('{vertical}', label)
  usual.reason = {
    text: contractArticles(REASON_TO_TRY.replace('{vertical}', label)),
    basis: [{ kind: 'sin_pedidos', id: usual.vertical, source: 'contexto' }],
  }
  return guarded(usual, concepts)
}

const daysAgo = (now, ts) => {
  const days = Math.floor((now - ts) / 86_400_000)
  return days <= 0 ? 'hoy' : days === 1 ? 'ayer' : `hace ${days} días`
}

/**
 * «¿Repetimos?» simplificado (engine.py: repeat_offer pide tres días de compra con ritmo; la demo no puede esperar
 * días): un concepto que la persona pidió en al menos dos pedidos `propuesta`, con el último producto que compró de él.
 */
export function repeatOffer(snapshot, state, now) {
  const { concepts, screen_verticals: screens } = snapshot.meta
  const seen = new Map() // concepto → { orders, last: { line, order } }
  for (const order of state.orders.filter((o) => o.mode === 'propuesta')) {
    for (const line of order.lines) {
      if (!line.concept_id) continue
      const entry = seen.get(line.concept_id) ?? { orders: new Set() }
      entry.orders.add(order.order_id)
      entry.last = { line, order }
      seen.set(line.concept_id, entry)
    }
  }
  const due = [...seen].filter(([, e]) => e.orders.size >= 2).sort((a, b) => b[1].last.order.ts - a[1].last.order.ts)
  for (const [conceptId, entry] of due) {
    const concept = concepts[conceptId]
    const { line, order } = entry.last
    const product = snapshot.byEntity.get(entityKey(line.entity_type, line.entity_id))
    if (!concept?.offerable || !screens[order.vertical] || !offerableProduct(product, concepts)) continue
    const name = concept.name.toLowerCase()
    const times = entry.orders.size
    return {
      moment: 'recompra',
      text: `¿Repetimos ${name}? Lo pediste ${times} veces.`,
      products: [product],
      vertical: order.vertical,
      prototype_vertical: screens[order.vertical],
      reason: {
        concept: conceptId,
        text: `Porque pediste ${name} ${times} veces y tu último pedido fue ${daysAgo(now, order.ts)}.`,
        basis: [{ kind: 'recompra', id: conceptId, source: 'pedidos' }],
      },
      actions: [{ label: 'Ver producto', route: [screens[order.vertical]], store_id: product.store_id }],
    }
  }
  return null
}

/**
 * El complemento de lo que hay (engine.py: complement): la oferta `carrito` real grabada para el concepto de origen,
 * sin lo que ya lleva. En `checkout` y `proximo_pedido` cambia el texto (y en el próximo pedido, el porqué).
 */
export function complementOffer(snapshot, moment, entities) {
  const { concepts, vertical_labels: labels } = snapshot.meta
  const have = new Set(entities.map((e) => entityKey(e.entity_type, e.entity_id)))
  const sources = [
    ...new Set(
      entities.map((e) => snapshot.byEntity.get(entityKey(e.entity_type, e.entity_id))?.concept).filter(Boolean),
    ),
  ]
  for (const source of sources) {
    const recorded = snapshot.complements[source]
    if (!recorded || sources.includes(recorded.reason?.concept)) continue
    const offer = guarded(
      {
        ...clone(recorded),
        products: recorded.products.filter((p) => !have.has(entityKey(p.entity_type, p.entity_id))),
      },
      concepts,
    )
    if (!offer) continue
    if (moment === 'carrito') return offer
    const target = concepts[offer.reason.concept]
    const values = { destino: target?.name.toLowerCase() ?? '', vertical: labels[offer.vertical] ?? offer.vertical }
    offer.moment = moment
    offer.text = fill(moment === 'checkout' ? CHECKOUT_TEXT : NEXT_ORDER_TEXT, values)
    if (moment === 'proximo_pedido') {
      const origin = concepts[source]
      offer.reason = origin?.offerable
        ? {
            ...offer.reason,
            text: fill(REASON_NEXT, { emoji: origin.emoji, name: origin.name.toLowerCase() }),
            basis: [{ kind: 'pedido', id: source, source: 'contexto' }],
          }
        : { ...offer.reason, text: REASON_NEXT_ANONYMOUS, basis: [] }
    }
    return offer
  }
  return null
}

/** La oferta de un momento, o null (204) si no hay nada que ofrecer. */
export function makeOffer(snapshot, state, now, { moment, context = {} }) {
  switch (moment) {
    case 'vertical_por_probar':
      return verticalToTry(snapshot, state, now)
    case 'recompra':
      return repeatOffer(snapshot, state, now)
    case 'carrito':
      return complementOffer(snapshot, moment, context.product ? [context.product] : (context.cart ?? []))
    case 'checkout':
      return complementOffer(snapshot, moment, context.cart ?? [])
    case 'proximo_pedido':
      return complementOffer(snapshot, moment, context.items ?? [])
    case 'plan':
      return guardedPlan(snapshot.planOffers[context.occasion])
    case 'sin_resultado':
      return snapshot.noResult[normalize(context.query)] ?? null
    default:
      return null
  }
}

/** Un kit grabado ya pasó las guardias del backend (el de un carrete puede traer alcohol, con su marca +18). */
const guardedPlan = (offer) => (offer ? clone(offer) : null)

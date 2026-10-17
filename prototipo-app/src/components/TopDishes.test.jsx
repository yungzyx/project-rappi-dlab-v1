import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'
import { toPrototypeProduct } from '../api/client'
import { fixture } from '../api/testing'
import { CartProvider } from '../state/CartContext'
import { DemoProvider } from '../state/DemoContext'
import { ProductSheetProvider, useProductSheet } from '../state/ProductSheetContext'
import AgentMessage from './assistant/AgentMessage'
import { LadderRail } from './assistant/TasteProfile'
import ProductRow from './ProductRow'
import TopDishes from './TopDishes'

// La respuesta real de `/search?q=pizza` (make contract): el primer plato de la pizzería trae lo más pedido.
const restaurants = () => fixture('search-grouped-restaurantes').groups.find((g) => g.vertical === 'restaurantes')
const withTop = () => toPrototypeProduct(restaurants().products[0])
const withoutTop = () => toPrototypeProduct(restaurants().products[1])

/** Lo que abrió la hoja del producto, para mirar qué plato se tocó. */
const sheetState = vi.fn()
const opened = () => sheetState.mock.calls.at(-1)[0]
function SheetSpy() {
  sheetState(useProductSheet().current)
  return null
}

function Providers({ children }) {
  return (
    <DemoProvider>
      <ProductSheetProvider>
        <CartProvider>
          {children}
          <SheetSpy />
        </CartProvider>
      </ProductSheetProvider>
    </DemoProvider>
  )
}

const setMode = (mode) => localStorage.setItem('rappi-proto-demo-mode', mode)

beforeEach(() => {
  setMode('final')
  sheetState.mockClear()
})
afterEach(() => {
  cleanup()
  localStorage.clear()
})

describe('lo que trae la API', () => {
  test('toPrototypeProduct pasa lo más pedido con su fuente, su rótulo y los platos en el formato de la app', () => {
    const top = withTop().topDishes
    expect(top.source).toBe('menu_rappi')
    expect(top.label).toBe('Lo más pedido, según su menú en Rappi')
    expect(top.dishes.length).toBeGreaterThanOrEqual(2)
    expect(top.dishes[0]).toMatchObject({ entityType: 'menu_item', storeId: 9801, price: '$8.990' })
    expect(withoutTop().topDishes).toBeUndefined() // el mismo local, una vez
  })
})

describe('TopDishes', () => {
  test('muestra el rótulo y cada plato con su precio; tocar uno abre su hoja con «Ver tienda»', () => {
    const onOpenStore = vi.fn()
    const top = withTop().topDishes
    render(<TopDishes topDishes={top} onOpenStore={onOpenStore} />, { wrapper: Providers })

    expect(screen.getByText('Lo más pedido, según su menú en Rappi')).toBeTruthy()
    const buttons = screen.getAllByRole('button')
    expect(buttons).toHaveLength(top.dishes.length)
    expect(within(buttons[0]).getByText(top.dishes[0].name)).toBeTruthy()
    expect(within(buttons[0]).getByText(top.dishes[0].price)).toBeTruthy()

    fireEvent.click(buttons[0])
    expect(opened().product).toBe(top.dishes[0])
    opened().onOpenStore()
    expect(onOpenStore).toHaveBeenCalledWith(top.dishes[0])
  })

  test('en «Rappi hoy» no se muestra', () => {
    setMode('actual')
    render(<TopDishes topDishes={withTop().topDishes} />, { wrapper: Providers })
    expect(screen.queryByText('Lo más pedido, según su menú en Rappi')).toBeNull()
  })

  test('sin lista o con un solo plato no pinta nada', () => {
    const top = withTop().topDishes
    const { container } = render(
      <>
        <TopDishes topDishes={undefined} />
        <TopDishes topDishes={{ ...top, dishes: top.dishes.slice(0, 1) }} />
      </>,
      { wrapper: Providers },
    )
    expect(container.querySelector('.top-dishes')).toBeNull()
  })
})

describe('dónde aparece', () => {
  test('en la fila del buscador, bajo el plato del restaurante y no en los demás', () => {
    render(
      <ul>
        <ProductRow product={withTop()} showStore />
        <ProductRow product={withoutTop()} showStore />
      </ul>,
      { wrapper: Providers },
    )
    const rows = document.querySelectorAll('.product-row')
    expect(rows[0].querySelector('.top-dishes')).not.toBeNull()
    expect(rows[1].querySelector('.top-dishes')).toBeNull()
  })

  test('en la tarjeta de una oferta del agente, compacta', () => {
    const message = { id: 1, from: 'bot', text: 'Aún no pides en restaurantes', products: [withTop(), withoutTop()] }
    render(<AgentMessage message={message} onOpenProduct={() => {}} onOpenStore={() => {}} onAction={() => {}} />, {
      wrapper: Providers,
    })
    const lists = document.querySelectorAll('.agent-msg-product .top-dishes--compact')
    expect(lists).toHaveLength(1)
  })

  test('en el peldaño de restaurantes de la escalera', () => {
    const ladder = {
      steps: [{ vertical: 'restaurants', backendVertical: 'restaurantes', text: 'Sushi', products: [withTop()] }],
      trip: null,
    }
    render(<LadderRail ladder={ladder} onOpenVertical={() => {}} onOpenTravel={() => {}} onOpenProduct={() => {}} />, {
      wrapper: Providers,
    })
    expect(document.querySelector('.taste-product .top-dishes')).not.toBeNull()
  })
})

import { StrictMode } from 'react'
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'
import { toMessage } from '../../api/client'
import { fixture, stubApi } from '../../api/testing'
import { CartProvider } from '../../state/CartContext'
import { DemoProvider } from '../../state/DemoContext'
import { ProductSheetProvider } from '../../state/ProductSheetContext'
import { ProfileProvider } from '../../state/ProfileContext'
import AgentMessage from './AgentMessage'

const noop = () => {}

function mount(response, { animate = false } = {}) {
  const message = { ...toMessage(response), animate }
  const result = render(
    <StrictMode>
      <DemoProvider>
        <ProfileProvider>
          <CartProvider>
            <ProductSheetProvider>
              <AgentMessage message={message} onOpenProduct={noop} onOpenStore={noop} onAction={noop} onRetry={noop} />
            </ProductSheetProvider>
          </CartProvider>
        </ProfileProvider>
      </DemoProvider>
    </StrictMode>,
  )
  return result
}

beforeEach(() => {
  stubApi({})
})
afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('reducir movimiento', () => {
  const matchMedia = (reduce) => (query) => ({
    matches: reduce && query.includes('prefers-reduced-motion'),
    addEventListener() {},
    removeEventListener() {},
  })

  test('con reduce la respuesta aparece entera en el primer render', () => {
    vi.stubGlobal('matchMedia', matchMedia(true))
    const response = fixture('agent-ask')
    mount(response, { animate: true })
    expect(screen.getByText(response.text)).toBeTruthy()
  })

  test('sin reduce la respuesta se escribe de a poco', () => {
    vi.stubGlobal('matchMedia', matchMedia(false))
    const response = fixture('agent-ask')
    mount(response, { animate: true })
    expect(screen.queryByText(response.text)).toBeNull()
  })
})

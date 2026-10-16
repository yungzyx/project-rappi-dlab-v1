import { act, cleanup, render, renderHook, waitFor } from '@testing-library/react'
import { afterEach, expect, test } from 'vitest'
import { fixture, stubApi } from '../../api/testing'
import { ProfileProvider, useProfile } from '../../state/ProfileContext'
import { useVerticalOrder } from './useVerticalOrder'

afterEach(cleanup)

const wrapper = ProfileProvider
const requests = (api) => api.mock.calls.filter(([url]) => url.includes('/verticales')).length

test('pide el orden al montar: los códigos del motor y si es personal', async () => {
  stubApi({ 'GET /profile/*': fixture('profile-verticales') })
  const { result } = renderHook(() => useVerticalOrder(), { wrapper })
  await waitFor(() => expect(result.current.personalized).toBe(true))
  expect(result.current.order).toEqual(['farmacia', 'supermercado', 'mall', 'licores', 'conveniencia', 'chocolateria'])
})

test('una persona nueva no es personal', async () => {
  const api = stubApi({ 'GET /profile/*': fixture('profile-verticales-nueva') })
  const { result } = renderHook(() => useVerticalOrder(), { wrapper })
  await waitFor(() => expect(requests(api)).toBe(1))
  await waitFor(() => expect(result.current.order).not.toBeNull())
  expect(result.current.personalized).toBe(false)
})

test('con la API caída: sin orden y sin personalizar', async () => {
  const api = stubApi({ 'GET /profile/*': 'offline' })
  const { result } = renderHook(() => useVerticalOrder(), { wrapper })
  await waitFor(() => expect(requests(api)).toBe(1))
  expect(result.current).toEqual({ order: null, personalized: false })
})

test('al olvidar (cambian las `resets`) pide otra vez y descarta la respuesta de la petición anterior', async () => {
  let calls = 0
  const api = stubApi({
    'GET /profile/*': () => {
      calls += 1
      // La primera tarda y es personal; la segunda llega antes y es la de una persona nueva.
      return calls === 1 ? { slow: 300, body: fixture('profile-verticales') } : fixture('profile-verticales-nueva')
    },
  })
  let reset
  function Probe({ onResult }) {
    reset = useProfile().reset
    onResult(useVerticalOrder())
    return null
  }
  let latest
  render(
    <ProfileProvider>
      <Probe onResult={(value) => (latest = value)} />
    </ProfileProvider>,
  )
  await waitFor(() => expect(requests(api)).toBe(1))
  act(() => reset())
  await waitFor(() => expect(requests(api)).toBe(2))
  await waitFor(() => expect(latest.order).not.toBeNull())
  expect(latest.personalized).toBe(false)
  await new Promise((resolve) => setTimeout(resolve, 400)) // la primera ya contestó: no pisa a la segunda
  expect(latest.personalized).toBe(false)
  expect(latest.order[0]).toBe('supermercado')
})

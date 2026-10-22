import { screen, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'
import { renderWithData, resetApi, serveFixtures, serveFixturesWith } from '../../test/fixtureApi.js'
import { OverviewView } from './OverviewView.jsx'

const NOT_EVIDENCE = 'uso del MVP, pocas personas: no es evidencia'
const decision = (name) => screen.getByRole('article', { name })

describe('OverviewView', () => {
  beforeEach(() => {
    vi.spyOn(console, 'warn').mockImplementation(() => {})
  })

  afterEach(resetApi)

  test('the four questions, each with its figure, its source and an action where there is one', async () => {
    serveFixtures()
    await renderWithData(<OverviewView source="synthetic" onNavigate={() => {}} />)

    const crossSell = decision('¿Dónde está la venta cruzada?')
    expect(within(crossSell).getByText('62,6%')).toBeTruthy()
    expect(within(crossSell).getByText('Dato de Rappi')).toBeTruthy()
    expect(within(crossSell).getByText(/Es una correlación, no un efecto\./)).toBeTruthy()

    const churn = decision('¿A quién estamos perdiendo?')
    expect(within(churn).getByText('230')).toBeTruthy()
    expect(within(churn).getByText(/otras 254 ya se perdieron/)).toBeTruthy()
    expect(within(churn).getByText('Simulado')).toBeTruthy()

    const mochi = decision('¿Funciona lo que ofrece Mochi?')
    expect(within(mochi).getByText('43,8%')).toBeTruthy()

    const demand = decision('¿Qué buscan y no encuentran?')
    expect(within(demand).getByText('26,9%')).toBeTruthy() // la última semana completa al corte
    expect(within(demand).getByText('+8,6 pp')).toBeTruthy()
    expect(
      within(demand).getByText(/🇵🇪 Comida peruana en Restaurantes, 721 personas \(\+42% en 4 semanas\)/),
    ).toBeTruthy()
    expect(within(demand).getByText('Oportunidad: sumar comercios o categoría.')).toBeTruthy()

    expect(screen.getAllByText('Acción sugerida')).toHaveLength(4)
    expect(screen.queryByText(NOT_EVIDENCE)).toBeNull()
  })

  test('how it is going: weekly figures against 4 weeks before, and the full series on demand', async () => {
    serveFixtures()
    await renderWithData(<OverviewView source="synthetic" onNavigate={() => {}} />)

    const active = screen.getByRole('article', { name: 'Personas activas' })
    expect(within(active).getByText('560')).toBeTruthy()
    expect(within(active).getByText('−12%')).toBeTruthy()
    expect(within(active).getByRole('img', { name: 'Personas activas, últimas 12 semanas completas' })).toBeTruthy()
    expect(within(screen.getByRole('article', { name: 'Frecuencia' })).getByText('2,34')).toBeTruthy()
    expect(screen.getByRole('table', { name: 'Serie semanal' })).toBeTruthy()
    expect(screen.getByText('Ver la serie semanal completa')).toBeTruthy()
  })

  test('with the prototype each card from it carries the MVP label, and Rappi data does not', async () => {
    serveFixtures()
    await renderWithData(<OverviewView source="prototype" onNavigate={() => {}} />)

    expect(within(decision('¿Dónde está la venta cruzada?')).queryByText(NOT_EVIDENCE)).toBeNull()
    for (const name of [
      '¿A quién estamos perdiendo?',
      '¿Funciona lo que ofrece Mochi?',
      '¿Qué buscan y no encuentran?',
    ]) {
      expect(within(decision(name)).getByText(NOT_EVIDENCE)).toBeTruthy()
    }
    // y una en «Cómo va»
    expect(screen.getAllByText(NOT_EVIDENCE)).toHaveLength(4)
    expect(
      within(decision('¿Funciona lo que ofrece Mochi?')).getByText('la tasa aparece desde 10 mostradas.', {
        exact: false,
      }),
    ).toBeTruthy()
  })

  test('a card whose data fails says so without taking down the others', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    serveFixturesWith({ offers: { source: 'synthetic', data: null } }) // respuesta no válida → lo guardado
    await renderWithData(<OverviewView source="prototype" onNavigate={() => {}} />)

    expect(within(decision('¿Dónde está la venta cruzada?')).getByText('62,6%')).toBeTruthy()
    expect(
      within(decision('¿Funciona lo que ofrece Mochi?')).getByText('No se pudieron cargar estos datos'),
    ).toBeTruthy()
  })
})

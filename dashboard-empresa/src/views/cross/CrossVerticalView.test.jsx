import { screen, within } from '@testing-library/react'
import { afterEach, describe, expect, test, vi } from 'vitest'
import { renderWithData, resetApi, serveFixtures, serveFixturesWith } from '../../test/fixtureApi.js'
import { motorBody } from '../../test/motorEvaluation.js'
import { CrossVerticalView } from './CrossVerticalView.jsx'
import { formatNumber } from '../../lib/format.js'
import suggestions from '../../fixtures/suggestions.synthetic.json'
import services from '../../fixtures/services.synthetic.json'
import combos from '../../fixtures/combos.synthetic.json'

describe('CrossVerticalView', () => {
  afterEach(resetApi)

  test('muestra sugerencias, afinidad marcada como no usada por el agente y retención por estrato', async () => {
    serveFixtures()
    await renderWithData(<CrossVerticalView source="synthetic" />)

    const shown = suggestions.data.reduce((total, row) => total + (row.mostradas ?? 0), 0)
    expect(await screen.findByText(formatNumber(shown))).toBeTruthy()
    expect(screen.getByText('Aristas aprendidas de datos simulados: solo se ven en el panel. El agente NO las usa.')).toBeTruthy()
    expect(await screen.findByRole('table', { name: 'Afinidad dirigida entre conceptos' })).toBeTruthy()
    expect((await screen.findAllByText('Sin grupo: menos de 20 usuarios')).length).toBeGreaterThan(0)
    expect(screen.getByText(/Supuesto del simulador/)).toBeTruthy()
    const servicesTable = await screen.findByRole('table', { name: 'Servicios sin catálogo' })
    const travel = services.data.find((row) => row.servicio === 'rappitravel')
    expect(within(servicesTable).getByText('✈️ RappiTravel')).toBeTruthy()
    expect(within(servicesTable).getByText(`${formatNumber(travel.ganchos_aceptados)} de ${formatNumber(travel.ganchos_mostrados)}`)).toBeTruthy()
  })

  test('en una demo en vivo el titular cuenta las sugerencias sin inventar un porcentaje', async () => {
    serveFixtures()
    const fixtures = globalThis.fetch
    const demo = [{ concepto: '🥤 Bebidas gaseosas', vertical: 'licores', mostradas: 2, aceptadas: 1, ignoradas: 0, convertidas: 1, aceptacion_pct: null }]
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url) =>
        url.includes('/analytics/suggestions')
          ? { ok: true, status: 200, json: async () => ({ source: 'prototype', data: demo }) }
          : fixtures(url),
      ),
    )
    await renderWithData(<CrossVerticalView source="prototype" />)

    expect(await screen.findByText('sugerencias cruzadas mostradas')).toBeTruthy()
    expect(screen.queryByText('de las sugerencias cruzadas se aceptan')).toBeNull()
  })

  test('sin datos del prototipo muestra estados vacíos', async () => {
    serveFixtures()
    await renderWithData(<CrossVerticalView source="prototype" />)

    expect(await screen.findByText('Sin sugerencias que evaluar')).toBeTruthy()
    expect(await screen.findByText('Sin aristas que mostrar')).toBeTruthy()
    expect(await screen.findByText('Sin usuarios elegibles')).toBeTruthy()
  })

  test('«Combinaciones de verticales» pone la tabla de Rappi junto a la propia, cada una con su rótulo', async () => {
    serveFixtures()
    await renderWithData(<CrossVerticalView source="synthetic" />)

    expect(screen.getByRole('heading', { name: 'Combinaciones de verticales' })).toBeTruthy()
    const rappi = await screen.findByRole('table', { name: 'Combinaciones de verticales de Rappi' })
    const own = await screen.findByRole('table', { name: 'Combinaciones de verticales con datos propios' })
    expect(screen.getByText('Dato compartido por Rappi (cohortes ene–jun 2026)')).toBeTruthy()
    expect(screen.getByText(combos.data.rappi.nota)).toBeTruthy()
    expect(combos.data.rappi.nota).toMatch(/Es una correlación, no un efecto/)
    expect(screen.getByText('Simulado: no es evidencia')).toBeTruthy()
    expect(screen.queryByText('uso del MVP, pocas personas: no es evidencia')).toBeNull()

    const rows = (table) => within(table).getAllByRole('row').slice(1).map((row) => within(row).getAllByRole('cell').map((cell) => cell.textContent))
    expect(rows(rappi).map((cells) => cells[0])).toEqual([
      'Restaurantes',
      'Turbo',
      'Restaurantes + Turbo',
      'Retail',
      'Restaurantes + Retail',
      'Restaurantes + Turbo + Retail',
      'Turbo + Retail',
      'Favor',
      'Todo Chile',
    ])
    expect(rows(rappi)[2]).toEqual(['Restaurantes + Turbo', '78.000', '6,6%', '12,2%', '5,5', '82%', '$123'])
    expect(rows(rappi).at(-1)).toEqual(['Todo Chile', '1.180.000', '100,0%', '100,0%', '3,0', '55%', '$68'])
    // La propia: la retención sin 30 meses con el siguiente completo no se inventa.
    const first = combos.data.propio[0]
    expect(rows(own)[0].slice(0, 2)).toEqual(['Restaurantes', formatNumber(first.meses_usuario)])
    expect(rows(own)[0][5]).toBe('—')
  })

  test('la retención propia se muestra como porcentaje cuando la API la entrega', async () => {
    const propio = [
      { combo: 'rest+turbo', meses_usuario: 120, pct_usuarios: 30, pct_pedidos: 45.5, pedidos_por_usuario: 5.25, retencion_m1: 0.9, retencion_n: 100, gasto_por_usuario: 150000 },
    ]
    serveFixturesWith({ combos: { source: 'synthetic', data: { ...combos.data, propio } } })
    await renderWithData(<CrossVerticalView source="synthetic" />)

    const own = await screen.findByRole('table', { name: 'Combinaciones de verticales con datos propios' })
    const [row] = within(own).getAllByRole('row').slice(1)
    expect(within(row).getAllByRole('cell').map((cell) => cell.textContent)).toEqual([
      'Restaurantes + Turbo', '120', '30,0%', '45,5%', '5,3', '90%', '$150.000',
    ])
  })

  test('con el prototipo, la tabla propia se rotula como uso del MVP y sin pedidos propios lo dice', async () => {
    serveFixtures()
    await renderWithData(<CrossVerticalView source="prototype" />)

    expect(await screen.findByRole('table', { name: 'Combinaciones de verticales de Rappi' })).toBeTruthy()
    // La tabla propia y el motor (que también corrió con pedidos del prototipo) llevan el rótulo.
    expect(screen.getAllByText('uso del MVP, pocas personas: no es evidencia')).toHaveLength(2)
    expect(screen.queryByText('Simulado: no es evidencia')).toBeNull()
    expect(screen.queryByRole('table', { name: 'Combinaciones de verticales con datos propios' })).toBeNull()
    expect(screen.getByText('Sin pedidos propios todavía')).toBeTruthy()
  })

  test('«Motor» sin evaluación muestra pesos, λ y la fecha, y dice por qué no hay métricas', async () => {
    serveFixtures()
    await renderWithData(<CrossVerticalView source="synthetic" />)

    expect(screen.getByRole('heading', { name: 'Motor' })).toBeTruthy()
    expect(await screen.findByText('Sin evaluación')).toBeTruthy()
    expect(screen.getByText('04-10-2026')).toBeTruthy()
    expect(screen.queryByRole('table', { name: 'Próximo vertical por método' })).toBeNull()
  })

  test('«Motor» sin corrida dice que todavía no corrió', async () => {
    serveFixturesWith({ motor: { source: 'prototype', data: null } })
    await renderWithData(<CrossVerticalView source="prototype" />)

    expect(await screen.findByText('El motor todavía no corrió')).toBeTruthy()
  })

  test('«Motor» con evaluación muestra las métricas por método, los pesos y el λ', async () => {
    serveFixturesWith({ motor: motorBody('synthetic') })
    await renderWithData(<CrossVerticalView source="synthetic" />)

    const cells = (table) => within(table).getAllByRole('row').slice(1).map((row) => within(row).getAllByRole('cell').map((cell) => cell.textContent))
    const next = await screen.findByRole('table', { name: 'Próximo vertical por método' })
    expect(cells(next)).toEqual([
      ['Orden fijo', '0,500', '20,0%'],
      ['Popularidad', '0,550', '30,0%'],
      ['Solo afinidad', '0,720', '50,0%'],
      ['Solo transiciones', '0,650', '40,0%'],
      ['Combinado', '0,812', '60,0%'],
    ])
    const cross = screen.getByRole('table', { name: 'Compra cruzada por método' })
    expect(cells(cross)).toEqual([
      ['Reglas aprendidas', '18,0%', '70,0%', '294'],
      ['Lo más pedido', '10,0%', '100,0%', '420'],
      ['Mezcla', '20,0%', '100,0%', '420'],
    ])
    const repeat = screen.getByRole('table', { name: 'Recompra' })
    expect(cells(repeat)).toEqual([['64', '40,0%', '3', '31,0%']])
    expect(screen.getByText('Afinidad 1 · Transición 0,5 · Popularidad 0,1')).toBeTruthy()
    expect(screen.getByText('λ = 2')).toBeTruthy()
    expect(screen.getByText(/prueba la mecánica del motor, no el efecto/)).toBeTruthy()
    expect(screen.getByText('Datos simulados:')).toBeTruthy()
  })

  test('«Motor» con aviso de validación lo muestra', async () => {
    const body = motorBody('synthetic')
    body.data.evaluacion = { ...body.data.evaluacion, validacion: { personas: 0, ndcg_combinado: null, precision3_mezcla: null, aviso: 'Nadie para validar: quedan los pesos de la corrida anterior' } }
    serveFixturesWith({ motor: body })
    await renderWithData(<CrossVerticalView source="synthetic" />)

    expect(await screen.findByText('Nadie para validar: quedan los pesos de la corrida anterior')).toBeTruthy()
  })
})

// Revisa en un Chrome real que la app del MVP responda como debe (lo corre scripts/mvp-check.sh con `make mvp-check`).
// Uso: node scripts/mvp-check.mjs --app http://localhost:5184 [--api http://localhost:8010] [--shop | --kit | --home | --expect-offline | --panel http://localhost:5185]
//   sin banderas: la app abre en la Home conectada, con la barra «Busca o pídele ideas a <agente>» y el aviso de privacidad
//     de la primera visita (que se cierra con «Entendido»);
//   con --shop: Home → vertical Grocery → primera tienda → agregar un producto → carrito → pagar, y la API recibe el
//     pedido (que después verifica scripts/mvp-check.sh en la base de prueba);
//   con --kit: busca «cerveza» en el buscador con Mochi (ve la búsqueda agrupada por vertical), vuelve a la Home, elige
//     la ocasión «Carrete», agrega el kit que arma Mochi (`plan`) y paga; scripts/mvp-check.sh verifica después en la base
//     de prueba que el pedido tiene líneas sembradas y al menos una aceptación `agent-plan`;
//   con --home: Home dinámica. Una persona nueva ve los 6 accesos en el orden fijo, con Loyalty y Benefits Pro al final y
//     sin el texto «Ordenadas según lo que más usas»; toca «Retail» (Rappi Mall) tres veces, volviendo a la Home cada
//     vez, espera a que la API acepte los toques (`vertical_open`; al volver a la Home la app los manda y vuelve a pedir
//     el orden) y, sin recargar, Retail queda primero y el texto aparece;
//   con --expect-offline: la API está detenida y la app muestra «Sin conexión con <agente>»;
//   con --panel <url del panel> (sin --app): corre después de las demás, con la API en marcha. Espera a que la API ya
//     cuente lo que dejó el kit (una oferta aceptada en «Plan»), abre el panel en «Uso del MVP» con la fuente del
//     prototipo y ve esa cifra ahí, con el rótulo «uso del MVP, pocas personas: no es evidencia» y sin el aviso de datos
//     guardados (que taparía una API que no responde).
// Con la API en marcha (sin --expect-offline) también falla ante un error de la página o de la consola, o una respuesta
// 4xx/5xx, desde la primera carga; solo se ignoran las imágenes del catálogo de prueba, que no existen.
// Sale con 0 si la revisión pasa y con 1 si no. Usa el Chrome instalado (playwright-core, sin descargar navegadores);
// CHROME_PATH apunta a otro ejecutable y PLAYWRIGHT_CHANNEL a otro canal (p. ej. chrome-beta); MVP_CHECK_ARTIFACTS=<carpeta>
// guarda ahí una captura cuando una revisión falla.
import { mkdirSync } from 'node:fs'
import { parseArgs } from 'node:util'
import { chromium } from 'playwright-core'
import { AGENT_NAME } from '../src/agent/name.js'

// Los textos visibles llevan el nombre del agente: salen de la misma constante que usa la app.
const HOME_HINT = `Busca o pídele ideas a ${AGENT_NAME}`
const OFFLINE_TITLE = `Sin conexión con ${AGENT_NAME}`
const SEARCH_DIALOG = `Buscador con ${AGENT_NAME}`
const API_DEFAULT = 'http://localhost:8010'
const TIMEOUT_MS = 20_000 // la barra rota tres frases cada 3,2 s: la de Mochi tarda hasta ~6 s en salir

/** Qué dice la página ahora: ayuda a entender por qué falló una espera. */
async function pageSays(page) {
  const text = await page.evaluate(() => document.body.innerText.replace(/\s+/g, ' ').trim())
  return text ? `la página dice «${text.slice(0, 120)}»` : 'la página está en blanco'
}

async function checkOnline(page) {
  const bar = page.locator('.smart-bar-hint', { hasText: HOME_HINT }).first()
  try {
    await bar.waitFor({ timeout: TIMEOUT_MS })
  } catch {
    throw new Error(`no apareció la barra «${HOME_HINT}»: ${await pageSays(page)}`)
  }
  if ((await page.getByRole('heading', { name: OFFLINE_TITLE }).count()) > 0) {
    throw new Error(`apareció «${OFFLINE_TITLE}» con la API en marcha`)
  }
  // Una persona nueva ve el aviso de privacidad (qué se guarda y cómo borrarlo); se cierra para que no tape el resto.
  const notice = page.getByRole('region', { name: 'Privacidad' })
  try {
    await notice.waitFor({ timeout: TIMEOUT_MS })
  } catch {
    throw new Error(`la primera visita no mostró el aviso de privacidad: ${await pageSays(page)}`)
  }
  await notice.getByRole('button', { name: 'Entendido' }).click()
  return `la Home abre con la barra «${HOME_HINT}» y el aviso de privacidad`
}

/**
 * Lo que la revisión vigila, enganchado antes de abrir la página (lo que falla al cargar no se puede recuperar después):
 * errores de la página, errores de la consola y respuestas 4xx/5xx. Las imágenes del catálogo de prueba no existen (la app
 * muestra la de reemplazo), así que solo las cargas de imágenes se ignoran. Devuelve la lista, que se va llenando.
 */
function watchProblems(page) {
  const problems = []
  page.on('pageerror', (error) => problems.push(error.message))
  // Una carga fallida sale por su respuesta (abajo), con su URL: la consola solo la repite sin decir cuál fue.
  page.on('console', (message) => {
    if (message.type() === 'error' && !message.text().startsWith('Failed to load resource'))
      problems.push(message.text())
  })
  page.on('response', (response) => {
    const request = response.request()
    if (response.status() >= 400 && request.resourceType() !== 'image')
      problems.push(`${request.method()} ${response.url()} → ${response.status()}`)
  })
  return problems
}

/** Recorre una compra real contra el catálogo de prueba. Los textos son los de la app (Grocery, View cart, Place order). */
async function checkShop(page) {
  await checkOnline(page)
  await step(page, 'abrir Grocery desde la Home', () =>
    page.getByRole('button', { name: 'Grocery', exact: true }).click(),
  )
  const stores = page.getByRole('region', { name: 'Tiendas' })
  await step(page, 'ver las tiendas de Grocery', () => stores.waitFor())
  await step(page, 'abrir la primera tienda', () =>
    stores
      .getByRole('button', { name: /de prueba/ })
      .first()
      .click(),
  )
  const store = await step(page, 'ver el nombre de la tienda', async () => {
    const heading = page.getByRole('heading', { level: 1 })
    await heading.waitFor()
    return heading.innerText()
  })
  // Solo los productos: el corazón de favoritos también empieza con «Agregar».
  const product = page
    .getByRole('listitem')
    .getByRole('button', { name: /^Agregar / })
    .first()
  await step(page, 'ver productos en la tienda', () => product.waitFor())
  await step(page, 'agregar un producto', () => product.click())
  await step(page, 'abrir el carrito', () => page.getByRole('button', { name: /View cart/ }).click())
  await step(page, 'ir al checkout', () => page.getByRole('button', { name: 'Go to checkout' }).click())
  const place = page.getByRole('button', { name: /^Place order/ })
  await step(page, 'ver el botón de pagar', () => place.waitFor())
  const posted = page.waitForResponse((r) => r.request().method() === 'POST' && new URL(r.url()).pathname === '/orders')
  await place.click()
  const response = await posted.catch(() => {
    throw new Error('la app no mandó el pedido a la API (POST /orders)')
  })
  if (!response.ok()) throw new Error(`la API rechazó el pedido (POST /orders → ${response.status()})`)
  return `compró en «${store}» y la API aceptó el pedido`
}

/**
 * Busca «cerveza» con Mochi (grupos por vertical), pide el kit de «Carrete» en la Home, lo agrega y paga. Los textos son
 * los de la app (Buscador con Mochi, Plan de hoy, Agregar el kit, Ir a pagar, Place order).
 */
async function checkKit(page) {
  await checkOnline(page)
  await step(page, 'abrir el buscador con Mochi', () => page.locator('.smart-bar').first().click())
  const panel = page.getByRole('dialog', { name: SEARCH_DIALOG })
  await step(page, 'escribir «cerveza»', () =>
    panel.getByRole('searchbox', { name: 'Buscar en Rappi' }).fill('cerveza'),
  )
  const groups = panel.locator('section[aria-labelledby] > h2')
  await step(page, 'ver la búsqueda agrupada por vertical', () => groups.first().waitFor())
  // El catálogo de prueba vende cerveza en tres verticales (licores, conveniencia y supermercado).
  const found = await step(page, 'contar los grupos de la búsqueda', async () => {
    await panel
      .getByText(/^Cerveza rubia/)
      .first()
      .waitFor()
    return groups.count()
  })
  if (found < 2) throw new Error(`«cerveza» salió en ${found} grupo(s) y se esperaban al menos 2`)
  await step(page, 'cerrar el buscador', () => panel.locator('.search-back').click())
  await step(page, 'ver que el buscador se cerró', () => panel.waitFor({ state: 'detached' }))
  await step(page, 'elegir la ocasión «Carrete»', () => page.getByRole('radio', { name: /Carrete/ }).click())
  await step(page, 'ver el kit de Mochi', () => page.locator('.live-kit-meta').waitFor())
  // Agregar el kit registra una aceptación por producto; la app las manda en lotes cada 5 s.
  const accepted = page.waitForResponse(
    (r) =>
      r.request().method() === 'POST' &&
      new URL(r.url()).pathname === '/events' &&
      (r.request().postData() ?? '').includes('suggestion_accepted'),
    { timeout: TIMEOUT_MS },
  )
  accepted.catch(() => {}) // si no llega, falla abajo con su propio mensaje
  await step(page, 'agregar el kit', () => page.getByRole('button', { name: /^Agregar el kit/ }).click())
  await step(page, 'ir a pagar', () => page.getByRole('button', { name: /Ir a pagar/ }).click())
  const place = page.getByRole('button', { name: /^Place order/ })
  await step(page, 'ver el botón de pagar', () => place.waitFor())
  const posted = page.waitForResponse((r) => r.request().method() === 'POST' && new URL(r.url()).pathname === '/orders')
  await place.click()
  const response = await posted.catch(() => {
    throw new Error('la app no mandó el pedido a la API (POST /orders)')
  })
  if (!response.ok()) throw new Error(`la API rechazó el pedido (POST /orders → ${response.status()})`)
  await accepted.catch(() => {
    throw new Error('la app no registró la aceptación del kit (POST /events con suggestion_accepted)')
  })
  return `buscó «cerveza» (${found} grupos), pidió el kit «Carrete», lo agregó y la API aceptó el pedido`
}

const ORDER_CAPTION = 'Ordenadas según lo que más usas'
const FIXED_LABELS = ['Grocery', 'Pharmacy', 'Retail', 'Liquor', 'Express', 'Chocolates']
const TAIL_LABELS = ['Loyalty', 'Benefits Pro']

/** Los nombres de los accesos de la fila de la Home, en el orden en que se ven. */
const shortcutLabels = (page) =>
  page.locator('.home-shortcut').evaluateAll((nodes) => nodes.map((node) => node.innerText.trim()))

/**
 * Home dinámica: sin historial, el orden fijo; tras tocar Retail tres veces, Retail va primero y la Home dice por qué.
 * Los toques se cuentan en las respuestas 200 de `POST /events` (al volver a la Home la app los manda y después vuelve a
 * pedir el orden): la Home se reordena sin recargar.
 */
async function checkHome(page) {
  await checkOnline(page)
  const row = page.locator('.home-shortcut').first()
  await step(page, 'ver la fila de accesos', () => row.waitFor())
  const before = await shortcutLabels(page)
  if (before.slice(0, 6).join() !== FIXED_LABELS.join())
    throw new Error(`una persona nueva ve ${before.slice(0, 6).join(', ')} y se esperaba ${FIXED_LABELS.join(', ')}`)
  if (before.slice(-2).join() !== TAIL_LABELS.join())
    throw new Error(`la fila debe terminar en ${TAIL_LABELS.join(' y ')} y termina en ${before.slice(-2).join(' y ')}`)
  if ((await page.getByText(ORDER_CAPTION).count()) > 0)
    throw new Error(`una persona nueva ve «${ORDER_CAPTION}» sin historial`)

  let opens = 0
  page.on('response', (response) => {
    const request = response.request()
    if (request.method() === 'POST' && new URL(request.url()).pathname === '/events' && response.status() === 200)
      opens += (request.postData() ?? '').split('"vertical_open"').length - 1
  })
  for (let tap = 1; tap <= 3; tap++) {
    await step(page, `tocar «Retail» (${tap} de 3)`, () =>
      page.locator('.home-shortcut', { hasText: 'Retail' }).first().click(),
    )
    await step(page, 'volver a la Home', () => page.locator('[aria-label="Volver"]').first().click())
    await step(page, 'ver la Home de nuevo', () => row.waitFor())
  }
  const deadline = Date.now() + EVENTS_WAIT_MS
  while (opens < 3 && Date.now() < deadline) await new Promise((resolve) => setTimeout(resolve, 250))
  if (opens < 3) throw new Error(`la API aceptó ${opens} de 3 toques (POST /events con vertical_open) tras 30 s`)

  await step(page, `ver el texto «${ORDER_CAPTION}»`, () => page.getByText(ORDER_CAPTION).waitFor())
  const after = await shortcutLabels(page)
  if (after[0] !== 'Retail') throw new Error(`tras tocar Retail 3 veces el primero es «${after[0]}»`)
  if (after.slice(-2).join() !== TAIL_LABELS.join())
    throw new Error(`con el orden personal, la fila debe terminar en ${TAIL_LABELS.join(' y ')}`)
  return `orden fijo sin historial; tras 3 toques a Retail queda primero (${after.slice(0, 3).join(', ')}…) con el texto «${ORDER_CAPTION}»`
}

/** Cuánto se espera a que la API cuente los eventos de las revisiones anteriores (la app los manda en lotes cada 5 s). */
const EVENTS_WAIT_MS = 30_000
const NOT_EVIDENCE = 'uso del MVP, pocas personas: no es evidencia'

/** Pide una métrica del panel a la API hasta que `ready` diga que ya tiene lo esperado; si no llega, dice qué faltó. */
async function waitForMetric(api, name, ready, missing) {
  const deadline = Date.now() + EVENTS_WAIT_MS
  let last = 'sin respuesta'
  while (Date.now() < deadline) {
    try {
      const reply = await fetch(`${api}/analytics/${name}?source=prototype`)
      if (reply.ok) {
        const { data } = await reply.json()
        if (ready(data)) return data
        last = 'todavía sin eventos'
      } else {
        last = `GET /analytics/${name} → ${reply.status}`
      }
    } catch (error) {
      last = error.message
    }
    await new Promise((resolve) => setTimeout(resolve, 500))
  }
  throw new Error(
    `no pude ver ${missing} en GET /analytics/${name} de la API tras ${EVENTS_WAIT_MS / 1000} s (${last})`,
  )
}

/** Abre «Uso del MVP» del panel con los datos del prototipo y ve lo que dejaron las revisiones anteriores. */
async function checkPanel(page, panel, api) {
  const plan = await waitForMetric(
    api,
    'offers',
    (data) => data.momentos.some((row) => row.momento === 'plan' && row.aceptadas >= 1),
    'una oferta aceptada del kit en «Plan»',
  )
  await page.goto(`${panel}/?vista=mvp&fuente=prototipo`, { timeout: TIMEOUT_MS })
  const offers = page.getByRole('table', { name: 'Ofertas del agente por momento' })
  await step(page, 'ver la tabla «Ofertas del agente por momento»', () => offers.waitFor())
  const accepted = await step(page, 'leer las ofertas aceptadas de «Plan»', async () => {
    const row = offers.getByRole('row', { name: /^Plan / })
    await row.waitFor()
    return Number((await row.getByRole('cell').nth(2).innerText()).replace(/\D/g, ''))
  })
  if (!(accepted >= 1)) throw new Error(`«Plan» muestra ${accepted} aceptadas y se esperaba al menos 1`)
  const notes = await step(page, `ver el rótulo «${NOT_EVIDENCE}»`, async () => {
    await page.getByText(NOT_EVIDENCE).first().waitFor()
    return page.getByText(NOT_EVIDENCE).count()
  })
  // Los datos guardados tienen la misma forma: si la API no contestó, el panel los muestra y este recorrido no probaría nada.
  if ((await page.getByText('Modo sin conexión (datos guardados):').count()) > 0)
    throw new Error('el panel mostró datos guardados en vez de los de la API')
  return `el panel muestra «Plan» con ${accepted} aceptada(s) (la API: ${plan.momentos.length} momento(s)) y ${notes} rótulos «${NOT_EVIDENCE}»`
}

/** Un paso del recorrido: si falla, dice cuál era y qué mostraba la página. */
async function step(page, what, action) {
  try {
    return await action()
  } catch (error) {
    throw new Error(`no pude ${what}: ${error.message.split('\n')[0]}; ${await pageSays(page)}`, { cause: error })
  }
}

async function checkOffline(page) {
  try {
    await page.getByRole('heading', { name: OFFLINE_TITLE }).waitFor({ timeout: TIMEOUT_MS })
  } catch {
    throw new Error(`no apareció «${OFFLINE_TITLE}»: ${await pageSays(page)}`)
  }
  if ((await page.locator('.smart-bar').count()) > 0) throw new Error('la Home se montó sin API')
  return `la app muestra «${OFFLINE_TITLE}»`
}

const { values } = parseArgs({
  options: {
    app: { type: 'string' },
    shop: { type: 'boolean', default: false },
    kit: { type: 'boolean', default: false },
    home: { type: 'boolean', default: false },
    api: { type: 'string', default: API_DEFAULT },
    'expect-offline': { type: 'boolean', default: false },
    panel: { type: 'string' },
  },
})
const offline = values['expect-offline']
const label = values.panel
  ? 'panel'
  : offline
    ? 'sin API'
    : values.kit
      ? 'kit de Mochi'
      : values.home
        ? 'home'
        : values.shop
          ? 'compra'
          : 'en línea'

/** Con MVP_CHECK_ARTIFACTS=<carpeta> (lo usa el CI), una revisión que falla deja la captura de lo que se veía. */
async function saveFailureScreenshot(page) {
  const dir = process.env.MVP_CHECK_ARTIFACTS
  if (!dir || !page) return
  mkdirSync(dir, { recursive: true })
  const name = label.replace(/[^a-z0-9]+/gi, '-')
  await page.screenshot({ path: `${dir}/${name}.png`, fullPage: true }).catch(() => {})
}

async function main() {
  if (!values.app && !values.panel) throw new Error('falta --app <url> (por ejemplo --app http://localhost:5184)')
  const launchOptions = process.env.CHROME_PATH
    ? { executablePath: process.env.CHROME_PATH }
    : { channel: process.env.PLAYWRIGHT_CHANNEL || 'chrome' }
  const browser = await chromium.launch(launchOptions).catch((error) => {
    throw new Error(`no pude abrir Chrome (${error.message.split('\n')[0]})`)
  })
  let page
  try {
    page = await browser.newPage({
      viewport: values.panel ? { width: 1280, height: 900 } : { width: 560, height: 960 },
    })
    page.setDefaultTimeout(TIMEOUT_MS)
    const problems = watchProblems(page)
    if (!values.panel) await page.goto(values.app, { timeout: TIMEOUT_MS })
    const checks = {
      home: checkHome,
      kit: checkKit,
      shop: checkShop,
    }
    const picked = Object.keys(checks).find((name) => values[name])
    const check = values.panel
      ? (p) => checkPanel(p, values.panel, values.api)
      : offline
        ? checkOffline
        : (checks[picked] ?? checkOnline)
    const done = await check(page)
    // Sin API es lo esperado que fallen sus llamadas: ahí no se miran.
    if (!offline && problems.length > 0) throw new Error(`fallos en la página o en la API: ${problems[0]}`)
    console.log(`  ✓ ${label}: ${done}`)
  } catch (error) {
    await saveFailureScreenshot(page)
    throw error
  } finally {
    await browser.close()
  }
}

main().catch((error) => {
  console.error(`  ✗ ${label}: ${(error.message ?? String(error)).split('\n')[0]}`)
  process.exitCode = 1
})

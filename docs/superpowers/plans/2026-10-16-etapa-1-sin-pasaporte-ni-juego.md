# Etapa 1: salida del pasaporte y del juego. Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que el pasaporte Rappi y el juego de verticales desaparezcan de todo el proyecto (API, base, app, panel, scripts, CI, despliegue y documentos vigentes) sin romper nada de lo que queda.

**Architecture:** Borrado en capas: primero la base y el backend (migración 035, paquete `game`, rutas, comando y métrica), después el momento `vertical_por_probar` sin sellos, luego la app, el panel y los scripts, y al final los documentos. El contrato API-app (`make contract`) se regenera después de los cambios del backend.

**Tech Stack:** Python 3.13 + FastAPI + psycopg (rappi-ia), Postgres 17 + pgvector, React 19 + Vite + Vitest (prototipo-app, dashboard-empresa), bash y Node (scripts).

**Spec:** `docs/superpowers/specs/2026-10-16-motor-multivertical-design.md` (§4, Etapa 1).

## Global Constraints

- Código en inglés; todo lo que ve una persona (textos, logs, CLI, docs, comentarios SQL) en español.
- Migraciones solo en `rappi-scraper/src/rappi_scraper/storage/migrations/`; no se editan las ya aplicadas (028, 029).
- `make test` y `make lint` en `rappi-ia/` (y en `rappi-scraper/` si se toca); `npm test` y `npm run lint` en `prototipo-app/` y `dashboard-empresa/`.
- Las fixtures de `prototipo-app/src/api/fixtures/` y `dashboard-empresa/src/fixtures/` las escribe `make contract` en `rappi-ia`; nunca a mano. Una fixture que ya no tiene ejemplo se borra a mano.
- Los planes y specs fechados de `docs/superpowers/` y `docs/resultados/juego-verificacion-2026-10-09.md` no se tocan: son historia.
- Falsos positivos que NO se tocan: segmentos `explorador` y `gamer`, «videojuego» y «tarjeta de regalo» de la taxonomía, `knowledge_edges` y la capa de grafo, el borrado de tarjetas de crédito en `events/store.py`, «envío gratis» de tiendas y de Pro, las insignias «Unavailable».
- Nunca borrar archivos fuera del repo; dentro del repo, con `git rm`.

## Review Focus

- Una app abierta antes del cambio que todavía manda `context.stamped` a `vertical_por_probar`: la API responde 422 (el cuerpo es estricto) y la app nueva ya no lo manda; no debe quedar ningún llamado con `stamped`.
- `localStorage` con las claves viejas del juego (`rappi-proto-juego-v1`, `rappi-proto-pasaporte`): la app no debe fallar ni leerlas; «Borrar mis datos» las sigue limpiando junto con el resto (vacía el almacenamiento local).
- «Silenciar por hoy» del agente sigue funcionando: `today()` cambia de módulo, no de comportamiento (zona `America/Santiago`).
- `deploy-migrate` sobre una base ya en 034: aplica la 035 y termina sin cargar tarjetas; `test_deploy_migrate.py` lo cubre.
- Purga de personas inactivas: ya no mira `game_state`; una persona del prototipo sin eventos ni pedidos recientes se purga igual que antes (`test_pool.py`).

---

### Task 1: Base y backend sin juego

**Files:**
- Create: `rappi-scraper/src/rappi_scraper/storage/migrations/035_sin_juego.sql`
- Delete (git rm): `rappi-ia/src/rappi_ia/game/` (todo), `rappi-ia/src/rappi_ia/api/game.py`, `rappi-ia/tests/unit/test_knowledge_cards.py`, `rappi-ia/tests/unit/test_game_challenges.py`, `rappi-ia/tests/integration/test_did_you_know.py`, `rappi-ia/tests/integration/test_game_api.py`, `rappi-ia/tests/integration/test_game_challenge_api.py`, `rappi-ia/tests/integration/test_knowledge_load.py`, `rappi-ia/tests/integration/test_game_events.py`
- Modify: `rappi-ia/src/rappi_ia/api/app.py` (import y bloque de `did_you_know` en `POST /agent/ask`, `game_router`, `"game"` en `ANALYTICS`, comentario de «¿Sabías que…?»), `rappi-ia/src/rappi_ia/cli.py` (`cmd_knowledge`, `_card_proposals_with_jev`, subparser `knowledge`, docstring; `deploy-migrate` ya no carga tarjetas ni imprime «Tarjetas del juego…», y su ayuda), `rappi-ia/src/rappi_ia/config.py` (`GAME_MIN_ITEMS`), `rappi-ia/src/rappi_ia/demo/seed.py` (`load_knowledge` en `seed_demo`), `rappi-ia/src/rappi_ia/events/store.py` (los dos tipos del juego en `EVENT_TYPES`, su comentario, y `game_state` en `purge_inactive_users`), `rappi-ia/src/rappi_ia/analytics/queries.py` (`MIN_GAME_ROUNDS` y `game()`), `rappi-ia/src/rappi_ia/api/identity.py` (docstring), `rappi-ia/pyproject.toml` (`"rappi_ia.game"` en package-data), `rappi-ia/.env.example` (`GAME_MIN_ITEMS`), `rappi-ia/Makefile` (`knowledge` en `.PHONY`, su target, `SERVE_PREP`, `post-refresh` y sus textos, descripción de `deploy-migrate`), `deploy/db/grants.sql` (`game_state`), `deploy/docker-compose.yml` (comentario de tarjetas)
- Modify tests: `rappi-ia/tests/integration/test_contract.py` (quitar `"game"` de `PANEL_METRICS`, los ejemplos `agent-ask-dato`, `game-cards`, `game-challenge`, `game-state-put`, `game-state`, `GAME_STATE`, el monkeypatch de `GAME_MIN_ITEMS`, el estado de `u-contrato` y los eventos del juego de `prototype_journey`), `test_analytics_mvp.py` (forma `"game"`, helpers `_round`/`_card`, los dos tests del juego y sus asserts en `test_every_new_metric_never_mixes_sources`), `test_ownership.py` (`test_put_other_game_state_is_403` y la línea de `game/state`), `test_pool.py` (la persona `p-juego` con `game_state`), `test_deploy_migrate.py` (sin 108 tarjetas ni paso `knowledge`), `test_jev_pilot.py` (import de `cards` y los 6 tests de propuestas de tarjetas), `unit/test_api_health_logs.py` (`test_order_and_game_other_source_errors_are_generic` queda solo con pedidos y se renombra `test_order_other_source_errors_are_generic`), `unit/test_cors.py` (`test_preflight_allows_put_for_the_game_state` → probar el `PUT`/`DELETE` que aún exista o borrar si no queda ninguno con PUT), `unit/test_api_inputs.py` (aserción de `/game/cards`), `tests/owner_client.py` (`game/state` en `USER_IN_PATH`)
- Create test: `rappi-ia/tests/integration/test_sin_juego.py`

**Interfaces:**
- Produces: la base queda sin `knowledge_cards`, `knowledge_card_concepts` ni `game_state`; `EVENT_TYPES` sin `game_round_finished` ni `game_card_discovered`; `ANALYTICS` sin `game`; `/agent/ask` ya no devuelve `did_you_know`.

- [ ] **Step 1: Write the failing tests** en `tests/integration/test_sin_juego.py`:

```python
def test_migration_035_drops_game_tables(db):
    rows = db.execute(
        "select table_name from information_schema.tables where table_schema='public' "
        "and table_name in ('knowledge_cards','knowledge_card_concepts','game_state')"
    ).fetchall()
    assert rows == []

def test_game_event_types_are_rejected(db):
    db.execute("insert into app_users(user_id, source) values ('u1','prototype')")
    with pytest.raises(psycopg.errors.CheckViolation):
        db.execute("insert into app_events(user_id, session_id, type, source) values ('u1','s','game_round_finished','prototype')")

def test_game_routes_are_gone(client):  # usa el cliente de la API de los tests de integración
    assert client.get("/game/cards").status_code == 404

def test_analytics_has_no_game():
    from rappi_ia.api.app import ANALYTICS
    assert "game" not in ANALYTICS

def test_event_types_have_no_game():
    from rappi_ia.events.store import EVENT_TYPES
    assert not {t for t in EVENT_TYPES if t.startswith("game_")}
```

(Usar los fixtures `db` y el cliente que ya usan los demás tests de integración; ajustar nombres de fixture a los de `tests/conftest.py`.)

- [ ] **Step 2: Run** `cd rappi-ia && scripts/with-test-db-lock.sh .venv/bin/python -m pytest tests/integration/test_sin_juego.py -q` → FAIL.

- [ ] **Step 3: Write `035_sin_juego.sql`**: `DELETE FROM app_events WHERE type IN ('game_round_finished','game_card_discovered');` luego `DROP TABLE game_state, knowledge_card_concepts, knowledge_cards;`, luego el `CHECK` de `app_events.type` con los 16 tipos anteriores a la 029 (`app_open, search, chat, ask, view_store, view_item, cart_add, cart_remove, checkout_start, order_placed, suggestion_shown, suggestion_accepted, suggestion_dismissed, recommendation_click, service_shown, service_opened`) y un `COMMENT ON COLUMN app_events.type` sin mención del juego. Encabezado en español: «El juego y el pasaporte salen del proyecto (16-10-2026); su historia está en rappi-evolucion-proyecto, etiqueta etapa-12-pasaporte-y-juego».

- [ ] **Step 4: Remove the game from the backend and its tests** (lista de Files). En `cli.py`, `deploy-migrate` queda: respaldar si hay pendientes, migrar, permisos.

- [ ] **Step 5: Run** `cd rappi-ia && make lint && make test` → todo verde (salvo el contrato, que se regenera en la Task 2).

- [ ] **Step 6: Commit** `git commit -m "feat(sin-juego): la base y la API sin el juego ni el pasaporte (migración 035)"`.

### Task 2: `vertical_por_probar` sin sellos y contrato

**Files:**
- Modify: `rappi-ia/src/rappi_ia/offers/engine.py` (docstrings; `PASSPORT_ORDER` → `TO_TRY_ORDER` con el mismo orden y un comentario que ya no menciona el juego; `REASON_TO_TRY`; `make_offer`; `vertical_to_try`), `rappi-ia/src/rappi_ia/api/agent.py` (`ToTryContext` sin campos; quitar la normalización de `stamped`)
- Modify tests: `tests/integration/test_agent_offer.py`, `tests/integration/test_offer_affinity.py` (helper `to_try` y los `test_vertical_to_try_*`), `tests/integration/test_personalization_done.py` (helper `to_try`), `tests/unit/test_offer_reasons.py`, `tests/unit/test_text_contractions.py` (frase de ejemplo nueva), `tests/integration/test_contract.py` (los dos ejemplos de `vertical_por_probar` con `context: {}`; el «afín» siembra un pedido en lugar de sellos)
- Regenerate: fixtures con `make contract`; borrar con `git rm` las que quedaron sin ejemplo: `prototipo-app/src/api/fixtures/{game-cards,game-challenge,game-state,game-state-put,agent-ask-dato}.json`, `dashboard-empresa/src/fixtures/game.prototype.json`, `dashboard-empresa/src/fixtures/game.synthetic.json`

**Interfaces:**
- Consumes: Task 1.
- Produces: `POST /agent/offer` con `{"moment": "vertical_por_probar", "context": {}}`; `vertical_to_try(conn: Connection, tried: set[str], interests: Interests) -> Offer | None`; `tried_verticals(conn: Connection, user_id: str | None) -> set[str]` en `offers/engine.py` (verticales con algún pedido `mode = 'propuesta'` de la persona; vacío sin persona). `REASON_TO_TRY = "Porque aún no pides en {vertical}."`; la señal de contexto es `_context_signal("sin_pedidos", vertical)`.

- [ ] **Step 1: Write the failing tests** (en `test_agent_offer.py`):

```python
def test_vertical_to_try_skips_verticals_with_orders_and_pharmacy(db, client):
    # persona con un pedido 'propuesta' en supermercado → la oferta no es de supermercado ni farmacia ni licores
    ...
    r = client.post("/agent/offer", json={"user_id": uid, "moment": "vertical_por_probar", "context": {}}, headers=token)
    assert r.json()["vertical"] not in {"supermercado", "farmacia", "licores"}

def test_vertical_to_try_ignores_actual_mode_orders(db, client):
    # un pedido mode='actual' en supermercado no cuenta como probado → con catálogo de prueba, la primera es supermercado
    ...
    assert r.json()["vertical"] == "supermercado"

def test_vertical_to_try_reason_says_no_orders(db, client):
    ...
    assert r.json()["reason"]["text"] == "Porque aún no pides en Conveniencia."  # o la etiqueta que dé VERTICAL_LABELS, contraída
    assert r.json()["reason"]["basis"] == [{"kind": "sin_pedidos", "id": "conveniencia", "source": "contexto"}]

def test_vertical_to_try_rejects_stamped(client):
    r = client.post("/agent/offer", json={"moment": "vertical_por_probar", "context": {"stamped": []}})
    assert r.status_code == 422
```

(Con la etiqueta real de `VERTICAL_LABELS` del vertical que gane; adaptar los tests existentes de sellos a pedidos.)

- [ ] **Step 2: Run** los tests de ofertas → FAIL.
- [ ] **Step 3: Implement** `tried_verticals` y el nuevo `vertical_to_try` (`make_offer` pasa `tried_verticals(conn, user_id)`).
- [ ] **Step 4: Run** `make test` → verde salvo el contrato; luego `make contract` y `git rm` de las fixtures huérfanas; `make test` → todo verde.
- [ ] **Step 5: Commit** `git commit -m "feat(ofertas): la vertical por probar sale de los pedidos y no de los sellos; contrato al día"`.

### Task 3: La app sin pasaporte ni juego

**Files:**
- Create: `prototipo-app/src/lib/today.js` (o el módulo de utilidades de fecha que ya exista en la app, si lo hay) con `export function today(): string` idéntico al de `src/game/progress.js` (mismo formato y zona), y su test movido.
- Delete (git rm): `prototipo-app/src/game/` (todo), `prototipo-app/src/screens/game/` (todo), `prototipo-app/src/state/GameContext.jsx`, `GameContext.test.jsx`, `prototipo-app/src/api/game.js`, `prototipo-app/src/components/assistant/AssistantPanel.forget.test.jsx` si solo prueba el juego (si tiene algo más, conservar eso), `prototipo-app/docs/screenshots/31-juego-camino.jpg`, `32-juego-espera.jpg`
- Modify: `src/App.jsx` (`GameProvider`, pantalla `game`, `SCREENS_WITHOUT_CART`), `src/App.game.test.jsx` (conservar solo el test del aviso de privacidad; mover a `App.privacy.test.jsx` y borrar el resto), `src/App.stack.test.jsx`, `src/hooks/useNavigation.js` y su test (`'game'`), `src/api/testing.js` (todo lo del juego), `src/test/setup.js`, `vite.config.js` (comentario), `src/api/agent.js` (comentario), `src/api/client.js` y `client.test.js` (`didYouKnow`), `src/screens/home/live/LiveBlocks.jsx` (`Passport`, `STAMP_EMOJI`, `LEVEL_NAMES` e imports), `src/screens/home/live/LiveHomeFeed.jsx` (bloque `passport` en `ORDER` y `blocks`, pasos del `TOUR` del pasaporte, `GREETING` sin sellos, `useGame`, `freshStamp`, `visit` sin sellar, `openFromBlock`, `welcomeBack` sin sellos ni envío gratis, `poke()` manda `context: {}` y su acción ya no dice «Jugar»), `src/screens/home/live/live.css` (estilos del pasaporte y su bloque de movimiento reducido), `LiveHomeFeed.test.jsx` (sin `GameProvider` ni el `describe('pasaporte del juego')`; orden de bloques sin `passport`), `LiveBlocks.test.js`, `src/state/liveMemory.js` (`newStamp`), `src/components/assistant/AgentMessage.jsx` + `assistant.css` + `AgentMessage.test.jsx` (`DidYouKnow`), `AgentPresence.jsx` + test (`useGame`, pantalla `game`, «¿Qué puedo probar?» manda `context: {}`), `AssistantPanel.jsx` + `AssistantPanel.test.jsx` (mocks del juego, `stamped`, tests de Olvidar ↔ juego), `src/state/forgetAll.js` + `screens/account/forget.test.jsx` (sin `game`), `screens/account/demoRow.test.jsx`, `components/ForgetConfirm.jsx` (sin «y tu progreso del juego»), `components/ConnectionGate.jsx` (comentario), `screens/tracking/TrackingScreen.jsx` + `tracking.css` + test (`WaitingGame`), `state/AssistantContext.jsx` y `state/DemoContext.jsx` (comentarios), `scripts/screenshots.mjs` (tomas 31 y 32), `prototipo-app/README.md` (sección «Juego de verticales» y menciones)
- Los imports de `NEVER_PUSHED` que queden fuera del juego pasan a una constante local en el archivo que la use (la API ya filtra Farmacia y Licores).

**Interfaces:**
- Consumes: Task 2 (`vertical_por_probar` con `context: {}`).
- Produces: `today()` en su módulo nuevo; la Home del Prototipo final con bloques `['essentials', 'promos', 'turbo', 'plan', 'nearby', 'lower']`.

- [ ] **Step 1: Write the failing tests**: en `LiveHomeFeed.test.jsx`, «la Home no muestra el pasaporte» (`queryByText(/pasaporte/i)` es null y no hay botón «Jugar»); en `AgentPresence.test.jsx`, «¿Qué puedo probar?» manda `{moment: 'vertical_por_probar', context: {}}`; en `TrackingScreen.test.jsx`, no aparece «Juega mientras llega tu pedido»; en `useNavigation.test.jsx`, `#/game` abre la Home.
- [ ] **Step 2: Run** `npm test` → FAIL en esos tests.
- [ ] **Step 3: Remove the game from the app** (lista de Files), moviendo primero `today()`.
- [ ] **Step 4: Run** `cd prototipo-app && npm run lint && npm test && npm run build` → verde; `grep -rniE "pasaporte|passport|useGame|GameProvider|/game/|did_?you_?know|sabías" src scripts` no encuentra nada vivo.
- [ ] **Step 5: Commit** `git commit -m "feat(app): sin pasaporte ni juego; la vertical por probar sin sellos"`.

### Task 4: Panel, scripts, CI y despliegue

**Files:**
- Delete: `dashboard-empresa/src/views/mvp/GameUsage.jsx`
- Modify: `dashboard-empresa/src/views/mvp/MvpUsageView.jsx` y su test (sección «Juego»), `src/lib/labels.js` y su test (`viajes` como vertical del juego y `game: 'juego'`), `src/App.test.jsx` (aviso «Los datos simulados no incluyen el juego»), `scripts/update-fixtures.mjs` (comentario), `dashboard-empresa/README.md`, `dashboard-empresa/presentacion.html` (alt «y el pasaporte Rappi»)
- Modify: `scripts/mvp-check.sh` (pasos 4 juego y 5 dato fuera, `CHECK_GAME`, `USER_FILE` si solo servía al juego, `GAME_MIN_ITEMS`, `total`), `prototipo-app/scripts/mvp-check.mjs` (`finishRound`, `checkGame`, `checkDato`, import de `LABELS` del juego, lo del juego en `checkPanel`, flags y despacho), `scripts/mvp.sh` (`make -C rappi-ia knowledge`), `scripts/check-dist.sh` (`'make knowledge'`), `.github/workflows/ci.yml` (`GAME_MIN_ITEMS`, comentarios)
- Las revisiones de `mvp-check` se renumeran sin huecos; `OffersByMoment.jsx` conserva «Vertical por probar».

**Interfaces:**
- Consumes: Tasks 1-3.

- [ ] **Step 1: Write the failing test**: en `MvpUsageView.test.jsx`, «Uso del MVP no tiene sección Juego» (`queryByRole('heading', {name: /juego/i})` es null).
- [ ] **Step 2: Run** `cd dashboard-empresa && npm test` → FAIL.
- [ ] **Step 3: Remove** lo del juego del panel, los scripts y el CI.
- [ ] **Step 4: Run** `npm run lint && npm test` en el panel → verde; `bash -n scripts/mvp-check.sh scripts/mvp.sh scripts/check-dist.sh`; `node --check prototipo-app/scripts/mvp-check.mjs`; luego `make mvp-check` desde la raíz → todas las revisiones OK.
- [ ] **Step 5: Commit** `git commit -m "chore(sin-juego): panel, mvp-check, CI y despliegue sin el juego"`.

### Task 5: Documentos vigentes

**Files:**
- Modify: `CLAUDE.md` (descripción del repo; borrar el párrafo «Juego»; «tarjetas del juego» de los derivados), `README.md` (menciones, tabla de capturas sin 31 y 32), `docs/README.md`, `docs/instalacion.md` (pasos de `mvp-check` renumerados, tarjetas), `docs/demo.md` (sección «Juego de verticales» y menciones), `docs/diseno-ia.md` (métrica «Juego», ER sin `KNOWLEDGE_CARD`/`GAME_STATE`, fila de la etapa 4 como historia), `docs/despliegue.md` (`GAME_MIN_ITEMS`, `/game/state`, `game_state`), `docs/ecosistema-rappi.md`, `docs/sql/README.md`, `docs/jev.md` (`knowledge --jev-propuestas`), `docs/contexto-y-problema.md`, `rappi-ia/README.md`, `docs/diagramas-fuente/arquitectura-ia.json` y `rag-datos.json` (nodos y textos del juego; el HTML se regenera con Archify en la etapa 6), `docs/decisiones.md` (fila nueva con fecha 16-10-2026: el pasaporte y el juego salen; por qué: pedido del usuario tras hablar con Rappi, el foco pasa a la Home dinámica y al motor multivertical; costo: se pierde el «¿Sabías que…?» del agente; la historia queda en `rappi-evolucion-proyecto`, etiqueta `etapa-12-pasaporte-y-juego`)
- Add: el spec de esta tanda y este plan (ya están en la rama).

- [ ] **Step 1: Run** `grep -rniE "pasaporte|passport|juego|game_state|knowledge_card|did_you_know|sabías que|GAME_MIN" --include=*.md --include=*.json --include=*.html . | grep -v -E "docs/superpowers/|docs/resultados/juego-verificacion|node_modules|decisiones.md"` y anotar lo que queda.
- [ ] **Step 2: Edit** cada documento vigente para que describa el proyecto sin el juego (tono de propuesta, español).
- [ ] **Step 3: Run** el mismo grep → solo falsos positivos (videojuegos, «juego de sábanas», etc.) y los HTML de `docs/diagramas/` (pendientes de la etapa 6).
- [ ] **Step 4: Commit** `git commit -m "docs: el proyecto sin el pasaporte ni el juego; diseño y plan del motor multivertical"`.

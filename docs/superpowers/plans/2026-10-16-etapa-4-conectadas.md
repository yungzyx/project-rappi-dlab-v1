# Etapa 4: recomendaciones conectadas. Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que las ofertas del agente usen el motor: la vertical por probar busca la combinación que falta (Rest → Rest + Turbo → Rest + Turbo + Retail), aparece la recompra («¿Repetimos?»), los complementos prefieren el vertical que completa la combinación, «Para ti» suma lo más pedido, y el panel muestra las combinaciones junto a la tabla de Rappi.

**Architecture:** Un módulo `motor/recommend.py` mezcla lo más pedido de la población (`trends`) con el empuje de la compra cruzada aprendida (`cross_sell_rules`) y lo personal; la mezcla se evalúa con la misma evaluación por fechas (método nuevo `mezcla`) y su peso se elige solo. `offers/engine.py` lo consume. El panel lee dos métricas nuevas.

**Tech Stack:** Python + FastAPI (rappi-ia), React (prototipo-app, dashboard-empresa).

**Spec:** `docs/superpowers/specs/2026-10-16-motor-multivertical-design.md` (§4, Etapa 4).

## Global Constraints

- Guardias de ofertas intactas: nunca alcohol, Licores, Farmacia, bebé, salud ni sensibles por iniciativa propia (`offers/guards.py`: `is_offerable`, `offerable_vertical`, `search_products(..., offer=True)`).
- La razón que ve la persona habla de ella («Porque pides sushi…»), nunca de cifras de retención; la `basis` declara la fuente: `{"kind": "combinacion", "id": "<actual>→<objetivo>", "source": "rappi"}`, `{"kind": "compra_cruzada", "id": "<A>→<B>@<vertical>", "source": "poblacion:<fuente>"}`, `{"kind": "lo_mas_pedido", "id": "<vertical>", "source": "poblacion:<fuente>"}`, `{"kind": "recompra", "id": "<concepto>", "source": "pedidos"}`.
- «Rappi hoy» no recibe ofertas del motor (como hoy, el agente no cruza en `mode = 'actual'`).
- Los momentos nuevos van al contrato (`make contract`) y al panel («Ofertas del agente por momento»).
- Código en inglés; textos en español. `make test`/`make lint`, `npm test`/`npm run lint`.

## Review Focus

- Persona sin pedidos: la vertical por probar se comporta como hoy (orden fijo de lo no probado) y la recompra responde 204.
- Persona con Rest + Turbo + Retail: no hay paso de combinación; la vertical por probar ofrece un vertical que todavía no pide (como hoy) o 204.
- La combinación objetivo es Retail y el vertical con mejor predicción es Farmacia o Licores: se salta a la siguiente vertical del grupo que se pueda ofrecer.
- Recompra de un concepto que hoy no tiene oferta vigente en ese vertical: se busca otro producto del concepto; si no hay, 204.
- Un concepto olvidado («Olvidar») no vuelve en la recompra.

---

### Task 1: La mezcla «lo más pedido + compra cruzada» y su evaluación

**Files:**
- Create: `rappi-ia/src/rappi_ia/motor/recommend.py`
- Modify: `rappi-ia/src/rappi_ia/motor/evaluate.py` (método `mezcla` en la compra cruzada; ajuste de `CROSS_SELL_LAMBDA` en la grilla `GRID_LAMBDA = (0, 0.5, 1, 2, 4)` sobre validación; se guarda en la corrida como `"lambda_cruzada"`), `rappi-ia/src/rappi_ia/motor/build.py` (guardar el lambda)
- Test: `rappi-ia/tests/unit/test_motor_recommend.py`, `tests/unit/test_motor_evaluate.py`, `tests/integration/test_motor_recommend.py`

**Interfaces:**
- Produces:
  - `mix_scores(popular: dict[tuple[str, str], float], rules: dict[tuple[str, str], float], lam: float) -> dict[tuple[str, str], float]`: función pura; `popular` = cuota de pedidos del par (concepto, vertical) en la ventana; `rules` = lift máximo de las reglas que llegan a ese par desde los conceptos de la persona; puntaje = `popular × (1 + lam × max(0, lift − 1))`; un par sin popularidad no aparece.
  - `@dataclass CrossPick(concept_id: str, vertical: str, score: float, from_concept: str | None, lift: float | None)` y `cross_picks(conn, user_id: str, verticals: Iterable[str] | None = None, population: str | None = None, k: int = 3) -> list[CrossPick]`: conceptos de la persona en sus pedidos `propuesta` de los últimos 30 días → reglas de `cross_sell_rules` de la población → mezcla con `trends` (scope `concepto`) → sin pares que la persona ya pidió en ese vertical en 30 días, sin conceptos que no pasan `is_offerable`, sin verticales que no pasan `offerable_vertical`, solo `verticals` si se da; lambda de la última corrida (`latest_lambda(conn, population)`, por defecto 1.0).
  - La evaluación compara `reglas`, `lo_mas_pedido` y `mezcla` sobre las mismas personas.

- [ ] Tests: `mix_scores` con lam 0 = popularidad; con lam > 0 una regla con lift 3 sube un par por sobre otro más popular; `cross_picks` respeta guardias, verticales y lo ya pedido; la evaluación reporta `mezcla` y el ajuste elige el lambda con mejor precisión@3 en validación (empate → el menor).
- [ ] Implement; `make lint && make test`; correr `rappi-ia motor --source synthetic` en `rappi_staging` y anotar `mezcla` frente a las otras dos.
- [ ] Commit `feat(motor): la compra cruzada se mezcla con lo más pedido y su peso se elige solo`.

### Task 2: La vertical por probar busca la combinación que falta

**Files:**
- Modify: `rappi-ia/src/rappi_ia/offers/engine.py` (`vertical_to_try`), `rappi-ia/tests/integration/test_agent_offer.py`, `test_offer_affinity.py`, `test_contract.py` (ejemplo `vertical_por_probar` con una persona solo-restaurantes → Turbo)
- Create: `rappi-ia/tests/integration/test_offer_combo.py`

**Interfaces:**
- Consumes: `motor.predict.target_step`, `next_verticals`, `motor.recommend.cross_picks`, `trends` (scope `producto`).
- Produces: `vertical_to_try(conn, embedder, tried, interests, user_id)`:
  1. Si `target_step(conn, user_id)` da un grupo: candidatas = verticales de ese grupo que se pueden ofrecer, en el orden de `next_verticals`; si no, las de hoy (`TO_TRY_ORDER` sin probar, por afinidad).
  2. Para la primera candidata con algo que mostrar: productos de `cross_picks(conn, user_id, [vertical])` (búsqueda del concepto con `offer=True`, hasta 3); si no, lo más pedido del vertical (`trends` scope `producto`, solo ofertas vigentes de `v_latest_offers` o platos con precio vigente, guardias por nombre); si no, lo de hoy (`_offerable_deals` / `_popular_dishes`).
  3. Textos: con compra cruzada, `TO_TRY_CROSS_TEXT = "Para acompañar tu {origen}: {destino} en {vertical}."` y `REASON_TO_TRY_CROSS = "Porque pides {emoji} {name} y quienes lo piden suelen sumar {destino} en {vertical}."`; con lo más pedido, `TO_TRY_TOP_TEXT = "Lo más pedido en {vertical}."` y `REASON_TO_TRY_TOP = "Porque aún no pides en {vertical}: esto es lo que más se pide."`; con lo de hoy, los textos de hoy. `contract_articles` en todos.
  4. `basis` con la señal `combinacion` cuando hubo paso, más la de `compra_cruzada` o `lo_mas_pedido`.
- [ ] Tests de la Review Focus (sin pedidos, combinación completa, Farmacia/Licores saltados) y: persona solo-restaurantes con sushi → vertical `turbo`, `basis` con `combinacion` `rest→rest+turbo`.
- [ ] Implement; `make lint && make test && make contract`.
- [ ] Commit `feat(ofertas): la vertical por probar busca la combinación de verticales que más retiene`.

### Task 3: Recompra («¿Repetimos?»)

**Files:**
- Modify: `rappi-ia/src/rappi_ia/offers/engine.py` (momento `recompra`), `rappi-ia/src/rappi_ia/api/agent.py` (`RepeatIn` con `context: {}` estricto), `rappi-ia/src/rappi_ia/analytics/queries.py` (`recompra` en `OFFER_MOMENTS`), `rappi-ia/tests/integration/test_contract.py` (ejemplo `agent-offer-recompra`), `prototipo-app/src/api/agent.js`, `prototipo-app/src/screens/home/live/LiveHomeFeed.jsx` (bloque `recompra` tras `essentials` cuando hay oferta; registra `suggestion_shown`/`accepted` con origen `agent-recompra`), `dashboard-empresa/src/views/mvp/OffersByMoment.jsx` (etiqueta «Recompra»)
- Test: `rappi-ia/tests/integration/test_offer_repeat.py`, `LiveHomeFeed.test.jsx`, panel

**Interfaces:**
- Produces: `repeat_offer(conn, embedder, user_id) -> Offer | None`: filas de `replenishment` de la persona con `due_on` entre hoy − `interval_days` y hoy + 2 días, concepto que pasa `is_offerable` y vertical que pasa `offerable_vertical`, la más atrasada primero; producto = el último que compró de ese concepto si sigue vigente, si no, búsqueda del concepto en ese vertical (`offer=True`). `REPEAT_TEXT = "¿Repetimos {destino}? Lo pides cada {dias} días."`, `REASON_REPEAT = "Porque lo pides cada {dias} días y tu último pedido fue hace {hace}."`; acción `"Agregar"` (ruta a la tienda del producto) y «Después».
- [ ] Tests (Review Focus de recompra y «Olvidar»). - [ ] Implement. - [ ] `make test`, `make contract`, `npm test` en app y panel. - [ ] Commit `feat(ofertas): recompra en el momento justo según el ritmo de cada persona`.

### Task 4: Complementos que completan la combinación y «Para ti» con lo más pedido

**Files:**
- Modify: `rappi-ia/src/rappi_ia/agent/tools.py` (`suggest_complement`: candidatos curados + `cross_picks` del concepto de origen; ante dos candidatos cuyo peso difiere en menos de `SIMILAR_MARGIN = 0.1`, gana el del grupo de la combinación objetivo de la persona; parámetro nuevo `prefer_verticals: set[str] | None`), `rappi-ia/src/rappi_ia/offers/engine.py` (`complement` pasa `prefer_verticals` desde `target_step`), `rappi-ia/src/rappi_ia/api/app.py` (`/recommendations`: si quedan filas libres, «Lo más pedido en {vertical}» del vertical con mejor `next_verticals` que se pueda ofrecer y que no esté ya en las filas)
- Test: `rappi-ia/tests/integration/test_complement_combo.py`, `test_recommendations_trends.py`
- [ ] Tests: con dos complementos parecidos, gana el del vertical objetivo; con uno claramente mejor, gana ese; «Para ti» sin intereses muestra «Lo más pedido en …» y nunca Farmacia ni Licores.
- [ ] Implement; `make test`, `make contract`. - [ ] Commit `feat(agente): los complementos prefieren el vertical que completa la combinación y «Para ti» suma lo más pedido`.

### Task 5: El panel muestra las combinaciones y el motor

**Files:**
- Modify: `rappi-ia/src/rappi_ia/analytics/queries.py` (`combos(conn, source)` → `{"rappi": [...filas de combos.toml + total y nota], "propio": [...combo_stats de la fuente], "nota": ...}`; `motor(conn, source)` → pesos, lambda y evaluación de la última corrida `done` de la fuente; `home(conn, source)` → toques de accesos `vertical_open` por vertical: personas y toques), `rappi-ia/src/rappi_ia/api/app.py` (`ANALYTICS`), `rappi-ia/tests/integration/test_contract.py` (`PANEL_METRICS`), `dashboard-empresa/src/views/cross/…` (sección «Combinaciones de verticales»: las dos tablas lado a lado, la de Rappi rotulada «Dato compartido por Rappi (cohortes ene–jun 2026)» y la propia «Simulado: no es evidencia»; sección «Motor»: métricas de la evaluación y pesos), `dashboard-empresa/src/views/mvp/MvpUsageView.jsx` (sección «Accesos de la Home»), fixtures por `make contract`
- [ ] Tests de las tres métricas (formas, fuentes que no se mezclan) y de las vistas. - [ ] Implement. - [ ] Commit `feat(panel): combinaciones de verticales junto a la tabla de Rappi, el motor y los accesos de la Home`.

### Task 6: `mvp-check` y documentos

- `scripts/mvp-check.sh` + `prototipo-app/scripts/mvp-check.mjs`: revisión «combinación»: una persona nueva pide en Restaurantes, toca a Mochi y la oferta es de Turbo con su «¿Por qué?».
- Documentos: `docs/demo.md` (cómo mostrar la escalera de combinaciones y la recompra), `README.md` (la propuesta: la escalera Rest → Turbo → Retail con la tabla de Rappi como punto de partida), `docs/diseno-ia.md` (palancas «Recompra por ciclo» y «Segunda vertical» implementadas), `docs/decisiones.md`, `CLAUDE.md`.
- [ ] `make mvp-check` → todas OK. - [ ] Commit `docs: recomendaciones conectadas por combinación; mvp-check las revisa`.

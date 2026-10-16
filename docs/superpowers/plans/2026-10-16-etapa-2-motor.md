# Etapa 2: el motor multivertical en la base. Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Una capa nueva de la base que conecta todos los verticales: aprende el gusto por vertical de cada persona, el paso de un vertical a otro, las combinaciones de verticales y su retención, la compra cruzada, lo más pedido y la recompra; predice el próximo vertical y la combinación que conviene, y se evalúa sola.

**Architecture:** Paquete `rappi_ia/motor/`. Las cuentas son funciones puras sobre registros en memoria (`model.py`), así la evaluación por fechas reusa exactamente el mismo código que la corrida; `data.py` carga los registros desde la base y `build.py` escribe las tablas nuevas (migración 036) con su corrida en `layer_runs`. `predict.py` responde a la API. Los datos simulados se recalibran con la tabla de Rappi (`combos.toml`).

**Tech Stack:** Python 3.13, psycopg 3, Postgres 17, pytest.

**Spec:** `docs/superpowers/specs/2026-10-16-motor-multivertical-design.md` (§3 y §4, Etapa 2).

## Global Constraints

- Código en inglés; textos, logs, CLI, comentarios SQL y docs en español. Cada vista y columna de `capa` lleva comentario en español.
- Datos de personas: `synthetic` y `prototype` nunca se mezclan en una cifra ni en una tabla de población (columna `data_source`).
- Lo personal (afinidad y recompra) sale solo de los datos de la propia persona; lo de población, de una fuente (`config.MOTOR_POBLACION`, por defecto `"synthetic"`).
- «Rappi hoy» no enseña: pedidos con `mode = 'actual'` y eventos con `payload->>'mode' = 'actual'` no cuentan.
- Nunca conceptos sensibles (`concepts.sensitive`) en compra cruzada, tendencias de concepto o recompra.
- Farmacia y Licores solo suben por señales de la propia persona: en la predicción, su transición y su popularidad pesan 0.
- Agrupación gruesa: `rest` = restaurantes; `turbo` = turbo; `retail` = supermercado, conveniencia, farmacia, licores, mall, chocolatería. Nombre de una combinación: grupos en el orden `rest`, `turbo`, `retail` unidos por `+` (`rest+turbo+retail`); sin pedidos, `ninguna`.
- Constantes (en `model.py`, con su comentario): `AFFINITY_HALF_LIFE_DAYS = 30`, `AFFINITY_WINDOW_DAYS = 180`, pesos de afinidad `{"order": 5.0, "cart_add": 1.5, "vertical_open": 1.0, "view_store": 1.0, "search": 0.5, "view_item": 0.3}`, `TRANSITION_ALPHA = 1.0`, `CROSS_SELL_WINDOW_DAYS = 14`, `CROSS_SELL_MIN_USERS = 10`, `CROSS_SELL_MIN_LIFT = 1.2`, `TREND_WINDOW_DAYS = 28`, `TREND_MIN_PREV = 5`, `TREND_TOP_PRODUCTS = 50`, `REPLENISH_MIN_ORDERS = 3`, `REPLENISH_MAX_CV = 0.6`, `LEARNED_RETENTION_PRIOR = 100` (la retención aprendida pesa n/(n+100)), `LEARNED_RETENTION_MIN_USERS = 30`.
- La migración es `036_motor.sql` (la 035 es la de la etapa 1).
- `make test`/`make lint` en `rappi-ia/`; la base de tests es `rappi_ia_test`.

## Review Focus

- Persona sin pedidos ni eventos: `next_verticals` devuelve el orden por defecto (los 8 verticales, sin error) y `target_step` devuelve `None`.
- Un carro repartido en dos verticales (mismo `cart_id`) no cuenta como transición entre ellos.
- Un mes calendario incompleto al final del rango no entra al cálculo de retención (su M+1 no existe todavía).
- La recompra no sale de un mismo concepto pedido dos veces el mismo día (se cuentan días distintos).
- `build_motor` dos veces seguidas deja las mismas filas (reemplaza, no duplica), y un `synthetic` nuevo no borra lo de `prototype`.

---

### Task 1: Migración 036 y `combos.toml`

**Files:**
- Create: `rappi-scraper/src/rappi_scraper/storage/migrations/036_motor.sql`
- Create: `rappi-ia/src/rappi_ia/motor/__init__.py` (docstring del paquete en español), `rappi-ia/src/rappi_ia/motor/combos.toml`, `rappi-ia/src/rappi_ia/motor/combos.py`
- Modify: `rappi-ia/pyproject.toml` (package-data `"rappi_ia.motor" = ["*.toml"]`), `rappi-ia/src/rappi_ia/config.py` (`MOTOR_POBLACION = os.environ.get("MOTOR_POBLACION", "synthetic")`, con comentario), `rappi-ia/.env.example`, `rappi-ia/src/rappi_ia/events/store.py` (`vertical_open` en `EVENT_TYPES`; los clientes pueden mandarlo)
- Test: `rappi-ia/tests/unit/test_motor_combos.py`, `rappi-ia/tests/integration/test_motor_schema.py`

**Interfaces:**
- Produces (SQL), todas con `run_id bigint REFERENCES layer_runs ON DELETE SET NULL` salvo las personales:
  - `layer_runs.layer` acepta `'motor'`.
  - `app_events.type` acepta `'vertical_open'` (los 16 tipos de la 035 más este).
  - `user_vertical_affinity(user_id text REFERENCES app_users ON DELETE CASCADE, vertical text REFERENCES verticals(code), score real NOT NULL, orders int NOT NULL, signals int NOT NULL, last_ts timestamptz, updated_at timestamptz NOT NULL DEFAULT now(), PRIMARY KEY (user_id, vertical))`
  - `vertical_transitions(data_source text CHECK IN ('synthetic','prototype'), from_vertical text, to_vertical text, n int NOT NULL, prob real NOT NULL, run_id, PRIMARY KEY (data_source, from_vertical, to_vertical))`
  - `combo_stats(data_source, combo text, user_months int NOT NULL, pct_users real, pct_orders real, orders_per_user real, retention_m1 real, retention_n int, spend_per_user numeric, run_id, PRIMARY KEY (data_source, combo))` (`retention_n` = meses con M+1 completo)
  - `combo_steps(data_source, from_combo text, to_combo text, users int NOT NULL, prob real NOT NULL, run_id, PRIMARY KEY (data_source, from_combo, to_combo))`
  - `cross_sell_rules(data_source, from_concept text REFERENCES concepts ON DELETE CASCADE, from_vertical text, to_concept text REFERENCES concepts ON DELETE CASCADE, to_vertical text, users_from int, users_both int, confidence real, lift real, run_id, PRIMARY KEY (data_source, from_concept, from_vertical, to_concept, to_vertical))` + índice `(data_source, from_concept)`
  - `trends(data_source, scope text CHECK IN ('vertical','concepto','producto'), vertical text, item_key text, concept_id text REFERENCES concepts ON DELETE SET NULL, entity_type text, entity_id text, orders_now int, orders_prev int, users_now int, growth real, rank int, window_end date, run_id, PRIMARY KEY (data_source, scope, vertical, item_key))` (`item_key`: el vertical, el concepto o `entity_type:entity_id`)
  - `replenishment(user_id text REFERENCES app_users ON DELETE CASCADE, concept_id text REFERENCES concepts ON DELETE CASCADE, vertical text, orders int, interval_days real, cv real, last_ts timestamptz, due_on date, updated_at timestamptz NOT NULL DEFAULT now(), PRIMARY KEY (user_id, concept_id))`
  - Vistas `capa.user_vertical_affinity`, `capa.vertical_transitions`, `capa.combo_stats`, `capa.combo_steps`, `capa.cross_sell_rules`, `capa.trends`, `capa.replenishment` (SELECT * de cada tabla), con `COMMENT ON VIEW` y `COMMENT ON COLUMN` en español; `GRANT SELECT` igual que las demás vistas de `capa` (mirar 026 y `deploy/db/grants.sql`; la API escribe `user_vertical_affinity` y `replenishment`, así que van en los permisos de escritura de `rappi_api`).
- Produces (Python, `motor/combos.py`):
  - `GROUP_ORDER: tuple[str, ...] = ("rest", "turbo", "retail")`
  - `@dataclass(frozen=True) class ComboRow: combo: str; users: int; pct_users: float; pct_orders: float; orders_per_user: float; retention_m1: float; spend_per_user: float`
  - `@dataclass(frozen=True) class Combos: version: str; groups: dict[str, tuple[str, ...]]; group_of: dict[str, str]; rappi: dict[str, ComboRow]; rappi_total: ComboRow; source_note: str`
  - `load_combos() -> Combos` (con caché; valida: cada vertical de `verticals` en exactamente un grupo, `retention_m1` en [0,1], combos solo con grupos conocidos o `favor`)
  - `combo_key(groups: Iterable[str]) -> str`, `combo_of_verticals(verticals: Iterable[str]) -> str`
  - `expected_retention(combo: str, learned: dict[str, tuple[int, float]] | None = None) -> float | None`: la de Rappi mezclada con la aprendida `(n, ret)` si `n >= LEARNED_RETENTION_MIN_USERS`: `(ret_rappi * 100 + ret * n) / (100 + n)`; solo aprendida si Rappi no tiene la fila; `None` si ninguna.
  - `next_step(combo: str, learned=None) -> tuple[str, str, float] | None`: `(grupo_a_sumar, combo_objetivo, ganancia)` con la mayor ganancia positiva de retención esperada; `None` para `ninguna`, para `rest+turbo+retail` o si nada gana.

`combos.toml` lleva la tabla del spec §3 verbatim (filas `rest`, `turbo`, `rest+turbo`, `retail`, `rest+retail`, `rest+turbo+retail`, `turbo+retail`, `favor` y el total), retención como fracción (0.47…), gasto en la moneda de la fuente (`gasto_por_usuario = 42`), y `nota = "Dato compartido por el equipo de Rappi: cohortes de enero a junio de 2026, Chile, agrupación gruesa (MX crosswalk). Es una correlación, no un efecto."`

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/test_motor_combos.py
def test_every_vertical_has_one_group():
    c = load_combos()
    assert sorted(c.group_of) == sorted(["restaurantes","turbo","supermercado","conveniencia","farmacia","licores","mall","chocolateria"])
    assert c.group_of["mall"] == "retail" and c.group_of["turbo"] == "turbo"

def test_combo_key_is_canonical():
    assert combo_key(["retail","rest","turbo"]) == "rest+turbo+retail"
    assert combo_key([]) == "ninguna"
    assert combo_of_verticals(["mall","restaurantes","farmacia"]) == "rest+retail"

def test_rappi_table_is_loaded_verbatim():
    r = load_combos().rappi["rest+turbo+retail"]
    assert (r.users, r.pct_users, r.orders_per_user, r.retention_m1, r.spend_per_user) == (56000, 4.7, 10.5, 0.93, 257)

def test_next_step_follows_the_retention_ladder():
    assert next_step("rest")[:2] == ("turbo", "rest+turbo")            # 0.82 > 0.76
    assert next_step("rest+turbo")[:2] == ("retail", "rest+turbo+retail")
    assert next_step("retail")[:2] == ("turbo", "turbo+retail")        # 0.80 > 0.76
    assert next_step("turbo")[:2] == ("rest", "rest+turbo")            # 0.82 > 0.80
    assert next_step("rest+turbo+retail") is None and next_step("ninguna") is None

def test_learned_retention_needs_enough_people_and_blends():
    assert expected_retention("rest", {"rest": (10, 0.9)}) == 0.47
    assert expected_retention("rest", {"rest": (100, 0.67)}) == pytest.approx((0.47*100 + 0.67*100)/200)
```

```python
# tests/integration/test_motor_schema.py
def test_motor_tables_and_capa_views_exist(db): ...  # las 7 tablas y las 7 vistas, cada vista con comentario
def test_vertical_open_is_a_valid_event(db): ...      # insert de un app_events type='vertical_open' pasa
def test_layer_runs_accepts_motor(db): ...
def test_affinity_rows_go_with_the_person(db): ...    # borrar el app_users borra su afinidad y recompra
```

- [ ] **Step 2: Run** `scripts/with-test-db-lock.sh .venv/bin/python -m pytest tests/unit/test_motor_combos.py tests/integration/test_motor_schema.py -q` → FAIL.
- [ ] **Step 3: Implement** la migración, `combos.toml`, `combos.py`, config y `EVENT_TYPES`.
- [ ] **Step 4: Run** `make lint && make test` → verde.
- [ ] **Step 5: Commit** `feat(motor): tablas del motor multivertical (migración 036) y la tabla de combinaciones de Rappi`.

### Task 2: Datos simulados recalibrados con la tabla de Rappi

**Files:**
- Modify: `rappi-ia/src/rappi_ia/events/synth.py`
- Test: `rappi-ia/tests/unit/test_synth_personas.py` (agregar), `rappi-ia/tests/integration/test_synth_combos.py` (nuevo)

**Interfaces:**
- Consumes: `load_combos()`, `combo_of_verticals()` (Task 1).
- Produces:
  - `ARCHETYPES: dict[str, float]`: las 7 combinaciones de la tabla sin `favor`, con su `pct_users` renormalizado a 1.
  - `draw_archetype(rng: random.Random) -> str`
  - `effective_interests(persona: Persona, archetype: str) -> dict[str, dict[str, float]]`: los intereses de la persona solo en los verticales de los grupos del arquetipo. Si a un grupo del arquetipo no le queda ningún vertical: `turbo` toma los conceptos de `supermercado` y `conveniencia` de la persona (si no tiene, `GENERIC_INTERESTS["turbo"]`); `rest` usa `GENERIC_INTERESTS["restaurantes"]`; `retail` usa `GENERIC_INTERESTS["supermercado"]`. `GENERIC_INTERESTS = {"turbo": {"snacks-salados": 2, "gaseosas": 2, "lacteos": 1.5, "frutas": 1}, "restaurantes": {"pizza": 3, "hamburguesa": 2.5, "sushi": 2, "pollo-preparado": 1.5}, "supermercado": {"lacteos": 3, "frutas": 2, "limpieza": 2, "panaderia": 1.5}}` (sin alcohol ni bebé).
  - `archetype_cadence(archetype: str) -> float`: `30 / (orders_per_user × SESSIONS_PER_ORDER)` días, `SESSIONS_PER_ORDER = 1.3` (sesiones que no terminan en pedido: búsquedas sin resultado, carros abandonados, solo mirar).
  - La retención reemplaza a `MULTI_VERTICAL_RETENTION` (se borra): en cada sesión, la persona sigue activa con probabilidad `retention ** (gap / 30)` × los factores de búsquedas sin resultado y carros abandonados de hoy, donde `retention = expected_retention(combo de sus pedidos de los últimos 30 días)` (si `ninguna`, la de su arquetipo). Aceptar una sugerencia que la hace pedir en otro grupo cambia su combinación de verdad, y con ella su retención: **supuesto explícito** (la correlación de la tabla tratada como efecto), escrito en el docstring de SUPUESTOS.
  - `UserState` suma `archetype: str` e `interests: dict` (los efectivos); `_session` usa `s.interests` en lugar de `s.persona.interests`. El ritmo es `archetype_cadence(...) * exp(gauss(0, 0.35))` (la persona ya no fija el ritmo; sí las horas, el abandono y lo que prefiere).
  - `app_users.segment` sigue guardando el id de la persona.

- [ ] **Step 1: Write the failing tests**

```python
def test_archetypes_follow_rappi_shares():
    rng = random.Random(1); n = 20000
    counts = Counter(draw_archetype(rng) for _ in range(n))
    assert counts["rest"] / n == pytest.approx(62.6 / 93.4, abs=0.015)   # 93.4 = suma de las 7 filas sin favor
    assert set(counts) == {"rest","turbo","rest+turbo","retail","rest+retail","rest+turbo+retail","turbo+retail"}

def test_effective_interests_stay_in_the_archetype_groups():
    familia = next(p for p in PERSONAS if p.id == "familia")
    eff = effective_interests(familia, "rest+turbo")
    assert set(eff) <= {"restaurantes", "turbo"} and eff["turbo"]  # turbo sale del súper de la familia
    assert "panales" not in eff["turbo"] and "alimentacion-bebe" not in eff["turbo"]  # sin bebé fuera del súper

def test_cadence_follows_orders_per_user():
    assert archetype_cadence("rest+turbo+retail") < archetype_cadence("rest+turbo") < archetype_cadence("rest")
```

(Si `effective_interests` copia los intereses del súper a Turbo, saca los conceptos de los grupos `bebe` y `salud` y los sensibles; el test lo fija.)

```python
# tests/integration/test_synth_combos.py, con seed_demo y generate(db, users=600, weeks=26, seed=3, until=date(2026, 10, 4))
def test_synthetic_users_mostly_order_only_restaurants(db): ...   # en meses con pedidos, «rest» es la combinación más común
def test_more_groups_retain_more_in_the_simulation(db): ...        # retención M+1 de rest+turbo+retail > la de rest (medido con SQL directo sobre app_orders)
```

- [ ] **Step 2: Run** los tests → FAIL.
- [ ] **Step 3: Implement** en `synth.py` (docstring de SUPUESTOS al día).
- [ ] **Step 4: Run** `make test` → verde (incluidos los de analytics y contrato que usan `generate`; si una cifra fija de un test cambia por la recalibración, se actualiza el número, no la lógica; el contrato se regenera con `make contract`).
- [ ] **Step 5: Commit** `feat(synth): personas simuladas con la mezcla de combinaciones de Rappi y retención por combinación`.

### Task 3: El modelo (funciones puras) y la carga de datos

**Files:**
- Create: `rappi-ia/src/rappi_ia/motor/model.py`, `rappi-ia/src/rappi_ia/motor/data.py`
- Test: `rappi-ia/tests/unit/test_motor_model.py`, `rappi-ia/tests/integration/test_motor_data.py`

**Interfaces:**
- Produces (`data.py`), dataclasses congeladas:
  - `Line(concept_id: str | None, entity_type: str, entity_id: str, from_suggestion: bool)`
  - `Order(user_id: str, order_id: str, cart_id: str | None, ts: datetime, vertical: str, total: float, lines: tuple[Line, ...])`
  - `Signal(user_id: str, ts: datetime, kind: str, vertical: str)` (`kind` ∈ claves de `AFFINITY_WEIGHTS`)
  - `load_orders(conn, source: str, user_id: str | None = None, before: datetime | None = None) -> list[Order]` (solo `mode = 'propuesta'`, orden por `ts`)
  - `load_signals(conn, source: str, user_id: str | None = None, before=None) -> list[Signal]` (pedidos como `kind="order"` + eventos `cart_add`, `vertical_open`, `view_store`, `search` con vertical, `view_item`; sin `payload->>'mode' = 'actual'`)
  - `sensitive_concepts(conn) -> frozenset[str]`
- Produces (`model.py`), sin acceso a la base:
  - `affinity(signals: Iterable[Signal], now: datetime) -> dict[str, dict[str, float]]` → `user_id → vertical → puntaje` (ventana y vida media de las constantes)
  - `transitions(orders: Iterable[Order]) -> dict[str, dict[str, float]]` → P(to | from) con Laplace sobre los 8 verticales; pedidos consecutivos de la misma persona, saltando el siguiente si comparte `cart_id`.
  - `@dataclass ComboMonth(user_id, month: date, combo: str, orders: int, spend: float, retained: bool | None)` y `combo_months(orders) -> list[ComboMonth]` (`retained=None` si M+1 no está completo: el último mes con datos y el anterior a él si el rango termina antes de fin de mes)
  - `combo_stats(months: list[ComboMonth]) -> dict[str, dict]` (claves: `user_months, pct_users, pct_orders, orders_per_user, retention_m1, retention_n, spend_per_user`) y `combo_steps(months) -> dict[tuple[str, str], tuple[int, float]]`
  - `@dataclass Rule(from_concept, from_vertical, to_concept, to_vertical, users_from, users_both, confidence, lift)` y `cross_sell(orders, sensitive: frozenset[str]) -> list[Rule]` (B dentro de 14 días después de A, en otro vertical; B de `from_suggestion` no cuenta; umbrales de las constantes)
  - `@dataclass TrendRow(scope, vertical, item_key, concept_id, entity_type, entity_id, orders_now, orders_prev, users_now, growth, rank)` y `trends(orders, window_end: date, sensitive) -> list[TrendRow]`
  - `@dataclass Replenish(user_id, concept_id, vertical, orders, interval_days, cv, last_ts, due_on: date)` y `replenishment(orders, sensitive) -> list[Replenish]`
  - `popularity(orders, now: datetime) -> dict[str, float]` (cuota de pedidos por vertical en los últimos 28 días)
  - `DEFAULT_WEIGHTS = {"afinidad": 1.0, "transicion": 0.3, "popularidad": 0.1}` y `rank_verticals(aff: dict[str, float], last_vertical: str | None, trans, pop, weights) -> list[tuple[str, float]]`: normaliza la afinidad a suma 1, suma `a·afinidad + b·P(v | último) + c·popularidad`, con b = c = 0 para `farmacia` y `licores`; desempata con `DEFAULT_ORDER = ("restaurantes","turbo","supermercado","farmacia","mall","licores","conveniencia","chocolateria")`.

- [ ] **Step 1: Write the failing tests** (`test_motor_model.py`, con registros armados a mano; una prueba por función como mínimo):

```python
def test_affinity_decays_by_half_in_30_days():  # un pedido hoy = 5; uno hace 30 días = 2.5
def test_affinity_ignores_signals_older_than_180_days():
def test_split_cart_is_not_a_transition():      # pedidos A y B con el mismo cart_id → sin transición A→B
def test_transitions_are_smoothed_and_sum_to_one():
def test_last_month_without_next_month_has_no_retention():
def test_combo_stats_reproduce_shares_and_retention():   # 3 personas a mano → pct_users, retention_m1 exactos
def test_cross_sell_needs_ten_people_and_lift():          # 10 personas sushi→despensa-asiatica en turbo dentro de 14 días: sale; 9: no
def test_cross_sell_skips_suggested_lines_and_sensitive():
def test_trends_rank_and_growth():                        # growth = (now - prev) / max(prev, 5)
def test_replenishment_needs_three_days_and_regularity(): # 3 compras cada 14 días → due_on = última + 14; irregular (cv > 0.6) → nada; dos el mismo día cuentan una
def test_pharmacy_and_liquor_rise_only_by_own_signals():  # transición fuerte hacia farmacia y popularidad alta, sin afinidad propia → farmacia no sube del lugar por defecto
def test_rank_without_any_signal_is_the_default_order():
```

y `test_motor_data.py` (integración): `load_orders` excluye `mode='actual'` y la otra fuente; `load_signals` excluye eventos con `payload.mode = 'actual'` y trae `vertical_open`.

- [ ] **Step 2: Run** → FAIL. - [ ] **Step 3: Implement.** - [ ] **Step 4: Run** `make lint && make test` → verde.
- [ ] **Step 5: Commit** `feat(motor): el modelo (afinidad, transiciones, combinaciones, compra cruzada, tendencias y recompra) como funciones puras`.

### Task 4: Construir el motor, recalcular por persona y predecir

**Files:**
- Create: `rappi-ia/src/rappi_ia/motor/build.py`, `rappi-ia/src/rappi_ia/motor/predict.py`
- Modify: `rappi-ia/src/rappi_ia/api/app.py` (después de `POST /orders`, `background.add_task(refresh_user, connector, body.user_id)` junto a `recalculate_user_segments`; `DELETE /profile/{id}` («Olvidar») recalcula en el acto la afinidad y la recompra de la persona con su conexión, para que no quede lo que olvidó), `rappi-ia/src/rappi_ia/cli.py` (comando `motor [--source synthetic|prototype]`, sin `--source` corre las dos), `rappi-ia/Makefile` (`motor` en `.PHONY` y target; `layers` termina con `$(PY) -m rappi_ia motor`), `rappi-ia/README.md` (comando nuevo)
- Test: `rappi-ia/tests/integration/test_motor_build.py`, `rappi-ia/tests/integration/test_motor_predict.py`

**Interfaces:**
- Consumes: Task 3.
- Produces:
  - `build_motor(conn, source: str) -> dict` (counts): abre una corrida `layer='motor'` con `rules_version(load_combos().version, combos.toml, model.py)`, reemplaza las filas de esa fuente en las 5 tablas de población y la afinidad y recompra de todas las personas de esa fuente, y cierra la corrida con counts `{"transiciones", "combinaciones", "reglas", "tendencias", "afinidad", "recompra"}` más `"pesos"` (los de `evaluate.tune` de la Task 5 si ya existe; en esta tarea, `DEFAULT_WEIGHTS`).
  - `refresh_user(connector, user_id: str) -> None`: recalcula afinidad y recompra de una persona (abre su propia conexión, como `recalculate_user_segments`; nunca levanta excepción: registra y sigue).
  - `latest_weights(conn, source: str) -> dict[str, float]`: los `pesos` de la última corrida `motor` terminada de esa fuente; si no hay, `DEFAULT_WEIGHTS`.
  - `@dataclass VerticalScore(vertical: str, score: float, affinity: float, transition: float, popularity: float)` y `next_verticals(conn, user_id: str | None, population: str = config.MOTOR_POBLACION, now: datetime | None = None) -> list[VerticalScore]`: afinidad calculada en vivo con `load_signals(conn, source_de_la_persona, user_id)` (siempre fresca), transiciones y popularidad leídas de las tablas de `population`, pesos de `latest_weights`.
  - `current_combo(conn, user_id: str, now=None) -> str` (pedidos `propuesta` de los últimos 30 días) y `target_step(conn, user_id: str, population=…) -> tuple[str, str, float] | None` (`next_step` con la retención aprendida de `combo_stats` de la población: `{combo: (retention_n, retention_m1)}`).

- [ ] **Step 1: Write the failing tests**

```python
def test_build_motor_fills_every_table_and_records_the_run(db): ...       # tras seed_demo + generate pequeño
def test_build_motor_twice_replaces_rows(db): ...
def test_build_synthetic_keeps_prototype_rows(db): ...
def test_refresh_user_updates_affinity_after_an_order(db, client): ...    # POST /orders de una persona prototype → fila de afinidad del vertical
def test_forget_clears_affinity_and_replenishment(db, client): ...          # DELETE /profile/{id} → sin filas de afinidad ni recompra
def test_next_verticals_puts_the_most_used_first(db): ...                 # 3 pedidos en farmacia → farmacia primero
def test_next_verticals_without_history_is_the_default_order(db): ...
def test_target_step_for_a_restaurant_only_person_is_turbo(db): ...
def test_latest_weights_default_without_runs(db): ...
```

- [ ] **Step 2: Run** → FAIL. - [ ] **Step 3: Implement.** - [ ] **Step 4: Run** `make lint && make test` → verde.
- [ ] **Step 5: Commit** `feat(motor): rappi-ia motor arma la capa, recalcula a cada persona tras su pedido y predice el próximo vertical`.

### Task 5: Evaluación por fechas y ajuste de pesos

**Files:**
- Create: `rappi-ia/src/rappi_ia/motor/evaluate.py`
- Modify: `rappi-ia/src/rappi_ia/motor/build.py` (llama a `tune` y guarda pesos y métricas en la corrida), `rappi-ia/src/rappi_ia/cli.py` (`motor --sin-evaluar` para saltarla; el informe va a `config.DATA_DIR / "eval" / "motor.md"`)
- Test: `rappi-ia/tests/unit/test_motor_evaluate.py`

**Interfaces:**
- Consumes: Task 3 (`model.*`, `Order`, `Signal`).
- Produces:
  - `@dataclass Split(train_end: datetime, valid_end: datetime, test_end: datetime)` y `make_split(orders) -> Split | None` (fin = último pedido; prueba = últimos 28 días; validación = los 28 anteriores; `None` si hay menos de 84 días de datos).
  - `rank_metrics(ranking: list[str], relevant: set[str]) -> dict` con `hit1`, `hit3`, `mrr`, `ndcg` (binario, sobre los 8).
  - `evaluate_next_vertical(orders, signals, cut: datetime, end: datetime, weights) -> dict[str, dict]` para los métodos `orden_fijo`, `popularidad`, `afinidad`, `transicion`, `combinado`; personas con pedidos antes de `cut` y en `[cut, end)`.
  - `GRID_B = (0, 0.1, 0.3, 0.5, 1, 2)`, `GRID_C = (0, 0.05, 0.1, 0.3, 0.5, 1)`; `tune(orders, signals, split) -> dict[str, float]`: elige (b, c) con a = 1 por nDCG en validación; empata a favor de pesos más chicos.
  - `evaluate_cross_sell(orders, sensitive, cut, end) -> dict` (`precision3`, `cobertura`, y la línea base `lo_mas_pedido`), `evaluate_replenishment(orders, sensitive, cut, end) -> dict` (`error_mediano_dias`, `acierto_7_dias`, `n`).
  - `report(results: dict, source: str) -> str`: markdown en español con la advertencia «Datos simulados: esto prueba la mecánica del motor, no su efecto» cuando `source == "synthetic"`.

- [ ] **Step 1: Write the failing tests** (unitarios con datos armados): `test_rank_metrics_values` (ranking `["a","b","c"]`, relevantes `{"b"}` → hit1 0, hit3 1, mrr 0.5), `test_split_needs_84_days`, `test_tune_picks_transitions_when_people_alternate` (personas que siempre alternan A→B: el ajuste elige b > 0 y `combinado` supera a `afinidad` en prueba), `test_report_warns_on_synthetic`.
- [ ] **Step 2: Run** → FAIL. - [ ] **Step 3: Implement.** - [ ] **Step 4: Run** `make lint && make test` → verde; `rappi-ia synth` + `rappi-ia motor --source synthetic` sobre `rappi_ia_test` sembrada (o `rappi_staging` si existe) y leer `data/eval/motor.md`.
- [ ] **Step 5: Commit** `feat(motor): evaluación por fechas contra líneas base y pesos elegidos solos`.

### Task 6: Documentos y cifras

**Files:**
- Modify: `docs/capa-de-datos.md` (sección «Motor multivertical»: tablas, vistas, cómo se calcula, qué es población y qué es personal), `docs/decisiones.md` (filas del 16-10-2026: agrupación gruesa como supuesto; el motor aprende la población de `MOTOR_POBLACION` y lo declara; Farmacia y Licores solo por señales propias; simulados recalibrados con la tabla de Rappi y el supuesto de efecto), `docs/diseno-ia.md` (las aristas de simulados: la decisión cambia para el motor, con el porqué; «Recompra por ciclo» y «Segunda vertical» pasan a implementadas), `CLAUDE.md` (una línea: motor en `rappi_ia/motor/`, `make motor`, `MOTOR_POBLACION`), `README.md#resultados` (cifras del motor sobre simulados, rotuladas), `docs/resultados/motor-2026-10-16.md` (copia del informe con fecha)
- [ ] **Step 1:** Escribir. - [ ] **Step 2:** `grep` de coherencia (nombres de tablas y comandos iguales a los del código). - [ ] **Step 3: Commit** `docs(motor): la capa del motor, sus decisiones y sus cifras sobre datos simulados`.

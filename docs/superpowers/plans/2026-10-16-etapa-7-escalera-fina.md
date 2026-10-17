# Etapa 7: escalera fina por retención. Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Aumentar la retención llevando a cada persona a combinar más verticales, no solo los tres grupos de la tabla de Rappi. La escalera razona con las 8 verticales del catálogo más los servicios RappiFavor y RappiTravel: sigue dentro de Retail (súper, Express, Mall, Chocolatería) y continúa después de Rest + Turbo + Retail. Quien no pidió en los últimos 30 días también entra a la escalera, con su combinación de 90 días.

**Architecture:** Una combinación fina es el conjunto de verticales (y servicios) que la persona usó. Su retención esperada parte de la del grupo grueso (la tabla de Rappi mezclada con lo aprendido, como hoy) y suma un **rendimiento decreciente por cada vertical extra dentro de un grupo** (supuesto propio, en `combos.toml`); con al menos 30 personas, se mezcla con la retención fina aprendida. El paso es la vertical que más retención esperada suma. El motor guarda las combinaciones finas junto a las gruesas (migración 037) y el generador simulado aplica el mismo supuesto.

**Tech Stack:** Python, Postgres, React (sin cambios de app salvo textos si hace falta), panel React.

**Spec:** `docs/superpowers/specs/2026-10-16-motor-multivertical-design.md` (§3–§5) y la regla guía del usuario (16-10-2026): el objetivo es aumentar la retención; expandir la escalera a más verticales.

## Decisiones del usuario (16-10-2026)

- Escalera con **verticales finas**: las 8 del catálogo más RappiFavor y RappiTravel; Farmacia y Licores nunca se empujan.
- Supuesto de **rendimiento decreciente** dentro de cada grupo, rotulado como propio; con datos reales se reemplaza solo (la retención fina aprendida pesa n/(n+100) con n ≥ 30).

## Global Constraints

- Orden fino: `FINE_ORDER = ("restaurantes", "turbo", "supermercado", "conveniencia", "mall", "chocolateria", "farmacia", "licores", "favor", "travel")`. Nombre de una combinación fina: sus miembros en ese orden unidos por `+`; sin uso, `ninguna`.
- Servicios: `favor` (RappiFavor) y `travel` (RappiTravel). Se «usan» con un evento `service_opened` de la persona (`payload.servicio` = `rappifavor` / `rappitravel`); no tienen pedidos. Grupo grueso: `favor` es la fila «favor» de Rappi; `travel` no está en la tabla.
- Supuesto en `combos.toml` (sección `[rendimiento_decreciente]`): `reduccion_base = 0.10`, `decaimiento = 0.5`, `servicio = 0.05`. El supuesto reduce la parte que no vuelve: la j-ésima vertical del catálogo dentro de un grupo (j ≥ 2) tiene f = reduccion_base·decaimiento^(j−2) (2.ª −10 %, 3.ª −5 %, 4.ª −2,5 %…) y cada servicio usado, f = `servicio`. La retención fina esperada = 1 − (1 − gruesa)·Π(1 − f), donde «gruesa» es la retención gruesa esperada (la de hoy, `expected_retention`) de los grupos presentes (sin servicios; si solo hay servicios: `favor` → la fila «favor» de Rappi, que no reduce nada, y `travel` reduce con `servicio`; `travel` solo → `None`); nunca llega a 1 y no hay tope fijo. Si hay retención fina aprendida con n ≥ 30, se mezcla: `(esperada·100 + aprendida·n)/(100 + n)`.
- Farmacia y Licores nunca son un paso (`OWN_SIGNALS_ONLY`); un servicio solo es paso si no queda ninguna vertical del catálogo con ganancia > 0.
- Ventanas: combinación actual = últimos 30 días; si está vacía, los últimos 90 (`LAPSED_COMBO_DAYS = 90`).
- El texto que ve la persona no cita retenciones; la `basis` declara la fuente: `combinacion` con id `<actual fina>→<objetivo fina>` y fuente `rappi`, `rappi+supuesto` (si pesó el bono) o `rappi+supuesto+poblacion:<fuente>` (si pesó lo aprendido).
- Código en inglés; textos en español; `make test`/`make lint`; `make contract`; `npm test` del panel; migración `037_*.sql` nueva (no editar la 036).

## Review Focus

- Persona con Rest + Turbo + Retail (solo súper): el paso es otra vertical de Retail (Express, Mall o Chocolatería), nunca Farmacia ni Licores.
- Persona que usa todas las verticales del catálogo que se pueden ofrecer: el paso es RappiFavor o RappiTravel; si también los usó, `None`.
- Persona sin pedidos en 30 días pero con pedidos en 90: entra a la escalera con su combinación de 90 días; sin pedidos en 90, `None` (oferta de siempre).
- La escalera gruesa sigue mandando: a quien solo pide en Restaurantes se le propone Turbo (un grupo nuevo suma mucho más que una vertical extra dentro de un grupo).
- El supuesto nunca hace que la retención esperada pase de 0,97.

---

### Task 1: El modelo fino de combinaciones (migración 037 y `combos.py`)

**Files:** `rappi-scraper/src/rappi_scraper/storage/migrations/037_combos_finos.sql`, `rappi-ia/src/rappi_ia/motor/combos.toml`, `rappi-ia/src/rappi_ia/motor/combos.py`, tests `tests/unit/test_motor_combos.py`, `tests/integration/test_motor_schema.py`.

- Migración 037: `combo_stats` y `combo_steps` ganan `nivel text NOT NULL DEFAULT 'grueso' CHECK (nivel IN ('grueso', 'fino'))`; la llave primaria pasa a incluir `nivel` (`(data_source, nivel, combo)` y `(data_source, nivel, from_combo, to_combo)`); las vistas `capa.combo_stats` y `capa.combo_steps` se recrean con la columna y su comentario en español.
- `combos.toml`: sección `[rendimiento_decreciente]` con los valores de Global Constraints y su nota («supuesto propio: cada vertical extra dentro de un grupo suma algo de retención, cada vez menos; con datos reales se reemplaza por lo aprendido»); `[servicios]` con `favor = "rappifavor"` y `travel = "rappitravel"`.
- `combos.py` produce: `FINE_ORDER`; `fine_key(members) -> str`; `fine_of(verticals, services=()) -> str`; `group_counts(fine) -> dict[str, int]`; `fine_bonus(fine) -> float`; `expected_fine_retention(fine, learned_coarse=None, learned_fine=None) -> float | None`; `@dataclass(frozen=True) Step(vertical: str, current: str, target: str, gain: float, used_assumption: bool)`; `next_fine_step(fine, candidates: Sequence[str], learned_coarse=None, learned_fine=None) -> Step | None` (candidatos en el orden de preferencia de la persona; desempate por ese orden; servicios solo si ninguna vertical del catálogo gana > 0).
- Tests: claves y orden; bono 0,04/0,02/0,01; tope 0,97; servicios; mezcla con lo aprendido; los cinco casos de la Review Focus con candidatos armados a mano; `next_step` grueso de hoy sin cambios.
- [ ] Tests → implementar → `make lint && make test` → commit `feat(motor): combinaciones finas con rendimiento decreciente por vertical (migración 037)`.

### Task 2: Aprender y simular a nivel fino

**Files:** `rappi-ia/src/rappi_ia/motor/model.py` (`combo_months` con nivel; o una función hermana `fine_combo_months`), `motor/build.py` (escribe `nivel = 'fino'` además de `grueso`), `events/synth.py` (la supervivencia usa `expected_fine_retention` de las verticales de los últimos 30 días; el docstring SUPUESTOS suma el supuesto), tests.

- Las filas finas aprendidas solo cuentan verticales del catálogo (los simulados no abren servicios con regularidad).
- Medir en `rappi_staging` (`synth` + `segments --source synthetic` + `motor --source synthetic`): la tabla fina aprendida (top 15 combinaciones con su retención) y que la gruesa siga parecida a la de antes (anotar ambas en el informe).
- [ ] Tests → implementar → `make test` (+ `make contract`, revirtiendo cambios solo de fecha) → commit `feat(motor): el motor aprende y el generador simula combinaciones finas`.

### Task 3: El paso fino en las ofertas

**Files:** `motor/predict.py` (`current_fine(conn, user_id, now=None) -> str` con 30 días y respaldo de 90; servicios por `service_opened`; `target_step` devuelve `Step | None` con candidatos ordenados por `next_verticals` de la persona, sin Farmacia ni Licores ni verticales que no se pueden ofrecer, y los servicios al final; `step_signal(conn, step, population)` con la fuente de Global Constraints), `offers/engine.py` (`vertical_to_try` usa `step.vertical` directo; si es un servicio, oferta sin productos: texto `"¿Conoces {servicio}? {beneficio}"` con `{beneficio}` de la taxonomía de servicios o una frase fija por servicio, razón `"Porque ya pides en {n} verticales: {servicio} te ayuda con lo que no está en la app."` para Favor y `"Porque ya pides en {n} verticales: con {servicio} planeas el viaje."` para Travel, acción a su pantalla (`["favor"]` / `["travel"]`)), `agent/tools.py` (`suggest_complement` prefiere `{step.vertical}` en el desempate), `api/agent.py` si cambia la forma, contrato y tests.
- [ ] Tests (los de Review Focus por la API, y que `basis` declare el paso fino) → implementar → `make test && make contract` → `npm test` en prototipo-app (el globo de Mochi y AgentPresence con una oferta sin productos) → commit `feat(ofertas): la escalera sigue vertical por vertical y suma RappiFavor y RappiTravel`.

### Task 4: Medir el paso, panel y documentos

**Files:** `motor/evaluate.py` (métrica nueva «paso»: entre quienes suman una vertical nueva en la ventana de prueba, ¿el paso calculado al corte es esa vertical? acierto@1 contra la línea base «la vertical que más se suma en la población»; solo verticales del catálogo), `analytics/queries.py` y el panel (`combos` con la tabla fina aprendida rotulada «Simulado: no es evidencia» y el supuesto explicado), documentos (`docs/capa-de-datos.md`, `docs/decisiones.md` con las dos decisiones del usuario, `docs/demo.md` con la escalera fina, `README.md#resultados` con la cifra nueva rotulada, `docs/resultados/motor-2026-10-16.md` sección «Escalera fina»), `CLAUDE.md` (una línea).
- [ ] Implementar con tests → correr `rappi-ia motor --source synthetic` en `rappi_staging` y anotar la métrica → `make test`, panel `npm test`, `make mvp-check` (7 de 7) → commit `feat(motor): el paso fino se mide y el panel muestra las combinaciones finas`.

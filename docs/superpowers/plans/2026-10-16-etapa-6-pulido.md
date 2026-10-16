# Etapa 6: pulido final del repo. Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que el repo se lea de punta a punta como una propuesta pulida: lo primero que ve Rappi cuenta el motor multivertical, la Home dinámica y la tabla de combinaciones; sin restos del pasaporte ni del juego; diagramas, capturas y documentos al día; código y formato limpios.

**Architecture:** Cinco tareas sobre la auditoría `docs/superpowers/plans/2026-10-16-auditoria-pulido.md` (copia del informe de auditoría de solo lectura): higiene de código, diagramas (Archify), capturas, narrativa principal y documentos de referencia.

**Tech Stack:** Python, React, Markdown, Archify (diagramas), Playwright (capturas).

**Spec:** `docs/superpowers/specs/2026-10-16-motor-multivertical-design.md` (§4, Etapa 6).

## Global Constraints

- Tono: propuesta independiente y respetuosa a Rappi (no afiliada); todo en español; cifras con su rótulo (real, simulado, uso del MVP, dato compartido por Rappi).
- Sin cambios de comportamiento salvo los que se nombran (formato, imports públicos, código muerto, altura de la leyenda).
- Las capturas que escriben pedidos usan `rappi_staging`, nunca `rappi`.
- Las fechas y los documentos fechados (`docs/superpowers/`, `docs/resultados/*-fecha.md`) son historia: no se reescriben, salvo erratas.
- `make test`/`make lint` (rappi-ia, rappi-scraper), `npm test`/`npm run lint` (las dos apps), `make mvp-check`.

## Decisiones tomadas (controlador, 16-10-2026)

1. `docs/simulacion-catalogo.html` (sin seguimiento en `~/Rappi`): no se toca ni se sube.
2. «Lo más pedido» se mantiene como rótulo; la fuente va en `basis` y en los documentos (fila en `decisiones.md`).
3. Productos sin alcohol desde tiendas rotuladas «Licores» dentro de Express o el súper: permitidos (fila en `decisiones.md`).
4. Contenido (aristas curadas nuevas, conceptos mal asignados): fuera de esta etapa; queda como propuesta para el usuario.
5. Ramas `[gone]` y worktrees viejos de `~/Rappi`: no se tocan (uno guarda una rama local sin subir).
6. Capturas: con la API sobre `rappi_staging` (puede escribir ahí); nunca pedidos en `rappi`.

## Review Focus

- Un enlace relativo roto en cualquier `.md` (verificar con un script: 0 rotos).
- Una cifra en el README que no coincide con `docs/resultados/`.
- Una captura o diagrama que todavía muestra el pasaporte, «Jugar» o «/game».
- Un `prettier --write` masivo que cambia comportamiento (solo formato; tests verdes antes y después).
- Un import privado reemplazado que rompe un test que lo parchaba.

---

### Task 1: Higiene de código (sin cambiar comportamiento)
- Formato: commit aparte con prettier en `prototipo-app` y `dashboard-empresa` (al panel se le agregan `.prettierrc`, la dependencia y el script `format`); sumar `prettier --check` a los dos jobs de `.github/workflows/ci.yml`.
- `rappi-ia/pyproject.toml`: `httpx` → `httpx2` en `dev`.
- Imports privados: `catalog/stores.py` (`_product` → público) y quien lo usa (`catalog/deals.py`, `catalog/restaurants.py`, `offers/engine.py`); `retrieval/hybrid.py` (`_concepts_of`); `agent/verticals.py` (`_SHARES`); `motor/model.py`, `motor/predict.py`.
- Borrar `prototipo-app/src/components/NotReplicated.jsx` y `not-replicated.css`; quitar los `export` que sobran y las 4 reglas CSS sin uso; `scripts/mvp-check.sh` sin `mochi-plan`.
- «Bigotes» → «Mochi»/«agent» en `rappi-scraper/storage/search.py:109` y en los nombres y docstrings de tests (sin tocar las pruebas de vocativo); `test_spare_connection.py:105`.
- Reservar la altura de la leyenda de la Home (`home.css`).
- Verificación: `make lint test` (rappi-ia, rappi-scraper), `npm run lint && npm test && npx prettier --check src scripts` (las dos apps), `make mvp-check`, y pytest sin el aviso de Starlette.

### Task 2: Diagramas (Archify)
- Archivos: `docs/diagramas-fuente/rag-datos.json`, `arquitectura-ia.json`, opcional el nuevo `motor-flujo.json`; regenerar `docs/diagramas/{rag-datos,arquitectura-ia,despliegue}.html/.png` (y `motor-flujo.*`).
- Copiar `rag-datos.png` a `dashboard-empresa/public/presentacion/flujo-de-datos.png`.
- Verificación: validación de Archify; que el HTML y el PNG no tengan «tarjetas», «juego» ni «/game»; que el motor y la Home aparezcan.

### Task 3: Capturas
- `prototipo-app/scripts/screenshots.mjs`: capturas nuevas, «Home dinámica» (accesos con la leyenda), «¿Repetimos?» y «Mochi propone la siguiente vertical» con `page.route` sobre los fixtures del contrato (sin escribir en la base para esas capturas). Volver a tomar `00`, `01`, `26` y el resto.
- Pasar la nueva portada a `dashboard-empresa/public/presentacion/prototipo-final.jpg`.
- `dashboard-empresa`: `npm run screenshots` (sobre todo `4-verticales`, con combinaciones y motor).
- Ojo: la compra de 25-27 escribe en la base que use el MVP. Pedirle permiso al usuario o usar `rappi_staging`.
- Verificación: revisar cada imagen a ojo; `grep` de los `alt` en los README.

### Task 4: Narrativa principal (README raíz, presentación, índice)
- `README.md`:
  - entrada con el motor, la Home y la tabla de Rappi;
  - «dos piezas» → cuatro, con el motor primero;
  - quitar «se puede jugar»;
  - «Cómo funciona» con el motor;
  - real/simulado/**compartido por Rappi**;
  - tests y conceptos recontados;
  - panel con Combinaciones, Motor y Accesos de la Home;
  - el límite del motor;
  - el diagrama nuevo.
- `dashboard-empresa/presentacion.html`: quitar «sin base de datos, solo Node»; sección del motor; tests y conceptos al día; fecha nueva.
- `docs/README.md`: fila del motor con la spec, los 5 planes y los 2 informes.
- `docs/contexto-y-problema.md`: fase del motor y la tabla de Rappi.
- `docs/demo.md`: líneas 58 y 86; Home y escalera en el recorrido principal.
- Verificación: script de enlaces (0 rotos); releer de punta a punta; las cifras coinciden con `docs/resultados/`.

### Task 5: Documentos de referencia y CLAUDE.md
- `rappi-ia/README.md`:
  - piezas (motor, ofertas);
  - endpoints (`/profile/{id}/verticales`, momento `recompra`, analytics sin `game` y con `combos`/`motor`/`home`);
  - migración 036;
  - conteos;
  - `make help` de `layers` y `synth`.
- `prototipo-app/README.md`: sección «La Home que aprende», fecha de las capturas, las 7 revisiones de mvp-check.
- `dashboard-empresa/README.md`: Entre verticales (combinaciones y motor), las 3 secciones de Uso del MVP y los momentos.
- `docs/diseno-ia.md`: fecha, cifra de «sin resultado» (línea 68), §4b del motor, `agent-recompra`, §7 con las etapas del 16-10.
- `docs/capa-de-datos.md:18`.
- `docs/despliegue.md`: `MOTOR_POBLACION`, el motor en el servidor y las tablas personales.
- `docs/decisiones.md`:
  - marcar como reemplazadas las filas 64, 135-139, 146, 147, 153, 164, 188, 193 y 198;
  - fila de las tiendas «Licores»;
  - opcional, un resumen de lo vigente arriba.
- `docs/resultados/motor-2026-10-16.md:204`.
- `CLAUDE.md`: línea 5 (Accesos de la Home); acortar las viñetas 25-31 a convenciones e invariantes, con enlaces.
- Verificación: script de enlaces; `git grep -n -E "pasaporte|/game|133 conceptos|dos piezas"` sin resultados fuera de lo fechado o histórico.


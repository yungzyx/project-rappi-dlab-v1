# Auditoría para el pulido final (etapa 6)

Rama auditada: `chore/qa-motor` (4952fe68, contiene las etapas 1 a 5). Solo lectura: no se editó nada ni se escribió en ninguna base.
Fecha: 16-10-2026.

Severidad: **alta** = lo ve quien recibe la propuesta (Rappi) o afirma algo falso; **media** = desactualizado o incompleto, confunde a quien lee el repo; **baja** = higiene.
Esfuerzo: **S** < 30 min · **M** 30–90 min · **L** > 90 min.

Verificaciones hechas:
- **Enlaces:** script propio sobre los 55 `.md` versionados, 333 enlaces relativos (archivos y anclas `#`). **0 rotos.**
- **Ruff:** `ruff check` y `ruff format --check` limpios en rappi-ia (198 archivos) y rappi-scraper (55).
- **Prettier:** `prettier --check` falla en las dos apps (detalle en §4).
- **`make help`:** corrido en la raíz, rappi-ia y rappi-scraper.
- **Capturas:** revisadas una por una.
- **Ledgers:** leídos los `progress.md` de las 5 etapas y comprobado cada pendiente contra el código.

---

## 1. Narrativa y documentación

### README.md (raíz)

El orden ya es el pedido: problema → propuesta → cómo funciona → resultados → probarlo. Lo que falla es que el motor y la Home dinámica, que según la spec (`2026-10-16-motor-multivertical-design.md:15`) son «la innovación central», no están arriba, y quedan restos del juego.

| Sev. | Lugar | Qué | Arreglo | Esf. |
|---|---|---|---|---|
| alta | README.md:10-12 | La imagen de portada `00-modo-demo.jpg` muestra «Tu pasaporte Rappi», «Jugar» y «junta sellos en tu pasaporte». | Volver a tomar las capturas (§3) | — (en §3) |
| alta | README.md:44 | «Farmacia se puede jugar pero nunca se propone»: el juego ya no existe. | «Farmacia nunca se propone por iniciativa propia» | S |
| alta | README.md:22 | «El prototipo final lo muestra en **dos** piezas», pero la tabla tiene 4 (Mochi en la Home, Recomendaciones conectadas, Home que aprende el orden, Buscador con Mochi). | Corregir el conteo y poner primero las 2 piezas del motor | S |
| alta | README.md:1-3 | El título y la entrada hablan de Mochi y del buscador. No nombran el motor (escalera Restaurantes → Turbo → Retail, compra cruzada, recompra), la Home dinámica ni la tabla de combinaciones que compartió Rappi. | Reescribir la entrada: «un motor que conecta las verticales…», nombrar la tabla de Rappi («dato compartido por Rappi», correlación, no efecto) y la Home | M |
| media | README.md:50-58 | «Cómo funciona», pasos 1-5: el motor no aparece. Corre offline en `make layers`/`post-refresh` y online en `/agent/offer` y `/profile/{id}/verticales`. | Sumar el motor al paso 3 (offline) y al 4 o 5 (ofertas y Home) | S |
| media | README.md:62-71 | La tabla de diagramas no tiene uno del motor. | Ligar al diagrama nuevo o actualizado (§2) | S |
| media | README.md:88 | «Tests (11-10-2026): scraper 262 · rappi-ia 1638 · prototipo 732 · panel 114». El ledger de la etapa 5 da rappi-ia 2416 passed + 2 skipped. | Recontar con `pytest --collect-only -q` y `npm test`; cambiar la fecha | S |
| media | README.md:83 | «133 conceptos · 103 complementos curados» aparece como cifra vigente. La taxonomía tiene hoy 116 conceptos + 20 grupos = 136 (3 asiáticos agregados el 14-10) y `complements.toml` tiene 106 aristas. | Recontar (`make concepts --solo-reporte`) o dejar la fecha explícita | S |
| media | README.md:160-164 | «Qué es real y qué es simulado» no menciona la tabla de combinaciones de Rappi, un tercer tipo de dato. | Agregar «**Compartido por Rappi:** la tabla de combinaciones (cohortes ene–jun 2026), correlación, no efecto» | S |
| media | README.md:198-201 | En el panel faltan «Combinaciones de verticales» y «Motor» (pestaña Entre verticales) y «Accesos de la Home» (Uso del MVP). A la lista de momentos le faltan «recompra» y «perfil de gusto». | Actualizar los dos párrafos | S |
| baja | README.md:166-174 | En «Límites» no está el del motor: población simulada, λ = 0 hace que «Para tu pedido de …» no se vea en la demo, y la tabla es una correlación. | Una viñeta, con enlace a decisiones | S |
| baja | README.md:113 | Recompra «0,114 sobre 79 predicciones … una variante … se descartó»: se entiende, pero es muy denso para una tabla. | Dejar la cifra en la tabla y mover el intento descartado al informe | S |

### docs/README.md (índice)

Todos los documentos de `docs/*.md` están enlazados y no hay enlaces rotos.

| Sev. | Lugar | Qué | Arreglo | Esf. |
|---|---|---|---|---|
| media | docs/README.md:28 | «Hacia dónde va el proyecto: la Home dinámica y el motor» enlaza solo el plan de la **etapa 1**. Las etapas 2-5 ya están hechas: el texto sigue en futuro y no liga los planes 2-5. | Fila nueva «Motor multivertical y Home dinámica (16-10, 5 etapas)» con la spec, los 5 planes y los 2 informes de resultados | S |
| baja | docs/README.md:26 | «Qué es el MVP integrado (7 etapas)» está bien, pero no hay una fila equivalente para las etapas del motor. | Ídem | S |
| baja | docs/README.md:35-41 | A la tabla de diagramas le falta el del motor, si se crea (§2). | — | S |

### CLAUDE.md

Tiene 38 líneas y 11,6 KB. La regla de `decisiones.md:212` dice que CLAUDE.md lleva solo convenciones, pero varias viñetas son documentación de diseño.

| Sev. | Lugar | Qué | Arreglo | Esf. |
|---|---|---|---|---|
| media | CLAUDE.md:5 | Dice que «Uso del MVP» muestra «ofertas del agente por momento y búsquedas sin resultado». Falta «Accesos de la Home» (`dashboard-empresa/src/views/mvp/MvpUsageView.jsx:80`). | Agregarlo | S |
| media | CLAUDE.md:25-28 | Las viñetas del motor, las ofertas conectadas, la Home dinámica y los perfiles de gusto suman unas 900 palabras: fórmulas (`popularidad × (1 + λ·…)`), kinds de `basis`, reglas de Turbo y Farmacia. Repiten `capa-de-datos.md` y `diseno-ia.md`. | Dejar en cada una dónde vive el código, el comando y la invariante que no hay que romper (por ejemplo, «Farmacia y Licores solo por señales propias; ningún concepto sensible en compra cruzada»), y enlazar a la doc | M |
| baja | CLAUDE.md:29, 31 | Las viñetas de precarga y de precio vigente también son largas, aunque son invariantes reales («no recalcular la vigencia…»). | Acortar sin perder la regla | S |
| baja | CLAUDE.md:11 | «Los documentos fechados todavía dicen Bigotes»: es cierto y sirve. | — | — |

### docs/decisiones.md

Tiene 7 secciones temáticas. Dentro de cada una el orden de fechas se mezcla y casi todas las filas son muy largas (más de 2.000 caracteres): la tabla cuesta leerla en GitHub.

| Sev. | Lugar | Qué | Arreglo | Esf. |
|---|---|---|---|---|
| media | decisiones.md:135-139, 146, 147, 153 | Las filas de «Bigotes vivo», el pasaporte, el juego, la guía con «Jugar» y el juego en el RAG no se marcan como reemplazadas. La 155 dice «las filas anteriores sobre el juego quedan como historia», pero cada fila sigue leyéndose como vigente. | Prefijo «**Reemplazada el 16-10** (ver fila del pasaporte)» en cada una, o moverlas a una sección «Historia» al final | S |
| media | decisiones.md:164 | «Las aristas aprendidas de datos simulados solo se ven en el panel; el agente no las usa». La 171 dice que esto cambia con el motor. | Marcar «Matizada el 16-10 (motor, ver fila …)» | S |
| media | decisiones.md:198 | «el chat del prototipo espera 8 s y marca «Respuesta local» si contestan sus reglas». Ya no hay chat ni reglas locales (filas 148 y 152). | Marcar como reemplazada | S |
| media | decisiones.md:64 | «CLIP … Whisper (faster-whisper)» como modelos vigentes. La 152 los quitó. | Marcar como reemplazada | S |
| baja | decisiones.md:188, 193 | Citan `make images`, que ya no existe en ningún Makefile. | Marcar como reemplazada o histórica | S |
| baja | decisiones.md:155 | «Las capturas 00 y 01 todavía muestran el pasaporte y se vuelven a tomar en una etapa posterior»: sigue abierto (§3). | Cerrarlo al tomar las capturas | — |
| baja | decisiones.md (falta la fila; sección «Agente (Mochi)») | El QA dejó como «decisión pendiente» si se permiten productos sin alcohol de tiendas rotuladas «Licores» dentro de Express o el súper (`docs/resultados/qa-motor-2026-10-16.md:82`). El ledger de la etapa 5 dice «documentar en decisiones» y no se hizo. | Agregar la fila o preguntar al usuario | S |
| baja | estructura | Leer 220 filas de una línea muy larga es difícil. | Opcional: un índice al inicio con «Lo vigente en 10 líneas» que enlace a las filas clave | M |

### docs/diseno-ia.md

| Sev. | Lugar | Qué | Arreglo | Esf. |
|---|---|---|---|---|
| alta | diseno-ia.md:68 | Contradice al README y al reporte: «precisión 1,00 y recall 0,71 (29 de 41) … Mochi anota 21 de las 41». El reporte del 06-10 (`resultados/busqueda-2026-10-06.md:74,78`) y README:87 dicen 30 de 41 (0,732) y 23 de 41 en lo que Mochi registra. | Alinear las cifras al reporte | S |
| media | diseno-ia.md:4 | «Última actualización: 11-10-2026», aunque §5 y §6 ya traen texto del 16-10. | Cambiar la fecha | S |
| media | diseno-ia.md §0, §4 | El documento central de diseño no tiene una sección del motor ni de la Home dinámica: solo aparecen en las filas de palancas (235, 238) y en una nota (277). §0 sigue con «concepto → complemento → búsqueda» como único camino cruzado. | Sección corta «4b. Motor y Home dinámica» (qué decide, entradas, guardias), enlazada a capa-de-datos §Motor | M |
| media | diseno-ia.md:210 | La lista de orígenes de «Ofertas del agente por momento» no trae `agent-recompra`. | Agregarlo | S |
| media | diseno-ia.md:283-313 | En §7 Etapas faltan las 5 etapas del 16-10 (sin pasaporte, motor, Home, conectadas, QA). | Tabla «Etapas del motor (16-10-2026)» con sus planes | S |
| baja | diseno-ia.md:220 | La vista 3 («Entre verticales») del panel no trae combinaciones ni motor. | Agregar | S |

### docs/capa-de-datos.md

Bien al día con el motor.

| Sev. | Lugar | Qué | Arreglo | Esf. |
|---|---|---|---|---|
| media | capa-de-datos.md:18 | «133 conceptos: 113 tipos de producto en 20 grupos». Hoy son 116 + 20. | Recontar | S |
| baja | capa-de-datos.md:15 | «144 segmentos» es correcto (`segments.toml`). La fila 113 de decisiones dice 146, pero es una fila fechada. | — | — |

### docs/demo.md

El guion coincide con la app: se revisaron los textos «Toca y te armo algo», «¿Repetimos?», «Ordenadas según lo que más usas», «Repetir escena» y «¿Qué se te antoja hoy?» (la barra rota tres frases, `SmartBar.jsx:6`).

| Sev. | Lugar | Qué | Arreglo | Esf. |
|---|---|---|---|---|
| media | demo.md:86 | «Qué va con qué: los complementos son una lista escrita a mano. Con datos de pedidos de Rappi se reemplazan…»: ya hay un motor que aprende reglas de compra cruzada de la población (hoy simulada, λ = 0). | Reescribir: curados + reglas del motor sobre la población simulada; con datos reales se cambia `MOTOR_POBLACION` | S |
| baja | demo.md:58 | El paso 4 del panel nombra «Combinaciones de verticales», «Motor» y «Recompra» y no menciona «Accesos de la Home» (Uso del MVP), que es justo lo que deja el paso de la Home dinámica. | Una línea | S |
| baja | demo.md:3 | El guion dura unos 10 minutos y las tres secciones opcionales nuevas suman 5 más; la Home dinámica, que es lo que pidió Rappi, quedó como «opcional». | Pasar la Home dinámica y la escalera al recorrido principal | S |

### docs/instalacion.md

Al día: las 7 revisiones de mvp-check, los puertos y la advertencia de `npm run screenshots` sobre la base real. No hay hallazgos.

### docs/despliegue.md

| Sev. | Lugar | Qué | Arreglo | Esf. |
|---|---|---|---|---|
| media | despliegue.md §2 (≈50-133) | Falta `MOTOR_POBLACION` (api y jobs), que está en `rappi-ia/.env.example:83`. Comprobado con un cruce de todas las `os.environ.get` de los dos paquetes contra el documento: es la única variable que falta. | Fila en la tabla de API | S |
| baja | despliegue.md §6 / timers | No dice cómo se recalcula el motor en el servidor: `jobs` solo purga y respalda, y `rappi-refresh.timer` está apagado. Las tablas de población vienen del dump y las personales las recalcula la API tras `POST /orders`. | Una línea en «Actualizar» | S |
| baja | despliegue.md:423-434 | «Qué se guarda»: faltan `user_vertical_affinity` y `replenishment` (son por persona y se borran con ella). | Agregar | S |

### docs/contexto-y-problema.md

| Sev. | Lugar | Qué | Arreglo | Esf. |
|---|---|---|---|---|
| media | contexto-y-problema.md:75-84 | «Estado al 11-10-2026»: falta la fase del motor y la Home dinámica, y no aparece el insumo nuevo más importante, la tabla de combinaciones de Rappi, que convierte la hipótesis del silo en una correlación con datos de Rappi. | Fila «Motor multivertical (16-10)» y una línea en §1 o §5: «Rappi compartió…» | S |

### rappi-ia/README.md

| Sev. | Lugar | Qué | Arreglo | Esf. |
|---|---|---|---|---|
| alta | rappi-ia/README.md:93 | `/analytics/{… game …}`: esa ruta ya no existe (`api/app.py:633-652`) y faltan `combos`, `motor` y `home`. | Corregir la lista | S |
| media | rappi-ia/README.md:85 | En los momentos de `/agent/offer` falta `recompra`. `vertical_por_probar` se describe como «donde aún no pide, según sus pedidos», pero hoy sigue la escalera de combinaciones. | Corregir | S |
| media | rappi-ia/README.md:80-94 | Falta el endpoint `GET /profile/{id}/verticales` (Home dinámica). | Fila nueva | S |
| media | rappi-ia/README.md:11-19 | A la tabla «Pieza / Qué hace / Dónde» le falta la fila del motor (`motor/`) y la de ofertas (`offers/`). | 2 filas | S |
| media | rappi-ia/README.md:202-218 | En la tabla de migraciones falta `036_motor.sql`. | Fila nueva | S |
| media | rappi-ia/README.md:5 | «133 conceptos, con 103 complementos curados»: hoy son 136 y 106. | Recontar o quitar el número | S |
| baja | rappi-ia/README.md:187 | `motor/`: «modelo, tablas por fuente y predicción del próximo vertical». Falta «recomendaciones (cross_picks), Home (home.py) y evaluación». | Ampliar | S |
| baja | `make help` (rappi-ia/Makefile:124) | «Capa de perfiles … (crece con las etapas del plan)»: es la frase del plan de la capa del 06-10. | «Capa de datos: …, segmentos y motor» | S |
| baja | `make help` (synth) | «Usuarios y eventos SIMULADOS para el panel»: hoy también alimentan al motor. | «para el panel y el motor» | S |

### rappi-scraper/README.md

Sin hallazgos relevantes. `make help` coincide con la tabla de objetivos.

### prototipo-app/README.md

| Sev. | Lugar | Qué | Arreglo | Esf. |
|---|---|---|---|---|
| alta | prototipo-app/README.md:9, 72, 122 | Las capturas 00, 01 y 26 muestran el pasaporte, «Jugar» y «Juega mientras llega tu pedido». | §3 | — |
| media | prototipo-app/README.md:66-107 | No hay sección de la Home dinámica (accesos ordenados con «Ordenadas según lo que más usas»), del bloque «¿Repetimos?» ni de la escalera de combinaciones al tocar a Mochi. | Subsección «La Home que aprende» con captura | S |
| media | prototipo-app/README.md:11 | «Las capturas … se tomaron o se revisaron el 10-10-2026». | Nueva fecha al volver a tomarlas | S |
| baja | prototipo-app/README.md:196 | «el recorrido de `make mvp-check` (Home, compra, kit de Mochi, Home dinámica, panel y API caída)»: falta «combinación» (son 7). | Agregar | S |

### dashboard-empresa/README.md y la página de presentación

| Sev. | Lugar | Qué | Arreglo | Esf. |
|---|---|---|---|---|
| **alta** | dashboard-empresa/presentacion.html:250-253 | «**En dos minutos, sin base de datos.** El prototipo y el panel corren en el navegador con datos guardados. Solo hace falta Node.» **Es falso desde el 10-10**: la app no abre sin la API. Es la página que se abre antes del panel para presentar la propuesta. | Reescribir «Verlo funcionando» con `make mvp` | S |
| **alta** | presentacion.html:55-62 y `public/presentacion/prototipo-final.jpg` | La portada muestra el pasaporte, «Jugar» y «junta sellos». | Volver a capturar (§3) | — |
| alta | presentacion.html:232-234 | «Tests automáticos 1.900 — Scraper 144, capa de IA 1.077, prototipo 589 y panel 90». Está muy desactualizado. | Cifras nuevas o quitar el bloque | S |
| alta | presentacion.html (todo) | «Resultados al 6 de octubre». No hay nada del motor, la escalera, la Home dinámica ni la tabla de Rappi; la tesis sigue siendo «lo que compras en el súper debería mejorar lo que ves en farmacia». | Sección «El motor» (escalera, compra cruzada, recompra, Home), con las cifras simuladas rotuladas y la tabla de Rappi como «dato compartido por Rappi» | M |
| media | presentacion.html:102 | «133 conceptos (113 y 20 grupos)». | 136 (116 + 20) | S |
| media | public/presentacion/flujo-de-datos.png | Es una copia de `docs/diagramas/rag-datos.png` del 10-10 y trae las tarjetas del juego. | Volver a copiarla después de regenerar (§2) | S |
| media | dashboard-empresa/README.md:114-118 | En «Entre verticales» faltan «Combinaciones de verticales» (`views/cross/ComboTables.jsx`) y «Motor» (`MotorEvaluation.jsx`). La línea 117, «las aristas aprendidas de datos simulados no las usa el agente», necesita el matiz del motor. | Dos viñetas y el matiz | S |
| media | dashboard-empresa/README.md:140-143 | «Uso del MVP … en dos secciones»: son tres (falta «Accesos de la Home»). A la lista de momentos le faltan «recompra» y «perfil de gusto». | Corregir | S |
| media | dashboard-empresa/README.md:120 y `docs/screenshots/4-verticales-escritorio-claro.jpg` (09-10) | La captura de «Entre verticales» no tiene combinaciones ni motor. | `npm run screenshots` en el panel; no necesita la API: usa fixtures | S |
| baja | dashboard-empresa/README.md:3 | Lo mismo que CLAUDE.md:5 (las secciones de Uso del MVP). | — | S |

---

## 2. Diagramas (`docs/diagramas-fuente/*.json` → `docs/diagramas/*.html` + `.png`)

Se regeneran con la skill **Archify** (CLAUDE.md:35).

| Sev. | Diagrama | Estado | Arreglo | Esf. |
|---|---|---|---|---|
| alta | `rag-datos` | La fuente se limpió el 16-10, pero el HTML y el PNG son del 11-10: el PNG trae «conceptos, **tarjetas**, embeddings» y «**/game** y /analytics en la API». Sale en README:52, diseno-ia:25, rappi-ia/README:7 y la presentación. La fuente no tiene el motor: no hay nodo `motor` en «IA offline» (afinidad, transiciones, combos, compra cruzada, tendencias, recompra), ni `combos.toml` («dato compartido por Rappi») como entrada, ni la Home en Apps. | Agregar a la fuente el nodo «Motor (capa)» entre conceptos/eventos y API, y el flujo `combos.toml` → motor → `/agent/offer` + `/profile/{id}/verticales`; regenerar el HTML y el PNG; copiar el PNG a `dashboard-empresa/public/presentacion/flujo-de-datos.png` | M |
| alta | `arquitectura-ia` | El HTML (11-10) trae el nodo `tarjetas`, la arista «knowledge» y el prototipo como «buscador · **juego**». La fuente ya los quitó, pero tampoco tiene el motor: el carril «Entre verticales» solo trae `conceptos`. | Sumar al carril «Entre verticales» un nodo «Motor multivertical» (escalera, compra cruzada, recompra) y «Home dinámica» al prototipo; regenerar | M |
| media | `despliegue` | El HTML (11-10) dice «migrate: respalda, migra, **carga tarjetas** y da permisos». La fuente ya está corregida. | Solo regenerar el HTML y el PNG | S |
| ok | `scraper-flujo` | Fuente y salidas del 28-09, sin cambios de alcance. | — | — |
| opcional | nuevo `motor-flujo` | Un diagrama propio del motor (pedidos y señales → afinidad, transiciones, combo_stats + tabla de Rappi → target_step → oferta con basis; trends y cross_sell_rules → cross_picks λ; replenishment → «¿Repetimos?»; afinidad → orden de la Home) sería la pieza visual de la «innovación central». | Fuente JSON nueva más Archify; ligarlo en README, docs/README y capa-de-datos | M |

Antes de generar, comprobar que no queden los archivos `docs/diagramas/*.visual-check.*` (están ignorados).

---

## 3. Capturas (`prototipo-app/docs/screenshots`)

**Cómo se generan:** `npm run screenshots` corre `prototipo-app/scripts/screenshots.mjs`.
- Exige el MVP corriendo con la API en `http://localhost:8000/health`, o sea `make mvp` sobre la **base real `rappi`**. Usa el Chrome instalado y un Vite propio en el 5199.
- Borra `localStorage`, así que cada corrida es una persona nueva y ve la Home en el orden fijo.
- **Paga una compra**: deja un pedido `prototype` y sus eventos en `rappi` (lo advierte README:11 de la app y instalacion.md:128).
- No captura nada de la Home dinámica, la recompra ni la escalera.

| Sev. | Captura | Problema |
|---|---|---|
| alta | `00-modo-demo.jpg`, `01-home-final.jpg` (09-10) | Pasaporte («Tu pasaporte Rappi», «2 sellos», «Jugar») y globo «junta sellos en tu pasaporte». Son la portada del README raíz y de la app. |
| alta | `26-seguimiento.jpg` (10-10) | Tarjeta «🎮 Juega mientras llega tu pedido · gana el sello de Express». |
| alta | `dashboard-empresa/public/presentacion/prototipo-final.jpg` | La misma Home con pasaporte (portada de `presentacion.html`). |
| media | falta | No hay captura de la Home dinámica (accesos reordenados con «Ordenadas según lo que más usas»), ni del bloque «¿Repetimos …? Pides cada N días.», ni de la oferta de Mochi en la Home con la escalera («¿Por qué?»). |
| baja | `30-ficha-mochi.jpg` | El arte dice «La esencia de Bigotes». Es arte histórico; aceptable o reemplazar. |
| baja | `27-entregado.jpg` | Sin juego («¿Y ahora quesos?»). Bien. |

**Cómo producir las nuevas sin ensuciar la base real:**
- Las capturas de la Home dinámica y de «¿Repetimos?» necesitan historia: tres compras con ritmo para la recompra, toques o pedidos para el orden. Generarla con la app escribiría eventos y pedidos en `rappi`.
- **Opción limpia:** en `screenshots.mjs`, con `page.route`, servir para esas capturas `/profile/{id}/verticales` y `/agent/offer` (`recompra`, `vertical_por_probar`) desde los fixtures del contrato (`src/api/fixtures/profile-verticales.json`, `agent-offer-recompra.json`, `agent-offer-vertical-por-probar-combinacion.json`). El resto se captura contra el catálogo real.
- La compra de 25-27 sigue escribiendo en `rappi`, como hoy. Si se quiere evitar, correr contra una copia `rappi_staging` (`DATABASE_URL=postgresql:///rappi_staging make mvp`).

Esfuerzo: M (script) + S (correrlo y revisar).

---

## 4. Higiene del código

### Formato

| Sev. | Lugar | Qué | Arreglo | Esf. |
|---|---|---|---|---|
| media | prototipo-app | `npx prettier --check src` (prettier 3.9.9, `.prettierrc` del paquete): **87 archivos** con diferencias, más `scripts/screenshots.mjs`. Son diferencias reales: imports partidos, `useSyncExternalStore(...)` y `transition:` en CSS. El CI no lo revisa: `npm run lint` es solo ESLint. Ya estaba anotado en el ledger de la etapa 3. | Un commit aparte de solo formato (`npm run format` + `prettier --write scripts`); después sumar `prettier --check src scripts` al job del CI | S (+ revisar el diff) |
| media | dashboard-empresa | No tiene `prettier` en `package.json`, ni `.prettierrc`, ni script `format`. Con la config de la app quedan 45 archivos distintos (con la de prettier por defecto, 99). | Copiar la `.prettierrc` de la app, sumar la dependencia y el script `format`, un commit de formato y el `--check` en el CI | S |
| ok | rappi-ia, rappi-scraper | `ruff check` y `ruff format --check` limpios; el CI ya los corre. | — | — |

### Aviso de pytest `StarletteDeprecationWarning` (httpx)

Viene de `starlette/testclient.py:34-51` (starlette 1.7.0): `TestClient` intenta `import httpx2` y, si no está, cae a `httpx` y avisa «Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.».
- `rappi-ia/requirements.lock.txt:23` **ya fija `httpx2==2.13.1`**, pero no se instala: el lock es solo de restricciones (`pip install -c`) y nadie pide `httpx2`.
- `rappi-ia/pyproject.toml:23` pide `dev = [… "httpx>=0.27"]`.
- En el `.venv`: `ModuleNotFoundError: httpx2`.

**Arreglo limpio** (severidad baja, esfuerzo S):
1. En `rappi-ia/pyproject.toml`, `dev`, cambiar `"httpx>=0.27"` por `"httpx2>=2.13"`. `httpx` igual llega como dependencia de `anthropic` (extra `llm`); el código propio solo lo nombra para silenciar sus logs (`api/logs.py:41`, `cli.py:799`).
2. `make install` y el CI lo instalan con el lock.

No hace falta `filterwarnings`. Estaba en los pendientes de la etapa 2.

### Imports privados entre módulos

| Sev. | Lugar | Qué | Arreglo | Esf. |
|---|---|---|---|---|
| media | rappi-ia/src/rappi_ia/offers/engine.py:48 | `from ..catalog.stores import BIGINT_MAX, _product, product_detail`: importa una privada desde otro paquete (`_product`, agregada el 16-10 en bb38d65b). | Renombrar `_product` → `product_card` (público) en `catalog/stores.py` y actualizar `catalog/deals.py:29`, `catalog/restaurants.py:17` y `offers/engine.py` | S |
| media | offers/engine.py:55 | `from ..retrieval.hybrid import _concepts_of`. | Publicarla (`concepts_of`) | S |
| baja | analytics/queries.py:12 | `from ..agent.verticals import _SHARES`. | Exponer una función o constante pública | S |
| baja | motor/evaluate.py:17-21 (`_concepts`, `_local_day` de `.model`), motor/recommend.py:21 (`_source_of` de `.predict`) | Privadas usadas dentro del mismo paquete `motor`. | Hacerlas públicas en `model.py` y `predict.py` | S |
| baja | catalog/home.py:10, deals.py:29 (`_CURRENT_OFFERS`, `_OWN_VERTICAL`, `_card`) | Mismo paquete `catalog`. Aceptable, pero sería coherente publicarlas. | Opcional | S |
| baja | layers/segments.py:30 (`_phrase_key`), layers/canonical.py:12 (`_NAME_MEASURE`) | Mismo paquete. | Opcional | S |

### Código muerto (solo lo de alta confianza)

| Sev. | Lugar | Qué | Arreglo | Esf. |
|---|---|---|---|---|
| media | prototipo-app/src/components/NotReplicated.jsx + not-replicated.css | Ningún archivo los importa (es lo único que referencia `not-replicated`). | Borrar los dos | S |
| baja | prototipo-app: `poseFor` (TrackingMap.jsx), `ConnectionNotice` (ConnectionGate.jsx:50), `AGENT_HIDDEN_SCREENS` (AgentPresence.jsx), `FINAL_TAIL` (data/home.js) | Se exportan pero solo se usan en su propio archivo. | Quitar el `export` | S |
| baja | dashboard-empresa: `readUrlState` (lib/useUrlState.js), `TIMEOUT_MS` (lib/api.js), `STRATA` (views/cross/strata.js) | Lo mismo. | Quitar el `export` | S |
| baja | CSS sin uso: `live-card-emoji`, `live-card-head` (prototipo `screens/home/live/live.css`); `grid-2` (panel `styles/global.css`), `chip-list` (panel `components/components.css`) | Ninguna clase se referencia en JS/JSX/HTML. Revisión heurística que descarta los nombres armados con `${…}`. | Borrar las reglas | S |
| baja | rappi-ia/src/rappi_ia/motor/evaluate.py:187-238, 358-368 | `evaluate_next_vertical`, `tune`, `evaluate_cross_sell`, `tune_lambda` y `evaluate_replenishment` son envoltorios públicos que solo usan los tests: producción va por `evaluate()` con `_tune`, `_cross_sell`, etc. | Dejarlo (es API de prueba legítima) o que los tests usen `evaluate()`. Decidir. | S |
| baja | scripts/mvp-check.sh:10, 65, 87 | Acepta el origen viejo `mochi-plan`, que una base recién sembrada (`rappi_ia_test`) nunca tiene. | Dejar solo `agent-plan` | S |
| info | diseno-ia.md:279 | La tabla `image_embeddings` no se usa; ya está documentado como decisión. | — | — |

No hay ningún `TODO`, `FIXME`, `XXX` ni `HACK` en el código.

### Restos de lo que se quitó (juego, pasaporte, Bigotes)

En el código de producción no quedan restos del juego. Solo siguen, a propósito:
- `legacyStorage.js`, que borra claves viejas del navegador;
- los tests que comprueban que el juego no está;
- las migraciones 028, 029 y 035.

«Bigotes» quedó en:

| Sev. | Lugar | Qué | Arreglo | Esf. |
|---|---|---|---|---|
| baja | rappi-scraper/src/rappi_scraper/storage/search.py:109 | Comentario SQL: «Bigotes no los muestra cuando se habla de síntomas». | «el agente» o «Mochi» | S |
| baja | tests (docstrings y nombres): rappi-ia/tests/integration/test_analytics.py:117-119, 517-519; test_api.py:544; test_rappi_agent.py:274, 514; tests/unit/test_search_eval.py:200-226; test_rappi_agent_words.py:1; rappi-scraper/tests/integration/test_repository.py:142, 492 | Nombres y docstrings con «Bigotes». | Renombrar a «agent»/«Mochi» (`test_*_bigotes_*` → `test_*_agent_*`). **No tocar** las pruebas de vocativo «hola bigotes» (test_agent_parts.py:195-211, test_user_phrases.py:95, test_rappi_agent_words.py:58, 118; text.py:15), que prueban a propósito el nombre antiguo. | S |
| baja | rappi-ia/tests/unit/test_spare_connection.py:105 | El docstring dice «el juego o una búsqueda nueva no esperan…». | Sacar «el juego» | S |
| baja | docs/resultados/busqueda-2026-10-06.md:76 | «Lo que registra Bigotes»: es un reporte fechado y queda como histórico. | — | — |

---

## 5. Estructura del repositorio

| Sev. | Lugar | Qué | Arreglo | Esf. |
|---|---|---|---|---|
| baja | `docs/simulacion-catalogo.html` (sin seguimiento, solo en el checkout principal `~/Rappi`, del 11-10) | Archivo suelto de 58 KB. | Preguntar al usuario: versionarlo (¿en `docs/mapas/`?) o moverlo a la Papelera | S |
| baja | `docs/superpowers/plans` y `specs` | Siguen en el repo los planes y specs del juego (`2026-10-09-juego-*`, `mvp-etapa-4-juego`) aunque el README dice que la historia del juego está en `rappi-evolucion-proyecto`. Se enlazan como «Historia» y no hay enlaces rotos. | Decidir: dejarlos rotulados como historia (hoy) o moverlos al repo de evolución. Recomendación: dejarlos. | S |
| baja | rappi-scraper/.gitignore | `data/supermercados_csv/` y `data/exports/` sobran, porque la raíz ya ignora `rappi-scraper/data/` entero. | Quitar o dejar; es inofensivo | S |
| ok | .gitignore raíz | Cubre `.env*`, dumps, `.superpowers/`, `Proyecto/`, `.claude/` local y las evidencias de archify. Las apps ignoran `node_modules/` y `dist*/`. No hay archivos sueltos en el worktree. | — | — |
| baja | ramas locales en `~/Rappi` | 40 o más ramas locales con upstream `[gone]` y 64 ya fusionadas en main. | Con el permiso del usuario, `git fetch --prune` y borrar las ramas `[gone]` | S |
| baja | worktrees | `wt-noche` (`feat/backend-perfiles-y-calidad`, `[gone]`) y `wt-sushi` (`demo/prototipo-sushi`, la rama local de la demo del sushi) de otra sesión siguen registrados. | Preguntar; wt-sushi es la demo local a propósito (memoria) | S |
| ok | Makefiles | `make help` de la raíz (help, mvp, mvp-check, build), de rappi-ia (25 objetivos) y de rappi-scraper (16) coinciden con los README. Solo `check-migrations` y `verify-migrations` de rappi-ia no tienen `##`: son internos y está bien. Textos viejos en §1 (rappi-ia). | — | — |
| ok | CI (`.github/workflows/ci.yml`) | Jobs: rappi-scraper, rappi-ia (ruff + pytest, que incluye el contrato), prototipo-app y dashboard-empresa (lint, test y build), build-produccion (+ check-dist), scripts (shellcheck), docker (compose + smoke) y mvp-check. Coincide con README:190. `modelos-semanal.yml` coincide con rappi-ia/README:33. **Falta** el `prettier --check` (§4). | — | — |
| ok | `scripts/` | `mvp.sh`, `mvp-lib.sh`, `mvp-check.sh` y `check-dist.sh`, documentados y con shellcheck en el CI. | — | — |

---

## 6. Pendientes de los ledgers (`.superpowers/sdd/*/progress.md`)

Se comprobó cada pendiente diferido contra el código actual.

**Cerrados (no hacer nada):**
- Etapa 1: comentarios del juego en `config.py`, `cache.py` y `cli.py`; CORS sin PUT (`app.py:143`); TO_TRY_TEXT «aún no pides» (`engine.py:123`); props sin uso de `ConnectionNotice`.
- Etapa 2: carrera build vs «Olvidar» (49288d30, `FOR KEY SHARE SKIP LOCKED`); `_suggestion` con la guardia de bebé (`synth.py:64`); `post-refresh` que purga aunque falle (`Makefile:148`); layer-report por fuente.
- Etapa 4: docstring de `suggest_complement` con el respaldo curado (`tools.py:229`); textos con plurales (etapa 5, T1).
- Etapa 5: `qa_motor.py` en solo lectura; «sepa que buscas eso»; `Catalog.pick` con guardia; README:107.

**Siguen abiertos después de la etapa 5:**

| # | Origen | Pendiente | Sev. | Dónde |
|---|---|---|---|---|
| 1 | Etapa 2, final | Aviso Starlette/httpx en pytest | baja | §4: `pyproject.toml:23` → `httpx2` |
| 2 | Etapa 3, T2 | `prettier --check` falla (anotado como «previo») | media | §4 |
| 3 | Etapa 3, T2 | La leyenda «Ordenadas según lo que más usas» desplaza la fila unos 25 px al aparecer (`HomeSections.jsx:75`, renderizado condicional) y la Home parpadea al «Olvidar» | baja | Reservar la altura de `.home-shortcuts-caption` (`home.css:190`) |
| 4 | Etapa 5, final | `docs/resultados/motor-2026-10-16.md:204`: «no pasaron la regla» debería decir «no pasaron la regla **o la validación**» | baja | 1 línea |
| 5 | Etapa 5, T2 | Decisión pendiente: productos sin alcohol de tiendas rotuladas «Licores» dentro de Express o el súper (`qa-motor-2026-10-16.md:82`). El ruling dice «documentar en decisiones» y no se hizo. | baja | decisiones.md, «Agente (Mochi)» |
| 6 | Etapa 4, final | Ruling «Lo más pedido» como rótulo aunque la población sea simulada: «anotado para la decisión del usuario» | media (honestidad) | Preguntar al usuario; ¿rótulo «(simulado)» en la demo? |
| 7 | Etapa 5, T2 | Contenido: carritos sin complemento (gaseosas, lácteos, energéticas, postres, despensa asiática, mascotas); poca variedad (95 de 129 carritos ofrecen las mismas 3 gaseosas); conceptos mal asignados («Buldak» como salsas, «Just Mila Xl» como pastelería) | media (calidad visible en la demo) | `complements.toml`, `category_map.csv`, reglas; decisión del usuario |
| 8 | Etapa 2, T4 | `load_orders` se lee dos veces en `_build` (`build.py:97` para la población, `:201` por lotes de personas) | baja | Opcional (rendimiento; la corrida tarda segundos) |
| 9 | Etapa 2, T2 | `test_synth_combos` depende del catálogo de prueba y de una fecha fija | baja | Opcional |
| 10 | Etapa 3, T1 | Parámetro `client` sin uso en un test de `test_home_verticals.py` | baja | Opcional |
| 11 | Etapa 4, T1 | La evaluación excluye todo lo pedido antes del corte y el servicio solo los últimos 30 días (diferencia de definición) | baja | Documentarlo en el informe del motor o alinearlo |
| 12 | Etapa 4, T4 | Filas de interés sin `kind`/`basis` en la oferta; el respaldo curado se prueba en la posición de la regla | baja | Opcional |
| 13 | Etapa 1 | `EVOLUCION.md` de rappi-evolucion-proyecto esperaba el número del PR #89 | baja | Otro repo; comprobar |

---

## Plan de pulido propuesto (5 tareas)

Orden sugerido: 1 → 2 → 3 → 4 → 5. La 2 y la 3 se pueden hacer en paralelo.

**Tarea 1. Higiene de código (sin cambiar comportamiento)**
- Formato: commit aparte con prettier en `prototipo-app` y `dashboard-empresa` (al panel se le agregan `.prettierrc`, la dependencia y el script `format`); sumar `prettier --check` a los dos jobs de `.github/workflows/ci.yml`.
- `rappi-ia/pyproject.toml`: `httpx` → `httpx2` en `dev`.
- Imports privados: `catalog/stores.py` (`_product` → público) y quien lo usa (`catalog/deals.py`, `catalog/restaurants.py`, `offers/engine.py`); `retrieval/hybrid.py` (`_concepts_of`); `agent/verticals.py` (`_SHARES`); `motor/model.py`, `motor/predict.py`.
- Borrar `prototipo-app/src/components/NotReplicated.jsx` y `not-replicated.css`; quitar los `export` que sobran y las 4 reglas CSS sin uso; `scripts/mvp-check.sh` sin `mochi-plan`.
- «Bigotes» → «Mochi»/«agent» en `rappi-scraper/storage/search.py:109` y en los nombres y docstrings de tests (sin tocar las pruebas de vocativo); `test_spare_connection.py:105`.
- Reservar la altura de la leyenda de la Home (`home.css`).
- Verificación: `make lint test` (rappi-ia, rappi-scraper), `npm run lint && npm test && npx prettier --check src scripts` (las dos apps), `make mvp-check`, y pytest sin el aviso de Starlette.

**Tarea 2. Diagramas (Archify)**
- Archivos: `docs/diagramas-fuente/rag-datos.json`, `arquitectura-ia.json`, opcional el nuevo `motor-flujo.json`; regenerar `docs/diagramas/{rag-datos,arquitectura-ia,despliegue}.html/.png` (y `motor-flujo.*`).
- Copiar `rag-datos.png` a `dashboard-empresa/public/presentacion/flujo-de-datos.png`.
- Verificación: validación de Archify; que el HTML y el PNG no tengan «tarjetas», «juego» ni «/game»; que el motor y la Home aparezcan.

**Tarea 3. Capturas**
- `prototipo-app/scripts/screenshots.mjs`: capturas nuevas, «Home dinámica» (accesos con la leyenda), «¿Repetimos?» y «Mochi propone la siguiente vertical» con `page.route` sobre los fixtures del contrato (sin escribir en la base para esas capturas). Volver a tomar `00`, `01`, `26` y el resto.
- Pasar la nueva portada a `dashboard-empresa/public/presentacion/prototipo-final.jpg`.
- `dashboard-empresa`: `npm run screenshots` (sobre todo `4-verticales`, con combinaciones y motor).
- Ojo: la compra de 25-27 escribe en la base que use el MVP. Pedirle permiso al usuario o usar `rappi_staging`.
- Verificación: revisar cada imagen a ojo; `grep` de los `alt` en los README.

**Tarea 4. Narrativa principal (README raíz, presentación, índice)**
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

**Tarea 5. Documentos de referencia y CLAUDE.md**
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

**Decisiones para el usuario (antes o durante la tarea 4):**
1. Qué hacer con `docs/simulacion-catalogo.html` (sin seguimiento).
2. ¿Rotular «Lo más pedido» como simulado en la demo? (ledger de la etapa 4, #6).
3. ¿Se permiten las tiendas «Licores» dentro de Express o el súper? (#5).
4. Contenido: ¿curar aristas nuevas (gaseosas, lácteos, postres…) y corregir Buldak y Just Mila en esta etapa o después? (#7).
5. ¿Limpiar las ramas `[gone]` y los worktrees viejos de `~/Rappi`?
6. Para la tarea 3: ¿se permite que `npm run screenshots` deje un pedido `prototype` en `rappi`, o se usa `rappi_staging`?

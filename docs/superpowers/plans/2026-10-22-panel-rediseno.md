# Rediseño del panel de negocio: 3 vistas alrededor de 4 preguntas

Fecha: 22-10-2026. Rama `claude/panel-rediseno-761601`. Solo `dashboard-empresa/` (más `mvp-check` y la documentación);
la API no cambia.

Pedido del usuario: «Diseñe todo de nuevo para que Rappi pueda utilizar bien las cosas del dashboard. Sólo cosas
relevantes sin tener tantas pestañas».

## 1. Auditoría (antes)

Recorrido el 22-10 con la API de este worktree sobre `rappi_panel` (copia de `rappi_staging` sin los datos de búsqueda),
a 1280 px, con las dos fuentes. Hoy son **6 pestañas, 21 bloques** y unos 33.000 px de alto con datos simulados (solo
«Entre verticales» mide 7.000 px).

| Pestaña | Bloque | ¿Qué decisión de Rappi ayuda a tomar? | Datos | ¿Se repite? |
|---|---|---|---|---|
| Resumen | Qué hacer esta semana (3 acciones) | Prioridades: demanda sin oferta, concepto que sube, rescate | Simulado / prototipo | Sí: las 3 se repiten en Oportunidades y Frecuencia |
| Resumen | 8 indicadores al corte | Ninguna por sí sola: sin comparación ni tendencia, solo definiciones | Simulado / prototipo | En riesgo y perdidos, 3 veces en el panel |
| Resumen | Evolución semanal (4 series) | Contexto de tendencia (activos, pedidos, abandono, sin resultado) | Simulado / prototipo | Sin resultado, también en Oportunidades |
| Oportunidades | Demanda no satisfecha (tabla) | Sumar comercios o categoría | Simulado / prototipo | Con «Búsquedas sin resultado» (Uso del MVP) y «Surtido vs demanda» (Catálogo) |
| Oportunidades | Conceptos que suben y bajan | Campañas de lo que sube (RappiAds) | Simulado / prototipo | Con la acción 2 del Resumen |
| Frecuencia | Embudo por vertical (8 embudos) | Producto/operación (dónde se cae el pago), no gerencia ni RappiAds | Simulado / prototipo | No |
| Frecuencia | Retención por cohorte (mapa de calor) | Ninguna: describe, no dice qué hacer | Simulado / prototipo | La retención ya la cuenta la tabla de Rappi |
| Frecuencia | Días entre pedidos (histograma) | Ninguna: explica la regla de riesgo | Simulado / prototipo | No |
| Frecuencia | A quién rescatar (100 ids) | A quién reactivar y con qué | Simulado / prototipo | Con «A quién invitar a volver» (Uso del MVP) |
| Entre verticales | Sugerencias del agente | Qué ofrecer entre verticales (RappiAds) | Simulado / prototipo | Con «Ofertas por momento» (Uso del MVP) |
| Entre verticales | Servicios sin catálogo | Si Mochi lleva a Travel y Favor | Simulado / prototipo | Parte de lo que hace Mochi |
| Entre verticales | Afinidad A → B (25 aristas) | Ninguna hoy: el agente no las usa y son simuladas | Simulado | No |
| Entre verticales | ¿Retiene más quien usa dos verticales? | Respalda la estrategia, pero en simulados sale por construcción | Simulado | La tabla de Rappi dice lo mismo con datos reales |
| Entre verticales | Combinaciones (tabla de Rappi + propia + finas) | **Dónde está la venta cruzada** (la tabla de Rappi es el único dato real de personas) | Rappi + simulado / prototipo | La propia y la fina repiten el supuesto del simulador |
| Entre verticales | Evaluación del motor (4 tablas) | Si el motor funciona (equipo de datos); a la gerencia le basta motor vs línea base | Simulado | No |
| Catálogo | Cobertura, calidad, productos en varias verticales | Salud del scraper, no una decisión de Rappi (Rappi conoce su catálogo) | Real | No |
| Catálogo | Surtido vs demanda | Dónde falta surtido | Real + simulado | Con demanda no satisfecha |
| Uso del MVP | Ofertas del agente por momento | En qué momento ofrecer (RappiAds) | Prototipo | Con sugerencias del agente |
| Uso del MVP | A quién invitar a volver | Rescate dentro de la app | Prototipo / simulado | Con a quién rescatar |
| Uso del MVP | Búsquedas sin resultado | Demanda que el catálogo no cubre | Prototipo | Con demanda no satisfecha |
| Uso del MVP | Accesos de la Home | Ninguna directa: cómo la Home aprende el orden | Prototipo | No |

Problemas transversales: la misma pregunta repartida en 2 o 3 pestañas; números sin comparación; el lector tiene que
saber que «Uso del MVP» es la única vista útil con la fuente del prototipo; la tabla de Rappi, el dato más fuerte,
queda en la quinta sección de la cuarta pestaña.

## 2. Para quién y para qué

- **Gerencia general:** crecimiento, retención y venta cruzada entre verticales.
- **RappiAds:** a quién ofrecer qué, en qué momento y con qué resultado.

El panel se ordena en 4 preguntas. Lo que no responde a una de ellas sale.

1. **¿Dónde está la oportunidad de venta cruzada?** Tabla de Rappi (dato compartido, correlación): cuántos usuarios
   están en cada combinación y cuánto más retiene la combinación con un grupo más.
2. **¿A quién estamos perdiendo y qué le ofrecemos?** En riesgo y perdidos según su ritmo; a cuántos les toca
   «¿Volvemos a…?» o «¿Repetimos?»; qué pedían y si aceptan avisos.
3. **¿Qué está haciendo Mochi y funciona?** Ofertas por momento, sugerencias entre verticales (aceptación y pedido),
   servicios sin catálogo y el motor contra su línea base.
4. **¿Qué busca la gente y no encuentra?** Búsquedas sin resultado con su tendencia, la demanda agrupada con acción,
   lo que sube y dónde hay poco surtido.

## 3. Estructura: 3 vistas

| Vista (`?vista=`) | Para | Contenido |
|---|---|---|
| **Resumen** (`resumen`, principal) | Gerencia y RappiAds | «Cómo va»: 5 indicadores con su comparación (tendencia de 4 semanas o el dato que los explica). «Qué decidir»: las 4 preguntas, cada una con su cifra, su contexto, una acción sugerida y el enlace al detalle |
| **Retención y venta cruzada** (`clientes`) | Gerencia | Preguntas 1 y 2: la escalera de la tabla de Rappi (gráfico de pesas: retención de hoy → con un grupo más) y a quién estamos perdiendo (cifras, qué pedían, la lista seudónima a pedido) |
| **Mochi y búsquedas** (`mochi`) | RappiAds | Preguntas 3 y 4: ofertas por momento (la tabla que revisa `mvp-check`), sugerencias que funcionan, servicios, motor vs línea base; búsquedas sin resultado, demanda agrupada, lo que sube y poco surtido |

Se mantienen: la fuente (Simulados / Prototipo) en la URL y arriba, el aviso de procedencia fijo, una insignia de
fuente en cada sección, el rótulo «uso del MVP, pocas personas: no es evidencia» en cada sección con la fuente del
prototipo, «Actualizar», el tema claro/oscuro, el modo sin conexión y el enlace a la presentación. Los enlaces viejos
siguen abriendo algo con sentido: `vista=mvp`, `oportunidades` y `catalogo` llevan a `mochi`; `frecuencia` y
`verticales`, a `clientes`.

## 4. Qué queda, qué se fusiona y qué sale

| Bloque de hoy | Destino | Por qué |
|---|---|---|
| Qué hacer esta semana | **Se fusiona** en «Qué decidir» (Resumen) | Ahora son las 4 preguntas, con acción y enlace |
| 8 indicadores + evolución semanal | **Se fusionan** en «Cómo va» (5 indicadores con tendencia o comparación) | Un número sin comparación no ayuda a decidir; la serie completa sigue en «Ver tabla» |
| Combinaciones: tabla de Rappi | **Queda**, como gráfico de pesas (y su tabla completa) | Es el único dato real de personas y responde la pregunta 1 |
| Combinaciones propias y finas | **Salen** | Con simulados repiten el supuesto del simulador; las finas son detalle del motor (docs) |
| A quién rescatar + A quién invitar a volver | **Se fusionan** en «A quién estamos perdiendo» | Misma pregunta; ahora agrupado por lo que pedían, con la lista a pedido |
| Ofertas por momento + Sugerencias del agente + Servicios | **Se fusionan** en «Qué hace Mochi» | Misma pregunta para RappiAds |
| Evaluación del motor (4 tablas) | **Se resume** en una tabla motor vs línea base | Responde «¿funciona?» sin los detalles de método |
| Demanda no satisfecha + Búsquedas sin resultado + Surtido vs demanda + Conceptos que suben | **Se fusionan** en «Qué buscan y no encuentran» | Misma pregunta; cada fuente muestra lo que tiene |
| Embudo por vertical | **Sale** | Decisión de producto, no de gerencia ni RappiAds; el abandono de carrito queda en «Cómo va» |
| Retención por cohorte, días entre pedidos | **Salen** | Describen, no deciden; la regla de riesgo queda escrita junto a la cifra |
| Afinidad A → B | **Sale** | El agente no la usa y es simulada |
| ¿Retiene más quien usa dos verticales? | **Sale** | La tabla de Rappi responde lo mismo con datos reales; en simulados es por construcción |
| Catálogo: cobertura, calidad, productos en varias verticales | **Salen** | Salud del scraper (docs y README de resultados), no una decisión de Rappi |
| Accesos de la Home | **Sale** | No responde a una decisión; la Home dinámica se ve en la app |

Endpoints que el panel deja de pedir (siguen en la API): `funnel`, `cohorts`, `rhythm`, `multi-vertical`, `affinity`,
`catalog` y `home`. Sus respuestas guardadas salen de `src/fixtures/` y de las listas de `npm run fixtures` y
`make contract` (que solo las comparaba para el panel).

## 5. Reglas que no cambian

- Nunca una métrica simulada como evidencia; cada número dice su fuente (Simulado, Prototipo o «Dato de Rappi»).
- La tabla de Rappi se rotula «Dato compartido por Rappi» y «correlación, no efecto».
- Con el prototipo, cada sección lleva «uso del MVP, pocas personas: no es evidencia».
- Nada sensible se ofrece: las listas por persona usan su concepto top no sensible (la API ya lo filtra).
- Textos en español, código en inglés; sin rayas largas en el texto nuevo.

## 6. Pasos

1. Vistas nuevas en `src/views/{overview,customers,mochi}/` con sus funciones puras y tests; se borra lo que queda
   huérfano (vistas, gráficos de líneas/columnas/calor, fixtures).
   → verificar: `npm test`, `npm run lint`, `npx prettier --check src scripts`.
2. Gráficos revisados con la skill dataviz (pesas y chispas), modo claro y oscuro, 1280 px y tablet (768 px).
   → verificar: capturas de antes y después, sin scroll horizontal, sin errores de consola.
3. `make mvp-check` revisión 6: abre `?vista=mochi&fuente=prototipo` y busca la misma tabla, «Plan» y el rótulo.
   → verificar: 7 de 7.
4. Documentación: `dashboard-empresa/README.md`, `README.md`, `CLAUDE.md`, `docs/demo.md`, `docs/instalacion.md`,
   `docs/diseno-ia.md` §5, `docs/contexto-y-problema.md`, `docs/README.md` y una fila en `docs/decisiones.md`.
5. Revisión de código y de diseño con un subagente; PR contra main con capturas y esta tabla.

## 7. Después de la revisión de diseño (23-10)

Lo que cambió con la revisión de un subagente (capturas de antes y después a 1280, 768 y 390 px, claro y oscuro):

- La acción de Mochi nombra una sugerencia ganadora solo entre las de 50 o más mostradas (con 11 ganaba el azar) y
  muestra sus cuentas («24 de 86»). Con datos del prototipo la acción se llama «Para revisar en el MVP».
- «Pp» pasa a «puntos»; «Retención M+1», a «vuelven al mes siguiente»; las ventanas van en el título («Frecuencia (30
  días)»); los momentos de las ofertas llevan una línea que dice dónde se hacen.
- La escalera dice «correlación, no efecto» en su bajada, la leyenda ya no sugiere causa («Quienes además usan el
  grupo siguiente») y suma los pedidos por usuario de una y otra combinación. En el teléfono, el eje calza con los
  puntos (la columna de la diferencia tiene el mismo ancho en filas y eje).
- El motor: la primera fila aclara que no mide venta cruzada, y la diferencia sale de las cifras que se muestran.
- La demanda «sumar comercios» pide revisar primero el buscador.
- Bajo 900 px las tablas pasan a tarjetas; en el teléfono las pestañas usan nombres cortos.

Y el panel en un solo HTML («Panel Rappi.html», `npm run panel:snapshot` y `npm run panel:html`): las respuestas de una
API sobre `rappi_staging` grabadas en el archivo, que abre con doble clic sin la API ni internet.

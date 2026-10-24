# Preguntarle a Mochi en texto libre (24-10-2026)

Objetivo: que en el buscador con Mochi se le pueda escribir una pregunta («¿qué llevo para un asado de 6?», «algo
para la tos de mi hija», «quiero algo dulce y barato») y responda con productos reales y sus razones, con las mismas
guardias que el resto.

## Lo que ya había

- `POST /agent/ask` (`RappiAgent`) ya entiende saludos, ocasiones, conceptos, topes de precio, «barato», síntomas,
  servicios, «qué me recomiendas» y seguimientos. Responde con productos reales, «También en» y una sugerencia
  cruzada que pasa por `offers/guards.py`.
- En la app, el buscador con Mochi (`AssistantPanel`) solo le pregunta a Mochi con los chips («Arma un carrete»…):
  lo que se escribe en el campo va a `/search` y tapa la tarjeta de Mochi. No hay dónde escribirle.

## Diseño (skill design-taste-frontend; lectura: ajuste de producto dentro de la app, se conserva su lenguaje)

Un solo campo, sin modos ni pestañas:

1. El campo dice «Busca o pregúntale a Mochi» (hoy dice, en inglés, «What do you want today?»).
2. Apenas se escribe, la primera fila de resultados es **«Pregúntale a Mochi»** con lo escrito entre comillas y la
   mascota. Tocarla le pregunta eso a Mochi.
3. Si lo escrito parece una pregunta y no un producto (empieza con «¿», «qué», «cómo», «algo para», «tengo»…, o
   nombra una cantidad de personas o un presupuesto), esa fila va resaltada y **Enter** le pregunta a Mochi; si no,
   Enter sigue siendo buscar. La regla es corta y vive en un solo archivo (`assistant/question.js`).
4. Al preguntar, el campo se vacía, vuelve la tarjeta de Mochi con «Preguntaste «…»» y su respuesta, y el cuerpo sube
   al inicio. Lo demás (chips, «Olvidar», «Para ti») no cambia.

Sin animaciones nuevas: la fila usa el mismo estilo de las filas del buscador y el acento naranja de Mochi.

## Backend: lo que no resolvía (set de 40 preguntas, `eval/frases_usuarios/preguntas-libres.txt`)

Con reglas y los datos que ya hay, en `agent/understand.py` y `agent/rappi_agent.py`:

- **Cantidad de personas** («asado de 6», «somos 10», «para dos»): se entiende y se dice («Para 6 personas…»); en el
  asado, cuánta carne calcular (dato de la ocasión en `taxonomy.toml`, no del LLM).
- **Presupuesto con «con»** («qué puedo cenar con 8 mil pesos»): es un tope de precio.
- **Frases de pregunta** («qué llevo para», «qué compro para», «se me antoja», «cosas para»): no se buscan literal.
- **Ocasiones y palabras que faltaban**: picnic, frío («algo calentito»), «algo salado», «limpiar la casa»,
  «regalarle», «trago».
- **«¿Qué es un poke?», «¿qué lleva una paella?»**: una ficha corta del plato (`agent/glosario.toml`, datos escritos a
  mano) y lo que hay. Si el plato no tiene ficha, lo dice y muestra lo que hay.
- **«¿Con qué acompaño un salmón?»**: el complemento de ese concepto (la misma `suggest_complement`, con sus
  guardias), no más salmón.
- **Salud**: «¿qué le doy?», «¿qué me tomo?», dosis: Mochi no da consejo médico y no muestra remedios; dice que lo vea
  un médico o el químico farmacéutico. Un síntoma sin remedio que lo nombre ya no trae analgésicos «por si acaso».
- **Alcohol pedido** («qué trago me recomiendas»): se comporta como la búsqueda, con +18.

LLM: la redacción con Claude (`redaccion`) sigue igual y opcional, con plantillas de respaldo. No se usa para
entender ni para las fichas: las reglas alcanzan para estas preguntas y la demo no puede depender de la red.

## Demo sin conexión

`snapshot.json` graba las 40 preguntas (más las de antes) de la API real. Lo que no esté grabado: la API simulada
reconoce las preguntas de salud y de «¿qué es…?» y lo dice con honestidad («En esta demo sin conexión no puedo…»).

## Verificación

TDD (unitarios de `understand`, integración del agente), `make test`, `make lint`, `make contract` si cambia una
respuesta; en la app `npm test`, `npm run lint`, prettier; `make mvp-check` con una revisión nueva de «preguntarle a
Mochi». Tabla antes/después de las 40 preguntas en el PR.

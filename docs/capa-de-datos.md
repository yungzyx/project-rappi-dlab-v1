# La capa de datos para otras herramientas

La base guarda lo que Rappi publica. Esta capa le suma **significado**: qué es cada producto, de qué marca, cuánto trae, qué atributos tiene, con qué se relaciona y qué tipo de persona lo compra. Está pensada para que la búsqueda, las recomendaciones, el panel y cualquier herramienta futura lean lo mismo sin repetir el trabajo.

Todo lo que ve una herramienta externa vive en el esquema **`capa`**: vistas con nombres y columnas estables, comentadas en español. Las tablas internas pueden cambiar; las vistas no.

## Qué contiene

| Pieza | Qué responde | Dónde se define |
|---|---|---|
| **Medidas** | «¿Cuánto trae?»: cantidad, unidad base (g, ml, und), pack y total; marca las medidas que parecen un error de Rappi | `rappi_ia/layers/measures.py` |
| **Atributos** | «¿Qué es?»: 83 atributos en 9 familias (sin gluten, vegano, familiar, premium, para perro…) con fuente y confianza | `concepts/attributes.toml` |
| **Marcas y producto canónico** | «¿De qué marca?» y «¿es el mismo producto en otra tienda o vertical?» | `concepts/brands.toml`, `layers/brands.py`, `layers/canonical.py` |
| **Grafo de conocimiento** | «¿Con qué se relaciona?»: complementa, sustituye, es de la ocasión, se vende en, tiene el atributo, marca de, sinónimo… | `concepts/relations.toml`, `layers/graph.py` |
| **Segmentos de usuario** | «¿Qué tipo de persona es?»: 144 segmentos por comportamiento en 12 familias, con puntaje, nivel y evidencia | `concepts/segments.toml`, `layers/segments.py` |
| **Motor multivertical** | «¿Qué vertical conviene sumarle?» y «¿qué le toca pedir de nuevo?»: afinidad por vertical, transiciones, combinaciones de verticales con su retención, compra cruzada, tendencias y recompra | `rappi_ia/motor/`, `motor/combos.toml` |

Los conceptos (la taxonomía propia de 133 conceptos: 113 tipos de producto en 20 grupos) vienen de la capa de IA y son el eje que une todo.

## Vistas de `capa`

| Vista | Una fila es… | Para qué sirve |
|---|---|---|
| `capa.items` | un ítem (producto o plato) en una vertical | Punto de entrada: nombre, concepto, marca, canónico, medida y precio |
| `capa.item_attributes` | un atributo de un ítem | Filtrar por «sin gluten», «vegano», «familiar»… con fuente y evidencia |
| `capa.item_unit_prices` | el precio por kilo, litro o unidad de un ítem | Comparar precios de verdad (un sobre de 15 g es barato en la góndola y caro por gramo) |
| `capa.unit_price_ratios` | un ítem frente a la mediana de su concepto | Detectar precios mal cargados |
| `capa.item_brands` | la marca de un ítem | Marcas unidas («Coca-Cola» = «COCA COLA») y marcas propias de tienda |
| `capa.canonical_products` | un producto canónico | El mismo producto con distintos ids de Rappi o en varias verticales |
| `capa.knowledge_edges` | una arista del grafo | Relaciones entre conceptos, atributos, marcas, verticales y segmentos (sin lo aprendido de datos simulados) |
| `capa.segment_defs` | un segmento | Su definición y su regla |
| `capa.user_segments` | un segmento de una persona | A qué segmentos pertenece cada persona (sin los sensibles) |
| `capa.segment_sizes` | un segmento, semana y nivel | Cuántas personas hay en cada segmento (los sensibles solo con 5 o más) |
| `capa.user_vertical_affinity` | un vertical de una persona | Cuánto le interesa cada vertical, con sus pedidos y señales (personal) |
| `capa.vertical_transitions` | un paso de un vertical a otro, por fuente | Qué vertical pide la gente después de otro |
| `capa.combo_stats` | una combinación de grupos de verticales, por fuente | La tabla de Rappi medida con los datos propios: personas-mes, pedidos, gasto y retención al mes siguiente |
| `capa.combo_steps` | un paso de una combinación a otra al mes siguiente, por fuente | Qué pasa con quien usa «rest» el mes siguiente |
| `capa.cross_sell_rules` | una regla «quien pide A en un vertical pide B en otro», por fuente | Compra cruzada con confianza y lift |
| `capa.trends` | un vertical, concepto o producto, por fuente | Lo más pedido y lo que sube (4 semanas contra las 4 anteriores) |
| `capa.replenishment` | un concepto que una persona recompra | Cada cuántos días y cuándo le toca de nuevo (personal) |
| `capa.layer_runs` | una corrida de una capa | De dónde viene cada dato: qué reglas, cuándo y cuántas filas |

Cada vista y cada columna tienen comentario: `\d+ capa.items` en `psql` los muestra.

### Ejemplos

Los diez productos sin gluten más baratos por kilo en supermercado:

```sql
SELECT i.name, i.brand_name, p.price_per_kg
FROM capa.items i
JOIN capa.item_attributes a USING (entity_type, entity_id)
JOIN capa.item_unit_prices p USING (entity_type, entity_id, vertical)
WHERE a.attribute_id = 'sin-gluten' AND i.vertical = 'supermercado' AND p.price_per_kg IS NOT NULL
ORDER BY p.price_per_kg LIMIT 10;
```

En qué verticales se vende un concepto y qué lo sustituye:

```sql
SELECT relation, to_kind, to_id, round(weight::numeric, 2) AS peso
FROM capa.knowledge_edges
WHERE from_kind = 'concept' AND from_id = 'cafe' AND relation IN ('se_vende_en', 'sustituye', 'complementa')
ORDER BY relation, weight DESC;
```

Cuántas personas simuladas tiene cada segmento de comida en la última foto semanal (los datos de `synthetic` son simulados):

```sql
SELECT segment_name, level, users
FROM capa.segment_sizes
WHERE family = 'comida' AND source = 'synthetic' AND week = (SELECT max(week) FROM capa.segment_sizes)
ORDER BY users DESC LIMIT 10;
```

## Cómo se arma

`make layers` en `rappi-ia/` corre las capas en este orden (unos 70 segundos con el catálogo completo). `make post-refresh` lo incluye después de cada descarga semanal, junto con conceptos, embeddings, evaluación y datos simulados:

1. `measures`: tamaño, unidad y pack de cada ítem.
2. `brands`: marca canónica de cada ítem.
3. `canonical`: el mismo producto entre ids y verticales.
4. `attributes`: atributos (usan medidas y marcas).
5. `relations`: grafo de conocimiento.
6. `segments`: segmentos de cada persona, una vez por fuente (`synthetic` y `prototype`), con la foto semanal.
7. `motor`: el motor multivertical, una vez por fuente (ver abajo). También se evalúa por fechas y escribe `data/eval/motor-{fuente}.md`.

Cada paso corre en una transacción, es **idempotente** (correrlo dos veces deja lo mismo) y deja una fila en `layer_runs` (las capas, solo si terminan: una que falla se deshace con su transacción y no deja fila; el motor, en cambio, deja también su corrida en curso y la que falla, marcada `failed`) con la versión de las reglas (la fecha más una huella de su contenido: dos corridas con la misma huella usaron exactamente las mismas reglas). `make layer-report` genera `data/eval/capas.md`: cobertura por atributo y vertical, fuentes, medidas dudosas, marcas, canónicos, distribución de segmentos y una muestra de 20 ítems por atributo para revisar a ojo.

## Motor multivertical

Responde dos preguntas por persona: **qué vertical conviene sumarle** y **qué concepto le toca pedir de nuevo**. Vive en `rappi-ia/src/rappi_ia/motor/` (`model.py` son funciones puras; `data.py` lee la base; `build.py` escribe las tablas; `predict.py` responde por persona; `evaluate.py` mide) y se corre con `make motor` (o `rappi-ia motor [--source synthetic|prototype] [--sin-evaluar]`; `make layers` lo corre al final, y con él `make post-refresh`). Es otra capa más: deja su corrida en `layer_runs` con la fuente, los pesos y la evaluación. A diferencia de las otras capas, confirma primero una fila `running` y, si falla, deshace sus tablas pero deja la fila marcada `failed` (con la fuente y la clase del error).

| Tabla y vista | Qué guarda | Cómo se calcula |
|---|---|---|
| `user_vertical_affinity` | Cuánto le interesa cada vertical a una persona | Suma de señales de los últimos 180 días, cada una con su peso por 0,5 elevado a (días / 30): pedido 5, agregar al carro 1,5, abrir el vertical (`vertical_open`) 1, ver una tienda 1, buscar 0,5, ver un ítem 0,3. Guarda también los pedidos y señales de la ventana |
| `vertical_transitions` | Qué vertical pide una persona después de otro | Pedidos consecutivos de la misma persona, con suavizado de Laplace (+1) sobre los 8 verticales. Un carro repartido en dos verticales (mismo `cart_id`) no es una transición |
| `combo_stats` | La tabla de Rappi medida con los datos propios | Por persona y mes calendario (hora de Santiago), la combinación de grupos usada (`rest`, `turbo`, `retail`, en ese orden, unidos por «+»): % de personas-mes y de pedidos, pedidos y gasto por persona-mes y retención al mes siguiente, medida solo en los meses cuyo mes siguiente está completo (`retention_n`) |
| `combo_steps` | De qué combinación pasan a cuál al mes siguiente | Sobre los mismos meses con mes siguiente completo; quien no vuelve pasa a «ninguna» |
| `cross_sell_rules` | «Quien pide A en X pide B en Y» | B dentro de los 14 días después de A, en otro vertical **y en otro carro**; al menos 10 personas y lift sobre 1,2. Las líneas de B que vinieron de una sugerencia del agente no cuentan, ni los conceptos sensibles |
| `trends` | Lo más pedido y lo que sube | Las 4 semanas que terminan en el último pedido contra las 4 anteriores, por vertical, concepto y producto (los 50 más pedidos de cada vertical). `growth` = (ahora − antes) / max(antes, 5); sin conceptos sensibles |
| `replenishment` | Qué concepto recompra una persona y cuándo le toca | Al menos 3 días de compra distintos e intervalos regulares (variación ≤ 0,6); intervalo mediano y fecha del próximo. Sin conceptos sensibles |

### Población y persona

- **Población** (`vertical_transitions`, `combo_stats`, `combo_steps`, `cross_sell_rules`, `trends`): cada fila lleva `data_source` (`synthetic` o `prototype`) y las dos nunca se mezclan en un mismo cálculo. Cada corrida reemplaza las filas de su fuente. La predicción por persona lee la población que diga `config.MOTOR_POBLACION` (variable de entorno `MOTOR_POBLACION`; por defecto `synthetic`, porque con pocas personas del prototipo no hay patrón que aprender). Mientras sea `synthetic`, lo que el motor recomienda sale de patrones simulados y así se declara; con personas reales del prototipo se cambia en una variable.
- **Persona** (`user_vertical_affinity`, `replenishment`): se arman solo con los pedidos y señales de esa persona y se van con ella (`ON DELETE CASCADE`: «Olvidar» las borra). Sus vistas traen `source` (`synthetic` o `prototype`, de `app_users.source`, como `capa.user_segments`), y la de recompra no trae conceptos sensibles. Para una persona del prototipo se recalculan solas después de cada `POST /orders` (en segundo plano) y de «Olvidar»; a las simuladas las arma `make motor`. La afinidad que usa la predicción se calcula en vivo con las señales de la persona, así que no depende de cuándo corrió el motor.
- **Ranking de verticales**: puntaje = a × afinidad (normalizada, suma 1) + b × P(vertical | último vertical pedido) + c × popularidad (cuota de pedidos de los últimos 28 días). Con a = 1, `rappi-ia motor` elige b y c en una grilla por nDCG@8 en un tramo de validación y los guarda en la corrida; sin 84 días de pedidos usa los de partida (1 / 0,3 / 0,1), y si no hay a quién validar no guarda pesos nuevos.

### Guardias

- **Farmacia y Licores solo suben por señales propias de la persona**: no reciben peso de transiciones ni de popularidad, así que ningún patrón de otras personas los empuja.
- **Ningún concepto sensible** (los marcados `sensitive`, ver Privacidad) entra a compra cruzada, tendencias de concepto y de producto ni recompra.
- Lo que pasa en «Rappi hoy» no enseña: solo entran pedidos `mode = 'propuesta'` y ningún evento con `payload.mode = 'actual'`.

### La tabla de Rappi como punto de partida

`motor/combos.toml` guarda la tabla de combinaciones que compartió el equipo de Rappi (cohortes de enero a junio de 2026, Chile): para cada combinación de grupos, personas, % de personas y de pedidos, pedidos y gasto por persona y retención al mes siguiente. Es una **correlación, no un efecto**: quien pide mucho usa más verticales y además vuelve más. El motor la toma como punto de partida para decidir qué grupo sumarle a una persona (el que más sube la retención esperada), y mezcla esa retención con la aprendida de la población, que pesa lo que pesan sus personas frente a 100 «personas» de Rappi, y solo cuando la combinación tiene al menos 30.

La tabla viene con una agrupación gruesa de Rappi (`rest`, `turbo`, `retail`). La asignación de los verticales del proyecto a esos grupos es un **supuesto propio**: `retail` junta supermercado, conveniencia, farmacia, licores, mall y chocolatería; RappiFavor, que no tiene catálogo, queda fuera.

### Qué esperar de las cifras

`rappi-ia motor` mide el modelo por fechas (entrenar, validar y probar) contra líneas base y escribe un informe por fuente en `rappi-ia/data/eval/motor-{fuente}.md`; la última corrida sobre datos simulados está en [resultados/motor-2026-10-16.md](resultados/motor-2026-10-16.md). Sobre `synthetic` mide la mecánica, no el efecto, porque el generador ya supone que sumar verticales retiene (ver [decisiones.md](decisiones.md#datos-simulados-y-panel)).

## Datos simulados y datos reales

- Los productos, precios, atributos, marcas y el grafo del catálogo son **reales** (de rappi.cl).
- Las personas y sus eventos son **simulados** (`source = 'synthetic'`) o del prototipo (`'prototype'`). Los simulados muestran la mecánica, no evidencia: las vistas de `capa` marcan la fuente y `capa.knowledge_edges` oculta lo aprendido de ellos. Nunca se mezclan fuentes en un mismo cálculo. Las tablas del motor sí muestran lo aprendido de `synthetic` (cada fila lleva su `data_source`), a diferencia de `capa.knowledge_edges`; lo que se aprende de ahí se declara y se rotula como simulado.

## Privacidad

- Los segmentos que tocan salud o vida privada (sin gluten, sin lactosa, sin azúcar, bajo sodio, sin frutos secos, bebé, embarazo, adulto mayor, salud sexual, farmacia, uso continuo, tabaco y vapeo) están marcados `sensitive` y se **nombran por lo que la persona compra**, nunca por una condición («compra sin gluten», no «celíaco»).
- `capa.user_segments` no trae filas de segmentos sensibles, y la evidencia de un segmento común no nombra lo que mira uno sensible (si «cazaofertas» listara los pañales comprados, sería el mismo dato por otra puerta). `capa.segment_sizes` muestra un segmento sensible una sola vez, sin separar por nivel, y solo si tiene 5 o más personas y el resto de su fuente también son 5 o más (con 9 personas del prototipo, ninguno aparece). Las filas por persona de los sensibles quedan en la tabla interna; hoy ninguna otra pieza las lee.
- Esto es una **convención de la capa, no una frontera de seguridad**: no hay un rol de solo lectura, y quien tenga las credenciales de la base lee también las tablas internas.
- Los segmentos sensibles no generan aristas `afin_a` ni se usan para sugerir.
- «Olvidar» borra a la persona (y con ella sus segmentos e historia); olvidar un concepto recalcula sus segmentos sin él.
- Una sola persona no crea una relación en el grafo: `co_busqueda` exige sesiones de 5 o más personas distintas.

## Calidad medida

La cobertura dice cuánto se etiquetó, no si está bien. `rappi-ia layer-sample [--seed N]` arma una muestra fija de lo que la capa afirma: 10 ítems por atributo y regla, 3 por atributo declarado por Rappi, 140 marcas y 440 conceptos repartidos por método. En git van solo los ids y las afirmaciones (`rappi-ia/src/rappi_ia/eval/capas-muestra*.json`, con sus juicios en `capas-juicios*.json`); los nombres y descripciones para juzgar quedan en `rappi-ia/data/eval/`, fuera de git. `rappi-ia layer-precision [--seed N]` calcula la precisión por regla con el mínimo que se puede asegurar (límite de Wilson al 95 %), la cifra si los «dudoso» fueran errores, y lista las reglas bajo 80 %.

Se midió dos veces con jueces de modelos de lenguaje (10 agentes independientes por muestra): con las reglas originales (semilla 7) y, después de corregirlas, con una muestra nueva de otros ítems (semilla 11), para no medir con los mismos casos que guiaron los cambios.

| Qué | Antes | Después, muestra nueva | Después, si los dudosos fueran errores |
|---|---|---|---|
| Conceptos por regla de nombre | 81 % | 86 % | 83 % |
| Conceptos por mapeo de categoría, sección o cocina | 82 % | 88 % | 85 % |
| Conceptos por vecinos (embeddings) | 57 % | 88 % | 84 % |
| Atributos por reglas propias | 92 % | 92 % | 86 % |
| Atributos declarados por Rappi | 86 % | 86 % | 67 % |
| Marcas deducidas del nombre / declaradas | 99 % / 97 % | 98 % / 97 % | 97 % / 95 % |

Las correcciones: los vecinos solo deciden con 80 % de acuerdo; la cocina del local cuenta solo con un mapeo muy confiable («Asiática» ya no es sushi y «Combos» no dice el plato); la proteína del nombre de un plato le gana a una sección genérica; un ingrediente en el nombre de un plato («Macarrón Frutilla») no lo vuelve fruta; una sección sin mapeo que nombra un plato («Empanadas de Horno») sí da concepto; y se acotaron reglas de atributos que calzaban fuera de su ámbito. Los atributos no mejoraron fuera de muestra: esas correcciones atacaron errores puntuales. El costo: los restaurantes con concepto bajaron de 98,2 % a 94,7 %. Los agregados siguen el diseño de la muestra (prioriza reglas propias y platos), no la proporción de cada fuente en la base.

## Cómo agregar algo

| Quiero… | Qué hago |
|---|---|
| Un atributo nuevo | Una entrada en `attributes.toml` con sus frases (y, si sirve, el campo de Rappi que lo declara); un test con frases positivas y negativas |
| Un segmento nuevo | Una entrada en `segments.toml` combinando piezas (conceptos, atributos, palabras de consulta, horas, métricas…); el cargador valida que todo exista. Ver la cabecera del archivo para las piezas |
| Una relación curada | Una arista en `relations.toml` (los tipos y existencia de los nodos se validan) |
| Una vista para otra herramienta | Una migración que cree la vista en `capa` con `COMMENT` en la vista y en cada columna; un test lo exige |

Cambiar las reglas basta con volver a correr `make layers`: no hay que tocar código ni la base a mano.

## Límites que conviene conocer

- Los atributos salen de lo que Rappi declara y de frases en el nombre: dicen «el nombre dice sin gluten», no que el producto lo sea. La fuente y la confianza van en cada fila.
- `capa.canonical_products.verticals` se infla con tiendas que Rappi etiqueta en dos verticales.
- `co_busqueda` sale vacía mientras no haya sesiones reales con varios conceptos (el simulador genera un concepto por sesión).
- Los umbrales de los segmentos se calibraron con datos simulados: habrá que ajustarlos cuando haya uso real.
- `capa.segment_sizes` no impide deducir a una persona comparando dos semanas (un total sensible que sube de 5 a 6 cuando se sabe que se sumó una sola persona); el umbral de 5 es el de la spec; el panel de negocio usa 20.
- `capa.layer_runs` solo guarda las corridas terminadas de las capas de atributos a segmentos; una que falla no deja fila. El motor es la excepción: deja la corrida `running` y la `failed`.
- Las dos vistas personales del motor (`capa.user_vertical_affinity` y `capa.replenishment`) traen `source`, pero esa persona sigue siendo un id seudónimo y, como el resto de la capa, una convención y no una frontera de seguridad; la afinidad incluye también Farmacia y Licores, de la propia persona.
- Con pocas personas, la compra cruzada puede salir vacía (hacen falta 10 con el mismo patrón) y la recompra pide al menos 3 compras del concepto.

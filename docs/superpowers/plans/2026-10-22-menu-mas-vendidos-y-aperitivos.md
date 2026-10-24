# Restaurantes: «Más vendidos» en el menú y los aperitivos que caían en alcohol (cierre del MVP técnico)

**Objetivo:** dos arreglos de restaurantes. (1) El menú de la app muestra cada sección con todos sus platos, también
«Más vendidos». (2) La comida de las secciones «Aperitivo» deja de tomar un concepto de alcohol por el nombre de la
sección, sin que ninguna bebida alcohólica lo pierda.

## 1. «Más vendidos» en la página del restaurante

**Causa.** #126 (migración 040) guarda un plato que el menú repite una sola vez: `section_id` es la última sección
donde aparece y las demás van en `menu_items.extra_section_ids`. `_MENU` (`catalog/restaurants.py`) une los platos
con su sección solo por `mi.section_id`, así que «Más vendidos» (casi siempre la primera, y la que el plato no tiene
como última) sale vacía o no sale.

**Diseño.**
- `_MENU` une cada plato con todas sus secciones: `ms.section_id = mi.section_id OR ms.section_id =
  ANY(mi.extra_section_ids)` (la regla de CLAUDE.md). Una fila por (plato, sección): un plato no se repite dentro de
  una sección aunque el arreglo traiga repetidos o su propia sección, y un id de una sección que ya no existe no
  suma nada. El orden sigue igual: posición de la sección y, dentro de ella, el id que les dio Rappi.
- La sección virtual «Lo más pedido» (`is_popular`) agrega cada plato una sola vez: con varias filas por plato se
  repetía.
- La forma de la respuesta no cambia (`sections: [{name, items}]`): el contrato (`make contract`) no debería cambiar;
  se corre para comprobarlo. La app ya pinta un plato en varias secciones (las llaves son por sección).
- Fuera: la portada de la tarjeta (`_CARDS`) sigue con la sección propia del plato (como antes de #126).

**Pruebas.** Integración sobre `seed_demo` en `rappi_ia_test`: un «Más vendidos» con platos de otras secciones
(incluido un popular), un arreglo con repetidos y con la propia sección, y un id de sección que no existe. A mano: la
API y la app sobre una base de prueba propia (`rappi_menuchk_test`, sembrada con `seed-demo` y un «Más vendidos»),
en puertos libres (8020 y 5194), sin tocar la demo de `~/Rappi`.

## 2. Aperitivos que caen en alcohol

**Causa (base `rappi` en solo lectura, simulación de reglas y kNN en memoria, 22-10-2026).** Un plato cuyo nombre
no dice qué es toma el concepto de su sección por `_from_section_name`. «aperitivo» es keyword de `licores`, así que
quesos, sopaipillas, papas y chorizos de secciones «Aperitivos» quedan como alcohol: Mochi no los ofrece (la
dirección segura), pero es un error. Lo mismo pasa con «Cocktail» en singular, que en Chile es comida para picar
(«Emp. queso horno cocktail»). Esas secciones también traen cócteles cuyo nombre no dice alcohol con las palabras de
las guardias («Vaina», «Tom Collins», «Algarrobina») y para ellos el concepto de alcohol es la única protección: la
guardia de secciones (`alcohol_section`) no ve «Aperitivos».

**Diseño (cero fugas por construcción, comprobado a mano).**
- La sección sigue mandando por defecto: un plato que no se reconoce (ni comida ni trago) se queda con el alcohol de
  la sección, como hoy.
- Solo en una sección ambigua (la palabra que la lleva a alcohol es «aperitivo(s)» o «cóctel»/«cocktail» en
  singular, y las guardias no la ven como de tragos: «Aperitivos & Tragos» sigue siendo de tragos) la sección no
  decide para un plato cuyo nombre dice comida sólida (quesos, fiambres o verduras: «Queso Brie», «Chorizo», «Papas
  Supremas», «Sopaipilla de zapallo») y cuyo nombre y descripción no dicen alcohol: ni una keyword de alcohol de la
  taxonomía, ni una palabra de alcohol de las guardias de menús (sour, schop, michelada…), ni una graduación. Frutas,
  lácteos y huevos no cuentan como comida: están en los cócteles («Mango Sour», «Piña Colada», «Ruso Blanco»).
  `assign_menu_item` recibe la descripción del plato (`menu_items_for_assignment` la lee).
- Los cócteles conocidos se reconocen por su nombre en cualquier sección: keywords nuevas en `cocteles` y `licores` de
  la taxonomía, elegidas con la base (un nombre que en el catálogo o en los menús es otra cosa no entra: «mule» son
  tazones de cobre, «negroni» es una marca de salames y tomates, «chilcano» es una sopa, «manhattan» una hamburguesa,
  «cola de mono» un sabor de té y helado).
- Agregado tras la primera medición: el kNN no saca del alcohol a un plato que la sección puso ahí («Jengibre Sour»
  de «Aperitivos» pasaba a salsas y se podía ofrecer), y «cocktelería» (otra ortografía) es una sección de tragos.
- Agregado tras la revisión de código: lo que sale de la sección debe no decir *bebida* (también una palabra de bebida,
  un volumen o una palabra de sección de tragos de las guardias: «Pepino Tonic» no es comida), una sección es ambigua
  solo si nada más en ella dice bebida («Aperitivos y Whisky» no lo es), los cócteles nuevos van también a las palabras
  de alcohol de los platos en las guardias (si el kNN los saca del alcohol, el nombre los bloquea), y «vaina» y
  «algarrobina» quedan solo en las guardias (en la taxonomía tocaban porotos, vainilla y un jarabe en las búsquedas).
- Medición, en solo lectura: reglas y kNN en memoria con el código de main y con el de la rama sobre `rappi`; cada
  plato o producto que cambia de concepto se clasifica a mano; además, la lista completa de los platos de secciones
  de aperitivo, tragos o bar, y para todos los platos, cuáles pasan a poder ofrecerse (concepto, nombre y sección
  por las guardias de ofertas): ninguno puede ser una bebida alcohólica. Si no se puede garantizar, la regla de la
  sección queda como está y el PR lo explica.
- Se anota la decisión en `docs/decisiones.md`. Recalcular conceptos en `rappi` queda para después de fusionar
  (`make concepts layers` en rappi-ia, desde main).

## Pasos

1. Tests que fallan (TDD): integración del menú (paso 1) y unitarios de `assign_menu_item` (paso 2).
2. `_MENU` y `restaurant_menu`; `_from_section_name`, la descripción en `menu_items_for_assignment`/`pipeline` y las
   keywords de la taxonomía.
3. `make test` y `make lint` en rappi-ia; `make contract`; la app a mano (y `npm test`/`npm run lint` si se toca).
4. Simulación antes/después sobre `rappi` en solo lectura y clasificación a mano.
5. `docs/decisiones.md`, revisión de código con un subagente y PR.

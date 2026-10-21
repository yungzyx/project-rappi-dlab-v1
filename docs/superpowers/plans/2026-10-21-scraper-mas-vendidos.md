# Scraper: un plato en «Más vendidos» y en su sección queda en las dos (fase 3 de 4)

**Objetivo:** que el scraper de restaurantes no pierda la señal de «lo más pedido» del menú público (borrador #106).

## Causa (base `rappi` en solo lectura y fixture `restaurant.html`, 21-10-2026)

Rappi manda el menú como una lista de pasillos (`corridors`), cada uno con sus platos. Un plato que el local pone en
«Más vendidos» viene dos veces: en ese pasillo y en el suyo, con el mismo `id`. `parse_restaurant` agrega un ítem por
aparición, y `save_restaurant` los guarda con `ON CONFLICT (store_id, rappi_item_id) DO UPDATE SET section_id = …`:
gana la última aparición. «Más vendidos» es la primera sección del menú en 32 de las 66 secciones populares, la
última en 2 y queda al medio en 32: la última aparición suele ser la sección propia, pero no siempre. Así:

- de las 66 secciones populares (la regla de #106, `_TOP_SECTION`) de 62 locales, 24 quedan vacías;
- en la corrida 8, 93 locales guardaron 773 apariciones repetidas (el `items` del job menos los platos distintos);
- `is_popular` también lo pone la última aparición (hoy lo tienen 3 platos de un local, ninguno en una sección popular).

Las secciones no chocan entre sí: el `section_id` de «Más vendidos» es su propio `corridorId` (ningún local tiene
huecos en las posiciones de sus secciones).

## Diseño

- `menu_items.extra_section_ids bigint[] NOT NULL DEFAULT '{}'` (migración 040): las otras secciones del menú donde
  también está el plato. `section_id` no cambia de significado (la última aparición, como hoy), así que la búsqueda,
  los conceptos, las guardias de alcohol por sección y el menú de la app leen la misma sección. Sí cambia `is_popular`
  si una aparición lo marca y la última no (hoy lo tienen 3 platos). Con `'{}'` por defecto, los que insertan platos a
  mano (la demo, los tests de rappi-ia) siguen bien, y un plato en una sola sección no cambia.
- `parse_restaurant` devuelve un ítem por plato: los datos de su última aparición, `extra_section_ids` con las demás
  secciones y `is_popular` si Rappi lo marca en alguna.
- `save_restaurant` guarda y actualiza `extra_section_ids` como las demás columnas: cada descarga la reemplaza. El
  `items` del resultado de cada job pasa a contar platos distintos (antes, apariciones); nada lo lee.
- Sin llenado: los platos de hoy no traen cuántas veces aparecían. La base `rappi` lo tendrá recién con la próxima
  descarga semanal de restaurantes.
- Quien lea «los platos de una sección» la junta con
  `ms.section_id = mi.section_id OR ms.section_id = ANY(mi.extra_section_ids)` (#106, en `candidates` y en el nombre de
  sección que filtra `_TOP_SECTION`; la consulta 2.4 de `docs/sql/consultas.sql`).

Descartado: una marca `in_top_section` en el plato. Obliga al scraper a decidir qué nombre de sección es «lo más
pedido», que es regla de rappi-ia (#106), y no sirve para nada más.

## Pasos

1. Tests que fallan (TDD): un menú con un plato en «Más vendidos» y en «Hamburguesas» da un solo ítem con las dos
   secciones (unitario, sobre el fixture con un pasillo agregado) y queda así en la base (integración, `rappi_test`),
   también al volver a descargarlo sin «Más vendidos»; el fixture tal cual (sin repetidos) da los mismos ítems que hoy.
2. Migración 040, parser y repository.
3. `make test` y `make lint` en rappi-scraper y `make test` en rappi-ia (lee `menu_items`).
4. Estimación de cobertura con la base `rappi` en solo lectura (antes y techo después) y PR.

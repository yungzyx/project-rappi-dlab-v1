# Búsqueda: un número o una palabra suelta no basta para mostrar un producto (fase 1 de 4)

**Objetivo:** que «neumáticos aro 15» en Express no muestre jugos en polvo Zuko «15 g». Si la vertical no tiene lo
pedido, queda vacía (el vacío honesto) y la búsqueda agrupada muestra dónde sí se vende, como ya hace desde el PR #116.

## Causa (base `rappi`, 21-10-2026, en solo lectura)

«neumáticos aro 15» en conveniencia nombra el concepto `automotriz`, y la vertical lo tiene: 34 ítems de cuidado del
auto (cubreautos, cera, silicona), sobre el piso de «sin resultado» (`concept_in_vertical`). Ninguno dice «neumáticos»
(df 0) y «aro» está en 2 documentos, así que la léxica se llena con los 123 que dicen «15». La vectorial (e5) también
pone arriba los nombres cortos con «15 g» o «x15». En la fusión (RRF) gana lo que está en las dos listas, y los ítems de
`automotriz` quedan en los puestos 13, 18 y 25 aunque tengan el refuerzo por concepto: fuera de los 12 que mira
`agent/tools._focus`.

En `_focus`, si nada de lo encontrado es del concepto pedido:

- el vertical no vende el concepto: solo lo que lo dice en su nombre (`_names_query`, PR #116);
- **el vertical sí lo vende: se muestra todo lo encontrado.** Por esta salida se cuelan los Zuko.

La misma salida explica otros tres casos del barrido inicial: «televisor 50 pulgadas» en conveniencia (cuchillos, un
licor de 50 grados, hilo dental de 50 m), «bicicleta aro 20» en Turbo (servilletas, film de 20 m) y «zapatillas talla
42» en farmacia (pañales y un pantalón «talla»).

## Regla

En `_focus`, la regla del nombre del PR #116 rige también cuando el vertical vende el concepto: si nada de lo
encontrado es del concepto pedido, solo se muestra lo que dice lo pedido en su nombre. Siguen igual las excepciones de
#116 (una ocasión, «algo para el asado», o un concepto `broad`), la regla de «sin resultado», τ y el orden de la
búsqueda. No hay consultas extra.

Queda fuera, y se informa en el PR: las consultas que no nombran ningún concepto («colchón 2 plazas» en Turbo trae un
ratchet y pilas «2 unidades»). Ahí decide τ, que en Turbo, Mall y Chocolatería está en el piso de la grilla o cerca.

## Pasos

1. Tests que fallan (`tests/integration/test_search_out_of_place.py`, sobre `seed_demo`): una vertical que vende el
   concepto pedido, pero cuyos productos con el número de la consulta son de otro concepto («neumáticos aro 15» en
   Express) no los muestra; lo legítimo sigue: «leche 1 litro», «cerveza pack 6» en Licores, «sándwiches» en Express,
   «algo para el asado» en Licores. Además, la búsqueda agrupada sin el grupo de Express.
2. El arreglo en `_focus` y su docstring.
3. Medición en la base real, en solo lectura: el barrido de 42 consultas fuera de lugar y 25 legítimas, el barrido de
   #116 (2 keywords por concepto × 8 verticales, con y sin una medida al final, más las búsquedas de ofertas por
   nombre de concepto) y `rappi-ia eval-search` (sin `--guardar-tau`), antes y después.
4. `make test` y `make lint` en rappi-ia; `make contract` si cambia una respuesta de ejemplo; docs
   (`docs/decisiones.md`, `docs/diseno-ia.md` §1).
5. Revisión de código con un subagente, PR contra main y aviso a la sesión que coordina con el CI en verde.

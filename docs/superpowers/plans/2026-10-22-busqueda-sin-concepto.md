# Búsqueda: sin concepto ni ocasión, el τ de la vertical no basta (cierre del MVP técnico)

**Objetivo:** que «sofá de tres cuerpos» en Turbo no muestre pisco Tres Erres, ni «colchón 2 plazas» un ratchet y
pilas «2 unidades». Si la vertical no tiene lo pedido, queda «sin resultado»: se anota la demanda y la búsqueda
agrupada dice dónde sí hay.

## Causa (base `rappi`, 22-10-2026, en solo lectura)

Cuando la consulta no nombra un concepto y nada calza todas sus palabras, «sin resultado» depende solo del coseno
máximo contra el τ de la vertical (`retrieval.hybrid._unmet`). Si no cae, `agent/tools._focus` muestra todo lo
encontrado. Los cosenos de e5 se concentran (0,78 a 0,86), así que un τ por vertical no separa:

| Vertical | Negativas sin concepto (coseno máx.) | Positivas sin concepto (coseno máx.) |
|---|---|---|
| Turbo (τ 0,79) | colchón 2 plazas 0,824 · sofá 0,821 · gasfiter 0,831 · cancha de pádel 0,826 | «cuchuflis» (error de tipeo) 0,843 |
| Súper (τ 0,81) | sofá 0,839 · arriendo departamento 0,821 | algo calentito para la once 0,827 · «nutela» 0,824 |
| Mall (τ 0,70) | sofá 0,839 · hotel 3 noches 0,821 | regalo para mi polola 0,819 |

Exigir que el nombre diga alguna palabra de la consulta tampoco separa: «colchón 2 plazas» en Turbo trae un yogur
«Colchón de Frutas», «hotel 3 noches» en el Mall un libro «Hocus Pocus Hotel» y «entradas para el estadio 2
personas» en chocolaterías tortas «8 Personas».

Lo que sí separa: las cuatro positivas del set que dependen de τ nombran una **ocasión** («once», «regalo»,
«antojo», «guagua»). De las negativas sin concepto, ninguna nombra una. La búsqueda agrupada ya trata así las consultas
sin concepto ni ocasión: solo entra una vertical que calce todas las palabras o con coseno ≥ `ALL_VERTICALS_TAU`
(0,85, calibrado en la base real). La búsqueda de una vertical (`/search?vertical=`, Mochi) usaba el τ de la vertical.

## Regla

En `_unmet`, si la consulta no nombra concepto **ni ocasión** y nada calza todas sus palabras, el τ es el de la búsqueda
agrupada (0,85) en vez del de la vertical. El τ de la vertical queda para las que nombran una ocasión sin concepto
(«regalo para mi polola» en el Mall). Se reutiliza:

- `named_occasion` y sus keywords de `taxonomy.toml` (la excepción de la ocasión de #116 en `_focus`), que pasa de
  `agent/tools.py` a `retrieval/hybrid.py` junto a `detect_concepts`, porque la recuperación no importa del agente;
- `ALL_VERTICALS_TAU`, que pasa de `agent/grouped_search.py` a `retrieval/hybrid.py` como `UNNAMED_TAU` (ya no es solo
  de la búsqueda en todas las verticales);
- `_focus` sin cambios: con «sin resultado», sin concepto, ya no muestra nada.

La evaluación (`eval/search_eval._is_unmet`, `calibrate_tau`, `negative_diagnosis`) sigue la misma regla. τ solo se
calibra con las consultas que nombran una ocasión: el resto ya no depende de él. Sin consultas extra a la base.

Costo esperado (barrido de las 378 frases de `eval/frases_usuarios` × 8 verticales): 256 de 3.024 búsquedas dejan de
mostrar algo. Casi todo es ruido («+ más barato», «cuál es la capital de francia», «hotel en viña del mar»). Lo útil
que se pierde son errores de tipeo («cervezaaaa», «nutela») y síntomas sin palabra de ocasión («remedio para la tos»).
La búsqueda agrupada ya los perdía: ninguno llega a 0,85.

## Pasos

1. Set renovado (`eval/queries.json`): cada negativa contra el catálogo; las que tienen oferta pasan a positivas;
   negativas nuevas sin concepto ni ocasión (con números o medidas) y positivas de control sin concepto. Línea base
   con `rappi-ia eval-search` (sin `--guardar-tau`).
2. Tests que fallan (`tests/integration/test_search_out_of_place.py`, sobre `seed_demo`): «sofá de tres cuerpos» y
   «colchón 2 plazas» en Turbo, con un coseno sobre el τ de Turbo y bajo 0,85. Controles: una marca y un nombre de
   producto sin concepto (calzan todas sus palabras) y una ocasión sin concepto siguen mostrando productos. Más los
   unitarios de `_unmet` y de la evaluación.
3. El cambio en `_unmet`, `named_occasion` y `UNNAMED_TAU` en `hybrid.py`, y la evaluación.
4. Medición en la base real, en solo lectura: `eval-search` antes y después con el mismo set, el barrido de frases y
   los sondeos de #125 (42 fuera de lugar, 25 legítimas).
5. `make test` y `make lint` en rappi-ia; `make contract` si cambia una respuesta de ejemplo; docs (README#resultados,
   reporte de búsqueda en `docs/resultados/`, `docs/decisiones.md`, `docs/diseno-ia.md` §1).
6. Revisión de código con un subagente, PR contra main y aviso a la sesión que coordina con el CI en verde.

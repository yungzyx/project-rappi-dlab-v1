# Búsqueda que tolera errores de tipeo (24-10)

## Problema
#129 dejó en 0,85 el τ de una consulta sin concepto ni ocasión que no calza todas sus palabras. Dejaron de salir
vecinos sin relación, pero también los errores de tipeo: «nutela» en el súper, «cuchuflis» en Turbo, «cervezaaaa» en
Licores y «eh quiero este una coca» quedan «sin resultado».

## Idea
Corregir la consulta **solo cuando la búsqueda queda «sin resultado»** y volver a buscar con las reglas de siempre. Lo
que hoy encuentra algo no cambia (ni el nDCG ni lo que se muestra), y una negativa solo deja de serlo si la consulta
corregida pasa las mismas reglas de #129.

1. **Vocabulario del catálogo** (`search_vocabulary`, migración 041): cada palabra de `search_documents.content`, sin
   tildes, en minúsculas, por vertical, con en cuántos documentos está. Índice de trigramas (`pg_trgm`, extensión
   «trusted»: la crea rappi_owner; igual va en `deploy/db/init-roles.sh` y en `restore-check.sh` como las demás). Lo
   rearma `build_search_documents` en la misma transacción (los tests y el catálogo inventado también lo tienen).
2. **Corrección** (`rappi_ia/retrieval/spelling.py`), palabra por palabra:
   - se quitan las muletillas y las palabras de pedido («eh», «este», «quiero», «una»…);
   - letras repetidas tres o más veces: «cervezaaaa» → «cerveza» (o «ll», «rr»: la forma que tenga más documentos);
   - una palabra de 5 letras o más que la vertical casi no tiene se cambia por la más parecida que la vertical tiene
     al menos 10 veces más: candidatas por trigramas, distancia de edición (con trasposición) 1, o 2 desde 8 letras;
     entre las más cercanas gana la de más documentos. No se cambia por su plural o singular (la raíz ya los junta).
   - la búsqueda agrupada corrige con el vocabulario de todas las verticales, una vez, si ninguna vertical calza todas las palabras.
3. **Respuesta**: `/search` dice `corrected_query` (null si no corrigió); con `correct=false` busca tal cual. Un
   concepto detectado tras corregir usa las reglas normales (la corrección es otra consulta, no otra regla).
4. **App**: «Mostrando resultados para "nutella"» y «Buscar "nutela" tal cual», en `SearchResults` (buscador con Mochi
   y el de cada vertical). `make contract` con un ejemplo corregido.
5. **Evaluación**: `eval/typos.json` (≥ 40 errores de tipeo con lo que se quiso escribir y su motivo) y
   `rappi-ia eval-typos`: recuperado si no queda «sin resultado» y muestra al menos 3 de los 5 primeros productos de
   lo que se quiso escribir. Las 58 negativas de `eval/queries.json` se miden con la corrección (deben seguir sin
   resultado), y `eval-search` mide lo que ve el usuario con la corrección. Latencia p50/p95 de `/search` antes y
   después.

## Criterios
- Precisión de «sin resultado» 1,00; recall ≥ 54 de 58; nDCG@10 igual; la mayoría del set de tipeo recuperada.
- `make test`/`make lint` (rappi-ia y rappi-scraper), `npm test`/lint/prettier en prototipo-app, `make mvp-check`.

## Fuera
- Mochi (`agent/rappi_agent.py`) no corrige todavía: lo trabaja otro chat; `search_products(correct=True)` queda listo.
- Las keywords de conceptos no entran al vocabulario (casi todas están en el catálogo).

## Cambios durante la implementación (medidos en `rappi_staging`)
- Se corrige cuando **nada calza todas las palabras** (no solo con «sin resultado»: «heladoo de chocolate» mostraba
  chocolates), y lo corregido se acepta **solo si calza todas sus palabras** («pasaje … punta arenas» → «masaje …
  avenas» no). La agrupada sigue la misma regla.
- Guardas que salieron del barrido de frases y de la revisión de código: no se corrigen palabras con 20 documentos o
  más en el catálogo, conceptos, números, ocasiones ni lo que le habla al asistente; ni se cambia por una stopword o
  una palabra de la misma raíz (en vez de la regla de plurales). Mínimo 6 letras para cambiar una letra (5 para una
  letra doble), dos ediciones desde 9. Muletillas solo al inicio y si queda una consulta corta.
- `pg_trgm` no va en `init-roles.sh` (es «trusted»: la crea rappi_owner), y su comentario se salta si no es dueño.
- El vocabulario guarda cómo escribe el catálogo cada palabra (`display`), para el aviso.
- La evaluación mide la búsqueda agrupada (la de la app) además de la de una vertical, y un producto «es de lo
  pedido» si su nombre dice lo que se quiso escribir.

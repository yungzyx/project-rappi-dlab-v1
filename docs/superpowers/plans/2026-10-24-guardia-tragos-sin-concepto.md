# Ofertas: los tragos que solo dice la descripción (cierre del MVP técnico)

**Objetivo:** que Mochi no ofrezca por su cuenta un trago o un combo con alcohol que no tiene concepto ni dice alcohol
en el nombre ni en la sección: solo la descripción lo dice (pendiente de #130: los cócteles de «Barra Barbazul»).

## Medición (base `rappi`, 24-10-2026, solo lectura)

De 179.353 platos, 12.395 no tienen concepto; 12.293 tienen precio y las guardias de `main` los dejan ofrecer
(`agent/tools._allowed` no es estricto con lo que no tiene concepto). De esos, 371 tienen alguna señal de alcohol en la
descripción o la sección. Clasificados a mano:

| Grupo | Platos | Ejemplos |
|---|---|---|
| Tragos | 22 | los 10 «… Deli» de «Barra Barbazul» («Vodka ron gin blue curacao…, 475cc o 1 litro»), «HAVANA ESPECIAL» y «ABSOLUTE BLUE» («Corto + Bebida», en «Combinados» junto a platos peruanos), «Growler 2 L» («Cerveza a elección»), «Agave Azul» (en «Principales») |
| Combos o packs con alcohol | 22 | «Promo 4» (+ 2 cervezas Heineken), «Pack Parrillero» (+ botella de Alto del Carmen o fernet), packs de quesos con un vino de regalo, «Menú Ejecutivo» con pisco sour |
| Comida con alcohol en la receta | 80 | risottos al vino blanco, canelés al ron, cannoli al marsala, leche de tigre con pisco |
| Comida o bebida sin alcohol, con otra palabra | el resto | «cóctel de camarones», «empanaditas cóctel», «sour cream», «chocolate bitter», kombuchas, tónicas, café «corto» |

Mirar la descripción de **todos** los platos tocaría unos 1.000 platos ofrecibles con un concepto de comida que nombran
alcohol, casi todos comida (seco de vacuno a la cerveza, tiramisú). Sin concepto son 126, y 44 son alcohol. Las
alternativas sugeridas no alcanzan: exigir además una señal de bebida (ml, cc, vaso, «con hielo») deja pasar «Promo 4»,
«Growler 2 L», «Agave Azul» y los packs con vino; ser estrictos solo en secciones de bar deja pasar «Combinados»,
«Principales», «Promociones» y «Bebestibles».

## Regla

`offers/guards.alcohol_in_description(descripción, concepto)`: un plato **sin concepto o con uno de bebida** (grupo
`bebidas`: un concepto como gaseosas o café no dice si el trago lleva alcohol; un concepto que ya no está en la
taxonomía cuenta como sin concepto) cuya descripción nombra alcohol cuenta como +18 en una oferta. Las palabras: las de
los nombres de platos (`MENU_ALCOHOL_NAME_WORDS`) sin «vaina» ni «algarrobina», más tragos («trago», «chilcano»,
«alcohólica», «con alcohol»), destilados, licores y sus marcas (mezcal, fernet, jägermeister, kahlúa, triple sec,
havana, alto del carmen, mistral, aperol, vermouth, coñac, smirnoff, bacardi…), el cóctel y el corto. Una descripción es
larga, así que solo la libra una frase de comida pegada a la palabra («cóctel de camarones», «empanaditas cóctel»,
«sour cream», «pizza margarita», «espresso corto»), no una palabra de comida en otra parte («tabla de empanadas + 2
cócteles»): las frases sueltas de los nombres («papas», «roll», «jugo») no sirven aquí. «Sin alcohol» no la libra
(«Mojito con o sin alcohol»), y «alcohol» solo no cuenta: casi siempre es «sin alcohol». La aplican los tres caminos
que ofrecen platos: `agent/tools._with_prices` (búsquedas de oferta), `offers/engine._priced_in_vertical` (lo más
pedido) y `offers/engine._find_popular_dishes` (los populares de «vertical por probar»), sobre
`clean_html(mi.description)`. Los nombres suman «absolut», «absolute» («ABSOLUTE PEAR» tenía concepto sandwiches) y
«ramazzoti» (mal escrito). La búsqueda y la pregunta no cambian.

Demo sin conexión (`src/api/offline/offers.js`): la API no da descripciones, así que la muestra no las tiene; ahí
ningún plato sin concepto o con concepto de bebida se ofrece (más estricto que el backend: un café de un restaurante
tampoco), y los nombres de platos suman «absolut» y «absolute».

## Cero fugas

Guardias de `main` contra las de la rama, sobre todos los platos con precio: 160 pasan a bloqueados y ninguno se
libera. Los 160, revisados uno por uno: 52 fugas cerradas (los 44 de arriba, 7 tragos con concepto de bebida como
«Gautama Jack» o un café irlandés, y «ABSOLUTE PEAR»), 2 dudosos con alcohol (un americano con amaretto, un helado con
whisky), 82 comida (con alcohol en la receta o con otra palabra: «Cóctel de jugo de limón con trozos de pescado») y 24
cosas sin alcohol (cafés con jarabe de amaretto, piñas coladas sin alcohol, espressos «cortos», jugos «en cada
trago»). De los que se siguen pudiendo ofrecer sin concepto o con concepto de bebida, 1.002 tienen alguna señal amplia
(también «sin alcohol», «shot», «tónica», «drinks», «barra», «combinado», «anís»): revisados todos, ninguno es un trago.

La revisión de código (subagente) encontró que una primera versión heredaba de los nombres frases de comida de una
palabra, que en una descripción larga la libraban («tabla de empanadas + 2 cócteles», «2 rolls + 2 sour de
maracuyá», «piña colada con o sin alcohol»), que faltaban «trago», «chilcano», «prosecco» y marcas, que no miraba los
populares de «vertical por probar» ni limpiaba el HTML de la descripción. No había casos así en la base; quedaron
arreglados con tests, y las cifras son de la versión final.

## Pendiente (fuera de este cambio)

Con un concepto de comida, la descripción no cuenta, y ahí quedan tragos: «Mega Tropical Summer», «Tropical Summer» y
«Malfy Originale» (gin, concepto pizza, secciones «Botellas» y «Gin»), «Pack ballentines» (pizza, «Pack Botellas»),
«Mai Tai» (sushi, «Cock Ta Ils»), «Enkai Fresh» (sushi). Las secciones «Gin», «Botellas» y «Cock Ta Ils» no son
palabras de tragos de las guardias.

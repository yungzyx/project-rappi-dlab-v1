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
`bebidas`: un concepto como gaseosas o café no dice si el trago lleva alcohol) cuya descripción nombra alcohol cuenta
como +18 en una oferta. Las palabras: las de los nombres de platos (`MENU_ALCOHOL_NAME_WORDS`, con sus sentidos de
comida) sin «vaina» ni «algarrobina», más destilados y licores (mezcal, fernet, jägermeister, kahlúa, triple sec,
havana, alto del carmen, mistral, aperol, campari, vermouth, coñac, brandy, bourbon, baileys, amaretto), el cóctel
(salvo el de camarones o el tamaño de las empanadas) y el corto (salvo el de café o el queso). «Sin alcohol» no la
libra («Mojito con o sin alcohol»). La aplican los dos caminos que ofrecen platos: `agent/tools._with_prices`
(búsquedas de oferta) y `offers/engine._priced_in_vertical` (lo más pedido). Los nombres suman «absolut», «absolute»
(«ABSOLUTE PEAR» tenía concepto sandwiches) y «ramazzoti» (mal escrito). La búsqueda y la pregunta no cambian.

Demo sin conexión (`src/api/offline/offers.js`): la API no da descripciones, así que la muestra no las tiene; ahí
ningún plato sin concepto o con concepto de bebida se ofrece, y los nombres suman «absolut» y «absolute».

## Cero fugas

Guardias de `main` contra las de la rama, sobre todos los platos con precio: 150 pasan a bloqueados y ninguno se
libera. Los 150, revisados uno por uno: 52 fugas cerradas (los 44 de arriba, 7 tragos con concepto de bebida como
«Gautama Jack» o un café irlandés, y «ABSOLUTE PEAR»), 2 dudosos con alcohol (un americano con amaretto, un helado con
whisky), 80 comida y 16 cosas sin alcohol (cafés con jarabe de amaretto, una cerveza sin alcohol, combos de pizza
«margarita» con concepto gaseosas). De los que se siguen pudiendo ofrecer sin concepto o con concepto de bebida, 1.010
tienen alguna señal amplia (también «sin alcohol», «shot», «tónica», «drinks», «barra», «combinado», «anís»): revisados
todos, ninguno es un trago.

## Pendiente (fuera de este cambio)

Con un concepto de comida, la descripción no cuenta, y ahí quedan tragos: «Mega Tropical Summer», «Tropical Summer» y
«Malfy Originale» (gin, concepto pizza, secciones «Botellas» y «Gin»), «Pack ballentines» (pizza, «Pack Botellas»),
«Mai Tai» (sushi, «Cock Ta Ils»), «Enkai Fresh» (sushi). Las secciones «Gin», «Botellas» y «Cock Ta Ils» no son
palabras de tragos de las guardias.

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

`offers/guards.alcohol_in_description(descripción, concepto, sección)`: un plato **sin concepto o con uno de bebida**
(grupo `bebidas`: un concepto como gaseosas o café no dice si el trago lleva alcohol; un concepto que ya no está en la
taxonomía cuenta como sin concepto) cuya descripción nombra alcohol cuenta como +18 en una oferta; **sin concepto**,
también si su sección es de botellas, vinos o destilados («Botellas», «Tinto», «Blanco», «Gin», «Destilados»,
«Spritz», «Combinados», «Cock Ta Ils»; no «Té blanco» ni «Chocolate blanco»). Con concepto esas secciones no deciden:
ahí hay gaseosas («Botellas 1.5 Lts») y platos peruanos («Combinados»).

Las palabras de la descripción: las de los nombres de platos (`MENU_ALCOHOL_NAME_WORDS`) sin «vaina» ni «algarrobina»,
más tragos («trago», «chilcano», «alcohólica», «con alcohol», «tinto», «chop»), destilados, licores y sus marcas
(mezcal, fernet, jägermeister, kahlúa, triple sec, havana, alto del carmen, capel, aperol, smirnoff, gordon's…), algunos
plurales que el matcher no reduce («piñas coladas», «stellas artois»), el cóctel y el corto. Una descripción es larga:
antes de buscar se quitan las frases de comida («cóctel de camarones», «empanaditas cóctel», «sour cream», «pizza
margarita», «espresso corto», «chop suey», «café tinto»), así que solo se libra la palabra que queda dentro de una de
ellas, no las demás («Empanadas cóctel x12 + 2 cócteles») ni por una palabra de comida en otra parte («tabla de
empanadas + 2 cócteles»). «Sin alcohol» no la libra («Mojito con o sin alcohol»), y «alcohol» solo no cuenta: casi
siempre es «sin alcohol». Sin apóstrofes («Gordon's»).

La aplican los tres caminos que ofrecen platos: `agent/tools._with_prices` (búsquedas de oferta; la descripción solo
se lee con `offer`), `offers/engine._priced_in_vertical` (lo más pedido) y `offers/engine._find_popular_dishes` (los
populares de «vertical por probar»), sobre `clean_html(mi.description)`. Los nombres de platos suman «absolut»,
«absolute» («ABSOLUTE PEAR» tenía concepto sandwiches) y «ramazzoti» (mal escrito). La búsqueda y la pregunta no
cambian.

Demo sin conexión (`src/api/offline/offers.js`): la API no da descripciones, así que la muestra no las tiene; ahí
ningún plato sin concepto o con concepto de bebida se ofrece (más estricto que el backend: un café de un restaurante
tampoco), y los nombres de platos suman «absolut» y «absolute».

## Cero fugas

Guardias de `main` contra las de la rama, sobre todos los platos con precio: 182 pasan a bloqueados y ninguno se
libera. Los 182, revisados uno por uno:

| | platos | ejemplos |
|---|---|---|
| Fugas cerradas | 68 | los 44 de arriba; 6 vinos de «Tinto» y «Blanco» con el nombre abreviado o mal escrito («Cab.Sauvig CASAS PATRONALES», «Chardonay AROMO»); 4 cervezas de «Botellas» («Erdinger Dunkel», «Gulden Draak»); 9 tragos con concepto de bebida («Gautama Jack», un café irlandés, «Havanna Anejo Reserva Con Bebida», «Clery 300 ml»); «ABSOLUTE PEAR» (sandwiches); combos con cerveza («2 bebidas o 2 stellas artois», una copa con «Gran Torobayo») |
| Dudosos con alcohol | 2 | un americano «Espresso & amaretto», un helado de café con whisky |
| Comida | 83 | risottos al vino blanco, canelés al ron, cannoli al marsala, leche de tigre con pisco, un «Combinado especial» peruano |
| Sin alcohol | 29 | cafés con jarabe de amaretto, piñas coladas sin alcohol, espressos «cortos», jugos «en cada trago», cafés de la marca Havanna |

De los que se siguen pudiendo ofrecer sin concepto o con concepto de bebida, 1.780 tienen alguna señal amplia
(también «sin alcohol», «shot», «tónica», «drinks», «barra», «botella», «blanco», «combinado», «anís»): revisados
todos, ninguno es un trago (aguas, gaseosas, cafés «mocha blanco», quesos, chocolates blancos; el único dudoso,
«Botella De Guenazo 1lt», está entre jugos y aguas y no dice qué es). Un barrido aparte, con las palabras de los
nombres que solo usan los productos con alcohol del catálogo (471 marcas y formatos), dejó 151 ofrecibles, revisados
todos: ninguno es alcohol (las «Peroni» y «Mahou» que quedan dicen sin alcohol).

La revisión de código (dos vueltas de un subagente) encontró que una primera versión liberaba una descripción larga
por una palabra de comida en cualquier parte («tabla de empanadas + 2 cócteles», «2 rolls + 2 sour de maracuyá») o por
una frase de comida junto a otro trago («Empanadas cóctel x12 + 2 cócteles»), que la piña colada se libraba con «sin
alcohol», que faltaban palabras, plurales y marcas con apóstrofe, y que no miraba los populares de «vertical por probar»
ni limpiaba el HTML. No había casos así en la base; quedaron arreglados con tests. Los vinos y cervezas de «Tinto» y
«Botellas» los encontró el censo de la versión corregida. Las cifras son de la versión final.

## Pendiente (fuera de este cambio)

Con un concepto de comida (o de frescos, dulces, despensa o snacks), la descripción no cuenta, y ahí quedan tragos:
«Mega Tropical Summer», «Tropical Summer» y «Malfy Originale» (gin, concepto pizza, secciones «Botellas» y «Gin»),
«Pack ballentines» (pizza, «Pack Botellas»), «Mai Tai» (sushi, «Cock Ta Ils»), «Enkai Fresh» (sushi) y combos «2
bebidas o 2 cervezas» con concepto de comida. Son unos 1.100 platos ofrecibles cuya descripción nombra alcohol, casi
todos comida: necesita otra regla (por ejemplo, las secciones de botellas, gin o vinos también con concepto, salvo las
gaseosas, o un trago reconocido por el kNN sobre la descripción).

# Ofertas de Mochi más variadas y sin «No encontré» propio (fase 2 de 4)

**Objetivo:** que «qué me recomiendas» no termine en «No encontré» cuando la persona tiene otros gustos o el interés se
nombra de otra forma, que `carrito` y `proximo_pedido` no ofrezcan casi siempre gaseosas, y que la cocina de un local
no etiquete mal sus platos. Las guardias de ofertas siguen en 0.

## 1. «Qué me recomiendas» (`agent/rappi_agent.py`, rama `recomendar`)

**Causa (base `rappi`, solo lectura).** Mochi busca el nombre del interés más alto y responde con lo que salga. En 720
recomendaciones (90 intereses ofrecibles × 8 verticales) hay 25 «No encontré» (14 antes de #125):

- **Farmacia (8):** las tiendas de Farmacia no se ofrecen (`offers/guards.py`), así que ahí nada sale nunca.
- **«Manualidades y mercería» (8):** el nombre no trae los productos del concepto (en el Mall son «Supersoft - Gris Perla
  100 Gr», hilos y lanas), y desde #125 tampoco lo que solo dice «manualidades» (la tijera es de útiles).
- **Música (6), ropa en el súper, textiles del hogar en Express:** surtido mínimo o el nombre no calza.
- Además, el «No encontré» de una recomendación se anota como demanda («Lo anoté…»): Mochi anota su propia oferta.
- De paso: en Licores, la recomendación muestra productos de tiendas de Licores, que las guardias excluyen de toda
  oferta (`OFFER_BLOCKED_VERTICALS`).

**Regla.** Por cada interés ofrecible, de mayor a menor (hasta `RECOMMEND_INTERESTS` = 3): se busca por su nombre y, si
no hay nada, por su primera keyword (como se llaman sus productos: «lana», «ropa de cama»). Desde Farmacia, Licores o la Home la
búsqueda va a la vertical más típica de ese interés entre las que Mochi propone. El primero con productos responde
(«Por tu interés en…»); si ninguno, los ejemplos de ayuda, como sin perfil. Lo que no encontró no se muestra ni se anota.
Los intentos fallidos se redactan con plantillas: con Claude, solo se redacta el que responde.

## 2. Complementos (`agent/tools.suggest_complement`)

**Causa.** Las gaseosas son el primer complemento curado de pizza (0,6), hamburguesa (0,7), pollo frito (0,6) y
sándwiches (0,6): todos los que llevan comida preparada ven las mismas gaseosas. «No repetir lo que vio hace poco» ya
existe (`COMPLEMENT_REPEAT_DAYS`, 17-10), pero solo actúa entre pedidos de la misma persona.

**Regla.** Con `user_id`, entre los complementos curados (o aprendidos de datos reales) que pesan a `ROTATION_MARGIN`
(0,2) o menos del primero, cada persona ve uno fijo: el de la posición md5(persona + concepto de origen) módulo cuántos
son. Determinista y estable entre procesos. Sin `user_id`, el orden de siempre. No rota si el primero es una compra
cruzada de la persona. Después siguen igual «no repetir lo de hace poco», el desempate por la combinación y la marca.

**Medición.** `scripts/qa_motor.py --base rappi_staging --sin-modelo` antes y después (misma población): con oferta,
conceptos distintos, veces gaseosas, p95. Datos simulados: no es evidencia.

## 3. Conceptos mal asignados (`concepts/assign.py`, `category_map.csv`)

- «Ramen Muy Picante Buldak» → salsas ya se arregló el 17-10 (0c328567, `test_a_buldak_ramen_is_instant_ramen_not_a_sauce`);
  la base `rappi` ya lo tiene en snacks asiáticos.
- «Just Mila Xl» → pastelería sale de **la cocina del local** («Milas - El Golf»: Desayunos, Internacional, Pastelería y
  Postres), no de una regla del nombre. Muestra de la misma regla (base `rappi`): (a) entre varias cocinas confiables
  gana la primera por orden alfabético, no la más confiable: en los locales «Asiática, Sushi», 13.605 platos de sushi
  (rolls, piezas, handrolls) quedan como comida asiática; (b) «Pastelería y Postres» (0,85) etiqueta todo lo que no
  tiene otra pista en cafeterías, juguerías y heladerías: en dos muestras acertaba unos 4 de cada 10 (té, papas fritas,
  batidos, quesos, quiches).

**Regla.** (a) La cocina más confiable del local (a igual confianza, la primera por orden). (b) «Pastelería y Postres» →
pastelería baja de 0,85 a 0,6 (una pista dudosa, como «Americana» o «Carnes»): deja de etiquetar platos por sí sola;
la sección del menú o el kNN deciden.

## Pasos

1. Tests que fallan: recomendación que pasa al siguiente interés, a la keyword, a la vertical ofrecible desde Farmacia y
   Licores, a los ejemplos sin anotar demanda; complemento que rota por persona (estable, sin `user_id` igual, con
   «no repetir» encima); cocina más confiable y «Pastelería y Postres» que ya no etiqueta sola.
2. Los cambios, con sus docstrings.
3. Medición: `recommend.py` (720) y con los perfiles reales; `qa_motor.py` antes y después; conceptos en memoria
   (reglas + kNN) antes y después, con muestras juzgadas.
4. `make test` y `make lint` en rappi-ia; `make contract` si cambia un ejemplo; docs (`docs/decisiones.md`,
   `docs/diseno-ia.md`).
5. Revisión de código con un subagente; PR contra main con las tablas (rotuladas: datos simulados) y el comando para
   recalcular conceptos después de fusionar (`make concepts layers` en rappi-ia).

const graphemes = new Intl.Segmenter('es')

/**
 * Hasta dónde se ve un texto que se escribe letra por letra cuando van `count` unidades: el último grafema entero. Un
 * emoji como 🧡 son dos unidades de UTF-16 (y ❤️ o 👩‍🍳, más); partido, cada mitad se ve como un símbolo raro y más
 * ancho, y la línea puede saltar.
 */
export function typedEnd(text, count) {
  let end = 0
  for (const { index, segment } of graphemes.segment(text)) {
    const next = index + segment.length
    if (next > count) break
    end = next
  }
  return end
}

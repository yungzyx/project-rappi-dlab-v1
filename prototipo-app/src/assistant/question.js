// Si lo escrito en el buscador parece una pregunta para Mochi y no el nombre de un producto: entonces Enter le pregunta
// a Mochi (y su fila va resaltada); si no, Enter busca como siempre. Tocar «Pregúntale a Mochi» pregunta siempre.

const strip = (text) =>
  text
    .toLowerCase()
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/[^\w$\s]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()

// Cómo empieza una pregunta o un pedido abierto («algo dulce», «tengo hambre», «qué llevo para…»).
const LEADS =
  /^(?:que|cual|cuales|como|cuanto|cuanta|cuantos|cuantas|donde|con que|algo|alguna|tengo|me|se me|recomiendame|sugiereme|sorprendeme|ayudame|hola|dame algo|(?:quiero|necesito|busco|hay) algo)\b/
// Una cantidad de personas o un presupuesto («asado para 6», «somos 10», «con 8 mil»).
const PEOPLE = /\b(?:somos|personas?)\b|\bpara (?:\d{1,2}|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez)\b/
const BUDGET = /\$|\b(?:lucas|mil)\b/
const LONG = 5 // palabras: un nombre de producto rara vez es tan largo

export function looksLikeQuestion(text) {
  const raw = text.trim()
  if (!raw) return false
  if (raw.startsWith('¿') || raw.endsWith('?')) return true
  const plain = strip(raw)
  return LEADS.test(plain) || PEOPLE.test(plain) || BUDGET.test(plain) || plain.split(' ').length >= LONG
}

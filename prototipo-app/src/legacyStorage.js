// Claves del pasaporte y del juego, que ya no existen: un navegador que volvió las conserva para siempre.
const LEGACY_KEYS = ['rappi-proto-juego-v1', 'rappi-proto-pasaporte']

/** Borra del almacenamiento local las claves de funciones que se quitaron (sin almacenamiento, no hay nada que borrar). */
export function removeLegacyKeys(getStorage = () => localStorage) {
  let storage
  try {
    storage = getStorage()
  } catch {
    // Acceder a localStorage puede lanzar (SecurityError): sin almacenamiento, no hay nada que borrar.
    return
  }
  for (const key of LEGACY_KEYS) {
    try {
      storage.removeItem(key)
    } catch {
      // Almacenamiento bloqueado.
    }
  }
}

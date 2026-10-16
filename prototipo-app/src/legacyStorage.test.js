import { afterEach, describe, expect, test } from 'vitest'
import { removeLegacyKeys } from './legacyStorage.js'

afterEach(() => localStorage.clear())

describe('claves viejas del pasaporte y del juego', () => {
  test('se borran y el resto del almacenamiento queda', () => {
    localStorage.setItem('rappi-proto-juego-v1', '{}')
    localStorage.setItem('rappi-proto-pasaporte', '{}')
    localStorage.setItem('rappi-proto-user', 'proto-1')
    removeLegacyKeys()
    expect(localStorage.getItem('rappi-proto-juego-v1')).toBeNull()
    expect(localStorage.getItem('rappi-proto-pasaporte')).toBeNull()
    expect(localStorage.getItem('rappi-proto-user')).toBe('proto-1')
  })

  test('con el almacenamiento bloqueado no lanza', () => {
    const broken = { removeItem: () => { throw new Error('bloqueado') } }
    expect(() => removeLegacyKeys(() => broken)).not.toThrow()
  })

  test('no falla si acceder al almacenamiento lanza un error', () => {
    expect(() => removeLegacyKeys(() => { throw new Error('SecurityError') })).not.toThrow()
  })
})

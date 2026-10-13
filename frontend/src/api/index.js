// Punto unico de acceso a los datos. Las pantallas SIEMPRE importan desde aqui:
//   import { api } from '@/api'
// VITE_API_MODO=simulado -> datos de demostracion en el navegador
// VITE_API_MODO=real     -> backend (ver real.js: contrato de cada endpoint)
import { api as real, fijarToken } from './real'
import { api as simulado } from './simulado'

export const MODO = import.meta.env.VITE_API_MODO === 'real' ? 'real' : 'simulado'
export const api = MODO === 'real' ? real : simulado
export { fijarToken }
export { ErrorApi } from './errores'

// Error comun para ambos modos (simulado y real).
// mensaje: texto para el usuario; estado: codigo HTTP; campos: errores por campo { asunto: '...' }
export class ErrorApi extends Error {
  constructor(mensaje, estado = 400, campos = null) {
    super(mensaje)
    this.name = 'ErrorApi'
    this.estado = estado
    this.campos = campos
  }
}

// Oculta datos personales en el navegador antes de copiar un texto para una IA externa.
// Conserva los codigos de documentos (CGE/SCSL/GAAJ/C-166/2026).

const reglas = [
  { nombre: 'correo', patron: /[\w.+-]+@[\w-]+\.[\w.-]+/g, reemplazo: '[CORREO]' },
  { nombre: 'ci', patron: /\b(C\.?\s?I\.?|c[eé]dula(?: de identidad)?)\s*(N[°º.]?\s*)?:?\s*\d{5,10}(\s*-?\s*[A-Z0-9]{1,3})?(\s*(LP|CB|SC|OR|PT|CH|TJ|BE|PD))?\b/gi, reemplazo: '[CI]' },
  { nombre: 'nit', patron: /\bNIT\s*(N[°º.]?\s*)?:?\s*\d{7,15}\b/gi, reemplazo: '[NIT]' },
  { nombre: 'cuenta', patron: /\b(cuenta|cta\.?)\s*(bancaria|corriente|de ahorro)?\s*(N[°º.]?\s*)?:?\s*[\d-]{8,24}\b/gi, reemplazo: '[CUENTA]' },
  { nombre: 'telefono', patron: /\b(?:\+?591[\s-]?)?[67]\d{7}\b/g, reemplazo: '[TELÉFONO]' }
]

export function enmascarar(texto) {
  let resultado = String(texto ?? '')
  const conteo = {}
  for (const r of reglas) {
    resultado = resultado.replace(r.patron, () => {
      conteo[r.nombre] = (conteo[r.nombre] || 0) + 1
      return r.reemplazo
    })
  }
  return { texto: resultado, ocultos: Object.values(conteo).reduce((a, b) => a + b, 0) }
}

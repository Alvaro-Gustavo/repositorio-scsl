// Formatos de fecha y numero en espanol (Bolivia).

const fechaCorta = new Intl.DateTimeFormat('es-BO', { day: '2-digit', month: '2-digit', year: 'numeric', timeZone: 'America/La_Paz' })
const fechaHora = new Intl.DateTimeFormat('es-BO', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit', timeZone: 'America/La_Paz' })
const fechaLarga = new Intl.DateTimeFormat('es-BO', { day: 'numeric', month: 'long', year: 'numeric', timeZone: 'America/La_Paz' })
const numero = new Intl.NumberFormat('es-BO')

// Una fecha sin hora ("2026-08-17") se interpreta como dia local, no UTC.
function aFecha(valor) {
  if (!valor) return null
  if (typeof valor === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(valor)) return new Date(valor + 'T12:00:00-04:00')
  const d = new Date(valor)
  return Number.isNaN(d.getTime()) ? null : d
}

export const formatoFecha = (v) => (aFecha(v) ? fechaCorta.format(aFecha(v)) : '—')
export const formatoFechaHora = (v) => (aFecha(v) ? fechaHora.format(aFecha(v)) : '—')
export const formatoFechaLarga = (v) => (aFecha(v) ? fechaLarga.format(aFecha(v)) : '—')
export const formatoNumero = (v) => numero.format(v ?? 0)

export function hoyISO() {
  const d = new Date(Date.now() - 4 * 3600 * 1000)
  return d.toISOString().slice(0, 10)
}

export function diasDesde(valor) {
  const d = aFecha(valor)
  if (!d) return null
  return Math.floor((Date.now() - d.getTime()) / 86400000)
}

export function plural(n, uno, varios) {
  return `${formatoNumero(n)} ${n === 1 ? uno : varios}`
}

// Nombre de archivo seguro a partir de un codigo: CGE/SCSL/C-157/2026 -> CGE-SCSL-C-157-2026.pdf
export function nombreArchivo(codigo, extension = 'pdf') {
  const base = String(codigo || 'documento').normalize('NFD').replace(/[̀-ͯ]/g, '')
    .replace(/[^A-Za-z0-9_-]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 120)
  return `${base || 'documento'}.${extension}`
}

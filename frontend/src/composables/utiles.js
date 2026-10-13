// Ayudas comunes para las pantallas.
import { ref } from 'vue'
import { api } from '@/api'
import { useAvisos } from '@/stores/avisos'
import { nombreArchivo } from '@/utils/formato'

// Carga de datos con estado de espera y error:
//   const { datos, cargando, error, cargar } = useCarga(() => api.tramites.obtener(id))
export function useCarga(fn, { inmediato = true, inicial = null } = {}) {
  const datos = ref(inicial)
  const cargando = ref(false)
  const error = ref('')
  async function cargar(...args) {
    cargando.value = true
    error.value = ''
    try {
      datos.value = await fn(...args)
    } catch (e) {
      error.value = e.message || 'No se pudo cargar la información.'
    } finally {
      cargando.value = false
    }
    return datos.value
  }
  if (inmediato) cargar()
  return { datos, cargando, error, cargar }
}

// Envio de formularios: guarda errores por campo y muestra el mensaje general.
//   const { errores, enviando, enviar } = useEnvio()
//   await enviar(() => api.tramites.crear(form), 'Trámite registrado')
export function useEnvio() {
  const errores = ref({})
  const enviando = ref(false)
  const avisos = useAvisos()
  async function enviar(fn, mensajeExito) {
    enviando.value = true
    errores.value = {}
    try {
      const r = await fn()
      if (mensajeExito) avisos.exito(mensajeExito)
      return r
    } catch (e) {
      if (e.campos) errores.value = e.campos
      avisos.error(e.message || 'No se pudo completar la operación.')
      throw e
    } finally {
      enviando.value = false
    }
  }
  return { errores, enviando, enviar }
}

// Descarga el PDF original de un tramite (solo ADMIN y JEFE; el backend lo verifica).
export async function descargarInforme(tramite) {
  const avisos = useAvisos()
  try {
    const blob = await api.tramites.descargarInforme(tramite.id)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = nombreArchivo(tramite.numero_documento || tramite.hoja_ruta)
    document.body.appendChild(a)
    a.click()
    a.remove()
    setTimeout(() => URL.revokeObjectURL(url), 2000)
    avisos.exito('Descarga iniciada.')
  } catch (e) {
    avisos.error(e.estado === 403 ? 'No tiene permisos para descargar este documento.' : e.message)
  }
}

// Imprime la pagina actual y deja constancia en la auditoria.
export async function imprimirConAuditoria(detalle, modulo = 'CONSULTA') {
  try { await api.auditoria.registrar({ accion: 'IMPRIMIR_CONSULTA', modulo, detalle }) } catch { /* imprimir igual */ }
  window.print()
}

// Copia texto al portapapeles (requiere HTTPS o localhost).
export async function copiarTexto(texto) {
  try {
    await navigator.clipboard.writeText(texto)
    return true
  } catch {
    const area = document.createElement('textarea')
    area.value = texto
    area.setAttribute('readonly', '')
    area.style.position = 'fixed'
    area.style.opacity = '0'
    document.body.appendChild(area)
    area.select()
    const ok = document.execCommand('copy')
    area.remove()
    return ok
  }
}

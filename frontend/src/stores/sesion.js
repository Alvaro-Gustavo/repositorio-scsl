// Estado de la sesion: usuario, rol y permisos. Las pantallas preguntan
// sesion.puede('DESCARGAR_INFORME') para mostrar u ocultar acciones.
// La decision final SIEMPRE la toma el backend: ocultar un boton no es seguridad.
import { defineStore } from 'pinia'
import { api, fijarToken } from '@/api'

const CLAVE_TOKEN = 'scsl_token'

export const useSesion = defineStore('sesion', {
  state: () => ({ usuario: null, cargada: false }),
  getters: {
    autenticado: (s) => !!s.usuario,
    rol: (s) => s.usuario?.rol ?? null,
    permisos: (s) => new Set(s.usuario?.permisos ?? [])
  },
  actions: {
    puede(...permisos) {
      return permisos.some((p) => this.permisos.has(p))
    },
    async restaurar() {
      if (this.cargada) return
      try {
        const token = sessionStorage.getItem(CLAVE_TOKEN)
        if (token) {
          fijarToken(token)
          this.usuario = await api.auth.sesion()
        }
      } catch {
        this.limpiar()
      } finally {
        this.cargada = true
      }
    },
    async ingresar(credenciales) {
      const { token, usuario } = await api.auth.ingresar(credenciales)
      fijarToken(token)
      try { sessionStorage.setItem(CLAVE_TOKEN, token) } catch { /* sin almacen */ }
      this.usuario = usuario
      this.cargada = true
      return usuario
    },
    async salir() {
      try { await api.auth.salir() } catch { /* la sesion igual se cierra en el navegador */ }
      this.limpiar()
    },
    limpiar() {
      this.usuario = null
      fijarToken(null)
      try { sessionStorage.removeItem(CLAVE_TOKEN) } catch { /* sin almacen */ }
    },
    actualizarUsuario(datos) {
      this.usuario = { ...this.usuario, ...datos }
    }
  }
})

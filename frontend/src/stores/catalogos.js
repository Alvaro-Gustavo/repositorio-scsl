// Cache de catalogos para los formularios y filtros (se piden una vez por sesion).
import { defineStore } from 'pinia'
import { api } from '@/api'

export const useCatalogos = defineStore('catalogos', {
  state: () => ({ datos: {}, cargando: {} }),
  actions: {
    async obtener(tipo, { forzar = false } = {}) {
      if (!forzar && this.datos[tipo]) return this.datos[tipo]
      if (this.cargando[tipo]) return this.cargando[tipo]
      this.cargando[tipo] = api.catalogos.listar(tipo).then((lista) => {
        this.datos[tipo] = lista
        return lista
      }).finally(() => { delete this.cargando[tipo] })
      return this.cargando[tipo]
    },
    async varios(tipos) {
      await Promise.all(tipos.map((t) => this.obtener(t)))
    },
    agregar(tipo, valor) {
      if (this.datos[tipo]) this.datos[tipo] = [...this.datos[tipo], valor].sort((a, b) => a.nombre.localeCompare(b.nombre, 'es'))
    },
    invalidar(tipo) {
      delete this.datos[tipo]
    }
  }
})

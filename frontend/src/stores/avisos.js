// Mensajes breves en pantalla (exito, error, aviso). Uso:
//   const avisos = useAvisos(); avisos.exito('Trámite registrado')
import { defineStore } from 'pinia'

let siguiente = 1

export const useAvisos = defineStore('avisos', {
  state: () => ({ lista: [] }),
  actions: {
    mostrar(tipo, texto, ms = 4500) {
      const id = siguiente++
      this.lista.push({ id, tipo, texto })
      if (ms) setTimeout(() => this.cerrar(id), ms)
    },
    exito(texto) { this.mostrar('exito', texto) },
    error(texto) { this.mostrar('peligro', texto, 7000) },
    aviso(texto) { this.mostrar('aviso', texto) },
    info(texto) { this.mostrar('info', texto) },
    cerrar(id) { this.lista = this.lista.filter((a) => a.id !== id) }
  }
})

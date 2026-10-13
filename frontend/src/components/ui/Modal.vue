<script setup>
// Ventana modal accesible.
// <Modal v-model="abierto" titulo="Asignar abogado" ancho="560px"> ...contenido... <template #pie>botones</template></Modal>
import { watch, ref, nextTick, onBeforeUnmount } from 'vue'
import { X } from '@lucide/vue'

const props = defineProps({ modelValue: Boolean, titulo: { type: String, required: true }, ancho: { type: String, default: '560px' } })
const emit = defineEmits(['update:modelValue'])
const caja = ref(null)
let foco = null

function cerrar() { emit('update:modelValue', false) }
function teclado(e) {
  if (e.key === 'Escape') cerrar()
  if (e.key === 'Tab' && caja.value) {
    const f = caja.value.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])')
    if (!f.length) return
    const primero = f[0]; const ultimo = f[f.length - 1]
    if (e.shiftKey && document.activeElement === primero) { ultimo.focus(); e.preventDefault() }
    else if (!e.shiftKey && document.activeElement === ultimo) { primero.focus(); e.preventDefault() }
  }
}
watch(() => props.modelValue, async (v) => {
  if (v) {
    foco = document.activeElement
    document.body.style.overflow = 'hidden'
    await nextTick()
    const primero = caja.value?.querySelector('input, select, textarea, button:not(.modal-cerrar)')
    ;(primero || caja.value)?.focus()
  } else {
    document.body.style.overflow = ''
    foco?.focus?.()
  }
}, { immediate: true })
onBeforeUnmount(() => { document.body.style.overflow = '' })
</script>

<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="modelValue" class="modal-fondo" @mousedown.self="cerrar" @keydown="teclado">
        <div ref="caja" class="modal" role="dialog" aria-modal="true" :aria-label="titulo" tabindex="-1" :style="{ maxWidth: ancho }">
          <header class="modal-cabecera">
            <h2>{{ titulo }}</h2>
            <button type="button" class="boton boton-icono boton-fantasma modal-cerrar" aria-label="Cerrar" @click="cerrar"><X /></button>
          </header>
          <div class="modal-cuerpo"><slot /></div>
          <footer v-if="$slots.pie" class="modal-pie"><slot name="pie" /></footer>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.modal-fondo { position: fixed; inset: 0; z-index: 60; background: rgba(19, 41, 75, .5); display: grid; place-items: center; padding: 16px; overflow-y: auto; }
.modal { width: 100%; background: var(--superficie); border-radius: var(--radio-panel); box-shadow: var(--sombra-flotante); outline: none; max-height: calc(100vh - 32px); display: flex; flex-direction: column; }
.modal-cabecera { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 16px 20px; border-bottom: 1px solid var(--linea); }
.modal-cabecera h2 { font-size: var(--t-lg); }
.modal-cuerpo { padding: 20px; overflow-y: auto; }
.modal-pie { display: flex; justify-content: flex-end; gap: 8px; padding: 14px 20px; border-top: 1px solid var(--linea); background: var(--superficie-2); border-radius: 0 0 var(--radio-panel) var(--radio-panel); flex-wrap: wrap; }
.modal-enter-active, .modal-leave-active { transition: opacity .15s; }
.modal-enter-from, .modal-leave-to { opacity: 0; }
</style>

<script setup>
import { CircleCheck, CircleX, AlertTriangle, Info, X } from '@lucide/vue'
import { useAvisos } from '@/stores/avisos'

const avisos = useAvisos()
const iconos = { exito: CircleCheck, peligro: CircleX, aviso: AlertTriangle, info: Info }
</script>

<template>
  <div class="avisos" aria-live="polite" aria-atomic="false">
    <TransitionGroup name="aviso">
      <div v-for="a in avisos.lista" :key="a.id" class="aviso mensaje" :class="`mensaje-${a.tipo}`" :role="a.tipo === 'peligro' ? 'alert' : 'status'">
        <component :is="iconos[a.tipo]" aria-hidden="true" />
        <span>{{ a.texto }}</span>
        <button type="button" class="cerrar" aria-label="Cerrar mensaje" @click="avisos.cerrar(a.id)"><X /></button>
      </div>
    </TransitionGroup>
  </div>
</template>

<style scoped>
.avisos { position: fixed; right: 20px; bottom: 20px; z-index: 100; display: flex; flex-direction: column; gap: 8px; width: min(420px, calc(100vw - 32px)); }
.aviso { box-shadow: var(--sombra-flotante); background-clip: padding-box; align-items: center; }
.aviso span { flex: 1; color: var(--texto); }
.cerrar { border: none; background: none; cursor: pointer; color: var(--texto-2); padding: 2px; display: inline-flex; }
.cerrar svg { width: 16px; height: 16px; margin: 0; }
.aviso-enter-active, .aviso-leave-active { transition: opacity .18s, transform .18s; }
.aviso-enter-from, .aviso-leave-to { opacity: 0; transform: translateY(8px); }
</style>

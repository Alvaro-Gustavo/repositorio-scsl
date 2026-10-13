<script setup>
// Pantalla vacia que invita a actuar.
// <EstadoVacio :icono="Inbox" titulo="No hay trámites por asignar" texto="..."><RouterLink ...>Registrar</RouterLink></EstadoVacio>
import { Inbox } from '@lucide/vue'
defineProps({ icono: { type: [Object, Function], default: () => Inbox }, titulo: { type: String, required: true }, texto: { type: String, default: '' } })
</script>

<template>
  <div class="vacio">
    <component :is="icono" aria-hidden="true" class="vacio-icono" />
    <h3>{{ titulo }}</h3>
    <p v-if="texto">{{ texto }}</p>
    <div v-if="$slots.default" class="vacio-acciones"><slot /></div>
  </div>
</template>

<style scoped>
.vacio { text-align: center; padding: var(--e-10) var(--e-6); color: var(--texto-2); }
.vacio-icono { width: 40px; height: 40px; margin: 0 auto var(--e-3); color: var(--linea-fuerte); }
.vacio h3 { font-size: var(--t-md); color: var(--texto); margin-bottom: 4px; }
.vacio p { max-width: 52ch; margin: 0 auto; font-size: var(--t-sm); }
.vacio-acciones { margin-top: var(--e-4); display: flex; justify-content: center; gap: 8px; flex-wrap: wrap; }
</style>

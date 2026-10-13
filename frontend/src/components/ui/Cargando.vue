<script setup>
import { Loader2 } from '@lucide/vue'
defineProps({ texto: { type: String, default: 'Cargando información…' } })
</script>

<template>
  <div class="cargando" role="status"><Loader2 class="girar" aria-hidden="true" /> {{ texto }}</div>
</template>

<style scoped>
.cargando svg { width: 20px; height: 20px; }
</style>

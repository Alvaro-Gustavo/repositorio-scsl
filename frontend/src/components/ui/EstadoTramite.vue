<script setup>
// Insignia con el estado del tramite: <EstadoTramite estado="EN_ELABORACION" />
import { computed } from 'vue'
import { ESTADOS_TRAMITE } from '@/utils/constantes'

const props = defineProps({ estado: { type: String, required: true }, vencido: Boolean })
const info = computed(() => ESTADOS_TRAMITE[props.estado] || { etiqueta: props.estado, clase: 'recibido' })
</script>

<template>
  <span class="insignia" :class="`estado-${info.clase}`" :title="info.descripcion">{{ info.etiqueta }}</span>
  <span v-if="vencido" class="insignia insignia-peligro">Vencido</span>
</template>

<style scoped>
.estado-recibido { background: var(--recibido-suave); color: var(--recibido); }
.estado-elaboracion { background: var(--elaboracion-suave); color: var(--elaboracion); }
.estado-concluido { background: var(--concluido-suave); color: var(--concluido); }
.estado-archivado { background: var(--archivado-suave); color: var(--archivado); }
.insignia + .insignia { margin-left: 6px; }
</style>

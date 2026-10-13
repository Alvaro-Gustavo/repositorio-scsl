<script setup>
// Encabezado institucional que solo aparece al imprimir (ver styles/print.css).
// <EncabezadoImpresion titulo="Reporte de consulta" :criterio="'Búsqueda: ampliación de plazo'" :resultados="12" />
import { useSesion } from '@/stores/sesion'
import { formatoFechaHora } from '@/utils/formato'

defineProps({ titulo: { type: String, required: true }, criterio: { type: String, default: '' }, resultados: { type: Number, default: null } })
const sesion = useSesion()
const ahora = new Date().toISOString()
</script>

<template>
  <div class="solo-impresion impresion-encabezado">
    <div class="fila" style="gap: 12px">
      <img src="/escudo.svg" alt="" width="40" height="40" />
      <div>
        <h1>Repositorio SCSL · {{ titulo }}</h1>
        <p>Contraloría General del Estado · Subcontraloría de Servicios Legales · Repositorio local cerrado</p>
      </div>
    </div>
    <p>Generado por {{ sesion.usuario?.nombre_completo }} ({{ sesion.usuario?.correo }}) el {{ formatoFechaHora(ahora) }}</p>
    <p v-if="criterio">Criterio: {{ criterio }}<template v-if="resultados !== null"> · Resultados: {{ resultados }}</template></p>
  </div>
</template>

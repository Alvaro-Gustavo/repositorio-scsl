<script setup>
// Barras horizontales apiladas por estado (o una sola serie).
// <GraficoBarras :filas="[{ nombre: 'DRA. ZENTENO', valores: { concluidos: 12, en_elaboracion: 3 } }]"
//                :series="[{ clave: 'concluidos', etiqueta: 'Concluidos', color: 'var(--concluido)' }, ...]" />
import { computed } from 'vue'
import { formatoNumero } from '@/utils/formato'

const props = defineProps({
  filas: { type: Array, required: true },
  series: { type: Array, required: true },
  vacio: { type: String, default: 'Sin datos para mostrar.' }
})
const maximo = computed(() => Math.max(1, ...props.filas.map((f) => props.series.reduce((s, x) => s + (f.valores[x.clave] || 0), 0))))
const total = (f) => props.series.reduce((s, x) => s + (f.valores[x.clave] || 0), 0)
</script>

<template>
  <div class="grafico">
    <ul v-if="series.length > 1" class="leyenda" aria-hidden="true">
      <li v-for="s in series" :key="s.clave"><span class="muestra" :style="{ background: s.color }" />{{ s.etiqueta }}</li>
    </ul>
    <p v-if="!filas.length" class="texto-3 texto-pequeno">{{ vacio }}</p>
    <table v-else class="sr-only">
      <thead><tr><th>Nombre</th><th v-for="s in series" :key="s.clave">{{ s.etiqueta }}</th></tr></thead>
      <tbody><tr v-for="f in filas" :key="f.nombre"><td>{{ f.nombre }}</td><td v-for="s in series" :key="s.clave">{{ f.valores[s.clave] || 0 }}</td></tr></tbody>
    </table>
    <div v-for="f in filas" :key="f.nombre" class="fila-barra" aria-hidden="true">
      <span class="nombre" :title="f.nombre">{{ f.nombre }}</span>
      <span class="pista">
        <span v-for="s in series" :key="s.clave" class="tramo" :title="`${s.etiqueta}: ${f.valores[s.clave] || 0}`"
          :style="{ width: `${(100 * (f.valores[s.clave] || 0)) / maximo}%`, background: s.color }" />
      </span>
      <span class="valor">{{ formatoNumero(total(f)) }}</span>
    </div>
  </div>
</template>

<style scoped>
.leyenda { display: flex; flex-wrap: wrap; gap: 6px 16px; list-style: none; margin: 0 0 12px; padding: 0; font-size: var(--t-xs); color: var(--texto-2); }
.leyenda li { display: inline-flex; align-items: center; gap: 6px; }
.muestra { width: 10px; height: 10px; border-radius: 2px; }
.fila-barra { display: grid; grid-template-columns: minmax(110px, 34%) 1fr 40px; align-items: center; gap: 10px; padding: 5px 0; font-size: var(--t-sm); }
.nombre { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--texto-2); }
.pista { display: flex; height: 14px; background: var(--superficie-2); border-radius: 3px; overflow: hidden; }
.tramo { height: 100%; }
.tramo + .tramo { border-left: 1px solid var(--superficie); }
.valor { text-align: right; font-weight: 650; font-variant-numeric: tabular-nums; }
</style>

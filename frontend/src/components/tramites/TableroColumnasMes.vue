<script setup>
// Columnas agrupadas por mes (SVG propio, se dibuja al ancho real del contenedor
// para que los textos no se encojan en pantallas angostas).
// <TableroColumnasMes :meses="[{ mes: '2026-10', registrados: 4, concluidos: 3 }]"
//   :series="[{ clave: 'registrados', etiqueta: 'Registrados', color: 'var(--recibido)' }, ...]" />
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { formatoNumero } from '@/utils/formato'

const props = defineProps({
  meses: { type: Array, required: true },
  series: { type: Array, required: true },
  alto: { type: Number, default: 240 },
  titulo: { type: String, default: 'Trámites por mes' }
})

const MESES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']
const MESES_LARGOS = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
const partes = (m) => { const [a, n] = String(m).split('-'); return { anio: a, indice: Number(n) - 1 } }
const corto = (m) => MESES[partes(m).indice] || m
const largo = (m) => { const p = partes(m); return `${MESES_LARGOS[p.indice] || m} ${p.anio}` }

const contenedor = ref(null)
const ancho = ref(640)
let observador = null
onMounted(() => {
  if (!contenedor.value) return
  ancho.value = contenedor.value.clientWidth || 640
  if ('ResizeObserver' in window) {
    observador = new ResizeObserver(([e]) => { ancho.value = Math.max(280, Math.round(e.contentRect.width)) })
    observador.observe(contenedor.value)
  }
})
onBeforeUnmount(() => observador?.disconnect())

const margen = { arriba: 12, derecha: 8, abajo: 40, izquierda: 34 }
const areaAncho = computed(() => ancho.value - margen.izquierda - margen.derecha)
const areaAlto = computed(() => props.alto - margen.arriba - margen.abajo)

// Escala "redonda" para el eje vertical.
const escala = computed(() => {
  const max = Math.max(0, ...props.meses.flatMap((m) => props.series.map((s) => m[s.clave] || 0)))
  if (max <= 4) return { tope: Math.max(4, max), paso: 1 }
  const bruto = max / 4
  const mag = 10 ** Math.floor(Math.log10(bruto))
  const paso = [1, 2, 2.5, 5, 10].map((f) => f * mag).find((p) => p >= bruto && Number.isInteger(p)) || Math.ceil(bruto)
  return { tope: Math.ceil(max / paso) * paso, paso }
})
const marcas = computed(() => {
  const r = []
  for (let v = 0; v <= escala.value.tope; v += escala.value.paso) r.push(v)
  return r
})
const y = (v) => margen.arriba + areaAlto.value - (v / escala.value.tope) * areaAlto.value

const banda = computed(() => areaAncho.value / Math.max(1, props.meses.length))
const columna = computed(() => Math.max(3, Math.min(22, (banda.value * 0.72) / Math.max(1, props.series.length))))
// En pantallas angostas se rotula un mes de cada dos.
const saltoEtiqueta = computed(() => (banda.value < 34 ? 2 : 1))

const grupos = computed(() => props.meses.map((m, i) => {
  const centro = margen.izquierda + banda.value * i + banda.value / 2
  const anchoGrupo = columna.value * props.series.length + 2 * (props.series.length - 1)
  const inicio = centro - anchoGrupo / 2
  return {
    mes: m.mes, centro, rotular: (props.meses.length - 1 - i) % saltoEtiqueta.value === 0,
    nuevoAnio: i === 0 || partes(m.mes).indice === 0,
    barras: props.series.map((s, j) => {
      const v = m[s.clave] || 0
      return { clave: s.clave, color: s.color, valor: v, etiqueta: s.etiqueta, x: inicio + j * (columna.value + 2), y: y(v), alto: Math.max(0, y(0) - y(v)) }
    })
  }
}))
</script>

<template>
  <figure class="columnas">
    <ul class="leyenda" aria-hidden="true">
      <li v-for="s in series" :key="s.clave"><span class="muestra" :style="{ background: s.color }" />{{ s.etiqueta }}</li>
    </ul>
    <div ref="contenedor" class="lienzo">
      <svg :width="ancho" :height="alto" :viewBox="`0 0 ${ancho} ${alto}`" aria-hidden="true" focusable="false">
        <g class="eje-y">
          <g v-for="v in marcas" :key="v">
            <line :x1="margen.izquierda" :x2="ancho - margen.derecha" :y1="y(v)" :y2="y(v)" :class="{ base: v === 0 }" />
            <text :x="margen.izquierda - 6" :y="y(v)" dy="0.32em" text-anchor="end">{{ formatoNumero(v) }}</text>
          </g>
        </g>
        <g v-for="g in grupos" :key="g.mes">
          <rect v-for="b in g.barras" :key="b.clave" :x="b.x" :y="b.y" :width="columna" :height="b.alto" :style="{ fill: b.color }" rx="1.5">
            <title>{{ largo(g.mes) }} · {{ b.etiqueta }}: {{ b.valor }}</title>
          </rect>
          <text v-if="g.rotular" class="mes" :x="g.centro" :y="alto - margen.abajo + 16" text-anchor="middle">{{ corto(g.mes) }}</text>
          <text v-if="g.nuevoAnio" class="anio" :x="g.centro" :y="alto - margen.abajo + 31" text-anchor="middle">{{ g.mes.slice(0, 4) }}</text>
        </g>
      </svg>
    </div>
    <table class="sr-only">
      <caption>{{ titulo }}</caption>
      <thead><tr><th scope="col">Mes</th><th v-for="s in series" :key="s.clave" scope="col">{{ s.etiqueta }}</th></tr></thead>
      <tbody>
        <tr v-for="m in meses" :key="m.mes"><th scope="row">{{ largo(m.mes) }}</th><td v-for="s in series" :key="s.clave">{{ m[s.clave] || 0 }}</td></tr>
      </tbody>
    </table>
  </figure>
</template>

<style scoped>
.columnas { margin: 0; }
.leyenda { display: flex; flex-wrap: wrap; gap: 6px 16px; list-style: none; margin: 0 0 12px; padding: 0; font-size: var(--t-xs); color: var(--texto-2); }
.leyenda li { display: inline-flex; align-items: center; gap: 6px; }
.muestra { width: 10px; height: 10px; border-radius: 2px; }
.lienzo { width: 100%; overflow: hidden; }
svg { max-width: 100%; }
.eje-y line { stroke: var(--linea); stroke-width: 1; shape-rendering: crispEdges; }
.eje-y line.base { stroke: var(--linea-fuerte); }
text { font-family: var(--fuente-texto); font-size: 11px; fill: var(--texto-3); font-variant-numeric: tabular-nums; }
text.mes { font-size: 12px; fill: var(--texto-2); }
text.anio { font-weight: 650; fill: var(--texto-2); }
@media print { rect { print-color-adjust: exact; -webkit-print-color-adjust: exact; } }
</style>

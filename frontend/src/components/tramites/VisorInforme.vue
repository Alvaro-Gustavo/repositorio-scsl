<script setup>
// Visor protegido del informe: muestra cada pagina como imagen con marca de agua
// (el PDF original nunca llega al navegador de quien no puede descargarlo).
// Busca dentro del informe: resalta cada coincidencia sobre la pagina y salta entre ellas.
// <VisorInforme v-model="abierto" :tramite="t" buscar="palabra" :pagina-inicial="3" />
import { ref, watch, computed, nextTick } from 'vue'
import { ChevronLeft, ChevronRight, ChevronUp, ChevronDown, ZoomIn, ZoomOut, Download, ShieldCheck, Search, X } from '@lucide/vue'
import Modal from '@/components/ui/Modal.vue'
import Cargando from '@/components/ui/Cargando.vue'
import { api } from '@/api'
import { descargarInforme } from '@/composables/utiles'
import { plural } from '@/utils/formato'

const props = defineProps({
  modelValue: Boolean,
  tramite: { type: Object, required: true },
  buscar: { type: String, default: '' },        // lo buscado en la busqueda universal
  paginaInicial: { type: Number, default: 1 }
})
const emit = defineEmits(['update:modelValue'])
const abierto = computed({ get: () => props.modelValue, set: (v) => emit('update:modelValue', v) })

const paginas = ref([])
const pagina = ref(1)
const zoom = ref(1)
const cargando = ref(false)
const error = ref('')

// ---------- Busqueda dentro del informe ----------
const texto = ref('')            // lo que se escribe en el buscador del visor
const buscado = ref('')          // lo que se busco por ultima vez
const marcasPorPagina = ref([])  // [[x0, y0, x1, y1] en fracciones] por pagina
const actual = ref(0)            // indice en la lista plana de coincidencias
const buscando = ref(false)
const errorBusqueda = ref('')
const hoja = ref(null)

const lista = computed(() => marcasPorPagina.value.flatMap((marcas, i) => marcas.map((r) => ({ pagina: i + 1, r }))))
const paginasConCoincidencias = computed(() => marcasPorPagina.value
  .map((marcas, i) => ({ pagina: i + 1, cantidad: marcas.length })).filter((p) => p.cantidad))
const marcasVisibles = computed(() => (marcasPorPagina.value[pagina.value - 1] || []).map((r) => {
  const indice = lista.value.findIndex((c) => c.r === r)
  return { r, indice, esActual: indice === actual.value }
}))

function estilo([x0, y0, x1, y1]) {
  return { left: `${x0 * 100}%`, top: `${y0 * 100}%`, width: `${(x1 - x0) * 100}%`, height: `${(y1 - y0) * 100}%` }
}

async function mostrarActual() {
  const c = lista.value[actual.value]
  if (!c) return
  pagina.value = c.pagina
  await nextTick()
  hoja.value?.querySelector('.marca-actual')?.scrollIntoView({ block: 'center', inline: 'center', behavior: 'smooth' })
}
function ir(paso) {
  if (!lista.value.length) return
  actual.value = (actual.value + paso + lista.value.length) % lista.value.length
  mostrarActual()
}
function irAPagina(n) {
  const i = lista.value.findIndex((c) => c.pagina === n)
  if (i >= 0) { actual.value = i; mostrarActual() } else pagina.value = n
}

async function buscarEnInforme(q, desdePagina = 1) {
  q = q.trim()
  errorBusqueda.value = ''
  if (!q) { limpiarBusqueda(); return }
  if (q === buscado.value && lista.value.length) { ir(1); return }  // Enter otra vez: siguiente
  buscando.value = true
  try {
    const r = await api.tramites.coincidenciasInforme(props.tramite.id, q)
    buscado.value = q
    marcasPorPagina.value = r.paginas || []
    const i = lista.value.findIndex((c) => c.pagina >= desdePagina)
    actual.value = Math.max(0, i)
    if (lista.value.length) await mostrarActual()
  } catch (e) {
    errorBusqueda.value = e.message || 'No se pudo buscar en el informe.'
  } finally {
    buscando.value = false
  }
}
function limpiarBusqueda() {
  texto.value = ''; buscado.value = ''; marcasPorPagina.value = []; actual.value = 0; errorBusqueda.value = ''
}
function teclaBuscador(e) {
  if (e.key === 'Enter' && e.shiftKey) { e.preventDefault(); ir(-1) }
}

watch(abierto, async (v) => {
  if (!v) return
  pagina.value = 1; zoom.value = 1; error.value = ''; cargando.value = true
  limpiarBusqueda()
  try {
    const r = await api.tramites.paginasInforme(props.tramite.id)
    paginas.value = r.paginas?.length ? r.paginas
      : Array.from({ length: r.paginas || props.tramite.informe?.paginas || 1 }, (_, i) => api.tramites.urlPaginaInforme(props.tramite.id, i + 1))
  } catch (e) {
    error.value = e.message
    return
  } finally {
    cargando.value = false
  }
  pagina.value = Math.min(Math.max(1, props.paginaInicial), paginas.value.length || 1)
  if (props.buscar) {
    texto.value = props.buscar
    await buscarEnInforme(props.buscar, pagina.value)
  }
}, { immediate: true })  // immediate: desde un enlace de la búsqueda el visor nace ya abierto
</script>

<template>
  <Modal v-model="abierto" :titulo="`Informe ${tramite.numero_documento || tramite.hoja_ruta}`" ancho="1040px">
    <div class="barra-visor no-imprimir">
      <form class="buscar-informe" role="search" @submit.prevent="buscarEnInforme(texto)">
        <label for="buscar-en-informe" class="sr-only">Buscar dentro del informe</label>
        <Search class="buscar-icono" aria-hidden="true" />
        <input id="buscar-en-informe" v-model="texto" type="search" class="entrada" autocomplete="off"
          placeholder="Buscar en este informe…" :disabled="cargando || !!error" @keydown="teclaBuscador" />
        <span v-if="buscado && !buscando" class="contador texto-pequeno" aria-live="polite">
          <template v-if="lista.length">{{ actual + 1 }} de {{ lista.length }}</template>
          <template v-else>Sin coincidencias</template>
        </span>
        <span v-else-if="buscando" class="contador texto-pequeno texto-3">Buscando…</span>
        <button type="button" class="boton boton-pequeno" aria-label="Coincidencia anterior" title="Anterior (Mayús + Enter)" :disabled="!lista.length" @click="ir(-1)"><ChevronUp /></button>
        <button type="button" class="boton boton-pequeno" aria-label="Coincidencia siguiente" title="Siguiente (Enter)" :disabled="!lista.length" @click="ir(1)"><ChevronDown /></button>
        <button v-if="buscado" type="button" class="boton boton-pequeno boton-fantasma" aria-label="Quitar la búsqueda" @click="limpiarBusqueda"><X /></button>
      </form>
      <span class="fila">
        <button type="button" class="boton boton-pequeno" aria-label="Alejar" :disabled="zoom <= 0.6" @click="zoom = Math.round((zoom - 0.2) * 10) / 10"><ZoomOut /></button>
        <span class="texto-pequeno">{{ Math.round(zoom * 100) }} %</span>
        <button type="button" class="boton boton-pequeno" aria-label="Acercar" :disabled="zoom >= 2" @click="zoom = Math.round((zoom + 0.2) * 10) / 10"><ZoomIn /></button>
        <span class="separador-v" />
        <button type="button" class="boton boton-pequeno" aria-label="Página anterior" :disabled="pagina <= 1" @click="pagina--"><ChevronLeft /></button>
        <span class="texto-pequeno">Página {{ pagina }} de {{ paginas.length || '…' }}</span>
        <button type="button" class="boton boton-pequeno" aria-label="Página siguiente" :disabled="pagina >= paginas.length" @click="pagina++"><ChevronRight /></button>
      </span>
    </div>
    <p v-if="errorBusqueda" class="mensaje mensaje-peligro texto-pequeno">{{ errorBusqueda }}</p>
    <div v-if="paginasConCoincidencias.length" class="paginas-con no-imprimir">
      <span class="texto-xs texto-3">«{{ buscado }}» aparece en:</span>
      <button v-for="p in paginasConCoincidencias" :key="p.pagina" type="button" class="chip" :class="{ activa: p.pagina === pagina }"
        :aria-label="`Página ${p.pagina}, ${plural(p.cantidad, 'coincidencia', 'coincidencias')}`" @click="irAPagina(p.pagina)">
        Pág. {{ p.pagina }} <span class="chip-cantidad">{{ p.cantidad }}</span>
      </button>
    </div>
    <p v-else-if="buscado && !buscando && !errorBusqueda" class="texto-pequeno texto-2 sin-coincidencias">
      No se encontró «{{ buscado }}» en el texto del informe. Si es un PDF escaneado (imagen), su texto no se puede buscar.
    </p>

    <Cargando v-if="cargando" texto="Preparando el informe…" />
    <p v-else-if="error" class="mensaje mensaje-peligro">{{ error }}</p>
    <div v-else ref="hoja" class="hoja-contenedor" @contextmenu.prevent @dragstart.prevent>
      <div class="hoja" :style="{ width: `${zoom * 100}%` }">
        <img :src="paginas[pagina - 1]" :alt="`Página ${pagina} del informe`" draggable="false" />
        <span v-for="m in marcasVisibles" :key="m.indice" class="marca" :class="{ 'marca-actual': m.esActual }" :style="estilo(m.r)" aria-hidden="true" />
      </div>
    </div>
    <template #pie>
      <span class="texto-xs texto-3 nota fila"><ShieldCheck aria-hidden="true" class="icono" /> Solo lectura con marca de agua · {{ tramite.informe?.nombre_original }}</span>
      <button v-if="tramite.permisos?.descargar" type="button" class="boton" @click="descargarInforme(tramite)"><Download /> Descargar PDF</button>
      <button type="button" class="boton boton-primario" @click="abierto = false">Cerrar</button>
    </template>
  </Modal>
</template>

<style scoped>
.barra-visor { display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; margin-bottom: 10px; }
.icono { width: 16px; height: 16px; color: var(--exito); }
.separador-v { width: 1px; height: 20px; background: var(--linea); margin: 0 4px; }

.buscar-informe { position: relative; display: flex; align-items: center; gap: 6px; flex: 1; min-width: 260px; max-width: 520px; }
.buscar-informe .entrada { padding-left: 34px; flex: 1; min-width: 0; }
.buscar-icono { position: absolute; left: 10px; top: 50%; transform: translateY(-50%); width: 16px; height: 16px; color: var(--texto-3); pointer-events: none; }
.contador { white-space: nowrap; min-width: 72px; text-align: center; }

.paginas-con { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; margin-bottom: 10px; }
.chip { display: inline-flex; align-items: center; gap: 6px; padding: 2px 10px; border: 1px solid var(--linea); border-radius: 999px; background: var(--superficie); color: var(--texto-2); font-size: var(--t-xs); cursor: pointer; }
.chip:hover { border-color: var(--sello); }
.chip.activa { border-color: var(--resaltado-actual-borde); color: var(--texto); font-weight: 700; }
.chip-cantidad { background: var(--resaltado); color: var(--resaltado-texto); border-radius: 999px; padding: 0 6px; font-weight: 700; }
.sin-coincidencias { margin: 0 0 10px; }

.hoja-contenedor { background: var(--superficie-2); border: 1px solid var(--linea); border-radius: var(--radio-control); padding: 16px; overflow: auto; max-height: 66vh; user-select: none; }
.hoja { position: relative; margin: 0 auto; max-width: none; box-shadow: var(--sombra-panel); background: #fff; }
.hoja img { display: block; width: 100%; }
.marca { position: absolute; background: var(--resaltado-visor); border-radius: 2px; mix-blend-mode: multiply; pointer-events: none; }
.marca-actual { background: var(--resaltado-actual); outline: 2px solid var(--resaltado-actual-borde); outline-offset: 1px; }
.nota { margin-right: auto; }
</style>

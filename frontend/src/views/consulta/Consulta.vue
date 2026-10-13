<script setup>
// Búsqueda universal: texto libre + filtros combinables. Todo el estado vive
// en la URL (route.query) para poder volver atrás y compartir la consulta.
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Search, SlidersHorizontal, X, Printer, ExternalLink, SearchX, ChevronDown, FileSearch } from '@lucide/vue'
import { api } from '@/api'
import { useCatalogos } from '@/stores/catalogos'
import { imprimirConAuditoria } from '@/composables/utiles'
import { ESTADOS_TRAMITE } from '@/utils/constantes'
import { plural } from '@/utils/formato'
import TarjetaTramite from '@/components/tramites/TarjetaTramite.vue'
import Paginacion from '@/components/ui/Paginacion.vue'
import Cargando from '@/components/ui/Cargando.vue'
import EstadoVacio from '@/components/ui/EstadoVacio.vue'
import EncabezadoImpresion from '@/components/ui/EncabezadoImpresion.vue'

const route = useRoute()
const router = useRouter()
const catalogos = useCatalogos()

// Filtros de catálogo (clave en la URL -> catálogo)
const FILTROS_CATALOGO = [
  { clave: 'entidad_id', tipo: 'entidades', etiqueta: 'Entidad' },
  { clave: 'tipo_tramite_id', tipo: 'tipos_tramite', etiqueta: 'Tipo de trámite' },
  { clave: 'tipo_documento_id', tipo: 'tipos_documento', etiqueta: 'Tipo de documento' },
  { clave: 'profesional_id', tipo: 'profesionales', etiqueta: 'Abogado' },
  { clave: 'procedencia_id', tipo: 'procedencias', etiqueta: 'Procedencia' }
]
const CLAVES_FILTRO = ['anio', 'estado', ...FILTROS_CATALOGO.map((f) => f.clave)]
const ORDENES = { relevancia: 'Relevancia', reciente: 'Más reciente', antiguo: 'Más antiguo' }

const anioActual = new Date().getFullYear()
const anios = Array.from({ length: anioActual - 2009 }, (_, i) => anioActual - i)

const texto = ref('')
const filtrosAbiertos = ref(false)
const resultado = ref(null)
const cargando = ref(false)
const error = ref('')
const fuentes = ref([])

const q = computed(() => String(route.query.q || '').trim())
const filtros = computed(() => Object.fromEntries(CLAVES_FILTRO.map((k) => [k, String(route.query[k] ?? '')])))
const orden = computed(() => (ORDENES[route.query.orden] ? route.query.orden : 'relevancia'))
const pagina = computed(() => Math.max(1, Number(route.query.pagina) || 1))
// Dónde buscar el texto: en todo el trámite o solo dentro de los informes PDF.
const soloContenido = computed(() => route.query.en === 'contenido')
const cantidadFiltros = computed(() => CLAVES_FILTRO.filter((k) => filtros.value[k]).length)
const hayCriterio = computed(() => !!q.value || cantidadFiltros.value > 0)

function nombreValor(clave, valor) {
  if (clave === 'anio') return valor
  if (clave === 'estado') return ESTADOS_TRAMITE[valor]?.etiqueta || valor
  const f = FILTROS_CATALOGO.find((x) => x.clave === clave)
  return (catalogos.datos[f.tipo] || []).find((v) => String(v.id) === valor)?.nombre || valor
}
const ETIQUETAS = { anio: 'Año', estado: 'Estado', ...Object.fromEntries(FILTROS_CATALOGO.map((f) => [f.clave, f.etiqueta])) }

// Texto del criterio para la impresión y la auditoría.
const criterio = computed(() => {
  const partes = []
  if (q.value) partes.push(soloContenido.value ? `«${q.value}» dentro de los informes` : `«${q.value}»`)
  CLAVES_FILTRO.forEach((k) => { if (filtros.value[k]) partes.push(`${ETIQUETAS[k]}: ${nombreValor(k, filtros.value[k])}`) })
  if (!partes.length) return 'Trámites más recientes'
  if (orden.value !== 'relevancia') partes.push(`Orden: ${ORDENES[orden.value].toLowerCase()}`)
  return partes.join(' · ')
})

function navegar(cambios, { reiniciarPagina = true } = {}) {
  const query = { ...route.query, ...cambios }
  if (reiniciarPagina) delete query.pagina
  Object.keys(query).forEach((k) => { if (query[k] === '' || query[k] == null || (k === 'orden' && query[k] === 'relevancia') || (k === 'pagina' && Number(query[k]) <= 1)) delete query[k] })
  router.push({ name: 'consulta', query })
}
function buscar() { navegar({ q: texto.value.trim() }) }
function cambiarAlcance(contenido) { navegar({ en: contenido ? 'contenido' : '' }) }
function cambiarFiltro(clave, evento) { navegar({ [clave]: evento.target.value }) }
function limpiarFiltros() { navegar(Object.fromEntries(CLAVES_FILTRO.map((k) => [k, '']))) }
function irAPagina(n) {
  navegar({ pagina: n }, { reiniciarPagina: false })
  document.getElementById('resultados')?.scrollIntoView({ block: 'start' })
}

let turno = 0
async function cargar() {
  const mio = ++turno
  cargando.value = true
  error.value = ''
  try {
    const r = await api.tramites.buscar({
      q: q.value, ...filtros.value, orden: orden.value, pagina: pagina.value, por_pagina: 10,
      ...(soloContenido.value && q.value ? { en: 'contenido' } : {})
    })
    if (mio === turno) resultado.value = r
  } catch (e) {
    if (mio === turno) error.value = e.message || 'No se pudo realizar la búsqueda.'
  } finally {
    if (mio === turno) cargando.value = false
  }
}

watch(q, (v) => { texto.value = v }, { immediate: true })
watch(() => route.fullPath, () => { if (route.name === 'consulta') cargar() }, { immediate: true })

onMounted(async () => {
  catalogos.varios(FILTROS_CATALOGO.map((f) => f.tipo)).catch(() => {})
  try { fuentes.value = (await api.fuentes.listar()).filter((f) => f.activo) } catch { fuentes.value = [] }
})

// ---------- Fuentes externas ----------
function enlaceFuente(f) {
  return f.url_busqueda && q.value ? f.url_busqueda.replaceAll('{q}', encodeURIComponent(q.value)) : f.url
}
function abrirFuente(f) {
  api.auditoria.registrar({ accion: 'ABRIR_FUENTE_EXTERNA', modulo: 'CONSULTA', detalle: { fuente: f.nombre, q: q.value || null } }).catch(() => {})
}

function imprimir() {
  imprimirConAuditoria({ criterio: criterio.value, cantidad: resultado.value?.total ?? 0 })
}
</script>

<template>
  <div class="pagina">
    <EncabezadoImpresion titulo="Reporte de consulta" :criterio="criterio" :resultados="resultado?.total ?? 0" />

    <header class="pagina-cabecera no-imprimir">
      <div>
        <h1>Búsqueda universal</h1>
        <p>Busque en todos los trámites por cualquier dato y combine filtros para afinar el resultado.</p>
      </div>
      <div class="pagina-acciones">
        <button type="button" class="boton" :disabled="!resultado?.items?.length" @click="imprimir"><Printer aria-hidden="true" /> Imprimir consulta</button>
      </div>
    </header>

    <form class="buscador no-imprimir" role="search" @submit.prevent="buscar">
      <label for="consulta-texto" class="sr-only">Texto a buscar</label>
      <Search class="buscador-icono" aria-hidden="true" />
      <input id="consulta-texto" v-model="texto" type="search" class="entrada buscador-entrada" autocomplete="off"
        placeholder="Escriba cualquier criterio: entidad, hoja de ruta, número de documento, abogado, asunto…" />
      <button type="submit" class="boton boton-primario buscador-boton">Buscar</button>
    </form>
    <fieldset class="alcance no-imprimir">
      <legend class="sr-only">Dónde buscar</legend>
      <label class="alcance-opcion" :class="{ activa: !soloContenido }">
        <input type="radio" name="alcance" class="sr-only" :checked="!soloContenido" @change="cambiarAlcance(false)" />
        <Search aria-hidden="true" /> En todo el trámite
      </label>
      <label class="alcance-opcion" :class="{ activa: soloContenido }">
        <input type="radio" name="alcance" class="sr-only" :checked="soloContenido" @change="cambiarAlcance(true)" />
        <FileSearch aria-hidden="true" /> Solo dentro de los informes PDF
      </label>
    </fieldset>

    <div class="consulta">
      <aside class="lateral no-imprimir">
        <section class="panel filtros" aria-labelledby="titulo-filtros">
          <div class="panel-cabecera">
            <h2 id="titulo-filtros">Filtros</h2>
            <button type="button" class="boton boton-pequeno boton-fantasma alternar" :aria-expanded="filtrosAbiertos"
              aria-controls="filtros-cuerpo" @click="filtrosAbiertos = !filtrosAbiertos">
              <SlidersHorizontal aria-hidden="true" />
              {{ filtrosAbiertos ? 'Ocultar' : 'Mostrar' }}<template v-if="cantidadFiltros"> ({{ cantidadFiltros }})</template>
              <ChevronDown class="chevron" :class="{ girado: filtrosAbiertos }" aria-hidden="true" />
            </button>
          </div>
          <div id="filtros-cuerpo" class="panel-cuerpo filtros-cuerpo" :class="{ abierto: filtrosAbiertos }">
            <div class="campo">
              <label for="f-orden">Ordenar por</label>
              <select id="f-orden" class="seleccion" :value="orden" @change="navegar({ orden: $event.target.value })">
                <option v-for="(etiqueta, clave) in ORDENES" :key="clave" :value="clave">{{ etiqueta }}</option>
              </select>
              <p v-if="!q && orden === 'relevancia'" class="ayuda">Sin texto de búsqueda se muestran primero los más recientes.</p>
            </div>
            <div class="campo">
              <label for="f-anio">Año de gestión</label>
              <select id="f-anio" class="seleccion" :value="filtros.anio" @change="cambiarFiltro('anio', $event)">
                <option value="">Todos</option>
                <option v-for="a in anios" :key="a" :value="String(a)">{{ a }}</option>
              </select>
            </div>
            <div class="campo">
              <label for="f-estado">Estado</label>
              <select id="f-estado" class="seleccion" :value="filtros.estado" @change="cambiarFiltro('estado', $event)">
                <option value="">Todos</option>
                <option v-for="(e, clave) in ESTADOS_TRAMITE" :key="clave" :value="clave">{{ e.etiqueta }}</option>
              </select>
            </div>
            <div v-for="f in FILTROS_CATALOGO" :key="f.clave" class="campo">
              <label :for="`f-${f.clave}`">{{ f.etiqueta }}</label>
              <select :id="`f-${f.clave}`" class="seleccion" :value="filtros[f.clave]" @change="cambiarFiltro(f.clave, $event)">
                <option value="">Todos</option>
                <option v-for="v in catalogos.datos[f.tipo] || []" :key="v.id" :value="String(v.id)">{{ v.nombre }}</option>
              </select>
            </div>
            <button v-if="cantidadFiltros" type="button" class="boton" @click="limpiarFiltros"><X aria-hidden="true" /> Limpiar filtros</button>
          </div>
        </section>

        <section v-if="fuentes.length" class="panel" aria-labelledby="titulo-fuentes">
          <div class="panel-cabecera"><h2 id="titulo-fuentes">Buscar en sitios legales</h2></div>
          <div class="panel-cuerpo">
            <p class="ayuda fuentes-ayuda">Se abren en una pestaña nueva, fuera del repositorio.<template v-if="q"> Donde el sitio lo permite, se envía su texto de búsqueda.</template></p>
            <ul class="fuentes">
              <li v-for="f in fuentes" :key="f.id">
                <a :href="enlaceFuente(f)" target="_blank" rel="noopener noreferrer" @click="abrirFuente(f)">
                  <span class="fuente-nombre">{{ f.nombre }} <ExternalLink aria-hidden="true" /></span>
                  <span v-if="f.descripcion" class="texto-xs texto-3">{{ f.descripcion }}</span>
                  <span class="sr-only">(se abre en una pestaña nueva)</span>
                </a>
              </li>
            </ul>
          </div>
        </section>
      </aside>

      <section id="resultados" class="resultados" aria-labelledby="titulo-resultados" :aria-busy="cargando">
        <div class="fila-entre resultados-cabecera">
          <h2 id="titulo-resultados" class="conteo" aria-live="polite">
            <template v-if="!resultado && cargando">Buscando…</template>
            <template v-else-if="resultado && hayCriterio">{{ plural(resultado.total, 'trámite encontrado', 'trámites encontrados') }}</template>
            <template v-else-if="resultado">Trámites más recientes</template>
          </h2>
          <p v-if="hayCriterio && resultado" class="texto-pequeno texto-2 criterio no-imprimir">{{ criterio }}</p>
        </div>

        <p v-if="error" class="mensaje mensaje-peligro" role="alert">{{ error }}</p>
        <Cargando v-else-if="cargando && !resultado" texto="Buscando trámites…" />
        <template v-else-if="resultado">
          <EstadoVacio v-if="!resultado.items.length" :icono="SearchX" titulo="No se encontraron resultados"
            texto="Revise la ortografía, use menos palabras o palabras más generales (por ejemplo, solo el nombre de la entidad) y quite algunos filtros.">
            <button v-if="cantidadFiltros" type="button" class="boton" @click="limpiarFiltros">Limpiar filtros</button>
            <button v-if="q" type="button" class="boton" @click="texto = ''; navegar({ q: '' })">Quitar el texto</button>
          </EstadoVacio>
          <div v-else class="lista" :class="{ actualizando: cargando }">
            <TarjetaTramite v-for="t in resultado.items" :key="t.id" :tramite="t" :q="q" />
          </div>
          <Paginacion :pagina="resultado.pagina" :paginas="resultado.paginas" :total="resultado.total" @cambiar="irAPagina" />
        </template>
      </section>
    </div>
  </div>
</template>

<style scoped>
.buscador { position: relative; display: flex; gap: var(--e-2); margin-bottom: var(--e-3); }
.alcance { display: flex; flex-wrap: wrap; gap: var(--e-2); border: 0; margin: 0 0 var(--e-6); padding: 0; }
.alcance-opcion { display: inline-flex; align-items: center; gap: 6px; padding: 6px 14px; border: 1px solid var(--linea); border-radius: 999px; background: var(--superficie); color: var(--texto-2); font-size: var(--t-sm); cursor: pointer; }
.alcance-opcion svg { width: 16px; height: 16px; }
.alcance-opcion.activa { border-color: var(--sello); background: var(--sello-suave); color: var(--tinta); font-weight: 600; }
.alcance-opcion:focus-within { box-shadow: var(--foco); }
.buscador-icono { position: absolute; left: 16px; top: 50%; transform: translateY(-50%); width: 20px; height: 20px; color: var(--texto-3); pointer-events: none; }
.buscador-entrada { min-height: 52px; padding-left: 46px; font-size: var(--t-lg); border-width: 1.5px; box-shadow: var(--sombra-panel); }
.buscador-boton { min-height: 52px; padding: 0 var(--e-6); font-size: var(--t-md); }

.consulta { display: grid; grid-template-columns: 280px minmax(0, 1fr); gap: var(--e-6); align-items: start; }
.lateral > .panel + .panel { margin-top: var(--e-6); }
.filtros-cuerpo { display: grid; gap: var(--e-4); }
.alternar { display: none; }
.chevron { transition: transform .15s; }
.chevron.girado { transform: rotate(180deg); }

.fuentes-ayuda { margin-bottom: var(--e-3); }
.fuentes { list-style: none; margin: 0; padding: 0; }
.fuentes li + li { border-top: 1px solid var(--linea); }
.fuentes a { display: flex; flex-direction: column; gap: 2px; padding: var(--e-2) 0; }
.fuente-nombre { display: inline-flex; align-items: center; gap: 6px; font-weight: 600; font-size: var(--t-sm); }
.fuente-nombre svg { width: 14px; height: 14px; flex: none; }

.resultados-cabecera { margin-bottom: var(--e-4); align-items: baseline; }
.conteo { font-size: var(--t-lg); }
.criterio { overflow-wrap: anywhere; }
.lista { display: grid; gap: var(--e-3); }
.lista.actualizando { opacity: .6; }

@media (max-width: 960px) {
  .consulta { grid-template-columns: 1fr; }
  .alternar { display: inline-flex; }
  .filtros-cuerpo:not(.abierto) { display: none; }
}
@media (max-width: 520px) {
  .buscador { flex-direction: column; }
  .buscador-icono { top: 26px; }
  .buscador-entrada { font-size: var(--t-md); }
  .buscador-boton { min-height: 44px; }
}
@media print {
  .consulta { display: block; }
  .lista.actualizando { opacity: 1; }
}
</style>

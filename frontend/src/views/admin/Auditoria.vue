<script setup>
// Bitácora de auditoría: solo lectura, con filtros reflejados en la dirección (URL).
import { reactive, ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Printer, Lock, ChevronRight, ChevronDown, ScrollText, RotateCcw } from '@lucide/vue'
import { api } from '@/api'
import { useCarga, imprimirConAuditoria } from '@/composables/utiles'
import { ACCIONES_AUDITORIA } from '@/utils/constantes'
import { formatoFechaHora, formatoFecha, formatoNumero } from '@/utils/formato'
import { ETIQUETAS_MODULOS, RESULTADOS_AUDITORIA, etiquetaAccion, etiquetaModulo } from '@/components/admin/etiquetasAuditoria'
import Cargando from '@/components/ui/Cargando.vue'
import EstadoVacio from '@/components/ui/EstadoVacio.vue'
import Paginacion from '@/components/ui/Paginacion.vue'
import EncabezadoImpresion from '@/components/ui/EncabezadoImpresion.vue'

const route = useRoute()
const router = useRouter()
const CAMPOS = ['usuario_id', 'accion', 'modulo', 'resultado', 'desde', 'hasta']

const filtros = reactive(Object.fromEntries(CAMPOS.map((c) => [c, String(route.query[c] ?? '')])))
const pagina = computed(() => Math.max(1, Number(route.query.pagina) || 1))

const { datos: usuarios } = useCarga(() => api.usuarios.listar(), { inicial: [] })
const usuariosOrdenados = computed(() => [...(usuarios.value || [])].sort((a, b) => a.nombre_completo.localeCompare(b.nombre_completo, 'es')))
const acciones = computed(() => [...ACCIONES_AUDITORIA].sort((a, b) => etiquetaAccion(a).localeCompare(etiquetaAccion(b), 'es')))

const { datos: resultado, cargando, error, cargar } = useCarga(
  () => api.auditoria.listar({ ...Object.fromEntries(CAMPOS.map((c) => [c, route.query[c] || ''])), pagina: pagina.value, por_pagina: 20 }),
  { inmediato: false }
)

const abiertos = ref(new Set())
const nombreRuta = route.name

// Filtros -> URL (vuelve a la página 1). URL -> carga.
watch(filtros, () => {
  const query = {}
  CAMPOS.forEach((c) => { if (filtros[c]) query[c] = filtros[c] })
  router.replace({ query })
})
watch(() => route.query, () => {
  if (route.name !== nombreRuta) return
  CAMPOS.forEach((c) => { const v = String(route.query[c] ?? ''); if (filtros[c] !== v) filtros[c] = v })
  abiertos.value = new Set()
  cargar()
}, { immediate: true })

function irPagina(n) { router.replace({ query: { ...route.query, pagina: n > 1 ? n : undefined } }) }
function limpiar() { CAMPOS.forEach((c) => { filtros[c] = '' }) }
const hayFiltros = computed(() => CAMPOS.some((c) => filtros[c]))
const fechasInvalidas = computed(() => filtros.desde && filtros.hasta && filtros.desde > filtros.hasta)

// Filas expandidas
function alternar(id) {
  const s = new Set(abiertos.value)
  s.has(id) ? s.delete(id) : s.add(id)
  abiertos.value = s
}
function detalleJson(r) {
  return JSON.stringify(r.detalle ?? null, null, 2)
}
const objeto = (r) => (r.objeto_tipo ? `${r.objeto_tipo}${r.objeto_id ? ` #${r.objeto_id}` : ''}` : '—')
const nombreUsuario = (r) => usuarios.value?.find((u) => u.id === r.usuario_id)?.nombre_completo || null

// Impresión
const criterio = computed(() => {
  const partes = []
  if (filtros.usuario_id) partes.push(`usuario: ${usuarios.value?.find((u) => String(u.id) === filtros.usuario_id)?.correo || filtros.usuario_id}`)
  if (filtros.accion) partes.push(`acción: ${etiquetaAccion(filtros.accion)}`)
  if (filtros.modulo) partes.push(`módulo: ${etiquetaModulo(filtros.modulo)}`)
  if (filtros.resultado) partes.push(`resultado: ${RESULTADOS_AUDITORIA[filtros.resultado]?.etiqueta}`)
  if (filtros.desde) partes.push(`desde ${formatoFecha(filtros.desde)}`)
  if (filtros.hasta) partes.push(`hasta ${formatoFecha(filtros.hasta)}`)
  return (partes.join(' · ') || 'sin filtros') + ` · página ${pagina.value}`
})
function imprimir() {
  imprimirConAuditoria({ pantalla: 'auditoria', filtros: { ...filtros }, pagina: pagina.value, resultados: resultado.value?.total ?? 0 }, 'AUDITORIA')
}
</script>

<template>
  <div class="pagina">
    <EncabezadoImpresion titulo="Auditoría" :criterio="criterio" :resultados="resultado?.total ?? null" />

    <header class="pagina-cabecera no-imprimir">
      <div>
        <h1>Auditoría</h1>
        <p>Registro de quién hizo qué y cuándo en el repositorio: ingresos, consultas, descargas, cambios y administración.</p>
      </div>
      <div class="pagina-acciones">
        <button type="button" class="boton" :disabled="!resultado?.items?.length" @click="imprimir"><Printer aria-hidden="true" /> Imprimir</button>
      </div>
    </header>

    <div class="mensaje mensaje-info nota no-imprimir">
      <Lock aria-hidden="true" />
      <span>La bitácora es de solo lectura: sus registros no pueden modificarse ni borrarse, ni siquiera por un administrador.</span>
    </div>

    <form class="panel filtros no-imprimir" aria-label="Filtros de auditoría" @submit.prevent>
      <div class="panel-cuerpo rejilla-filtros">
        <div class="campo">
          <label for="aud-usuario">Usuario</label>
          <select id="aud-usuario" v-model="filtros.usuario_id" class="seleccion">
            <option value="">Todos</option>
            <option v-for="u in usuariosOrdenados" :key="u.id" :value="String(u.id)">{{ u.nombre_completo }}</option>
          </select>
        </div>
        <div class="campo">
          <label for="aud-accion">Acción</label>
          <select id="aud-accion" v-model="filtros.accion" class="seleccion">
            <option value="">Todas</option>
            <option v-for="a in acciones" :key="a" :value="a">{{ etiquetaAccion(a) }}</option>
          </select>
        </div>
        <div class="campo">
          <label for="aud-modulo">Módulo</label>
          <select id="aud-modulo" v-model="filtros.modulo" class="seleccion">
            <option value="">Todos</option>
            <option v-for="(etiqueta, clave) in ETIQUETAS_MODULOS" :key="clave" :value="clave">{{ etiqueta }}</option>
          </select>
        </div>
        <div class="campo">
          <label for="aud-resultado">Resultado</label>
          <select id="aud-resultado" v-model="filtros.resultado" class="seleccion">
            <option value="">Todos</option>
            <option v-for="(r, clave) in RESULTADOS_AUDITORIA" :key="clave" :value="clave">{{ r.etiqueta }}</option>
          </select>
        </div>
        <div class="campo">
          <label for="aud-desde">Desde</label>
          <input id="aud-desde" v-model="filtros.desde" type="date" class="entrada" :max="filtros.hasta || undefined" :aria-invalid="!!fechasInvalidas" />
        </div>
        <div class="campo">
          <label for="aud-hasta">Hasta</label>
          <input id="aud-hasta" v-model="filtros.hasta" type="date" class="entrada" :min="filtros.desde || undefined" :aria-invalid="!!fechasInvalidas" aria-describedby="aud-fechas-error" />
          <span v-if="fechasInvalidas" id="aud-fechas-error" class="error-campo">La fecha final es anterior a la inicial.</span>
        </div>
      </div>
      <div v-if="hayFiltros" class="limpiar">
        <button type="button" class="boton boton-fantasma boton-pequeno" @click="limpiar"><RotateCcw aria-hidden="true" /> Quitar filtros</button>
      </div>
    </form>

    <div class="panel">
      <div class="panel-cabecera no-imprimir">
        <h2>Registros</h2>
        <span v-if="resultado" class="texto-2 texto-pequeno" role="status">{{ formatoNumero(resultado.total) }} {{ resultado.total === 1 ? 'registro' : 'registros' }}</span>
      </div>
      <Cargando v-if="cargando && !resultado" texto="Cargando auditoría…" />
      <div v-else-if="error" class="panel-cuerpo"><div class="mensaje mensaje-peligro" role="alert">{{ error }}</div></div>
      <EstadoVacio v-else-if="!resultado?.items?.length" :icono="ScrollText" titulo="No hay registros" :texto="hayFiltros ? 'Ningún registro cumple los filtros elegidos.' : 'Todavía no se registró actividad.'" />
      <div v-else class="tabla-contenedor" :aria-busy="cargando">
        <table class="tabla">
          <caption class="sr-only">Registros de auditoría</caption>
          <thead>
            <tr>
              <th scope="col" class="no-imprimir"><span class="sr-only">Ver detalle</span></th>
              <th scope="col">Fecha y hora</th>
              <th scope="col">Usuario</th>
              <th scope="col">Acción</th>
              <th scope="col">Módulo</th>
              <th scope="col">Objeto</th>
              <th scope="col">Resultado</th>
              <th scope="col">IP</th>
            </tr>
          </thead>
          <tbody>
            <template v-for="r in resultado.items" :key="r.id">
              <tr :class="{ abierta: abiertos.has(r.id) }">
                <td class="no-imprimir">
                  <button
                    type="button" class="boton boton-icono boton-fantasma boton-pequeno" :aria-expanded="abiertos.has(r.id)"
                    :aria-controls="`aud-detalle-${r.id}`" :aria-label="abiertos.has(r.id) ? 'Ocultar detalle' : 'Ver detalle'" @click="alternar(r.id)"
                  >
                    <ChevronDown v-if="abiertos.has(r.id)" aria-hidden="true" /><ChevronRight v-else aria-hidden="true" />
                  </button>
                </td>
                <td class="sin-salto">{{ formatoFechaHora(r.creado_en) }}</td>
                <td>
                  <span v-if="nombreUsuario(r)">{{ nombreUsuario(r) }}<div class="texto-3 texto-xs">{{ r.usuario_correo }}</div></span>
                  <span v-else>{{ r.usuario_correo }}</span>
                </td>
                <td>{{ etiquetaAccion(r.accion) }}</td>
                <td>{{ etiquetaModulo(r.modulo) }}</td>
                <td class="sin-salto">{{ objeto(r) }}</td>
                <td><span class="insignia" :class="RESULTADOS_AUDITORIA[r.resultado]?.clase">{{ RESULTADOS_AUDITORIA[r.resultado]?.etiqueta || r.resultado }}</span></td>
                <td class="sin-salto texto-2">{{ r.ip || '—' }}</td>
              </tr>
              <tr v-if="abiertos.has(r.id)" :id="`aud-detalle-${r.id}`" class="detalle">
                <td colspan="8">
                  <dl class="detalle-datos">
                    <div><dt>Registro</dt><dd>#{{ r.id }}</dd></div>
                    <div><dt>Código de acción</dt><dd>{{ r.accion }}</dd></div>
                  </dl>
                  <p class="etiqueta">Detalle</p>
                  <pre v-if="r.detalle" class="json">{{ detalleJson(r) }}</pre>
                  <p v-else class="texto-3 texto-pequeno">Este registro no tiene detalle adicional.</p>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
      <div v-if="resultado?.paginas > 1" class="panel-cuerpo pie-paginacion no-imprimir">
        <Paginacion :pagina="resultado.pagina" :paginas="resultado.paginas" :total="resultado.total" @cambiar="irPagina" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.nota { margin-bottom: var(--e-4); }
.filtros { margin-bottom: var(--e-6); }
.rejilla-filtros { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: var(--e-4); }
.limpiar { padding: 0 var(--e-6) var(--e-4); display: flex; justify-content: flex-end; }
.sin-salto { white-space: nowrap; }
.abierta td { background: var(--sello-suave); }
.detalle td { background: var(--superficie-2); }
.detalle-datos { display: flex; gap: var(--e-6); flex-wrap: wrap; margin: 0 0 var(--e-3); }
.detalle-datos dt { font-size: var(--t-xs); color: var(--texto-3); }
.detalle-datos dd { margin: 0; font-weight: 600; }
.json {
  margin: var(--e-2) 0 0; padding: var(--e-3) var(--e-4); background: var(--superficie); border: 1px solid var(--linea);
  border-radius: var(--radio-control); font-size: var(--t-xs); white-space: pre-wrap; overflow-wrap: anywhere; max-width: 100%;
}
.pie-paginacion { padding-top: 0; }
.pie-paginacion :deep(.paginacion) { margin-top: var(--e-4); }
</style>

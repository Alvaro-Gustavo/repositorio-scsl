<script setup>
// Gestion de prompts. ABOGADO: sus propuestas. JEFE/ADMIN: revisar, aprobar, devolver y retirar.
import { ref, computed } from 'vue'
import { RouterLink } from 'vue-router'
import { Plus, Eye, Pencil, Check, Undo2, Archive, ArrowLeft, MessageSquareText } from '@lucide/vue'
import { api } from '@/api'
import { useSesion } from '@/stores/sesion'
import { useCarga, useEnvio } from '@/composables/utiles'
import { CATEGORIAS_PROMPT, ESTADOS_PROMPT } from '@/utils/constantes'
import { formatoFecha, formatoNumero, plural } from '@/utils/formato'
import Modal from '@/components/ui/Modal.vue'
import Cargando from '@/components/ui/Cargando.vue'
import EstadoVacio from '@/components/ui/EstadoVacio.vue'
import TextoPrompt from '@/components/prompts/TextoPrompt.vue'

const sesion = useSesion()
const esJefe = computed(() => sesion.puede('GESTIONAR_PROMPTS'))

const { datos: prompts, cargando, error, cargar } = useCarga(() => api.prompts.gestion(), { inicial: [] })

const PESTANAS = [
  { clave: 'BORRADOR', titulo: 'Por revisar', vacio: 'No hay propuestas pendientes de revisión.' },
  { clave: 'VIGENTE', titulo: 'Vigentes', vacio: 'No hay prompts vigentes.' },
  { clave: 'RETIRADO', titulo: 'Retirados', vacio: 'No hay prompts retirados.' }
]
const pestana = ref('BORRADOR')
const conteo = computed(() => {
  const c = {}
  for (const p of prompts.value || []) c[p.estado] = (c[p.estado] || 0) + 1
  return c
})
const lista = computed(() => (esJefe.value ? (prompts.value || []).filter((p) => p.estado === pestana.value) : prompts.value || []))
const textoVacio = computed(() => (esJefe.value
  ? PESTANAS.find((p) => p.clave === pestana.value).vacio
  : 'Todavía no propuso ningún prompt. Sus propuestas aparecerán aquí con su estado.'))

const puedeEditar = (p) => p.estado === 'BORRADOR' || (p.estado === 'VIGENTE' && esJefe.value)
const devuelto = (p) => p.estado === 'BORRADOR' && !!p.observacion

function moverFoco(e, i) {
  const n = PESTANAS.length
  const j = e.key === 'ArrowRight' ? (i + 1) % n : e.key === 'ArrowLeft' ? (i - 1 + n) % n : null
  if (j === null) return
  pestana.value = PESTANAS[j].clave
  document.getElementById(`pestana-${PESTANAS[j].clave}`)?.focus()
}

// ---------- Ver / revisar ----------
const verAbierto = ref(false)
const actual = ref(null)
function ver(p) { actual.value = p; verAbierto.value = true }

const { enviando, enviar } = useEnvio()
async function aprobar(p) {
  try {
    await enviar(() => api.prompts.aprobar(p.id), 'Prompt aprobado. Ya está disponible en el catálogo.')
    verAbierto.value = false
    cargar()
  } catch { /* el aviso ya se mostro */ }
}

// ---------- Devolver ----------
const devolverAbierto = ref(false)
const observacion = ref('')
const envioDevolver = useEnvio()
const errorObservacion = computed(() => envioDevolver.errores.value.observacion)
function abrirDevolver(p) {
  actual.value = p
  observacion.value = ''
  envioDevolver.errores.value = {}
  verAbierto.value = false
  devolverAbierto.value = true
}
async function confirmarDevolver() {
  if (!observacion.value.trim()) {
    envioDevolver.errores.value = { observacion: 'Escriba qué debe corregirse.' }
    document.getElementById('observacion')?.focus()
    return
  }
  try {
    await envioDevolver.enviar(() => api.prompts.devolver(actual.value.id, observacion.value.trim()), 'Propuesta devuelta con observación.')
    devolverAbierto.value = false
    cargar()
  } catch { /* el aviso ya se mostro */ }
}

// ---------- Retirar ----------
const retirarAbierto = ref(false)
function abrirRetirar(p) { actual.value = p; retirarAbierto.value = true }
async function confirmarRetirar() {
  try {
    await enviar(() => api.prompts.retirar(actual.value.id), 'Prompt retirado del catálogo.')
    retirarAbierto.value = false
    cargar()
  } catch { /* el aviso ya se mostro */ }
}
</script>

<template>
  <div class="pagina">
    <header class="pagina-cabecera">
      <div>
        <h1>{{ esJefe ? 'Gestión de prompts' : 'Mis propuestas' }}</h1>
        <p v-if="esJefe">Revise las propuestas, apruébelas o devuélvalas con una observación, y retire los prompts que ya no deben usarse.</p>
        <p v-else>Los prompts que propone pasan a revisión de la jefatura. Si se los devuelven, corríjalos y quedarán otra vez por revisar.</p>
      </div>
      <div class="pagina-acciones">
        <RouterLink to="/prompts" class="boton"><ArrowLeft aria-hidden="true" /> Catálogo</RouterLink>
        <RouterLink to="/prompts/nuevo" class="boton boton-primario"><Plus aria-hidden="true" /> Proponer un prompt</RouterLink>
      </div>
    </header>

    <div v-if="esJefe" class="pestanas" role="tablist" aria-label="Estado de los prompts">
      <button v-for="(t, i) in PESTANAS" :id="`pestana-${t.clave}`" :key="t.clave" type="button" class="pestana" role="tab"
        :aria-selected="pestana === t.clave" :tabindex="pestana === t.clave ? 0 : -1" aria-controls="panel-prompts"
        @click="pestana = t.clave" @keydown="moverFoco($event, i)">
        {{ t.titulo }} <span class="pestana-n">{{ conteo[t.clave] || 0 }}</span>
      </button>
    </div>

    <section id="panel-prompts" class="panel" :role="esJefe ? 'tabpanel' : null"
      :aria-labelledby="esJefe ? `pestana-${pestana}` : null" :aria-busy="cargando">
      <Cargando v-if="cargando" texto="Cargando prompts…" />
      <div v-else-if="error" class="panel-cuerpo">
        <p class="mensaje mensaje-peligro" role="alert">{{ error }}</p>
        <div class="formulario-acciones"><button type="button" class="boton" @click="cargar()">Reintentar</button></div>
      </div>
      <EstadoVacio v-else-if="!lista.length" :icono="MessageSquareText" titulo="Sin prompts" :texto="textoVacio">
        <RouterLink v-if="!esJefe" to="/prompts/nuevo" class="boton boton-primario">Proponer un prompt</RouterLink>
      </EstadoVacio>
      <div v-else class="tabla-contenedor">
        <table class="tabla">
          <thead>
            <tr>
              <th scope="col">Título</th>
              <th scope="col">Categoría</th>
              <th scope="col">Tipo de documento</th>
              <th v-if="esJefe" scope="col">Propuesto por</th>
              <th v-else scope="col">Estado</th>
              <th scope="col">Actualizado</th>
              <th scope="col" class="num">Usos</th>
              <th scope="col"><span class="sr-only">Acciones</span></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="p in lista" :key="p.id">
              <td class="col-titulo">
                <strong>{{ p.titulo }}</strong>
                <span v-if="esJefe && devuelto(p)" class="insignia insignia-aviso insignia-sin-punto marca-devuelto">Devuelto, espera corrección</span>
                <p v-if="!esJefe && devuelto(p)" class="observacion">
                  <span class="etiqueta">Observación de la jefatura:</span> {{ p.observacion }}
                </p>
              </td>
              <td>{{ CATEGORIAS_PROMPT[p.categoria] || p.categoria }}</td>
              <td>{{ p.tipo_documento?.nombre || 'General' }}</td>
              <td v-if="esJefe">{{ p.propuesto_por?.nombre_completo || '—' }}</td>
              <td v-else>
                <span class="insignia" :class="devuelto(p) ? 'insignia-peligro' : ESTADOS_PROMPT[p.estado]?.clase">
                  {{ devuelto(p) ? 'Devuelto' : (p.estado === 'BORRADOR' ? 'En revisión' : ESTADOS_PROMPT[p.estado]?.etiqueta || p.estado) }}
                </span>
              </td>
              <td class="sin-salto">{{ formatoFecha(p.actualizado_en) }}</td>
              <td class="num">{{ formatoNumero(p.usos) }}</td>
              <td>
                <div class="acciones-fila">
                  <button type="button" class="boton boton-pequeno" :aria-label="`${esJefe && p.estado === 'BORRADOR' ? 'Revisar' : 'Ver'} ${p.titulo}`" @click="ver(p)">
                    <Eye aria-hidden="true" /> {{ esJefe && p.estado === 'BORRADOR' ? 'Revisar' : 'Ver' }}
                  </button>
                  <RouterLink v-if="puedeEditar(p)" :to="`/prompts/${p.id}/editar`" class="boton boton-pequeno boton-fantasma" :aria-label="`Editar ${p.titulo}`">
                    <Pencil aria-hidden="true" /> Editar
                  </RouterLink>
                  <button v-if="esJefe && p.estado === 'VIGENTE'" type="button" class="boton boton-pequeno boton-peligro" :aria-label="`Retirar ${p.titulo}`" @click="abrirRetirar(p)">
                    <Archive aria-hidden="true" /> Retirar
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- Ver o revisar el texto completo -->
    <Modal v-model="verAbierto" :titulo="actual?.titulo || 'Prompt'" ancho="720px">
      <div v-if="actual" class="formulario">
        <dl class="datos">
          <div><dt>Categoría</dt><dd>{{ CATEGORIAS_PROMPT[actual.categoria] || actual.categoria }}</dd></div>
          <div><dt>Tipo de documento</dt><dd>{{ actual.tipo_documento?.nombre || 'General' }}</dd></div>
          <div><dt>Propuesto por</dt><dd>{{ actual.propuesto_por?.nombre_completo || '—' }}</dd></div>
          <div><dt>Estado</dt><dd>{{ devuelto(actual) ? 'Devuelto con observación' : ESTADOS_PROMPT[actual.estado]?.etiqueta }}</dd></div>
          <div v-if="actual.aprobado_por"><dt>Aprobado por</dt><dd>{{ actual.aprobado_por.nombre_completo }} · {{ formatoFecha(actual.aprobado_en) }}</dd></div>
          <div v-if="actual.estado !== 'BORRADOR'"><dt>Usos</dt><dd>{{ plural(actual.usos || 0, 'copia', 'copias') }}</dd></div>
        </dl>
        <p v-if="devuelto(actual)" class="mensaje mensaje-aviso"><span><strong>Observación:</strong> {{ actual.observacion }}</span></p>
        <div class="campo">
          <span class="etiqueta">Texto del prompt</span>
          <TextoPrompt :texto="actual.texto" />
        </div>
        <div class="campo">
          <span class="etiqueta">Instrucciones de uso</span>
          <p class="texto-2 texto-pequeno">{{ actual.instrucciones || 'Sin instrucciones.' }}</p>
        </div>
      </div>
      <template #pie>
        <button type="button" class="boton" @click="verAbierto = false">Cerrar</button>
        <template v-if="esJefe && actual?.estado === 'BORRADOR'">
          <button type="button" class="boton" :disabled="enviando" @click="abrirDevolver(actual)"><Undo2 aria-hidden="true" /> Devolver con observación</button>
          <button type="button" class="boton boton-primario" :disabled="enviando" @click="aprobar(actual)"><Check aria-hidden="true" /> Aprobar</button>
        </template>
      </template>
    </Modal>

    <!-- Devolver -->
    <Modal v-model="devolverAbierto" titulo="Devolver con observación">
      <form id="form-devolver" class="formulario" novalidate @submit.prevent="confirmarDevolver">
        <p class="texto-2 texto-pequeno">La propuesta «{{ actual?.titulo }}» vuelve a quien la propuso para que la corrija.</p>
        <div class="campo">
          <label for="observacion">Qué debe corregirse<span class="requerido" aria-hidden="true">*</span></label>
          <textarea id="observacion" v-model="observacion" class="area-texto" rows="4" required
            :aria-invalid="!!errorObservacion" :aria-describedby="errorObservacion ? 'observacion-error' : null"></textarea>
          <span v-if="errorObservacion" id="observacion-error" class="error-campo">{{ errorObservacion }}</span>
        </div>
      </form>
      <template #pie>
        <button type="button" class="boton" @click="devolverAbierto = false">Cancelar</button>
        <button type="submit" form="form-devolver" class="boton boton-primario" :disabled="envioDevolver.enviando.value">
          <Undo2 aria-hidden="true" /> Devolver
        </button>
      </template>
    </Modal>

    <!-- Retirar -->
    <Modal v-model="retirarAbierto" titulo="Retirar prompt">
      <p>¿Retirar «{{ actual?.titulo }}» del catálogo? Los doctores ya no podrán copiarlo. El historial de usos se conserva.</p>
      <template #pie>
        <button type="button" class="boton" @click="retirarAbierto = false">Cancelar</button>
        <button type="button" class="boton boton-peligro" :disabled="enviando" @click="confirmarRetirar"><Archive aria-hidden="true" /> Retirar</button>
      </template>
    </Modal>
  </div>
</template>

<style scoped>
.pestana-n { margin-left: 4px; font-size: var(--t-xs); color: var(--texto-3); font-variant-numeric: tabular-nums; }
.col-titulo { min-width: 220px; }
.marca-devuelto { margin-top: var(--e-1); }
.col-titulo strong { display: block; }
.observacion { margin-top: var(--e-2); font-size: var(--t-xs); color: var(--aviso); background: var(--aviso-suave); padding: var(--e-2) var(--e-3); border-radius: var(--radio-control); max-width: 48ch; }
.observacion .etiqueta { font-size: inherit; color: inherit; }
.sin-salto { white-space: nowrap; }
.acciones-fila { display: flex; gap: var(--e-1); justify-content: flex-end; flex-wrap: wrap; }
</style>

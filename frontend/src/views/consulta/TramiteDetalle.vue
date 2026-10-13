<script setup>
// Expediente de un trámite: datos, informe, precedentes, cadena, similares e historial.
// Las acciones visibles dependen de tramite.permisos (el backend vuelve a verificarlas).
import { ref, reactive, computed, watch } from 'vue'
import { useRouter, RouterLink } from 'vue-router'
import {
  Pencil, UserPlus, FileUp, Archive, Trash2, Printer, Sparkles, Eye, Download, Link2, Plus, Search, FileX, ArrowLeft
} from '@lucide/vue'
import { api } from '@/api'
import { useCatalogos } from '@/stores/catalogos'
import { useEnvio, descargarInforme, imprimirConAuditoria } from '@/composables/utiles'
import { RELEVANCIAS, TIPOS_RELACION } from '@/utils/constantes'
import { formatoFecha, formatoFechaHora, formatoNumero } from '@/utils/formato'
import Modal from '@/components/ui/Modal.vue'
import Cargando from '@/components/ui/Cargando.vue'
import EstadoVacio from '@/components/ui/EstadoVacio.vue'
import EstadoTramite from '@/components/ui/EstadoTramite.vue'
import RielEstado from '@/components/ui/RielEstado.vue'
import EncabezadoImpresion from '@/components/ui/EncabezadoImpresion.vue'
import VisorInforme from '@/components/tramites/VisorInforme.vue'
import CadenaPrecedentes from '@/components/consulta/CadenaPrecedentes.vue'

const props = defineProps({ id: { type: String, required: true } })
const router = useRouter()
const catalogos = useCatalogos()

const codigo = (t) => t?.numero_documento || t?.hoja_ruta || 'Sin código'
const vacio = (v) => (v === null || v === undefined || v === '' ? '—' : v)

// ---------- Carga ----------
const tramite = ref(null)
const cargando = ref(true)
const error = ref('')
const noExiste = ref(false)
const similares = ref([])
const cargandoSimilares = ref(false)

async function cargarTramite({ silencioso = false } = {}) {
  if (!silencioso) cargando.value = true
  error.value = ''
  noExiste.value = false
  try {
    tramite.value = await api.tramites.obtener(props.id)
  } catch (e) {
    noExiste.value = e.estado === 404
    error.value = e.message || 'No se pudo cargar el trámite.'
    if (!silencioso) tramite.value = null
  } finally {
    cargando.value = false
  }
}
async function cargarSimilares() {
  cargandoSimilares.value = true
  try { similares.value = await api.tramites.similares(props.id) } catch { similares.value = [] } finally { cargandoSimilares.value = false }
}
watch(() => props.id, () => { cargarTramite(); cargarSimilares() }, { immediate: true })

const t = computed(() => tramite.value)
const permisos = computed(() => t.value?.permisos || {})

// ---------- Informe ----------
const visorAbierto = ref(false)
const quienSubeInforme = computed(() => {
  if (!t.value) return ''
  if (t.value.origen_registro === 'MIGRACION') return 'Registro histórico migrado del Excel: no tiene informe digital adjunto.'
  if (t.value.profesional) return `Lo sube ${t.value.profesional.nombre_completo}, el abogado asignado, al concluir el trámite.`
  return 'Primero se asigna un abogado; el abogado asignado sube el informe al concluir el trámite.'
})
const tamano = (bytes) => (bytes ? `${formatoNumero(Math.round((bytes / 1048576) * 10) / 10)} MB` : '')

// ---------- Asignar ----------
const asignarAbierto = ref(false)
const profesionalElegido = ref('')
const profesionales = ref([])
const envioAsignar = useEnvio()
async function abrirAsignar() {
  profesionalElegido.value = t.value.profesional?.id ? String(t.value.profesional.id) : ''
  asignarAbierto.value = true
  try {
    const lista = await catalogos.obtener('profesionales')
    profesionales.value = lista.filter((p) => p.activo && p.usuario_id != null)
  } catch { profesionales.value = [] }
}
async function asignar() {
  if (!profesionalElegido.value) { envioAsignar.errores.value = { profesional_id: 'Elija un abogado.' }; return }
  try {
    tramite.value = await envioAsignar.enviar(() => api.tramites.asignar(props.id, Number(profesionalElegido.value)), 'Abogado asignado')
    asignarAbierto.value = false
  } catch { /* el aviso ya se mostró */ }
}

// ---------- Archivar ----------
const archivarAbierto = ref(false)
const envioArchivar = useEnvio()
async function archivar() {
  try {
    tramite.value = await envioArchivar.enviar(() => api.tramites.archivar(props.id), 'Trámite archivado')
    archivarAbierto.value = false
  } catch { /* aviso mostrado */ }
}

// ---------- Baja ----------
const bajaAbierto = ref(false)
const motivoBaja = ref('')
const envioBaja = useEnvio()
function abrirBaja() { motivoBaja.value = ''; envioBaja.errores.value = {}; bajaAbierto.value = true }
async function darDeBaja() {
  if (!motivoBaja.value.trim()) { envioBaja.errores.value = { motivo: 'Indique el motivo de la baja.' }; return }
  try {
    await envioBaja.enviar(() => api.tramites.darDeBaja(props.id, motivoBaja.value.trim()), 'Trámite dado de baja')
    bajaAbierto.value = false
    router.push('/consulta')
  } catch { /* aviso mostrado */ }
}

// ---------- Imprimir ----------
function imprimir() {
  imprimirConAuditoria({ expediente: props.id, codigo: codigo(t.value), cantidad: t.value?.precedentes?.length ?? 0 }, 'TRAMITES')
}

// ---------- Precedentes ----------
const vincularAbierto = ref(false)
const busqueda = ref('')
const candidatos = ref([])
const buscandoCandidatos = ref(false)
const seleccion = ref(null)
const formPrecedente = reactive({ criterio_legal: '', relevancia: 'ORIENTADOR', tipo_relacion: 'APLICA', observaciones: '' })
const envioPrecedente = useEnvio()

const vinculados = computed(() => new Set((t.value?.precedentes || []).map((p) => p.tramite?.id)))
const sugerencias = computed(() => similares.value.filter((s) => !vinculados.value.has(s.tramite.id)))
const candidatosFiltrados = computed(() => candidatos.value.filter((c) => c.id !== props.id && !vinculados.value.has(c.id)))

function abrirVincular() {
  Object.assign(formPrecedente, { criterio_legal: '', relevancia: 'ORIENTADOR', tipo_relacion: 'APLICA', observaciones: '' })
  busqueda.value = ''
  candidatos.value = []
  seleccion.value = null
  envioPrecedente.errores.value = {}
  vincularAbierto.value = true
}
let esperaBusqueda = null
let turnoBusqueda = 0
watch(busqueda, (v) => {
  clearTimeout(esperaBusqueda)
  const texto = v.trim()
  if (texto.length < 2) { candidatos.value = []; buscandoCandidatos.value = false; return }
  buscandoCandidatos.value = true
  esperaBusqueda = setTimeout(async () => {
    const mio = ++turnoBusqueda
    try {
      const r = await api.tramites.buscar({ q: texto, por_pagina: 8, auditar: false })
      if (mio === turnoBusqueda) candidatos.value = r.items
    } catch { if (mio === turnoBusqueda) candidatos.value = [] } finally { if (mio === turnoBusqueda) buscandoCandidatos.value = false }
  }, 300)
})
function elegir(x, afinidad = null) {
  seleccion.value = { id: x.id, codigo: codigo(x), asunto: x.asunto, afinidad }
}
async function guardarPrecedente() {
  const campos = {}
  if (!seleccion.value) campos.tramite_precedente_id = 'Elija el trámite precedente.'
  if (!formPrecedente.criterio_legal.trim()) campos.criterio_legal = 'Escriba el criterio legal.'
  if (Object.keys(campos).length) { envioPrecedente.errores.value = campos; return }
  try {
    await envioPrecedente.enviar(() => api.precedentes.crear(props.id, {
      tramite_precedente_id: seleccion.value.id,
      criterio_legal: formPrecedente.criterio_legal.trim(),
      relevancia: formPrecedente.relevancia,
      tipo_relacion: formPrecedente.tipo_relacion,
      observaciones: formPrecedente.observaciones.trim() || null
    }), 'Precedente vinculado')
    vincularAbierto.value = false
    cargarTramite({ silencioso: true })
  } catch { /* aviso mostrado */ }
}

const precedenteAEliminar = ref(null)
const eliminarAbierto = computed({ get: () => !!precedenteAEliminar.value, set: (v) => { if (!v) precedenteAEliminar.value = null } })
const envioEliminar = useEnvio()
async function eliminarPrecedente() {
  try {
    await envioEliminar.enviar(() => api.precedentes.eliminar(precedenteAEliminar.value.id), 'Precedente desvinculado')
    precedenteAEliminar.value = null
    cargarTramite({ silencioso: true })
  } catch { /* aviso mostrado */ }
}

// ---------- Historial ----------
const ACCIONES_HISTORIAL = {
  CREAR_TRAMITE: 'Trámite registrado',
  EDITAR_TRAMITE: 'Datos editados',
  ASIGNAR_TRAMITE: 'Abogado asignado',
  SUBIR_INFORME: 'Informe subido',
  ARCHIVAR_TRAMITE: 'Trámite archivado',
  BAJA_TRAMITE: 'Trámite dado de baja'
}
function detalleHistorial(h) {
  const d = h.detalle || {}
  if (h.accion === 'ASIGNAR_TRAMITE' && d.profesional) return d.profesional
  if (h.accion === 'SUBIR_INFORME') return [d.archivo, d.version ? `versión ${d.version}` : ''].filter(Boolean).join(' · ')
  if (h.accion === 'BAJA_TRAMITE' && d.motivo) return `Motivo: ${d.motivo}`
  return ''
}
</script>

<template>
  <div class="pagina">
    <Cargando v-if="cargando" texto="Cargando el expediente…" />

    <div v-else-if="!t" class="panel">
      <EstadoVacio :icono="FileX" :titulo="noExiste ? 'No encontramos este trámite' : 'No se pudo cargar el trámite'"
        :texto="noExiste ? 'Puede que el enlace sea incorrecto o que el trámite haya sido dado de baja.' : error">
        <RouterLink to="/consulta" class="boton boton-primario"><Search aria-hidden="true" /> Ir a la búsqueda</RouterLink>
        <button v-if="!noExiste" type="button" class="boton" @click="cargarTramite()">Reintentar</button>
      </EstadoVacio>
    </div>

    <template v-else>
      <EncabezadoImpresion titulo="Expediente del trámite" :criterio="codigo(t)" />

      <RouterLink to="/consulta" class="volver no-imprimir"><ArrowLeft aria-hidden="true" /> Búsqueda</RouterLink>

      <header class="cabecera">
        <div class="fila">
          <span class="codigo codigo-sello">{{ codigo(t) }}</span>
          <EstadoTramite :estado="t.estado_tramite" />
          <span v-if="t.origen_registro === 'MIGRACION'" class="insignia insignia-sin-punto" title="Registro migrado del Excel histórico">Histórico</span>
          <span v-if="!t.activo" class="insignia insignia-peligro">Dado de baja</span>
        </div>
        <h1 class="asunto">{{ t.asunto || 'Sin asunto registrado' }}</h1>
        <div class="pagina-acciones no-imprimir">
          <RouterLink v-if="permisos.concluir" :to="`/tramites/${t.id}/concluir`" class="boton boton-primario">
            <FileUp aria-hidden="true" /> {{ t.estado_tramite === 'CONCLUIDO' ? 'Subir nueva versión' : 'Concluir' }}
          </RouterLink>
          <RouterLink v-if="permisos.editar" :to="`/tramites/${t.id}/editar`" class="boton"><Pencil aria-hidden="true" /> Editar</RouterLink>
          <button v-if="permisos.asignar" type="button" class="boton" @click="abrirAsignar">
            <UserPlus aria-hidden="true" /> {{ t.profesional ? 'Reasignar' : 'Asignar abogado' }}
          </button>
          <button v-if="permisos.archivar" type="button" class="boton" @click="archivarAbierto = true"><Archive aria-hidden="true" /> Archivar</button>
          <RouterLink v-if="t.tipo_documento" :to="{ path: '/prompts', query: { tipo_documento_id: t.tipo_documento.id } }" class="boton">
            <Sparkles aria-hidden="true" /> Usar un prompt
          </RouterLink>
          <button type="button" class="boton" @click="imprimir"><Printer aria-hidden="true" /> Imprimir expediente</button>
          <button v-if="permisos.baja" type="button" class="boton boton-peligro" @click="abrirBaja"><Trash2 aria-hidden="true" /> Dar de baja</button>
        </div>
      </header>

      <p v-if="error" class="mensaje mensaje-peligro no-imprimir" role="alert">{{ error }}</p>

      <section class="panel riel-panel no-imprimir" aria-label="Recorrido del trámite">
        <div class="panel-cuerpo"><RielEstado :tramite="t" /></div>
      </section>

      <div class="detalle">
        <div class="principal">
          <section class="panel" aria-labelledby="titulo-datos">
            <div class="panel-cabecera"><h2 id="titulo-datos">Datos del registro</h2></div>
            <div class="panel-cuerpo">
              <dl class="datos">
                <div><dt>Hoja de ruta</dt><dd class="codigo">{{ vacio(t.hoja_ruta) }}</dd></div>
                <div><dt>Registro interno</dt><dd>{{ vacio(t.registro_interno) }}</dd></div>
                <div><dt>Año de gestión</dt><dd>{{ vacio(t.anio_gestion) }}</dd></div>
                <div><dt>Procedencia</dt><dd>{{ vacio(t.procedencia?.nombre) }}</dd></div>
                <div class="ancho"><dt>Entidad</dt><dd>{{ vacio(t.entidad?.nombre) }}</dd></div>
                <div><dt>Tipo de trámite</dt><dd>{{ vacio(t.tipo_tramite?.nombre) }}</dd></div>
                <div><dt>Área o unidad</dt><dd>{{ vacio(t.area?.nombre) }}</dd></div>
                <div><dt>Abogado</dt><dd>{{ t.profesional?.nombre_completo || 'Sin asignar' }}</dd></div>
                <div>
                  <dt>Asignado por</dt>
                  <dd>
                    <template v-if="t.asignado_por">{{ t.asignado_por.nombre_completo }} <span class="texto-3 normal">· {{ formatoFecha(t.fecha_asignacion) }}</span></template>
                    <template v-else>—</template>
                  </dd>
                </div>
                <div class="ancho"><dt>Observaciones</dt><dd class="normal">{{ vacio(t.observaciones) }}</dd></div>
              </dl>
              <hr class="separador" />
              <h3 class="subtitulo">Respuesta</h3>
              <dl class="datos">
                <div><dt>Tipo de documento</dt><dd>{{ vacio(t.tipo_documento?.nombre) }}</dd></div>
                <div><dt>Número de documento</dt><dd class="codigo">{{ vacio(t.numero_documento) }}</dd></div>
                <div><dt>Fecha de salida</dt><dd>{{ formatoFecha(t.fecha_salida) }}</dd></div>
                <div><dt>Registrado</dt><dd>{{ formatoFecha(t.creado_en) }}<span v-if="t.creado_por" class="texto-3 normal"> · {{ t.creado_por.nombre_completo }}</span></dd></div>
              </dl>
            </div>
          </section>

          <section class="panel" aria-labelledby="titulo-precedentes">
            <div class="panel-cabecera">
              <h2 id="titulo-precedentes">Precedentes y criterios legales</h2>
              <button v-if="permisos.precedentes" type="button" class="boton boton-pequeno no-imprimir" @click="abrirVincular">
                <Plus aria-hidden="true" /> Vincular precedente
              </button>
            </div>
            <div class="panel-cuerpo">
              <p v-if="!t.precedentes?.length" class="texto-3 texto-pequeno">
                Este trámite no tiene precedentes vinculados.<template v-if="permisos.precedentes"> Use «Vincular precedente» para citar un trámite anterior y su criterio legal.</template>
              </p>
              <ol v-else class="precedentes">
                <li v-for="p in t.precedentes" :key="p.id" class="precedente">
                  <div class="fila-entre">
                    <span class="fila">
                      <RouterLink v-if="p.tramite" :to="`/tramites/${p.tramite.id}`" class="codigo codigo-sello enlace-codigo">{{ codigo(p.tramite) }}</RouterLink>
                      <span class="insignia" :class="{ 'insignia-info': p.relevancia === 'VINCULANTE' }">{{ RELEVANCIAS[p.relevancia] || p.relevancia }}</span>
                      <span class="insignia insignia-sin-punto">{{ TIPOS_RELACION[p.tipo_relacion] || p.tipo_relacion }}</span>
                    </span>
                    <button v-if="permisos.precedentes" type="button" class="boton boton-pequeno boton-fantasma quitar no-imprimir"
                      :aria-label="`Desvincular el precedente ${codigo(p.tramite)}`" @click="precedenteAEliminar = p">
                      <Trash2 aria-hidden="true" /> Desvincular
                    </button>
                  </div>
                  <p v-if="p.tramite?.asunto" class="texto-pequeno texto-2 precedente-asunto">{{ p.tramite.asunto }}</p>
                  <blockquote class="criterio">{{ p.criterio_legal }}</blockquote>
                  <p v-if="p.observaciones" class="texto-pequeno"><span class="texto-3">Observaciones:</span> {{ p.observaciones }}</p>
                  <p class="texto-xs texto-3">Vinculado por {{ p.creado_por?.nombre_completo || 'el sistema' }} el {{ formatoFecha(p.creado_en) }}</p>
                </li>
              </ol>

              <template v-if="t.citado_por?.length">
                <hr class="separador" />
                <h3 class="subtitulo">Citado por</h3>
                <ul class="citado">
                  <li v-for="p in t.citado_por" :key="p.id">
                    <span class="fila">
                      <RouterLink v-if="p.tramite" :to="`/tramites/${p.tramite.id}`" class="codigo codigo-sello enlace-codigo">{{ codigo(p.tramite) }}</RouterLink>
                      <span class="insignia" :class="{ 'insignia-info': p.relevancia === 'VINCULANTE' }">{{ RELEVANCIAS[p.relevancia] || p.relevancia }}</span>
                      <span class="texto-xs texto-3">{{ formatoFecha(p.creado_en) }}</span>
                    </span>
                    <p class="texto-pequeno texto-2 citado-criterio">{{ p.criterio_legal }}</p>
                  </li>
                </ul>
              </template>
            </div>
          </section>

          <section class="panel no-imprimir" aria-labelledby="titulo-cadena">
            <div class="panel-cabecera"><h2 id="titulo-cadena">Cadena de precedentes</h2></div>
            <div class="panel-cuerpo"><CadenaPrecedentes :tramite="t" /></div>
          </section>

          <section class="panel no-imprimir" aria-labelledby="titulo-historial">
            <div class="panel-cabecera"><h2 id="titulo-historial">Historial</h2></div>
            <div class="panel-cuerpo">
              <p v-if="!t.historial?.length" class="texto-3 texto-pequeno">
                Sin movimientos registrados en el sistema<template v-if="t.origen_registro === 'MIGRACION'"> (registro migrado del Excel histórico)</template>.
              </p>
              <ol v-else class="historial">
                <li v-for="(h, i) in t.historial" :key="i">
                  <span class="punto" aria-hidden="true" />
                  <div>
                    <strong class="texto-pequeno">{{ ACCIONES_HISTORIAL[h.accion] || h.accion }}</strong>
                    <p v-if="detalleHistorial(h)" class="texto-pequeno texto-2">{{ detalleHistorial(h) }}</p>
                    <p class="texto-xs texto-3">{{ formatoFechaHora(h.fecha) }} · {{ h.usuario }}</p>
                  </div>
                </li>
              </ol>
            </div>
          </section>
        </div>

        <aside class="lateral no-imprimir">
          <section class="panel" aria-labelledby="titulo-informe">
            <div class="panel-cabecera"><h2 id="titulo-informe">Informe</h2></div>
            <div class="panel-cuerpo">
              <template v-if="t.informe">
                <p class="informe-nombre">{{ t.informe.nombre_original }}</p>
                <dl class="informe-datos texto-pequeno">
                  <div><dt>Páginas</dt><dd>{{ t.informe.paginas }}</dd></div>
                  <div><dt>Versión</dt><dd>{{ t.informe.versiones }}</dd></div>
                  <div v-if="t.informe.tamano_bytes"><dt>Tamaño</dt><dd>{{ tamano(t.informe.tamano_bytes) }}</dd></div>
                  <div><dt>Subido</dt><dd>{{ t.informe.subido_por?.nombre_completo || '—' }} · {{ formatoFecha(t.informe.subido_en) }}</dd></div>
                </dl>
                <div class="informe-acciones">
                  <button type="button" class="boton boton-primario" @click="visorAbierto = true"><Eye aria-hidden="true" /> Ver informe</button>
                  <button v-if="permisos.descargar" type="button" class="boton" @click="descargarInforme(t)"><Download aria-hidden="true" /> Descargar PDF</button>
                </div>
              </template>
              <template v-else>
                <p class="texto-pequeno"><strong>Aún no hay informe.</strong></p>
                <p class="texto-pequeno texto-2">{{ quienSubeInforme }}</p>
              </template>
            </div>
          </section>

          <section class="panel" aria-labelledby="titulo-similares">
            <div class="panel-cabecera"><h2 id="titulo-similares">Trámites similares</h2></div>
            <div class="panel-cuerpo">
              <Cargando v-if="cargandoSimilares && !similares.length" texto="Buscando similares…" />
              <p v-else-if="!similares.length" class="texto-3 texto-pequeno">No hay trámites con un asunto parecido.</p>
              <ul v-else class="similares">
                <li v-for="s in similares" :key="s.tramite.id">
                  <div class="fila-entre">
                    <RouterLink :to="`/tramites/${s.tramite.id}`" class="codigo enlace-similar">{{ codigo(s.tramite) }}</RouterLink>
                    <span class="afinidad" :title="`Afinidad del asunto: ${s.afinidad} %`">{{ s.afinidad }} %</span>
                  </div>
                  <p class="texto-xs texto-2 recorte">{{ s.tramite.asunto }}</p>
                </li>
              </ul>
            </div>
          </section>
        </aside>
      </div>

      <!-- Modales -->
      <VisorInforme v-if="t.informe" v-model="visorAbierto" :tramite="t" />

      <Modal v-model="asignarAbierto" :titulo="t.profesional ? 'Reasignar abogado' : 'Asignar abogado'">
        <form id="form-asignar" class="formulario" @submit.prevent="asignar">
          <div class="campo">
            <label for="asignar-profesional">Abogado<span class="requerido" aria-hidden="true">*</span></label>
            <select id="asignar-profesional" v-model="profesionalElegido" class="seleccion" :aria-invalid="!!envioAsignar.errores.value.profesional_id">
              <option value="" disabled>Elija un abogado</option>
              <option v-for="p in profesionales" :key="p.id" :value="String(p.id)">{{ p.nombre }}</option>
            </select>
            <p v-if="envioAsignar.errores.value.profesional_id" class="error-campo">{{ envioAsignar.errores.value.profesional_id }}</p>
            <p v-else class="ayuda">Solo aparecen abogados con cuenta activa en el sistema. El trámite pasa a «En elaboración».</p>
          </div>
        </form>
        <template #pie>
          <button type="button" class="boton" @click="asignarAbierto = false">Cancelar</button>
          <button type="submit" form="form-asignar" class="boton boton-primario" :disabled="envioAsignar.enviando.value">
            {{ envioAsignar.enviando.value ? 'Guardando…' : 'Asignar' }}
          </button>
        </template>
      </Modal>

      <Modal v-model="archivarAbierto" titulo="Archivar trámite" ancho="480px">
        <p>¿Archivar el trámite <span class="codigo">{{ codigo(t) }}</span>? El archivo es el cierre definitivo y ya no se podrán subir nuevas versiones del informe.</p>
        <template #pie>
          <button type="button" class="boton" @click="archivarAbierto = false">Cancelar</button>
          <button type="button" class="boton boton-primario" :disabled="envioArchivar.enviando.value" @click="archivar">
            {{ envioArchivar.enviando.value ? 'Archivando…' : 'Archivar' }}
          </button>
        </template>
      </Modal>

      <Modal v-model="bajaAbierto" titulo="Dar de baja el trámite" ancho="520px">
        <form id="form-baja" class="formulario" @submit.prevent="darDeBaja">
          <p class="mensaje mensaje-aviso">El trámite dejará de aparecer en las búsquedas. No se borra: queda en la base de datos y en la auditoría.</p>
          <div class="campo">
            <label for="baja-motivo">Motivo de la baja<span class="requerido" aria-hidden="true">*</span></label>
            <textarea id="baja-motivo" v-model="motivoBaja" class="area-texto" maxlength="500" :aria-invalid="!!envioBaja.errores.value.motivo"
              aria-describedby="baja-motivo-ayuda" />
            <p v-if="envioBaja.errores.value.motivo" id="baja-motivo-ayuda" class="error-campo">{{ envioBaja.errores.value.motivo }}</p>
            <p v-else id="baja-motivo-ayuda" class="ayuda">Por ejemplo: registro duplicado de la hoja de ruta CGE/GSL/INF-006/2026.</p>
          </div>
        </form>
        <template #pie>
          <button type="button" class="boton" @click="bajaAbierto = false">Cancelar</button>
          <button type="submit" form="form-baja" class="boton boton-peligro" :disabled="envioBaja.enviando.value">
            {{ envioBaja.enviando.value ? 'Procesando…' : 'Dar de baja' }}
          </button>
        </template>
      </Modal>

      <Modal v-model="eliminarAbierto" titulo="Desvincular precedente" ancho="480px">
        <p v-if="precedenteAEliminar">
          ¿Desvincular <span class="codigo">{{ codigo(precedenteAEliminar.tramite) }}</span> de este trámite? Se pierde el criterio legal registrado en el vínculo; los trámites no cambian.
        </p>
        <template #pie>
          <button type="button" class="boton" @click="precedenteAEliminar = null">Cancelar</button>
          <button type="button" class="boton boton-peligro" :disabled="envioEliminar.enviando.value" @click="eliminarPrecedente">
            {{ envioEliminar.enviando.value ? 'Desvinculando…' : 'Desvincular' }}
          </button>
        </template>
      </Modal>

      <Modal v-model="vincularAbierto" titulo="Vincular precedente" ancho="720px">
        <form id="form-precedente" class="formulario" @submit.prevent="guardarPrecedente">
          <div class="campo">
            <label for="precedente-buscar">Trámite precedente<span class="requerido" aria-hidden="true">*</span></label>
            <div v-if="seleccion" class="seleccionado">
              <span class="codigo codigo-sello">{{ seleccion.codigo }}</span>
              <span class="texto-pequeno texto-2 recorte">{{ seleccion.asunto }}</span>
              <button type="button" class="boton boton-pequeno" @click="seleccion = null">Cambiar</button>
            </div>
            <template v-else>
              <input id="precedente-buscar" v-model="busqueda" type="search" class="entrada" autocomplete="off"
                placeholder="Busque por número de documento, hoja de ruta, entidad o asunto"
                :aria-invalid="!!envioPrecedente.errores.value.tramite_precedente_id" aria-describedby="precedente-buscar-ayuda" />
              <p v-if="envioPrecedente.errores.value.tramite_precedente_id" id="precedente-buscar-ayuda" class="error-campo">{{ envioPrecedente.errores.value.tramite_precedente_id }}</p>
              <p v-else id="precedente-buscar-ayuda" class="ayuda">Escriba al menos 2 letras o elija una sugerencia.</p>

              <div class="candidatos" aria-live="polite">
                <p v-if="buscandoCandidatos" class="texto-xs texto-3">Buscando…</p>
                <template v-else-if="busqueda.trim().length >= 2">
                  <p v-if="!candidatosFiltrados.length" class="texto-xs texto-3">Sin resultados para «{{ busqueda.trim() }}».</p>
                  <ul v-else class="opciones">
                    <li v-for="c in candidatosFiltrados" :key="c.id">
                      <button type="button" class="opcion" @click="elegir(c)">
                        <span class="codigo">{{ codigo(c) }}</span>
                        <span class="texto-xs texto-2 recorte">{{ c.asunto }}</span>
                      </button>
                    </li>
                  </ul>
                </template>
                <template v-if="sugerencias.length && busqueda.trim().length < 2">
                  <p class="etiqueta sugerencias-titulo">Sugerencias por asunto parecido</p>
                  <ul class="opciones">
                    <li v-for="s in sugerencias" :key="s.tramite.id">
                      <button type="button" class="opcion" @click="elegir(s.tramite, s.afinidad)">
                        <span class="fila-entre"><span class="codigo">{{ codigo(s.tramite) }}</span><span class="afinidad">{{ s.afinidad }} %</span></span>
                        <span class="texto-xs texto-2 recorte">{{ s.tramite.asunto }}</span>
                      </button>
                    </li>
                  </ul>
                </template>
              </div>
            </template>
          </div>

          <div class="campo">
            <label for="precedente-criterio">Criterio legal citado<span class="requerido" aria-hidden="true">*</span></label>
            <textarea id="precedente-criterio" v-model="formPrecedente.criterio_legal" class="area-texto" maxlength="2000"
              :aria-invalid="!!envioPrecedente.errores.value.criterio_legal" aria-describedby="precedente-criterio-ayuda" />
            <p v-if="envioPrecedente.errores.value.criterio_legal" id="precedente-criterio-ayuda" class="error-campo">{{ envioPrecedente.errores.value.criterio_legal }}</p>
            <p v-else id="precedente-criterio-ayuda" class="ayuda">El razonamiento del precedente que se aplica en este trámite.</p>
          </div>

          <div class="formulario-2">
            <div class="campo">
              <label for="precedente-relevancia">Relevancia</label>
              <select id="precedente-relevancia" v-model="formPrecedente.relevancia" class="seleccion" :aria-invalid="!!envioPrecedente.errores.value.relevancia">
                <option v-for="(etiqueta, clave) in RELEVANCIAS" :key="clave" :value="clave">{{ etiqueta }}</option>
              </select>
              <p v-if="envioPrecedente.errores.value.relevancia" class="error-campo">{{ envioPrecedente.errores.value.relevancia }}</p>
            </div>
            <div class="campo">
              <label for="precedente-relacion">Tipo de relación</label>
              <select id="precedente-relacion" v-model="formPrecedente.tipo_relacion" class="seleccion">
                <option v-for="(etiqueta, clave) in TIPOS_RELACION" :key="clave" :value="clave">{{ etiqueta }}</option>
              </select>
            </div>
          </div>

          <div class="campo">
            <label for="precedente-observaciones">Observaciones <span class="opcional">(opcional)</span></label>
            <textarea id="precedente-observaciones" v-model="formPrecedente.observaciones" class="area-texto observaciones" maxlength="1000" />
          </div>
        </form>
        <template #pie>
          <button type="button" class="boton" @click="vincularAbierto = false">Cancelar</button>
          <button type="submit" form="form-precedente" class="boton boton-primario" :disabled="envioPrecedente.enviando.value">
            <Link2 aria-hidden="true" /> {{ envioPrecedente.enviando.value ? 'Vinculando…' : 'Vincular' }}
          </button>
        </template>
      </Modal>
    </template>
  </div>
</template>

<style scoped>
.volver { display: inline-flex; align-items: center; gap: 4px; font-size: var(--t-sm); font-weight: 600; margin-bottom: var(--e-4); }
.volver svg { width: 16px; height: 16px; }

.cabecera { margin-bottom: var(--e-6); }
.cabecera .asunto { font-size: var(--t-xl); margin: var(--e-3) 0 var(--e-4); max-width: 80ch; overflow-wrap: anywhere; }
.cabecera .mensaje { margin-top: var(--e-4); }
.riel-panel { margin-bottom: var(--e-6); }

.detalle { display: grid; grid-template-columns: minmax(0, 1fr) 320px; gap: var(--e-6); align-items: start; }
.lateral > .panel + .panel { margin-top: var(--e-6); }

.subtitulo { font-size: var(--t-sm); color: var(--texto-2); margin-bottom: var(--e-3); }
.normal { font-weight: 400; }

/* Precedentes */
.precedentes { list-style: none; margin: 0; padding: 0; }
.precedente + .precedente { border-top: 1px solid var(--linea); margin-top: var(--e-5); padding-top: var(--e-5); }
.precedente > * + * { margin-top: var(--e-2); }
.enlace-codigo { text-decoration: none; max-width: 100%; overflow: hidden; text-overflow: ellipsis; }
.enlace-codigo:hover { background: var(--sello-suave); text-decoration: none; }
.precedente-asunto { max-width: 80ch; }
.criterio {
  margin: var(--e-3) 0 0; padding: var(--e-3) var(--e-4); border-left: 3px solid var(--sello);
  background: var(--superficie-2); font-family: var(--fuente-titulo); font-style: italic; line-height: 1.55; overflow-wrap: anywhere;
}
.quitar { color: var(--peligro); }
.quitar:hover { background: var(--peligro-suave); }
.citado { list-style: none; margin: 0; padding: 0; }
.citado li + li { border-top: 1px solid var(--linea); margin-top: var(--e-3); padding-top: var(--e-3); }
.citado-criterio { margin-top: var(--e-1); }

/* Historial */
.historial { list-style: none; margin: 0; padding: 0; position: relative; }
.historial li { display: grid; grid-template-columns: 14px minmax(0, 1fr); gap: var(--e-3); position: relative; padding-bottom: var(--e-4); }
.historial li:last-child { padding-bottom: 0; }
.historial li:not(:last-child)::before { content: ''; position: absolute; left: 6px; top: 16px; bottom: 0; width: 2px; background: var(--linea); }
.punto { width: 14px; height: 14px; border-radius: 50%; border: 2px solid var(--tinta); background: var(--superficie); margin-top: 3px; }

/* Lateral */
.informe-nombre { font-weight: 650; overflow-wrap: anywhere; margin-bottom: var(--e-3); }
.informe-datos { margin: 0 0 var(--e-4); display: grid; gap: var(--e-1); }
.informe-datos div { display: flex; justify-content: space-between; gap: var(--e-3); }
.informe-datos dt { color: var(--texto-3); }
.informe-datos dd { margin: 0; text-align: right; }
.informe-acciones { display: grid; gap: var(--e-2); }
.similares { list-style: none; margin: 0; padding: 0; }
.similares li + li { border-top: 1px solid var(--linea); margin-top: var(--e-3); padding-top: var(--e-3); }
.enlace-similar { font-size: var(--t-sm); color: var(--sello); overflow: hidden; text-overflow: ellipsis; min-width: 0; }
.afinidad { font-size: var(--t-xs); font-weight: 650; color: var(--sello); background: var(--sello-suave); border-radius: 999px; padding: 1px 8px; white-space: nowrap; }
.recorte { display: -webkit-box; -webkit-line-clamp: 2; line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }

/* Modal de precedente */
.seleccionado { display: flex; align-items: center; gap: var(--e-3); flex-wrap: wrap; padding: var(--e-3); border: 1px solid var(--linea); border-radius: var(--radio-control); background: var(--superficie-2); }
.seleccionado .recorte { flex: 1; min-width: 160px; }
.candidatos { margin-top: var(--e-2); }
.sugerencias-titulo { display: block; margin: var(--e-2) 0; }
.opciones { list-style: none; margin: 0; padding: 0; border: 1px solid var(--linea); border-radius: var(--radio-control); max-height: 240px; overflow-y: auto; }
.opciones li + li { border-top: 1px solid var(--linea); }
.opcion { display: flex; flex-direction: column; gap: 2px; width: 100%; text-align: left; padding: var(--e-2) var(--e-3); border: none; background: var(--superficie); cursor: pointer; }
.opcion:hover { background: var(--sello-suave); }
.opcion .codigo { white-space: normal; overflow-wrap: anywhere; }
.observaciones { min-height: 64px; }

@media (max-width: 960px) {
  .detalle { grid-template-columns: 1fr; }
}
@media print {
  .detalle { display: block; }
  .principal > .panel + .panel { margin-top: 10pt; }
  .criterio { background: none; border-left-color: #000; }
}
</style>

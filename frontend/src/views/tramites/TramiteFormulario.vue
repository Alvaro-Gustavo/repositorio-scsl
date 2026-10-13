<script setup>
// Registro (sin id) y edicion (con id) de un tramite.
// Registro optimizado: 7 campos principales; area y observaciones en "Mas datos".
// En edicion la asignacion no se cambia aqui (se reasigna desde el expediente).
import { ref, computed, onMounted, nextTick, useId } from 'vue'
import { useRouter, RouterLink } from 'vue-router'
import { CircleCheck, Lock, Save, Plus, Eye } from '@lucide/vue'
import { api } from '@/api'
import { useSesion } from '@/stores/sesion'
import { useCatalogos } from '@/stores/catalogos'
import { useEnvio } from '@/composables/utiles'
import { formatoFecha } from '@/utils/formato'
import CampoCatalogo from '@/components/ui/CampoCatalogo.vue'
import EstadoTramite from '@/components/ui/EstadoTramite.vue'
import Cargando from '@/components/ui/Cargando.vue'

const props = defineProps({ id: { type: String, default: null } })

const router = useRouter()
const sesion = useSesion()
const catalogos = useCatalogos()
const { errores, enviando, enviar } = useEnvio()
const uid = useId()

const esEdicion = computed(() => !!props.id)
const tramite = ref(null)
const cargando = ref(false)
const errorCarga = ref('')
const creado = ref(null)
const masDatos = ref(false)
const maxAsunto = ref(500)
const campoHojaRuta = ref(null)

const vacio = () => ({
  hoja_ruta: '', registro_interno: '', procedencia_id: null, entidad_id: null, tipo_tramite_id: null,
  asunto: '', profesional_id: '', area_id: null, observaciones: '',
  tipo_documento_id: '', numero_documento: '', fecha_salida: ''
})
const form = ref(vacio())

const procedencias = computed(() => catalogos.datos.procedencias || [])
const tiposDocumento = computed(() => catalogos.datos.tipos_documento || [])
const abogados = computed(() => (catalogos.datos.profesionales || []).filter((p) => p.usuario_id && p.activo))
const puedeAsignar = computed(() => sesion.puede('ASIGNAR_TRAMITE'))
const anioGestion = computed(() => (esEdicion.value ? tramite.value?.anio_gestion : new Date().getFullYear()))
const conRespuesta = computed(() => esEdicion.value && ['CONCLUIDO', 'ARCHIVADO'].includes(tramite.value?.estado_tramite))
const puedeEditar = computed(() => !esEdicion.value || !!tramite.value?.permisos?.editar)
const largoAsunto = computed(() => form.value.asunto.length)

onMounted(async () => {
  catalogos.varios(['procedencias', 'tipos_documento', 'profesionales']).catch(() => {})
  api.configuracion.listar().then((lista) => {
    const v = Number(lista.find((c) => c.clave === 'asunto_max_caracteres')?.valor)
    if (v > 0) maxAsunto.value = v
  }).catch(() => {})
  if (esEdicion.value) await cargarTramite()
  else focoInicial()
})

async function cargarTramite() {
  cargando.value = true
  errorCarga.value = ''
  try {
    const t = await api.tramites.obtener(props.id)
    tramite.value = t
    form.value = {
      hoja_ruta: t.hoja_ruta || '', registro_interno: t.registro_interno || '',
      procedencia_id: t.procedencia?.id ?? null, entidad_id: t.entidad?.id ?? null, tipo_tramite_id: t.tipo_tramite?.id ?? null,
      asunto: t.asunto || '', profesional_id: t.profesional?.id ?? '', area_id: t.area?.id ?? null, observaciones: t.observaciones || '',
      tipo_documento_id: t.tipo_documento?.id ?? '', numero_documento: t.numero_documento || '', fecha_salida: t.fecha_salida || ''
    }
    masDatos.value = !!(t.area || t.observaciones)
  } catch (e) {
    errorCarga.value = e.message || 'No se pudo cargar el trámite.'
  } finally {
    cargando.value = false
  }
}

function focoInicial() {
  nextTick(() => campoHojaRuta.value?.focus())
}

function mayusculasHojaRuta() {
  form.value.hoja_ruta = form.value.hoja_ruta.trim().toUpperCase()
}

function datosEnvio() {
  const f = form.value
  const datos = {
    hoja_ruta: f.hoja_ruta.trim().toUpperCase(),
    registro_interno: f.registro_interno.trim() || null,
    procedencia_id: f.procedencia_id,
    entidad_id: f.entidad_id,
    tipo_tramite_id: f.tipo_tramite_id,
    asunto: f.asunto.trim(),
    area_id: f.area_id || null,
    observaciones: f.observaciones.trim() || null
  }
  if (!esEdicion.value && puedeAsignar.value && f.profesional_id) datos.profesional_id = Number(f.profesional_id)
  if (conRespuesta.value) {
    datos.tipo_documento_id = f.tipo_documento_id ? Number(f.tipo_documento_id) : null
    datos.numero_documento = f.numero_documento.trim().toUpperCase() || null
    datos.fecha_salida = f.fecha_salida || null
  }
  return datos
}

async function guardar() {
  if (enviando.value || !puedeEditar.value || creado.value) return
  const datos = datosEnvio()
  try {
    if (esEdicion.value) {
      await enviar(() => api.tramites.actualizar(props.id, datos), 'Cambios guardados.')
      router.push(`/tramites/${props.id}`)
    } else {
      creado.value = await enviar(() => api.tramites.crear(datos), 'Trámite registrado.')
    }
  } catch {
    // useEnvio ya muestra el mensaje y marca los campos con error
    if (errores.value.area_id || errores.value.observaciones) masDatos.value = true
  }
}

function registrarOtro() {
  const procedencia = form.value.procedencia_id
  form.value = { ...vacio(), procedencia_id: procedencia }
  errores.value = {}
  creado.value = null
  masDatos.value = false
  focoInicial()
}

function cancelar() {
  if (esEdicion.value) router.push(`/tramites/${props.id}`)
  else if (window.history.length > 1) router.back()
  else router.push('/')
}
</script>

<template>
  <div class="pagina">
    <header class="pagina-cabecera">
      <div>
        <h1>{{ esEdicion ? 'Editar trámite' : 'Registrar trámite' }}</h1>
        <p v-if="esEdicion">Corrija los datos del registro. Los cambios quedan en el historial del trámite.</p>
        <p v-else>Registre el trámite recibido. Puede asignar el abogado ahora o después desde «Por asignar».</p>
      </div>
      <div v-if="esEdicion && tramite" class="pagina-acciones">
        <RouterLink :to="`/tramites/${id}`" class="boton boton-fantasma">Volver al expediente</RouterLink>
      </div>
    </header>

    <Cargando v-if="cargando" texto="Cargando el trámite…" />
    <p v-else-if="errorCarga" class="mensaje mensaje-peligro" role="alert">{{ errorCarga }}</p>

    <div v-else-if="esEdicion && tramite && !puedeEditar" class="panel">
      <div class="panel-cuerpo">
        <div class="mensaje mensaje-aviso">
          <Lock aria-hidden="true" />
          <div>
            <strong>No puede editar este trámite.</strong>
            <p>Solo quien lo registró, el abogado asignado o la jefatura pueden corregir sus datos. Los trámites archivados no se editan.</p>
          </div>
        </div>
        <div class="formulario-acciones">
          <RouterLink :to="`/tramites/${id}`" class="boton">Ver el expediente</RouterLink>
        </div>
      </div>
    </div>

    <!-- Registro exitoso -->
    <section v-else-if="creado" class="panel" aria-labelledby="titulo-creado">
      <div class="panel-cuerpo creado">
        <CircleCheck class="creado-icono" aria-hidden="true" />
        <div class="creado-texto">
          <h2 id="titulo-creado">Trámite registrado</h2>
          <p class="fila">
            <span class="codigo codigo-sello">{{ creado.hoja_ruta }}</span>
            <EstadoTramite :estado="creado.estado_tramite" />
          </p>
          <p class="texto-2 texto-pequeno">
            <template v-if="creado.profesional">Asignado a {{ creado.profesional.nombre_completo }}. Ya figura en sus pendientes.</template>
            <template v-else>Queda en la lista «Por asignar» hasta que se designe un abogado.</template>
          </p>
          <div class="fila acciones-creado">
            <RouterLink :to="`/tramites/${creado.id}`" class="boton"><Eye aria-hidden="true" /> Ver trámite</RouterLink>
            <button type="button" class="boton boton-primario" @click="registrarOtro"><Plus aria-hidden="true" /> Registrar otro</button>
          </div>
        </div>
      </div>
    </section>

    <form v-else-if="!esEdicion || tramite" class="panel" novalidate @submit.prevent="guardar"
      @keydown.ctrl.enter.prevent="guardar" @keydown.meta.enter.prevent="guardar">
      <div class="panel-cabecera">
        <h2>Datos del trámite</h2>
        <span class="texto-pequeno texto-2">Gestión <strong class="codigo">{{ anioGestion }}</strong>
          <span class="texto-3"> · {{ esEdicion ? 'registrada por el sistema' : 'la asigna el sistema' }}</span></span>
      </div>
      <div class="panel-cuerpo">
        <p v-if="tramite?.origen_registro === 'MIGRACION'" class="mensaje mensaje-info bloque">
          Registro migrado del Excel histórico: algunos datos pueden estar vacíos y no son obligatorios para guardarlo.
        </p>

        <div class="formulario-2">
          <div class="campo">
            <label :for="`${uid}-hr`">Hoja de ruta<span class="requerido" aria-hidden="true">*</span></label>
            <input :id="`${uid}-hr`" ref="campoHojaRuta" v-model="form.hoja_ruta" class="entrada mayusculas" type="text"
              autocomplete="off" spellcheck="false" placeholder="CGE/GSL/INF-006/2026" aria-required="true"
              :aria-invalid="!!errores.hoja_ruta" :aria-describedby="`${uid}-hr-ayuda`" @blur="mayusculasHojaRuta" />
            <p v-if="errores.hoja_ruta" :id="`${uid}-hr-ayuda`" class="error-campo" role="alert">{{ errores.hoja_ruta }}</p>
            <p v-else :id="`${uid}-hr-ayuda`" class="ayuda">Se guarda en mayúsculas.</p>
          </div>

          <div class="campo">
            <label :for="`${uid}-ri`">Registro interno <span class="opcional">(opcional)</span></label>
            <input :id="`${uid}-ri`" v-model="form.registro_interno" class="entrada" type="text" autocomplete="off"
              spellcheck="false" placeholder="GAAJ/1572" :aria-invalid="!!errores.registro_interno" />
            <p v-if="errores.registro_interno" class="error-campo" role="alert">{{ errores.registro_interno }}</p>
          </div>

          <fieldset class="campo campo-ancho grupo-opciones" :aria-invalid="!!errores.procedencia_id">
            <legend class="etiqueta">Procedencia<span class="requerido" aria-hidden="true">*</span></legend>
            <div class="segmentos" role="radiogroup" aria-required="true">
              <label v-for="p in procedencias" :key="p.id" class="segmento" :class="{ elegido: String(form.procedencia_id) === String(p.id) }">
                <input v-model="form.procedencia_id" type="radio" :name="`${uid}-procedencia`" :value="p.id" />
                <span>{{ p.nombre }}</span>
              </label>
              <span v-if="!procedencias.length" class="texto-3 texto-pequeno">Cargando…</span>
            </div>
            <p v-if="errores.procedencia_id" class="error-campo" role="alert">{{ errores.procedencia_id }}</p>
          </fieldset>

          <CampoCatalogo v-model="form.entidad_id" tipo="entidades" etiqueta="Entidad" requerido permitir-agregar
            :error="errores.entidad_id" ayuda="Elija de la lista. Si no existe, agréguela." />

          <CampoCatalogo v-model="form.tipo_tramite_id" tipo="tipos_tramite" etiqueta="Tipo de trámite" requerido permitir-agregar
            :error="errores.tipo_tramite_id" />

          <div class="campo campo-ancho">
            <label :for="`${uid}-asunto`">Asunto<span class="requerido" aria-hidden="true">*</span></label>
            <textarea :id="`${uid}-asunto`" v-model="form.asunto" class="area-texto" rows="4" :maxlength="maxAsunto"
              aria-required="true" :aria-invalid="!!errores.asunto" :aria-describedby="`${uid}-asunto-ayuda`"
              placeholder="Describa brevemente qué se solicita" />
            <div class="fila-entre">
              <p v-if="errores.asunto" :id="`${uid}-asunto-ayuda`" class="error-campo" role="alert">{{ errores.asunto }}</p>
              <p v-else :id="`${uid}-asunto-ayuda`" class="ayuda">Escriba el asunto como figura en la hoja de ruta.</p>
              <span class="ayuda contador" :class="{ cerca: largoAsunto > maxAsunto * 0.9 }">{{ largoAsunto }}/{{ maxAsunto }}</span>
            </div>
          </div>

          <!-- Asignacion: solo al registrar; en edicion se muestra como dato -->
          <div v-if="!esEdicion && puedeAsignar" class="campo campo-ancho">
            <label :for="`${uid}-abogado`">Abogado asignado <span class="opcional">(opcional)</span></label>
            <select :id="`${uid}-abogado`" v-model="form.profesional_id" class="seleccion"
              :aria-invalid="!!errores.profesional_id" :aria-describedby="`${uid}-abogado-ayuda`">
              <option value="">Sin asignar por ahora</option>
              <option v-for="p in abogados" :key="p.id" :value="p.id">{{ p.nombre }}</option>
            </select>
            <p v-if="errores.profesional_id" :id="`${uid}-abogado-ayuda`" class="error-campo" role="alert">{{ errores.profesional_id }}</p>
            <p v-else :id="`${uid}-abogado-ayuda`" class="ayuda">Si lo asigna ahora, el trámite pasa a «En elaboración».</p>
          </div>
          <div v-else-if="esEdicion" class="campo campo-ancho">
            <span class="etiqueta">Abogado asignado</span>
            <p class="dato-fijo">
              <strong>{{ tramite.profesional?.nombre_completo || 'Sin asignar' }}</strong>
              <EstadoTramite :estado="tramite.estado_tramite" />
            </p>
            <p class="ayuda">La asignación no se cambia aquí: se reasigna desde el expediente del trámite.</p>
          </div>
        </div>

        <!-- Datos de respuesta: solo en tramites concluidos -->
        <fieldset v-if="conRespuesta" class="respuesta">
          <legend><h3>Documento de respuesta</h3></legend>
          <div class="formulario-2">
            <div class="campo">
              <label :for="`${uid}-tdoc`">Tipo de documento</label>
              <select :id="`${uid}-tdoc`" v-model="form.tipo_documento_id" class="seleccion" :aria-invalid="!!errores.tipo_documento_id">
                <option value="">Sin tipo</option>
                <option v-for="d in tiposDocumento" :key="d.id" :value="d.id">{{ d.nombre }}</option>
              </select>
              <p v-if="errores.tipo_documento_id" class="error-campo" role="alert">{{ errores.tipo_documento_id }}</p>
            </div>
            <div class="campo">
              <label :for="`${uid}-num`">Número de documento</label>
              <input :id="`${uid}-num`" v-model="form.numero_documento" class="entrada mayusculas" type="text" autocomplete="off"
                spellcheck="false" placeholder="CGE/SCSL/GAAJ/C-166/2026" :aria-invalid="!!errores.numero_documento" />
              <p v-if="errores.numero_documento" class="error-campo" role="alert">{{ errores.numero_documento }}</p>
            </div>
            <div class="campo">
              <label :for="`${uid}-fecha`">Fecha de salida</label>
              <input :id="`${uid}-fecha`" v-model="form.fecha_salida" class="entrada" type="date" :aria-invalid="!!errores.fecha_salida" />
              <p v-if="errores.fecha_salida" class="error-campo" role="alert">{{ errores.fecha_salida }}</p>
              <p v-else-if="tramite.fecha_conclusion" class="ayuda">Concluido en el sistema el {{ formatoFecha(tramite.fecha_conclusion) }}.</p>
            </div>
          </div>
        </fieldset>

        <details class="mas-datos" :open="masDatos" @toggle="masDatos = $event.target.open">
          <summary>Más datos <span class="opcional">(opcional)</span></summary>
          <div class="formulario-2 mas-datos-cuerpo">
            <CampoCatalogo v-model="form.area_id" tipo="areas" etiqueta="Área o unidad" permitir-agregar :error="errores.area_id" />
            <div class="campo campo-ancho">
              <label :for="`${uid}-obs`">Observaciones</label>
              <textarea :id="`${uid}-obs`" v-model="form.observaciones" class="area-texto" rows="3" :aria-invalid="!!errores.observaciones" />
              <p v-if="errores.observaciones" class="error-campo" role="alert">{{ errores.observaciones }}</p>
            </div>
          </div>
        </details>

        <div class="formulario-acciones">
          <span class="ayuda atajo">Ctrl + Enter para guardar</span>
          <button type="button" class="boton" :disabled="enviando" @click="cancelar">Cancelar</button>
          <button type="submit" class="boton boton-primario" :disabled="enviando">
            <Save aria-hidden="true" /> {{ enviando ? 'Guardando…' : 'Guardar trámite' }}
          </button>
        </div>
      </div>
    </form>
  </div>
</template>

<style scoped>
.panel { max-width: 920px; }
.bloque { margin-bottom: var(--e-5); }
.mayusculas { text-transform: uppercase; }
.mayusculas::placeholder { text-transform: none; }

.grupo-opciones { border: none; margin: 0; padding: 0; }
.grupo-opciones legend { padding: 0; margin-bottom: 6px; }
.segmentos { display: inline-flex; flex-wrap: wrap; gap: var(--e-2); }
.segmento {
  position: relative; display: inline-flex; align-items: center; min-height: 40px; padding: 0 var(--e-5);
  border: 1px solid var(--linea-fuerte); border-radius: var(--radio-control); background: var(--superficie);
  font-weight: 600; font-size: var(--t-sm); letter-spacing: .03em; cursor: pointer; color: var(--texto-2);
}
.segmento input { position: absolute; opacity: 0; inset: 0; margin: 0; cursor: pointer; }
.segmento:hover { background: var(--superficie-2); }
.segmento.elegido { border-color: var(--sello); background: var(--sello-suave); color: var(--tinta); box-shadow: inset 0 0 0 1px var(--sello); }
.segmento:focus-within { box-shadow: var(--foco); }
.grupo-opciones[aria-invalid='true'] .segmento { border-color: var(--peligro); }

.contador { margin-left: auto; font-variant-numeric: tabular-nums; }
.contador.cerca { color: var(--aviso); font-weight: 650; }
.dato-fijo { display: flex; align-items: center; gap: var(--e-3); flex-wrap: wrap; min-height: 40px; padding: 6px 12px;
  background: var(--superficie-2); border: 1px dashed var(--linea-fuerte); border-radius: var(--radio-control); }

.respuesta { border: none; border-top: 1px solid var(--linea); margin: var(--e-6) 0 0; padding: var(--e-5) 0 0; }
.respuesta legend { padding: 0; float: left; width: 100%; margin-bottom: var(--e-4); }
.respuesta legend h3 { font-size: var(--t-md); }
.respuesta .formulario-2 { clear: both; }

.mas-datos { margin-top: var(--e-6); border-top: 1px solid var(--linea); padding-top: var(--e-4); }
.mas-datos summary { cursor: pointer; font-weight: 650; color: var(--tinta); font-size: var(--t-sm); width: fit-content; border-radius: var(--radio-control); }
.mas-datos .opcional { font-weight: 400; color: var(--texto-3); }
.mas-datos-cuerpo { margin-top: var(--e-4); }

.formulario-acciones { margin-top: var(--e-6); border-top: 1px solid var(--linea); padding-top: var(--e-4); align-items: center; }
.atajo { margin-right: auto; }

.creado { display: flex; gap: var(--e-4); align-items: flex-start; }
.creado-icono { width: 32px; height: 32px; color: var(--exito); flex: none; }
.creado-texto { display: grid; gap: var(--e-3); }
.acciones-creado { margin-top: var(--e-2); }

@media (max-width: 720px) {
  .atajo { display: none; }
  .formulario-acciones .boton { flex: 1; }
  .creado { flex-direction: column; }
}
</style>

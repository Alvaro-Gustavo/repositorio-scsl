<script setup>
// Conclusion del tramite por el abogado asignado: tipo y numero del documento
// de respuesta, fecha de salida y el informe en PDF. Si ya tiene informe,
// se sube una nueva version (la anterior se conserva inactiva).
import { ref, computed, onMounted, useId } from 'vue'
import { useRouter, RouterLink } from 'vue-router'
import { FileUp, FileText, X, Lock, Info, Send } from '@lucide/vue'
import { api } from '@/api'
import { useCatalogos } from '@/stores/catalogos'
import { useEnvio } from '@/composables/utiles'
import { diasDesde, formatoFecha, hoyISO, plural } from '@/utils/formato'
import Cargando from '@/components/ui/Cargando.vue'
import EstadoTramite from '@/components/ui/EstadoTramite.vue'
import Modal from '@/components/ui/Modal.vue'

const props = defineProps({ id: { type: String, required: true } })

const router = useRouter()
const catalogos = useCatalogos()
const { errores, enviando, enviar } = useEnvio()
const uid = useId()

const tramite = ref(null)
const cargando = ref(true)
const errorCarga = ref('')
const maxMb = ref(50)
const confirmar = ref(false)
const arrastrando = ref(false)
const entradaArchivo = ref(null)
const form = ref({ tipo_documento_id: '', numero_documento: '', fecha_salida: hoyISO(), archivo: null })

const tiposDocumento = computed(() => catalogos.datos.tipos_documento || [])
const nuevaVersion = computed(() => !!tramite.value?.informe)
const diasAsignado = computed(() => diasDesde(tramite.value?.fecha_asignacion))

onMounted(async () => {
  catalogos.obtener('tipos_documento').catch(() => {})
  api.configuracion.listar().then((lista) => {
    const v = Number(lista.find((c) => c.clave === 'pdf_max_mb')?.valor)
    if (v > 0) maxMb.value = v
  }).catch(() => {})
  try {
    const t = await api.tramites.obtener(props.id)
    tramite.value = t
    if (t.tipo_documento) form.value.tipo_documento_id = t.tipo_documento.id
    if (t.numero_documento) form.value.numero_documento = t.numero_documento
    if (t.fecha_salida) form.value.fecha_salida = t.fecha_salida
  } catch (e) {
    errorCarga.value = e.message || 'No se pudo cargar el trámite.'
  } finally {
    cargando.value = false
  }
})

function tamano(bytes) {
  if (bytes >= 1048576) return `${(bytes / 1048576).toLocaleString('es-BO', { maximumFractionDigits: 1 })} MB`
  return `${Math.max(1, Math.round(bytes / 1024)).toLocaleString('es-BO')} KB`
}

function tomarArchivo(archivo) {
  const { archivo: _, ...resto } = errores.value
  errores.value = resto
  if (!archivo) return
  if (!/\.pdf$/i.test(archivo.name) || (archivo.type && archivo.type !== 'application/pdf')) {
    errores.value = { ...errores.value, archivo: 'El archivo debe ser PDF.' }
    return
  }
  if (archivo.size > maxMb.value * 1048576) {
    errores.value = { ...errores.value, archivo: `El PDF supera el máximo de ${maxMb.value} MB.` }
    return
  }
  if (archivo.size === 0) {
    errores.value = { ...errores.value, archivo: 'El archivo está vacío.' }
    return
  }
  form.value.archivo = archivo
}
function alElegir(e) {
  tomarArchivo(e.target.files?.[0])
  e.target.value = ''
}
function alSoltar(e) {
  arrastrando.value = false
  const archivos = e.dataTransfer?.files
  if (archivos?.length > 1) {
    errores.value = { ...errores.value, archivo: 'Suelte un solo archivo PDF.' }
    return
  }
  tomarArchivo(archivos?.[0])
}
function quitarArchivo() {
  form.value.archivo = null
  entradaArchivo.value?.focus()
}

// Validacion previa en el navegador; el servidor vuelve a validar todo.
function revisar() {
  const campos = {}
  if (!form.value.tipo_documento_id) campos.tipo_documento_id = 'Seleccione el tipo de documento.'
  if (!form.value.numero_documento.trim()) campos.numero_documento = 'Ingrese el número del documento de respuesta.'
  if (!form.value.archivo) campos.archivo = errores.value.archivo || 'Adjunte el informe en PDF.'
  errores.value = campos
  if (Object.keys(campos).length) return
  confirmar.value = true
}

async function enviarInforme() {
  try {
    await enviar(() => api.tramites.concluir(props.id, {
      tipo_documento_id: Number(form.value.tipo_documento_id),
      numero_documento: form.value.numero_documento.trim().toUpperCase(),
      fecha_salida: form.value.fecha_salida || null,
      archivo: form.value.archivo
    }), nuevaVersion.value ? 'Nueva versión del informe subida.' : 'Informe subido. El trámite quedó concluido.')
    confirmar.value = false
    router.push(`/tramites/${props.id}`)
  } catch {
    confirmar.value = false
  }
}
</script>

<template>
  <div class="pagina">
    <header class="pagina-cabecera">
      <div>
        <h1>{{ nuevaVersion ? 'Subir nueva versión del informe' : 'Concluir trámite' }}</h1>
        <p>Registre el documento de respuesta y adjunte el informe firmado en PDF.</p>
      </div>
      <div class="pagina-acciones">
        <RouterLink :to="`/tramites/${id}`" class="boton boton-fantasma">Volver al expediente</RouterLink>
      </div>
    </header>

    <Cargando v-if="cargando" texto="Cargando el trámite…" />
    <p v-else-if="errorCarga" class="mensaje mensaje-peligro" role="alert">{{ errorCarga }}</p>

    <template v-else-if="tramite">
      <!-- Resumen del tramite -->
      <section class="panel resumen" aria-label="Trámite a concluir">
        <div class="panel-cuerpo">
          <div class="fila-entre">
            <span class="codigo codigo-sello">{{ tramite.hoja_ruta }}</span>
            <EstadoTramite :estado="tramite.estado_tramite" />
          </div>
          <p class="resumen-asunto">{{ tramite.asunto }}</p>
          <dl class="datos">
            <div><dt>Entidad</dt><dd>{{ tramite.entidad?.nombre || '—' }}</dd></div>
            <div><dt>Tipo de trámite</dt><dd>{{ tramite.tipo_tramite?.nombre || '—' }}</dd></div>
            <div><dt>Abogado asignado</dt><dd>{{ tramite.profesional?.nombre_completo || 'Sin asignar' }}</dd></div>
            <div>
              <dt>Asignado</dt>
              <dd>
                <template v-if="diasAsignado !== null">{{ diasAsignado <= 0 ? 'hoy' : `hace ${plural(diasAsignado, 'día', 'días')}` }}</template>
                <template v-else>—</template>
                <span v-if="tramite.fecha_asignacion" class="texto-3 normal"> · {{ formatoFecha(tramite.fecha_asignacion) }}</span>
              </dd>
            </div>
          </dl>
        </div>
      </section>

      <div v-if="!tramite.permisos?.concluir" class="panel">
        <div class="panel-cuerpo">
          <div class="mensaje mensaje-aviso">
            <Lock aria-hidden="true" />
            <div>
              <strong>No puede subir el informe de este trámite.</strong>
              <p v-if="tramite.estado_tramite === 'RECIBIDO'">El trámite aún no tiene abogado asignado. Primero debe asignarse.</p>
              <p v-else-if="tramite.estado_tramite === 'ARCHIVADO'">El trámite está archivado y ya no admite cambios en su informe.</p>
              <p v-else>Solo el abogado asignado al trámite puede subir el informe y concluirlo.</p>
            </div>
          </div>
        </div>
      </div>

      <form v-else class="panel" novalidate @submit.prevent="revisar">
        <div class="panel-cabecera"><h2>Documento de respuesta</h2></div>
        <div class="panel-cuerpo">
          <p v-if="nuevaVersion" class="mensaje mensaje-info bloque">
            <Info aria-hidden="true" />
            <span>Este trámite ya tiene un informe ({{ tramite.informe.nombre_original }}). Al subir uno nuevo, la versión anterior se conserva inactiva y deja de mostrarse.</span>
          </p>

          <div class="formulario-2">
            <div class="campo">
              <label :for="`${uid}-tipo`">Tipo de documento<span class="requerido" aria-hidden="true">*</span></label>
              <select :id="`${uid}-tipo`" v-model="form.tipo_documento_id" class="seleccion" aria-required="true" :aria-invalid="!!errores.tipo_documento_id">
                <option value="" disabled>Elija el tipo</option>
                <option v-for="d in tiposDocumento" :key="d.id" :value="d.id">{{ d.nombre }}</option>
              </select>
              <p v-if="errores.tipo_documento_id" class="error-campo" role="alert">{{ errores.tipo_documento_id }}</p>
            </div>
            <div class="campo">
              <label :for="`${uid}-fecha`">Fecha de salida</label>
              <input :id="`${uid}-fecha`" v-model="form.fecha_salida" class="entrada" type="date" :aria-invalid="!!errores.fecha_salida" />
              <p v-if="errores.fecha_salida" class="error-campo" role="alert">{{ errores.fecha_salida }}</p>
              <p v-else class="ayuda">Por defecto, la fecha de hoy.</p>
            </div>
            <div class="campo campo-ancho">
              <label :for="`${uid}-numero`">Número de documento<span class="requerido" aria-hidden="true">*</span></label>
              <input :id="`${uid}-numero`" v-model="form.numero_documento" class="entrada numero" type="text" autocomplete="off" spellcheck="false"
                placeholder="CGE/SCSL/GAAJ/C-166/2026" aria-required="true" :aria-invalid="!!errores.numero_documento" />
              <p v-if="errores.numero_documento" class="error-campo" role="alert">{{ errores.numero_documento }}</p>
              <p v-else class="ayuda">Tal como figura en el documento firmado. Se guarda en mayúsculas.</p>
            </div>

            <div class="campo campo-ancho">
              <span :id="`${uid}-pdf-etiqueta`" class="etiqueta">Informe en PDF<span class="requerido" aria-hidden="true">*</span></span>
              <div v-if="form.archivo" class="archivo-elegido">
                <FileText aria-hidden="true" class="archivo-icono" />
                <div class="archivo-datos">
                  <strong>{{ form.archivo.name }}</strong>
                  <span class="texto-3 texto-xs">{{ tamano(form.archivo.size) }}</span>
                </div>
                <button type="button" class="boton boton-fantasma boton-pequeno" @click="quitarArchivo"><X aria-hidden="true" /> Quitar</button>
              </div>
              <label v-else :for="`${uid}-pdf`" class="zona" :class="{ arrastrando, invalida: !!errores.archivo }"
                @dragenter.prevent="arrastrando = true" @dragover.prevent="arrastrando = true"
                @dragleave.prevent="arrastrando = false" @drop.prevent="alSoltar">
                <FileUp aria-hidden="true" class="zona-icono" />
                <span><strong>Suelte aquí el PDF</strong> o <span class="enlace">elija un archivo</span></span>
                <span class="texto-3 texto-xs">Solo PDF, hasta {{ maxMb }} MB</span>
              </label>
              <input :id="`${uid}-pdf`" ref="entradaArchivo" type="file" accept="application/pdf,.pdf" class="sr-only"
                :aria-labelledby="`${uid}-pdf-etiqueta`" :aria-invalid="!!errores.archivo" @change="alElegir" />
              <p v-if="errores.archivo" class="error-campo" role="alert">{{ errores.archivo }}</p>
            </div>
          </div>

          <div class="formulario-acciones">
            <RouterLink :to="`/tramites/${id}`" class="boton">Cancelar</RouterLink>
            <button type="submit" class="boton boton-primario" :disabled="enviando">
              <Send aria-hidden="true" /> {{ nuevaVersion ? 'Subir nueva versión' : 'Subir informe y concluir' }}
            </button>
          </div>
        </div>
      </form>

      <Modal v-model="confirmar" :titulo="nuevaVersion ? 'Confirmar nueva versión' : 'Confirmar conclusión'" ancho="520px">
        <div class="pila-corta">
          <p v-if="nuevaVersion">Se reemplazará el informe visible del trámite. La versión anterior se conserva inactiva.</p>
          <p v-else>Al subir el informe el trámite queda concluido y sale de sus pendientes.</p>
          <dl class="datos confirmacion">
            <div><dt>Tipo</dt><dd>{{ tiposDocumento.find((d) => String(d.id) === String(form.tipo_documento_id))?.nombre }}</dd></div>
            <div><dt>Fecha de salida</dt><dd>{{ formatoFecha(form.fecha_salida) }}</dd></div>
            <div class="ancho"><dt>Número</dt><dd class="codigo">{{ form.numero_documento.trim().toUpperCase() }}</dd></div>
            <div class="ancho"><dt>Archivo</dt><dd>{{ form.archivo?.name }}</dd></div>
          </dl>
        </div>
        <template #pie>
          <button type="button" class="boton" :disabled="enviando" @click="confirmar = false">Revisar</button>
          <button type="button" class="boton boton-primario" :disabled="enviando" @click="enviarInforme">
            {{ enviando ? 'Subiendo…' : (nuevaVersion ? 'Subir nueva versión' : 'Subir y concluir') }}
          </button>
        </template>
      </Modal>
    </template>
  </div>
</template>

<style scoped>
.panel { max-width: 860px; }
.resumen { border-left: 3px solid var(--tinta); }
.resumen-asunto { font-family: var(--fuente-titulo); font-size: 1.08rem; font-weight: 600; color: var(--tinta); margin: var(--e-3) 0 var(--e-4); line-height: 1.4; }
.normal { font-weight: 400; }
.bloque { margin-bottom: var(--e-5); }
.numero { text-transform: uppercase; }
.numero::placeholder { text-transform: none; }

.zona {
  display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 6px; text-align: center;
  min-height: 140px; padding: var(--e-6) var(--e-4); cursor: pointer;
  border: 1.5px dashed var(--linea-fuerte); border-radius: var(--radio-panel); background: var(--superficie-2);
  font-size: var(--t-sm); color: var(--texto-2); transition: border-color .12s, background-color .12s;
}
.zona:hover, .zona.arrastrando { border-color: var(--sello); background: var(--sello-suave); }
.zona.invalida { border-color: var(--peligro); }
.zona-icono { width: 28px; height: 28px; color: var(--sello); }
.enlace { color: var(--sello); text-decoration: underline; }
.campo:has(input[type='file']:focus-visible) .zona { box-shadow: var(--foco); border-color: var(--sello); }

.archivo-elegido { display: flex; align-items: center; gap: var(--e-3); padding: var(--e-3) var(--e-4);
  border: 1px solid var(--linea); border-radius: var(--radio-control); background: var(--concluido-suave); }
.archivo-icono { width: 24px; height: 24px; color: var(--concluido); flex: none; }
.archivo-datos { display: flex; flex-direction: column; min-width: 0; flex: 1; }
.archivo-datos strong { overflow-wrap: anywhere; font-size: var(--t-sm); }

.pila-corta > * + * { margin-top: var(--e-4); }
.confirmacion { padding: var(--e-4); background: var(--superficie-2); border-radius: var(--radio-control); }

@media (max-width: 720px) {
  .formulario-acciones .boton { flex: 1; }
  .archivo-elegido { flex-wrap: wrap; }
}
</style>

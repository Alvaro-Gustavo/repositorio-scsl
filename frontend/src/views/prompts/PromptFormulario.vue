<script setup>
// Proponer un prompt nuevo o editar uno existente (borrador propio o, para el jefe, uno vigente).
import { ref, reactive, computed } from 'vue'
import { useRouter, RouterLink } from 'vue-router'
import { Send, Save, ArrowLeft, TriangleAlert, Info } from '@lucide/vue'
import { api } from '@/api'
import { useSesion } from '@/stores/sesion'
import { useCatalogos } from '@/stores/catalogos'
import { useEnvio } from '@/composables/utiles'
import { CATEGORIAS_PROMPT } from '@/utils/constantes'
import Cargando from '@/components/ui/Cargando.vue'
import TextoPrompt from '@/components/prompts/TextoPrompt.vue'

const props = defineProps({ id: { type: [String, Number], default: null } })

const router = useRouter()
const sesion = useSesion()
const catalogos = useCatalogos()
const { errores, enviando, enviar } = useEnvio()

const esJefe = computed(() => sesion.puede('GESTIONAR_PROMPTS'))
const editando = computed(() => props.id != null && props.id !== '')

const form = reactive({ titulo: '', categoria: '', tipo_documento_id: '', texto: '', instrucciones: '' })
const original = ref(null)
const cargando = ref(false)
const errorCarga = ref('')

const tiposDocumento = ref([])
catalogos.obtener('tipos_documento').then((l) => { tiposDocumento.value = l }).catch(() => {})
// Si el prompt usa un tipo ya desactivado, se mantiene en la lista para no perderlo.
const opcionesTipo = computed(() => {
  const t = original.value?.tipo_documento
  if (t && !tiposDocumento.value.some((x) => x.id === t.id)) return [...tiposDocumento.value, t]
  return tiposDocumento.value
})

async function cargarPrompt() {
  cargando.value = true
  errorCarga.value = ''
  try {
    const lista = await api.prompts.gestion()
    const p = (lista || []).find((x) => String(x.id) === String(props.id))
    if (!p) { errorCarga.value = 'El prompt no existe o no tiene acceso a él.'; return }
    original.value = p
    Object.assign(form, {
      titulo: p.titulo || '', categoria: p.categoria || '',
      tipo_documento_id: p.tipo_documento_id != null ? String(p.tipo_documento_id) : '',
      texto: p.texto || '', instrucciones: p.instrucciones || ''
    })
  } catch (e) {
    errorCarga.value = e.message || 'No se pudo cargar el prompt.'
  } finally {
    cargando.value = false
  }
}
if (editando.value) cargarPrompt()

const esVigente = computed(() => original.value?.estado === 'VIGENTE')
const bloqueado = computed(() => {
  const p = original.value
  if (!p) return ''
  if (p.estado === 'RETIRADO') return 'Este prompt está retirado y ya no se puede editar. Si hace falta, proponga uno nuevo.'
  if (p.estado === 'VIGENTE' && !esJefe.value) return 'Este prompt ya está vigente. Solo la jefatura puede modificarlo.'
  return ''
})

const marcadores = computed(() => (form.texto.match(/\[[^\]\n]+\]/g) || []).length)

const datos = () => ({
  titulo: form.titulo, categoria: form.categoria,
  tipo_documento_id: form.tipo_documento_id ? Number(form.tipo_documento_id) : null,
  texto: form.texto, instrucciones: form.instrucciones
})

async function guardar() {
  try {
    if (editando.value) {
      await enviar(() => api.prompts.actualizar(original.value.id, datos()),
        esVigente.value ? 'Cambios guardados. Ya se ven en el catálogo.' : 'Cambios guardados. La propuesta sigue en revisión.')
    } else {
      await enviar(() => api.prompts.proponer(datos()), 'Propuesta enviada a revisión.')
    }
    router.push('/prompts/gestion')
  } catch {
    // Llevar el foco al primer campo con error.
    const primero = ['titulo', 'categoria', 'tipo_documento_id', 'texto', 'instrucciones'].find((c) => errores.value[c])
    if (primero) document.getElementById(`campo-${primero}`)?.focus()
  }
}

const describir = (campo, ayuda) => [errores.value[campo] ? `campo-${campo}-error` : null, ayuda].filter(Boolean).join(' ') || null
</script>

<template>
  <div class="pagina">
    <header class="pagina-cabecera">
      <div>
        <h1>{{ editando ? 'Editar prompt' : 'Proponer un prompt' }}</h1>
        <p v-if="!editando">Escriba la instrucción que los doctores copiarán en su herramienta de IA. La jefatura la revisa antes de publicarla en el catálogo.</p>
        <p v-else>Corrija el prompt y guarde los cambios.</p>
      </div>
      <div class="pagina-acciones">
        <RouterLink to="/prompts/gestion" class="boton"><ArrowLeft aria-hidden="true" /> Volver a gestión</RouterLink>
      </div>
    </header>

    <Cargando v-if="cargando" texto="Cargando prompt…" />
    <p v-else-if="errorCarga" class="mensaje mensaje-peligro" role="alert">{{ errorCarga }}</p>
    <p v-else-if="bloqueado" class="mensaje mensaje-peligro" role="alert"><TriangleAlert aria-hidden="true" /> <span>{{ bloqueado }}</span></p>

    <div v-else class="editor">
      <form class="panel" novalidate @submit.prevent="guardar">
        <div class="panel-cuerpo formulario">
          <p v-if="editando && esVigente" class="mensaje mensaje-aviso" role="note">
            <TriangleAlert aria-hidden="true" />
            <span>Este prompt está vigente. Los cambios se aplican de inmediato para todos los doctores que usan el catálogo.</span>
          </p>
          <p v-if="editando && original?.observacion && original?.estado === 'BORRADOR'" class="mensaje mensaje-aviso" role="note">
            <TriangleAlert aria-hidden="true" />
            <span><strong>Observación de la jefatura:</strong> {{ original.observacion }}</span>
          </p>

          <div class="campo">
            <label for="campo-titulo">Título<span class="requerido" aria-hidden="true">*</span></label>
            <input id="campo-titulo" v-model="form.titulo" class="entrada" type="text" maxlength="150" required autocomplete="off"
              :aria-invalid="!!errores.titulo" :aria-describedby="describir('titulo', 'campo-titulo-ayuda')" />
            <span id="campo-titulo-ayuda" class="ayuda">Corto y claro, por ejemplo «Extraer el criterio legal de un informe».</span>
            <span v-if="errores.titulo" id="campo-titulo-error" class="error-campo">{{ errores.titulo }}</span>
          </div>

          <div class="formulario-2">
            <div class="campo">
              <label for="campo-categoria">Categoría<span class="requerido" aria-hidden="true">*</span></label>
              <select id="campo-categoria" v-model="form.categoria" class="seleccion" required
                :aria-invalid="!!errores.categoria" :aria-describedby="describir('categoria')">
                <option value="" disabled>Elija una categoría</option>
                <option v-for="(nombre, clave) in CATEGORIAS_PROMPT" :key="clave" :value="clave">{{ nombre }}</option>
              </select>
              <span v-if="errores.categoria" id="campo-categoria-error" class="error-campo">{{ errores.categoria }}</span>
            </div>
            <div class="campo">
              <label for="campo-tipo_documento_id">Tipo de documento</label>
              <select id="campo-tipo_documento_id" v-model="form.tipo_documento_id" class="seleccion"
                :aria-invalid="!!errores.tipo_documento_id" :aria-describedby="describir('tipo_documento_id')">
                <option value="">General (cualquier tipo)</option>
                <option v-for="t in opcionesTipo" :key="t.id" :value="String(t.id)">{{ t.nombre }}</option>
              </select>
              <span v-if="errores.tipo_documento_id" id="campo-tipo_documento_id-error" class="error-campo">{{ errores.tipo_documento_id }}</span>
            </div>
          </div>

          <div class="campo">
            <label for="campo-texto">Texto del prompt<span class="requerido" aria-hidden="true">*</span></label>
            <textarea id="campo-texto" v-model="form.texto" class="area-texto area-prompt" rows="12" required
              :aria-invalid="!!errores.texto" :aria-describedby="describir('texto', 'campo-texto-ayuda')"></textarea>
            <span id="campo-texto-ayuda" class="ayuda">
              Use corchetes para lo que el doctor debe completar, por ejemplo [PEGUE AQUÍ EL TEXTO].
              <template v-if="marcadores">Tiene {{ marcadores }} {{ marcadores === 1 ? 'marcador' : 'marcadores' }}.</template>
            </span>
            <span v-if="errores.texto" id="campo-texto-error" class="error-campo">{{ errores.texto }}</span>
          </div>

          <div class="campo">
            <label for="campo-instrucciones">Instrucciones de uso <span class="opcional">(opcional)</span></label>
            <textarea id="campo-instrucciones" v-model="form.instrucciones" class="area-texto" rows="3"
              :aria-invalid="!!errores.instrucciones" :aria-describedby="describir('instrucciones', 'campo-instrucciones-ayuda')"></textarea>
            <span id="campo-instrucciones-ayuda" class="ayuda">Qué debe revisar el doctor antes y después de usarlo.</span>
            <span v-if="errores.instrucciones" id="campo-instrucciones-error" class="error-campo">{{ errores.instrucciones }}</span>
          </div>

          <p v-if="!editando && esJefe" class="mensaje mensaje-info" role="note">
            <Info aria-hidden="true" />
            <span>Quedará como propuesta por revisar. Puede aprobarla después desde la gestión de prompts.</span>
          </p>

          <div class="formulario-acciones">
            <RouterLink to="/prompts/gestion" class="boton">Cancelar</RouterLink>
            <button type="submit" class="boton boton-primario" :disabled="enviando">
              <template v-if="editando"><Save aria-hidden="true" /> Guardar cambios</template>
              <template v-else><Send aria-hidden="true" /> Enviar a revisión</template>
            </button>
          </div>
        </div>
      </form>

      <aside class="panel vista" aria-labelledby="vista-titulo">
        <div class="panel-cabecera"><h2 id="vista-titulo">Vista previa</h2></div>
        <div class="panel-cuerpo vista-cuerpo">
          <p class="vista-nombre">{{ form.titulo || 'Sin título' }}</p>
          <div class="fila">
            <span class="insignia insignia-info insignia-sin-punto">{{ CATEGORIAS_PROMPT[form.categoria] || 'Sin categoría' }}</span>
            <span class="insignia insignia-sin-punto">{{ opcionesTipo.find((t) => String(t.id) === form.tipo_documento_id)?.nombre || 'General' }}</span>
          </div>
          <p v-if="form.instrucciones.trim()" class="texto-2 texto-pequeno"><span class="etiqueta">Cómo usarlo:</span> {{ form.instrucciones }}</p>
          <TextoPrompt v-if="form.texto.trim()" :texto="form.texto" />
          <p v-else class="texto-3 texto-pequeno">El texto del prompt aparecerá aquí, con los marcadores resaltados.</p>
        </div>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.editor { display: grid; grid-template-columns: minmax(0, 1.2fr) minmax(0, 1fr); gap: var(--e-6); align-items: start; }
.area-prompt { min-height: 240px; }
.vista { position: sticky; top: calc(var(--alto-superior) + var(--e-4)); }
.vista-cuerpo { display: grid; gap: var(--e-3); }
.vista-nombre { font-weight: 650; color: var(--tinta); overflow-wrap: anywhere; }
.vista .etiqueta { font-size: inherit; }
@media (max-width: 960px) {
  .editor { grid-template-columns: 1fr; }
  .vista { position: static; }
}
</style>

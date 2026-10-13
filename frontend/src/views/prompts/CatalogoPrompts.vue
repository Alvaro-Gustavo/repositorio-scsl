<script setup>
// Catalogo de prompts aprobados. El sistema no usa IA: el doctor copia el prompt
// y lo pega en su propia herramienta. Cada copia se registra (usos y auditoria).
import { ref, computed, watch } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import { Search, Plus, Settings2, MessageSquareText, ShieldCheck, Copy } from '@lucide/vue'
import { api } from '@/api'
import { useSesion } from '@/stores/sesion'
import { useAvisos } from '@/stores/avisos'
import { useCatalogos } from '@/stores/catalogos'
import { useCarga, copiarTexto } from '@/composables/utiles'
import { CATEGORIAS_PROMPT } from '@/utils/constantes'
import { plural } from '@/utils/formato'
import { enmascarar } from '@/utils/enmascarar'
import Modal from '@/components/ui/Modal.vue'
import Cargando from '@/components/ui/Cargando.vue'
import EstadoVacio from '@/components/ui/EstadoVacio.vue'
import TarjetaPrompt from '@/components/prompts/TarjetaPrompt.vue'
import TextoPrompt from '@/components/prompts/TextoPrompt.vue'

const route = useRoute()
const sesion = useSesion()
const avisos = useAvisos()
const catalogos = useCatalogos()

const tramiteId = computed(() => route.query.tramite_id || null)
const tipoDocumento = ref(route.query.tipo_documento_id ? String(route.query.tipo_documento_id) : '')
const categoria = ref('')
const busqueda = ref('')

// Aviso de proteccion de datos (configurable por el administrador).
const aviso = ref('')
api.configuracion.listar()
  .then((lista) => { aviso.value = (lista || []).find((c) => c.clave === 'prompts_aviso')?.valor || '' })
  .catch(() => { /* sin aviso configurado */ })

const tiposDocumento = ref([])
catalogos.obtener('tipos_documento').then((l) => { tiposDocumento.value = l }).catch(() => {})

// Se piden al servidor por tipo de documento (incluye los generales); categoria y texto se filtran aqui.
const { datos: prompts, cargando, error, cargar } = useCarga(
  () => api.prompts.vigentes(tipoDocumento.value ? { tipo_documento_id: tipoDocumento.value } : {}),
  { inicial: [] }
)
watch(tipoDocumento, () => cargar())

const normalizar = (t) => String(t || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim()

const porTexto = computed(() => {
  const q = normalizar(busqueda.value)
  if (!q) return prompts.value || []
  return (prompts.value || []).filter((p) => normalizar(`${p.titulo} ${p.texto} ${p.instrucciones || ''}`).includes(q))
})
const conteoCategoria = computed(() => {
  const c = {}
  for (const p of porTexto.value) c[p.categoria] = (c[p.categoria] || 0) + 1
  return c
})
const filtrados = computed(() => porTexto.value.filter((p) => !categoria.value || p.categoria === categoria.value))

// Con un tipo elegido se separan los propios del tipo y los generales.
const grupos = computed(() => {
  if (!tipoDocumento.value) return [{ clave: 'todos', titulo: null, lista: filtrados.value }]
  const nombreTipo = tiposDocumento.value.find((t) => String(t.id) === tipoDocumento.value)?.nombre || 'este tipo de documento'
  return [
    { clave: 'tipo', titulo: `Para ${nombreTipo.toLowerCase()}`, lista: filtrados.value.filter((p) => p.tipo_documento_id != null) },
    { clave: 'general', titulo: 'Generales (cualquier tipo de documento)', lista: filtrados.value.filter((p) => p.tipo_documento_id == null) }
  ].filter((g) => g.lista.length)
})

const hayFiltros = computed(() => !!(tipoDocumento.value || categoria.value || busqueda.value))
function limpiarFiltros() {
  tipoDocumento.value = ''
  categoria.value = ''
  busqueda.value = ''
}

// ---------- Copiar ----------
const idCopiado = ref(null)
const ocupado = ref(false)
let temporizador = null

async function registrarCopia(prompt, texto, mensaje) {
  ocupado.value = true
  try {
    const ok = await copiarTexto(texto)
    if (!ok) {
      avisos.error('No se pudo copiar. Seleccione el texto y cópielo manualmente.')
      return false
    }
    try {
      await api.prompts.registrarUso(prompt.id, tramiteId.value ? Number(tramiteId.value) || tramiteId.value : null)
      prompt.usos = (prompt.usos || 0) + 1
    } catch { /* la copia ya se hizo; el registro de uso no debe impedir el trabajo */ }
    avisos.exito(mensaje)
    idCopiado.value = prompt.id
    clearTimeout(temporizador)
    temporizador = setTimeout(() => { idCopiado.value = null }, 2500)
    return true
  } finally {
    ocupado.value = false
  }
}

function copiar(prompt) {
  registrarCopia(prompt, prompt.texto, 'Prompt copiado. Péguelo en su herramienta de IA.')
}

// El enlace abre la pestaña del asistente; aquí solo se copia el prompt y se audita.
function copiarYAbrir(prompt, asistente) {
  registrarCopia(prompt, prompt.texto, `Prompt copiado. Péguelo en ${asistente.nombre} (Ctrl + V).`)
  api.auditoria.registrar({ accion: 'ABRIR_ASISTENTE_IA', modulo: 'PROMPTS', detalle: { asistente: asistente.nombre, prompt: prompt.id } }).catch(() => {})
}

// ---------- Copiar enmascarado ----------
const modalAbierto = ref(false)
const promptElegido = ref(null)
const textoAgregado = ref('')

const marcadores = computed(() => (promptElegido.value?.texto.match(/\[[^\]\n]+\]/g) || []))
const enmascarado = computed(() => enmascarar(textoAgregado.value))
const textoFinal = computed(() => {
  const p = promptElegido.value
  if (!p) return ''
  const agregado = enmascarado.value.texto.trim()
  if (!agregado) return p.texto
  // Si el prompt tiene un unico marcador, el texto ocupa su lugar; si no, va al final.
  if (marcadores.value.length === 1) return p.texto.replace(marcadores.value[0], () => agregado)
  return `${p.texto}\n\n${agregado}`
})

function abrirEnmascarado(prompt) {
  promptElegido.value = prompt
  textoAgregado.value = ''
  modalAbierto.value = true
}

async function copiarEnmascarado() {
  const n = enmascarado.value.ocultos
  const ok = await registrarCopia(promptElegido.value, textoFinal.value,
    n ? `Prompt copiado con ${plural(n, 'dato oculto', 'datos ocultos')}. Péguelo en su herramienta de IA.`
      : 'Prompt copiado. Péguelo en su herramienta de IA.')
  if (ok) modalAbierto.value = false
}
</script>

<template>
  <div class="pagina">
    <header class="pagina-cabecera">
      <div>
        <h1>Catálogo de prompts</h1>
        <p>Instrucciones aprobadas por la jefatura para usar en su propia herramienta de IA. El sistema no se conecta a ninguna IA.</p>
      </div>
      <div v-if="sesion.puede('PROPONER_PROMPT')" class="pagina-acciones">
        <RouterLink to="/prompts/gestion" class="boton"><Settings2 aria-hidden="true" /> Gestionar prompts</RouterLink>
        <RouterLink to="/prompts/nuevo" class="boton boton-primario"><Plus aria-hidden="true" /> Proponer un prompt</RouterLink>
      </div>
    </header>

    <p v-if="aviso" class="mensaje mensaje-aviso aviso-datos" role="note">
      <ShieldCheck aria-hidden="true" /> <span>{{ aviso }}</span>
    </p>

    <div class="catalogo">
      <div class="catalogo-principal">
        <section class="panel filtros" aria-label="Filtros del catálogo">
          <div class="panel-cuerpo">
            <div class="formulario-2">
              <div class="campo">
                <label for="filtro-tipo">Tipo de documento</label>
                <select id="filtro-tipo" v-model="tipoDocumento" class="seleccion">
                  <option value="">Todos</option>
                  <option v-for="t in tiposDocumento" :key="t.id" :value="String(t.id)">{{ t.nombre }}</option>
                </select>
              </div>
              <div class="campo">
                <label for="filtro-texto">Buscar</label>
                <div class="entrada-icono">
                  <Search aria-hidden="true" />
                  <input id="filtro-texto" v-model="busqueda" type="search" class="entrada" placeholder="Título o palabras del prompt" autocomplete="off" />
                </div>
              </div>
            </div>
            <div class="chips" role="group" aria-label="Categoría">
              <button type="button" class="chip" :aria-pressed="categoria === ''" @click="categoria = ''">
                Todas <span class="chip-n">{{ porTexto.length }}</span>
              </button>
              <button v-for="(nombre, clave) in CATEGORIAS_PROMPT" :key="clave" type="button" class="chip"
                :aria-pressed="categoria === clave" @click="categoria = clave">
                {{ nombre }} <span class="chip-n">{{ conteoCategoria[clave] || 0 }}</span>
              </button>
            </div>
          </div>
        </section>

        <section class="panel" aria-live="polite" :aria-busy="cargando">
          <div class="panel-cabecera">
            <h2>Prompts vigentes</h2>
            <span v-if="!cargando && !error" class="texto-3 texto-pequeno">{{ plural(filtrados.length, 'prompt', 'prompts') }}</span>
          </div>
          <Cargando v-if="cargando" texto="Cargando prompts…" />
          <div v-else-if="error" class="panel-cuerpo">
            <p class="mensaje mensaje-peligro" role="alert">{{ error }}</p>
            <div class="formulario-acciones"><button type="button" class="boton" @click="cargar()">Reintentar</button></div>
          </div>
          <EstadoVacio v-else-if="!filtrados.length" :icono="MessageSquareText" titulo="No hay prompts para estos criterios"
            :texto="hayFiltros ? 'Pruebe con otra categoría o tipo de documento, o borre la búsqueda.' : 'Todavía no hay prompts aprobados.'">
            <button v-if="hayFiltros" type="button" class="boton" @click="limpiarFiltros">Quitar filtros</button>
            <RouterLink v-if="sesion.puede('PROPONER_PROMPT')" to="/prompts/nuevo" class="boton boton-primario">Proponer un prompt</RouterLink>
          </EstadoVacio>
          <template v-else>
            <div v-for="g in grupos" :key="g.clave" class="grupo">
              <h3 v-if="g.titulo" class="grupo-titulo">{{ g.titulo }}</h3>
              <TarjetaPrompt v-for="p in g.lista" :key="p.id" :prompt="p" :copiado="idCopiado === p.id" :ocupado="ocupado"
                @copiar="copiar" @copiar-enmascarado="abrirEnmascarado" @copiar-y-abrir="copiarYAbrir" />
            </div>
          </template>
        </section>
      </div>

      <aside class="panel como-usar" aria-labelledby="como-usar-titulo">
        <div class="panel-cabecera"><h2 id="como-usar-titulo">Cómo usar</h2></div>
        <ol class="pasos panel-cuerpo">
          <li><strong>Elija el prompt</strong> según el tipo de documento que está elaborando y la tarea.</li>
          <li><strong>Cópielo</strong> y complete lo que está resaltado entre corchetes. Use «Copiar enmascarado» si va a agregar texto con datos personales.</li>
          <li><strong>Péguelo en su IA y revise la respuesta</strong> antes de usarla: verifique normas y citas. El criterio final lo firma el abogado.</li>
        </ol>
      </aside>
    </div>

    <Modal v-model="modalAbierto" titulo="Copiar enmascarado" ancho="720px">
      <div v-if="promptElegido" class="formulario">
        <p class="texto-2 texto-pequeno">
          Pegue el texto que quiere agregar al prompt «{{ promptElegido.titulo }}». Antes de copiar se ocultan correos,
          carnets de identidad, NIT, cuentas bancarias y teléfonos. Revise igual que no queden nombres u otros datos reservados.
        </p>
        <div class="campo">
          <label for="texto-agregado">Texto a agregar</label>
          <textarea id="texto-agregado" v-model="textoAgregado" class="area-texto" rows="7"
            placeholder="Por ejemplo, el texto del informe" aria-describedby="texto-agregado-ayuda"></textarea>
          <span id="texto-agregado-ayuda" class="ayuda">
            {{ marcadores.length === 1 ? `Reemplazará el marcador ${marcadores[0]}.` : 'Se agregará al final del prompt.' }}
          </span>
        </div>
        <p v-if="textoAgregado.trim()" class="mensaje" :class="enmascarado.ocultos ? 'mensaje-exito' : 'mensaje-info'" role="status">
          <ShieldCheck aria-hidden="true" />
          <span>{{ enmascarado.ocultos ? `Se ocultaron ${plural(enmascarado.ocultos, 'dato', 'datos')}.` : 'No se encontraron datos para ocultar.' }}</span>
        </p>
        <div class="campo">
          <span class="etiqueta">Vista previa de lo que se copiará</span>
          <div class="vista-previa"><TextoPrompt :texto="textoFinal" /></div>
        </div>
      </div>
      <template #pie>
        <button type="button" class="boton" @click="modalAbierto = false">Cancelar</button>
        <button type="button" class="boton boton-primario" :disabled="ocupado" @click="copiarEnmascarado">
          <Copy aria-hidden="true" /> Copiar prompt y texto
        </button>
      </template>
    </Modal>
  </div>
</template>

<style scoped>
.aviso-datos { margin-bottom: var(--e-6); }
.catalogo { display: grid; grid-template-columns: minmax(0, 1fr) 300px; gap: var(--e-6); align-items: start; }
.catalogo-principal > * + * { margin-top: var(--e-6); }
.como-usar { position: sticky; top: calc(var(--alto-superior) + var(--e-4)); }
.pasos { margin: 0; padding-left: calc(var(--e-6) + var(--e-4)); display: grid; gap: var(--e-3); font-size: var(--t-sm); color: var(--texto-2); }
.pasos strong { color: var(--texto); }

.entrada-icono { position: relative; }
.entrada-icono svg { position: absolute; left: 12px; top: 50%; transform: translateY(-50%); width: 16px; height: 16px; color: var(--texto-3); pointer-events: none; }
.entrada-icono .entrada { padding-left: 36px; }

.chips { display: flex; flex-wrap: wrap; gap: var(--e-2); margin-top: var(--e-5); }
.chip {
  display: inline-flex; align-items: center; gap: 6px; min-height: 32px; padding: 0 var(--e-3);
  border: 1px solid var(--linea-fuerte); border-radius: 999px; background: var(--superficie);
  font-size: var(--t-sm); font-weight: 600; color: var(--texto-2); cursor: pointer;
}
.chip:hover { border-color: var(--sello); color: var(--sello); }
.chip[aria-pressed='true'] { background: var(--sello-suave); border-color: var(--sello); color: var(--sello); }
.chip-n { font-size: var(--t-xs); color: var(--texto-3); font-variant-numeric: tabular-nums; }
.chip[aria-pressed='true'] .chip-n { color: inherit; }

.grupo + .grupo { border-top: 1px solid var(--linea); }
.grupo-titulo {
  font-size: var(--t-xs); font-weight: 650; text-transform: none; color: var(--texto-3);
  padding: var(--e-3) var(--e-6); background: var(--superficie-2); border-bottom: 1px solid var(--linea);
}
.vista-previa { max-height: 260px; overflow-y: auto; }

@media (max-width: 960px) {
  .catalogo { grid-template-columns: 1fr; }
  .como-usar { position: static; order: -1; }
}
@media (max-width: 720px) {
  .grupo-titulo { padding: var(--e-3) var(--e-4); }
}
</style>

<script setup>
// Parámetros del sistema, editables uno a uno.
import { reactive, computed, watch } from 'vue'
import { Save, Info, RotateCcw } from '@lucide/vue'
import { api } from '@/api'
import { useCarga } from '@/composables/utiles'
import { useAvisos } from '@/stores/avisos'
import Cargando from '@/components/ui/Cargando.vue'

const avisos = useAvisos()

const PARAMETROS = {
  plazo_dias_tramite: { etiqueta: 'Plazo para elaborar un trámite', unidad: 'días', vacio: true, ayudaVacio: 'Déjelo vacío para no controlar plazos.' },
  asunto_max_caracteres: { etiqueta: 'Largo máximo del asunto', unidad: 'caracteres' },
  pdf_max_mb: { etiqueta: 'Tamaño máximo del informe PDF', unidad: 'MB' },
  sesion_inactividad_minutos: { etiqueta: 'Cierre de sesión por inactividad', unidad: 'minutos' },
  ingreso_max_intentos: { etiqueta: 'Intentos de ingreso antes del bloqueo', unidad: 'intentos' },
  ingreso_bloqueo_minutos: { etiqueta: 'Duración del bloqueo', unidad: 'minutos' },
  anios_retencion_auditoria: { etiqueta: 'Conservación de la auditoría', unidad: 'años' },
  respaldos_retenidos: { etiqueta: 'Respaldos diarios que se conservan', unidad: 'respaldos' },
  prompts_aviso: { etiqueta: 'Aviso junto a cada prompt', texto: true, vacio: true }
}
const GRUPOS = [
  { titulo: 'Trámites', claves: ['plazo_dias_tramite', 'asunto_max_caracteres', 'pdf_max_mb'] },
  { titulo: 'Seguridad', claves: ['sesion_inactividad_minutos', 'ingreso_max_intentos', 'ingreso_bloqueo_minutos'], nota: 'Los cambios de seguridad se aplican en los próximos ingresos; las sesiones abiertas no se ven afectadas.' },
  { titulo: 'Conservación', claves: ['anios_retencion_auditoria', 'respaldos_retenidos'] },
  { titulo: 'Prompts', claves: ['prompts_aviso'] }
]

const { datos, cargando, error } = useCarga(() => api.configuracion.listar(), { inicial: [] })

// Estado de edición por clave
const valores = reactive({})
const guardados = reactive({})
const errores = reactive({})
const guardando = reactive({})
watch(datos, (lista) => {
  ;(lista || []).forEach((p) => {
    guardados[p.clave] = p.valor ?? ''
    valores[p.clave] = p.valor ?? ''
  })
}, { immediate: true })

const porClave = computed(() => Object.fromEntries((datos.value || []).map((p) => [p.clave, p])))
const grupos = computed(() => {
  const conocidas = new Set(GRUPOS.flatMap((g) => g.claves))
  const lista = GRUPOS.map((g) => ({ ...g, claves: g.claves.filter((c) => porClave.value[c]) }))
  const otras = Object.keys(porClave.value).filter((c) => !conocidas.has(c))
  if (otras.length) lista.push({ titulo: 'Otros', claves: otras })
  return lista.filter((g) => g.claves.length)
})

const meta = (c) => PARAMETROS[c] || { etiqueta: c }
const cambiado = (c) => String(valores[c] ?? '') !== String(guardados[c] ?? '')

function validar(c) {
  const v = String(valores[c] ?? '').trim()
  const m = meta(c)
  if (m.texto) return ''
  if (v === '') return m.vacio ? '' : 'Este parámetro no puede quedar vacío.'
  if (!/^\d+$/.test(v)) return 'Ingrese un número entero, sin decimales.'
  if (Number(v) < 1) return 'Debe ser mayor que cero.'
  return ''
}

async function guardar(c) {
  errores[c] = validar(c)
  if (errores[c]) return
  guardando[c] = true
  try {
    const valor = meta(c).texto ? String(valores[c] ?? '') : String(valores[c] ?? '').trim()
    const r = await api.configuracion.actualizar(c, valor)
    guardados[c] = r?.valor ?? ''
    valores[c] = r?.valor ?? ''
    avisos.exito(`${meta(c).etiqueta}: cambio guardado`)
  } catch (e) {
    errores[c] = e.campos?.valor || e.message || 'No se pudo guardar.'
    avisos.error(e.message || 'No se pudo guardar el parámetro.')
  } finally {
    guardando[c] = false
  }
}
function deshacer(c) { valores[c] = guardados[c]; errores[c] = '' }
</script>

<template>
  <div class="pagina">
    <header class="pagina-cabecera">
      <div>
        <h1>Configuración</h1>
        <p>Ajuste los parámetros generales del repositorio. Cada parámetro se guarda por separado y el cambio queda en la auditoría.</p>
      </div>
    </header>

    <Cargando v-if="cargando && !datos.length" texto="Cargando parámetros…" />
    <div v-else-if="error" class="mensaje mensaje-peligro" role="alert">{{ error }}</div>

    <template v-else>
      <section v-for="g in grupos" :key="g.titulo" class="panel" :aria-labelledby="`grupo-${g.titulo}`">
        <div class="panel-cabecera"><h2 :id="`grupo-${g.titulo}`">{{ g.titulo }}</h2></div>
        <div v-if="g.nota" class="panel-cuerpo nota-grupo">
          <div class="mensaje mensaje-info"><Info aria-hidden="true" /><span>{{ g.nota }}</span></div>
        </div>
        <ul class="parametros">
          <li v-for="c in g.claves" :key="c" class="parametro">
            <form class="parametro-form" novalidate @submit.prevent="guardar(c)">
              <div class="parametro-texto">
                <label :for="`param-${c}`" class="etiqueta">{{ meta(c).etiqueta }}</label>
                <p :id="`param-${c}-ayuda`" class="ayuda">
                  {{ porClave[c].descripcion }}<template v-if="meta(c).ayudaVacio"> {{ meta(c).ayudaVacio }}</template>
                </p>
              </div>
              <div class="parametro-control" :class="{ ancho: meta(c).texto }">
                <textarea
                  v-if="meta(c).texto" :id="`param-${c}`" v-model="valores[c]" class="area-texto" rows="3"
                  :aria-invalid="!!errores[c]" :aria-describedby="`param-${c}-ayuda param-${c}-error`"
                />
                <div v-else class="con-unidad">
                  <input
                    :id="`param-${c}`" v-model="valores[c]" type="number" inputmode="numeric" min="1" step="1" class="entrada"
                    :placeholder="meta(c).vacio ? 'Sin control' : ''" :aria-invalid="!!errores[c]" :aria-describedby="`param-${c}-ayuda param-${c}-error`"
                  />
                  <span v-if="meta(c).unidad" class="unidad">{{ meta(c).unidad }}</span>
                </div>
                <div class="fila parametro-acciones">
                  <button v-if="cambiado(c)" type="button" class="boton boton-fantasma boton-pequeno" @click="deshacer(c)"><RotateCcw aria-hidden="true" /> Deshacer</button>
                  <button type="submit" class="boton boton-primario boton-pequeno" :disabled="!cambiado(c) || guardando[c]" :aria-label="`Guardar ${meta(c).etiqueta}`">
                    <Save aria-hidden="true" /> {{ guardando[c] ? 'Guardando…' : 'Guardar' }}
                  </button>
                </div>
                <span v-if="errores[c]" :id="`param-${c}-error`" class="error-campo" role="alert">{{ errores[c] }}</span>
              </div>
            </form>
          </li>
        </ul>
      </section>
    </template>
  </div>
</template>

<style scoped>
.nota-grupo { padding-bottom: 0; }
.parametros { list-style: none; margin: 0; padding: 0; }
.parametro + .parametro { border-top: 1px solid var(--linea); }
.parametro-form { display: grid; grid-template-columns: minmax(0, 1fr) minmax(240px, 320px); gap: var(--e-3) var(--e-6); padding: var(--e-4) var(--e-6); align-items: start; }
.parametro-texto .ayuda { margin-top: 2px; font-size: var(--t-sm); color: var(--texto-2); }
.parametro-control { display: flex; flex-direction: column; gap: var(--e-2); }
.parametro-control.ancho { grid-column: 1 / -1; }
.con-unidad { display: flex; align-items: center; gap: var(--e-2); }
.con-unidad .entrada { max-width: 140px; }
.unidad { color: var(--texto-2); font-size: var(--t-sm); }
.parametro-acciones { justify-content: flex-end; }
@media (max-width: 720px) {
  .parametro-form { grid-template-columns: 1fr; padding: var(--e-4); }
  .parametro-acciones { justify-content: flex-start; }
}
</style>

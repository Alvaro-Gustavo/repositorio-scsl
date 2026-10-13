<script setup>
// Bandeja "Por asignar": tramites RECIBIDO esperando abogado.
// Cada fila tiene su propio selector; al asignar, la fila sale de la lista.
import { ref, computed, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { Inbox, Plus, UserCheck, RefreshCw } from '@lucide/vue'
import { api } from '@/api'
import { useSesion } from '@/stores/sesion'
import { useCatalogos } from '@/stores/catalogos'
import { useAvisos } from '@/stores/avisos'
import { useCarga } from '@/composables/utiles'
import { diasDesde, formatoFecha, plural } from '@/utils/formato'
import Cargando from '@/components/ui/Cargando.vue'
import EstadoVacio from '@/components/ui/EstadoVacio.vue'

const sesion = useSesion()
const catalogos = useCatalogos()
const avisos = useAvisos()

const { datos: lista, cargando, error, cargar } = useCarga(() => api.tramites.porAsignar(), { inicial: [] })
const verCarga = computed(() => sesion.puede('VER_TABLERO'))
const pendientes = ref([])
const eleccion = ref({})
const asignando = ref({})

const abogados = computed(() => (catalogos.datos.profesionales || []).filter((p) => p.usuario_id && p.activo))

// Carga actual: cuantos tramites tiene cada abogado en elaboracion.
const cargaAbogados = computed(() => {
  const cuenta = new Map()
  pendientes.value.forEach((t) => { if (t.profesional) cuenta.set(t.profesional.id, (cuenta.get(t.profesional.id) || 0) + 1) })
  return abogados.value.map((p) => ({ id: p.id, nombre: p.nombre, cantidad: cuenta.get(p.id) || 0 }))
    .sort((a, b) => a.cantidad - b.cantidad || a.nombre.localeCompare(b.nombre, 'es'))
})
const maxCarga = computed(() => Math.max(1, ...cargaAbogados.value.map((a) => a.cantidad)))

async function cargarCarga() {
  if (!verCarga.value) return
  try { pendientes.value = await api.tramites.pendientes() } catch { pendientes.value = [] }
}

onMounted(() => {
  catalogos.obtener('profesionales').catch(() => {})
  cargarCarga()
})

function recargar() {
  cargar()
  cargarCarga()
}

async function asignar(t) {
  const profesionalId = eleccion.value[t.id]
  if (!profesionalId || asignando.value[t.id]) return
  asignando.value = { ...asignando.value, [t.id]: true }
  try {
    const r = await api.tramites.asignar(t.id, Number(profesionalId))
    lista.value = lista.value.filter((x) => x.id !== t.id)
    const nombre = r.profesional?.nombre_completo || abogados.value.find((p) => String(p.id) === String(profesionalId))?.nombre
    avisos.exito(`Trámite ${t.hoja_ruta} asignado a ${nombre}.`)
    if (verCarga.value) pendientes.value = [...pendientes.value, r]
  } catch (e) {
    avisos.error(e.message || 'No se pudo asignar el trámite.')
  } finally {
    const { [t.id]: _, ...resto } = asignando.value
    asignando.value = resto
  }
}

function hace(fecha) {
  const d = diasDesde(fecha)
  if (d === null) return '—'
  if (d <= 0) return 'hoy'
  if (d === 1) return 'ayer'
  return `hace ${d} días`
}
</script>

<template>
  <div class="pagina">
    <header class="pagina-cabecera">
      <div>
        <h1>Por asignar</h1>
        <p>Trámites recibidos que aún no tienen abogado. Elija a quién derivar cada uno.</p>
      </div>
      <div class="pagina-acciones">
        <button type="button" class="boton" :disabled="cargando" @click="recargar"><RefreshCw aria-hidden="true" /> Actualizar</button>
        <RouterLink v-if="sesion.puede('CREAR_REGISTRO')" to="/tramites/nuevo" class="boton boton-primario"><Plus aria-hidden="true" /> Registrar trámite</RouterLink>
      </div>
    </header>

    <section v-if="verCarga && cargaAbogados.length" class="carga panel" aria-labelledby="titulo-carga">
      <h2 id="titulo-carga" class="carga-titulo">Carga actual <span class="texto-3">en elaboración</span></h2>
      <ul class="carga-lista">
        <li v-for="a in cargaAbogados" :key="a.id">
          <span class="carga-nombre">{{ a.nombre }}</span>
          <span class="carga-pista" aria-hidden="true"><span :style="{ width: `${(100 * a.cantidad) / maxCarga}%` }" /></span>
          <span class="carga-valor">{{ a.cantidad }}<span class="sr-only"> en elaboración</span></span>
        </li>
      </ul>
    </section>

    <Cargando v-if="cargando && !lista.length" texto="Buscando trámites por asignar…" />
    <p v-else-if="error" class="mensaje mensaje-peligro" role="alert">{{ error }}</p>

    <div v-else-if="!lista.length" class="panel">
      <EstadoVacio :icono="Inbox" titulo="No hay trámites por asignar" texto="Todos los trámites recibidos ya tienen abogado. Los nuevos registros sin asignar aparecerán aquí.">
        <RouterLink v-if="sesion.puede('CREAR_REGISTRO')" to="/tramites/nuevo" class="boton boton-primario"><Plus aria-hidden="true" /> Registrar trámite</RouterLink>
      </EstadoVacio>
    </div>

    <section v-else class="panel" aria-labelledby="titulo-lista">
      <div class="panel-cabecera">
        <h2 id="titulo-lista">{{ plural(lista.length, 'trámite recibido', 'trámites recibidos') }}</h2>
        <span class="texto-3 texto-pequeno">Del más antiguo al más reciente</span>
      </div>
      <div class="tabla-contenedor">
        <table class="tabla tabla-apilable">
          <thead>
            <tr><th scope="col">Hoja de ruta</th><th scope="col">Asunto</th><th scope="col">Entidad</th><th scope="col">Tipo</th><th scope="col">Registrado</th><th scope="col">Asignar a</th></tr>
          </thead>
          <TransitionGroup tag="tbody" name="fila">
            <tr v-for="t in lista" :key="t.id">
              <td data-etiqueta="Hoja de ruta"><RouterLink :to="`/tramites/${t.id}`" class="codigo codigo-sello">{{ t.hoja_ruta }}</RouterLink></td>
              <td data-etiqueta="Asunto" class="asunto">{{ t.asunto }}</td>
              <td data-etiqueta="Entidad">{{ t.entidad?.nombre || '—' }}</td>
              <td data-etiqueta="Tipo">{{ t.tipo_tramite?.nombre || '—' }}</td>
              <td data-etiqueta="Registrado"><span :title="formatoFecha(t.creado_en)" :class="{ antiguo: diasDesde(t.creado_en) > 3 }">{{ hace(t.creado_en) }}</span></td>
              <td data-etiqueta="Asignar a" class="celda-asignar">
                <div class="asignar">
                  <label :for="`abogado-${t.id}`" class="sr-only">Abogado para {{ t.hoja_ruta }}</label>
                  <select :id="`abogado-${t.id}`" :value="eleccion[t.id] ?? ''" class="seleccion" :disabled="asignando[t.id]"
                    @change="eleccion[t.id] = $event.target.value">
                    <option value="" disabled>Elija abogado</option>
                    <option v-for="p in abogados" :key="p.id" :value="p.id">{{ p.nombre }}</option>
                  </select>
                  <button type="button" class="boton boton-primario" :disabled="!eleccion[t.id] || asignando[t.id]" @click="asignar(t)">
                    <UserCheck aria-hidden="true" /> {{ asignando[t.id] ? 'Asignando…' : 'Asignar' }}
                  </button>
                </div>
              </td>
            </tr>
          </TransitionGroup>
        </table>
      </div>
    </section>
  </div>
</template>

<style scoped>
.carga { padding: var(--e-4) var(--e-6); margin-bottom: var(--e-6); }
.carga-titulo { font-family: var(--fuente-texto); font-size: var(--t-sm); font-weight: 650; color: var(--texto-2); margin-bottom: var(--e-3); }
.carga-titulo .texto-3 { font-weight: 400; }
.carga-lista { list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: var(--e-2) var(--e-6); }
.carga-lista li { display: grid; grid-template-columns: minmax(0, 1fr) 72px 28px; align-items: center; gap: var(--e-2); font-size: var(--t-sm); }
.carga-nombre { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-weight: 600; }
.carga-pista { height: 8px; background: var(--superficie-2); border-radius: 2px; overflow: hidden; }
.carga-pista span { display: block; height: 100%; background: var(--elaboracion); }
.carga-valor { text-align: right; font-weight: 700; font-variant-numeric: tabular-nums; }

.asunto { max-width: 42ch; }
.antiguo { color: var(--aviso); font-weight: 600; }
.asignar { display: flex; gap: var(--e-2); align-items: center; }
.asignar .seleccion { min-width: 160px; }
.celda-asignar { min-width: 280px; }

.fila-leave-active { transition: opacity .25s; }
.fila-leave-to { opacity: 0; }

@media (max-width: 720px) {
  .carga { padding: var(--e-3) var(--e-4); }
  .tabla-apilable thead { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }
  .tabla-apilable, .tabla-apilable tbody, .tabla-apilable tr, .tabla-apilable td { display: block; width: 100%; }
  .tabla-apilable tr { padding: var(--e-3) var(--e-4); border-bottom: 1px solid var(--linea); }
  .tabla-apilable tbody tr:last-child { border-bottom: none; }
  .tabla-apilable td { border: none; padding: 4px 0; max-width: none; min-width: 0; }
  .tabla-apilable td::before { content: attr(data-etiqueta); display: block; font-size: var(--t-xs); color: var(--texto-3); }
  .tabla-apilable td:first-child::before, .tabla-apilable td.celda-asignar::before { display: none; }
  .celda-asignar { padding-top: var(--e-2) !important; }
  .asignar { flex-wrap: wrap; }
  .asignar .seleccion { flex: 1 1 100%; }
  .asignar .boton { flex: 1; }
}
</style>

<script setup>
// ABOGADO: sus tramites en elaboracion, del mas antiguo al mas reciente.
// JEFE/ADMIN (VER_TABLERO): todos los tramites en elaboracion, con filtro por abogado.
import { ref, computed } from 'vue'
import { RouterLink } from 'vue-router'
import { ClipboardCheck, FileUp, RefreshCw, FolderOpen } from '@lucide/vue'
import { api } from '@/api'
import { useSesion } from '@/stores/sesion'
import { useCarga } from '@/composables/utiles'
import { formatoFecha, plural } from '@/utils/formato'
import Cargando from '@/components/ui/Cargando.vue'
import EstadoVacio from '@/components/ui/EstadoVacio.vue'

const sesion = useSesion()
const supervisa = computed(() => sesion.puede('VER_TABLERO'))
const { datos, cargando, error, cargar } = useCarga(() => api.tramites.pendientes(), { inicial: [] })
const filtroAbogado = ref('')

const abogados = computed(() => {
  const mapa = new Map()
  ;(datos.value || []).forEach((t) => { if (t.profesional) mapa.set(String(t.profesional.id), t.profesional.nombre_completo) })
  return [...mapa.entries()].map(([id, nombre]) => ({ id, nombre })).sort((a, b) => a.nombre.localeCompare(b.nombre, 'es'))
})
const lista = computed(() => {
  const todos = [...(datos.value || [])].sort((a, b) => (b.dias_en_elaboracion ?? 0) - (a.dias_en_elaboracion ?? 0))
  return filtroAbogado.value ? todos.filter((t) => String(t.profesional?.id) === filtroAbogado.value) : todos
})
const vencidos = computed(() => lista.value.filter((t) => t.vencido).length)

// Concluir: el abogado asignado (o el administrador). El backend vuelve a verificarlo.
const puedeConcluir = (t) => sesion.puede('SUBIR_INFORME') && (sesion.rol === 'ADMIN' || t.profesional?.usuario_id === sesion.usuario?.id)

function dias(n) {
  if (n === null || n === undefined) return '—'
  if (n <= 0) return 'desde hoy'
  return plural(n, 'día', 'días')
}
</script>

<template>
  <div class="pagina">
    <header class="pagina-cabecera">
      <div>
        <h1>{{ supervisa ? 'Trámites en elaboración' : 'Mis pendientes' }}</h1>
        <p v-if="supervisa">Trámites asignados que aún no tienen informe, del que lleva más tiempo al más reciente.</p>
        <p v-else>Trámites que tiene asignados y esperan su informe. Empiece por los más antiguos.</p>
      </div>
      <div class="pagina-acciones">
        <button type="button" class="boton" :disabled="cargando" @click="cargar()"><RefreshCw aria-hidden="true" /> Actualizar</button>
      </div>
    </header>

    <Cargando v-if="cargando && !datos?.length" texto="Cargando pendientes…" />
    <p v-else-if="error" class="mensaje mensaje-peligro" role="alert">{{ error }}</p>

    <div v-else-if="!datos?.length" class="panel">
      <EstadoVacio v-if="supervisa" :icono="ClipboardCheck" titulo="No hay trámites en elaboración"
        texto="Ningún abogado tiene trámites pendientes de informe en este momento.">
        <RouterLink v-if="sesion.puede('ASIGNAR_TRAMITE')" to="/asignacion" class="boton">Ver trámites por asignar</RouterLink>
      </EstadoVacio>
      <EstadoVacio v-else :icono="ClipboardCheck" titulo="No tiene trámites pendientes"
        texto="Cuando le asignen un trámite aparecerá aquí para que suba su informe.">
        <RouterLink to="/consulta" class="boton">Ir a la búsqueda</RouterLink>
      </EstadoVacio>
    </div>

    <section v-else class="panel" aria-labelledby="titulo-pendientes">
      <div class="panel-cabecera">
        <h2 id="titulo-pendientes">
          {{ plural(lista.length, 'trámite', 'trámites') }}
          <span v-if="vencidos" class="insignia insignia-peligro">{{ plural(vencidos, 'vencido', 'vencidos') }}</span>
        </h2>
        <div v-if="supervisa && abogados.length > 1" class="filtro">
          <label for="filtro-abogado" class="etiqueta">Abogado</label>
          <select id="filtro-abogado" v-model="filtroAbogado" class="seleccion">
            <option value="">Todos</option>
            <option v-for="a in abogados" :key="a.id" :value="a.id">{{ a.nombre }}</option>
          </select>
        </div>
      </div>

      <p v-if="!lista.length" class="texto-2 texto-pequeno sin-filas">Este abogado no tiene trámites en elaboración.</p>
      <div v-else class="tabla-contenedor">
        <table class="tabla tabla-apilable">
          <thead>
            <tr>
              <th scope="col">Hoja de ruta</th>
              <th scope="col">Asunto</th>
              <th scope="col">Entidad</th>
              <th v-if="supervisa" scope="col">Abogado</th>
              <th scope="col" class="num">En elaboración</th>
              <th scope="col"><span class="sr-only">Acciones</span></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="t in lista" :key="t.id" :class="{ vencido: t.vencido }">
              <td data-etiqueta="Hoja de ruta">
                <RouterLink :to="`/tramites/${t.id}`" class="codigo codigo-sello">{{ t.hoja_ruta }}</RouterLink>
                <span class="texto-3 texto-xs bloque">{{ t.tipo_tramite?.nombre }}</span>
              </td>
              <td data-etiqueta="Asunto" class="asunto">{{ t.asunto }}</td>
              <td data-etiqueta="Entidad">{{ t.entidad?.nombre || '—' }}</td>
              <td v-if="supervisa" data-etiqueta="Abogado">{{ t.profesional?.nombre_completo || '—' }}</td>
              <td data-etiqueta="En elaboración" class="num">
                <span class="dias" :title="`Asignado el ${formatoFecha(t.fecha_asignacion)}`">{{ dias(t.dias_en_elaboracion) }}</span>
                <span v-if="t.vencido" class="insignia insignia-peligro">Vencido</span>
              </td>
              <td class="acciones">
                <div class="fila">
                  <RouterLink v-if="puedeConcluir(t)" :to="`/tramites/${t.id}/concluir`" class="boton boton-primario boton-pequeno">
                    <FileUp aria-hidden="true" /> Concluir
                  </RouterLink>
                  <RouterLink :to="`/tramites/${t.id}`" class="boton boton-fantasma boton-pequeno" :aria-label="`Ver expediente ${t.hoja_ruta}`">
                    <FolderOpen aria-hidden="true" /> Expediente
                  </RouterLink>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>

<style scoped>
.panel-cabecera h2 { display: flex; align-items: center; gap: var(--e-3); flex-wrap: wrap; }
.filtro { display: flex; align-items: center; gap: var(--e-2); }
.filtro .seleccion { min-width: 200px; min-height: 36px; padding-top: 4px; padding-bottom: 4px; }
.sin-filas { padding: var(--e-6); }
.bloque { display: block; margin-top: 4px; }
.asunto { max-width: 46ch; }
.dias { display: block; font-weight: 650; white-space: nowrap; }
td.num .insignia { margin-top: 4px; }
tr.vencido td:first-child { box-shadow: inset 3px 0 0 var(--peligro); }
tr.vencido .dias { color: var(--peligro); }
.acciones .fila { justify-content: flex-end; flex-wrap: nowrap; }

@media (max-width: 720px) {
  .filtro { width: 100%; }
  .filtro .seleccion { flex: 1; min-width: 0; }
  .tabla-apilable thead { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }
  .tabla-apilable, .tabla-apilable tbody, .tabla-apilable tr, .tabla-apilable td { display: block; width: 100%; }
  .tabla-apilable tr { padding: var(--e-3) var(--e-4); border-bottom: 1px solid var(--linea); }
  .tabla-apilable tbody tr:last-child { border-bottom: none; }
  .tabla-apilable td { border: none; padding: 4px 0; max-width: none; text-align: left; }
  .tabla-apilable td[data-etiqueta]:not(:first-child)::before { content: attr(data-etiqueta); display: block; font-size: var(--t-xs); color: var(--texto-3); }
  tr.vencido td:first-child { box-shadow: none; }
  tr.vencido { box-shadow: inset 3px 0 0 var(--peligro); }
  .dias { display: inline; margin-right: var(--e-2); }
  .acciones .fila { justify-content: flex-start; flex-wrap: wrap; margin-top: var(--e-2); }
}
</style>

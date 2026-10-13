<script setup>
// Campana de notificaciones de la barra superior. Consulta cada minuto (y al volver
// a la pestaña) si hay avisos nuevos, por ejemplo un trámite asignado al abogado.
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { Bell, BellRing, FileInput, ArrowRightLeft, CheckCheck } from '@lucide/vue'
import { api } from '@/api'
import { useAvisos } from '@/stores/avisos'
import { formatoFechaHora } from '@/utils/formato'

const INTERVALO_MS = 60000
const ICONOS = { TRAMITE_ASIGNADO: FileInput, TRAMITE_REASIGNADO: ArrowRightLeft }

const router = useRouter()
const avisos = useAvisos()
const abierto = ref(false)
const items = ref([])
const noLeidas = ref(0)
const raiz = ref(null)
let primeraCarga = true
let temporizador = null

const etiqueta = computed(() => (noLeidas.value ? `Notificaciones: ${noLeidas.value} sin leer` : 'Notificaciones'))

async function cargar() {
  try {
    const r = await api.notificaciones.listar()
    // Aviso emergente solo cuando llega algo nuevo después de la primera carga.
    if (!primeraCarga && r.no_leidas > noLeidas.value) {
      const nueva = r.items.find((n) => !n.leida_en)
      if (nueva) avisos.info(nueva.titulo)
    }
    items.value = r.items
    noLeidas.value = r.no_leidas
    primeraCarga = false
  } catch { /* sin conexión: se reintenta en el siguiente ciclo */ }
}

async function abrirNotificacion(n) {
  abierto.value = false
  if (!n.leida_en) {
    n.leida_en = new Date().toISOString()
    noLeidas.value = Math.max(0, noLeidas.value - 1)
    api.notificaciones.marcarLeida(n.id).catch(() => {})
  }
  if (n.tramite_id) router.push(`/tramites/${n.tramite_id}`)
}

async function marcarTodas() {
  await api.notificaciones.marcarTodas().catch(() => {})
  items.value.forEach((n) => { n.leida_en ||= new Date().toISOString() })
  noLeidas.value = 0
}

function alternar() {
  abierto.value = !abierto.value
  if (abierto.value) cargar()
}
function fuera(e) {
  if (abierto.value && raiz.value && !raiz.value.contains(e.target)) abierto.value = false
}
function alVolver() {
  if (document.visibilityState === 'visible') cargar()
}

onMounted(() => {
  cargar()
  temporizador = setInterval(() => { if (document.visibilityState === 'visible') cargar() }, INTERVALO_MS)
  document.addEventListener('pointerdown', fuera)
  document.addEventListener('visibilitychange', alVolver)
})
onBeforeUnmount(() => {
  clearInterval(temporizador)
  document.removeEventListener('pointerdown', fuera)
  document.removeEventListener('visibilitychange', alVolver)
})
</script>

<template>
  <div ref="raiz" class="notificaciones" @keydown.esc="abierto = false">
    <button type="button" class="campana" :class="{ activa: noLeidas }" :aria-label="etiqueta" :title="etiqueta"
      :aria-expanded="abierto" aria-haspopup="true" aria-controls="panel-notificaciones" @click="alternar">
      <BellRing v-if="noLeidas" aria-hidden="true" /><Bell v-else aria-hidden="true" />
      <span v-if="noLeidas" class="contador" aria-hidden="true">{{ noLeidas > 9 ? '9+' : noLeidas }}</span>
    </button>

    <div v-if="abierto" id="panel-notificaciones" class="panel-notif" role="dialog" aria-label="Notificaciones">
      <header class="notif-cabecera">
        <strong>Notificaciones</strong>
        <button v-if="noLeidas" type="button" class="enlace-boton" @click="marcarTodas"><CheckCheck aria-hidden="true" /> Marcar todas como leídas</button>
      </header>
      <p v-if="!items.length" class="notif-vacio">No tiene notificaciones.</p>
      <ul v-else class="notif-lista">
        <li v-for="n in items" :key="n.id">
          <button type="button" class="notif" :class="{ 'no-leida': !n.leida_en }" @click="abrirNotificacion(n)">
            <span class="notif-icono" :class="n.tipo === 'TRAMITE_REASIGNADO' ? 'icono-reasignado' : 'icono-asignado'" aria-hidden="true">
              <component :is="ICONOS[n.tipo] || Bell" />
            </span>
            <span class="notif-texto">
              <strong>{{ n.titulo }}</strong>
              <span v-if="n.mensaje" class="notif-mensaje">{{ n.mensaje }}</span>
              <small>{{ formatoFechaHora(n.creado_en) }}</small>
            </span>
            <span v-if="!n.leida_en" class="punto" aria-label="Sin leer" />
          </button>
        </li>
      </ul>
    </div>
  </div>
</template>

<style scoped>
.notificaciones { position: relative; }
.campana {
  position: relative; width: 40px; height: 40px; display: grid; place-items: center;
  border: 1px solid transparent; border-radius: 50%; background: none; color: var(--texto-2); cursor: pointer;
}
.campana:hover, .campana[aria-expanded='true'] { background: var(--superficie-2); border-color: var(--linea); }
.campana.activa { color: var(--sello); }
.campana svg { width: 20px; height: 20px; }
.contador {
  position: absolute; top: 2px; right: 1px; min-width: 18px; height: 18px; padding: 0 5px; border-radius: 999px;
  background: var(--peligro); color: var(--texto-inverso); font-size: 0.68rem; font-weight: 700; line-height: 18px;
  border: 2px solid var(--superficie);
}
.panel-notif {
  position: absolute; right: 0; top: calc(100% + 6px); width: 380px; max-height: 480px; overflow-y: auto; z-index: 30;
  background: var(--superficie); border: 1px solid var(--linea); border-radius: var(--radio-panel); box-shadow: var(--sombra-flotante);
}
.notif-cabecera {
  position: sticky; top: 0; display: flex; justify-content: space-between; align-items: center; gap: 8px;
  padding: 12px 14px; background: var(--superficie); border-bottom: 1px solid var(--linea);
}
.enlace-boton { display: inline-flex; align-items: center; gap: 4px; border: none; background: none; color: var(--sello); font-size: var(--t-xs); cursor: pointer; padding: 2px; }
.enlace-boton svg { width: 14px; height: 14px; }
.notif-vacio { padding: 24px 14px; text-align: center; color: var(--texto-3); font-size: var(--t-sm); }
.notif-lista { list-style: none; margin: 0; padding: 4px; }
.notif {
  width: 100%; display: flex; gap: 12px; align-items: flex-start; text-align: left; padding: 10px; border: none;
  border-radius: var(--radio-control); background: none; color: var(--texto); cursor: pointer;
}
.notif:hover { background: var(--superficie-2); }
.notif.no-leida { background: var(--sello-suave); }
.notif.no-leida:hover { background: color-mix(in srgb, var(--sello-suave) 70%, var(--linea)); }
.notif-icono { width: 34px; height: 34px; flex: none; border-radius: 50%; display: grid; place-items: center; }
.notif-icono svg { width: 17px; height: 17px; }
.icono-asignado { background: var(--elaboracion-suave); color: var(--elaboracion); }
.icono-reasignado { background: var(--recibido-suave); color: var(--recibido); }
.notif-texto { flex: 1; min-width: 0; display: grid; gap: 2px; }
.notif-texto strong { font-size: var(--t-sm); line-height: 1.3; }
.notif-mensaje { font-size: var(--t-xs); color: var(--texto-2); display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.notif-texto small { font-size: var(--t-xs); color: var(--texto-3); }
.punto { width: 9px; height: 9px; margin-top: 6px; flex: none; border-radius: 50%; background: var(--sello); }
@media (max-width: 720px) {
  .panel-notif { position: fixed; left: 12px; right: 12px; top: calc(var(--alto-superior) + 4px); width: auto; }
}
</style>

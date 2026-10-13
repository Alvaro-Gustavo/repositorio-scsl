<script setup>
// Marco de la aplicacion: barra lateral (menu por rol), barra superior
// (busqueda universal, estado local, usuario) y el contenido de cada pagina.
import { computed, ref, watch, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter, RouterLink, RouterView } from 'vue-router'
import { Search, Lock, LogOut, UserRound, Menu, X, FlaskConical, RotateCcw } from '@lucide/vue'
import { useSesion } from '@/stores/sesion'
import { useAvisos } from '@/stores/avisos'
import { api, MODO } from '@/api'
import { menuPara } from '@/navegacion'
import AccesoIA from './AccesoIA.vue'
import Notificaciones from './Notificaciones.vue'
import { ROLES } from '@/utils/constantes'

const sesion = useSesion()
const avisos = useAvisos()
const route = useRoute()
const router = useRouter()

const menu = computed(() => menuPara(sesion))
const lateralAbierta = ref(false)
const menuUsuario = ref(false)
const texto = ref('')

const iniciales = computed(() => (sesion.usuario?.nombre_completo || '?')
  .replace(/^(Dr|Dra|Lic|Ing)\.?\s+/i, '').split(' ').filter(Boolean).slice(0, 2).map((p) => p[0]).join('').toUpperCase())

watch(() => route.fullPath, () => { lateralAbierta.value = false; menuUsuario.value = false })
watch(() => route.query.q, (q) => { if (route.name === 'consulta') texto.value = q || '' }, { immediate: true })

function buscar() {
  router.push({ name: 'consulta', query: texto.value.trim() ? { q: texto.value.trim() } : {} })
}

async function salir() {
  await sesion.salir()
  router.push({ name: 'ingresar' })
}

function reiniciarDemo() {
  if (!window.confirm('Se borrarán los cambios hechos en la demostración y se cargarán los datos iniciales. ¿Continuar?')) return
  api.demo.reiniciar()
  window.location.reload()
}

// Cierre de sesion por inactividad (30 minutos, igual que el servidor).
const MINUTOS_INACTIVIDAD = 30
let temporizador = null
function reiniciarTemporizador() {
  clearTimeout(temporizador)
  temporizador = setTimeout(async () => {
    await sesion.salir()
    avisos.aviso('La sesión se cerró por inactividad.')
    router.push({ name: 'ingresar' })
  }, MINUTOS_INACTIVIDAD * 60000)
}
const eventos = ['pointerdown', 'keydown', 'scroll']
onMounted(() => { eventos.forEach((e) => window.addEventListener(e, reiniciarTemporizador, { passive: true })); reiniciarTemporizador() })
onBeforeUnmount(() => { eventos.forEach((e) => window.removeEventListener(e, reiniciarTemporizador)); clearTimeout(temporizador) })

function esActiva(a) {
  return a === '/' ? route.path === '/' : route.path === a || route.path.startsWith(a + '/')
}
</script>

<template>
  <div class="marco">
    <a class="saltar" href="#contenido">Saltar al contenido</a>

    <aside class="barra-lateral" :class="{ abierta: lateralAbierta }" aria-label="Menú principal">
      <RouterLink to="/" class="marca">
        <img src="/escudo.svg" alt="" width="40" height="40" />
        <span>
          <strong>Repositorio SCSL</strong>
          <small>Subcontraloría de Servicios Legales</small>
        </span>
      </RouterLink>
      <button class="cerrar-lateral boton-icono" type="button" aria-label="Cerrar menú" @click="lateralAbierta = false"><X /></button>

      <nav>
        <div v-for="g in menu" :key="g.grupo" class="grupo">
          <p class="grupo-titulo">{{ g.grupo }}</p>
          <RouterLink v-for="o in g.opciones" :key="o.a + o.etiqueta" :to="o.a" class="opcion" :class="{ activa: esActiva(o.a) }"
            :aria-current="esActiva(o.a) ? 'page' : undefined">
            <component :is="o.icono" aria-hidden="true" />
            <span>{{ o.etiqueta }}</span>
          </RouterLink>
        </div>
      </nav>

      <div class="pie-lateral">
        <span class="estado-local"><Lock aria-hidden="true" /> Repositorio local cerrado</span>
      </div>
    </aside>
    <div v-if="lateralAbierta" class="velo" @click="lateralAbierta = false" />

    <div class="marco-contenido">
      <header class="barra-superior">
        <button class="boton boton-icono abrir-lateral" type="button" aria-label="Abrir menú" @click="lateralAbierta = true"><Menu /></button>

        <form v-if="sesion.puede('BUSCAR')" class="busqueda-global" role="search" @submit.prevent="buscar">
          <Search aria-hidden="true" />
          <label for="busqueda-global" class="sr-only">Búsqueda universal</label>
          <input id="busqueda-global" v-model="texto" type="search" autocomplete="off"
            placeholder="Hoja de ruta, entidad, número de documento, abogado, asunto…" />
        </form>
        <div v-else class="espacio" />

        <span v-if="MODO === 'simulado'" class="chip-demo" title="Datos de demostración guardados en este navegador">
          <FlaskConical aria-hidden="true" /> Demostración
          <button type="button" class="reiniciar" title="Reiniciar datos de demostración" aria-label="Reiniciar datos de demostración" @click="reiniciarDemo"><RotateCcw /></button>
        </span>

        <AccesoIA class="acceso-ia-barra" />
        <Notificaciones />

        <div class="usuario">
          <button type="button" class="usuario-boton" :aria-expanded="menuUsuario" aria-haspopup="menu" @click="menuUsuario = !menuUsuario">
            <span class="avatar" aria-hidden="true">{{ iniciales }}</span>
            <span class="usuario-texto">
              <strong>{{ sesion.usuario?.nombre_completo }}</strong>
              <small>{{ ROLES[sesion.rol] }}</small>
            </span>
          </button>
          <div v-if="menuUsuario" class="menu-usuario" role="menu" @keydown.esc="menuUsuario = false">
            <p class="menu-correo">{{ sesion.usuario?.correo }}</p>
            <RouterLink to="/perfil" role="menuitem"><UserRound aria-hidden="true" /> Mi perfil</RouterLink>
            <button type="button" role="menuitem" @click="salir"><LogOut aria-hidden="true" /> Salir</button>
          </div>
        </div>
      </header>

      <main id="contenido" tabindex="-1">
        <RouterView />
      </main>
    </div>
  </div>
</template>

<style scoped>
.marco { display: grid; grid-template-columns: var(--ancho-lateral) minmax(0, 1fr); min-height: 100vh; }
.saltar { position: absolute; left: -999px; top: 8px; z-index: 50; background: var(--superficie); padding: 8px 12px; border-radius: var(--radio-control); }
.saltar:focus { left: 8px; }

.barra-lateral {
  position: sticky; top: 0; height: 100vh; overflow-y: auto;
  background: var(--tinta); color: #dbe4f1; display: flex; flex-direction: column;
}
.marca { display: flex; align-items: center; gap: 12px; padding: 20px 18px 18px; color: #fff; text-decoration: none; border-bottom: 1px solid rgba(255,255,255,.1); }
.marca:hover { text-decoration: none; }
.marca strong { display: block; font-family: var(--fuente-titulo); font-size: 1.15rem; font-weight: 600; letter-spacing: .01em; }
.marca small { display: block; font-size: var(--t-xs); color: #a9b9d1; line-height: 1.3; margin-top: 2px; }
.cerrar-lateral { display: none; }
nav { padding: 12px 10px; flex: 1; }
.grupo + .grupo { margin-top: 18px; }
.grupo-titulo { font-size: var(--t-xs); color: #8ea2c0; padding: 0 10px 6px; font-weight: 600; }
.opcion {
  display: flex; align-items: center; gap: 10px; padding: 9px 10px; border-radius: var(--radio-control);
  color: #dbe4f1; font-size: var(--t-sm); font-weight: 500; text-decoration: none; position: relative;
}
.opcion svg { width: 18px; height: 18px; flex: none; opacity: .85; }
.opcion:hover { background: rgba(255,255,255,.07); color: #fff; text-decoration: none; }
.opcion.activa { background: rgba(255,255,255,.12); color: #fff; font-weight: 650; }
.opcion.activa::before { content: ''; position: absolute; left: -10px; top: 8px; bottom: 8px; width: 3px; border-radius: 0 3px 3px 0; background: #8fb4e6; }
.pie-lateral { padding: 14px 18px; border-top: 1px solid rgba(255,255,255,.1); }
.estado-local { display: inline-flex; align-items: center; gap: 8px; font-size: var(--t-xs); color: #a9b9d1; }
.estado-local svg { width: 14px; height: 14px; }

.marco-contenido { min-width: 0; display: flex; flex-direction: column; }
.barra-superior {
  position: sticky; top: 0; z-index: 20; height: var(--alto-superior);
  display: flex; align-items: center; gap: 16px; padding: 0 24px;
  background: var(--superficie); border-bottom: 1px solid var(--linea);
}
.abrir-lateral { display: none; }
.busqueda-global { flex: 1; max-width: 620px; position: relative; }
.busqueda-global svg { position: absolute; left: 12px; top: 50%; transform: translateY(-50%); width: 18px; height: 18px; color: var(--texto-3); }
.busqueda-global input {
  width: 100%; height: 40px; padding: 0 14px 0 40px; border: 1px solid var(--linea-fuerte);
  border-radius: 999px; background: var(--superficie-2); font-size: var(--t-sm);
}
.busqueda-global input:focus { outline: none; background: var(--superficie); border-color: var(--sello); box-shadow: var(--foco); }
.espacio { flex: 1; }
.chip-demo { display: inline-flex; align-items: center; gap: 6px; padding: 4px 6px 4px 10px; border-radius: 999px; background: var(--aviso-suave); color: var(--aviso); font-size: var(--t-xs); font-weight: 650; white-space: nowrap; }
.chip-demo svg { width: 14px; height: 14px; }
.reiniciar { border: none; background: none; color: inherit; padding: 2px; border-radius: 50%; cursor: pointer; display: inline-flex; }
.reiniciar:hover { background: rgba(161,82,10,.12); }
.acceso-ia-barra { margin-left: auto; }
.usuario { position: relative; }
.usuario-boton { display: flex; align-items: center; gap: 10px; border: none; background: none; cursor: pointer; padding: 4px 6px; border-radius: var(--radio-control); text-align: left; }
.usuario-boton:hover { background: var(--superficie-2); }
.avatar { width: 36px; height: 36px; border-radius: 50%; background: var(--sello-suave); color: var(--tinta); display: grid; place-items: center; font-weight: 700; font-size: var(--t-sm); }
.usuario-texto strong { display: block; font-size: var(--t-sm); line-height: 1.2; }
.usuario-texto small { display: block; font-size: var(--t-xs); color: var(--texto-3); }
.menu-usuario { position: absolute; right: 0; top: calc(100% + 6px); min-width: 220px; background: var(--superficie); border: 1px solid var(--linea); border-radius: var(--radio-panel); box-shadow: var(--sombra-flotante); padding: 6px; z-index: 30; }
.menu-correo { font-size: var(--t-xs); color: var(--texto-3); padding: 6px 10px 8px; border-bottom: 1px solid var(--linea); margin-bottom: 4px; }
.menu-usuario a, .menu-usuario button { display: flex; align-items: center; gap: 10px; width: 100%; padding: 8px 10px; border: none; background: none; border-radius: var(--radio-control); color: var(--texto); font-size: var(--t-sm); cursor: pointer; text-decoration: none; }
.menu-usuario a:hover, .menu-usuario button:hover { background: var(--superficie-2); text-decoration: none; }
.menu-usuario svg { width: 16px; height: 16px; color: var(--texto-2); }
main { flex: 1; outline: none; }
.velo { display: none; }

@media (max-width: 1024px) {
  .marco { grid-template-columns: 1fr; }
  .barra-lateral { position: fixed; left: 0; top: 0; bottom: 0; width: 280px; z-index: 40; transform: translateX(-100%); transition: transform .2s ease; }
  .barra-lateral.abierta { transform: none; }
  .velo { display: block; position: fixed; inset: 0; background: rgba(19,41,75,.45); z-index: 35; }
  .abrir-lateral { display: inline-flex; }
  .cerrar-lateral { display: inline-flex; position: absolute; right: 10px; top: 22px; border: none; background: none; color: #fff; cursor: pointer; }
  .cerrar-lateral svg { width: 20px; height: 20px; }
}
@media (max-width: 720px) {
  .barra-superior { padding: 0 12px; gap: 8px; }
  .usuario-texto, .chip-demo { display: none; }
}
</style>

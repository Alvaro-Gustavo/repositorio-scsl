<script setup>
// Acceso rapido a asistentes de IA externos (ChatGPT, Gemini...) desde la barra superior.
// Abre cada uno en otra pestana y deja constancia en la auditoria. La lista esta en
// utils/constantes.js (ASISTENTES_IA).
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { RouterLink } from 'vue-router'
import { Sparkles, ExternalLink, TriangleAlert, ChevronDown, BookMarked } from '@lucide/vue'
import { api } from '@/api'
import { useSesion } from '@/stores/sesion'
import { ASISTENTES_IA } from '@/utils/constantes'

const sesion = useSesion()
const abierto = ref(false)
const raiz = ref(null)

function abrir(a) {
  api.auditoria.registrar({ accion: 'ABRIR_ASISTENTE_IA', modulo: 'PROMPTS', detalle: { asistente: a.nombre, origen: 'barra' } }).catch(() => {})
  abierto.value = false
}
function fuera(e) {
  if (abierto.value && raiz.value && !raiz.value.contains(e.target)) abierto.value = false
}
onMounted(() => document.addEventListener('pointerdown', fuera))
onBeforeUnmount(() => document.removeEventListener('pointerdown', fuera))
</script>

<template>
  <div ref="raiz" class="acceso-ia" @keydown.esc="abierto = false">
    <button type="button" class="boton-ia" :aria-expanded="abierto" aria-haspopup="menu" aria-controls="menu-ia"
      @click="abierto = !abierto">
      <Sparkles aria-hidden="true" /> <span class="boton-ia-texto">Asistentes IA</span> <ChevronDown aria-hidden="true" class="flecha" />
    </button>

    <div v-if="abierto" id="menu-ia" class="menu-ia" role="menu">
      <p class="menu-ia-titulo">Abrir en otra pestaña</p>
      <a v-for="a in ASISTENTES_IA" :key="a.id" :href="a.url" target="_blank" rel="noopener noreferrer" role="menuitem"
        class="opcion-ia" @click="abrir(a)">
        <span class="sigla" :style="{ background: a.color }" aria-hidden="true">{{ a.sigla }}</span>
        <span class="opcion-ia-texto"><strong>{{ a.nombre }}</strong><small>{{ a.empresa }}</small></span>
        <ExternalLink aria-hidden="true" class="externo" />
      </a>
      <RouterLink v-if="sesion.puede('USAR_PROMPTS')" to="/prompts" role="menuitem" class="opcion-ia" @click="abierto = false">
        <span class="sigla sigla-catalogo" aria-hidden="true"><BookMarked /></span>
        <span class="opcion-ia-texto"><strong>Catálogo de prompts</strong><small>Instrucciones aprobadas para copiar</small></span>
      </RouterLink>
      <p class="aviso-ia"><TriangleAlert aria-hidden="true" /> No pegue datos personales ni información reservada en una IA externa.</p>
    </div>
  </div>
</template>

<style scoped>
.acceso-ia { position: relative; }
.boton-ia {
  display: inline-flex; align-items: center; gap: 6px; height: 38px; padding: 0 12px;
  border: 1px solid var(--linea-fuerte); border-radius: 999px; background: var(--superficie);
  color: var(--tinta); font-size: var(--t-sm); font-weight: 600; cursor: pointer; white-space: nowrap;
}
.boton-ia:hover, .boton-ia[aria-expanded='true'] { border-color: var(--sello); background: var(--sello-suave); }
.boton-ia svg { width: 17px; height: 17px; color: var(--sello); }
.boton-ia .flecha { width: 14px; height: 14px; color: var(--texto-3); }
.menu-ia {
  position: absolute; right: 0; top: calc(100% + 6px); width: 300px; z-index: 30; padding: 6px;
  background: var(--superficie); border: 1px solid var(--linea); border-radius: var(--radio-panel); box-shadow: var(--sombra-flotante);
}
.menu-ia-titulo { font-size: var(--t-xs); color: var(--texto-3); padding: 6px 10px 4px; }
.opcion-ia { display: flex; align-items: center; gap: 12px; padding: 9px 10px; border-radius: var(--radio-control); color: var(--texto); text-decoration: none; }
.opcion-ia:hover { background: var(--superficie-2); text-decoration: none; }
.sigla { width: 34px; height: 34px; flex: none; border-radius: 9px; display: grid; place-items: center; color: var(--texto-inverso); font-weight: 750; font-size: var(--t-sm); }
.sigla-catalogo { background: var(--tinta); }
.sigla-catalogo svg { width: 17px; height: 17px; }
.opcion-ia-texto { flex: 1; min-width: 0; }
.opcion-ia-texto strong { display: block; font-size: var(--t-sm); }
.opcion-ia-texto small { display: block; font-size: var(--t-xs); color: var(--texto-3); }
.externo { width: 15px; height: 15px; color: var(--texto-3); }
.aviso-ia { display: flex; gap: 8px; align-items: flex-start; margin-top: 4px; padding: 8px 10px; border-top: 1px solid var(--linea); font-size: var(--t-xs); color: var(--aviso); }
.aviso-ia svg { width: 15px; height: 15px; flex: none; margin-top: 1px; }
@media (max-width: 720px) {
  .boton-ia { padding: 0 10px; }
  .boton-ia-texto, .boton-ia .flecha { display: none; }
  .menu-ia { position: fixed; left: 12px; right: 12px; top: calc(var(--alto-superior) + 4px); width: auto; }
}
</style>

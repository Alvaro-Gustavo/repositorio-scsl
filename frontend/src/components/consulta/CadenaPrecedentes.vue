<script setup>
// Cadena de precedentes en vertical: los trámites que este aplica (arriba),
// el trámite actual (centro) y los que lo citan (abajo).
// <CadenaPrecedentes :tramite="detalle" />  (necesita precedentes y citado_por)
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { ArrowDown } from '@lucide/vue'
import { RELEVANCIAS } from '@/utils/constantes'

const props = defineProps({ tramite: { type: Object, required: true } })

const codigo = (t) => t?.numero_documento || t?.hoja_ruta || 'Sin código'
const nodo = (p) => ({ id: p.tramite?.id, codigo: codigo(p.tramite), relevancia: RELEVANCIAS[p.relevancia] || p.relevancia, clave: p.id })

const antecesores = computed(() => (props.tramite.precedentes || []).filter((p) => p.tramite).map(nodo))
const sucesores = computed(() => (props.tramite.citado_por || []).filter((p) => p.tramite).map(nodo))
</script>

<template>
  <div class="cadena">
    <template v-if="antecesores.length">
      <p class="nivel-titulo">Precedentes que aplica</p>
      <ul class="nivel" aria-label="Precedentes que aplica este trámite">
        <li v-for="n in antecesores" :key="n.clave">
          <RouterLink :to="`/tramites/${n.id}`" class="codigo codigo-sello nodo">{{ n.codigo }}</RouterLink>
          <small class="texto-3">{{ n.relevancia }}</small>
        </li>
      </ul>
      <ArrowDown class="flecha" aria-hidden="true" />
    </template>

    <p class="nivel-titulo">Este trámite</p>
    <div class="nivel">
      <span class="codigo codigo-sello nodo actual" aria-current="page">{{ codigo(tramite) }}</span>
    </div>

    <template v-if="sucesores.length">
      <ArrowDown class="flecha" aria-hidden="true" />
      <p class="nivel-titulo">Lo citan después</p>
      <ul class="nivel" aria-label="Trámites que citan a este">
        <li v-for="n in sucesores" :key="n.clave">
          <RouterLink :to="`/tramites/${n.id}`" class="codigo codigo-sello nodo">{{ n.codigo }}</RouterLink>
          <small class="texto-3">{{ n.relevancia }}</small>
        </li>
      </ul>
    </template>

    <p v-if="!antecesores.length && !sucesores.length" class="texto-3 texto-pequeno vacio">
      Todavía no hay trámites vinculados a este.
    </p>
  </div>
</template>

<style scoped>
.cadena { display: flex; flex-direction: column; align-items: center; text-align: center; gap: var(--e-2); }
.nivel-titulo { font-size: var(--t-xs); color: var(--texto-3); }
.nivel { list-style: none; margin: 0; padding: 0; display: flex; flex-wrap: wrap; justify-content: center; gap: var(--e-3); max-width: 100%; }
.nivel li { display: flex; flex-direction: column; align-items: center; gap: 2px; min-width: 0; max-width: 100%; }
.nodo { max-width: 100%; overflow: hidden; text-overflow: ellipsis; text-decoration: none; }
a.nodo:hover { background: var(--sello-suave); text-decoration: none; }
.actual { background: var(--tinta); color: var(--texto-inverso); border-color: var(--tinta); }
.flecha { width: 18px; height: 18px; color: var(--linea-fuerte); }
.vacio { margin-top: var(--e-2); }
</style>

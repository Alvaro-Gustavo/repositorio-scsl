<script setup>
// Un prompt vigente del catalogo con sus acciones de copia.
// <TarjetaPrompt :prompt="p" :copiado="idCopiado === p.id" @copiar="..." @copiar-enmascarado="..." />
import { computed } from 'vue'
import { Copy, Check, EyeOff, ExternalLink } from '@lucide/vue'
import TextoPrompt from './TextoPrompt.vue'
import { CATEGORIAS_PROMPT, ASISTENTES_IA } from '@/utils/constantes'
import { plural } from '@/utils/formato'

const props = defineProps({
  prompt: { type: Object, required: true },
  copiado: { type: Boolean, default: false },
  ocupado: { type: Boolean, default: false }
})
defineEmits(['copiar', 'copiar-enmascarado', 'copiar-y-abrir'])

const idTitulo = computed(() => `prompt-${props.prompt.id}-titulo`)
</script>

<template>
  <article class="tarjeta-prompt" :aria-labelledby="idTitulo">
    <header class="tp-cabecera">
      <div class="tp-titulo">
        <h3 :id="idTitulo">{{ prompt.titulo }}</h3>
        <div class="fila tp-meta">
          <span class="insignia insignia-info insignia-sin-punto">{{ CATEGORIAS_PROMPT[prompt.categoria] || prompt.categoria }}</span>
          <span class="insignia insignia-sin-punto">{{ prompt.tipo_documento?.nombre || 'General' }}</span>
          <span class="texto-3 texto-xs">{{ plural(prompt.usos || 0, 'uso', 'usos') }}</span>
        </div>
      </div>
      <div class="tp-acciones">
        <button type="button" class="boton boton-primario boton-pequeno" :disabled="ocupado" @click="$emit('copiar', prompt)">
          <Check v-if="copiado" aria-hidden="true" /><Copy v-else aria-hidden="true" />
          {{ copiado ? 'Copiado' : 'Copiar' }}
        </button>
        <button type="button" class="boton boton-pequeno" :disabled="ocupado" @click="$emit('copiar-enmascarado', prompt)">
          <EyeOff aria-hidden="true" /> Copiar enmascarado
        </button>
      </div>
    </header>
    <p v-if="prompt.instrucciones" class="tp-instrucciones texto-2 texto-pequeno">
      <span class="etiqueta">Cómo usarlo:</span> {{ prompt.instrucciones }}
    </p>
    <TextoPrompt :texto="prompt.texto" />
    <div class="tp-abrir">
      <span class="texto-3 texto-xs">Copiar y abrir en:</span>
      <a v-for="a in ASISTENTES_IA" :key="a.id" :href="a.url" target="_blank" rel="noopener noreferrer"
        class="boton boton-pequeno tp-ia" :aria-label="`Copiar el prompt y abrir ${a.nombre}`"
        @click="$emit('copiar-y-abrir', prompt, a)">
        <span class="tp-punto" :style="{ background: a.color }" aria-hidden="true" /> {{ a.nombre }} <ExternalLink aria-hidden="true" />
      </a>
    </div>
  </article>
</template>

<style scoped>
.tarjeta-prompt { padding: var(--e-5) var(--e-6); display: grid; gap: var(--e-3); }
.tarjeta-prompt + .tarjeta-prompt { border-top: 1px solid var(--linea); }
.tp-cabecera { display: flex; justify-content: space-between; align-items: flex-start; gap: var(--e-3); flex-wrap: wrap; }
.tp-titulo { min-width: 0; flex: 1 1 260px; }
.tp-titulo h3 { font-size: var(--t-md); margin-bottom: var(--e-1); }
.tp-meta { gap: var(--e-2); }
.tp-acciones { display: flex; gap: var(--e-2); flex-wrap: wrap; }
.tp-instrucciones .etiqueta { font-size: inherit; }
.tp-abrir { display: flex; align-items: center; gap: var(--e-2); flex-wrap: wrap; }
.tp-ia { text-decoration: none; }
.tp-ia:hover { text-decoration: none; }
.tp-punto { width: 9px; height: 9px; border-radius: 50%; }
@media (max-width: 720px) {
  .tarjeta-prompt { padding: var(--e-4); }
  .tp-acciones { width: 100%; }
  .tp-acciones .boton { flex: 1 1 auto; }
}
</style>

<script setup>
// Texto de un prompt, legible y con los marcadores [ ... ] resaltados.
// <TextoPrompt :texto="prompt.texto" />
import { computed } from 'vue'

const props = defineProps({ texto: { type: String, default: '' } })

// Divide el texto en partes normales y marcadores entre corchetes (sin saltos de linea dentro).
const partes = computed(() => String(props.texto || '').split(/(\[[^\]\n]+\])/g)
  .filter((p) => p !== '')
  .map((p) => ({ texto: p, marcador: /^\[[^\]\n]+\]$/.test(p) })))
</script>

<template>
  <div class="texto-prompt"><template v-for="(p, i) in partes" :key="i"><mark v-if="p.marcador" class="marcador">{{ p.texto }}</mark><template v-else>{{ p.texto }}</template></template></div>
</template>

<style scoped>
.texto-prompt {
  white-space: pre-wrap; overflow-wrap: anywhere;
  font-family: var(--fuente-texto); font-size: var(--t-sm); line-height: 1.6; color: var(--texto);
  background: var(--superficie-2); border: 1px solid var(--linea); border-left: 3px solid var(--linea-fuerte);
  border-radius: var(--radio-control); padding: var(--e-3) var(--e-4);
}
.marcador {
  background: var(--aviso-suave); color: var(--aviso); font-weight: 650;
  padding: 0 3px; border-radius: 3px; box-decoration-break: clone; -webkit-box-decoration-break: clone;
}
</style>

<script setup>
// Lista de requisitos de la nueva contrasena, marcados a medida que se cumplen.
// <RequisitosClave :clave="nueva" :confirmacion="confirmacion" />
// Exporta claveValida(clave, confirmacion) -> { campo: mensaje } para validar antes de enviar.
import { computed } from 'vue'
import { Check, Circle } from '@lucide/vue'

const props = defineProps({ clave: { type: String, default: '' }, confirmacion: { type: String, default: '' } })

const requisitos = computed(() => [
  { texto: 'Al menos 10 caracteres', ok: props.clave.length >= 10 },
  { texto: 'Las dos contraseñas coinciden', ok: !!props.clave && props.clave === props.confirmacion }
])
</script>

<script>
export const MIN_CLAVE = 10
export function erroresClave(clave, confirmacion, campoClave = 'clave') {
  const e = {}
  if (!clave || clave.length < MIN_CLAVE) e[campoClave] = `Use al menos ${MIN_CLAVE} caracteres.`
  if (clave !== confirmacion) e.confirmacion = 'Las contraseñas no coinciden.'
  return e
}
</script>

<template>
  <div class="requisitos" aria-live="polite">
    <p class="ayuda">La nueva contraseña debe cumplir:</p>
    <ul>
      <li v-for="r in requisitos" :key="r.texto" :class="{ cumple: r.ok }">
        <Check v-if="r.ok" aria-hidden="true" /><Circle v-else aria-hidden="true" />
        <span>{{ r.texto }}<span class="sr-only">{{ r.ok ? ': cumplido' : ': pendiente' }}</span></span>
      </li>
    </ul>
    <p class="ayuda">Se recomienda combinar letras, números y algún símbolo. No use su nombre ni su correo.</p>
  </div>
</template>

<style scoped>
.requisitos { padding: var(--e-3) var(--e-4); background: var(--superficie-2); border: 1px solid var(--linea); border-radius: var(--radio-control); }
ul { list-style: none; margin: var(--e-2) 0; padding: 0; display: grid; gap: 4px; }
li { display: flex; align-items: center; gap: var(--e-2); font-size: var(--t-sm); color: var(--texto-2); }
li svg { width: 14px; height: 14px; flex: none; color: var(--texto-3); }
li.cumple { color: var(--exito); }
li.cumple svg { color: var(--exito); }
</style>

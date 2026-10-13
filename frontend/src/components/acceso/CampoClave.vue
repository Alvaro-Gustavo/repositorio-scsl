<script setup>
// Campo de contrasena con boton mostrar/ocultar.
// <CampoClave id="clave" v-model="clave" etiqueta="Contraseña" :error="errores.clave" autocomplete="current-password" />
import { ref, computed } from 'vue'
import { Eye, EyeOff, Lock } from '@lucide/vue'

const props = defineProps({
  id: { type: String, required: true },
  etiqueta: { type: String, required: true },
  modelValue: { type: String, default: '' },
  error: { type: String, default: '' },
  ayuda: { type: String, default: '' },
  autocomplete: { type: String, default: 'current-password' },
  requerido: { type: Boolean, default: true },
  icono: { type: Boolean, default: false },   // candado a la izquierda (pantalla de ingreso)
  placeholder: { type: String, default: '' }
})
const emit = defineEmits(['update:modelValue'])
const visible = ref(false)
const describe = computed(() => [props.ayuda && `${props.id}-ayuda`, props.error && `${props.id}-error`].filter(Boolean).join(' ') || undefined)
</script>

<template>
  <div class="campo">
    <label :for="id">{{ etiqueta }}</label>
    <div class="clave" :class="{ 'con-icono': icono }">
      <Lock v-if="icono" class="icono-campo" aria-hidden="true" />
      <input :id="id" class="entrada" :type="visible ? 'text' : 'password'" :value="modelValue" :autocomplete="autocomplete"
        :placeholder="placeholder || undefined"
        :required="requerido" :aria-invalid="error ? 'true' : undefined" :aria-describedby="describe"
        spellcheck="false" autocapitalize="off" @input="emit('update:modelValue', $event.target.value)" />
      <button type="button" class="ver" :aria-label="visible ? 'Ocultar contraseña' : 'Mostrar contraseña'" :aria-pressed="visible"
        :title="visible ? 'Ocultar contraseña' : 'Mostrar contraseña'" @click="visible = !visible">
        <EyeOff v-if="visible" aria-hidden="true" /><Eye v-else aria-hidden="true" />
      </button>
    </div>
    <p v-if="ayuda" :id="`${id}-ayuda`" class="ayuda">{{ ayuda }}</p>
    <p v-if="error" :id="`${id}-error`" class="error-campo">{{ error }}</p>
  </div>
</template>

<style scoped>
.clave { position: relative; }
.clave .entrada { padding-right: 46px; }
.con-icono .entrada { padding-left: 44px; }
.icono-campo { position: absolute; left: 14px; top: 50%; transform: translateY(-50%); width: 19px; height: 19px; color: var(--texto-3); pointer-events: none; }
.con-icono:focus-within .icono-campo { color: var(--sello); }
.ver {
  position: absolute; right: 3px; top: 50%; transform: translateY(-50%);
  width: 36px; height: 34px; display: grid; place-items: center;
  border: none; background: none; color: var(--texto-2); border-radius: var(--radio-control); cursor: pointer;
}
.ver:hover { background: var(--superficie-2); color: var(--tinta); }
.ver svg { width: 18px; height: 18px; }
</style>

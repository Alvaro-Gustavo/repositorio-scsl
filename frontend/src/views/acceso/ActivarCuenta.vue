<script setup>
// Activacion de cuenta: correo + codigo de 6 digitos recibido por correo + nueva contrasena.
// El enlace del correo trae ambos despues de "#" (/activar#correo=...&codigo=...): no viajan al
// servidor ni quedan en sus registros; al leerlos se borran de la barra de direcciones.
import { ref } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import { CheckCircle2, LoaderCircle, Info } from '@lucide/vue'
import MarcoAcceso from '@/components/acceso/MarcoAcceso.vue'
import CampoClave from '@/components/acceso/CampoClave.vue'
import RequisitosClave, { erroresClave } from '@/components/acceso/RequisitosClave.vue'
import { MODO, api } from '@/api'
import { useEnvio } from '@/composables/utiles'

const route = useRoute()
const delEnlace = new URLSearchParams(window.location.hash.slice(1))
const codigoDelEnlace = /^\d{6}$/.test(delEnlace.get('codigo') || '') ? delEnlace.get('codigo') : ''
if (window.location.hash) history.replaceState(history.state, '', window.location.pathname + window.location.search)
const form = ref({
  correo: delEnlace.get('correo') || (typeof route.query.correo === 'string' ? route.query.correo : ''),
  codigo: codigoDelEnlace,
  clave: '',
  confirmacion: ''
})
const listo = ref(false)
const { errores, enviando, enviar } = useEnvio()

async function activar() {
  const e = erroresClave(form.value.clave, form.value.confirmacion)
  if (!form.value.correo.trim()) e.correo = 'Ingrese su correo.'
  if (!/^\d{6}$/.test(form.value.codigo)) e.codigo = 'El código tiene 6 dígitos.'
  if (Object.keys(e).length) { errores.value = e; return }
  try {
    await enviar(() => api.auth.activar({ correo: form.value.correo.trim(), codigo: form.value.codigo, clave: form.value.clave }))
    listo.value = true
  } catch { /* errores ya marcados */ }
}

const soloDigitos = (v) => v.replace(/\D/g, '').slice(0, 6)
</script>

<template>
  <MarcoAcceso v-if="!listo" titulo="Activar mi cuenta" subtitulo="Ingrese el código que recibió en su correo institucional y elija su contraseña.">
    <form class="formulario" novalidate @submit.prevent="activar">
      <p v-if="MODO === 'simulado'" class="mensaje mensaje-info"><Info aria-hidden="true" /> En demostración el código es 123456.</p>
      <p v-else-if="codigoDelEnlace" class="mensaje mensaje-info"><Info aria-hidden="true" /> Su correo y su código ya están cargados: solo elija su contraseña.</p>

      <div class="campo">
        <label for="correo">Correo</label>
        <input id="correo" v-model="form.correo" class="entrada" type="email" autocomplete="username" inputmode="email" required
          :aria-invalid="errores.correo ? 'true' : undefined" />
        <p v-if="errores.correo" class="error-campo">{{ errores.correo }}</p>
      </div>

      <div class="campo">
        <label for="codigo">Código de activación</label>
        <input id="codigo" :value="form.codigo" class="entrada codigo-entrada" inputmode="numeric" autocomplete="one-time-code"
          maxlength="6" required aria-describedby="codigo-ayuda" :aria-invalid="errores.codigo ? 'true' : undefined"
          @input="form.codigo = soloDigitos($event.target.value); $event.target.value = form.codigo" />
        <p id="codigo-ayuda" class="ayuda">6 dígitos. Si venció, pida al administrador que le envíe uno nuevo.</p>
        <p v-if="errores.codigo" class="error-campo">{{ errores.codigo }}</p>
      </div>

      <CampoClave id="clave" v-model="form.clave" etiqueta="Nueva contraseña" :error="errores.clave" autocomplete="new-password" />
      <CampoClave id="confirmacion" v-model="form.confirmacion" etiqueta="Repita la contraseña" :error="errores.confirmacion" autocomplete="new-password" />
      <RequisitosClave :clave="form.clave" :confirmacion="form.confirmacion" />

      <button type="submit" class="boton boton-primario boton-ancho" :disabled="enviando">
        <LoaderCircle v-if="enviando" class="girar" aria-hidden="true" />
        {{ enviando ? 'Activando…' : 'Activar cuenta' }}
      </button>
    </form>
    <template #pie>
      <RouterLink to="/ingresar">Volver a ingresar</RouterLink>
    </template>
  </MarcoAcceso>

  <MarcoAcceso v-else titulo="Cuenta activada">
    <div class="mensaje mensaje-exito" role="status">
      <CheckCircle2 aria-hidden="true" />
      <p>Su cuenta quedó activa. Ya puede ingresar con su correo y la contraseña que eligió.</p>
    </div>
    <RouterLink :to="{ name: 'ingresar', query: { correo: form.correo.trim() } }" class="boton boton-primario boton-ancho espacio-arriba">Ir a ingresar</RouterLink>
  </MarcoAcceso>
</template>

<style scoped>
.boton-ancho { width: 100%; min-height: 44px; font-size: var(--t-md); }
.espacio-arriba { margin-top: var(--e-5); }
.codigo-entrada { letter-spacing: 0.3em; font-variant-numeric: tabular-nums; max-width: 200px; }
</style>

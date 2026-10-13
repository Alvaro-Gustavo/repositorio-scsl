<script setup>
// Recuperacion de contrasena en dos pasos. El primer paso nunca revela si el correo existe.
import { ref } from 'vue'
import { RouterLink } from 'vue-router'
import { CheckCircle2, LoaderCircle, Info, MailCheck } from '@lucide/vue'
import MarcoAcceso from '@/components/acceso/MarcoAcceso.vue'
import CampoClave from '@/components/acceso/CampoClave.vue'
import RequisitosClave, { erroresClave } from '@/components/acceso/RequisitosClave.vue'
import { MODO, api } from '@/api'
import { useEnvio } from '@/composables/utiles'

const paso = ref(1)
const correo = ref('')
const codigo = ref('')
const clave = ref('')
const confirmacion = ref('')
const { errores, enviando, enviar } = useEnvio()

async function solicitar() {
  if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(correo.value.trim())) { errores.value = { correo: 'Ingrese un correo válido.' }; return }
  try {
    await enviar(() => api.auth.solicitarRecuperacion({ correo: correo.value.trim() }))
    paso.value = 2
  } catch { /* aviso ya mostrado */ }
}

async function restablecer() {
  const e = erroresClave(clave.value, confirmacion.value)
  if (!/^\d{6}$/.test(codigo.value)) e.codigo = 'El código tiene 6 dígitos.'
  if (Object.keys(e).length) { errores.value = e; return }
  try {
    await enviar(() => api.auth.restablecer({ correo: correo.value.trim(), codigo: codigo.value, clave: clave.value }))
    paso.value = 3
  } catch { /* errores ya marcados */ }
}

function cambiarCorreo() {
  paso.value = 1
  codigo.value = ''
  errores.value = {}
}

const soloDigitos = (v) => v.replace(/\D/g, '').slice(0, 6)
</script>

<template>
  <MarcoAcceso v-if="paso === 1" titulo="Recuperar contraseña" subtitulo="Le enviaremos un código a su correo institucional para que elija una nueva contraseña.">
    <form class="formulario" novalidate @submit.prevent="solicitar">
      <div class="campo">
        <label for="correo">Correo</label>
        <input id="correo" v-model="correo" class="entrada" type="email" autocomplete="username" inputmode="email" required
          placeholder="nombre@contraloria.gob.bo" :aria-invalid="errores.correo ? 'true' : undefined" />
        <p v-if="errores.correo" class="error-campo">{{ errores.correo }}</p>
      </div>
      <button type="submit" class="boton boton-primario boton-ancho" :disabled="enviando">
        <LoaderCircle v-if="enviando" class="girar" aria-hidden="true" />
        {{ enviando ? 'Enviando…' : 'Enviar código' }}
      </button>
    </form>
    <template #pie><RouterLink to="/ingresar">Volver a ingresar</RouterLink></template>
  </MarcoAcceso>

  <MarcoAcceso v-else-if="paso === 2" titulo="Elija una nueva contraseña">
    <form class="formulario" novalidate @submit.prevent="restablecer">
      <div class="mensaje mensaje-info" role="status">
        <MailCheck aria-hidden="true" />
        <p>Si el correo <strong>{{ correo.trim() }}</strong> está registrado, recibirá un código. Puede tardar unos minutos.</p>
      </div>
      <p v-if="MODO === 'simulado'" class="mensaje mensaje-info"><Info aria-hidden="true" /> En demostración el código es 123456.</p>

      <div class="campo">
        <label for="codigo">Código recibido</label>
        <input id="codigo" :value="codigo" class="entrada codigo-entrada" inputmode="numeric" autocomplete="one-time-code"
          maxlength="6" required :aria-invalid="errores.codigo ? 'true' : undefined"
          @input="codigo = soloDigitos($event.target.value); $event.target.value = codigo" />
        <p v-if="errores.codigo" class="error-campo">{{ errores.codigo }}</p>
      </div>

      <CampoClave id="clave" v-model="clave" etiqueta="Nueva contraseña" :error="errores.clave" autocomplete="new-password" />
      <CampoClave id="confirmacion" v-model="confirmacion" etiqueta="Repita la contraseña" :error="errores.confirmacion" autocomplete="new-password" />
      <RequisitosClave :clave="clave" :confirmacion="confirmacion" />

      <button type="submit" class="boton boton-primario boton-ancho" :disabled="enviando">
        <LoaderCircle v-if="enviando" class="girar" aria-hidden="true" />
        {{ enviando ? 'Guardando…' : 'Guardar nueva contraseña' }}
      </button>
    </form>
    <template #pie>
      <div class="fila-entre">
        <button type="button" class="enlace" @click="cambiarCorreo">Usar otro correo o pedir otro código</button>
        <RouterLink to="/ingresar">Volver a ingresar</RouterLink>
      </div>
    </template>
  </MarcoAcceso>

  <MarcoAcceso v-else titulo="Contraseña actualizada">
    <div class="mensaje mensaje-exito" role="status">
      <CheckCircle2 aria-hidden="true" />
      <p>Ya puede ingresar con su nueva contraseña.</p>
    </div>
    <RouterLink :to="{ name: 'ingresar', query: { correo: correo.trim() } }" class="boton boton-primario boton-ancho espacio-arriba">Ir a ingresar</RouterLink>
  </MarcoAcceso>
</template>

<style scoped>
.boton-ancho { width: 100%; min-height: 44px; font-size: var(--t-md); }
.espacio-arriba { margin-top: var(--e-5); }
.codigo-entrada { letter-spacing: 0.3em; font-variant-numeric: tabular-nums; max-width: 200px; }
.enlace { border: none; background: none; padding: 0; color: var(--sello); cursor: pointer; font-size: inherit; text-align: left; }
.enlace:hover { text-decoration: underline; }
.mensaje strong { overflow-wrap: anywhere; }
</style>

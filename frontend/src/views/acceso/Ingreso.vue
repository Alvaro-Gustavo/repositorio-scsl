<script setup>
// Pantalla de ingreso (fuera del marco). Al ingresar vuelve a la pagina pedida
// o, si la cuenta debe cambiar su contrasena, lleva al perfil.
import { ref, computed } from 'vue'
import { useRoute, useRouter, RouterLink } from 'vue-router'
import { LogIn, LoaderCircle, AlertCircle, FlaskConical, UserRound } from '@lucide/vue'
import MarcoAcceso from '@/components/acceso/MarcoAcceso.vue'
import CampoClave from '@/components/acceso/CampoClave.vue'
import { useSesion } from '@/stores/sesion'
import { useAvisos } from '@/stores/avisos'
import { MODO, api } from '@/api'
import { ROLES } from '@/utils/constantes'

const sesion = useSesion()
const avisos = useAvisos()
const route = useRoute()
const router = useRouter()

const correo = ref(typeof route.query.correo === 'string' ? route.query.correo : '')
const clave = ref('')
const codigo2fa = ref('')
const pide2fa = ref(false)
const enviando = ref(false)
const error = ref('')
const errores = ref({})

const cuentasDemo = computed(() => (MODO === 'simulado' && api.demo ? api.demo.cuentas() : []))

// Solo rutas internas: evita redirigir a otro sitio con ?volver=//otro.sitio
function destino() {
  const v = route.query.volver
  return typeof v === 'string' && v.startsWith('/') && !v.startsWith('//') ? v : '/'
}

async function ingresar() {
  error.value = ''
  errores.value = {}
  if (!correo.value.trim()) errores.value.correo = 'Ingrese su correo.'
  if (!clave.value) errores.value.clave = 'Ingrese su contraseña.'
  if (pide2fa.value && !/^\d{6}$/.test(codigo2fa.value)) errores.value.codigo_2fa = 'Ingrese los 6 dígitos de su aplicación.'
  if (Object.keys(errores.value).length) return

  enviando.value = true
  try {
    const datos = { correo: correo.value.trim(), clave: clave.value }
    if (pide2fa.value) datos.codigo_2fa = codigo2fa.value
    const usuario = await sesion.ingresar(datos)
    if (usuario?.debe_cambiar_contrasena) {
      avisos.aviso('Por seguridad, cambie su contraseña antes de continuar.')
      router.replace({ name: 'perfil', query: { cambiar: '1' } })
    } else {
      router.replace(destino())
    }
  } catch (e) {
    // El servidor pide el segundo factor indicando el campo codigo_2fa.
    if (e.campos && 'codigo_2fa' in e.campos) {
      if (pide2fa.value) errores.value.codigo_2fa = e.campos.codigo_2fa
      pide2fa.value = true
    }
    error.value = e.message || 'No se pudo ingresar.'
    clave.value = pide2fa.value ? clave.value : ''
  } finally {
    enviando.value = false
  }
}

function usarCuenta(c) {
  correo.value = c.correo
  clave.value = api.demo.claveDemo
  error.value = ''
  errores.value = {}
}
</script>

<template>
  <MarcoAcceso titulo="Bienvenido" subtitulo="Ingrese sus credenciales para acceder al sistema.">
    <form class="formulario" novalidate @submit.prevent="ingresar">
      <div v-if="error" class="mensaje mensaje-peligro" role="alert">
        <AlertCircle aria-hidden="true" />
        <div>
          <p>{{ error }}</p>
          <p v-if="/active su cuenta/i.test(error)"><RouterLink :to="{ name: 'activar', query: { correo } }">Activar mi cuenta</RouterLink></p>
        </div>
      </div>

      <div class="campo">
        <label for="correo">Correo institucional</label>
        <div class="con-icono">
          <UserRound class="icono-campo" aria-hidden="true" />
          <input id="correo" v-model="correo" class="entrada" type="email" autocomplete="username" inputmode="email"
          placeholder="nombre@contraloria.gob.bo" required :aria-invalid="errores.correo ? 'true' : undefined"
          :aria-describedby="errores.correo ? 'correo-error' : undefined" />
        </div>
        <p v-if="errores.correo" id="correo-error" class="error-campo">{{ errores.correo }}</p>
      </div>

      <CampoClave id="clave" v-model="clave" etiqueta="Contraseña" :error="errores.clave" autocomplete="current-password"
        icono placeholder="Su contraseña" />

      <div v-if="pide2fa" class="campo">
        <label for="codigo-2fa">Código de verificación</label>
        <input id="codigo-2fa" v-model="codigo2fa" class="entrada codigo-entrada" inputmode="numeric" autocomplete="one-time-code"
          maxlength="6" pattern="\d{6}" :aria-invalid="errores.codigo_2fa ? 'true' : undefined" aria-describedby="codigo-2fa-ayuda" />
        <p id="codigo-2fa-ayuda" class="ayuda">Los 6 dígitos que muestra su aplicación autenticadora.</p>
        <p v-if="errores.codigo_2fa" class="error-campo">{{ errores.codigo_2fa }}</p>
      </div>

      <button type="submit" class="boton boton-primario boton-ancho" :disabled="enviando">
        <LoaderCircle v-if="enviando" class="girar" aria-hidden="true" /><LogIn v-else aria-hidden="true" />
        {{ enviando ? 'Ingresando…' : 'Iniciar sesión' }}
      </button>
    </form>

    <section v-if="cuentasDemo.length" class="demo" aria-labelledby="demo-titulo">
      <h2 id="demo-titulo" class="demo-titulo"><FlaskConical aria-hidden="true" /> Cuentas de demostración</h2>
      <p class="ayuda">Elija una cuenta para llenar el formulario. Los datos se guardan solo en este navegador.</p>
      <ul class="demo-lista">
        <li v-for="c in cuentasDemo" :key="c.correo">
          <button type="button" class="demo-cuenta" @click="usarCuenta(c)">
            <span class="demo-nombre">{{ c.nombre }}</span>
            <span class="demo-detalle">{{ ROLES[c.rol] || c.rol }} · {{ c.correo }}</span>
          </button>
        </li>
      </ul>
    </section>

    <template #pie>
      <nav class="enlaces" aria-label="Ayuda con la cuenta">
        <RouterLink to="/recuperar">¿Olvidó su contraseña?</RouterLink>
        <RouterLink to="/activar">Activar mi cuenta</RouterLink>
      </nav>
    </template>
  </MarcoAcceso>
</template>

<style scoped>
.boton-ancho { width: 100%; min-height: 44px; font-size: var(--t-md); margin-top: var(--e-2); }
.con-icono { position: relative; }
.con-icono .entrada { width: 100%; padding-left: 44px; }
.icono-campo { position: absolute; left: 14px; top: 50%; transform: translateY(-50%); width: 19px; height: 19px; color: var(--texto-3); pointer-events: none; }
.con-icono:focus-within .icono-campo { color: var(--sello); }
.codigo-entrada { letter-spacing: 0.3em; font-variant-numeric: tabular-nums; max-width: 200px; }
.enlaces { display: flex; justify-content: space-between; gap: var(--e-3); flex-wrap: wrap; }

.demo { margin-top: var(--e-6); padding: var(--e-4); border: 1px dashed var(--linea-fuerte); border-radius: var(--radio-panel); background: var(--superficie-2); }
.demo-titulo { display: flex; align-items: center; gap: var(--e-2); font-family: var(--fuente-texto); font-size: var(--t-sm); font-weight: 650; color: var(--aviso); }
.demo-titulo svg { width: 16px; height: 16px; }
.demo .ayuda { margin-top: 2px; }
.demo-lista { list-style: none; margin: var(--e-3) 0 0; padding: 0; display: grid; gap: 6px; }
.demo-cuenta {
  width: 100%; text-align: left; display: flex; flex-direction: column; gap: 0;
  padding: 8px 12px; border: 1px solid var(--linea); border-radius: var(--radio-control); background: var(--superficie); cursor: pointer;
}
.demo-cuenta:hover { border-color: var(--sello); background: var(--sello-suave); }
.demo-nombre { font-weight: 600; font-size: var(--t-sm); }
.demo-detalle { font-size: var(--t-xs); color: var(--texto-3); overflow-wrap: anywhere; }
</style>

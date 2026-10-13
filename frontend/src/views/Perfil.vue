<script setup>
// Perfil del usuario: datos propios, cambio de contrasena y segundo factor (2FA).
import { ref, computed, onMounted, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { AlertTriangle, ShieldCheck, ShieldOff, Copy, LoaderCircle, KeyRound } from '@lucide/vue'
import { api } from '@/api'
import { useSesion } from '@/stores/sesion'
import { useAvisos } from '@/stores/avisos'
import { useEnvio, copiarTexto } from '@/composables/utiles'
import { formatoFechaHora } from '@/utils/formato'
import { ROLES } from '@/utils/constantes'
import CampoClave from '@/components/acceso/CampoClave.vue'
import RequisitosClave, { erroresClave } from '@/components/acceso/RequisitosClave.vue'
import Modal from '@/components/ui/Modal.vue'

const sesion = useSesion()
const avisos = useAvisos()
const route = useRoute()
const usuario = computed(() => sesion.usuario || {})

// ---------- Datos ----------
const datos = ref({ nombre_completo: usuario.value.nombre_completo || '', cargo: usuario.value.cargo || '' })
const envioDatos = useEnvio()
const erroresDatos = envioDatos.errores
const cambiosDatos = computed(() => datos.value.nombre_completo.trim() !== (usuario.value.nombre_completo || '')
  || datos.value.cargo.trim() !== (usuario.value.cargo || ''))

async function guardarDatos() {
  if (!datos.value.nombre_completo.trim()) { erroresDatos.value = { nombre_completo: 'Ingrese su nombre.' }; return }
  try {
    const r = await envioDatos.enviar(() => api.perfil.actualizar({ nombre_completo: datos.value.nombre_completo.trim(), cargo: datos.value.cargo.trim() }), 'Datos actualizados')
    sesion.actualizarUsuario(r)
    datos.value = { nombre_completo: r.nombre_completo || '', cargo: r.cargo || '' }
  } catch { /* errores ya marcados */ }
}

// ---------- Contrasena ----------
const clave = ref({ actual: '', nueva: '', confirmacion: '' })
const envioClave = useEnvio()
const erroresClaveForm = envioClave.errores

async function cambiarClave() {
  const e = erroresClave(clave.value.nueva, clave.value.confirmacion, 'nueva')
  if (!clave.value.actual) e.actual = 'Ingrese su contraseña actual.'
  else if (clave.value.nueva && clave.value.nueva === clave.value.actual) e.nueva = 'La nueva contraseña debe ser distinta de la actual.'
  if (Object.keys(e).length) { erroresClaveForm.value = e; return }
  try {
    await envioClave.enviar(() => api.perfil.cambiarClave({ actual: clave.value.actual, nueva: clave.value.nueva }), 'Contraseña actualizada')
    sesion.actualizarUsuario({ debe_cambiar_contrasena: false })
    clave.value = { actual: '', nueva: '', confirmacion: '' }
  } catch { /* errores ya marcados */ }
}

// ---------- Segundo factor ----------
const configuracion2fa = ref(null) // { secreto, uri } mientras se configura
const codigo2fa = ref('')
const error2fa = ref('')
const envio2fa = useEnvio()
const confirmarDesactivar = ref(false)

const secretoAgrupado = computed(() => (configuracion2fa.value?.secreto || '').replace(/(.{4})/g, '$1 ').trim())

async function iniciar2fa() {
  error2fa.value = ''
  codigo2fa.value = ''
  try { configuracion2fa.value = await envio2fa.enviar(() => api.perfil.iniciar2fa()) } catch { /* aviso ya mostrado */ }
}
async function confirmar2fa() {
  error2fa.value = /^\d{6}$/.test(codigo2fa.value) ? '' : 'Ingrese los 6 dígitos que muestra la aplicación.'
  if (error2fa.value) return
  try {
    await envio2fa.enviar(() => api.perfil.confirmar2fa(codigo2fa.value), 'Segundo factor activado')
    sesion.actualizarUsuario({ totp_activo: true })
    configuracion2fa.value = null
    codigo2fa.value = ''
  } catch (e) { error2fa.value = e.message }
}
function cancelar2fa() {
  configuracion2fa.value = null
  codigo2fa.value = ''
  error2fa.value = ''
}
async function desactivar2fa() {
  try {
    await envio2fa.enviar(() => api.perfil.desactivar2fa(), 'Segundo factor desactivado')
    sesion.actualizarUsuario({ totp_activo: false })
  } catch { /* aviso ya mostrado */ }
  confirmarDesactivar.value = false
}
async function copiarSecreto() {
  const ok = await copiarTexto(configuracion2fa.value.secreto)
  ok ? avisos.exito('Clave copiada') : avisos.error('No se pudo copiar. Escríbala manualmente.')
}

const soloDigitos = (v) => v.replace(/\D/g, '').slice(0, 6)

// Si llega desde el ingreso con contrasena por cambiar, llevar el foco a ese formulario.
onMounted(async () => {
  if (route.query.cambiar || usuario.value.debe_cambiar_contrasena) {
    await nextTick()
    document.getElementById('cambiar-clave')?.scrollIntoView({ block: 'start' })
    document.getElementById('clave-actual')?.focus({ preventScroll: true })
  }
})
</script>

<template>
  <div class="pagina perfil">
    <header class="pagina-cabecera">
      <div>
        <h1>Mi perfil</h1>
        <p>Sus datos, su contraseña y la verificación en dos pasos.</p>
      </div>
    </header>

    <div v-if="usuario.debe_cambiar_contrasena" class="mensaje mensaje-aviso aviso-clave" role="alert">
      <AlertTriangle aria-hidden="true" />
      <div>
        <p><strong>Debe cambiar su contraseña.</strong> Fue creada o restablecida por el administrador; elija una propia para seguir usando el sistema con normalidad.</p>
        <p><a href="#cambiar-clave">Ir a cambiar contraseña</a></p>
      </div>
    </div>

    <!-- Datos -->
    <section class="panel" aria-labelledby="titulo-datos">
      <header class="panel-cabecera"><h2 id="titulo-datos">Mis datos</h2></header>
      <div class="panel-cuerpo">
        <dl class="datos solo-lectura">
          <div><dt>Correo</dt><dd>{{ usuario.correo }}</dd></div>
          <div><dt>Rol</dt><dd>{{ ROLES[usuario.rol] || usuario.rol }}</dd></div>
          <div><dt>Último acceso</dt><dd>{{ formatoFechaHora(usuario.ultimo_acceso) }}</dd></div>
        </dl>
        <p class="ayuda nota">El correo y el rol solo los puede cambiar el administrador.</p>

        <form class="formulario-2" novalidate @submit.prevent="guardarDatos">
          <div class="campo">
            <label for="nombre">Nombre completo<span class="requerido" aria-hidden="true">*</span></label>
            <input id="nombre" v-model="datos.nombre_completo" class="entrada" autocomplete="name" required maxlength="150"
              :aria-invalid="erroresDatos.nombre_completo ? 'true' : undefined" />
            <p v-if="erroresDatos.nombre_completo" class="error-campo">{{ erroresDatos.nombre_completo }}</p>
          </div>
          <div class="campo">
            <label for="cargo">Cargo <span class="opcional">(opcional)</span></label>
            <input id="cargo" v-model="datos.cargo" class="entrada" autocomplete="organization-title" maxlength="150"
              :aria-invalid="erroresDatos.cargo ? 'true' : undefined" />
            <p v-if="erroresDatos.cargo" class="error-campo">{{ erroresDatos.cargo }}</p>
          </div>
          <div class="formulario-acciones campo-ancho">
            <button type="submit" class="boton boton-primario" :disabled="envioDatos.enviando.value || !cambiosDatos">
              <LoaderCircle v-if="envioDatos.enviando.value" class="girar" aria-hidden="true" /> Guardar datos
            </button>
          </div>
        </form>
      </div>
    </section>

    <!-- Contrasena -->
    <section id="cambiar-clave" class="panel" aria-labelledby="titulo-clave">
      <header class="panel-cabecera"><h2 id="titulo-clave">Cambiar contraseña</h2></header>
      <div class="panel-cuerpo">
        <form class="formulario-2" novalidate @submit.prevent="cambiarClave">
          <CampoClave id="clave-actual" v-model="clave.actual" etiqueta="Contraseña actual" :error="erroresClaveForm.actual" autocomplete="current-password" class="campo-ancho media" />
          <CampoClave id="clave-nueva" v-model="clave.nueva" etiqueta="Nueva contraseña" :error="erroresClaveForm.nueva" autocomplete="new-password" />
          <CampoClave id="clave-confirmacion" v-model="clave.confirmacion" etiqueta="Repita la nueva contraseña" :error="erroresClaveForm.confirmacion" autocomplete="new-password" />
          <RequisitosClave class="campo-ancho" :clave="clave.nueva" :confirmacion="clave.confirmacion" />
          <div class="formulario-acciones campo-ancho">
            <button type="submit" class="boton boton-primario" :disabled="envioClave.enviando.value">
              <LoaderCircle v-if="envioClave.enviando.value" class="girar" aria-hidden="true" /><KeyRound v-else aria-hidden="true" /> Cambiar contraseña
            </button>
          </div>
        </form>
      </div>
    </section>

    <!-- Segundo factor -->
    <section class="panel" aria-labelledby="titulo-2fa">
      <header class="panel-cabecera">
        <h2 id="titulo-2fa">Verificación en dos pasos</h2>
        <span v-if="usuario.totp_activo" class="insignia insignia-exito">Activa</span>
        <span v-else class="insignia">Inactiva</span>
      </header>
      <div class="panel-cuerpo">
        <template v-if="usuario.totp_activo">
          <p class="texto-2">Al ingresar, además de su contraseña se le pedirá el código de 6 dígitos de su aplicación autenticadora.</p>
          <div class="formulario-acciones">
            <button type="button" class="boton boton-peligro" @click="confirmarDesactivar = true"><ShieldOff aria-hidden="true" /> Desactivar</button>
          </div>
        </template>

        <template v-else-if="!configuracion2fa">
          <p class="texto-2">Además de la contraseña, al ingresar se pedirá un código temporal de una aplicación autenticadora (por ejemplo Google Authenticator, Microsoft Authenticator o FreeOTP). Recomendado para cuentas que descargan informes o administran el sistema.</p>
          <div class="formulario-acciones">
            <button type="button" class="boton boton-primario" :disabled="envio2fa.enviando.value" @click="iniciar2fa">
              <LoaderCircle v-if="envio2fa.enviando.value" class="girar" aria-hidden="true" /><ShieldCheck v-else aria-hidden="true" /> Configurar
            </button>
          </div>
        </template>

        <form v-else class="formulario" novalidate @submit.prevent="confirmar2fa">
          <ol class="pasos">
            <li>
              <p>Abra su aplicación autenticadora y elija <strong>agregar cuenta</strong> con <strong>clave de configuración</strong>.</p>
            </li>
            <li>
              <p>Escriba esta clave (tipo «basada en tiempo»):</p>
              <div class="secreto">
                <code class="codigo" aria-label="Clave de configuración">{{ secretoAgrupado }}</code>
                <button type="button" class="boton boton-pequeno" @click="copiarSecreto"><Copy aria-hidden="true" /> Copiar</button>
              </div>
              <p class="ayuda">Cuenta: Repositorio SCSL · {{ usuario.correo }}. No comparta esta clave con nadie.</p>
            </li>
            <li>
              <div class="campo">
                <label for="codigo-2fa">Escriba el código de 6 dígitos que muestra la aplicación</label>
                <input id="codigo-2fa" :value="codigo2fa" class="entrada codigo-entrada" inputmode="numeric" autocomplete="one-time-code" maxlength="6"
                  :aria-invalid="error2fa ? 'true' : undefined" :aria-describedby="error2fa ? 'codigo-2fa-error' : undefined"
                  @input="codigo2fa = soloDigitos($event.target.value); $event.target.value = codigo2fa" />
                <p v-if="error2fa" id="codigo-2fa-error" class="error-campo">{{ error2fa }}</p>
              </div>
            </li>
          </ol>
          <div class="formulario-acciones">
            <button type="button" class="boton" @click="cancelar2fa">Cancelar</button>
            <button type="submit" class="boton boton-primario" :disabled="envio2fa.enviando.value">
              <LoaderCircle v-if="envio2fa.enviando.value" class="girar" aria-hidden="true" /> Confirmar y activar
            </button>
          </div>
        </form>
      </div>
    </section>

    <Modal v-model="confirmarDesactivar" titulo="Desactivar verificación en dos pasos" ancho="480px">
      <p>Su cuenta quedará protegida solo con la contraseña. ¿Desea desactivarla?</p>
      <template #pie>
        <button type="button" class="boton" @click="confirmarDesactivar = false">Cancelar</button>
        <button type="button" class="boton boton-peligro" :disabled="envio2fa.enviando.value" @click="desactivar2fa">Desactivar</button>
      </template>
    </Modal>
  </div>
</template>

<style scoped>
.perfil { max-width: 880px; }
.aviso-clave { margin-bottom: var(--e-6); }
.aviso-clave p + p { margin-top: var(--e-1); }
.aviso-clave a { color: inherit; text-decoration: underline; font-weight: 600; }
.solo-lectura { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.nota { margin: var(--e-3) 0 var(--e-5); padding-bottom: var(--e-5); border-bottom: 1px solid var(--linea); }
.media { max-width: calc(50% - var(--e-3)); }
#cambiar-clave { scroll-margin-top: calc(var(--alto-superior) + var(--e-4)); }
.pasos { margin: 0; padding-left: 1.25rem; display: grid; gap: var(--e-5); }
.pasos li::marker { font-weight: 650; color: var(--tinta); }
.pasos p + * { margin-top: var(--e-2); }
.secreto { display: flex; align-items: center; gap: var(--e-3); flex-wrap: wrap; padding: var(--e-3) var(--e-4); background: var(--superficie-2); border: 1px dashed var(--linea-fuerte); border-radius: var(--radio-control); }
.secreto code { font-size: var(--t-lg); letter-spacing: 0.08em; white-space: normal; overflow-wrap: anywhere; }
.codigo-entrada { letter-spacing: 0.3em; font-variant-numeric: tabular-nums; max-width: 200px; }
@media (max-width: 720px) {
  .solo-lectura { grid-template-columns: 1fr; }
  .media { max-width: none; }
}
</style>

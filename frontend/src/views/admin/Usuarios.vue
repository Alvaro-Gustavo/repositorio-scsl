<script setup>
// Administración de usuarios: alta, edición, activación y matriz de permisos por rol.
import { ref, computed } from 'vue'
import { UserPlus, Pencil, Power, Mail, Search, Users, Check, Info } from '@lucide/vue'
import { api } from '@/api'
import { useCarga, useEnvio } from '@/composables/utiles'
import { useSesion } from '@/stores/sesion'
import { ROLES } from '@/utils/constantes'
import { formatoFechaHora } from '@/utils/formato'
import { GRUPOS_PERMISOS, etiquetaPermiso } from '@/components/admin/etiquetasPermisos'
import Modal from '@/components/ui/Modal.vue'
import Cargando from '@/components/ui/Cargando.vue'
import EstadoVacio from '@/components/ui/EstadoVacio.vue'

const sesion = useSesion()
const pestana = ref('usuarios')

const { datos: usuarios, cargando, error, cargar } = useCarga(() => api.usuarios.listar(), { inicial: [] })
const { datos: roles } = useCarga(() => api.usuarios.roles(), { inicial: [] })

const texto = ref('')
const filtroRol = ref('')
const normalizar = (t) => String(t ?? '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()

const filtrados = computed(() => {
  const q = normalizar(texto.value.trim())
  return (usuarios.value || [])
    .filter((u) => !filtroRol.value || u.rol === filtroRol.value)
    .filter((u) => !q || normalizar(`${u.nombre_completo} ${u.correo} ${u.cargo || ''}`).includes(q))
    .sort((a, b) => Number(b.activo) - Number(a.activo) || a.nombre_completo.localeCompare(b.nombre_completo, 'es'))
})

const nombreRol = (r) => ROLES[r] || r
const descripcionRol = (r) => roles.value?.find((x) => x.nombre === r)?.descripcion || ''
const esYo = (u) => u.id === sesion.usuario?.id

// ---------- Nuevo usuario ----------
const altaAbierta = ref(false)
const alta = ref({})
const envioAlta = useEnvio()
function abrirAlta() {
  alta.value = { nombre_completo: '', correo: '', cargo: '', rol: '' }
  envioAlta.errores.value = {}
  altaAbierta.value = true
}
async function crear() {
  try {
    const u = await envioAlta.enviar(() => api.usuarios.crear(alta.value))
    altaAbierta.value = false
    activacionEnviada.value = u.correo
    await cargar()
  } catch { /* errores por campo ya mostrados */ }
}
const activacionEnviada = ref('')

// ---------- Editar ----------
const edicionAbierta = ref(false)
const edicion = ref({})
// El correo es la identidad de la cuenta: al cambiarlo, la persona vuelve a activar su cuenta desde el correo nuevo.
const cambiaCorreo = computed(() => !edicion.value.propio && !!edicion.value.correo
  && edicion.value.correo.trim().toLowerCase() !== (edicion.value.correoOriginal || '').toLowerCase())
const envioEdicion = useEnvio()
function abrirEdicion(u) {
  edicion.value = { id: u.id, correo: u.correo, correoOriginal: u.correo, nombre_completo: u.nombre_completo, cargo: u.cargo || '', rol: u.rol, propio: esYo(u) }
  envioEdicion.errores.value = {}
  edicionAbierta.value = true
}
async function guardarEdicion() {
  const { id, nombre_completo, cargo, rol, propio, correo } = edicion.value
  const datos = propio ? { nombre_completo, cargo } : { nombre_completo, cargo, rol }
  if (cambiaCorreo.value) datos.correo = correo.trim()
  const aviso = cambiaCorreo.value ? `Usuario actualizado. Se envió un código de activación a ${datos.correo}` : 'Usuario actualizado'
  try {
    await envioEdicion.enviar(() => api.usuarios.actualizar(id, datos), aviso)
    edicionAbierta.value = false
    await cargar()
  } catch { /* mensaje ya mostrado */ }
}

// ---------- Activar / desactivar ----------
const cambioAbierto = ref(false)
const cambio = ref(null)
const envioCambio = useEnvio()
function abrirCambio(u) { cambio.value = u; cambioAbierto.value = true }
async function confirmarCambio() {
  const u = cambio.value
  try {
    await envioCambio.enviar(() => api.usuarios.activar(u.id, !u.activo), u.activo ? 'Usuario desactivado' : 'Usuario activado')
    cambioAbierto.value = false
    await cargar()
  } catch { /* mensaje ya mostrado */ }
}

// ---------- Reenviar activación ----------
const envioReenvio = useEnvio()
const reenviando = ref(null)
async function reenviar(u) {
  reenviando.value = u.id
  try {
    await envioReenvio.enviar(() => api.usuarios.reenviarActivacion(u.id), `Código de activación reenviado a ${u.correo}`)
  } catch { /* mensaje ya mostrado */ } finally { reenviando.value = null }
}

// ---------- Matriz ----------
const grupos = computed(() => {
  const todos = new Set((roles.value || []).flatMap((r) => r.permisos))
  const conocidos = new Set(GRUPOS_PERMISOS.flatMap((g) => Object.keys(g.permisos)))
  const lista = GRUPOS_PERMISOS.map((g) => ({ titulo: g.titulo, permisos: Object.keys(g.permisos).filter((p) => todos.has(p)) }))
  const otros = [...todos].filter((p) => !conocidos.has(p))
  if (otros.length) lista.push({ titulo: 'Otros', permisos: otros })
  return lista.filter((g) => g.permisos.length)
})
const tiene = (rol, permiso) => rol.permisos.includes(permiso)
</script>

<template>
  <div class="pagina">
    <header class="pagina-cabecera">
      <div>
        <h1>Usuarios</h1>
        <p>Cree cuentas, asigne el rol de cada persona y active o desactive su acceso al repositorio.</p>
      </div>
      <div class="pagina-acciones">
        <button type="button" class="boton boton-primario" @click="abrirAlta"><UserPlus aria-hidden="true" /> Nuevo usuario</button>
      </div>
    </header>

    <div class="pestanas" role="tablist">
      <button id="tab-usuarios" type="button" role="tab" class="pestana" :aria-selected="pestana === 'usuarios'" aria-controls="panel-usuarios" @click="pestana = 'usuarios'">Usuarios</button>
      <button id="tab-roles" type="button" role="tab" class="pestana" :aria-selected="pestana === 'roles'" aria-controls="panel-roles" @click="pestana = 'roles'">Roles y permisos</button>
    </div>

    <section v-show="pestana === 'usuarios'" id="panel-usuarios" role="tabpanel" aria-labelledby="tab-usuarios">
      <div v-if="activacionEnviada" class="mensaje mensaje-exito aviso-alta" role="status">
        <Mail aria-hidden="true" />
        <div class="fila-entre" style="flex: 1">
          <span>Usuario creado. Se envió un código de activación a <strong>{{ activacionEnviada }}</strong>. La persona debe activar su cuenta y definir su contraseña antes de ingresar.</span>
          <button type="button" class="boton boton-pequeno boton-fantasma" @click="activacionEnviada = ''">Entendido</button>
        </div>
      </div>

      <div class="panel">
        <div class="panel-cabecera filtros">
          <div class="campo campo-buscar">
            <label for="usuarios-buscar" class="sr-only">Buscar usuario</label>
            <div class="con-icono">
              <Search aria-hidden="true" />
              <input id="usuarios-buscar" v-model="texto" type="search" class="entrada" placeholder="Buscar por nombre, correo o cargo" />
            </div>
          </div>
          <div class="campo">
            <label for="usuarios-rol" class="sr-only">Filtrar por rol</label>
            <select id="usuarios-rol" v-model="filtroRol" class="seleccion">
              <option value="">Todos los roles</option>
              <option v-for="(etiqueta, clave) in ROLES" :key="clave" :value="clave">{{ etiqueta }}</option>
            </select>
          </div>
        </div>

        <Cargando v-if="cargando && !usuarios.length" texto="Cargando usuarios…" />
        <div v-else-if="error" class="panel-cuerpo"><div class="mensaje mensaje-peligro" role="alert">{{ error }}</div></div>
        <EstadoVacio v-else-if="!filtrados.length" :icono="Users" titulo="No hay usuarios que coincidan" texto="Cambie el texto de búsqueda o el rol elegido." />
        <div v-else class="tabla-contenedor">
          <table class="tabla">
            <thead>
              <tr>
                <th scope="col">Nombre</th>
                <th scope="col">Cargo</th>
                <th scope="col">Rol</th>
                <th scope="col">Estado</th>
                <th scope="col">Cuenta</th>
                <th scope="col">2FA</th>
                <th scope="col">Último acceso</th>
                <th scope="col"><span class="sr-only">Acciones</span></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="u in filtrados" :key="u.id" :class="{ inactivo: !u.activo }">
                <td>
                  <strong>{{ u.nombre_completo }}</strong>
                  <span v-if="esYo(u)" class="texto-3 texto-xs"> (usted)</span>
                  <div class="texto-3 texto-xs">{{ u.correo }}</div>
                </td>
                <td>{{ u.cargo || '—' }}</td>
                <td>{{ nombreRol(u.rol) }}</td>
                <td>
                  <span class="insignia" :class="u.activo ? 'insignia-exito' : ''">{{ u.activo ? 'Activo' : 'Inactivo' }}</span>
                </td>
                <td>
                  <span v-if="u.correo_verificado" class="insignia insignia-info">Activada</span>
                  <span v-else class="insignia insignia-aviso">Pendiente de activación</span>
                </td>
                <td>{{ u.totp_activo ? 'Sí' : 'No' }}</td>
                <td class="sin-salto">{{ u.ultimo_acceso ? formatoFechaHora(u.ultimo_acceso) : 'Nunca' }}</td>
                <td>
                  <div class="fila acciones">
                    <button type="button" class="boton boton-pequeno" :aria-label="`Editar a ${u.nombre_completo}`" @click="abrirEdicion(u)"><Pencil aria-hidden="true" /> Editar</button>
                    <button
                      v-if="!u.correo_verificado && u.activo" type="button" class="boton boton-pequeno"
                      :disabled="reenviando === u.id" :aria-label="`Reenviar activación a ${u.correo}`" @click="reenviar(u)"
                    ><Mail aria-hidden="true" /> Reenviar activación</button>
                    <button
                      v-if="!esYo(u)" type="button" class="boton boton-pequeno" :class="u.activo ? 'boton-peligro' : ''"
                      :aria-label="`${u.activo ? 'Desactivar' : 'Activar'} a ${u.nombre_completo}`" @click="abrirCambio(u)"
                    ><Power aria-hidden="true" /> {{ u.activo ? 'Desactivar' : 'Activar' }}</button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <section v-show="pestana === 'roles'" id="panel-roles" role="tabpanel" aria-labelledby="tab-roles">
      <div class="mensaje mensaje-info roles-nota">
        <Info aria-hidden="true" />
        <span>Esta matriz es de solo lectura. Los permisos de cada rol los define el sistema y se verifican en el servidor en cada operación.</span>
      </div>
      <div class="rejilla-roles">
        <div v-for="r in roles" :key="r.nombre" class="panel rol">
          <div class="panel-cuerpo">
            <h3>{{ nombreRol(r.nombre) }}</h3>
            <p class="texto-2 texto-pequeno">{{ r.descripcion }}</p>
          </div>
        </div>
      </div>
      <div class="panel">
        <div class="tabla-contenedor">
          <table class="tabla matriz">
            <caption class="sr-only">Permisos por rol</caption>
            <thead>
              <tr>
                <th scope="col">Permiso</th>
                <th v-for="r in roles" :key="r.nombre" scope="col" class="centro">{{ nombreRol(r.nombre) }}</th>
              </tr>
            </thead>
            <tbody>
              <template v-for="g in grupos" :key="g.titulo">
                <tr class="grupo"><th scope="rowgroup" :colspan="roles.length + 1">{{ g.titulo }}</th></tr>
                <tr v-for="p in g.permisos" :key="p">
                  <th scope="row" class="permiso">{{ etiquetaPermiso(p) }}</th>
                  <td v-for="r in roles" :key="r.nombre" class="centro">
                    <template v-if="tiene(r, p)"><Check class="marca-si" aria-hidden="true" /><span class="sr-only">Sí</span></template>
                    <template v-else><span class="texto-3" aria-hidden="true">—</span><span class="sr-only">No</span></template>
                  </td>
                </tr>
              </template>
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <!-- Nuevo usuario -->
    <Modal v-model="altaAbierta" titulo="Nuevo usuario" ancho="600px">
      <form id="form-alta" class="formulario" novalidate @submit.prevent="crear">
        <div class="formulario-2">
          <div class="campo campo-ancho">
            <label for="alta-nombre">Nombre completo<span class="requerido" aria-hidden="true">*</span></label>
            <input id="alta-nombre" v-model="alta.nombre_completo" class="entrada" autocomplete="off" required :aria-invalid="!!envioAlta.errores.value.nombre_completo" aria-describedby="alta-nombre-error" />
            <span v-if="envioAlta.errores.value.nombre_completo" id="alta-nombre-error" class="error-campo">{{ envioAlta.errores.value.nombre_completo }}</span>
          </div>
          <div class="campo">
            <label for="alta-correo">Correo institucional<span class="requerido" aria-hidden="true">*</span></label>
            <input id="alta-correo" v-model="alta.correo" type="email" class="entrada" autocomplete="off" required :aria-invalid="!!envioAlta.errores.value.correo" aria-describedby="alta-correo-ayuda alta-correo-error" />
            <span id="alta-correo-ayuda" class="ayuda">Aquí llegará el código de activación.</span>
            <span v-if="envioAlta.errores.value.correo" id="alta-correo-error" class="error-campo">{{ envioAlta.errores.value.correo }}</span>
          </div>
          <div class="campo">
            <label for="alta-cargo">Cargo <span class="opcional">(opcional)</span></label>
            <input id="alta-cargo" v-model="alta.cargo" class="entrada" autocomplete="off" />
          </div>
        </div>
        <fieldset class="campo grupo-roles" :aria-invalid="!!envioAlta.errores.value.rol">
          <legend class="etiqueta">Rol<span class="requerido" aria-hidden="true">*</span></legend>
          <label v-for="r in roles" :key="r.nombre" class="opcion-rol" :class="{ elegido: alta.rol === r.nombre }">
            <input v-model="alta.rol" type="radio" name="alta-rol" :value="r.nombre" />
            <span>
              <strong>{{ nombreRol(r.nombre) }}</strong>
              <span class="texto-2 texto-pequeno d-block">{{ r.descripcion }}</span>
            </span>
          </label>
          <span v-if="envioAlta.errores.value.rol" class="error-campo">{{ envioAlta.errores.value.rol }}</span>
        </fieldset>
      </form>
      <template #pie>
        <button type="button" class="boton" @click="altaAbierta = false">Cancelar</button>
        <button type="submit" form="form-alta" class="boton boton-primario" :disabled="envioAlta.enviando.value">Crear y enviar activación</button>
      </template>
    </Modal>

    <!-- Editar -->
    <Modal v-model="edicionAbierta" titulo="Editar usuario" ancho="520px">
      <form id="form-edicion" class="formulario" novalidate @submit.prevent="guardarEdicion">
        <p v-if="edicion.propio" class="texto-2 texto-pequeno">Correo: <strong>{{ edicion.correo }}</strong>. Cambie su propio correo desde <RouterLink to="/perfil">Mi perfil</RouterLink>, donde se confirma con un código.</p>
        <div v-else class="campo">
          <label for="ed-correo">Correo institucional<span class="requerido" aria-hidden="true">*</span></label>
          <input id="ed-correo" v-model="edicion.correo" type="email" class="entrada" autocomplete="off" required
            :aria-invalid="!!envioEdicion.errores.value.correo" aria-describedby="ed-correo-ayuda ed-correo-error" />
          <span v-if="envioEdicion.errores.value.correo" id="ed-correo-error" class="error-campo">{{ envioEdicion.errores.value.correo }}</span>
          <p v-if="cambiaCorreo" id="ed-correo-ayuda" class="mensaje mensaje-aviso texto-pequeno">
            Al guardar, se cierran las sesiones de esta persona y su cuenta queda pendiente de activación: recibirá un código en
            <strong>{{ edicion.correo.trim() }}</strong> para elegir una contraseña nueva. A la dirección anterior se le avisa del cambio.
          </p>
          <span v-else id="ed-correo-ayuda" class="ayuda">Es la dirección con la que ingresa y recibe los códigos.</span>
        </div>
        <div class="campo">
          <label for="ed-nombre">Nombre completo<span class="requerido" aria-hidden="true">*</span></label>
          <input id="ed-nombre" v-model="edicion.nombre_completo" class="entrada" required :aria-invalid="!!envioEdicion.errores.value.nombre_completo" />
          <span v-if="envioEdicion.errores.value.nombre_completo" class="error-campo">{{ envioEdicion.errores.value.nombre_completo }}</span>
        </div>
        <div class="campo">
          <label for="ed-cargo">Cargo <span class="opcional">(opcional)</span></label>
          <input id="ed-cargo" v-model="edicion.cargo" class="entrada" />
        </div>
        <div class="campo">
          <label for="ed-rol">Rol</label>
          <select id="ed-rol" v-model="edicion.rol" class="seleccion" :disabled="edicion.propio" aria-describedby="ed-rol-ayuda" :aria-invalid="!!envioEdicion.errores.value.rol">
            <option v-for="r in roles" :key="r.nombre" :value="r.nombre">{{ nombreRol(r.nombre) }}</option>
          </select>
          <span id="ed-rol-ayuda" class="ayuda">{{ edicion.propio ? 'No puede cambiar su propio rol. Pida a otro administrador que lo haga.' : descripcionRol(edicion.rol) }}</span>
          <span v-if="envioEdicion.errores.value.rol" class="error-campo">{{ envioEdicion.errores.value.rol }}</span>
        </div>
      </form>
      <template #pie>
        <button type="button" class="boton" @click="edicionAbierta = false">Cancelar</button>
        <button type="submit" form="form-edicion" class="boton boton-primario" :disabled="envioEdicion.enviando.value">Guardar cambios</button>
      </template>
    </Modal>

    <!-- Activar / desactivar -->
    <Modal v-model="cambioAbierto" :titulo="cambio?.activo ? 'Desactivar usuario' : 'Activar usuario'" ancho="480px">
      <template v-if="cambio">
        <p v-if="cambio.activo">
          <strong>{{ cambio.nombre_completo }}</strong> ya no podrá ingresar al repositorio. Sus trámites, informes y su historial en la auditoría se conservan. Puede volver a activarlo cuando lo necesite.
        </p>
        <p v-else>
          <strong>{{ cambio.nombre_completo }}</strong> podrá volver a ingresar con su contraseña actual y con los permisos del rol {{ nombreRol(cambio.rol) }}.
        </p>
      </template>
      <template #pie>
        <button type="button" class="boton" @click="cambioAbierto = false">Cancelar</button>
        <button type="button" class="boton" :class="cambio?.activo ? 'boton-peligro' : 'boton-primario'" :disabled="envioCambio.enviando.value" @click="confirmarCambio">
          {{ cambio?.activo ? 'Sí, desactivar' : 'Sí, activar' }}
        </button>
      </template>
    </Modal>
  </div>
</template>

<style scoped>
.aviso-alta { margin-bottom: var(--e-4); }
.filtros { justify-content: flex-start; flex-wrap: wrap; }
.campo-buscar { flex: 1 1 260px; }
.con-icono { position: relative; }
.con-icono svg { position: absolute; left: 10px; top: 50%; transform: translateY(-50%); width: 16px; height: 16px; color: var(--texto-3); }
.con-icono .entrada { padding-left: 34px; }
.inactivo td { color: var(--texto-3); }
.sin-salto { white-space: nowrap; }
.acciones { flex-wrap: nowrap; justify-content: flex-end; }
.roles-nota { margin-bottom: var(--e-4); }
.rejilla-roles { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: var(--e-4); margin-bottom: var(--e-6); }
.rejilla-roles .panel + .panel { margin-top: 0; }
.rol h3 { margin-bottom: var(--e-1); }
.matriz .centro { text-align: center; }
.matriz .grupo th { background: var(--superficie); color: var(--tinta); font-size: var(--t-xs); text-transform: none; padding-top: var(--e-4); }
.matriz .permiso { font-weight: 400; color: var(--texto); background: none; white-space: normal; }
.marca-si { width: 18px; height: 18px; color: var(--exito); margin: 0 auto; }
.grupo-roles { border: none; padding: 0; margin: 0; gap: var(--e-2); }
.grupo-roles legend { margin-bottom: var(--e-2); }
.opcion-rol { display: flex; gap: var(--e-3); align-items: flex-start; padding: var(--e-3); border: 1px solid var(--linea); border-radius: var(--radio-control); cursor: pointer; font-weight: 400; }
.opcion-rol:hover { background: var(--superficie-2); }
.opcion-rol.elegido { border-color: var(--sello); background: var(--sello-suave); }
.opcion-rol input { margin-top: 4px; accent-color: var(--sello); }
.d-block { display: block; }
</style>

<script setup>
// Catálogos del sistema (entidades, tipos, áreas, profesionales...) y sitios legales externos.
import { ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Plus, Pencil, Power, Merge, Info, Globe, ListX } from '@lucide/vue'
import { api } from '@/api'
import { useCarga, useEnvio } from '@/composables/utiles'
import { useCatalogos } from '@/stores/catalogos'
import { useAvisos } from '@/stores/avisos'
import { CATALOGOS } from '@/utils/constantes'
import { formatoNumero, plural } from '@/utils/formato'
import Modal from '@/components/ui/Modal.vue'
import Cargando from '@/components/ui/Cargando.vue'
import EstadoVacio from '@/components/ui/EstadoVacio.vue'

const route = useRoute()
const router = useRouter()
const cache = useCatalogos()
const avisos = useAvisos()

const PESTANAS = [...Object.entries(CATALOGOS).map(([clave, c]) => ({ clave, titulo: c.titulo })), { clave: 'fuentes', titulo: 'Sitios legales' }]
const pestana = ref(PESTANAS.some((p) => p.clave === route.query.tab) ? route.query.tab : PESTANAS[0].clave)
watch(pestana, (t) => router.replace({ query: { ...route.query, tab: t } }))

const esFuentes = computed(() => pestana.value === 'fuentes')
const info = computed(() => CATALOGOS[pestana.value] || null)
const esProfesionales = computed(() => pestana.value === 'profesionales')

// ---------- Valores del catálogo ----------
const { datos: valores, cargando, error, cargar } = useCarga(
  () => api.catalogos.listar(pestana.value, { inactivos: true }), { inmediato: false, inicial: [] }
)
const { datos: usuarios, cargar: cargarUsuarios } = useCarga(() => api.usuarios.listar(), { inmediato: false, inicial: [] })
const abogados = computed(() => (usuarios.value || []).filter((u) => u.rol === 'ABOGADO'))
const filtro = ref('')
const visibles = computed(() => {
  const q = filtro.value.trim().toLowerCase()
  return (valores.value || []).filter((v) => !q || v.nombre.toLowerCase().includes(q))
})


async function refrescar() {
  cache.invalidar(pestana.value)
  await cargar()
}

// Agregar
const nuevo = ref('')
const envioNuevo = useEnvio()
async function agregar() {
  try {
    await envioNuevo.enviar(() => api.catalogos.crear(pestana.value, { nombre: nuevo.value }), 'Valor agregado')
    nuevo.value = ''
    await refrescar()
  } catch { /* error mostrado */ }
}

// Renombrar
const renombrarAbierto = ref(false)
const renombre = ref({ id: null, nombre: '', original: '' })
const envioRenombre = useEnvio()
function abrirRenombre(v) {
  renombre.value = { id: v.id, nombre: v.nombre, original: v.nombre }
  envioRenombre.errores.value = {}
  renombrarAbierto.value = true
}
async function guardarRenombre() {
  try {
    await envioRenombre.enviar(() => api.catalogos.actualizar(pestana.value, renombre.value.id, { nombre: renombre.value.nombre }), 'Nombre actualizado')
    renombrarAbierto.value = false
    await refrescar()
  } catch { /* error mostrado */ }
}

// Activar / desactivar
const envioEstado = useEnvio()
async function alternar(v) {
  try {
    await envioEstado.enviar(() => api.catalogos.actualizar(pestana.value, v.id, { activo: !v.activo }), v.activo ? 'Valor desactivado' : 'Valor activado')
    await refrescar()
  } catch { /* error mostrado */ }
}

// Vincular cuenta (profesionales)
const envioCuenta = useEnvio()
const vinculadoA = (usuarioId, profesionalId) => (valores.value || []).find((p) => p.usuario_id === usuarioId && p.id !== profesionalId)
async function vincular(v, evento) {
  const usuario_id = evento.target.value ? Number(evento.target.value) : null
  try {
    await envioCuenta.enviar(() => api.catalogos.actualizar('profesionales', v.id, { usuario_id }), usuario_id ? 'Cuenta vinculada' : 'Cuenta desvinculada')
  } catch { /* error mostrado */ }
  await refrescar()
}

// Unificar duplicados
const unificarAbierto = ref(false)
const union = ref({ conservar: '', eliminar: '' })
const envioUnion = useEnvio()
const valorPorId = (id) => (valores.value || []).find((v) => v.id === Number(id))
function abrirUnificar() {
  union.value = { conservar: '', eliminar: '' }
  envioUnion.errores.value = {}
  unificarAbierto.value = true
}
const unionValida = computed(() => union.value.conservar && union.value.eliminar && union.value.conservar !== union.value.eliminar)
async function unificar() {
  try {
    const r = await envioUnion.enviar(() => api.catalogos.unificar(pestana.value, Number(union.value.conservar), Number(union.value.eliminar)))
    envioUnion.errores.value = {}
    unificarAbierto.value = false
    avisos.exito(`Valores unificados: ${plural(r?.movidos ?? 0, 'trámite pasó', 'trámites pasaron')} al valor conservado`)
    await refrescar()
  } catch { /* error mostrado */ }
}

// ---------- Sitios legales ----------
const { datos: fuentes, cargando: cargandoFuentes, error: errorFuentes, cargar: cargarFuentes } = useCarga(() => api.fuentes.listar(), { inmediato: false, inicial: [] })
const fuenteAbierta = ref(false)
const fuente = ref({})
const envioFuente = useEnvio()
function abrirFuente(f = null) {
  fuente.value = f
    ? { id: f.id, nombre: f.nombre, descripcion: f.descripcion || '', url: f.url, url_busqueda: f.url_busqueda || '', orden: f.orden }
    : { id: null, nombre: '', descripcion: '', url: '', url_busqueda: '', orden: 100 }
  envioFuente.errores.value = {}
  fuenteAbierta.value = true
}
async function guardarFuente() {
  const { id, ...datos } = fuente.value
  datos.orden = Number(datos.orden) || 100
  try {
    await envioFuente.enviar(() => (id ? api.fuentes.actualizar(id, datos) : api.fuentes.crear(datos)), id ? 'Sitio actualizado' : 'Sitio agregado')
    fuenteAbierta.value = false
    await cargarFuentes()
  } catch { /* error mostrado */ }
}
const envioEstadoFuente = useEnvio()
async function alternarFuente(f) {
  try {
    await envioEstadoFuente.enviar(() => api.fuentes.actualizar(f.id, { activo: !f.activo }), f.activo ? 'Sitio desactivado' : 'Sitio activado')
    await cargarFuentes()
  } catch { /* error mostrado */ }
}
const err = (envio, campo) => envio.errores.value[campo]

// Carga al cambiar de pestaña (al final: usa funciones declaradas arriba).
watch(pestana, (t) => {
  filtro.value = ''
  if (t === 'fuentes') return cargarFuentes()
  valores.value = []
  cargar()
  if (t === 'profesionales' && !usuarios.value.length) cargarUsuarios()
}, { immediate: true })
</script>

<template>
  <div class="pagina">
    <header class="pagina-cabecera">
      <div>
        <h1>Catálogos</h1>
        <p>Mantenga ordenadas las listas que se usan al registrar trámites: agregue valores, corrija nombres y unifique duplicados.</p>
      </div>
    </header>

    <div class="pestanas" role="tablist" aria-label="Catálogos">
      <button
        v-for="p in PESTANAS" :id="`tab-${p.clave}`" :key="p.clave" type="button" role="tab" class="pestana"
        :aria-selected="pestana === p.clave" aria-controls="panel-catalogo" @click="pestana = p.clave"
      >{{ p.titulo }}</button>
    </div>

    <!-- Catálogo -->
    <section v-if="!esFuentes" id="panel-catalogo" role="tabpanel" :aria-labelledby="`tab-${pestana}`">
      <div v-if="esProfesionales" class="mensaje mensaje-info nota">
        <Info aria-hidden="true" />
        <span>Solo los profesionales vinculados a una cuenta de usuario con rol abogado pueden recibir trámites. Vincule cada profesional con su cuenta en la columna "Cuenta de usuario".</span>
      </div>

      <div class="panel">
        <div class="panel-cabecera barra">
          <form class="fila agregar" novalidate @submit.prevent="agregar">
            <label :for="`nuevo-${pestana}`" class="sr-only">Nuevo valor de {{ info.singular }}</label>
            <input
              :id="`nuevo-${pestana}`" v-model="nuevo" class="entrada" :placeholder="`Agregar ${info.singular}`"
              :aria-invalid="!!err(envioNuevo, 'nombre')" autocomplete="off"
            />
            <button type="submit" class="boton boton-primario" :disabled="!nuevo.trim() || envioNuevo.enviando.value"><Plus aria-hidden="true" /> Agregar</button>
            <span v-if="err(envioNuevo, 'nombre')" class="error-campo ancho-total">{{ err(envioNuevo, 'nombre') }}</span>
          </form>
          <div class="fila">
            <label :for="`filtro-${pestana}`" class="sr-only">Filtrar valores</label>
            <input :id="`filtro-${pestana}`" v-model="filtro" type="search" class="entrada filtro" placeholder="Filtrar" />
            <button type="button" class="boton" :disabled="(valores || []).length < 2" @click="abrirUnificar"><Merge aria-hidden="true" /> Unificar duplicados</button>
          </div>
        </div>

        <Cargando v-if="cargando && !valores.length" />
        <div v-else-if="error" class="panel-cuerpo"><div class="mensaje mensaje-peligro" role="alert">{{ error }}</div></div>
        <EstadoVacio v-else-if="!visibles.length" :icono="ListX" :titulo="filtro ? 'Ningún valor coincide con el filtro' : 'El catálogo está vacío'" />
        <div v-else class="tabla-contenedor">
          <table class="tabla">
            <caption class="sr-only">{{ info.titulo }}</caption>
            <thead>
              <tr>
                <th scope="col">Nombre</th>
                <th scope="col" class="num">Usos</th>
                <th v-if="esProfesionales" scope="col">Cuenta de usuario</th>
                <th scope="col">Estado</th>
                <th scope="col"><span class="sr-only">Acciones</span></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="v in visibles" :key="v.id" :class="{ inactivo: !v.activo }">
                <td>{{ v.nombre }}</td>
                <td class="num">{{ formatoNumero(v.usos) }}</td>
                <td v-if="esProfesionales">
                  <label :for="`cuenta-${v.id}`" class="sr-only">Cuenta de usuario de {{ v.nombre }}</label>
                  <select :id="`cuenta-${v.id}`" class="seleccion seleccion-cuenta" :value="v.usuario_id ?? ''" :disabled="envioCuenta.enviando.value" @change="vincular(v, $event)">
                    <option value="">Sin cuenta (no recibe trámites)</option>
                    <option v-for="u in abogados" :key="u.id" :value="u.id" :disabled="!!vinculadoA(u.id, v.id)">
                      {{ u.nombre_completo }} · {{ u.correo }}{{ !u.activo ? ' (inactiva)' : '' }}{{ vinculadoA(u.id, v.id) ? ` (vinculada a ${vinculadoA(u.id, v.id).nombre})` : '' }}
                    </option>
                  </select>
                </td>
                <td><span class="insignia" :class="v.activo ? 'insignia-exito' : ''">{{ v.activo ? 'Activo' : 'Inactivo' }}</span></td>
                <td>
                  <div class="fila acciones">
                    <button type="button" class="boton boton-pequeno" :aria-label="`Renombrar ${v.nombre}`" @click="abrirRenombre(v)"><Pencil aria-hidden="true" /> Renombrar</button>
                    <button type="button" class="boton boton-pequeno" :disabled="envioEstado.enviando.value" :aria-label="`${v.activo ? 'Desactivar' : 'Activar'} ${v.nombre}`" @click="alternar(v)">
                      <Power aria-hidden="true" /> {{ v.activo ? 'Desactivar' : 'Activar' }}
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      <p class="ayuda pie-nota">Un valor desactivado ya no aparece al registrar trámites, pero se conserva en los trámites que ya lo usan.</p>
    </section>

    <!-- Sitios legales -->
    <section v-else id="panel-catalogo" role="tabpanel" aria-labelledby="tab-fuentes">
      <div class="panel">
        <div class="panel-cabecera">
          <p class="texto-2 texto-pequeno">Sitios oficiales que los usuarios pueden abrir desde la consulta. Cada apertura queda en la auditoría.</p>
          <button type="button" class="boton boton-primario" @click="abrirFuente()"><Plus aria-hidden="true" /> Nuevo sitio</button>
        </div>
        <Cargando v-if="cargandoFuentes && !fuentes.length" />
        <div v-else-if="errorFuentes" class="panel-cuerpo"><div class="mensaje mensaje-peligro" role="alert">{{ errorFuentes }}</div></div>
        <EstadoVacio v-else-if="!fuentes.length" :icono="Globe" titulo="No hay sitios legales registrados" />
        <div v-else class="tabla-contenedor">
          <table class="tabla">
            <caption class="sr-only">Sitios legales</caption>
            <thead>
              <tr>
                <th scope="col" class="num">Orden</th>
                <th scope="col">Nombre</th>
                <th scope="col">Dirección</th>
                <th scope="col">Búsqueda directa</th>
                <th scope="col">Estado</th>
                <th scope="col"><span class="sr-only">Acciones</span></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="f in fuentes" :key="f.id" :class="{ inactivo: !f.activo }">
                <td class="num">{{ f.orden }}</td>
                <td><strong>{{ f.nombre }}</strong><div v-if="f.descripcion" class="texto-3 texto-xs">{{ f.descripcion }}</div></td>
                <td class="url">{{ f.url }}</td>
                <td class="url">{{ f.url_busqueda || '—' }}</td>
                <td><span class="insignia" :class="f.activo ? 'insignia-exito' : ''">{{ f.activo ? 'Activo' : 'Inactivo' }}</span></td>
                <td>
                  <div class="fila acciones">
                    <button type="button" class="boton boton-pequeno" :aria-label="`Editar ${f.nombre}`" @click="abrirFuente(f)"><Pencil aria-hidden="true" /> Editar</button>
                    <button type="button" class="boton boton-pequeno" :disabled="envioEstadoFuente.enviando.value" :aria-label="`${f.activo ? 'Desactivar' : 'Activar'} ${f.nombre}`" @click="alternarFuente(f)">
                      <Power aria-hidden="true" /> {{ f.activo ? 'Desactivar' : 'Activar' }}
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <!-- Renombrar -->
    <Modal v-model="renombrarAbierto" titulo="Renombrar valor" ancho="480px">
      <form id="form-renombre" class="formulario" novalidate @submit.prevent="guardarRenombre">
        <p class="texto-2 texto-pequeno">Nombre actual: <strong>{{ renombre.original }}</strong>. El cambio se verá en todos los trámites que usan este valor.</p>
        <div class="campo">
          <label for="renombre-nombre">Nuevo nombre</label>
          <input id="renombre-nombre" v-model="renombre.nombre" class="entrada" :aria-invalid="!!err(envioRenombre, 'nombre')" />
          <span v-if="err(envioRenombre, 'nombre')" class="error-campo">{{ err(envioRenombre, 'nombre') }}</span>
        </div>
      </form>
      <template #pie>
        <button type="button" class="boton" @click="renombrarAbierto = false">Cancelar</button>
        <button type="submit" form="form-renombre" class="boton boton-primario" :disabled="!renombre.nombre.trim() || renombre.nombre.trim() === renombre.original || envioRenombre.enviando.value">Guardar</button>
      </template>
    </Modal>

    <!-- Unificar -->
    <Modal v-model="unificarAbierto" titulo="Unificar duplicados" ancho="560px">
      <form id="form-unificar" class="formulario" novalidate @submit.prevent="unificar">
        <p class="texto-2 texto-pequeno">
          Use esta opción cuando el mismo valor está escrito de dos formas (por ejemplo, con y sin tilde).
          Los trámites del valor que se elimina pasan al valor que se conserva, y el valor eliminado desaparece del catálogo.
        </p>
        <div class="campo">
          <label for="union-conservar">Valor que se conserva</label>
          <select id="union-conservar" v-model="union.conservar" class="seleccion">
            <option value="" disabled>Elija un valor</option>
            <option v-for="v in valores" :key="v.id" :value="String(v.id)">{{ v.nombre }} ({{ plural(v.usos, 'uso', 'usos') }})</option>
          </select>
        </div>
        <div class="campo">
          <label for="union-eliminar">Valor que se elimina</label>
          <select id="union-eliminar" v-model="union.eliminar" class="seleccion" :aria-invalid="union.eliminar && union.eliminar === union.conservar">
            <option value="" disabled>Elija un valor</option>
            <option v-for="v in valores" :key="v.id" :value="String(v.id)" :disabled="String(v.id) === union.conservar">{{ v.nombre }} ({{ plural(v.usos, 'uso', 'usos') }})</option>
          </select>
        </div>
        <div v-if="unionValida" class="mensaje mensaje-aviso" role="status">
          <Info aria-hidden="true" />
          <span>
            {{ plural(valorPorId(union.eliminar)?.usos ?? 0, 'trámite de', 'trámites de') }} "{{ valorPorId(union.eliminar)?.nombre }}"
            pasarán a "{{ valorPorId(union.conservar)?.nombre }}". "{{ valorPorId(union.eliminar)?.nombre }}" se eliminará del catálogo. Esta operación no se puede deshacer.
          </span>
        </div>
      </form>
      <template #pie>
        <button type="button" class="boton" @click="unificarAbierto = false">Cancelar</button>
        <button type="submit" form="form-unificar" class="boton boton-peligro" :disabled="!unionValida || envioUnion.enviando.value">Unificar</button>
      </template>
    </Modal>

    <!-- Sitio legal -->
    <Modal v-model="fuenteAbierta" :titulo="fuente.id ? 'Editar sitio legal' : 'Nuevo sitio legal'" ancho="600px">
      <form id="form-fuente" class="formulario" novalidate @submit.prevent="guardarFuente">
        <div class="formulario-2">
          <div class="campo">
            <label for="fuente-nombre">Nombre<span class="requerido" aria-hidden="true">*</span></label>
            <input id="fuente-nombre" v-model="fuente.nombre" class="entrada" :aria-invalid="!!err(envioFuente, 'nombre')" />
            <span v-if="err(envioFuente, 'nombre')" class="error-campo">{{ err(envioFuente, 'nombre') }}</span>
          </div>
          <div class="campo">
            <label for="fuente-orden">Orden</label>
            <input id="fuente-orden" v-model="fuente.orden" type="number" min="0" step="1" class="entrada" aria-describedby="fuente-orden-ayuda" />
            <span id="fuente-orden-ayuda" class="ayuda">Los números menores aparecen primero.</span>
          </div>
          <div class="campo campo-ancho">
            <label for="fuente-descripcion">Descripción <span class="opcional">(opcional)</span></label>
            <input id="fuente-descripcion" v-model="fuente.descripcion" class="entrada" />
          </div>
          <div class="campo campo-ancho">
            <label for="fuente-url">Dirección<span class="requerido" aria-hidden="true">*</span></label>
            <input id="fuente-url" v-model="fuente.url" type="url" class="entrada" placeholder="https://" :aria-invalid="!!err(envioFuente, 'url')" />
            <span v-if="err(envioFuente, 'url')" class="error-campo">{{ err(envioFuente, 'url') }}</span>
          </div>
          <div class="campo campo-ancho">
            <label for="fuente-busqueda">Dirección de búsqueda <span class="opcional">(opcional)</span></label>
            <input id="fuente-busqueda" v-model="fuente.url_busqueda" type="url" class="entrada" placeholder="https://sitio.gob.bo/buscar?texto={q}" aria-describedby="fuente-busqueda-ayuda" :aria-invalid="!!err(envioFuente, 'url_busqueda')" />
            <span id="fuente-busqueda-ayuda" class="ayuda">Escriba {q} donde debe ir el texto buscado. Si el sitio no permite buscar por dirección, déjelo vacío.</span>
            <span v-if="err(envioFuente, 'url_busqueda')" class="error-campo">{{ err(envioFuente, 'url_busqueda') }}</span>
          </div>
        </div>
      </form>
      <template #pie>
        <button type="button" class="boton" @click="fuenteAbierta = false">Cancelar</button>
        <button type="submit" form="form-fuente" class="boton boton-primario" :disabled="envioFuente.enviando.value">Guardar</button>
      </template>
    </Modal>
  </div>
</template>

<style scoped>
.nota { margin-bottom: var(--e-4); }
.barra { flex-wrap: wrap; }
.agregar { flex: 1 1 320px; flex-wrap: wrap; }
.agregar .entrada { flex: 1 1 200px; width: auto; }
.ancho-total { flex-basis: 100%; }
.filtro { width: 180px; }
.inactivo td { color: var(--texto-3); }
.acciones { flex-wrap: nowrap; justify-content: flex-end; }
.seleccion-cuenta { min-width: 240px; font-size: var(--t-sm); min-height: 34px; padding: 4px 8px; }
.url { font-size: var(--t-xs); color: var(--texto-2); overflow-wrap: anywhere; min-width: 160px; }
.pie-nota { margin-top: var(--e-3); }
@media (max-width: 720px) {
  .filtro { width: 100%; flex: 1 1 140px; }
}
</style>

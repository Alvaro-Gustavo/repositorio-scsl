<script setup>
// Alta masiva de usuarios desde Excel o CSV: primero revisa la lista (sin crear nada) y muestra
// qué filas están listas y cuáles tienen errores; al confirmar crea las listas y cada persona
// recibe por correo su enlace para activar la cuenta y elegir su contraseña.
// <ImportarUsuarios v-model="abierto" @creados="cargar" />
import { ref, computed, watch } from 'vue'
import { FileSpreadsheet, Download, CheckCircle2, AlertTriangle, LoaderCircle } from '@lucide/vue'
import Modal from '@/components/ui/Modal.vue'
import { api } from '@/api'
import { useEnvio } from '@/composables/utiles'
import { ROLES } from '@/utils/constantes'
import { plural } from '@/utils/formato'

const props = defineProps({ modelValue: Boolean })
const emit = defineEmits(['update:modelValue', 'creados'])
const abierto = computed({ get: () => props.modelValue, set: (v) => emit('update:modelValue', v) })

const archivo = ref(null)
const revision = ref(null) // {filas, validas, con_error}
const { errores, enviando, enviar } = useEnvio()

watch(abierto, (v) => { if (v) { archivo.value = null; revision.value = null; errores.value = {} } })

async function elegir(e) {
  archivo.value = e.target.files?.[0] || null
  e.target.value = ''
  revision.value = null
  if (!archivo.value) return
  try {
    revision.value = await enviar(() => api.usuarios.importar(archivo.value, false))
  } catch { /* error ya mostrado */ }
}

async function crear() {
  try {
    const r = await enviar(() => api.usuarios.importar(archivo.value, true),
      `Se crearon ${plural(revision.value.validas, 'cuenta', 'cuentas')}. Cada persona recibirá su enlace de activación.`)
    emit('creados', r.creados)
    abierto.value = false
  } catch { /* error ya mostrado */ }
}

// Plantilla CSV con «;» (el separador que usa Excel en español) y BOM para que respete las tildes.
function descargarPlantilla() {
  const filas = [
    'Nombre;Correo;Cargo;Rol',
    'María Quispe Mamani;maria.quispe@contraloria.gob.bo;Abogada;Abogado',
    'Juan Pérez Rojas;juan.perez@contraloria.gob.bo;Secretario;Secretaria',
    'Ana Flores Vargas;ana.flores@contraloria.gob.bo;Jefa de unidad;Jefe'
  ]
  const url = URL.createObjectURL(new Blob(['\ufeff' + filas.join('\r\n')], { type: 'text/csv;charset=utf-8' }))
  const a = document.createElement('a')
  a.href = url
  a.download = 'plantilla-usuarios.csv'
  a.click()
  URL.revokeObjectURL(url)
}
</script>

<template>
  <Modal v-model="abierto" titulo="Importar usuarios" ancho="860px">
    <ol class="pasos texto-pequeno">
      <li>Prepare una planilla con las columnas <strong>Nombre</strong>, <strong>Correo</strong>, <strong>Cargo</strong> (opcional) y <strong>Rol</strong>
        (Administrador, Jefe, Abogado o Secretaria). Puede partir de la plantilla.</li>
      <li>Súbala: se revisa sin crear nada todavía.</li>
      <li>Confirme: se crean las cuentas sin errores y cada persona recibe un correo con su enlace para elegir su contraseña.</li>
    </ol>

    <div class="fila acciones-archivo">
      <button type="button" class="boton" @click="descargarPlantilla"><Download aria-hidden="true" /> Descargar plantilla</button>
      <label class="boton boton-primario" :class="{ deshabilitado: enviando }">
        <LoaderCircle v-if="enviando" class="girar" aria-hidden="true" /><FileSpreadsheet v-else aria-hidden="true" />
        {{ archivo ? 'Elegir otro archivo' : 'Elegir archivo (.xlsx o .csv)' }}
        <input type="file" class="sr-only" accept=".xlsx,.csv,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
          :disabled="enviando" aria-describedby="importar-error" @change="elegir" />
      </label>
      <span v-if="archivo" class="texto-pequeno texto-2">{{ archivo.name }}</span>
    </div>
    <p v-if="errores.archivo" id="importar-error" class="error-campo">{{ errores.archivo }}</p>

    <template v-if="revision">
      <p class="resumen" role="status">
        <span class="listo"><CheckCircle2 aria-hidden="true" /> {{ plural(revision.validas, 'usuario listo', 'usuarios listos') }} para crear</span>
        <span v-if="revision.con_error" class="con-error"><AlertTriangle aria-hidden="true" /> {{ plural(revision.con_error, 'fila con error', 'filas con error') }} (no se crearán)</span>
      </p>
      <div class="tabla-contenedor lista">
        <table class="tabla">
          <thead><tr><th scope="col">Fila</th><th scope="col">Nombre</th><th scope="col">Correo</th><th scope="col">Rol</th><th scope="col">Estado</th></tr></thead>
          <tbody>
            <tr v-for="f in revision.filas" :key="f.fila" :class="{ 'fila-error': f.error }">
              <td>{{ f.fila }}</td>
              <td>{{ f.nombre_completo || '—' }}<div v-if="f.cargo" class="texto-xs texto-3">{{ f.cargo }}</div></td>
              <td>{{ f.correo || '—' }}</td>
              <td>{{ ROLES[f.rol] || '—' }}</td>
              <td>
                <span v-if="f.error" class="texto-peligro">{{ f.error }}</span>
                <span v-else class="texto-exito">Listo</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>

    <template #pie>
      <button type="button" class="boton" @click="abierto = false">Cancelar</button>
      <button type="button" class="boton boton-primario" :disabled="enviando || !revision?.validas" @click="crear">
        <LoaderCircle v-if="enviando" class="girar" aria-hidden="true" />
        {{ revision?.validas ? `Crear ${plural(revision.validas, 'usuario', 'usuarios')}` : 'Crear usuarios' }}
      </button>
    </template>
  </Modal>
</template>

<style scoped>
.pasos { margin: 0 0 var(--e-4); padding-left: 20px; display: grid; gap: 4px; color: var(--texto-2); }
.acciones-archivo { flex-wrap: wrap; gap: var(--e-3); align-items: center; }
.acciones-archivo label { cursor: pointer; }
.acciones-archivo label:focus-within { box-shadow: var(--foco); }
.deshabilitado { opacity: .6; pointer-events: none; }
.resumen { display: flex; flex-wrap: wrap; gap: var(--e-4); margin: var(--e-4) 0 var(--e-2); font-weight: 600; font-size: var(--t-sm); }
.resumen span { display: inline-flex; align-items: center; gap: 6px; }
.resumen svg { width: 16px; height: 16px; }
.listo { color: var(--exito); }
.con-error { color: var(--peligro); }
.lista { max-height: 46vh; overflow: auto; border: 1px solid var(--linea); border-radius: var(--radio-control); }
.fila-error td { background: var(--peligro-suave); }
.texto-peligro { color: var(--peligro); }
.texto-exito { color: var(--exito); font-weight: 600; }
</style>

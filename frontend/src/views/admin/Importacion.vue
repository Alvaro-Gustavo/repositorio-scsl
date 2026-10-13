<script setup>
// Importación controlada del Excel histórico: elegir, analizar, probar, migrar.
import { ref, computed } from 'vue'
import { FileSpreadsheet, Upload, FlaskConical, Database, ShieldCheck, Info, TriangleAlert, CircleCheck, RotateCcw, History } from '@lucide/vue'
import { api } from '@/api'
import { useCarga, useEnvio } from '@/composables/utiles'
import { formatoFechaHora, formatoNumero, plural } from '@/utils/formato'
import Modal from '@/components/ui/Modal.vue'
import Cargando from '@/components/ui/Cargando.vue'
import EstadoVacio from '@/components/ui/EstadoVacio.vue'

const PASOS = ['Elegir archivo', 'Revisar análisis', 'Probar y migrar', 'Resultado']

const archivo = ref(null)
const errorArchivo = ref('')
const arrastrando = ref(false)
const entrada = ref(null)
const analisis = ref(null)
const simulacion = ref(null)
const definitiva = ref(null)

const pasoActual = computed(() => (definitiva.value ? 4 : analisis.value ? (simulacion.value ? 3 : 2) : 1))

const { datos: historial, cargando: cargandoHistorial, error: errorHistorial, cargar: cargarHistorial } = useCarga(() => api.importacion.historial(), { inicial: [] })

// Paso 1: archivo
function elegir(lista) {
  const f = lista?.[0]
  errorArchivo.value = ''
  if (!f) return
  if (!/\.(xlsx|xls)$/i.test(f.name)) {
    errorArchivo.value = 'El archivo debe ser un Excel (.xlsx o .xls).'
    return
  }
  archivo.value = f
  analisis.value = null
  simulacion.value = null
  definitiva.value = null
}
function alSoltar(e) { arrastrando.value = false; elegir(e.dataTransfer?.files) }
const tamano = (b) => (b >= 1048576 ? `${(b / 1048576).toLocaleString('es-BO', { maximumFractionDigits: 1 })} MB` : `${Math.max(1, Math.round(b / 1024))} KB`)

// Paso 2: análisis
const envioAnalisis = useEnvio()
async function analizar() {
  try {
    analisis.value = await envioAnalisis.enviar(() => api.importacion.analizar(archivo.value))
    simulacion.value = null
  } catch (e) {
    if (e.campos?.archivo) errorArchivo.value = e.campos.archivo
  }
}
const resumen = computed(() => {
  const r = analisis.value?.resumen || {}
  return [
    { etiqueta: 'Filas encontradas', valor: r.filas },
    { etiqueta: 'Listas para migrar', valor: r.listas, tono: 'exito' },
    { etiqueta: 'Con incidencias', valor: r.con_incidencias, tono: r.con_incidencias ? 'aviso' : '' },
    { etiqueta: 'Hojas de ruta repetidas', valor: r.hojas_ruta_repetidas, tono: r.hojas_ruta_repetidas ? 'aviso' : '' },
    { etiqueta: 'Fechas ilegibles', valor: r.fechas_ilegibles, tono: r.fechas_ilegibles ? 'aviso' : '' },
    { etiqueta: 'Entidades nuevas', valor: r.entidades_nuevas, tono: 'info' }
  ].filter((x) => x.valor !== undefined && x.valor !== null)
})
const TIPOS_INCIDENCIA = {
  FECHA_ILEGIBLE: 'Fecha ilegible',
  ENTIDAD_VACIA: 'Entidad vacía',
  PROCEDENCIA_AMBIGUA: 'Procedencia ambigua',
  HOJA_RUTA_REPETIDA: 'Hoja de ruta repetida',
  TIPO_TRAMITE_VACIO: 'Tipo de trámite vacío'
}
const tipoIncidencia = (t) => TIPOS_INCIDENCIA[t] || (t ? t.charAt(0) + t.slice(1).toLowerCase().replace(/_/g, ' ') : '—')
const porcentaje = (c) => { const t = c.completos + c.vacios; return t ? Math.round((100 * c.completos) / t) : 0 }

// Paso 3: simulación y migración definitiva
const envioSimulacion = useEnvio()
async function probar() {
  try {
    simulacion.value = await envioSimulacion.enviar(() => api.importacion.ejecutar(analisis.value.id, 'SIMULACION'), 'Prueba de migración terminada')
  } catch { /* error mostrado */ }
}
const confirmarAbierto = ref(false)
const confirmacion = ref({ revisado: false, texto: '' })
const PALABRA = 'migrar'
function abrirConfirmar() { confirmacion.value = { revisado: false, texto: '' }; confirmarAbierto.value = true }
const confirmacionValida = computed(() => confirmacion.value.revisado && confirmacion.value.texto.trim().toLowerCase() === PALABRA)
const envioDefinitiva = useEnvio()
async function migrar() {
  try {
    definitiva.value = await envioDefinitiva.enviar(() => api.importacion.ejecutar(analisis.value.id, 'DEFINITIVA'), 'Migración definitiva completada')
    confirmarAbierto.value = false
    cargarHistorial()
  } catch { /* error mostrado */ }
}

function reiniciar() {
  archivo.value = null
  analisis.value = null
  simulacion.value = null
  definitiva.value = null
  errorArchivo.value = ''
  if (entrada.value) entrada.value.value = ''
}
const esDemo = computed(() => analisis.value?.demo || simulacion.value?.demo || definitiva.value?.demo)
const ESTADOS = { COMPLETADA: 'insignia-exito', FALLIDA: 'insignia-peligro', EN_CURSO: 'insignia-info' }
</script>

<template>
  <div class="pagina">
    <header class="pagina-cabecera">
      <div>
        <h1>Importar Excel histórico</h1>
        <p>Traiga al repositorio los registros que los profesionales llevaban en Excel. Primero se analiza y se prueba; la migración definitiva se confirma al final.</p>
      </div>
    </header>

    <ul class="principios" aria-label="Principios de la importación">
      <li><ShieldCheck aria-hidden="true" /><span><strong>El Excel original no se modifica.</strong> El sistema solo lo lee.</span></li>
      <li><ShieldCheck aria-hidden="true" /><span><strong>No se inventan datos.</strong> Lo que está vacío en el Excel queda vacío.</span></li>
      <li><ShieldCheck aria-hidden="true" /><span><strong>Lo dudoso no se corrige solo.</strong> Queda como incidencia para revisión.</span></li>
    </ul>

    <ol class="pasos" aria-label="Pasos de la importación">
      <li v-for="(nombre, i) in PASOS" :key="nombre" :class="{ hecho: pasoActual > i + 1, actual: pasoActual === i + 1 }" :aria-current="pasoActual === i + 1 ? 'step' : undefined">
        <span class="paso-numero" aria-hidden="true">{{ i + 1 }}</span>
        <span>{{ nombre }}</span>
      </li>
    </ol>

    <div v-if="esDemo" class="mensaje mensaje-aviso bloque" role="status">
      <Info aria-hidden="true" />
      <span>Modo de demostración: el análisis y los resultados son simulados y no se agregan registros. Con el servidor real se lee el archivo elegido.</span>
    </div>

    <!-- Paso 1 -->
    <section class="panel" aria-labelledby="paso1-titulo">
      <div class="panel-cabecera"><h2 id="paso1-titulo">1. Elegir archivo</h2></div>
      <div class="panel-cuerpo">
        <label
          for="archivo-excel" class="zona" :class="{ arrastrando, con_archivo: archivo }"
          @dragover.prevent="arrastrando = true" @dragleave.prevent="arrastrando = false" @drop.prevent="alSoltar"
        >
          <FileSpreadsheet aria-hidden="true" class="zona-icono" />
          <span v-if="archivo"><strong>{{ archivo.name }}</strong> · {{ tamano(archivo.size) }}</span>
          <span v-else><strong>Suelte aquí el archivo Excel</strong> o haga clic para elegirlo</span>
          <span class="ayuda">Formatos aceptados: .xlsx y .xls</span>
          <input
            id="archivo-excel" ref="entrada" type="file" class="sr-only" accept=".xlsx,.xls,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.ms-excel"
            :aria-invalid="!!errorArchivo" aria-describedby="archivo-error" :disabled="!!definitiva" @change="elegir($event.target.files)"
          />
        </label>
        <p v-if="errorArchivo" id="archivo-error" class="error-campo" role="alert">{{ errorArchivo }}</p>
        <div class="formulario-acciones">
          <button v-if="archivo && !definitiva" type="button" class="boton" @click="reiniciar">Quitar archivo</button>
          <button type="button" class="boton boton-primario" :disabled="!archivo || envioAnalisis.enviando.value || !!definitiva" @click="analizar">
            <Upload aria-hidden="true" /> {{ analisis ? 'Volver a analizar' : 'Analizar archivo' }}
          </button>
        </div>
        <Cargando v-if="envioAnalisis.enviando.value" texto="Analizando hojas, columnas y registros…" />
      </div>
    </section>

    <!-- Paso 2 -->
    <section v-if="analisis" class="panel" aria-labelledby="paso2-titulo">
      <div class="panel-cabecera">
        <h2 id="paso2-titulo">2. Revisar análisis</h2>
        <span class="texto-2 texto-pequeno">{{ analisis.archivo }}<template v-if="analisis.hojas?.length"> · {{ plural(analisis.hojas.length, 'hoja', 'hojas') }}: {{ analisis.hojas.join(', ') }}</template></span>
      </div>
      <div class="panel-cuerpo pila">
        <dl class="cifras">
          <div v-for="c in resumen" :key="c.etiqueta" :class="`cifra-${c.tono || 'normal'}`">
            <dt>{{ c.etiqueta }}</dt>
            <dd>{{ formatoNumero(c.valor) }}</dd>
          </div>
        </dl>

        <div>
          <h3 class="subtitulo">Correspondencia de columnas</h3>
          <p class="texto-2 texto-pequeno">Cómo se lee cada columna del Excel y a qué dato del sistema pasa.</p>
          <div class="tabla-contenedor marco-tabla">
            <table class="tabla">
              <thead>
                <tr>
                  <th scope="col">Columna del Excel</th>
                  <th scope="col">Dato del sistema</th>
                  <th scope="col" class="num">Completos</th>
                  <th scope="col" class="num">Vacíos</th>
                  <th scope="col">Cobertura</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="c in analisis.columnas" :key="c.excel">
                  <td class="codigo">{{ c.excel }}</td>
                  <td>{{ c.destino || 'Sin correspondencia (no se migra)' }}</td>
                  <td class="num">{{ formatoNumero(c.completos) }}</td>
                  <td class="num" :class="{ 'texto-aviso': c.vacios }">{{ formatoNumero(c.vacios) }}</td>
                  <td>
                    <div class="barra-cobertura" role="img" :aria-label="`${porcentaje(c)} % completo`">
                      <span :style="{ width: porcentaje(c) + '%' }" />
                    </div>
                    <span class="texto-3 texto-xs">{{ porcentaje(c) }} %</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div>
          <h3 class="subtitulo">Incidencias para revisión</h3>
          <p v-if="analisis.incidencias?.length" class="texto-2 texto-pequeno">
            Estas filas se migran tal como están en el Excel y quedan marcadas para que un responsable las revise.
            <template v-if="analisis.resumen?.con_incidencias > analisis.incidencias.length">Se muestran {{ analisis.incidencias.length }} de {{ formatoNumero(analisis.resumen.con_incidencias) }}.</template>
          </p>
          <EstadoVacio v-if="!analisis.incidencias?.length" :icono="CircleCheck" titulo="Sin incidencias" texto="No se encontraron datos dudosos en el archivo." />
          <div v-else class="tabla-contenedor marco-tabla">
            <table class="tabla">
              <thead>
                <tr><th scope="col" class="num">Fila</th><th scope="col">Tipo</th><th scope="col">Descripción</th></tr>
              </thead>
              <tbody>
                <tr v-for="(inc, i) in analisis.incidencias" :key="`${inc.fila}-${i}`">
                  <td class="num">{{ inc.fila }}</td>
                  <td class="sin-salto"><span class="insignia insignia-aviso">{{ tipoIncidencia(inc.tipo) }}</span></td>
                  <td>{{ inc.descripcion }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </section>

    <!-- Paso 3 -->
    <section v-if="analisis" class="panel" aria-labelledby="paso3-titulo">
      <div class="panel-cabecera"><h2 id="paso3-titulo">3. Probar y migrar</h2></div>
      <div class="panel-cuerpo pila">
        <div class="opcion-paso">
          <div>
            <h3>Probar migración</h3>
            <p class="texto-2 texto-pequeno">Ejecuta todo el proceso sin guardar nada, para ver cuántos registros entrarían y cuántos se rechazarían.</p>
          </div>
          <button type="button" class="boton" :disabled="envioSimulacion.enviando.value || !!definitiva" @click="probar">
            <FlaskConical aria-hidden="true" /> {{ simulacion ? 'Probar otra vez' : 'Probar migración' }}
          </button>
        </div>
        <Cargando v-if="envioSimulacion.enviando.value" texto="Probando la migración…" />
        <dl v-if="simulacion" class="cifras">
          <div><dt>Registros encontrados</dt><dd>{{ formatoNumero(simulacion.encontrados) }}</dd></div>
          <div class="cifra-exito"><dt>Entrarían</dt><dd>{{ formatoNumero(simulacion.simulados ?? simulacion.insertados) }}</dd></div>
          <div :class="simulacion.rechazados ? 'cifra-peligro' : ''"><dt>Rechazados</dt><dd>{{ formatoNumero(simulacion.rechazados) }}</dd></div>
          <div :class="simulacion.incidencias ? 'cifra-aviso' : ''"><dt>Con incidencias</dt><dd>{{ formatoNumero(simulacion.incidencias) }}</dd></div>
        </dl>

        <hr class="separador" />

        <div class="opcion-paso">
          <div>
            <h3>Migrar definitivamente</h3>
            <p class="texto-2 texto-pequeno">
              Guarda los registros en la base de datos oficial. Antes de hacerlo, el servidor debe contar con un respaldo reciente.
              <template v-if="!simulacion"> Primero pruebe la migración.</template>
            </p>
          </div>
          <button type="button" class="boton boton-primario" :disabled="!simulacion || !!definitiva" @click="abrirConfirmar">
            <Database aria-hidden="true" /> Migrar definitivamente
          </button>
        </div>
      </div>
    </section>

    <!-- Paso 4 -->
    <section v-if="definitiva" class="panel" aria-labelledby="paso4-titulo">
      <div class="panel-cabecera">
        <h2 id="paso4-titulo">4. Resultado</h2>
        <span class="insignia" :class="ESTADOS[definitiva.estado] || ''">{{ definitiva.estado === 'COMPLETADA' ? 'Migración completada' : definitiva.estado }}</span>
      </div>
      <div class="panel-cuerpo pila">
        <dl class="cifras">
          <div><dt>Registros encontrados</dt><dd>{{ formatoNumero(definitiva.encontrados) }}</dd></div>
          <div class="cifra-exito"><dt>Migrados</dt><dd>{{ formatoNumero(definitiva.insertados) }}</dd></div>
          <div :class="definitiva.rechazados ? 'cifra-peligro' : ''"><dt>Rechazados</dt><dd>{{ formatoNumero(definitiva.rechazados) }}</dd></div>
          <div :class="definitiva.incidencias ? 'cifra-aviso' : ''"><dt>Con incidencias</dt><dd>{{ formatoNumero(definitiva.incidencias) }}</dd></div>
        </dl>
        <p class="texto-2 texto-pequeno">Fecha: {{ formatoFechaHora(definitiva.fecha) }}. La operación quedó registrada en la auditoría y en el historial de importaciones.</p>
        <div class="formulario-acciones">
          <button type="button" class="boton" @click="reiniciar"><RotateCcw aria-hidden="true" /> Importar otro archivo</button>
        </div>
      </div>
    </section>

    <!-- Historial -->
    <section class="panel" aria-labelledby="historial-titulo">
      <div class="panel-cabecera"><h2 id="historial-titulo" class="fila"><History aria-hidden="true" class="icono-titulo" /> Historial de importaciones</h2></div>
      <Cargando v-if="cargandoHistorial && !historial.length" />
      <div v-else-if="errorHistorial" class="panel-cuerpo"><div class="mensaje mensaje-peligro" role="alert">{{ errorHistorial }}</div></div>
      <EstadoVacio v-else-if="!historial.length" :icono="History" titulo="Todavía no se importó ningún archivo" />
      <div v-else class="tabla-contenedor">
        <table class="tabla">
          <thead>
            <tr>
              <th scope="col">Fecha</th>
              <th scope="col">Archivo</th>
              <th scope="col">Modo</th>
              <th scope="col">Estado</th>
              <th scope="col" class="num">Encontrados</th>
              <th scope="col" class="num">Migrados</th>
              <th scope="col" class="num">Rechazados</th>
              <th scope="col" class="num">Incidencias</th>
              <th scope="col">Ejecutado por</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="h in historial" :key="h.id">
              <td class="sin-salto">{{ formatoFechaHora(h.fecha) }}</td>
              <td>{{ h.archivo }}</td>
              <td>{{ h.modo === 'DEFINITIVA' ? 'Definitiva' : h.modo === 'SIMULACION' ? 'Prueba' : h.modo }}</td>
              <td><span class="insignia" :class="ESTADOS[h.estado] || ''">{{ h.estado === 'COMPLETADA' ? 'Completada' : h.estado === 'FALLIDA' ? 'Fallida' : h.estado }}</span></td>
              <td class="num">{{ formatoNumero(h.encontrados) }}</td>
              <td class="num">{{ formatoNumero(h.insertados) }}</td>
              <td class="num">{{ formatoNumero(h.rechazados) }}</td>
              <td class="num">{{ formatoNumero(h.incidencias) }}</td>
              <td>{{ h.ejecutado_por }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- Confirmación fuerte -->
    <Modal v-model="confirmarAbierto" titulo="Confirmar migración definitiva" ancho="560px">
      <form id="form-migrar" class="formulario" novalidate @submit.prevent="migrar">
        <div class="mensaje mensaje-peligro">
          <TriangleAlert aria-hidden="true" />
          <span>
            Se guardarán {{ plural(simulacion?.simulados ?? simulacion?.encontrados ?? 0, 'registro', 'registros') }} de
            <strong>{{ analisis?.archivo }}</strong> en la base de datos oficial. Los registros migrados no se borran después: solo pueden darse de baja uno por uno.
          </span>
        </div>
        <ul class="texto-2 texto-pequeno lista-revision">
          <li>{{ plural(simulacion?.incidencias ?? 0, 'registro queda', 'registros quedan') }} con incidencias para revisión.</li>
          <li>{{ plural(simulacion?.rechazados ?? 0, 'registro no entrará', 'registros no entrarán') }}.</li>
          <li>Si este archivo ya fue importado antes, podría duplicar trámites. Revise el historial.</li>
        </ul>
        <label class="casilla">
          <input v-model="confirmacion.revisado" type="checkbox" />
          Revisé el análisis, la prueba y confirmo que existe un respaldo reciente.
        </label>
        <div class="campo">
          <label for="confirmar-texto">Para confirmar, escriba <strong>{{ PALABRA }}</strong></label>
          <input id="confirmar-texto" v-model="confirmacion.texto" class="entrada" autocomplete="off" spellcheck="false" />
        </div>
      </form>
      <template #pie>
        <button type="button" class="boton" @click="confirmarAbierto = false">Cancelar</button>
        <button type="submit" form="form-migrar" class="boton boton-peligro" :disabled="!confirmacionValida || envioDefinitiva.enviando.value">
          {{ envioDefinitiva.enviando.value ? 'Migrando…' : 'Migrar definitivamente' }}
        </button>
      </template>
    </Modal>
  </div>
</template>

<style scoped>
.principios { list-style: none; margin: 0 0 var(--e-6); padding: 0; display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: var(--e-3); }
.principios li { display: flex; gap: var(--e-2); align-items: flex-start; font-size: var(--t-sm); color: var(--texto-2); padding: var(--e-3) var(--e-4); border-left: 3px solid var(--sello); background: var(--superficie); border-radius: 0 var(--radio-control) var(--radio-control) 0; }
.principios svg { width: 18px; height: 18px; color: var(--sello); flex: none; margin-top: 2px; }
.principios strong { color: var(--tinta); }

.pasos { list-style: none; margin: 0 0 var(--e-6); padding: 0; display: flex; gap: var(--e-2); flex-wrap: wrap; counter-reset: none; }
.pasos li { display: flex; align-items: center; gap: var(--e-2); font-size: var(--t-sm); color: var(--texto-3); font-weight: 600; padding-right: var(--e-4); }
.pasos li:not(:last-child)::after { content: ''; width: 28px; height: 1px; background: var(--linea-fuerte); margin-left: var(--e-2); }
.paso-numero { display: inline-grid; place-items: center; width: 26px; height: 26px; border-radius: 50%; border: 1.5px solid var(--linea-fuerte); background: var(--superficie); font-size: var(--t-xs); }
.pasos .actual { color: var(--tinta); }
.pasos .actual .paso-numero { border-color: var(--sello); background: var(--sello); color: var(--texto-inverso); }
.pasos .hecho { color: var(--texto-2); }
.pasos .hecho .paso-numero { border-color: var(--exito); color: var(--exito); }

.bloque { margin-bottom: var(--e-6); }

.zona { display: flex; flex-direction: column; align-items: center; gap: var(--e-2); padding: var(--e-8) var(--e-4); border: 2px dashed var(--linea-fuerte); border-radius: var(--radio-panel); background: var(--superficie-2); text-align: center; cursor: pointer; color: var(--texto-2); font-weight: 400; }
.zona:hover, .zona.arrastrando { border-color: var(--sello); background: var(--sello-suave); }
.zona:focus-within { box-shadow: var(--foco); border-color: var(--sello); }
.zona.con_archivo { border-style: solid; border-color: var(--sello); }
.zona-icono { width: 36px; height: 36px; color: var(--sello); }
.formulario-acciones { margin-top: var(--e-4); }

.cifras { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: var(--e-3); margin: 0; }
.cifras div { padding: var(--e-3) var(--e-4); border: 1px solid var(--linea); border-radius: var(--radio-control); border-top: 3px solid var(--linea-fuerte); }
.cifras dt { font-size: var(--t-xs); color: var(--texto-2); }
.cifras dd { margin: 2px 0 0; font-size: var(--t-xl); font-weight: 650; color: var(--tinta); }
.cifras .cifra-exito { border-top-color: var(--exito); }
.cifras .cifra-aviso { border-top-color: var(--aviso); }
.cifras .cifra-aviso dd { color: var(--aviso); }
.cifras .cifra-peligro { border-top-color: var(--peligro); }
.cifras .cifra-peligro dd { color: var(--peligro); }
.cifras .cifra-info { border-top-color: var(--info); }

.subtitulo { margin-bottom: var(--e-1); }
.marco-tabla { margin-top: var(--e-3); border: 1px solid var(--linea); border-radius: var(--radio-control); }
.texto-aviso { color: var(--aviso); font-weight: 600; }
.sin-salto { white-space: nowrap; }
.barra-cobertura { width: 100px; height: 6px; background: var(--linea); border-radius: 3px; overflow: hidden; margin: 6px 0 2px; }
.barra-cobertura span { display: block; height: 100%; background: var(--concluido); }

.opcion-paso { display: flex; justify-content: space-between; align-items: flex-start; gap: var(--e-4); flex-wrap: wrap; }
.opcion-paso > div { flex: 1 1 320px; }
.opcion-paso h3 { margin-bottom: var(--e-1); }
.separador { margin: 0; }
.icono-titulo { width: 18px; height: 18px; color: var(--texto-3); }
.lista-revision { margin: 0; padding-left: var(--e-5); }
@media (max-width: 720px) {
  .pasos li:not(:last-child)::after { display: none; }
}
</style>

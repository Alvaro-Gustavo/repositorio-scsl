<script setup>
// Tablero de avance para la jefatura: estado general, avance por abogado,
// distribucion por gestion, tipo de documento y tipo de tramite, ritmo mensual y vencidos.
import { ref, computed, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { Printer, RefreshCw, AlarmClock, Settings } from '@lucide/vue'
import { api } from '@/api'
import { useSesion } from '@/stores/sesion'
import { useCarga, imprimirConAuditoria } from '@/composables/utiles'
import { formatoNumero, formatoFecha, plural } from '@/utils/formato'
import Cargando from '@/components/ui/Cargando.vue'
import GraficoBarras from '@/components/ui/GraficoBarras.vue'
import EncabezadoImpresion from '@/components/ui/EncabezadoImpresion.vue'
import TableroColumnasMes from '@/components/tramites/TableroColumnasMes.vue'

const sesion = useSesion()
const anio = ref('')
const { datos, cargando, error, cargar } = useCarga(() => api.tablero.resumen({ anio: anio.value || undefined }))
watch(anio, () => cargar())

const anios = ref([])
watch(datos, (d) => { if (d?.anios?.length && !anios.value.length) anios.value = d.anios })

const SERIES_ESTADO = [
  { clave: 'concluidos', etiqueta: 'Concluidos o archivados', color: 'var(--concluido)' },
  { clave: 'en_elaboracion', etiqueta: 'En elaboración', color: 'var(--elaboracion)' },
  { clave: 'sin_asignar', etiqueta: 'Sin asignar', color: 'var(--recibido)' }
]
const SERIES_MES = [
  { clave: 'registrados', etiqueta: 'Registrados', color: 'var(--recibido)' },
  { clave: 'concluidos', etiqueta: 'Concluidos', color: 'var(--concluido)' }
]

const t = computed(() => datos.value?.totales || {})
const indicadores = computed(() => [
  { clave: 'RECIBIDO', etiqueta: 'Recibidos', ayuda: 'sin abogado', valor: t.value.RECIBIDO, color: 'var(--recibido)' },
  { clave: 'EN_ELABORACION', etiqueta: 'En elaboración', ayuda: 'con abogado', valor: t.value.EN_ELABORACION, color: 'var(--elaboracion)' },
  { clave: 'CONCLUIDO', etiqueta: 'Concluidos', ayuda: 'con informe', valor: t.value.CONCLUIDO, color: 'var(--concluido)' },
  { clave: 'ARCHIVADO', etiqueta: 'Archivados', ayuda: 'cierre definitivo', valor: t.value.ARCHIVADO, color: 'var(--archivado)' }
])
const proporcion = (v) => (t.value.total ? (100 * (v || 0)) / t.value.total : 0)

const filas = (lista) => (lista || []).map((x) => ({ nombre: x.nombre, valores: { concluidos: x.concluidos, en_elaboracion: x.en_elaboracion, sin_asignar: x.sin_asignar } }))
const porAbogado = computed(() => (datos.value?.por_abogado || []).filter((a) => a.clave))
const sinAsignar = computed(() => (datos.value?.por_abogado || []).find((a) => !a.clave))
const ritmoMes = computed(() => (datos.value?.por_mes || []).reduce((s, m) => ({ r: s.r + m.registrados, c: s.c + m.concluidos }), { r: 0, c: 0 }))

const criterio = computed(() => `Gestión: ${anio.value || 'todas'}`)
function imprimir() {
  imprimirConAuditoria({ pantalla: 'tablero', anio: anio.value || 'todas', total: t.value.total }, 'TABLERO')
}
const dias = (n) => (n === null || n === undefined ? '—' : plural(n, 'día', 'días'))
</script>

<template>
  <div class="pagina">
    <EncabezadoImpresion titulo="Tablero de avance" :criterio="criterio" :resultados="t.total ?? null" />

    <header class="pagina-cabecera">
      <div>
        <h1>Tablero de avance</h1>
        <p>Cómo avanza el trabajo de la Subcontraloría: carga por abogado, ritmo mensual y trámites que superan el plazo.</p>
      </div>
      <div class="pagina-acciones no-imprimir">
        <div class="selector-anio">
          <label for="tablero-anio" class="etiqueta">Gestión</label>
          <select id="tablero-anio" v-model="anio" class="seleccion">
            <option value="">Todas</option>
            <option v-for="a in anios" :key="a" :value="String(a)">{{ a }}</option>
          </select>
        </div>
        <button type="button" class="boton" :disabled="cargando" aria-label="Actualizar datos" @click="cargar()"><RefreshCw aria-hidden="true" /></button>
        <button type="button" class="boton" :disabled="!datos" @click="imprimir"><Printer aria-hidden="true" /> Imprimir</button>
      </div>
    </header>

    <Cargando v-if="cargando && !datos" texto="Calculando el avance…" />
    <p v-else-if="error" class="mensaje mensaje-peligro" role="alert">{{ error }}</p>

    <div v-else-if="datos" class="pila" :class="{ atenuado: cargando }" :aria-busy="cargando">
      <!-- Indicadores -->
      <section class="panel resumen" aria-labelledby="titulo-resumen">
        <h2 id="titulo-resumen" class="sr-only">Resumen</h2>
        <div class="resumen-total">
          <span class="resumen-numero">{{ formatoNumero(t.total) }}</span>
          <span class="resumen-etiqueta">trámites {{ anio ? `de la gestión ${anio}` : 'en total' }}</span>
          <span v-if="!anio && t.gestion_actual" class="texto-3 texto-xs">{{ formatoNumero(t.gestion_actual) }} de la gestión actual</span>
        </div>
        <dl class="resumen-estados">
          <div v-for="i in indicadores" :key="i.clave">
            <dt><span class="marca" :style="{ background: i.color }" aria-hidden="true" />{{ i.etiqueta }}</dt>
            <dd>{{ formatoNumero(i.valor) }} <small class="texto-3">{{ i.ayuda }}</small></dd>
          </div>
          <div class="vencidos-indicador" :class="{ alerta: t.vencidos > 0 }">
            <dt><AlarmClock aria-hidden="true" class="icono" />Vencidos</dt>
            <dd v-if="datos.plazo_dias">{{ formatoNumero(t.vencidos) }} <small class="texto-3">más de {{ datos.plazo_dias }} días</small></dd>
            <dd v-else class="sin-plazo">—<small class="texto-3">plazo sin configurar</small></dd>
          </div>
        </dl>
        <div v-if="t.total" class="proporcion" aria-hidden="true">
          <span v-for="i in indicadores" :key="i.clave" :style="{ width: `${proporcion(i.valor)}%`, background: i.color }" />
        </div>
      </section>

      <!-- Avance por abogado -->
      <section class="panel" aria-labelledby="titulo-abogados">
        <div class="panel-cabecera">
          <h2 id="titulo-abogados">Avance por abogado</h2>
          <span v-if="sinAsignar?.total" class="texto-pequeno texto-2">{{ plural(sinAsignar.total, 'trámite sin asignar', 'trámites sin asignar') }}</span>
        </div>
        <div class="panel-cuerpo">
          <GraficoBarras :filas="filas(porAbogado)" :series="SERIES_ESTADO.slice(0, 2)" vacio="Aún no hay trámites asignados." />
          <div v-if="porAbogado.length" class="tabla-contenedor tabla-separada">
            <table class="tabla">
              <thead>
                <tr>
                  <th scope="col">Abogado</th>
                  <th scope="col" class="num">Asignados</th>
                  <th scope="col" class="num">Concluidos</th>
                  <th scope="col" class="num">En elaboración</th>
                  <th scope="col" class="num">Avance</th>
                  <th scope="col" class="num">Promedio de elaboración</th>
                  <th scope="col" class="num">Pendiente más antiguo</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="a in porAbogado" :key="a.clave">
                  <th scope="row" class="nombre-fila">{{ a.nombre }}</th>
                  <td class="num">{{ formatoNumero(a.total) }}</td>
                  <td class="num">{{ formatoNumero(a.concluidos) }}</td>
                  <td class="num">{{ formatoNumero(a.en_elaboracion) }}</td>
                  <td class="num">
                    <span class="avance">
                      <span class="avance-pista" aria-hidden="true"><span :style="{ width: `${a.porcentaje_avance}%` }" /></span>
                      {{ formatoNumero(a.porcentaje_avance) }} %
                    </span>
                  </td>
                  <td class="num">{{ dias(a.promedio_dias_elaboracion) }}</td>
                  <td class="num" :class="{ tarde: datos.plazo_dias && a.dias_pendiente_mas_antiguo > datos.plazo_dias }">{{ dias(a.dias_pendiente_mas_antiguo) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>

      <div class="rejilla-2">
        <!-- Por gestion -->
        <section class="panel" aria-labelledby="titulo-anio">
          <div class="panel-cabecera"><h2 id="titulo-anio">Por año de gestión</h2></div>
          <div class="panel-cuerpo">
            <GraficoBarras :filas="filas(datos.por_anio)" :series="SERIES_ESTADO" />
            <div v-if="datos.por_anio?.length" class="tabla-contenedor tabla-separada">
              <table class="tabla">
                <thead><tr><th scope="col">Gestión</th><th scope="col" class="num">Total</th><th scope="col" class="num">Concluidos</th><th scope="col" class="num">Pendientes</th><th scope="col" class="num">Avance</th></tr></thead>
                <tbody>
                  <tr v-for="a in datos.por_anio" :key="a.clave">
                    <th scope="row" class="codigo">{{ a.nombre }}</th>
                    <td class="num">{{ formatoNumero(a.total) }}</td>
                    <td class="num">{{ formatoNumero(a.concluidos) }}</td>
                    <td class="num">{{ formatoNumero(a.en_elaboracion + a.sin_asignar) }}</td>
                    <td class="num">{{ formatoNumero(a.porcentaje_avance) }} %</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </section>

        <div class="pila">
          <!-- Por tipo de documento -->
          <section class="panel" aria-labelledby="titulo-tdoc">
            <div class="panel-cabecera"><h2 id="titulo-tdoc">Por tipo de documento</h2></div>
            <div class="panel-cuerpo">
              <GraficoBarras :filas="filas(datos.por_tipo_documento)" :series="SERIES_ESTADO" />
            </div>
          </section>

          <!-- Por tipo de tramite -->
          <section class="panel" aria-labelledby="titulo-ttram">
            <div class="panel-cabecera"><h2 id="titulo-ttram">Por tipo de trámite</h2></div>
            <div class="panel-cuerpo">
              <GraficoBarras :filas="filas(datos.por_tipo_tramite)" :series="SERIES_ESTADO" />
            </div>
          </section>
        </div>
      </div>
      <!-- Ritmo mensual -->
      <section class="panel" aria-labelledby="titulo-mes">
        <div class="panel-cabecera">
          <h2 id="titulo-mes">Registrados y concluidos por mes</h2>
          <span class="texto-pequeno texto-2">Últimos 12 meses · {{ formatoNumero(ritmoMes.r) }} registrados, {{ formatoNumero(ritmoMes.c) }} concluidos</span>
        </div>
        <div class="panel-cuerpo">
          <TableroColumnasMes :meses="datos.por_mes || []" :series="SERIES_MES" titulo="Trámites registrados y concluidos por mes" />
          <p class="ayuda nota">Este gráfico siempre muestra los últimos 12 meses, sin importar la gestión elegida.</p>
        </div>
      </section>

      <!-- Vencidos -->
      <section class="panel" aria-labelledby="titulo-vencidos">
        <div class="panel-cabecera">
          <h2 id="titulo-vencidos">Trámites vencidos</h2>
          <span v-if="datos.plazo_dias" class="texto-pequeno texto-2">Más de {{ plural(datos.plazo_dias, 'día', 'días') }} en elaboración</span>
        </div>
        <div v-if="!datos.plazo_dias" class="panel-cuerpo">
          <div class="mensaje mensaje-info">
            <Settings aria-hidden="true" />
            <div>
              <p>El plazo para considerar vencido un trámite no está configurado, por eso no se marca ninguno.</p>
              <p v-if="sesion.puede('GESTIONAR_RETENCION')" class="no-imprimir"><RouterLink to="/admin/configuracion">Configurar el plazo en días</RouterLink></p>
              <p v-else>Pida al administrador que lo configure.</p>
            </div>
          </div>
        </div>
        <p v-else-if="!datos.vencidos?.length" class="panel-cuerpo texto-2 texto-pequeno">Ningún trámite supera el plazo. Buen trabajo.</p>
        <ul v-else class="vencidos">
          <li v-for="v in datos.vencidos" :key="v.id">
            <div class="vencido-principal">
              <RouterLink :to="`/tramites/${v.id}`" class="codigo codigo-sello">{{ v.hoja_ruta }}</RouterLink>
              <span class="vencido-asunto">{{ v.asunto }}</span>
              <span class="texto-3 texto-xs">{{ v.profesional?.nombre_completo || 'Sin abogado' }} · {{ v.entidad?.nombre || '—' }} · asignado el {{ formatoFecha(v.fecha_asignacion) }}</span>
            </div>
            <span class="vencido-dias"><strong>{{ formatoNumero(v.dias_en_elaboracion) }}</strong> días</span>
          </li>
        </ul>
      </section>

    </div>
  </div>
</template>

<style scoped>
.selector-anio { display: flex; align-items: center; gap: var(--e-2); }
.selector-anio .seleccion { min-width: 120px; min-height: 38px; padding-top: 4px; padding-bottom: 4px; }
.atenuado { opacity: .6; transition: opacity .15s; }

/* Resumen: una sola franja con divisores, sin tarjetas repetidas */
.resumen { display: grid; grid-template-columns: minmax(180px, auto) 1fr; overflow: hidden; }
.resumen-total { display: flex; flex-direction: column; justify-content: center; gap: 2px; padding: var(--e-5) var(--e-6); background: var(--tinta); color: var(--texto-inverso); }
.resumen-numero { font-family: var(--fuente-titulo); font-size: var(--t-3xl); font-weight: 600; line-height: 1; font-variant-numeric: tabular-nums; }
.resumen-etiqueta { font-size: var(--t-sm); opacity: .9; }
.resumen-total .texto-3 { color: var(--texto-inverso); opacity: .7; }
.resumen-estados { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); margin: 0; }
.resumen-estados > div { padding: var(--e-4) var(--e-5); border-left: 1px solid var(--linea); min-width: 0; }
.resumen-estados dt { display: flex; align-items: center; gap: 6px; font-size: var(--t-xs); color: var(--texto-2); font-weight: 600; }
.resumen-estados dd { margin: 4px 0 0; font-size: var(--t-xl); font-weight: 700; color: var(--tinta); font-variant-numeric: tabular-nums; }
.resumen-estados dd small { display: block; font-size: var(--t-xs); font-weight: 400; }
.marca { width: 8px; height: 8px; border-radius: 2px; flex: none; }
.icono { width: 14px; height: 14px; }
.vencidos-indicador.alerta { background: var(--peligro-suave); }
.vencidos-indicador.alerta dt, .vencidos-indicador.alerta dd { color: var(--peligro); }
.sin-plazo { color: var(--texto-3) !important; }
.proporcion { grid-column: 1 / -1; display: flex; height: 6px; background: var(--superficie-2); }
.proporcion span { height: 100%; }

.tabla-separada { margin-top: var(--e-5); border: 1px solid var(--linea); border-radius: var(--radio-control); }
.nombre-fila { font-weight: 600; color: var(--texto); background: none; white-space: nowrap; }
.tabla tbody th { padding: 12px var(--e-4); border-bottom: 1px solid var(--linea); text-align: left; }
.tabla tbody tr:last-child th { border-bottom: none; }
.avance { display: inline-flex; align-items: center; gap: var(--e-2); white-space: nowrap; }
.avance-pista { width: 56px; height: 6px; background: var(--superficie-2); border-radius: 2px; overflow: hidden; }
.avance-pista span { display: block; height: 100%; background: var(--concluido); }
.tarde { color: var(--peligro); font-weight: 650; }
.nota { margin-top: var(--e-3); }

.vencidos { list-style: none; margin: 0; padding: 0; }
.vencidos li { display: flex; align-items: center; justify-content: space-between; gap: var(--e-4); padding: var(--e-4) var(--e-6); border-bottom: 1px solid var(--linea); }
.vencidos li:last-child { border-bottom: none; }
.vencido-principal { display: grid; gap: 4px; min-width: 0; justify-items: start; }
.vencido-asunto { font-size: var(--t-sm); overflow: hidden; text-overflow: ellipsis; display: -webkit-box; -webkit-line-clamp: 2; line-clamp: 2; -webkit-box-orient: vertical; }
.vencido-dias { color: var(--peligro); white-space: nowrap; font-size: var(--t-sm); text-align: right; }
.vencido-dias strong { font-size: var(--t-xl); font-variant-numeric: tabular-nums; }

@media (max-width: 1080px) {
  .resumen { grid-template-columns: 1fr; }
  .resumen-total { flex-direction: row; align-items: baseline; flex-wrap: wrap; gap: var(--e-2) var(--e-3); padding: var(--e-4) var(--e-5); }
}
@media (max-width: 720px) {
  .resumen-estados { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .resumen-estados > div { border-left: none; border-top: 1px solid var(--linea); }
  .resumen-estados > div:nth-child(odd) { border-right: 1px solid var(--linea); }
  .vencidos-indicador { grid-column: 1 / -1; border-right: none !important; }
  .vencidos li { padding: var(--e-3) var(--e-4); align-items: flex-start; }
  .selector-anio { flex: 1; }
  .selector-anio .seleccion { flex: 1; }
}
@media print {
  .atenuado { opacity: 1; }
  .resumen-total { background: none; color: #000; border-right: 1px solid #999; }
  .resumen-total .texto-3 { color: #000; }
  .rejilla-2 { display: block; }
  .rejilla-2 > * + * { margin-top: 12pt; }
}
</style>

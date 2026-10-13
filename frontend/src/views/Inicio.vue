<script setup>
// Panel de inicio segun el rol: lo que cada persona necesita hacer hoy.
import { ref, computed } from 'vue'
import { useRouter, RouterLink } from 'vue-router'
import {
  Search, FilePlus2, UserCheck, ClipboardList, MessageSquareText, LayoutDashboard, Users, Library,
  FileUp, History, ArrowRight, CheckCircle2, FileText, RotateCw
} from '@lucide/vue'
import { api } from '@/api'
import { useSesion } from '@/stores/sesion'
import { useCarga } from '@/composables/utiles'
import { formatoFecha, formatoNumero, plural } from '@/utils/formato'
import { CATEGORIAS_PROMPT } from '@/utils/constantes'
import EstadoTramite from '@/components/ui/EstadoTramite.vue'
import EstadoVacio from '@/components/ui/EstadoVacio.vue'
import Cargando from '@/components/ui/Cargando.vue'

const sesion = useSesion()
const router = useRouter()
const { datos, cargando, error, cargar } = useCarga(() => api.tablero.inicio())

const rol = computed(() => datos.value?.rol || sesion.rol)
const esSupervisor = computed(() => ['JEFE', 'ADMIN'].includes(rol.value))

// Saludo con la hora de La Paz.
const ahora = new Date()
const horaLaPaz = Number(new Intl.DateTimeFormat('es-BO', { hour: 'numeric', hourCycle: 'h23', timeZone: 'America/La_Paz' }).format(ahora))
const saludo = horaLaPaz < 12 ? 'Buenos días' : horaLaPaz < 19 ? 'Buenas tardes' : 'Buenas noches'
const fechaHoy = new Intl.DateTimeFormat('es-BO', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric', timeZone: 'America/La_Paz' }).format(ahora)
const nombre = computed(() => sesion.usuario?.nombre_completo || '')

const texto = ref('')
function buscar() {
  const q = texto.value.trim()
  router.push({ name: 'consulta', query: q ? { q } : {} })
}

// Vencidos primero y, dentro de cada grupo, los mas antiguos arriba.
const pendientes = computed(() => [...(datos.value?.mis_pendientes || [])]
  .sort((a, b) => Number(b.vencido) - Number(a.vencido) || (b.dias_en_elaboracion ?? 0) - (a.dias_en_elaboracion ?? 0)))
const cantidadVencidos = computed(() => pendientes.value.filter((t) => t.vencido).length)

const indicadores = computed(() => {
  const t = datos.value?.totales || {}
  return [
    { etiqueta: 'Trámites en el repositorio', valor: t.total },
    { etiqueta: `Gestión ${new Date().getFullYear()}`, valor: t.gestion_actual },
    { etiqueta: 'En elaboración', valor: t.en_elaboracion, a: '/pendientes' },
    { etiqueta: 'Por asignar', valor: t.por_asignar, a: '/asignacion', destacar: t.por_asignar > 0 },
    { etiqueta: 'Concluidos este mes', valor: t.concluidos_mes },
    { etiqueta: 'Prompts por revisar', valor: t.prompts_por_revisar, a: '/prompts/gestion', destacar: t.prompts_por_revisar > 0 }
  ]
})

const atajosAdmin = [
  { a: '/admin/usuarios', etiqueta: 'Usuarios', icono: Users, texto: 'Altas, roles y activación de cuentas' },
  { a: '/admin/catalogos', etiqueta: 'Catálogos', icono: Library, texto: 'Entidades, tipos y profesionales' },
  { a: '/admin/importacion', etiqueta: 'Importar Excel', icono: FileUp, texto: 'Carga controlada del histórico' },
  { a: '/admin/auditoria', etiqueta: 'Auditoría', icono: History, texto: 'Quién hizo qué y cuándo' }
]
</script>

<template>
  <div class="pagina">
    <header class="pagina-cabecera">
      <div>
        <p class="fecha">{{ fechaHoy }}</p>
        <h1>{{ saludo }}, {{ nombre }}</h1>
      </div>
      <div class="pagina-acciones">
        <RouterLink v-if="esSupervisor" to="/tablero" class="boton"><LayoutDashboard aria-hidden="true" /> Ver tablero de avance</RouterLink>
        <RouterLink v-if="rol === 'SECRETARIA'" to="/tramites/nuevo" class="boton boton-primario"><FilePlus2 aria-hidden="true" /> Registrar trámite</RouterLink>
      </div>
    </header>

    <form v-if="sesion.puede('BUSCAR')" class="buscador" role="search" @submit.prevent="buscar">
      <label for="buscar-inicio" class="buscador-etiqueta">¿Qué necesita encontrar?</label>
      <div class="buscador-fila">
        <Search aria-hidden="true" class="buscador-icono" />
        <input id="buscar-inicio" v-model="texto" type="search" class="buscador-entrada" autocomplete="off"
          placeholder="Hoja de ruta, entidad, número de documento, abogado o asunto" />
        <button type="submit" class="boton boton-primario">Buscar</button>
      </div>
    </form>

    <Cargando v-if="cargando && !datos" texto="Cargando su resumen…" />

    <div v-else-if="error && !datos" class="mensaje mensaje-peligro" role="alert">
      <p>{{ error }}</p>
      <button type="button" class="boton boton-pequeno" @click="cargar"><RotateCw aria-hidden="true" /> Reintentar</button>
    </div>

    <template v-else-if="datos">
      <!-- Jefe y administrador: franja de indicadores -->
      <section v-if="esSupervisor" class="panel franja-panel" aria-labelledby="titulo-indicadores">
        <h2 id="titulo-indicadores" class="sr-only">Indicadores</h2>
        <dl class="franja">
          <div v-for="i in indicadores" :key="i.etiqueta" class="indicador" :class="{ destacar: i.destacar }">
            <dt>{{ i.etiqueta }}</dt>
            <dd>
              <RouterLink v-if="i.a" :to="i.a" class="indicador-valor">{{ formatoNumero(i.valor) }}<ArrowRight aria-hidden="true" /></RouterLink>
              <span v-else class="indicador-valor">{{ formatoNumero(i.valor) }}</span>
            </dd>
          </div>
        </dl>
      </section>

      <!-- Secretaria: por asignar -->
      <section v-if="rol === 'SECRETARIA'" class="panel aviso-asignar" aria-labelledby="titulo-asignar">
        <div class="aviso-asignar-texto">
          <span class="aviso-numero">{{ formatoNumero(datos.totales.por_asignar) }}</span>
          <div>
            <h2 id="titulo-asignar">{{ datos.totales.por_asignar === 1 ? 'Trámite por asignar' : 'Trámites por asignar' }}</h2>
            <p class="texto-2 texto-pequeno">{{ datos.totales.por_asignar ? 'Recibidos que todavía no tienen abogado designado.' : 'Todos los trámites recibidos tienen abogado.' }}</p>
          </div>
        </div>
        <RouterLink to="/asignacion" class="boton" :class="{ 'boton-primario': datos.totales.por_asignar }"><UserCheck aria-hidden="true" /> Asignar abogados</RouterLink>
      </section>

      <div class="inicio-rejilla">
        <div class="pila">
          <!-- Abogado: mis pendientes -->
          <section v-if="rol === 'ABOGADO'" class="panel" aria-labelledby="titulo-pendientes">
            <header class="panel-cabecera">
              <div>
                <h2 id="titulo-pendientes">Mis pendientes</h2>
                <p v-if="pendientes.length" class="texto-2 texto-pequeno">
                  {{ plural(pendientes.length, 'trámite en elaboración', 'trámites en elaboración') }}<template v-if="cantidadVencidos">, <strong class="texto-peligro">{{ plural(cantidadVencidos, 'vencido', 'vencidos') }}</strong></template>
                </p>
              </div>
              <RouterLink to="/pendientes" class="boton boton-fantasma boton-pequeno">Ver todos</RouterLink>
            </header>
            <ul v-if="pendientes.length" class="lista">
              <li v-for="t in pendientes" :key="t.id" class="lista-fila" :class="{ vencido: t.vencido }">
                <div class="lista-principal">
                  <div class="fila">
                    <RouterLink :to="`/tramites/${t.id}`" class="codigo codigo-sello">{{ t.hoja_ruta }}</RouterLink>
                    <EstadoTramite :estado="t.estado_tramite" :vencido="t.vencido" />
                  </div>
                  <RouterLink :to="`/tramites/${t.id}`" class="lista-asunto">{{ t.asunto || 'Sin asunto registrado' }}</RouterLink>
                  <p class="texto-3 texto-xs">{{ t.entidad?.nombre || 'Sin entidad' }} · {{ t.tipo_tramite?.nombre }}</p>
                </div>
                <div class="lista-lado">
                  <p class="dias" :class="{ 'texto-peligro': t.vencido }">
                    <strong>{{ formatoNumero(t.dias_en_elaboracion ?? 0) }}</strong> {{ t.dias_en_elaboracion === 1 ? 'día' : 'días' }}
                    <span class="texto-3">en elaboración</span>
                  </p>
                  <RouterLink :to="`/tramites/${t.id}/concluir`" class="boton boton-pequeno" :class="{ 'boton-primario': t.vencido }">
                    <CheckCircle2 aria-hidden="true" /> Concluir
                  </RouterLink>
                </div>
              </li>
            </ul>
            <EstadoVacio v-else :icono="CheckCircle2" titulo="No tiene trámites pendientes" texto="Cuando le asignen un trámite aparecerá aquí." />
          </section>

          <!-- Secretaria: registrados por mi -->
          <section v-if="rol === 'SECRETARIA'" class="panel" aria-labelledby="titulo-registrados">
            <header class="panel-cabecera">
              <h2 id="titulo-registrados">Registrados por mí</h2>
            </header>
            <ul v-if="datos.registrados_por_mi?.length" class="lista">
              <li v-for="t in datos.registrados_por_mi" :key="t.id" class="lista-fila">
                <div class="lista-principal">
                  <div class="fila">
                    <RouterLink :to="`/tramites/${t.id}`" class="codigo codigo-sello">{{ t.hoja_ruta }}</RouterLink>
                    <EstadoTramite :estado="t.estado_tramite" />
                  </div>
                  <RouterLink :to="`/tramites/${t.id}`" class="lista-asunto">{{ t.asunto || 'Sin asunto registrado' }}</RouterLink>
                  <p class="texto-3 texto-xs">{{ t.entidad?.nombre || 'Sin entidad' }} · {{ t.profesional?.nombre_completo || 'Sin abogado asignado' }}</p>
                </div>
                <div class="lista-lado">
                  <p class="texto-3 texto-xs">Registrado el {{ formatoFecha(t.creado_en) }}</p>
                </div>
              </li>
            </ul>
            <EstadoVacio v-else :icono="FilePlus2" titulo="Todavía no registró trámites" texto="Los trámites que registre aparecerán aquí.">
              <RouterLink to="/tramites/nuevo" class="boton boton-primario"><FilePlus2 aria-hidden="true" /> Registrar trámite</RouterLink>
            </EstadoVacio>
          </section>

          <!-- Todos: informes concluidos recientemente -->
          <section class="panel" aria-labelledby="titulo-recientes">
            <header class="panel-cabecera">
              <div>
                <h2 id="titulo-recientes">Informes concluidos recientemente</h2>
                <p class="texto-2 texto-pequeno">Los últimos trámites con informe PDF disponible.</p>
              </div>
              <RouterLink :to="{ name: 'consulta', query: { orden: 'reciente' } }" class="boton boton-fantasma boton-pequeno">Ver más</RouterLink>
            </header>
            <ul v-if="datos.recientes?.length" class="lista">
              <li v-for="t in datos.recientes" :key="t.id" class="lista-fila">
                <div class="lista-principal">
                  <div class="fila">
                    <RouterLink :to="`/tramites/${t.id}`" class="codigo codigo-sello"><FileText aria-hidden="true" class="icono-codigo" />{{ t.numero_documento || t.hoja_ruta }}</RouterLink>
                    <span v-if="t.origen_registro === 'MIGRACION'" class="insignia insignia-sin-punto" title="Registro migrado del Excel histórico">Histórico</span>
                  </div>
                  <RouterLink :to="`/tramites/${t.id}`" class="lista-asunto">{{ t.asunto || 'Sin asunto registrado' }}</RouterLink>
                  <p class="texto-3 texto-xs">{{ t.entidad?.nombre || 'Sin entidad' }} · {{ t.profesional?.nombre_completo || 'Sin abogado' }}</p>
                </div>
                <div class="lista-lado">
                  <p class="texto-3 texto-xs">{{ t.tipo_documento?.nombre }}</p>
                  <p class="texto-pequeno">{{ formatoFecha(t.fecha_salida || t.fecha_conclusion) }}</p>
                </div>
              </li>
            </ul>
            <EstadoVacio v-else :icono="FileText" titulo="Aún no hay informes concluidos" texto="Cuando un abogado concluya un trámite y suba su informe, aparecerá aquí." />
          </section>
        </div>

        <aside class="pila">
          <!-- Atajos del abogado -->
          <section v-if="rol === 'ABOGADO'" class="panel" aria-labelledby="titulo-atajos">
            <header class="panel-cabecera"><h2 id="titulo-atajos">Atajos</h2></header>
            <nav class="atajos" aria-labelledby="titulo-atajos">
              <RouterLink to="/consulta" class="atajo"><Search aria-hidden="true" /><span><strong>Búsqueda universal</strong><small>Precedentes y trámites anteriores</small></span></RouterLink>
              <RouterLink to="/prompts" class="atajo"><MessageSquareText aria-hidden="true" /><span><strong>Catálogo de prompts</strong><small>Textos aprobados para su IA</small></span></RouterLink>
              <RouterLink to="/prompts/nuevo" class="atajo"><FilePlus2 aria-hidden="true" /><span><strong>Proponer un prompt</strong><small>El jefe lo revisa antes de publicarlo</small></span></RouterLink>
            </nav>
          </section>

          <!-- Atajos del administrador -->
          <section v-if="rol === 'ADMIN'" class="panel" aria-labelledby="titulo-admin">
            <header class="panel-cabecera"><h2 id="titulo-admin">Administración</h2></header>
            <nav class="atajos" aria-labelledby="titulo-admin">
              <RouterLink v-for="a in atajosAdmin" :key="a.a" :to="a.a" class="atajo">
                <component :is="a.icono" aria-hidden="true" /><span><strong>{{ a.etiqueta }}</strong><small>{{ a.texto }}</small></span>
              </RouterLink>
            </nav>
          </section>

          <!-- Jefe: atajos de supervision -->
          <section v-if="rol === 'JEFE'" class="panel" aria-labelledby="titulo-supervision">
            <header class="panel-cabecera"><h2 id="titulo-supervision">Supervisión</h2></header>
            <nav class="atajos" aria-labelledby="titulo-supervision">
              <RouterLink to="/tablero" class="atajo"><LayoutDashboard aria-hidden="true" /><span><strong>Tablero de avance</strong><small>Avance por abogado, gestión y tipo</small></span></RouterLink>
              <RouterLink to="/pendientes" class="atajo"><ClipboardList aria-hidden="true" /><span><strong>Trámites en elaboración</strong><small>Plazos y reasignaciones</small></span></RouterLink>
              <RouterLink to="/prompts/gestion" class="atajo"><MessageSquareText aria-hidden="true" /><span><strong>Revisar prompts</strong><small>{{ plural(datos.totales.prompts_por_revisar, 'propuesta pendiente', 'propuestas pendientes') }}</small></span></RouterLink>
            </nav>
          </section>

          <!-- Prompts mas usados -->
          <section v-if="['ABOGADO', 'JEFE'].includes(rol) && sesion.puede('USAR_PROMPTS')" class="panel" aria-labelledby="titulo-prompts">
            <header class="panel-cabecera">
              <h2 id="titulo-prompts">Prompts más usados</h2>
              <RouterLink to="/prompts" class="boton boton-fantasma boton-pequeno">Catálogo</RouterLink>
            </header>
            <ol v-if="datos.prompts_mas_usados?.length" class="prompts">
              <li v-for="p in datos.prompts_mas_usados" :key="p.id">
                <RouterLink :to="p.tipo_documento ? { name: 'prompts', query: { tipo_documento_id: p.tipo_documento.id } } : { name: 'prompts' }" class="prompt-titulo">{{ p.titulo }}</RouterLink>
                <p class="texto-3 texto-xs">{{ CATEGORIAS_PROMPT[p.categoria] || p.categoria }}<template v-if="p.tipo_documento"> · {{ p.tipo_documento.nombre }}</template> · {{ plural(p.usos || 0, 'uso', 'usos') }}</p>
              </li>
            </ol>
            <EstadoVacio v-else :icono="MessageSquareText" titulo="Sin prompts vigentes" texto="Cuando el jefe apruebe prompts aparecerán aquí." />
          </section>

          <!-- Secretaria: acceso rapido -->
          <section v-if="rol === 'SECRETARIA'" class="panel" aria-labelledby="titulo-registro">
            <div class="panel-cuerpo registro-rapido">
              <h2 id="titulo-registro">Nuevo trámite</h2>
              <p class="texto-2 texto-pequeno">Hoja de ruta, entidad, tipo de trámite y asunto. El abogado se puede asignar después.</p>
              <RouterLink to="/tramites/nuevo" class="boton boton-primario boton-grande"><FilePlus2 aria-hidden="true" /> Registrar trámite</RouterLink>
            </div>
          </section>
        </aside>
      </div>
    </template>
  </div>
</template>

<style scoped>
.fecha { color: var(--texto-3); font-size: var(--t-sm); margin-bottom: var(--e-1); }
.fecha::first-letter { text-transform: uppercase; }
.texto-peligro { color: var(--peligro); }

/* Buscador grande */
.buscador { margin-bottom: var(--e-6); }
.buscador-etiqueta { display: block; font-weight: 600; font-size: var(--t-sm); margin-bottom: var(--e-2); color: var(--texto-2); }
.buscador-fila { position: relative; display: flex; gap: var(--e-2); }
.buscador-icono { position: absolute; left: 16px; top: 50%; transform: translateY(-50%); width: 20px; height: 20px; color: var(--texto-3); pointer-events: none; }
.buscador-entrada {
  flex: 1; min-width: 0; height: 52px; padding: 0 var(--e-4) 0 48px;
  border: 1px solid var(--linea-fuerte); border-radius: var(--radio-panel); background: var(--superficie);
  font-size: var(--t-lg); box-shadow: var(--sombra-panel);
}
.buscador-entrada:focus { outline: none; border-color: var(--sello); box-shadow: var(--foco); }
.buscador-fila .boton { min-height: 52px; padding: 0 var(--e-6); font-size: var(--t-md); }

/* Franja de indicadores */
.franja-panel { margin-bottom: var(--e-6); }
.franja { display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); margin: 0; }
.indicador { padding: var(--e-4) var(--e-5); border-left: 1px solid var(--linea); min-width: 0; }
.indicador:first-child { border-left: none; }
.indicador dt { font-size: var(--t-xs); color: var(--texto-2); line-height: 1.3; }
.indicador dd { margin: var(--e-1) 0 0; }
.indicador-valor { display: inline-flex; align-items: center; gap: 4px; font-family: var(--fuente-titulo); font-size: var(--t-2xl); font-weight: 600; color: var(--tinta); line-height: 1.1; font-variant-numeric: tabular-nums; }
a.indicador-valor:hover { color: var(--sello); text-decoration: none; }
a.indicador-valor svg { width: 16px; height: 16px; color: var(--texto-3); }
.indicador.destacar .indicador-valor { color: var(--elaboracion); }

/* Aviso de asignacion (secretaria) */
.aviso-asignar { display: flex; align-items: center; justify-content: space-between; gap: var(--e-4); flex-wrap: wrap; padding: var(--e-4) var(--e-6); margin-bottom: var(--e-6); border-left: 3px solid var(--elaboracion); }
.aviso-asignar-texto { display: flex; align-items: center; gap: var(--e-4); }
.aviso-asignar h2 { font-size: var(--t-lg); }
.aviso-numero { font-family: var(--fuente-titulo); font-size: var(--t-3xl); font-weight: 600; color: var(--tinta); line-height: 1; font-variant-numeric: tabular-nums; }

/* Rejilla principal */
.inicio-rejilla { display: grid; grid-template-columns: minmax(0, 2fr) minmax(0, 1fr); gap: var(--e-6); align-items: start; }
.panel-cabecera p { margin-top: 2px; }

/* Listas con divisores */
.lista { list-style: none; margin: 0; padding: 0; }
.lista-fila { display: flex; justify-content: space-between; gap: var(--e-4); padding: var(--e-4) var(--e-6); border-top: 1px solid var(--linea); }
.lista-fila:first-child { border-top: none; }
.lista-fila.vencido { background: var(--peligro-suave); box-shadow: inset 3px 0 0 var(--peligro); }
.lista-principal { min-width: 0; display: flex; flex-direction: column; gap: 6px; }
.lista-asunto { color: var(--texto); font-weight: 600; line-height: 1.4; display: -webkit-box; -webkit-line-clamp: 2; line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.lista-asunto:hover { color: var(--sello); }
.lista-lado { flex: none; display: flex; flex-direction: column; align-items: flex-end; justify-content: space-between; gap: var(--e-2); text-align: right; }
.dias { font-size: var(--t-sm); white-space: nowrap; }
.dias strong { font-size: var(--t-lg); font-variant-numeric: tabular-nums; }
.dias .texto-3 { display: block; font-size: var(--t-xs); }
.codigo-sello { text-decoration: none; }
.codigo-sello:hover { background: var(--sello-suave); text-decoration: none; }
.icono-codigo { width: 14px; height: 14px; color: var(--texto-3); }

/* Atajos */
.atajos { display: flex; flex-direction: column; padding: var(--e-2); }
.atajo { display: flex; align-items: flex-start; gap: var(--e-3); padding: var(--e-3); border-radius: var(--radio-control); color: var(--texto); text-decoration: none; }
.atajo:hover { background: var(--sello-suave); text-decoration: none; }
.atajo svg { width: 20px; height: 20px; flex: none; color: var(--sello); margin-top: 2px; }
.atajo strong { display: block; font-size: var(--t-sm); }
.atajo small { display: block; font-size: var(--t-xs); color: var(--texto-3); }

/* Prompts */
.prompts { list-style: none; margin: 0; padding: 0; counter-reset: prompt; }
.prompts li { position: relative; padding: var(--e-3) var(--e-6) var(--e-3) calc(var(--e-6) + 24px); border-top: 1px solid var(--linea); counter-increment: prompt; }
.prompts li:first-child { border-top: none; }
.prompts li::before { content: counter(prompt); position: absolute; left: var(--e-6); top: var(--e-3); font-family: var(--fuente-titulo); font-weight: 600; color: var(--texto-3); }
.prompt-titulo { font-weight: 600; font-size: var(--t-sm); }

/* Registro rapido */
.registro-rapido { display: flex; flex-direction: column; gap: var(--e-3); }
.registro-rapido h2 { font-size: var(--t-lg); }
.boton-grande { min-height: 48px; font-size: var(--t-md); }

@media (max-width: 1100px) {
  .franja { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .indicador:nth-child(3n + 1) { border-left: none; }
  .indicador:nth-child(n + 4) { border-top: 1px solid var(--linea); }
}
@media (max-width: 960px) {
  .inicio-rejilla { grid-template-columns: 1fr; }
}
@media (max-width: 720px) {
  .buscador-entrada { font-size: var(--t-md); height: 48px; }
  .buscador-fila .boton { min-height: 48px; padding: 0 var(--e-4); }
  .franja { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .indicador { padding: var(--e-3) var(--e-4); }
  .indicador:nth-child(3n + 1) { border-left: 1px solid var(--linea); }
  .indicador:nth-child(2n + 1) { border-left: none; }
  .indicador:nth-child(n + 3) { border-top: 1px solid var(--linea); }
  .indicador-valor { font-size: var(--t-xl); }
  .lista-fila { flex-direction: column; padding: var(--e-3) var(--e-4); }
  .lista-lado { flex-direction: row; align-items: center; text-align: left; }
  .dias .texto-3 { display: inline; }
  .prompts li { padding-left: calc(var(--e-4) + 24px); padding-right: var(--e-4); }
  .prompts li::before { left: var(--e-4); }
}
@media (max-width: 420px) {
  .buscador-fila { flex-direction: column; }
  .buscador-entrada { flex: none; }
  .buscador-icono { top: 24px; }
}
</style>

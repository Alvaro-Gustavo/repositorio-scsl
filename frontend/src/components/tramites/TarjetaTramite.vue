<script setup>
// Tarjeta de un tramite en resultados de busqueda y listas.
// <TarjetaTramite :tramite="t" q="texto buscado" /> ; slot "acciones" para botones extra.
// Con q y tramite.coincidencias_informe muestra dónde aparece lo buscado dentro del informe PDF;
// cada fragmento abre el visor en esa página con la palabra resaltada.
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { FileText, Link2, FileSearch, ArrowRight } from '@lucide/vue'
import EstadoTramite from '@/components/ui/EstadoTramite.vue'
import { formatoFecha, plural } from '@/utils/formato'

const props = defineProps({ tramite: { type: Object, required: true }, vencido: Boolean, q: { type: String, default: '' } })

const coincidencias = computed(() => (props.q ? props.tramite.coincidencias_informe : null))
const enlace = computed(() => `/tramites/${props.tramite.id}`)
function enlaceInforme(pagina) {
  return { path: enlace.value, query: { q: props.q, ver: 'informe', ...(pagina ? { pagina } : {}) } }
}
</script>

<template>
  <article class="tarjeta-resultado">
    <div class="encabezado">
      <RouterLink :to="`/tramites/${tramite.id}`" class="codigo codigo-sello">
        {{ tramite.numero_documento || tramite.hoja_ruta }}
      </RouterLink>
      <span class="fila">
        <EstadoTramite :estado="tramite.estado_tramite" :vencido="vencido" />
        <span v-if="tramite.origen_registro === 'MIGRACION'" class="insignia insignia-sin-punto" title="Registro migrado del Excel histórico">Histórico</span>
      </span>
    </div>
    <h3 class="asunto"><RouterLink :to="`/tramites/${tramite.id}`">{{ tramite.asunto || 'Sin asunto registrado' }}</RouterLink></h3>
    <dl class="meta">
      <div><dt>Entidad</dt><dd>{{ tramite.entidad?.nombre || '—' }}</dd></div>
      <div><dt>Hoja de ruta</dt><dd class="codigo">{{ tramite.hoja_ruta || '—' }}</dd></div>
      <div><dt>Abogado</dt><dd>{{ tramite.profesional?.nombre_completo || 'Sin asignar' }}</dd></div>
      <div><dt>{{ tramite.fecha_salida ? 'Fecha de salida' : 'Registrado' }}</dt><dd>{{ formatoFecha(tramite.fecha_salida || tramite.creado_en) }}</dd></div>
    </dl>
    <section v-if="coincidencias" class="en-informe" :aria-label="`Coincidencias en el informe de ${tramite.numero_documento || tramite.hoja_ruta}`">
      <p class="en-informe-titulo">
        <FileSearch aria-hidden="true" />
        {{ plural(coincidencias.total, 'coincidencia', 'coincidencias') }} dentro del informe
      </p>
      <ol class="fragmentos">
        <li v-for="(f, i) in coincidencias.fragmentos" :key="i">
          <RouterLink :to="enlaceInforme(f.pagina)" class="fragmento">
            <span class="fragmento-pagina">{{ f.pagina ? `Pág. ${f.pagina}` : 'Informe' }}</span>
            <span class="fragmento-texto"><template v-for="(p, j) in f.partes" :key="j"><mark v-if="p.marca">{{ p.texto }}</mark><template v-else>{{ p.texto }}</template></template></span>
          </RouterLink>
        </li>
      </ol>
      <RouterLink :to="enlaceInforme(coincidencias.fragmentos[0]?.pagina)" class="ver-en-informe">
        Ver resaltado en el informe <ArrowRight aria-hidden="true" />
      </RouterLink>
    </section>
    <footer class="pie">
      <span class="texto-3 texto-xs">{{ tramite.tipo_tramite?.nombre }}<template v-if="tramite.tipo_documento"> · {{ tramite.tipo_documento.nombre }}</template></span>
      <span class="fila">
        <span v-if="tramite.tiene_informe" class="indicador" title="Tiene informe PDF"><FileText aria-hidden="true" /> Informe</span>
        <span v-if="tramite.cantidad_precedentes" class="indicador" title="Precedentes vinculados"><Link2 aria-hidden="true" /> {{ tramite.cantidad_precedentes }}</span>
        <slot name="acciones" />
      </span>
    </footer>
  </article>
</template>

<style scoped>
.tarjeta-resultado { background: var(--superficie); border: 1px solid var(--linea); border-left: 3px solid var(--tinta); border-radius: var(--radio-panel); padding: 18px 20px; }
.encabezado { display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; }
.codigo-sello { text-decoration: none; }
.codigo-sello:hover { background: var(--sello-suave); text-decoration: none; }
.asunto { font-family: var(--fuente-titulo); font-size: 1.08rem; font-weight: 600; margin: 12px 0 10px; line-height: 1.4; max-width: 80ch; }
.asunto a { color: var(--tinta); }
.meta { display: grid; grid-template-columns: 2fr 1.3fr 1fr 0.8fr; gap: 6px 20px; margin: 0; font-size: var(--t-sm); }
.meta dt { font-size: var(--t-xs); color: var(--texto-3); }
.meta dd { margin: 0; font-weight: 600; overflow: hidden; text-overflow: ellipsis; }
.pie { display: flex; justify-content: space-between; align-items: center; gap: 12px; margin-top: 14px; padding-top: 12px; border-top: 1px dashed var(--linea); flex-wrap: wrap; }
.indicador { display: inline-flex; align-items: center; gap: 4px; font-size: var(--t-xs); color: var(--texto-2); }
.indicador svg { width: 14px; height: 14px; }
.en-informe { margin-top: 14px; padding: 12px 14px; background: var(--superficie-2); border: 1px solid var(--linea); border-radius: var(--radio-control); }
.en-informe-titulo { display: flex; align-items: center; gap: 6px; margin: 0 0 8px; font-size: var(--t-xs); font-weight: 700; color: var(--texto-2); text-transform: uppercase; letter-spacing: .03em; }
.en-informe-titulo svg { width: 15px; height: 15px; color: var(--sello); }
.fragmentos { list-style: none; margin: 0; padding: 0; display: grid; gap: 6px; }
.fragmento { display: flex; gap: 10px; align-items: baseline; padding: 6px 8px; margin: 0 -8px; border-radius: var(--radio-control); color: var(--texto); text-decoration: none; font-size: var(--t-sm); line-height: 1.5; }
.fragmento:hover { background: var(--sello-suave); text-decoration: none; }
.fragmento-pagina { flex: none; min-width: 52px; font-size: var(--t-xs); font-weight: 700; color: var(--sello); }
.fragmento-texto { overflow-wrap: anywhere; }
.fragmento mark { background: var(--resaltado); color: var(--resaltado-texto); padding: 0 2px; border-radius: 2px; font-weight: 600; }
.ver-en-informe { display: inline-flex; align-items: center; gap: 4px; margin-top: 8px; font-size: var(--t-sm); font-weight: 600; }
.ver-en-informe svg { width: 15px; height: 15px; }
@media print { .ver-en-informe { display: none; } .fragmento mark { background: none; text-decoration: underline; } }
@media (max-width: 900px) { .meta { grid-template-columns: 1fr 1fr; } }
@media (max-width: 520px) { .meta { grid-template-columns: 1fr; } }
</style>

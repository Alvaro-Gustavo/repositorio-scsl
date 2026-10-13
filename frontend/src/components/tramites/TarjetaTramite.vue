<script setup>
// Tarjeta de un tramite en resultados de busqueda y listas.
// <TarjetaTramite :tramite="t" /> ; slot "acciones" para botones extra.
import { RouterLink } from 'vue-router'
import { FileText, Link2 } from '@lucide/vue'
import EstadoTramite from '@/components/ui/EstadoTramite.vue'
import { formatoFecha } from '@/utils/formato'

defineProps({ tramite: { type: Object, required: true }, vencido: Boolean })
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
@media (max-width: 900px) { .meta { grid-template-columns: 1fr 1fr; } }
@media (max-width: 520px) { .meta { grid-template-columns: 1fr; } }
</style>

<script setup>
// Recorrido del tramite en 4 sellos: Recibido > En elaboracion > Concluido > Archivado.
// Cada sello cumplido muestra la fecha y quien lo hizo.
import { computed } from 'vue'
import { Check } from '@lucide/vue'
import { ORDEN_ESTADOS, ESTADOS_TRAMITE } from '@/utils/constantes'
import { formatoFecha } from '@/utils/formato'

const props = defineProps({ tramite: { type: Object, required: true } })

const pasos = computed(() => {
  const t = props.tramite
  const actual = ORDEN_ESTADOS.indexOf(t.estado_tramite)
  const detalle = {
    RECIBIDO: { fecha: t.creado_en, quien: t.creado_por?.nombre_completo },
    EN_ELABORACION: { fecha: t.fecha_asignacion, quien: t.profesional?.nombre_completo },
    CONCLUIDO: { fecha: t.fecha_conclusion || t.fecha_salida, quien: t.numero_documento },
    ARCHIVADO: { fecha: t.estado_tramite === 'ARCHIVADO' ? t.actualizado_en : null, quien: null }
  }
  return ORDEN_ESTADOS.map((e, i) => ({
    estado: e, etiqueta: ESTADOS_TRAMITE[e].etiqueta, hecho: i < actual, actual: i === actual,
    fecha: i <= actual ? detalle[e].fecha : null, quien: i <= actual ? detalle[e].quien : null
  }))
})
</script>

<template>
  <ol class="riel" aria-label="Recorrido del trámite">
    <li v-for="(p, i) in pasos" :key="p.estado" :class="{ hecho: p.hecho, actual: p.actual }" :aria-current="p.actual ? 'step' : undefined">
      <span class="sello" aria-hidden="true">
        <Check v-if="p.hecho" />
        <template v-else>{{ i + 1 }}</template>
      </span>
      <span class="paso-texto">
        <strong>{{ p.etiqueta }}</strong>
        <small v-if="p.fecha">{{ formatoFecha(p.fecha) }}</small>
        <small v-if="p.quien" class="quien">{{ p.quien }}</small>
      </span>
    </li>
  </ol>
</template>

<style scoped>
.riel { list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); }
li { position: relative; display: flex; flex-direction: column; gap: 8px; padding-right: 12px; color: var(--texto-3); }
li::after { content: ''; position: absolute; top: 17px; left: 40px; right: 4px; height: 2px; background: var(--linea); }
li:last-child::after { display: none; }
li.hecho::after { background: var(--tinta); }
.sello {
  width: 36px; height: 36px; border-radius: 50%; display: grid; place-items: center;
  border: 2px dashed var(--linea-fuerte); font-weight: 700; font-size: var(--t-sm); background: var(--superficie); position: relative; z-index: 1;
}
.sello svg { width: 18px; height: 18px; }
li.hecho .sello { border: 2px solid var(--tinta); background: var(--tinta); color: #fff; }
li.actual .sello { border: 2px solid var(--sello); color: var(--sello); background: var(--sello-suave); box-shadow: 0 0 0 4px rgba(31,95,168,.12); }
.paso-texto strong { display: block; font-size: var(--t-sm); color: var(--texto-2); }
li.hecho strong, li.actual strong { color: var(--tinta); }
.paso-texto small { display: block; font-size: var(--t-xs); }
.quien { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
@media (max-width: 720px) {
  .riel { grid-template-columns: 1fr; gap: 14px; }
  li { flex-direction: row; align-items: center; }
  li::after { display: none; }
}
</style>

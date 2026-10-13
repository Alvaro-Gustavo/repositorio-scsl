<script setup>
// Visor protegido del informe: muestra cada pagina como imagen con marca de agua
// (el PDF original nunca llega al navegador de quien no puede descargarlo).
// <VisorInforme v-model="abierto" :tramite="t" />
import { ref, watch, computed } from 'vue'
import { ChevronLeft, ChevronRight, ZoomIn, ZoomOut, Download, ShieldCheck } from '@lucide/vue'
import Modal from '@/components/ui/Modal.vue'
import Cargando from '@/components/ui/Cargando.vue'
import { api } from '@/api'
import { descargarInforme } from '@/composables/utiles'

const props = defineProps({ modelValue: Boolean, tramite: { type: Object, required: true } })
const emit = defineEmits(['update:modelValue'])
const abierto = computed({ get: () => props.modelValue, set: (v) => emit('update:modelValue', v) })

const paginas = ref([])
const pagina = ref(1)
const zoom = ref(1)
const cargando = ref(false)
const error = ref('')

watch(abierto, async (v) => {
  if (!v) return
  pagina.value = 1; zoom.value = 1; error.value = ''; cargando.value = true
  try {
    const r = await api.tramites.paginasInforme(props.tramite.id)
    paginas.value = r.paginas?.length ? r.paginas
      : Array.from({ length: r.paginas || props.tramite.informe?.paginas || 1 }, (_, i) => api.tramites.urlPaginaInforme(props.tramite.id, i + 1))
  } catch (e) {
    error.value = e.message
  } finally {
    cargando.value = false
  }
})
</script>

<template>
  <Modal v-model="abierto" :titulo="`Informe ${tramite.numero_documento || tramite.hoja_ruta}`" ancho="980px">
    <div class="barra-visor no-imprimir">
      <span class="fila texto-pequeno texto-2"><ShieldCheck aria-hidden="true" class="icono" /> Vista de solo lectura con marca de agua</span>
      <span class="fila">
        <button type="button" class="boton boton-pequeno" aria-label="Alejar" :disabled="zoom <= 0.6" @click="zoom = Math.round((zoom - 0.2) * 10) / 10"><ZoomOut /></button>
        <span class="texto-pequeno">{{ Math.round(zoom * 100) }} %</span>
        <button type="button" class="boton boton-pequeno" aria-label="Acercar" :disabled="zoom >= 2" @click="zoom = Math.round((zoom + 0.2) * 10) / 10"><ZoomIn /></button>
        <span class="separador-v" />
        <button type="button" class="boton boton-pequeno" aria-label="Página anterior" :disabled="pagina <= 1" @click="pagina--"><ChevronLeft /></button>
        <span class="texto-pequeno">Página {{ pagina }} de {{ paginas.length || '…' }}</span>
        <button type="button" class="boton boton-pequeno" aria-label="Página siguiente" :disabled="pagina >= paginas.length" @click="pagina++"><ChevronRight /></button>
      </span>
    </div>
    <Cargando v-if="cargando" texto="Preparando el informe…" />
    <p v-else-if="error" class="mensaje mensaje-peligro">{{ error }}</p>
    <div v-else class="hoja-contenedor" @contextmenu.prevent @dragstart.prevent>
      <img :src="paginas[pagina - 1]" :alt="`Página ${pagina} del informe`" class="hoja" :style="{ width: `${zoom * 100}%` }" draggable="false" />
    </div>
    <template #pie>
      <span class="texto-xs texto-3 nota">{{ tramite.informe?.nombre_original }}</span>
      <button v-if="tramite.permisos?.descargar" type="button" class="boton" @click="descargarInforme(tramite)"><Download /> Descargar PDF</button>
      <button type="button" class="boton boton-primario" @click="abierto = false">Cerrar</button>
    </template>
  </Modal>
</template>

<style scoped>
.barra-visor { display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; margin-bottom: 12px; }
.icono { width: 16px; height: 16px; color: var(--exito); }
.separador-v { width: 1px; height: 20px; background: var(--linea); margin: 0 4px; }
.hoja-contenedor { background: var(--superficie-2); border: 1px solid var(--linea); border-radius: var(--radio-control); padding: 16px; overflow: auto; max-height: 68vh; user-select: none; }
.hoja { margin: 0 auto; max-width: none; box-shadow: var(--sombra-panel); background: #fff; }
.nota { margin-right: auto; }
</style>

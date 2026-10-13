<script setup>
// Campo con lista de un catalogo: busca mientras se escribe, sugiere valores
// parecidos (para no crear "GOB. AUT. LA PAZ" si ya existe "Gobierno Autónomo...")
// y, si se permite, agrega el valor nuevo al catalogo.
//
// <CampoCatalogo v-model="form.entidad_id" tipo="entidades" etiqueta="Entidad" requerido permitir-agregar :error="errores.entidad_id" />
import { ref, computed, watch, onMounted, useId } from 'vue'
import { ChevronDown, Plus, X } from '@lucide/vue'
import { api } from '@/api'
import { useCatalogos } from '@/stores/catalogos'
import { useAvisos } from '@/stores/avisos'

const props = defineProps({
  modelValue: { type: [Number, String, null], default: null },
  tipo: { type: String, required: true },
  etiqueta: { type: String, required: true },
  requerido: Boolean,
  permitirAgregar: Boolean,
  placeholder: { type: String, default: 'Escriba para buscar…' },
  ayuda: { type: String, default: '' },
  error: { type: String, default: '' },
  deshabilitado: Boolean,
  filtro: { type: Function, default: null }
})
const emit = defineEmits(['update:modelValue', 'cambio'])

const catalogos = useCatalogos()
const avisos = useAvisos()
const uid = useId()
const texto = ref('')
const abierto = ref(false)
const activo = ref(-1)
const parecidos = ref([])
const agregando = ref(false)

const lista = computed(() => (catalogos.datos[props.tipo] || []).filter((v) => !props.filtro || props.filtro(v)))
const seleccionado = computed(() => lista.value.find((v) => String(v.id) === String(props.modelValue)) || null)
const norm = (t) => String(t ?? '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim()

const opciones = computed(() => {
  const q = norm(texto.value)
  if (!q || (seleccionado.value && texto.value === seleccionado.value.nombre)) return lista.value.slice(0, 50)
  const directas = lista.value.filter((v) => norm(v.nombre).includes(q))
  const extra = parecidos.value.filter((p) => !directas.some((d) => d.id === p.id)).map((p) => lista.value.find((v) => v.id === p.id)).filter(Boolean)
  return [...directas, ...extra].slice(0, 50)
})
const exacto = computed(() => lista.value.some((v) => norm(v.nombre) === norm(texto.value)))
const mostrarAgregar = computed(() => props.permitirAgregar && texto.value.trim().length >= 3 && !exacto.value)

onMounted(() => catalogos.obtener(props.tipo))
watch(seleccionado, (v) => { if (v) texto.value = v.nombre }, { immediate: true })
watch(() => props.modelValue, (v) => { if (v == null || v === '') { if (!abierto.value) texto.value = '' } })

let espera = null
function escribir() {
  abierto.value = true
  activo.value = -1
  if (seleccionado.value && texto.value !== seleccionado.value.nombre) emit('update:modelValue', null)
  clearTimeout(espera)
  const q = texto.value.trim()
  if (q.length < 3) { parecidos.value = []; return }
  espera = setTimeout(async () => {
    try { parecidos.value = await api.catalogos.sugerir(props.tipo, q) } catch { parecidos.value = [] }
  }, 250)
}
function elegir(v) {
  emit('update:modelValue', v.id)
  emit('cambio', v)
  texto.value = v.nombre
  abierto.value = false
}
function limpiar() {
  emit('update:modelValue', null)
  emit('cambio', null)
  texto.value = ''
  parecidos.value = []
}
async function agregar() {
  if (agregando.value) return
  agregando.value = true
  try {
    const nuevo = await api.catalogos.crear(props.tipo, { nombre: texto.value.trim() })
    catalogos.agregar(props.tipo, nuevo)
    elegir(nuevo)
    avisos.exito(`Se agregó "${nuevo.nombre}" al catálogo.`)
  } catch (e) {
    avisos.error(e.message)
  } finally {
    agregando.value = false
  }
}
function teclado(e) {
  const total = opciones.value.length + (mostrarAgregar.value ? 1 : 0)
  if (e.key === 'ArrowDown') { abierto.value = true; activo.value = Math.min(total - 1, activo.value + 1); e.preventDefault() }
  else if (e.key === 'ArrowUp') { activo.value = Math.max(0, activo.value - 1); e.preventDefault() }
  else if (e.key === 'Enter' && abierto.value && activo.value >= 0) {
    e.preventDefault()
    if (activo.value < opciones.value.length) elegir(opciones.value[activo.value]); else agregar()
  } else if (e.key === 'Escape') abierto.value = false
}
function salir() {
  setTimeout(() => {
    abierto.value = false
    if (!seleccionado.value && !mostrarAgregar.value) texto.value = ''
  }, 150)
}
</script>

<template>
  <div class="campo campo-catalogo">
    <label :for="uid">{{ etiqueta }}<span v-if="requerido" class="requerido" aria-hidden="true">*</span></label>
    <div class="caja" :class="{ abierto }">
      <input :id="uid" v-model="texto" class="entrada" type="text" role="combobox" autocomplete="off"
        :aria-expanded="abierto" :aria-controls="`${uid}-lista`" :aria-invalid="!!error" :aria-required="requerido"
        :aria-activedescendant="activo >= 0 ? `${uid}-op-${activo}` : undefined"
        :placeholder="placeholder" :disabled="deshabilitado"
        @input="escribir" @focus="abierto = true" @blur="salir" @keydown="teclado" />
      <button v-if="modelValue && !deshabilitado" type="button" class="icono-campo" aria-label="Quitar selección" @click="limpiar"><X /></button>
      <ChevronDown v-else class="icono-campo decorativo" aria-hidden="true" />
      <ul v-if="abierto && !deshabilitado && (opciones.length || mostrarAgregar)" :id="`${uid}-lista`" class="lista" role="listbox">
        <li v-for="(v, i) in opciones" :id="`${uid}-op-${i}`" :key="v.id" role="option" :aria-selected="String(v.id) === String(modelValue)"
          :class="{ activa: i === activo }" @mousedown.prevent="elegir(v)">
          {{ v.nombre }}
          <small v-if="parecidos.find((p) => p.id === v.id) && !norm(v.nombre).includes(norm(texto))" class="parecido">parecido</small>
        </li>
        <li v-if="mostrarAgregar" :id="`${uid}-op-${opciones.length}`" role="option" aria-selected="false" class="agregar"
          :class="{ activa: activo === opciones.length }" @mousedown.prevent="agregar">
          <Plus aria-hidden="true" /> Agregar «{{ texto.trim() }}» al catálogo
        </li>
      </ul>
    </div>
    <p v-if="error" class="error-campo" role="alert">{{ error }}</p>
    <p v-else-if="mostrarAgregar && parecidos.length && parecidos[0].parecido >= 45" class="ayuda aviso-parecido">
      ¿Quiso decir «{{ parecidos[0].nombre }}»? Revise la lista antes de agregar un valor nuevo.
    </p>
    <p v-else-if="ayuda" class="ayuda">{{ ayuda }}</p>
  </div>
</template>

<style scoped>
.caja { position: relative; }
.caja .entrada { padding-right: 38px; }
.icono-campo { position: absolute; right: 8px; top: 50%; transform: translateY(-50%); width: 24px; height: 24px; display: grid; place-items: center; border: none; background: none; color: var(--texto-3); cursor: pointer; border-radius: 4px; padding: 0; }
.icono-campo svg { width: 16px; height: 16px; }
.icono-campo.decorativo { width: 16px; height: 16px; pointer-events: none; }
.lista { position: absolute; z-index: 25; left: 0; right: 0; top: calc(100% + 4px); max-height: 280px; overflow-y: auto; margin: 0; padding: 4px; list-style: none;
  background: var(--superficie); border: 1px solid var(--linea); border-radius: var(--radio-control); box-shadow: var(--sombra-flotante); }
.lista li { padding: 8px 10px; border-radius: 4px; cursor: pointer; font-size: var(--t-sm); display: flex; align-items: center; gap: 8px; }
.lista li.activa, .lista li:hover { background: var(--sello-suave); }
.lista li[aria-selected='true'] { font-weight: 650; color: var(--tinta); }
.parecido { margin-left: auto; font-size: var(--t-xs); color: var(--aviso); }
.agregar { color: var(--sello); font-weight: 600; border-top: 1px solid var(--linea); margin-top: 4px; }
.agregar svg { width: 16px; height: 16px; }
.aviso-parecido { color: var(--aviso); }
</style>

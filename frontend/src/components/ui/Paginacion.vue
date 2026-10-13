<script setup>
// <Paginacion :pagina="r.pagina" :paginas="r.paginas" :total="r.total" @cambiar="ir" />
import { computed } from 'vue'
import { ChevronLeft, ChevronRight } from '@lucide/vue'
import { formatoNumero } from '@/utils/formato'

const props = defineProps({ pagina: { type: Number, required: true }, paginas: { type: Number, required: true }, total: { type: Number, default: null } })
const emit = defineEmits(['cambiar'])

const numeros = computed(() => {
  const n = props.paginas; const p = props.pagina
  const set = new Set([1, n, p - 1, p, p + 1].filter((x) => x >= 1 && x <= n))
  const lista = [...set].sort((a, b) => a - b)
  const conHuecos = []
  lista.forEach((x, i) => { if (i && x - lista[i - 1] > 1) conHuecos.push('…' + x); conHuecos.push(x) })
  return conHuecos
})
</script>

<template>
  <nav v-if="paginas > 1" class="paginacion" aria-label="Paginación">
    <span v-if="total !== null" class="texto-3 texto-pequeno">{{ formatoNumero(total) }} en total</span>
    <div class="fila">
      <button type="button" class="boton boton-pequeno" :disabled="pagina <= 1" aria-label="Página anterior" @click="emit('cambiar', pagina - 1)"><ChevronLeft /></button>
      <template v-for="x in numeros" :key="x">
        <span v-if="typeof x === 'string'" class="texto-3" aria-hidden="true">…</span>
        <button v-else type="button" class="boton boton-pequeno" :class="{ actual: x === pagina }" :aria-current="x === pagina ? 'page' : undefined" @click="emit('cambiar', x)">{{ x }}</button>
      </template>
      <button type="button" class="boton boton-pequeno" :disabled="pagina >= paginas" aria-label="Página siguiente" @click="emit('cambiar', pagina + 1)"><ChevronRight /></button>
    </div>
  </nav>
</template>

<style scoped>
.paginacion { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; margin-top: var(--e-6); }
.actual { background: var(--tinta); border-color: var(--tinta); color: #fff; }
.actual:hover { background: var(--tinta); }
</style>

<script setup>
import { RouterLink } from 'vue-router'
import { FileQuestion } from '@lucide/vue'
import EstadoVacio from '@/components/ui/EstadoVacio.vue'
</script>

<template>
  <div class="pagina">
    <div class="panel">
      <EstadoVacio :icono="FileQuestion" titulo="Esta página no existe"
        texto="La dirección puede estar mal escrita o el registro fue dado de baja. Use la búsqueda universal para encontrar el trámite.">
        <RouterLink to="/consulta" class="boton boton-primario">Ir a la búsqueda</RouterLink>
        <RouterLink to="/" class="boton">Ir al inicio</RouterLink>
      </EstadoVacio>
    </div>
  </div>
</template>

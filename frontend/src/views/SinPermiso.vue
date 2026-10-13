<script setup>
import { RouterLink } from 'vue-router'
import { Lock } from '@lucide/vue'
import EstadoVacio from '@/components/ui/EstadoVacio.vue'
</script>

<template>
  <div class="pagina">
    <div class="panel">
      <EstadoVacio :icono="Lock" titulo="No tiene permisos para ver esta sección"
        texto="Su rol no incluye esta opción. Si la necesita para su trabajo, solicítela al administrador del sistema.">
        <RouterLink to="/" class="boton boton-primario">Ir al inicio</RouterLink>
      </EstadoVacio>
    </div>
  </div>
</template>

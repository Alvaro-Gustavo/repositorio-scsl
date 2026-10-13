<script setup>
import { onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { useSesion } from '@/stores/sesion'
import { useAvisos } from '@/stores/avisos'
import AvisosPila from '@/components/ui/AvisosPila.vue'

const router = useRouter()
const sesion = useSesion()
const avisos = useAvisos()

// El backend avisa con 401 cuando la sesion vence: se vuelve al ingreso.
function sesionExpirada() {
  if (!sesion.autenticado) return
  sesion.limpiar()
  avisos.aviso('Su sesión expiró. Ingrese nuevamente.')
  router.push({ name: 'ingresar' })
}
onMounted(() => window.addEventListener('scsl:sesion-expirada', sesionExpirada))
onBeforeUnmount(() => window.removeEventListener('scsl:sesion-expirada', sesionExpirada))
</script>

<template>
  <RouterView />
  <AvisosPila />
</template>

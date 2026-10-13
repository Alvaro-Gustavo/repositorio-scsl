// Rutas. meta.permisos: el usuario necesita AL MENOS UNO. meta.publica: sin sesion.
import { createRouter, createWebHistory } from 'vue-router'
import { useSesion } from '@/stores/sesion'

// Cada pantalla se carga solo cuando se visita (archivos separados en la compilacion).
const vistas = import.meta.glob('../views/**/*.vue')
const vista = (nombre) => {
  const cargar = vistas[`../views/${nombre}.vue`]
  if (!cargar) throw new Error(`Falta la vista ${nombre}`)
  return cargar
}

const routes = [
  { path: '/ingresar', name: 'ingresar', component: vista('acceso/Ingreso'), meta: { publica: true, titulo: 'Ingresar' } },
  { path: '/activar', name: 'activar', component: vista('acceso/ActivarCuenta'), meta: { publica: true, titulo: 'Activar cuenta' } },
  { path: '/recuperar', name: 'recuperar', component: vista('acceso/RecuperarClave'), meta: { publica: true, titulo: 'Recuperar contraseña' } },
  {
    path: '/',
    component: () => import('../components/marco/AppMarco.vue'),
    children: [
      { path: '', name: 'inicio', component: vista('Inicio'), meta: { titulo: 'Inicio' } },
      { path: 'consulta', name: 'consulta', component: vista('consulta/Consulta'), meta: { titulo: 'Búsqueda universal', permisos: ['BUSCAR'] } },
      { path: 'tramites/nuevo', name: 'tramite-nuevo', component: vista('tramites/TramiteFormulario'), meta: { titulo: 'Registrar trámite', permisos: ['CREAR_REGISTRO'] } },
      { path: 'tramites/:id', name: 'tramite', component: vista('consulta/TramiteDetalle'), props: true, meta: { titulo: 'Trámite', permisos: ['BUSCAR'] } },
      { path: 'tramites/:id/editar', name: 'tramite-editar', component: vista('tramites/TramiteFormulario'), props: true, meta: { titulo: 'Editar trámite', permisos: ['EDITAR_PROPIOS', 'EDITAR_TODOS'] } },
      { path: 'tramites/:id/concluir', name: 'tramite-concluir', component: vista('tramites/ConcluirTramite'), props: true, meta: { titulo: 'Concluir trámite', permisos: ['SUBIR_INFORME'] } },
      { path: 'asignacion', name: 'asignacion', component: vista('tramites/Asignacion'), meta: { titulo: 'Por asignar', permisos: ['ASIGNAR_TRAMITE'] } },
      { path: 'pendientes', name: 'pendientes', component: vista('tramites/Pendientes'), meta: { titulo: 'Pendientes', permisos: ['SUBIR_INFORME', 'VER_TABLERO'] } },
      { path: 'prompts', name: 'prompts', component: vista('prompts/CatalogoPrompts'), meta: { titulo: 'Catálogo de prompts', permisos: ['USAR_PROMPTS'] } },
      { path: 'prompts/gestion', name: 'prompts-gestion', component: vista('prompts/GestionPrompts'), meta: { titulo: 'Gestión de prompts', permisos: ['PROPONER_PROMPT'] } },
      { path: 'prompts/nuevo', name: 'prompt-nuevo', component: vista('prompts/PromptFormulario'), meta: { titulo: 'Proponer prompt', permisos: ['PROPONER_PROMPT'] } },
      { path: 'prompts/:id/editar', name: 'prompt-editar', component: vista('prompts/PromptFormulario'), props: true, meta: { titulo: 'Editar prompt', permisos: ['PROPONER_PROMPT'] } },
      { path: 'tablero', name: 'tablero', component: vista('supervision/Tablero'), meta: { titulo: 'Tablero de avance', permisos: ['VER_TABLERO'] } },
      { path: 'admin/usuarios', name: 'usuarios', component: vista('admin/Usuarios'), meta: { titulo: 'Usuarios', permisos: ['GESTIONAR_USUARIOS'] } },
      { path: 'admin/catalogos', name: 'catalogos', component: vista('admin/Catalogos'), meta: { titulo: 'Catálogos', permisos: ['GESTIONAR_CATALOGOS'] } },
      { path: 'admin/importacion', name: 'importacion', component: vista('admin/Importacion'), meta: { titulo: 'Importar Excel', permisos: ['IMPORTAR_EXCEL'] } },
      { path: 'admin/auditoria', name: 'auditoria', component: vista('admin/Auditoria'), meta: { titulo: 'Auditoría', permisos: ['VER_AUDITORIA'] } },
      { path: 'admin/configuracion', name: 'configuracion', component: vista('admin/Configuracion'), meta: { titulo: 'Configuración', permisos: ['GESTIONAR_RETENCION'] } },
      { path: 'perfil', name: 'perfil', component: vista('Perfil'), meta: { titulo: 'Mi perfil' } },
      { path: 'sin-permiso', name: 'sin-permiso', component: vista('SinPermiso'), meta: { titulo: 'Sin permiso' } },
      { path: ':ruta(.*)*', name: 'no-encontrado', component: vista('NoEncontrado'), meta: { titulo: 'Página no encontrada' } }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: (to, from, guardada) => guardada || (to.path !== from.path ? { top: 0 } : undefined)
})

router.beforeEach(async (to) => {
  const sesion = useSesion()
  await sesion.restaurar()
  if (to.meta.publica) return sesion.autenticado && to.name === 'ingresar' ? { name: 'inicio' } : true
  if (!sesion.autenticado) return { name: 'ingresar', query: to.fullPath !== '/' ? { volver: to.fullPath } : {} }
  // Quien debe cambiar su contrasena (cuenta nueva o clave temporal) no puede seguir hasta hacerlo.
  if (sesion.usuario?.debe_cambiar_contrasena && to.name !== 'perfil') return { name: 'perfil', query: { cambiar: 1 } }
  if (to.meta.permisos && !sesion.puede(...to.meta.permisos)) return { name: 'sin-permiso' }
  return true
})

router.afterEach((to) => {
  document.title = `${to.meta.titulo ? to.meta.titulo + ' | ' : ''}Repositorio SCSL`
})

export default router

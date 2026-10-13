// Menu lateral. Cada opcion aparece solo si el usuario tiene alguno de sus permisos.
import {
  Home, Search, FilePlus2, UserCheck, ClipboardList, MessageSquareText, LayoutDashboard,
  Users, Library, History, FileUp, Settings
} from '@lucide/vue'

export const NAVEGACION = [
  {
    grupo: 'Trabajo',
    opciones: [
      { a: '/', etiqueta: 'Inicio', icono: Home },
      { a: '/consulta', etiqueta: 'Búsqueda universal', icono: Search, permisos: ['BUSCAR'] },
      { a: '/tramites/nuevo', etiqueta: 'Registrar trámite', icono: FilePlus2, permisos: ['CREAR_REGISTRO'] },
      { a: '/asignacion', etiqueta: 'Por asignar', icono: UserCheck, permisos: ['ASIGNAR_TRAMITE'] },
      { a: '/pendientes', etiqueta: 'Mis pendientes', icono: ClipboardList, permisos: ['SUBIR_INFORME'], roles: ['ABOGADO'] },
      { a: '/prompts', etiqueta: 'Catálogo de prompts', icono: MessageSquareText, permisos: ['USAR_PROMPTS'] }
    ]
  },
  {
    grupo: 'Supervisión',
    opciones: [
      { a: '/tablero', etiqueta: 'Tablero de avance', icono: LayoutDashboard, permisos: ['VER_TABLERO'] },
      { a: '/pendientes', etiqueta: 'Trámites en elaboración', icono: ClipboardList, permisos: ['VER_TABLERO'] }
    ]
  },
  {
    grupo: 'Administración',
    opciones: [
      { a: '/admin/usuarios', etiqueta: 'Usuarios', icono: Users, permisos: ['GESTIONAR_USUARIOS'] },
      { a: '/admin/catalogos', etiqueta: 'Catálogos', icono: Library, permisos: ['GESTIONAR_CATALOGOS'] },
      { a: '/admin/importacion', etiqueta: 'Importar Excel', icono: FileUp, permisos: ['IMPORTAR_EXCEL'] },
      { a: '/admin/auditoria', etiqueta: 'Auditoría', icono: History, permisos: ['VER_AUDITORIA'] },
      { a: '/admin/configuracion', etiqueta: 'Configuración', icono: Settings, permisos: ['GESTIONAR_RETENCION'] }
    ]
  }
]

export function menuPara(sesion) {
  return NAVEGACION.map((g) => ({
    ...g,
    opciones: g.opciones.filter((o) => (!o.permisos || sesion.puede(...o.permisos)) && (!o.roles || o.roles.includes(sesion.rol)))
  })).filter((g) => g.opciones.length)
}

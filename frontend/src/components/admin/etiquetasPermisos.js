// Nombres legibles de los permisos del sistema, agrupados para la matriz de roles.
// Si el backend agrega un permiso nuevo y no está aquí, se muestra su código tal cual.

export const GRUPOS_PERMISOS = [
  {
    titulo: 'Consulta',
    permisos: {
      BUSCAR: 'Buscar trámites',
      VER_INFORME: 'Ver informes en el visor protegido',
      IMPRIMIR_REPORTES: 'Imprimir consultas y reportes',
      DESCARGAR_INFORME: 'Descargar el PDF original del informe',
      VER_TABLERO: 'Ver el tablero de supervisión'
    }
  },
  {
    titulo: 'Trámites',
    permisos: {
      CREAR_REGISTRO: 'Registrar trámites',
      ASIGNAR_TRAMITE: 'Asignar trámites a un abogado',
      EDITAR_PROPIOS: 'Editar sus propios trámites',
      EDITAR_TODOS: 'Editar cualquier trámite',
      SUBIR_INFORME: 'Concluir trámites y subir el informe',
      ARCHIVAR_TRAMITE: 'Archivar trámites',
      GESTIONAR_PRECEDENTES: 'Registrar precedentes',
      ELIMINAR_LOGICO: 'Dar de baja trámites',
      ELIMINAR_FISICO: 'Eliminar definitivamente'
    }
  },
  {
    titulo: 'Prompts',
    permisos: {
      USAR_PROMPTS: 'Usar prompts aprobados',
      PROPONER_PROMPT: 'Proponer prompts',
      GESTIONAR_PROMPTS: 'Aprobar, devolver y retirar prompts'
    }
  },
  {
    titulo: 'Administración',
    permisos: {
      GESTIONAR_USUARIOS: 'Administrar usuarios',
      GESTIONAR_CATALOGOS: 'Administrar catálogos y sitios legales',
      IMPORTAR_EXCEL: 'Importar el Excel histórico',
      VER_AUDITORIA: 'Ver la auditoría',
      GESTIONAR_RETENCION: 'Cambiar la configuración del sistema'
    }
  }
]

export const ETIQUETAS_PERMISOS = Object.assign({}, ...GRUPOS_PERMISOS.map((g) => g.permisos))

export const etiquetaPermiso = (codigo) => ETIQUETAS_PERMISOS[codigo] || codigo

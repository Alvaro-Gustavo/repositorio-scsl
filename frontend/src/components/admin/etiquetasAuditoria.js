// Textos legibles para la bitácora de auditoría.

export const ETIQUETAS_ACCIONES = {
  INICIO_SESION: 'Inicio de sesión',
  INICIO_SESION_FALLIDO: 'Intento de ingreso fallido',
  CIERRE_SESION: 'Cierre de sesión',
  RECUPERAR_CONTRASENA: 'Recuperación de contraseña',
  CREAR_TRAMITE: 'Registro de trámite',
  EDITAR_TRAMITE: 'Edición de trámite',
  ASIGNAR_TRAMITE: 'Asignación de trámite',
  SUBIR_INFORME: 'Informe subido',
  ARCHIVAR_TRAMITE: 'Trámite archivado',
  BAJA_TRAMITE: 'Baja de trámite',
  VER_INFORME: 'Consulta de informe',
  DESCARGAR_INFORME: 'Descarga de informe',
  BUSCAR: 'Búsqueda',
  IMPRIMIR_CONSULTA: 'Impresión',
  CREAR_PRECEDENTE: 'Registro de precedente',
  COPIAR_PROMPT: 'Copia de prompt',
  PROPONER_PROMPT: 'Propuesta de prompt',
  APROBAR_PROMPT: 'Aprobación de prompt',
  RETIRAR_PROMPT: 'Retiro de prompt',
  ABRIR_FUENTE_EXTERNA: 'Apertura de sitio legal externo',
  ABRIR_ASISTENTE_IA: 'Apertura de asistente de IA externo',
  CREAR_USUARIO: 'Alta de usuario',
  EDITAR_USUARIO: 'Edición de usuario',
  IMPORTAR_EXCEL: 'Importación de Excel',
  EDITAR_CONFIGURACION: 'Cambio de configuración',
  EDITAR_CATALOGO: 'Cambio en catálogo'
}

export const ETIQUETAS_MODULOS = {
  ACCESO: 'Acceso',
  CONSULTA: 'Consulta',
  TRAMITES: 'Trámites',
  PROMPTS: 'Prompts',
  USUARIOS: 'Usuarios',
  CATALOGOS: 'Catálogos',
  IMPORTACION: 'Importación',
  CONFIGURACION: 'Configuración',
  AUDITORIA: 'Auditoría'
}

export const RESULTADOS_AUDITORIA = {
  EXITOSO: { etiqueta: 'Exitoso', clase: 'insignia-exito' },
  FALLIDO: { etiqueta: 'Fallido', clase: 'insignia-peligro' },
  BLOQUEADO: { etiqueta: 'Bloqueado', clase: 'insignia-aviso' }
}

export const etiquetaAccion = (c) => ETIQUETAS_ACCIONES[c] || c
export const etiquetaModulo = (c) => ETIQUETAS_MODULOS[c] || c

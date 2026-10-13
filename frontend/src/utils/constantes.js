// Valores fijos del sistema. Coinciden con los CHECK de la base de datos.

export const ESTADOS_TRAMITE = {
  RECIBIDO: { etiqueta: 'Recibido', clase: 'recibido', descripcion: 'Registrado, sin abogado asignado' },
  EN_ELABORACION: { etiqueta: 'En elaboración', clase: 'elaboracion', descripcion: 'El abogado elabora el informe' },
  CONCLUIDO: { etiqueta: 'Concluido', clase: 'concluido', descripcion: 'Informe subido' },
  ARCHIVADO: { etiqueta: 'Archivado', clase: 'archivado', descripcion: 'Cierre definitivo' }
}
export const ORDEN_ESTADOS = ['RECIBIDO', 'EN_ELABORACION', 'CONCLUIDO', 'ARCHIVADO']

export const ROLES = {
  ADMIN: 'Administrador',
  JEFE: 'Jefe',
  ABOGADO: 'Abogado',
  SECRETARIA: 'Secretaria'
}

export const CATEGORIAS_PROMPT = {
  CONSULTA: 'Consulta legal',
  PRECEDENTE: 'Generar precedente',
  JUICIO_VALOR: 'Juicio de valor',
  REDACCION: 'Redacción',
  REVISION: 'Revisión'
}

export const ESTADOS_PROMPT = {
  BORRADOR: { etiqueta: 'Borrador', clase: 'insignia-aviso' },
  VIGENTE: { etiqueta: 'Vigente', clase: 'insignia-exito' },
  RETIRADO: { etiqueta: 'Retirado', clase: '' }
}

export const RELEVANCIAS = {
  VINCULANTE: 'Vinculante',
  ORIENTADOR: 'Orientador',
  REFERENCIAL: 'Referencial'
}

export const TIPOS_RELACION = {
  APLICA: 'Aplica',
  COMPLEMENTA: 'Complementa',
  MODIFICA: 'Modifica',
  REVOCA: 'Revoca'
}

// Catalogos que administra el ADMIN (clave = nombre de la tabla).
export const CATALOGOS = {
  entidades: { titulo: 'Entidades', singular: 'entidad' },
  tipos_tramite: { titulo: 'Tipos de trámite', singular: 'tipo de trámite' },
  tipos_documento: { titulo: 'Tipos de documento', singular: 'tipo de documento' },
  areas: { titulo: 'Áreas o unidades', singular: 'área' },
  procedencias: { titulo: 'Procedencias', singular: 'procedencia' },
  profesionales: { titulo: 'Profesionales', singular: 'profesional' }
}

export const ACCIONES_AUDITORIA = [
  'INICIO_SESION', 'INICIO_SESION_FALLIDO', 'CIERRE_SESION', 'CREAR_TRAMITE', 'EDITAR_TRAMITE',
  'ASIGNAR_TRAMITE', 'SUBIR_INFORME', 'ARCHIVAR_TRAMITE', 'BAJA_TRAMITE', 'VER_INFORME', 'DESCARGAR_INFORME',
  'BUSCAR', 'IMPRIMIR_CONSULTA', 'CREAR_PRECEDENTE', 'COPIAR_PROMPT', 'PROPONER_PROMPT', 'APROBAR_PROMPT',
  'RETIRAR_PROMPT', 'ABRIR_FUENTE_EXTERNA', 'ABRIR_ASISTENTE_IA', 'CREAR_USUARIO', 'EDITAR_USUARIO', 'IMPORTAR_EXCEL',
  'EDITAR_CONFIGURACION', 'EDITAR_CATALOGO', 'RECUPERAR_CONTRASENA'
]

// Asistentes de IA externos (acceso rapido). El sistema no se conecta a ellos:
// solo abre su pagina en otra pestana. Para agregar uno, sume una fila aqui.
export const ASISTENTES_IA = [
  { id: 'chatgpt', nombre: 'ChatGPT', empresa: 'OpenAI', url: 'https://chatgpt.com/', sigla: 'C', color: 'var(--ia-chatgpt)' },
  { id: 'gemini', nombre: 'Gemini', empresa: 'Google', url: 'https://gemini.google.com/app', sigla: 'G', color: 'var(--ia-gemini)' }
]

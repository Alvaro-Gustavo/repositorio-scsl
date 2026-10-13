// ============================================================
// Datos de DEMOSTRACION para el modo simulado.
// No son datos reales de la Subcontraloria: sirven para ver y probar
// la interfaz sin backend. Se generan siempre iguales (semilla fija).
// ============================================================

const PERMISOS_POR_ROL = {
  ADMIN: ['BUSCAR', 'VER_INFORME', 'IMPRIMIR_REPORTES', 'USAR_PROMPTS', 'CREAR_REGISTRO', 'ASIGNAR_TRAMITE',
    'EDITAR_PROPIOS', 'EDITAR_TODOS', 'ARCHIVAR_TRAMITE', 'SUBIR_INFORME', 'DESCARGAR_INFORME', 'GESTIONAR_PRECEDENTES',
    'PROPONER_PROMPT', 'GESTIONAR_PROMPTS', 'VER_TABLERO', 'GESTIONAR_CATALOGOS', 'IMPORTAR_EXCEL', 'VER_AUDITORIA',
    'GESTIONAR_USUARIOS', 'GESTIONAR_RETENCION', 'ELIMINAR_LOGICO', 'ELIMINAR_FISICO'],
  JEFE: ['BUSCAR', 'VER_INFORME', 'IMPRIMIR_REPORTES', 'USAR_PROMPTS', 'CREAR_REGISTRO', 'ASIGNAR_TRAMITE',
    'EDITAR_TODOS', 'ARCHIVAR_TRAMITE', 'DESCARGAR_INFORME', 'GESTIONAR_PRECEDENTES', 'PROPONER_PROMPT',
    'GESTIONAR_PROMPTS', 'VER_TABLERO'],
  ABOGADO: ['BUSCAR', 'VER_INFORME', 'IMPRIMIR_REPORTES', 'USAR_PROMPTS', 'EDITAR_PROPIOS', 'SUBIR_INFORME',
    'GESTIONAR_PRECEDENTES', 'PROPONER_PROMPT'],
  SECRETARIA: ['BUSCAR', 'VER_INFORME', 'IMPRIMIR_REPORTES', 'USAR_PROMPTS', 'CREAR_REGISTRO', 'ASIGNAR_TRAMITE',
    'EDITAR_PROPIOS']
}

export const ROLES_DEMO = [
  { nombre: 'ADMIN', descripcion: 'Opera el sistema: usuarios, catálogos, importación del Excel, auditoría y configuración. Tiene todos los permisos.' },
  { nombre: 'JEFE', descripcion: 'Supervisa: tablero, reasigna, archiva, edita cualquier trámite, aprueba prompts y descarga informes.' },
  { nombre: 'ABOGADO', descripcion: 'Concluye sus trámites asignados, sube el informe, registra precedentes y propone prompts.' },
  { nombre: 'SECRETARIA', descripcion: 'Registra los trámites y los asigna a un abogado.' }
].map((r) => ({ ...r, permisos: PERMISOS_POR_ROL[r.nombre] }))

export const permisosDeRol = (rol) => PERMISOS_POR_ROL[rol] || []

export const CLAVE_DEMO = 'Demo#2026'

// Generador pseudoaleatorio con semilla fija: los datos salen siempre iguales.
function generador(semilla) {
  let s = semilla >>> 0
  return () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296 }
}

const ENTIDADES = [
  'Gobierno Autónomo Departamental de La Paz', 'Gobierno Autónomo Municipal de El Alto',
  'Gobierno Autónomo Municipal de La Paz', 'Ministerio de Obras Públicas, Servicios y Vivienda',
  'Ministerio de Salud y Deportes', 'Universidad Mayor de San Andrés', 'Servicio de Impuestos Nacionales',
  'Administradora Boliviana de Carreteras', 'Empresa Pública Nacional Estratégica Boliviana de Aviación',
  'Gobierno Autónomo Departamental de Cochabamba', 'Caja Nacional de Salud', 'Secretaría General de la CGE'
]
const TIPOS_TRAMITE = ['Verificación de contratos', 'Proceso de contratación', 'Responsabilidad por la función pública',
  'Consulta legal', 'Recurso de revocatoria', 'Convenio interinstitucional', 'Denuncia']
const TIPOS_DOCUMENTO = ['Informe legal', 'Nota', 'Resolución', 'Dictamen', 'Memorándum']
const AREAS = ['Secretaría General', 'Gerencia de Servicios Legales', 'Unidad de Auditoría Interna', 'Gerencia Departamental La Paz']
const ASUNTOS = {
  'Verificación de contratos': ['Verificación del contrato de obra {n} con ampliación de plazo', 'Verificación de legalidad del contrato de consultoría {n}', 'Revisión de cláusulas de multa en contrato de suministro {n}'],
  'Proceso de contratación': ['Proceso de contratación directa de bienes para {e}', 'Observaciones al proceso de licitación pública {n}', 'Proceso de contratación por excepción de servicios de mantenimiento'],
  'Responsabilidad por la función pública': ['Indicios de responsabilidad civil en la ejecución del proyecto {n}', 'Análisis de responsabilidad administrativa por pagos sin respaldo', 'Informe de responsabilidad por la función pública en adquisición de equipos'],
  'Consulta legal': ['Consulta sobre aplicación de la Ley 1178 en desembolsos', 'Consulta sobre prescripción de acciones de responsabilidad', 'Consulta sobre el alcance del control gubernamental posterior'],
  'Recurso de revocatoria': ['Recurso de revocatoria contra resolución de inhabilitación {n}', 'Recurso de revocatoria interpuesto por contratista sancionado'],
  'Convenio interinstitucional': ['Revisión de convenio interinstitucional de cooperación técnica', 'Adenda al convenio de financiamiento {n}'],
  'Denuncia': ['Denuncia por presuntas irregularidades en la ejecución de obra', 'Denuncia ciudadana sobre pagos en exceso a proveedor']
}
const CONCLUSIONES = [
  'Se concluye que procede la ampliación de plazo por causas ajenas al contratista, conforme al Decreto Supremo 0181.',
  'Se recomienda archivar el trámite al no evidenciarse indicios de responsabilidad por la función pública.',
  'Se observa la falta de garantía de cumplimiento de contrato y se recomienda su regularización.',
  'Se establece que el proceso de contratación se ajustó a las Normas Básicas del Sistema de Administración de Bienes y Servicios.',
  'Se identifican indicios de responsabilidad civil por pagos sin respaldo documental.',
  'Se recomienda confirmar la resolución impugnada por estar debidamente fundamentada.'
]

export function crearSemilla() {
  const azar = generador(20261012)
  const elegir = (lista) => lista[Math.floor(azar() * lista.length)]
  const ahora = Date.now()
  const haceDias = (d) => new Date(ahora - d * 86400000).toISOString()
  let idCat = 1
  const cat = (nombres) => nombres.map((nombre) => ({ id: idCat++, nombre, activo: true }))

  const usuarios = [
    { id: 1, nombre_completo: 'Administrador del sistema', correo: 'admin@contraloria.gob.bo', cargo: 'Responsable de sistemas', rol: 'ADMIN' },
    { id: 2, nombre_completo: 'Dr. Marcelo Rodríguez', correo: 'jefe@contraloria.gob.bo', cargo: 'Jefe de la Subcontraloría de Servicios Legales', rol: 'JEFE' },
    { id: 3, nombre_completo: 'Dra. Patricia Zenteno', correo: 'zenteno@contraloria.gob.bo', cargo: 'Abogada', rol: 'ABOGADO' },
    { id: 4, nombre_completo: 'Dra. Carla Ampuero', correo: 'ampuero@contraloria.gob.bo', cargo: 'Abogada', rol: 'ABOGADO' },
    { id: 5, nombre_completo: 'Dr. Javier Quispe', correo: 'quispe@contraloria.gob.bo', cargo: 'Abogado', rol: 'ABOGADO' },
    { id: 6, nombre_completo: 'Lic. Rocío Flores', correo: 'secretaria@contraloria.gob.bo', cargo: 'Secretaria', rol: 'SECRETARIA' }
  ].map((u, i) => ({
    ...u, clave: 'Demo#2026', activo: true, correo_verificado: true, debe_cambiar_contrasena: false,
    totp_activo: false, ultimo_acceso: haceDias(i), creado_en: haceDias(400)
  }))

  const catalogos = {
    procedencias: cat(['INTERNA', 'EXTERNA']),
    entidades: cat(ENTIDADES),
    tipos_tramite: cat(TIPOS_TRAMITE),
    tipos_documento: cat(TIPOS_DOCUMENTO),
    areas: cat(AREAS),
    profesionales: [
      { id: idCat++, nombre: 'DRA. ZENTENO', usuario_id: 3, activo: true },
      { id: idCat++, nombre: 'DRA. AMPUERO', usuario_id: 4, activo: true },
      { id: idCat++, nombre: 'DR. QUISPE', usuario_id: 5, activo: true },
      { id: idCat++, nombre: 'DRA. MAMANI', usuario_id: null, activo: true }
    ]
  }
  const abogadosConCuenta = catalogos.profesionales.filter((p) => p.usuario_id)

  const tramites = []
  for (let i = 0; i < 56; i++) {
    const anio = i < 10 ? 2024 : i < 26 ? 2025 : 2026
    const tipo = elegir(catalogos.tipos_tramite)
    const entidad = elegir(catalogos.entidades)
    const n = 100 + i * 7
    const asunto = elegir(ASUNTOS[tipo.nombre]).replace('{n}', `N.º ${n}/${anio}`).replace('{e}', entidad.nombre)
    const diasRegistro = anio === 2026 ? Math.floor(azar() * 250) + 5 : (2026 - anio) * 365 + Math.floor(azar() * 200)
    const migrado = anio < 2026
    let estado = 'CONCLUIDO'
    if (!migrado) {
      const r = azar()
      estado = r < 0.18 ? 'RECIBIDO' : r < 0.5 ? 'EN_ELABORACION' : r < 0.9 ? 'CONCLUIDO' : 'ARCHIVADO'
    } else if (azar() < 0.3) estado = 'ARCHIVADO'
    const profesional = estado === 'RECIBIDO' ? null : (migrado ? elegir(catalogos.profesionales) : elegir(abogadosConCuenta))
    const concluido = estado === 'CONCLUIDO' || estado === 'ARCHIVADO'
    const diasAsignado = Math.max(1, diasRegistro - Math.floor(azar() * 3))
    const diasElab = Math.floor(azar() * 25) + 3
    const tipoDoc = concluido ? (i % 5 === 0 ? catalogos.tipos_documento[1] : elegir(catalogos.tipos_documento.slice(0, 4))) : null
    tramites.push({
      id: `t-${String(i + 1).padStart(4, '0')}`,
      hoja_ruta: `CGE/GSL/INF-${String(n).padStart(3, '0')}/${anio}`,
      registro_interno: `GAAJ/${1400 + i * 3}`,
      anio_gestion: anio,
      procedencia_id: catalogos.procedencias[entidad.nombre.includes('CGE') ? 0 : 1].id,
      entidad_id: entidad.id,
      tipo_tramite_id: tipo.id,
      asunto,
      profesional_id: profesional?.id ?? null,
      tipo_documento_id: tipoDoc?.id ?? null,
      numero_documento: concluido ? `CGE/SCSL/GAAJ/C-${String(n + 50).padStart(3, '0')}/${anio}` : null,
      fecha_salida: concluido ? haceDias(Math.max(0, diasAsignado - diasElab)).slice(0, 10) : null,
      area_id: azar() < 0.4 ? elegir(catalogos.areas).id : null,
      observaciones: azar() < 0.25 ? 'Se remitió copia a la unidad solicitante.' : null,
      estado_tramite: estado,
      asignado_por: profesional && !migrado ? 6 : null,
      fecha_asignacion: profesional && !migrado ? haceDias(diasAsignado) : null,
      fecha_conclusion: concluido && !migrado ? haceDias(Math.max(0, diasAsignado - diasElab)) : null,
      activo: true, baja_motivo: null,
      origen_registro: migrado ? 'MIGRACION' : 'SISTEMA',
      creado_por: migrado ? 1 : 6,
      creado_en: haceDias(diasRegistro),
      actualizado_en: haceDias(Math.max(0, diasAsignado - diasElab)),
      informe: concluido ? {
        id: `inf-${i + 1}`, nombre_original: `informe-${n}-${anio}.pdf`, paginas: 2 + (i % 4),
        tamano_bytes: 180000 + i * 3100, subido_por: profesional?.usuario_id || 1,
        subido_en: haceDias(Math.max(0, diasAsignado - diasElab)), versiones: 1,
        texto: `${asunto}. ANTECEDENTES: la entidad remitió la documentación para análisis legal. ANÁLISIS: se revisó la normativa aplicable, Ley 1178 de Administración y Control Gubernamentales. CONCLUSIÓN: ${elegir(CONCLUSIONES)}`
      } : null
    })
  }

  // Precedentes entre tramites del mismo tipo
  const precedentes = []
  let idPre = 1
  const concluidos = tramites.filter((t) => t.informe)
  for (let i = 8; i < concluidos.length; i += 3) {
    const actual = concluidos[i]
    const previo = concluidos.slice(0, i).reverse().find((t) => t.tipo_tramite_id === actual.tipo_tramite_id)
    if (!previo) continue
    precedentes.push({
      id: `p-${idPre++}`, tramite_id: actual.id, tramite_precedente_id: previo.id,
      criterio_legal: elegir(CONCLUSIONES), relevancia: elegir(['VINCULANTE', 'ORIENTADOR', 'REFERENCIAL']),
      tipo_relacion: elegir(['APLICA', 'APLICA', 'COMPLEMENTA', 'MODIFICA']), origen: 'MANUAL', observaciones: null,
      creado_por: catalogos.profesionales.find((p) => p.id === actual.profesional_id)?.usuario_id || 2,
      creado_en: actual.actualizado_en
    })
  }

  const idDoc = (nombre) => catalogos.tipos_documento.find((t) => t.nombre === nombre).id
  const prompts = [
    { titulo: 'Extraer el criterio legal de un informe', categoria: 'PRECEDENTE', tipo_documento_id: idDoc('Informe legal'),
      texto: 'Actúa como abogado de la Contraloría General del Estado de Bolivia. A partir del informe legal que pegaré a continuación, redacta en un máximo de cinco líneas el criterio legal aplicado, citando la norma en la que se basa. No agregues hechos que no estén en el texto.\n\n[PEGUE AQUÍ EL TEXTO DEL INFORME]',
      instrucciones: 'Pegue el texto del informe sin datos personales. Revise que la norma citada exista y esté vigente antes de registrar el precedente.' },
    { titulo: 'Estructura de un informe legal', categoria: 'REDACCION', tipo_documento_id: idDoc('Informe legal'),
      texto: 'Redacta la estructura de un informe legal de la Subcontraloría de Servicios Legales con las secciones: antecedentes, normativa aplicable, análisis, conclusión y recomendación. El tema es:\n\n[DESCRIBA EL ASUNTO]\n\nUsa un lenguaje formal y frases breves.',
      instrucciones: 'Sirve como punto de partida; el contenido lo define el abogado.' },
    { titulo: 'Comparar con precedentes', categoria: 'JUICIO_VALOR', tipo_documento_id: null,
      texto: 'Compara el criterio del caso actual con los precedentes que te daré. Indica en qué coinciden, en qué difieren y si el precedente es aplicable. Caso actual:\n[RESUMEN DEL CASO]\n\nPrecedentes:\n[CRITERIOS DE LOS PRECEDENTES]',
      instrucciones: 'Copie los criterios desde la sección de precedentes del trámite.' },
    { titulo: 'Consulta sobre la Ley 1178', categoria: 'CONSULTA', tipo_documento_id: null,
      texto: 'Explica, citando artículos, qué establece la Ley 1178 de Administración y Control Gubernamentales sobre el siguiente tema:\n\n[TEMA]\n\nSi no estás seguro de un artículo, indícalo.',
      instrucciones: 'Verifique siempre las citas en la Gaceta Oficial.' },
    { titulo: 'Revisar normativa citada', categoria: 'REVISION', tipo_documento_id: idDoc('Dictamen'),
      texto: 'Revisa el siguiente texto y lista cada norma citada con su número y fecha. Señala las que podrían estar abrogadas o modificadas.\n\n[TEXTO]',
      instrucciones: 'La respuesta de la IA es una ayuda: confirme la vigencia en la Gaceta Oficial.' },
    { titulo: 'Redactar nota de respuesta', categoria: 'REDACCION', tipo_documento_id: idDoc('Nota'),
      texto: 'Redacta una nota de respuesta formal dirigida a [ENTIDAD] sobre [ASUNTO], en no más de tres párrafos, con tono institucional.',
      instrucciones: 'Complete los datos entre corchetes antes de pegar.' }
  ].map((p, i) => ({
    id: i + 1, ...p, estado: 'VIGENTE', observacion: null, usos: [34, 21, 15, 12, 6, 9][i],
    propuesto_por: i % 2 ? 3 : 2, aprobado_por: 2, aprobado_en: haceDias(60 - i), creado_en: haceDias(70 - i), actualizado_en: haceDias(60 - i)
  }))
  prompts.push({
    id: 7, titulo: 'Resumen de antecedentes', categoria: 'REDACCION', tipo_documento_id: idDoc('Informe legal'),
    texto: 'Resume en orden cronológico los antecedentes del siguiente expediente, en viñetas breves:\n\n[TEXTO DE ANTECEDENTES]',
    instrucciones: null, estado: 'BORRADOR', observacion: null, usos: 0, propuesto_por: 4, aprobado_por: null, aprobado_en: null,
    creado_en: haceDias(3), actualizado_en: haceDias(3)
  })

  const fuentes = [
    { id: 1, nombre: 'TCP - Jurisprudencia', descripcion: 'Tribunal Constitucional Plurinacional: buscador de jurisprudencia', url: 'https://jurisprudencia.tcpbolivia.bo/', url_busqueda: null, orden: 10, activo: true },
    { id: 2, nombre: 'TCP - Causas y resoluciones', descripcion: 'Tribunal Constitucional Plurinacional: causas y resoluciones', url: 'https://buscador.tcpbolivia.bo/', url_busqueda: null, orden: 20, activo: true },
    { id: 3, nombre: 'TSJ - Genesis', descripcion: 'Tribunal Supremo de Justicia: resoluciones y jurisprudencia', url: 'https://genesis.tsj.bo/', url_busqueda: null, orden: 30, activo: true },
    { id: 4, nombre: 'Gaceta Oficial de Bolivia', descripcion: 'Búsqueda de normas por número o palabra clave', url: 'http://www.gacetaoficialdebolivia.gob.bo/normas/busquedaAvanzada', url_busqueda: null, orden: 40, activo: true },
    { id: 5, nombre: 'Contraloría - Normativa', descripcion: 'Normativa y documentos de uso público de la CGE', url: 'https://www.contraloria.gob.bo/biblioteca-normativa/', url_busqueda: null, orden: 50, activo: true }
  ]

  const configuracion = [
    { clave: 'plazo_dias_tramite', valor: '20', descripcion: 'Días calendario para marcar un trámite como vencido. Vacío = sin control' },
    { clave: 'asunto_max_caracteres', valor: '500', descripcion: 'Largo máximo del asunto' },
    { clave: 'pdf_max_mb', valor: '50', descripcion: 'Tamaño máximo del informe PDF en MB' },
    { clave: 'sesion_inactividad_minutos', valor: '30', descripcion: 'Minutos sin uso antes de cerrar la sesión' },
    { clave: 'ingreso_max_intentos', valor: '5', descripcion: 'Intentos fallidos antes de bloquear la cuenta' },
    { clave: 'ingreso_bloqueo_minutos', valor: '15', descripcion: 'Minutos de bloqueo tras los intentos fallidos' },
    { clave: 'anios_retencion_auditoria', valor: '5', descripcion: 'Años que se conserva la auditoría' },
    { clave: 'respaldos_retenidos', valor: '30', descripcion: 'Cantidad de respaldos diarios que se conservan' },
    { clave: 'prompts_aviso', valor: 'Al pegar este prompt en una IA externa no incluya datos personales ni información reservada.', descripcion: 'Aviso que se muestra junto a cada prompt' }
  ]

  const auditoria = []
  let idAud = 1
  // Solo acciones que no cambian el historial de un tramite (el historial se arma con acciones reales).
  const acciones = [['INICIO_SESION', 'ACCESO'], ['BUSCAR', 'CONSULTA'], ['VER_INFORME', 'TRAMITES'],
    ['COPIAR_PROMPT', 'PROMPTS'], ['DESCARGAR_INFORME', 'TRAMITES'], ['INICIO_SESION_FALLIDO', 'ACCESO']]
  for (let i = 0; i < 90; i++) {
    const [accion, modulo] = elegir(acciones)
    const u = elegir(usuarios)
    auditoria.push({
      id: idAud++, creado_en: new Date(ahora - (90 - i) * 3.1 * 3600000).toISOString(), usuario_id: u.id, usuario_correo: u.correo,
      accion, modulo, objeto_tipo: modulo === 'TRAMITES' ? 'tramite' : modulo === 'PROMPTS' ? 'prompt' : null,
      objeto_id: modulo === 'TRAMITES' ? elegir(tramites).id : modulo === 'PROMPTS' ? String(1 + (i % 6)) : null,
      resultado: accion === 'INICIO_SESION_FALLIDO' ? 'FALLIDO' : 'EXITOSO', ip: `192.168.10.${20 + (i % 30)}`, detalle: null
    })
  }

  const importaciones = [{
    id: 1, archivo: 'Registro_SCSL_historico.xlsx', huella: 'demo', modo: 'DEFINITIVA', estado: 'COMPLETADA',
    encontrados: 26, insertados: 26, rechazados: 0, incidencias: 0, ejecutado_por: 'admin@contraloria.gob.bo', fecha: haceDias(200)
  }]

  return { version: 1, usuarios, catalogos, tramites, precedentes, prompts, fuentes, configuracion, auditoria, importaciones, secuencia: 1000 }
}

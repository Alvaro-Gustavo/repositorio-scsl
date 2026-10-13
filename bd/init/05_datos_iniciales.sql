-- ============================================================
-- REPOSITORIO SCSL - Paso 5 de 6: datos iniciales.
-- Solo lo que el sistema necesita para arrancar. Los catalogos de
-- negocio (entidades, tipos de tramite, tipos de documento, areas,
-- profesionales) NO se inventan: vienen del Excel historico.
-- ============================================================

-- Roles: cada uno con una sola responsabilidad.
INSERT INTO roles (nombre, descripcion) VALUES
    ('ADMIN',      'Opera el sistema: usuarios, catalogos, importacion del Excel, auditoria, configuracion. Tiene todos los permisos'),
    ('JEFE',       'Supervisa: tablero, reasigna, archiva, edita cualquier tramite, aprueba prompts y descarga informes'),
    ('ABOGADO',    'Concluye sus tramites asignados: datos de respuesta y subida del informe; registra precedentes y propone prompts'),
    ('SECRETARIA', 'Registra los tramites y los asigna a un abogado');

INSERT INTO permisos (codigo, descripcion) VALUES
    ('BUSCAR',                'Buscar y consultar tramites'),
    ('VER_INFORME',           'Ver informes en el visor protegido, sin descarga'),
    ('IMPRIMIR_REPORTES',     'Imprimir consultas y generar el reporte PDF de consulta'),
    ('USAR_PROMPTS',          'Ver y copiar prompts del catalogo'),
    ('CREAR_REGISTRO',        'Registrar un tramite nuevo'),
    ('ASIGNAR_TRAMITE',       'Asignar o reasignar el abogado de un tramite'),
    ('EDITAR_PROPIOS',        'Editar los tramites que registro o que tiene asignados'),
    ('EDITAR_TODOS',          'Editar cualquier tramite'),
    ('ARCHIVAR_TRAMITE',      'Archivar un tramite concluido'),
    ('SUBIR_INFORME',         'Subir el informe PDF del tramite asignado'),
    ('DESCARGAR_INFORME',     'Descargar el PDF original del informe'),
    ('GESTIONAR_PRECEDENTES', 'Registrar precedentes y criterios legales'),
    ('PROPONER_PROMPT',       'Proponer prompts para el catalogo'),
    ('GESTIONAR_PROMPTS',     'Aprobar, editar y retirar prompts'),
    ('VER_TABLERO',           'Ver el tablero de avance'),
    ('GESTIONAR_CATALOGOS',   'Administrar catalogos y fuentes externas'),
    ('IMPORTAR_EXCEL',        'Importar el Excel historico'),
    ('VER_AUDITORIA',         'Consultar la auditoria'),
    ('GESTIONAR_USUARIOS',    'Crear, editar, activar y desactivar usuarios'),
    ('GESTIONAR_RETENCION',   'Configurar respaldos y plazos de conservacion'),
    ('ELIMINAR_LOGICO',       'Dar de baja o reactivar un tramite');

-- Matriz de permisos (confirmada en el contexto del proyecto).
INSERT INTO roles_permisos (rol_id, permiso_id)
SELECT r.id, p.id
  FROM roles r
  JOIN permisos p ON
       r.nombre = 'ADMIN'
    OR (r.nombre = 'JEFE' AND p.codigo IN (
           'BUSCAR', 'VER_INFORME', 'IMPRIMIR_REPORTES', 'USAR_PROMPTS',
           'CREAR_REGISTRO', 'ASIGNAR_TRAMITE', 'EDITAR_TODOS', 'ARCHIVAR_TRAMITE',
           'DESCARGAR_INFORME', 'GESTIONAR_PRECEDENTES', 'PROPONER_PROMPT', 'GESTIONAR_PROMPTS', 'VER_TABLERO'))
    OR (r.nombre = 'ABOGADO' AND p.codigo IN (
           'BUSCAR', 'VER_INFORME', 'IMPRIMIR_REPORTES', 'USAR_PROMPTS',
           'EDITAR_PROPIOS', 'SUBIR_INFORME', 'GESTIONAR_PRECEDENTES', 'PROPONER_PROMPT'))
    OR (r.nombre = 'SECRETARIA' AND p.codigo IN (
           'BUSCAR', 'VER_INFORME', 'IMPRIMIR_REPORTES', 'USAR_PROMPTS',
           'CREAR_REGISTRO', 'ASIGNAR_TRAMITE', 'EDITAR_PROPIOS'));

-- Procedencia: valores fijos del formulario.
INSERT INTO procedencias (nombre) VALUES ('INTERNA'), ('EXTERNA');

-- Sitios legales del buscador.
INSERT INTO fuentes_externas (nombre, descripcion, url, orden) VALUES
    ('TCP - Jurisprudencia',        'Tribunal Constitucional Plurinacional: buscador de jurisprudencia',
     'https://jurisprudencia.tcpbolivia.bo/', 10),
    ('TCP - Causas y resoluciones', 'Tribunal Constitucional Plurinacional: causas y resoluciones',
     'https://buscador.tcpbolivia.bo/', 20),
    ('TSJ - Genesis',               'Tribunal Supremo de Justicia: resoluciones y jurisprudencia',
     'https://genesis.tsj.bo/', 30),
    ('Gaceta Oficial de Bolivia',   'Busqueda de normas por numero o palabra clave',
     'http://www.gacetaoficialdebolivia.gob.bo/normas/busquedaAvanzada', 40),
    ('Contraloria - Normativa',     'Normativa y documentos de uso publico de la CGE',
     'https://www.contraloria.gob.bo/biblioteca-normativa/', 50);

-- Parametros editables por el ADMIN.
INSERT INTO configuracion (clave, valor, descripcion) VALUES
    ('plazo_dias_tramite',         NULL,  'Dias calendario para marcar un tramite como vencido. Vacio = sin control'),
    ('asunto_max_caracteres',      '500', 'Largo maximo del asunto'),
    ('pdf_max_mb',                 '50',  'Tamano maximo del informe PDF en MB'),
    ('sesion_inactividad_minutos', '30',  'Minutos sin uso antes de cerrar la sesion'),
    ('ingreso_max_intentos',       '5',   'Intentos fallidos antes de bloquear la cuenta'),
    ('ingreso_bloqueo_minutos',    '15',  'Minutos de bloqueo tras los intentos fallidos'),
    ('anios_retencion_auditoria',  '5',   'Anios que se conserva la auditoria'),
    ('respaldos_retenidos',        '30',  'Cantidad de respaldos diarios que se conservan'),
    ('prompts_aviso',
     'Al pegar este prompt en una IA externa no incluya datos personales ni informacion reservada.',
     'Aviso que se muestra junto a cada prompt');

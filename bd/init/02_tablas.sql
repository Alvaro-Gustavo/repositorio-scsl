-- ============================================================
-- REPOSITORIO SCSL - Paso 2 de 6: tablas e indices.
--
-- Grupos:
--   A. Acceso: roles, permisos, usuarios, sesiones, codigos
--   B. Catalogos: procedencias, entidades, tipos de tramite,
--      tipos de documento, areas, profesionales
--   C. Tramites, informes PDF y precedentes
--   D. Catalogo de prompts
--   E. Soporte: fuentes externas, importacion del Excel,
--      incidencias, configuracion y auditoria
-- ============================================================

-- ============================================================
-- A. ACCESO
-- ============================================================
CREATE TABLE roles (
    id          SERIAL PRIMARY KEY,
    nombre      VARCHAR(30) NOT NULL UNIQUE,      -- ADMIN, JEFE, ABOGADO, SECRETARIA
    descripcion TEXT NOT NULL
);

CREATE TABLE permisos (
    id          SERIAL PRIMARY KEY,
    codigo      VARCHAR(50) NOT NULL UNIQUE,      -- ej. SUBIR_INFORME
    descripcion TEXT NOT NULL
);

CREATE TABLE roles_permisos (
    rol_id     INT NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permiso_id INT NOT NULL REFERENCES permisos(id) ON DELETE CASCADE,
    PRIMARY KEY (rol_id, permiso_id)
);

-- Cada usuario tiene UN rol.
CREATE TABLE usuarios (
    id                      SERIAL PRIMARY KEY,
    nombre_completo         VARCHAR(150) NOT NULL,
    correo                  VARCHAR(150) NOT NULL,     -- se ingresa con el correo
    cargo                   VARCHAR(120),
    rol_id                  INT NOT NULL REFERENCES roles(id),
    hash_contrasena         TEXT NOT NULL,             -- bcrypt; nunca la clave en texto
    activo                  BOOLEAN NOT NULL DEFAULT true,
    correo_verificado       BOOLEAN NOT NULL DEFAULT false,
    debe_cambiar_contrasena BOOLEAN NOT NULL DEFAULT true,
    totp_secreto            VARCHAR(64),               -- segundo factor (opcional)
    totp_activo             BOOLEAN NOT NULL DEFAULT false,
    intentos_fallidos       SMALLINT NOT NULL DEFAULT 0,
    bloqueado_hasta         TIMESTAMPTZ,
    ultimo_acceso           TIMESTAMPTZ,
    creado_en               TIMESTAMPTZ NOT NULL DEFAULT now(),
    actualizado_en          TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_usuarios_correo CHECK (correo ~* '^[^@\s]+@[^@\s]+\.[^@\s]+$'),
    CONSTRAINT ck_usuarios_totp   CHECK (NOT totp_activo OR totp_secreto IS NOT NULL)
);
CREATE UNIQUE INDEX uq_usuarios_correo ON usuarios (lower(correo));
CREATE INDEX idx_usuarios_rol ON usuarios (rol_id);

CREATE TABLE sesiones (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    usuario_id     INT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    creado_en      TIMESTAMPTZ NOT NULL DEFAULT now(),
    ultimo_uso_en  TIMESTAMPTZ NOT NULL DEFAULT now(),   -- cierre por inactividad
    expira_en      TIMESTAMPTZ NOT NULL,
    revocada_en    TIMESTAMPTZ,                          -- al salir o desactivar al usuario
    ip             VARCHAR(45),
    agente_usuario TEXT
);
CREATE INDEX idx_sesiones_vigentes ON sesiones (usuario_id, expira_en) WHERE revocada_en IS NULL;

-- Codigos de 6 digitos: activar la cuenta y recuperar la contrasena.
CREATE TABLE codigos_verificacion (
    id          BIGSERIAL PRIMARY KEY,
    usuario_id  INT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    proposito   VARCHAR(20) NOT NULL CHECK (proposito IN ('ACTIVACION', 'RECUPERACION')),
    hash_codigo TEXT NOT NULL,                          -- el codigo se guarda cifrado
    expira_en   TIMESTAMPTZ NOT NULL,
    usado_en    TIMESTAMPTZ,
    intentos    SMALLINT NOT NULL DEFAULT 0,
    creado_en   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_codigos_pendientes ON codigos_verificacion (usuario_id, proposito) WHERE usado_en IS NULL;

-- ============================================================
-- B. CATALOGOS
-- Cada catalogo guarda el nombre y su forma normalizada. La forma
-- normalizada es unica: "INFORME", "Informe" e "Informé" son el
-- mismo valor. El indice de trigramas sugiere valores parecidos.
-- ============================================================
CREATE TABLE procedencias (
    id                 SERIAL PRIMARY KEY,
    nombre             VARCHAR(100) NOT NULL,
    nombre_normalizado TEXT GENERATED ALWAYS AS (normalizar_texto(nombre)) STORED UNIQUE,
    activo             BOOLEAN NOT NULL DEFAULT true
);

CREATE TABLE entidades (
    id                 SERIAL PRIMARY KEY,
    nombre             VARCHAR(250) NOT NULL,
    nombre_normalizado TEXT GENERATED ALWAYS AS (normalizar_texto(nombre)) STORED UNIQUE,
    activo             BOOLEAN NOT NULL DEFAULT true,
    creado_en          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE tipos_tramite (
    id                 SERIAL PRIMARY KEY,
    nombre             VARCHAR(150) NOT NULL,
    nombre_normalizado TEXT GENERATED ALWAYS AS (normalizar_texto(nombre)) STORED UNIQUE,
    activo             BOOLEAN NOT NULL DEFAULT true,
    creado_en          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Tipo del documento de respuesta: informe, nota, resolucion...
-- Tambien ordena el catalogo de prompts.
CREATE TABLE tipos_documento (
    id                 SERIAL PRIMARY KEY,
    nombre             VARCHAR(150) NOT NULL,
    nombre_normalizado TEXT GENERATED ALWAYS AS (normalizar_texto(nombre)) STORED UNIQUE,
    activo             BOOLEAN NOT NULL DEFAULT true,
    creado_en          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Area o unidad de origen (dato opcional, seccion "Mas datos").
CREATE TABLE areas (
    id                 SERIAL PRIMARY KEY,
    nombre             VARCHAR(150) NOT NULL,
    nombre_normalizado TEXT GENERATED ALWAYS AS (normalizar_texto(nombre)) STORED UNIQUE,
    activo             BOOLEAN NOT NULL DEFAULT true,
    creado_en          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Profesionales a los que se asignan tramites. Los del Excel historico
-- pueden no tener cuenta; para asignar un tramite nuevo, el profesional
-- debe estar vinculado a un usuario ABOGADO activo.
CREATE TABLE profesionales (
    id                 SERIAL PRIMARY KEY,
    nombre_completo    VARCHAR(150) NOT NULL,
    nombre_normalizado TEXT GENERATED ALWAYS AS (normalizar_texto(nombre_completo)) STORED UNIQUE,
    usuario_id         INT UNIQUE REFERENCES usuarios(id) ON DELETE SET NULL,
    activo             BOOLEAN NOT NULL DEFAULT true,
    creado_en          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_entidades_parecido      ON entidades       USING GIN (nombre_normalizado gin_trgm_ops);
CREATE INDEX idx_tipos_tramite_parecido  ON tipos_tramite   USING GIN (nombre_normalizado gin_trgm_ops);
CREATE INDEX idx_tipos_documento_parecido ON tipos_documento USING GIN (nombre_normalizado gin_trgm_ops);
CREATE INDEX idx_areas_parecido          ON areas           USING GIN (nombre_normalizado gin_trgm_ops);
CREATE INDEX idx_profesionales_parecido  ON profesionales   USING GIN (nombre_normalizado gin_trgm_ops);

-- ============================================================
-- C. TRAMITES, INFORMES Y PRECEDENTES
-- ============================================================
-- Cada carga del Excel historico queda registrada (antes de tramites,
-- porque cada tramite migrado apunta a su carga).
CREATE TABLE importaciones_excel (
    id                    SERIAL PRIMARY KEY,
    archivo_nombre        VARCHAR(255) NOT NULL,
    huella_sha256         CHAR(64) NOT NULL,        -- identifica el archivo exacto
    modo                  VARCHAR(12) NOT NULL CHECK (modo IN ('SIMULACION', 'DEFINITIVA')),
    estado                VARCHAR(12) NOT NULL DEFAULT 'EN_CURSO'
                          CHECK (estado IN ('EN_CURSO', 'COMPLETADA', 'FALLIDA')),
    registros_encontrados INT NOT NULL DEFAULT 0,
    registros_insertados  INT NOT NULL DEFAULT 0,
    registros_rechazados  INT NOT NULL DEFAULT 0,
    reporte               JSONB,
    ejecutado_por         INT NOT NULL REFERENCES usuarios(id),
    iniciado_en           TIMESTAMPTZ NOT NULL DEFAULT now(),
    finalizado_en         TIMESTAMPTZ
);
-- Un mismo Excel no se carga dos veces en modo definitivo.
CREATE UNIQUE INDEX uq_importaciones_definitivas ON importaciones_excel (huella_sha256)
    WHERE modo = 'DEFINITIVA' AND estado = 'COMPLETADA';

CREATE TABLE tramites (
    id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Registro (secretaria): 7 campos
    hoja_ruta              VARCHAR(80),             -- NO es unica
    registro_interno       VARCHAR(50),
    procedencia_id         INT REFERENCES procedencias(id),
    entidad_id             INT REFERENCES entidades(id),
    tipo_tramite_id        INT REFERENCES tipos_tramite(id),
    asunto                 TEXT,
    profesional_id         INT REFERENCES profesionales(id),   -- abogado asignado

    -- Conclusion (abogado asignado): 3 campos + el PDF en la tabla informes
    tipo_documento_id      INT REFERENCES tipos_documento(id),
    numero_documento       VARCHAR(100),            -- ej. CGE/SCSL/GAAJ/C-166/2026
    fecha_salida           DATE,                    -- si no se indica: fecha de subida del PDF

    -- Lo llena el sistema
    anio_gestion           SMALLINT NOT NULL DEFAULT EXTRACT(YEAR FROM current_date)
                           CHECK (anio_gestion BETWEEN 1990 AND 2100),
    estado_tramite         VARCHAR(20) NOT NULL DEFAULT 'RECIBIDO'
                           CHECK (estado_tramite IN ('RECIBIDO', 'EN_ELABORACION', 'CONCLUIDO', 'ARCHIVADO')),
    asignado_por           INT REFERENCES usuarios(id),
    fecha_asignacion       TIMESTAMPTZ,
    fecha_conclusion       TIMESTAMPTZ,

    -- Mas datos (opcionales)
    area_id                INT REFERENCES areas(id),
    observaciones          TEXT,

    -- Baja logica: el historico nunca se borra
    activo                 BOOLEAN NOT NULL DEFAULT true,
    baja_por               INT REFERENCES usuarios(id),
    baja_en                TIMESTAMPTZ,
    motivo_baja            TEXT,

    -- Origen del registro
    origen_registro        VARCHAR(10) NOT NULL DEFAULT 'SISTEMA'
                           CHECK (origen_registro IN ('SISTEMA', 'MIGRACION')),
    importacion_id         INT REFERENCES importaciones_excel(id),
    fila_excel             INT,

    creado_por             INT NOT NULL REFERENCES usuarios(id),
    actualizado_por        INT REFERENCES usuarios(id),
    creado_en              TIMESTAMPTZ NOT NULL DEFAULT now(),
    actualizado_en         TIMESTAMPTZ NOT NULL DEFAULT now(),

    vector_busqueda        TSVECTOR,                -- lo mantiene un trigger (paso 3)

    -- Un tramite nuevo exige los 5 datos obligatorios del registro.
    -- Los migrados pueden traer vacios: no se inventan, se marcan como incidencia.
    CONSTRAINT ck_tramites_registro_completo CHECK (
        origen_registro = 'MIGRACION' OR (
            hoja_ruta IS NOT NULL AND procedencia_id IS NOT NULL AND entidad_id IS NOT NULL
            AND tipo_tramite_id IS NOT NULL AND asunto IS NOT NULL AND btrim(asunto) <> '')),
    CONSTRAINT ck_tramites_asunto_corto CHECK (origen_registro = 'MIGRACION' OR length(asunto) <= 500),
    CONSTRAINT ck_tramites_baja CHECK (activo OR (baja_en IS NOT NULL AND baja_por IS NOT NULL AND motivo_baja IS NOT NULL)),
    CONSTRAINT ck_tramites_migracion CHECK (origen_registro = 'SISTEMA' OR importacion_id IS NOT NULL)
);

CREATE INDEX idx_tramites_hoja_ruta        ON tramites USING GIN (hoja_ruta gin_trgm_ops);
CREATE INDEX idx_tramites_registro_interno ON tramites USING GIN (registro_interno gin_trgm_ops);
CREATE INDEX idx_tramites_numero_documento ON tramites USING GIN (numero_documento gin_trgm_ops);
CREATE INDEX idx_tramites_busqueda         ON tramites USING GIN (vector_busqueda);
CREATE INDEX idx_tramites_entidad          ON tramites (entidad_id);
CREATE INDEX idx_tramites_tipo_tramite     ON tramites (tipo_tramite_id);
CREATE INDEX idx_tramites_tipo_documento   ON tramites (tipo_documento_id);
CREATE INDEX idx_tramites_profesional      ON tramites (profesional_id);
CREATE INDEX idx_tramites_anio             ON tramites (anio_gestion);
CREATE INDEX idx_tramites_fecha_salida     ON tramites (fecha_salida DESC NULLS LAST) WHERE activo;
CREATE INDEX idx_tramites_pendientes       ON tramites (profesional_id, estado_tramite)
    WHERE activo AND estado_tramite IN ('RECIBIDO', 'EN_ELABORACION');

-- Informe PDF del tramite. Se guarda fuera de la web; solo se ve por la aplicacion.
CREATE TABLE informes (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tramite_id      UUID NOT NULL REFERENCES tramites(id) ON DELETE RESTRICT,
    ruta_archivo    TEXT NOT NULL,                 -- ruta interna con nombre aleatorio
    nombre_original VARCHAR(255) NOT NULL,
    tamano_bytes    BIGINT NOT NULL CHECK (tamano_bytes > 0),
    huella_sha256   CHAR(64) NOT NULL,             -- integridad del archivo
    paginas         INT NOT NULL DEFAULT 0 CHECK (paginas >= 0),
    texto_extraido  TEXT,                          -- para la busqueda
    requirio_ocr    BOOLEAN NOT NULL DEFAULT false,
    subido_por      INT NOT NULL REFERENCES usuarios(id),
    subido_en       TIMESTAMPTZ NOT NULL DEFAULT now(),
    activo          BOOLEAN NOT NULL DEFAULT true  -- las versiones anteriores quedan inactivas
);
CREATE INDEX idx_informes_tramite ON informes (tramite_id);
CREATE UNIQUE INDEX uq_informes_un_activo ON informes (tramite_id) WHERE activo;

-- Precedente: el tramite "tramite_id" se apoya en "tramite_precedente_id".
-- El criterio lo escribe una persona (puede haberlo trabajado con su propia IA).
CREATE TABLE precedentes (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tramite_id            UUID NOT NULL REFERENCES tramites(id) ON DELETE RESTRICT,
    tramite_precedente_id UUID NOT NULL REFERENCES tramites(id) ON DELETE RESTRICT,
    criterio_legal        TEXT NOT NULL CHECK (btrim(criterio_legal) <> ''),
    relevancia            VARCHAR(20) NOT NULL CHECK (relevancia IN ('VINCULANTE', 'ORIENTADOR', 'REFERENCIAL')),
    tipo_relacion         VARCHAR(15) NOT NULL DEFAULT 'APLICA'
                          CHECK (tipo_relacion IN ('APLICA', 'COMPLEMENTA', 'MODIFICA', 'REVOCA')),
    origen                VARCHAR(10) NOT NULL DEFAULT 'MANUAL' CHECK (origen IN ('MANUAL', 'SIMILITUD')),
    observaciones         TEXT,
    creado_por            INT NOT NULL REFERENCES usuarios(id),
    creado_en             TIMESTAMPTZ NOT NULL DEFAULT now(),
    actualizado_por       INT REFERENCES usuarios(id),
    actualizado_en        TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_precedentes_distintos CHECK (tramite_id <> tramite_precedente_id),
    CONSTRAINT uq_precedentes_par UNIQUE (tramite_id, tramite_precedente_id)
);
CREATE INDEX idx_precedentes_precedente ON precedentes (tramite_precedente_id);

-- ============================================================
-- D. CATALOGO DE PROMPTS
-- Instrucciones listas para que cada doctor las copie y pegue en su
-- propio modelo de IA. El sistema NO se conecta a ninguna IA.
-- ============================================================
CREATE TABLE prompts (
    id                SERIAL PRIMARY KEY,
    titulo            VARCHAR(150) NOT NULL,
    categoria         VARCHAR(20) NOT NULL
                      CHECK (categoria IN ('CONSULTA', 'PRECEDENTE', 'JUICIO_VALOR', 'REDACCION', 'REVISION')),
    tipo_documento_id INT REFERENCES tipos_documento(id),   -- vacio = sirve para cualquier tipo
    texto             TEXT NOT NULL CHECK (btrim(texto) <> ''),
    instrucciones     TEXT,                                 -- como usarlo, que pegar despues
    estado            VARCHAR(10) NOT NULL DEFAULT 'BORRADOR'
                      CHECK (estado IN ('BORRADOR', 'VIGENTE', 'RETIRADO')),
    observacion       TEXT,                                 -- comentario del jefe al revisar
    usos              INT NOT NULL DEFAULT 0 CHECK (usos >= 0),
    propuesto_por     INT NOT NULL REFERENCES usuarios(id),
    aprobado_por      INT REFERENCES usuarios(id),
    aprobado_en       TIMESTAMPTZ,
    actualizado_por   INT REFERENCES usuarios(id),
    creado_en         TIMESTAMPTZ NOT NULL DEFAULT now(),
    actualizado_en    TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_prompts_aprobado CHECK (estado <> 'VIGENTE' OR (aprobado_por IS NOT NULL AND aprobado_en IS NOT NULL))
);
-- No puede haber dos prompts en uso con el mismo titulo.
CREATE UNIQUE INDEX uq_prompts_titulo ON prompts (normalizar_texto(titulo)) WHERE estado <> 'RETIRADO';
CREATE INDEX idx_prompts_listado ON prompts (estado, tipo_documento_id, categoria);
CREATE INDEX idx_prompts_busqueda ON prompts
    USING GIN (to_tsvector('es_legal', titulo || ' ' || texto));

-- ============================================================
-- E. SOPORTE
-- ============================================================
-- Enlaces del buscador a sitios legales (TCP, TSJ, Gaceta...).
-- url_busqueda lleva {q}, que se reemplaza por lo que se busca.
CREATE TABLE fuentes_externas (
    id           SERIAL PRIMARY KEY,
    nombre       VARCHAR(120) NOT NULL UNIQUE,
    descripcion  VARCHAR(250),
    url          TEXT NOT NULL CHECK (url ~* '^https?://\S+$'),
    url_busqueda TEXT CHECK (url_busqueda IS NULL OR (url_busqueda ~* '^https?://\S+$' AND url_busqueda LIKE '%{q}%')),
    orden        SMALLINT NOT NULL DEFAULT 100,
    activo       BOOLEAN NOT NULL DEFAULT true
);

-- Filas del Excel que no se pudieron migrar tal cual: quedan para revision.
CREATE TABLE incidencias_migracion (
    id             SERIAL PRIMARY KEY,
    importacion_id INT NOT NULL REFERENCES importaciones_excel(id),
    fila_excel     INT NOT NULL,
    tipo           VARCHAR(50) NOT NULL,           -- ej. FECHA_ILEGIBLE, ENTIDAD_VACIA
    descripcion    TEXT NOT NULL,
    datos_origen   JSONB,                          -- la fila tal como vino
    tramite_id     UUID REFERENCES tramites(id),
    estado         VARCHAR(20) NOT NULL DEFAULT 'PENDIENTE'
                   CHECK (estado IN ('PENDIENTE', 'CORREGIDA', 'SIN_ACCION')),
    resuelto_por   INT REFERENCES usuarios(id),
    resuelto_en    TIMESTAMPTZ,
    creado_en      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_incidencias_estado ON incidencias_migracion (estado);

-- Parametros que el ADMIN cambia desde la aplicacion.
CREATE TABLE configuracion (
    clave           VARCHAR(60) PRIMARY KEY,
    valor           TEXT,
    descripcion     TEXT NOT NULL,
    actualizado_por INT REFERENCES usuarios(id),
    actualizado_en  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Bitacora de todo lo que pasa. No se modifica ni se borra (paso 3).
CREATE TABLE auditoria (
    id             BIGSERIAL PRIMARY KEY,
    usuario_id     INT REFERENCES usuarios(id),
    usuario_correo VARCHAR(150),                   -- copia, por si el usuario cambia
    accion         VARCHAR(50) NOT NULL,           -- ej. SUBIR_INFORME, COPIAR_PROMPT
    modulo         VARCHAR(50) NOT NULL,
    objeto_tipo    VARCHAR(50),                    -- ej. tramite, prompt, usuario
    objeto_id      VARCHAR(60),
    resultado      VARCHAR(10) NOT NULL CHECK (resultado IN ('EXITOSO', 'FALLIDO', 'BLOQUEADO')),
    ip             VARCHAR(45),
    detalle        JSONB,
    creado_en      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_auditoria_fecha   ON auditoria (creado_en DESC);
CREATE INDEX idx_auditoria_usuario ON auditoria (usuario_id, creado_en);
CREATE INDEX idx_auditoria_accion  ON auditoria (accion, creado_en);
CREATE INDEX idx_auditoria_objeto  ON auditoria (objeto_tipo, objeto_id);

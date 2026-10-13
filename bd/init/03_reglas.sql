-- ============================================================
-- REPOSITORIO SCSL - Paso 3 de 6: reglas de negocio en la base.
--
-- Estas reglas se cumplen aunque alguien escriba directo en la base
-- (sin pasar por la aplicacion):
--   1. Fechas de actualizacion automaticas
--   2. Permisos: funciones de consulta
--   3. Flujo del tramite (asignar, concluir, archivar)
--   4. Subida del informe (solo el abogado asignado; el PDF subido no se altera)
--      y registro de precedentes (solo con permiso)
--   5. Indice de busqueda
--   6. Catalogo de prompts (proponer, aprobar, usar)
--   7. Auditoria inmutable
--   8. Consultas de apoyo: cadena de precedentes, similares, unificar catalogo
-- ============================================================
SET client_min_messages = warning;

-- ============================================================
-- 1. FECHA DE ACTUALIZACION
-- ============================================================
CREATE FUNCTION fijar_actualizado_en() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    NEW.actualizado_en := now();
    RETURN NEW;
END $$;

CREATE TRIGGER trg_usuarios_actualizado BEFORE UPDATE ON usuarios
    FOR EACH ROW EXECUTE FUNCTION fijar_actualizado_en();
CREATE TRIGGER trg_precedentes_actualizado BEFORE UPDATE ON precedentes
    FOR EACH ROW EXECUTE FUNCTION fijar_actualizado_en();
CREATE TRIGGER trg_configuracion_actualizado BEFORE UPDATE ON configuracion
    FOR EACH ROW EXECUTE FUNCTION fijar_actualizado_en();

-- ============================================================
-- 2. PERMISOS
-- La aplicacion pregunta: SELECT usuario_tiene_permiso(7, 'DESCARGAR_INFORME');
-- ============================================================
CREATE FUNCTION usuario_tiene_permiso(p_usuario INT, p_permiso TEXT)
RETURNS BOOLEAN LANGUAGE sql STABLE AS $$
    SELECT EXISTS (
        SELECT 1 FROM usuarios u
          JOIN roles_permisos rp ON rp.rol_id = u.rol_id
          JOIN permisos p ON p.id = rp.permiso_id
         WHERE u.id = p_usuario AND u.activo AND p.codigo = p_permiso)
$$;

CREATE FUNCTION usuario_rol(p_usuario INT)
RETURNS TEXT LANGUAGE sql STABLE AS $$
    SELECT r.nombre FROM usuarios u JOIN roles r ON r.id = u.rol_id WHERE u.id = p_usuario
$$;

-- Ajustes de mantenimiento (scsl.mantenimiento, scsl.purga_auditoria):
-- solo cuentan si los activa el dueno de la base. Cualquier sesion puede
-- hacer SET; si bastara con eso, la cuenta de la aplicacion se saltaria
-- todas las reglas del flujo.
CREATE FUNCTION ajuste_del_dueno_activo(p_ajuste TEXT)
RETURNS BOOLEAN LANGUAGE sql STABLE AS $$
    SELECT coalesce(current_setting(p_ajuste, true), '') = 'on'
       AND pg_has_role(current_user,
                       (SELECT relowner FROM pg_class WHERE oid = 'public.tramites'::regclass), 'MEMBER')
$$;

-- ============================================================
-- 5 (se define antes porque el flujo la usa). INDICE DE BUSQUEDA
-- Pesos: A = codigos y asunto; B = catalogos y criterios de precedentes;
-- C = observaciones; D = texto del informe PDF.
-- ============================================================
CREATE FUNCTION construir_vector_tramite(t tramites)
RETURNS tsvector LANGUAGE sql STABLE AS $$
    SELECT
        setweight(to_tsvector('es_legal', concat_ws(' ',
            t.hoja_ruta, t.registro_interno, t.numero_documento, t.asunto)), 'A')
     || setweight(to_tsvector('es_legal', concat_ws(' ',
            (SELECT nombre FROM procedencias WHERE id = t.procedencia_id),
            (SELECT nombre FROM entidades WHERE id = t.entidad_id),
            (SELECT nombre FROM tipos_tramite WHERE id = t.tipo_tramite_id),
            (SELECT nombre FROM tipos_documento WHERE id = t.tipo_documento_id),
            (SELECT nombre FROM areas WHERE id = t.area_id),
            (SELECT nombre_completo FROM profesionales WHERE id = t.profesional_id),
            (SELECT string_agg(p.criterio_legal, ' ') FROM precedentes p WHERE p.tramite_id = t.id))), 'B')
     || setweight(to_tsvector('es_legal', coalesce(t.observaciones, '')), 'C')
     || setweight(to_tsvector('es_legal', coalesce((SELECT left(i.texto_extraido, 300000)
            FROM informes i WHERE i.tramite_id = t.id AND i.activo), '')), 'D')
$$;

-- ============================================================
-- 3. FLUJO DEL TRAMITE
--   RECIBIDO --(asignar abogado)--> EN_ELABORACION --(subir informe)--> CONCLUIDO --(archivar)--> ARCHIVADO
-- Los registros migrados del Excel conservan su estado historico.
-- ============================================================
CREATE FUNCTION tramites_antes_guardar() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    v_quien   INT := COALESCE(NEW.actualizado_por, NEW.creado_por);
    v_abogado INT;
BEGIN
    -- Fecha de actualizacion solo para cambios de un usuario (no para recalculos del indice).
    IF TG_OP = 'UPDATE' AND pg_trigger_depth() = 1
       AND coalesce(current_setting('scsl.reindexando', true), '') <> 'on' THEN
        NEW.actualizado_en := now();
    END IF;

    IF NOT ajuste_del_dueno_activo('scsl.mantenimiento') THEN
        -- El origen se fija al registrar: cambiarlo a MIGRACION saltaria el flujo.
        IF TG_OP = 'UPDATE' AND NEW.origen_registro IS DISTINCT FROM OLD.origen_registro THEN
            RAISE EXCEPTION 'El origen de un tramite no se cambia';
        END IF;
        -- Solo una importacion del Excel en curso crea registros migrados.
        IF TG_OP = 'INSERT' AND NEW.origen_registro = 'MIGRACION' AND (
               NOT usuario_tiene_permiso(NEW.creado_por, 'IMPORTAR_EXCEL')
               OR NOT EXISTS (SELECT 1 FROM importaciones_excel ie
                               WHERE ie.id = NEW.importacion_id AND ie.estado = 'EN_CURSO')) THEN
            RAISE EXCEPTION 'Solo una importacion del Excel en curso registra tramites migrados';
        END IF;
        -- Dar de baja o reactivar, tambien a los migrados, exige ELIMINAR_LOGICO.
        IF TG_OP = 'UPDATE' AND NEW.activo IS DISTINCT FROM OLD.activo
           AND NOT usuario_tiene_permiso(v_quien, 'ELIMINAR_LOGICO') THEN
            RAISE EXCEPTION 'No tiene permiso para dar de baja tramites';
        END IF;
    END IF;

    -- Baja logica: se registra cuando y quien.
    IF NOT NEW.activo AND (TG_OP = 'INSERT' OR OLD.activo) THEN
        NEW.baja_en  := COALESCE(NEW.baja_en, now());
        NEW.baja_por := COALESCE(NEW.baja_por, v_quien);
    ELSIF NEW.activo THEN
        NEW.baja_en := NULL; NEW.baja_por := NULL; NEW.motivo_baja := NULL;
    END IF;

    -- Las reglas del flujo no se aplican a los registros migrados ni durante
    -- tareas de mantenimiento del dueno de la base (unificar catalogos).
    IF NEW.origen_registro = 'SISTEMA' AND NOT ajuste_del_dueno_activo('scsl.mantenimiento') THEN
        -- Solo registra tramites quien tiene CREAR_REGISTRO (secretaria, jefe, admin).
        IF TG_OP = 'INSERT' AND NOT usuario_tiene_permiso(NEW.creado_por, 'CREAR_REGISTRO') THEN
            RAISE EXCEPTION 'No tiene permiso para registrar tramites';
        END IF;

        -- Un tramite concluido o archivado no vuelve atras ni cambia de abogado.
        IF TG_OP = 'UPDATE' AND OLD.estado_tramite IN ('CONCLUIDO', 'ARCHIVADO') THEN
            IF NEW.estado_tramite IN ('RECIBIDO', 'EN_ELABORACION') THEN
                RAISE EXCEPTION 'Un tramite concluido no vuelve a elaboracion';
            END IF;
            IF NEW.profesional_id IS DISTINCT FROM OLD.profesional_id THEN
                RAISE EXCEPTION 'No se cambia el abogado de un tramite concluido';
            END IF;
        END IF;

        -- Sacar un tramite del archivo exige el mismo permiso que archivarlo.
        IF TG_OP = 'UPDATE' AND OLD.estado_tramite = 'ARCHIVADO' AND NEW.estado_tramite <> 'ARCHIVADO'
           AND NOT usuario_tiene_permiso(v_quien, 'ARCHIVAR_TRAMITE') THEN
            RAISE EXCEPTION 'No tiene permiso para desarchivar tramites';
        END IF;

        -- Asignacion
        IF NEW.estado_tramite IN ('RECIBIDO', 'EN_ELABORACION') THEN
            IF NEW.profesional_id IS NULL THEN
                -- Quitar el abogado es una reasignacion: el abogado no se quita el tramite.
                IF TG_OP = 'UPDATE' AND OLD.profesional_id IS NOT NULL
                   AND NOT usuario_tiene_permiso(v_quien, 'ASIGNAR_TRAMITE') THEN
                    RAISE EXCEPTION 'No tiene permiso para asignar tramites';
                END IF;
                NEW.estado_tramite   := 'RECIBIDO';
                NEW.fecha_asignacion := NULL;
                NEW.asignado_por     := NULL;
            ELSIF TG_OP = 'INSERT' OR NEW.profesional_id IS DISTINCT FROM OLD.profesional_id THEN
                IF NOT usuario_tiene_permiso(v_quien, 'ASIGNAR_TRAMITE') THEN
                    RAISE EXCEPTION 'No tiene permiso para asignar tramites';
                END IF;
                SELECT p.usuario_id INTO v_abogado FROM profesionales p WHERE p.id = NEW.profesional_id AND p.activo;
                IF v_abogado IS NULL OR NOT usuario_tiene_permiso(v_abogado, 'SUBIR_INFORME') THEN
                    RAISE EXCEPTION 'Solo se asigna a un abogado con cuenta activa en el sistema';
                END IF;
                NEW.estado_tramite   := 'EN_ELABORACION';
                NEW.fecha_asignacion := now();
                NEW.asignado_por     := v_quien;
            ELSE
                -- Mismo abogado: el estado y los datos de la asignacion los fija
                -- la base; a mano quedaria RECIBIDO con abogado y fuera de su bandeja.
                NEW.estado_tramite   := 'EN_ELABORACION';
                NEW.fecha_asignacion := OLD.fecha_asignacion;
                NEW.asignado_por     := OLD.asignado_por;
            END IF;
        END IF;

        -- Conclusion: solo con informe activo (lo hace la subida del PDF).
        IF NEW.estado_tramite = 'CONCLUIDO' AND (TG_OP = 'INSERT' OR OLD.estado_tramite <> 'CONCLUIDO')
           AND NOT EXISTS (SELECT 1 FROM informes i WHERE i.tramite_id = NEW.id AND i.activo) THEN
            RAISE EXCEPTION 'El tramite se concluye cuando el abogado asignado sube el informe';
        END IF;

        -- Archivo: solo desde CONCLUIDO y con permiso.
        IF NEW.estado_tramite = 'ARCHIVADO' AND (TG_OP = 'INSERT' OR OLD.estado_tramite <> 'ARCHIVADO') THEN
            IF TG_OP = 'INSERT' OR OLD.estado_tramite <> 'CONCLUIDO' THEN
                RAISE EXCEPTION 'Solo se archiva un tramite concluido';
            END IF;
            IF NOT usuario_tiene_permiso(v_quien, 'ARCHIVAR_TRAMITE') THEN
                RAISE EXCEPTION 'No tiene permiso para archivar tramites';
            END IF;
        END IF;
    END IF;

    NEW.vector_busqueda := construir_vector_tramite(NEW);
    RETURN NEW;
END $$;

CREATE TRIGGER trg_tramites_antes_guardar BEFORE INSERT OR UPDATE ON tramites
    FOR EACH ROW EXECUTE FUNCTION tramites_antes_guardar();

-- ============================================================
-- 4. SUBIDA DEL INFORME
-- Solo el abogado asignado (o ADMIN) sube el informe, y antes debe
-- haber llenado el tipo y el numero del documento de respuesta.
-- Al subirlo, la version anterior queda inactiva y el tramite se concluye.
-- ============================================================
CREATE FUNCTION informes_antes_subir() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    t         tramites%ROWTYPE;
    v_abogado INT;
BEGIN
    SELECT * INTO t FROM tramites WHERE id = NEW.tramite_id;
    IF NOT t.activo THEN
        RAISE EXCEPTION 'No se sube un informe a un tramite dado de baja';
    END IF;

    IF usuario_rol(NEW.subido_por) IS DISTINCT FROM 'ADMIN' THEN
        SELECT p.usuario_id INTO v_abogado FROM profesionales p WHERE p.id = t.profesional_id;
        IF NEW.subido_por IS DISTINCT FROM v_abogado
           OR NOT usuario_tiene_permiso(NEW.subido_por, 'SUBIR_INFORME') THEN
            RAISE EXCEPTION 'Solo el abogado asignado al tramite puede subir el informe';
        END IF;
    END IF;

    IF t.origen_registro = 'SISTEMA' THEN
        IF t.estado_tramite NOT IN ('EN_ELABORACION', 'CONCLUIDO') THEN
            RAISE EXCEPTION 'El tramite debe estar en elaboracion para subir el informe';
        END IF;
        IF t.tipo_documento_id IS NULL OR coalesce(btrim(t.numero_documento), '') = '' THEN
            RAISE EXCEPTION 'Antes de subir el informe registre el tipo y el numero del documento de respuesta';
        END IF;
    END IF;

    IF NEW.activo THEN
        UPDATE informes SET activo = false WHERE tramite_id = NEW.tramite_id AND activo;
    END IF;
    RETURN NEW;
END $$;

CREATE TRIGGER trg_informes_antes_subir BEFORE INSERT ON informes
    FOR EACH ROW EXECUTE FUNCTION informes_antes_subir();

CREATE FUNCTION informes_despues_subir() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    UPDATE tramites
       SET estado_tramite   = CASE WHEN estado_tramite IN ('RECIBIDO', 'EN_ELABORACION')
                                   THEN 'CONCLUIDO' ELSE estado_tramite END,
           fecha_conclusion = COALESCE(fecha_conclusion, now()),
           fecha_salida     = COALESCE(fecha_salida, current_date),
           actualizado_por  = NEW.subido_por
     WHERE id = NEW.tramite_id;
    RETURN NULL;
END $$;

CREATE TRIGGER trg_informes_despues_subir AFTER INSERT ON informes
    FOR EACH ROW WHEN (NEW.activo) EXECUTE FUNCTION informes_despues_subir();

-- Un informe subido no se altera: ruta, huella y autor son la prueba de
-- integridad del PDF. Solo se completan los datos de lectura (texto,
-- paginas, OCR). La version activa cambia unicamente cuando la subida de
-- una nueva desactiva la anterior (pg_trigger_depth > 1); hacerlo a mano
-- dejaria un tramite concluido sin informe.
CREATE FUNCTION informes_antes_modificar() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF ajuste_del_dueno_activo('scsl.mantenimiento') THEN
        RETURN NEW;
    END IF;
    IF (NEW.tramite_id, NEW.ruta_archivo, NEW.nombre_original, NEW.tamano_bytes,
        NEW.huella_sha256, NEW.subido_por, NEW.subido_en)
       IS DISTINCT FROM
       (OLD.tramite_id, OLD.ruta_archivo, OLD.nombre_original, OLD.tamano_bytes,
        OLD.huella_sha256, OLD.subido_por, OLD.subido_en) THEN
        RAISE EXCEPTION 'Un informe subido no se modifica: suba una version nueva';
    END IF;
    IF NEW.activo IS DISTINCT FROM OLD.activo AND (NEW.activo OR pg_trigger_depth() = 1) THEN
        RAISE EXCEPTION 'La version activa del informe cambia solo al subir una version nueva';
    END IF;
    RETURN NEW;
END $$;

CREATE TRIGGER trg_informes_antes_modificar BEFORE UPDATE ON informes
    FOR EACH ROW EXECUTE FUNCTION informes_antes_modificar();

-- ============================================================
-- PRECEDENTES: los registra quien tiene GESTIONAR_PRECEDENTES
-- (abogado, jefe, admin).
-- ============================================================
CREATE FUNCTION precedentes_antes_guardar() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NOT usuario_tiene_permiso(COALESCE(NEW.actualizado_por, NEW.creado_por), 'GESTIONAR_PRECEDENTES') THEN
        RAISE EXCEPTION 'No tiene permiso para registrar precedentes';
    END IF;
    RETURN NEW;
END $$;

CREATE TRIGGER trg_precedentes_antes_guardar BEFORE INSERT OR UPDATE ON precedentes
    FOR EACH ROW EXECUTE FUNCTION precedentes_antes_guardar();

-- ============================================================
-- 5. INDICE DE BUSQUEDA: recalculo cuando cambian datos relacionados
-- ============================================================
-- Cambia un precedente o un informe -> se recalcula el tramite.
CREATE FUNCTION refrescar_vector_por_relacion() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    PERFORM set_config('scsl.reindexando', 'on', true);
    IF TG_OP <> 'DELETE' THEN
        UPDATE tramites SET vector_busqueda = NULL WHERE id = NEW.tramite_id;
    END IF;
    IF TG_OP = 'DELETE' OR NEW.tramite_id IS DISTINCT FROM OLD.tramite_id THEN
        UPDATE tramites SET vector_busqueda = NULL WHERE id = OLD.tramite_id;
    END IF;
    PERFORM set_config('scsl.reindexando', 'off', true);
    RETURN NULL;
END $$;

CREATE TRIGGER trg_informes_vector AFTER UPDATE OR DELETE ON informes
    FOR EACH ROW EXECUTE FUNCTION refrescar_vector_por_relacion();
CREATE TRIGGER trg_precedentes_vector AFTER INSERT OR UPDATE OR DELETE ON precedentes
    FOR EACH ROW EXECUTE FUNCTION refrescar_vector_por_relacion();

-- Se corrige el nombre de un valor de catalogo -> se recalculan sus tramites.
CREATE FUNCTION refrescar_vector_por_catalogo() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    PERFORM set_config('scsl.reindexando', 'on', true);
    EXECUTE format('UPDATE tramites SET vector_busqueda = NULL WHERE %I = $1', TG_ARGV[0]) USING NEW.id;
    PERFORM set_config('scsl.reindexando', 'off', true);
    RETURN NULL;
END $$;

CREATE TRIGGER trg_procedencias_vector AFTER UPDATE OF nombre ON procedencias
    FOR EACH ROW WHEN (OLD.nombre IS DISTINCT FROM NEW.nombre) EXECUTE FUNCTION refrescar_vector_por_catalogo('procedencia_id');
CREATE TRIGGER trg_entidades_vector AFTER UPDATE OF nombre ON entidades
    FOR EACH ROW WHEN (OLD.nombre IS DISTINCT FROM NEW.nombre) EXECUTE FUNCTION refrescar_vector_por_catalogo('entidad_id');
CREATE TRIGGER trg_tipos_tramite_vector AFTER UPDATE OF nombre ON tipos_tramite
    FOR EACH ROW WHEN (OLD.nombre IS DISTINCT FROM NEW.nombre) EXECUTE FUNCTION refrescar_vector_por_catalogo('tipo_tramite_id');
CREATE TRIGGER trg_tipos_documento_vector AFTER UPDATE OF nombre ON tipos_documento
    FOR EACH ROW WHEN (OLD.nombre IS DISTINCT FROM NEW.nombre) EXECUTE FUNCTION refrescar_vector_por_catalogo('tipo_documento_id');
CREATE TRIGGER trg_areas_vector AFTER UPDATE OF nombre ON areas
    FOR EACH ROW WHEN (OLD.nombre IS DISTINCT FROM NEW.nombre) EXECUTE FUNCTION refrescar_vector_por_catalogo('area_id');
CREATE TRIGGER trg_profesionales_vector AFTER UPDATE OF nombre_completo ON profesionales
    FOR EACH ROW WHEN (OLD.nombre_completo IS DISTINCT FROM NEW.nombre_completo) EXECUTE FUNCTION refrescar_vector_por_catalogo('profesional_id');

-- Recalcula todo el indice (despues de migrar el Excel).
CREATE FUNCTION reindexar_tramites() RETURNS INT LANGUAGE plpgsql AS $$
DECLARE n INT;
BEGIN
    PERFORM set_config('scsl.reindexando', 'on', true);
    UPDATE tramites SET vector_busqueda = NULL;
    GET DIAGNOSTICS n = ROW_COUNT;
    PERFORM set_config('scsl.reindexando', 'off', true);
    RETURN n;
END $$;

-- ============================================================
-- 6. CATALOGO DE PROMPTS
--   BORRADOR (lo propone un ABOGADO o el JEFE)
--     -> VIGENTE (lo aprueba quien tiene GESTIONAR_PROMPTS)
--     -> RETIRADO (deja de mostrarse; no se borra)
-- ============================================================
CREATE FUNCTION prompts_antes_guardar() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    v_quien INT := COALESCE(NEW.actualizado_por, NEW.propuesto_por);
BEGIN
    -- Contar un uso no es una edicion.
    IF TG_OP = 'UPDATE' AND (to_jsonb(NEW) - 'usos') = (to_jsonb(OLD) - 'usos') THEN
        RETURN NEW;
    END IF;

    IF TG_OP = 'INSERT' AND NOT usuario_tiene_permiso(NEW.propuesto_por, 'PROPONER_PROMPT') THEN
        RAISE EXCEPTION 'No tiene permiso para proponer prompts';
    END IF;

    -- Editar un prompt vigente o retirado, o cambiar su estado: solo quien
    -- gestiona el catalogo (un retirado no lo revive quien lo propuso).
    IF TG_OP = 'UPDATE' AND OLD.estado IN ('VIGENTE', 'RETIRADO')
       AND NOT usuario_tiene_permiso(v_quien, 'GESTIONAR_PROMPTS') THEN
        RAISE EXCEPTION 'Solo el jefe modifica un prompt vigente o retirado';
    END IF;

    IF NEW.estado = 'VIGENTE' AND (TG_OP = 'INSERT' OR OLD.estado <> 'VIGENTE') THEN
        IF NOT usuario_tiene_permiso(v_quien, 'GESTIONAR_PROMPTS') THEN
            RAISE EXCEPTION 'Solo el jefe aprueba prompts';
        END IF;
        NEW.aprobado_por := v_quien;
        NEW.aprobado_en  := now();
    ELSIF NEW.estado = 'RETIRADO' AND TG_OP = 'UPDATE' AND OLD.estado <> 'RETIRADO'
          AND NOT usuario_tiene_permiso(v_quien, 'GESTIONAR_PROMPTS') THEN
        RAISE EXCEPTION 'Solo el jefe retira prompts';
    ELSIF NEW.estado = 'BORRADOR' THEN
        NEW.aprobado_por := NULL;
        NEW.aprobado_en  := NULL;
    END IF;

    NEW.actualizado_en := now();
    RETURN NEW;
END $$;

CREATE TRIGGER trg_prompts_antes_guardar BEFORE INSERT OR UPDATE ON prompts
    FOR EACH ROW EXECUTE FUNCTION prompts_antes_guardar();

-- La aplicacion la llama cuando el usuario pulsa "Copiar".
-- Suma el uso y deja el registro en la auditoria.
CREATE FUNCTION registrar_uso_prompt(p_prompt INT, p_usuario INT, p_tramite UUID DEFAULT NULL, p_ip TEXT DEFAULT NULL)
RETURNS VOID LANGUAGE plpgsql AS $$
BEGIN
    IF NOT usuario_tiene_permiso(p_usuario, 'USAR_PROMPTS') THEN
        RAISE EXCEPTION 'No tiene permiso para usar prompts';
    END IF;
    UPDATE prompts SET usos = usos + 1 WHERE id = p_prompt AND estado = 'VIGENTE';
    IF NOT FOUND THEN
        RAISE EXCEPTION 'El prompt no existe o no esta vigente';
    END IF;
    INSERT INTO auditoria (usuario_id, usuario_correo, accion, modulo, objeto_tipo, objeto_id, resultado, ip, detalle)
    SELECT p_usuario, u.correo, 'COPIAR_PROMPT', 'PROMPTS', 'prompt', p_prompt::text, 'EXITOSO', p_ip,
           jsonb_build_object('tramite_id', p_tramite)
      FROM usuarios u WHERE u.id = p_usuario;
END $$;

-- ============================================================
-- 7. AUDITORIA INMUTABLE
-- Solo se borra por la politica de retencion, de forma explicita y como
-- dueno de la base (la cuenta de la aplicacion no puede):
--   BEGIN; SET LOCAL scsl.purga_auditoria = 'on';
--   DELETE FROM auditoria WHERE creado_en < now() - interval '5 years'; COMMIT;
-- TRUNCATE no dispara los triggers por fila: tiene el suyo y nunca se permite.
-- ============================================================
CREATE FUNCTION auditoria_inmutable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'DELETE' AND ajuste_del_dueno_activo('scsl.purga_auditoria') THEN
        RETURN OLD;
    END IF;
    RAISE EXCEPTION 'La auditoria no puede modificarse ni eliminarse';
END $$;

CREATE TRIGGER trg_auditoria_inmutable BEFORE UPDATE OR DELETE ON auditoria
    FOR EACH ROW EXECUTE FUNCTION auditoria_inmutable();
CREATE TRIGGER trg_auditoria_sin_truncate BEFORE TRUNCATE ON auditoria
    FOR EACH STATEMENT EXECUTE FUNCTION auditoria_inmutable();

-- ============================================================
-- 8. CONSULTAS DE APOYO
-- ============================================================
-- Cadena de precedentes de un tramite, hacia atras (en que se basa)
-- y hacia adelante (quien lo cita).
--   SELECT * FROM cadena_precedentes('<uuid>');
CREATE FUNCTION cadena_precedentes(p_tramite UUID, p_max_nivel INT DEFAULT 5)
RETURNS TABLE (direccion TEXT, nivel INT, tramite_id UUID, desde_tramite_id UUID,
               relevancia VARCHAR, tipo_relacion VARCHAR, criterio_legal TEXT)
LANGUAGE sql STABLE AS $$
    WITH RECURSIVE
    antecesores AS (
        SELECT 1 AS nivel, p.tramite_precedente_id AS t, p.tramite_id AS desde,
               p.relevancia, p.tipo_relacion, p.criterio_legal,
               ARRAY[p.tramite_id, p.tramite_precedente_id] AS ruta
          FROM precedentes p WHERE p.tramite_id = p_tramite
        UNION ALL
        SELECT a.nivel + 1, p.tramite_precedente_id, p.tramite_id,
               p.relevancia, p.tipo_relacion, p.criterio_legal, a.ruta || p.tramite_precedente_id
          FROM precedentes p JOIN antecesores a ON p.tramite_id = a.t
         WHERE a.nivel < p_max_nivel AND NOT p.tramite_precedente_id = ANY (a.ruta)
    ),
    sucesores AS (
        SELECT 1 AS nivel, p.tramite_id AS t, p.tramite_precedente_id AS desde,
               p.relevancia, p.tipo_relacion, p.criterio_legal,
               ARRAY[p.tramite_precedente_id, p.tramite_id] AS ruta
          FROM precedentes p WHERE p.tramite_precedente_id = p_tramite
        UNION ALL
        SELECT s.nivel + 1, p.tramite_id, p.tramite_precedente_id,
               p.relevancia, p.tipo_relacion, p.criterio_legal, s.ruta || p.tramite_id
          FROM precedentes p JOIN sucesores s ON p.tramite_precedente_id = s.t
         WHERE s.nivel < p_max_nivel AND NOT p.tramite_id = ANY (s.ruta)
    )
    SELECT 'SE_BASA_EN', a.nivel, a.t, a.desde, a.relevancia, a.tipo_relacion, a.criterio_legal
      FROM antecesores a JOIN tramites x ON x.id = a.t AND x.activo
    UNION ALL
    SELECT 'ES_CITADO_POR', s.nivel, s.t, s.desde, s.relevancia, s.tipo_relacion, s.criterio_legal
      FROM sucesores s JOIN tramites x ON x.id = s.t AND x.activo
    ORDER BY 1, 2
$$;

-- Tramites con asunto parecido (sugerencia de precedentes, sin IA).
--   SELECT * FROM tramites_similares('<uuid>');
CREATE FUNCTION tramites_similares(p_tramite UUID, p_limite INT DEFAULT 10)
RETURNS TABLE (tramite_id UUID, afinidad NUMERIC)
LANGUAGE sql STABLE AS $$
    SELECT t.id, round(100 * similarity(normalizar_texto(t.asunto), normalizar_texto(b.asunto))::numeric, 1)
      FROM tramites b
      JOIN tramites t ON t.id <> b.id AND t.activo AND t.asunto IS NOT NULL
     WHERE b.id = p_tramite AND b.asunto IS NOT NULL
       AND similarity(normalizar_texto(t.asunto), normalizar_texto(b.asunto)) > 0.2
     ORDER BY 2 DESC
     LIMIT p_limite
$$;

-- Une dos valores de catalogo que son el mismo (ej. "GOB. AUT. LA PAZ" y
-- "GOBIERNO AUTONOMO DE LA PAZ"): pasa los tramites al que se conserva y
-- borra el duplicado.  SELECT unificar_catalogo('entidades', 12, 47);
CREATE FUNCTION unificar_catalogo(p_tabla TEXT, p_conservar INT, p_eliminar INT)
RETURNS INT LANGUAGE plpgsql AS $$
DECLARE
    v_columna TEXT;
    v_movidos INT;
    v_cuenta  INT;
BEGIN
    v_columna := CASE p_tabla
        WHEN 'procedencias'    THEN 'procedencia_id'
        WHEN 'entidades'       THEN 'entidad_id'
        WHEN 'tipos_tramite'   THEN 'tipo_tramite_id'
        WHEN 'tipos_documento' THEN 'tipo_documento_id'
        WHEN 'areas'           THEN 'area_id'
        WHEN 'profesionales'   THEN 'profesional_id'
    END;
    IF v_columna IS NULL THEN
        RAISE EXCEPTION 'Catalogo desconocido: %', p_tabla;
    END IF;
    IF p_conservar = p_eliminar THEN
        RAISE EXCEPTION 'Los dos valores son el mismo';
    END IF;
    PERFORM set_config('scsl.mantenimiento', 'on', true);
    EXECUTE format('UPDATE tramites SET %I = $1 WHERE %I = $2', v_columna, v_columna) USING p_conservar, p_eliminar;
    GET DIAGNOSTICS v_movidos = ROW_COUNT;
    PERFORM set_config('scsl.mantenimiento', 'off', true);
    IF p_tabla = 'tipos_documento' THEN
        UPDATE prompts SET tipo_documento_id = p_conservar WHERE tipo_documento_id = p_eliminar;
    ELSIF p_tabla = 'profesionales' THEN
        -- Si el duplicado tenia la cuenta del abogado, la cuenta pasa al que se conserva.
        SELECT usuario_id INTO v_cuenta FROM profesionales WHERE id = p_eliminar;
        UPDATE profesionales SET usuario_id = NULL WHERE id = p_eliminar;
        UPDATE profesionales SET usuario_id = COALESCE(usuario_id, v_cuenta) WHERE id = p_conservar;
    END IF;
    EXECUTE format('DELETE FROM %I WHERE id = $1', p_tabla) USING p_eliminar;
    RETURN v_movidos;
END $$;

-- Puerta de la aplicacion para unificar: la cuenta de la aplicacion no
-- ejecuta unificar_catalogo (06_seguridad.sh), pero si esta funcion, que
-- corre como dueno de la base y exige GESTIONAR_CATALOGOS al usuario.
--   SELECT unificar_catalogo_app(1, 'entidades', 12, 47);
CREATE FUNCTION unificar_catalogo_app(p_usuario INT, p_tabla TEXT, p_conservar INT, p_eliminar INT)
RETURNS INT LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
BEGIN
    IF NOT usuario_tiene_permiso(p_usuario, 'GESTIONAR_CATALOGOS') THEN
        RAISE EXCEPTION 'No tiene permiso para unificar catalogos';
    END IF;
    RETURN unificar_catalogo(p_tabla, p_conservar, p_eliminar);
END $$;

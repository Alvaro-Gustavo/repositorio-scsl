#!/usr/bin/env bash
# ============================================================
# REPOSITORIO SCSL - Paso 7: notificaciones.
# Cuando un tramite se asigna a un abogado, el abogado recibe un aviso
# (campana de la barra superior). Si se reasigna, tambien se avisa al
# abogado anterior. Lo hace un trigger: sirve para cualquier forma de
# asignar (al registrar o desde "Por asignar").
#
# Se ejecuta solo al crear la base. En una base que YA tiene datos se
# aplica asi (no borra nada; se puede repetir sin problema):
#   docker exec scsl_bd bash /docker-entrypoint-initdb.d/07_notificaciones.sh
# ============================================================
set -euo pipefail

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
     -v app_usuario="${APP_BD_USUARIO:-scsl_app}" <<'SQL'
SET client_min_messages = warning;

CREATE TABLE IF NOT EXISTS notificaciones (
    id          BIGSERIAL PRIMARY KEY,
    usuario_id  INT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,   -- destinatario
    tipo        VARCHAR(30) NOT NULL CHECK (tipo IN ('TRAMITE_ASIGNADO', 'TRAMITE_REASIGNADO')),
    titulo      VARCHAR(200) NOT NULL,
    mensaje     TEXT,
    tramite_id  UUID REFERENCES tramites(id) ON DELETE CASCADE,
    creado_por  INT REFERENCES usuarios(id),
    leida_en    TIMESTAMPTZ,
    creado_en   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_notificaciones_usuario ON notificaciones (usuario_id, creado_en DESC);
CREATE INDEX IF NOT EXISTS idx_notificaciones_no_leidas ON notificaciones (usuario_id) WHERE leida_en IS NULL;

-- Avisa al abogado nuevo (y al anterior, si se reasigna).
CREATE OR REPLACE FUNCTION notificar_asignacion() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    v_nuevo     INT;
    v_anterior  INT;
    v_quien     INT := COALESCE(NEW.actualizado_por, NEW.creado_por);
    v_nombre    TEXT;
    v_codigo    TEXT := COALESCE(NEW.hoja_ruta, 'sin hoja de ruta');
BEGIN
    IF NEW.origen_registro <> 'SISTEMA' THEN
        RETURN NULL;
    END IF;
    IF TG_OP = 'UPDATE' AND NEW.profesional_id IS NOT DISTINCT FROM OLD.profesional_id THEN
        RETURN NULL;
    END IF;
    SELECT nombre_completo INTO v_nombre FROM usuarios WHERE id = v_quien;

    IF NEW.profesional_id IS NOT NULL THEN
        SELECT usuario_id INTO v_nuevo FROM profesionales WHERE id = NEW.profesional_id;
        IF v_nuevo IS NOT NULL AND v_nuevo IS DISTINCT FROM v_quien THEN
            INSERT INTO notificaciones (usuario_id, tipo, titulo, mensaje, tramite_id, creado_por)
            VALUES (v_nuevo, 'TRAMITE_ASIGNADO', 'Nuevo trámite asignado: ' || v_codigo,
                    left(NEW.asunto, 300) || ' — Asignado por ' || COALESCE(v_nombre, 'el sistema') || '.',
                    NEW.id, v_quien);
        END IF;
    END IF;

    IF TG_OP = 'UPDATE' AND OLD.profesional_id IS NOT NULL THEN
        SELECT usuario_id INTO v_anterior FROM profesionales WHERE id = OLD.profesional_id;
        IF v_anterior IS NOT NULL AND v_anterior IS DISTINCT FROM v_quien THEN
            INSERT INTO notificaciones (usuario_id, tipo, titulo, mensaje, tramite_id, creado_por)
            VALUES (v_anterior, 'TRAMITE_REASIGNADO', 'Trámite reasignado: ' || v_codigo,
                    'Ya no está a su cargo. Reasignado por ' || COALESCE(v_nombre, 'el sistema') || '.',
                    NEW.id, v_quien);
        END IF;
    END IF;
    RETURN NULL;
END $$;

DROP TRIGGER IF EXISTS trg_tramites_notificar_asignacion ON tramites;
CREATE TRIGGER trg_tramites_notificar_asignacion
    AFTER INSERT OR UPDATE OF profesional_id ON tramites
    FOR EACH ROW EXECUTE FUNCTION notificar_asignacion();

-- Permisos de la cuenta de la aplicacion: leer, crear y marcar como leidas.
GRANT SELECT, INSERT, UPDATE ON notificaciones TO :"app_usuario";
GRANT USAGE, SELECT ON SEQUENCE notificaciones_id_seq TO :"app_usuario";
GRANT EXECUTE ON FUNCTION notificar_asignacion() TO :"app_usuario";
SQL

echo "Repositorio SCSL: notificaciones listas."

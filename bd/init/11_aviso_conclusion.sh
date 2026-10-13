#!/usr/bin/env bash
# ============================================================
# REPOSITORIO SCSL - Paso 11: aviso de trámite concluido.
# Cuando el abogado sube el informe, reciben un aviso (campana y correo)
# los jefes y quien registró y quien asignó el trámite (por lo general la
# secretaria), para que lo revisen y lo archiven. Si sube una versión
# nueva del informe, el aviso dice "Informe actualizado".
#
# Se ejecuta solo al crear la base. En una base que YA tiene datos se
# aplica así (no borra nada; se puede repetir sin problema):
#   docker exec scsl_bd bash /docker-entrypoint-initdb.d/11_aviso_conclusion.sh
# ============================================================
set -euo pipefail

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
     -v app_usuario="${APP_BD_USUARIO:-scsl_app}" <<'SQL'
SET client_min_messages = warning;

ALTER TABLE notificaciones DROP CONSTRAINT IF EXISTS notificaciones_tipo_check;
ALTER TABLE notificaciones ADD CONSTRAINT notificaciones_tipo_check CHECK (tipo IN
    ('TRAMITE_ASIGNADO', 'TRAMITE_REASIGNADO', 'TRAMITE_CONCLUIDO', 'INFORME_ACTUALIZADO'));

-- Corre después de trg_informes_despues_subir (los triggers se ejecutan por orden alfabético):
-- el trámite ya está CONCLUIDO cuando se arma el aviso.
CREATE OR REPLACE FUNCTION notificar_conclusion() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    t          tramites%ROWTYPE;
    v_nombre   TEXT;
    v_version  INT;
    v_codigo   TEXT;
BEGIN
    SELECT * INTO t FROM tramites WHERE id = NEW.tramite_id;
    SELECT nombre_completo INTO v_nombre FROM usuarios WHERE id = NEW.subido_por;
    SELECT count(*) INTO v_version FROM informes WHERE tramite_id = NEW.tramite_id;
    v_codigo := COALESCE(t.numero_documento, t.hoja_ruta, 'sin código');

    INSERT INTO notificaciones (usuario_id, tipo, titulo, mensaje, tramite_id, creado_por)
    SELECT u.id,
           CASE WHEN v_version = 1 THEN 'TRAMITE_CONCLUIDO' ELSE 'INFORME_ACTUALIZADO' END,
           CASE WHEN v_version = 1 THEN 'Trámite concluido, listo para revisar: ' ELSE 'Informe actualizado: ' END || v_codigo,
           COALESCE(v_nombre, 'El abogado') ||
           CASE WHEN v_version = 1 THEN ' subió el informe y concluyó el trámite (HR ' ELSE ' subió la versión ' || v_version || ' del informe (HR ' END
           || COALESCE(t.hoja_ruta, '—') || '). ' || left(COALESCE(t.asunto, ''), 200),
           NEW.tramite_id, NEW.subido_por
      FROM usuarios u JOIN roles r ON r.id = u.rol_id
     WHERE u.activo
       AND u.id IS DISTINCT FROM NEW.subido_por
       AND (r.nombre = 'JEFE' OR u.id = t.asignado_por OR u.id = t.creado_por);
    RETURN NULL;
END $$;

DROP TRIGGER IF EXISTS trg_informes_notificar_conclusion ON informes;
CREATE TRIGGER trg_informes_notificar_conclusion
    AFTER INSERT ON informes
    FOR EACH ROW WHEN (NEW.activo) EXECUTE FUNCTION notificar_conclusion();

GRANT EXECUTE ON FUNCTION notificar_conclusion() TO :"app_usuario";
SQL

echo "Repositorio SCSL: aviso de trámite concluido listo."

#!/usr/bin/env bash
# ============================================================
# REPOSITORIO SCSL - Paso 6 de 6: usuario de la aplicacion y
# primer administrador.
#
# Lee las variables del archivo .env (las pasa docker-compose):
#   APP_BD_USUARIO / APP_BD_CLAVE   -> cuenta con la que la aplicacion se conecta
#   ADMIN_NOMBRE / ADMIN_CORREO / ADMIN_CLAVE -> primer usuario ADMIN del sistema
#
# Las claves se pasan como variables de psql (:'variable'), nunca pegadas
# dentro del SQL, para evitar errores e inyeccion.
# ============================================================
set -euo pipefail

for v in APP_BD_USUARIO APP_BD_CLAVE ADMIN_NOMBRE ADMIN_CORREO ADMIN_CLAVE; do
    if [ -z "${!v:-}" ]; then
        echo "ERROR: falta la variable $v en el archivo .env" >&2
        exit 1
    fi
done

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
     -v app_usuario="$APP_BD_USUARIO" -v app_clave="$APP_BD_CLAVE" -v base="$POSTGRES_DB" \
     -v admin_nombre="$ADMIN_NOMBRE" -v admin_correo="$ADMIN_CORREO" -v admin_clave="$ADMIN_CLAVE" <<'SQL'

-- 1. Cuenta de la aplicacion: puede leer y escribir datos, pero no
--    cambiar la estructura ni borrar la auditoria o los tramites.
CREATE ROLE :"app_usuario" LOGIN PASSWORD :'app_clave';
GRANT CONNECT ON DATABASE :"base" TO :"app_usuario";
GRANT USAGE ON SCHEMA public TO :"app_usuario";
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO :"app_usuario";
GRANT DELETE ON sesiones, codigos_verificacion, precedentes TO :"app_usuario";
REVOKE UPDATE ON auditoria FROM :"app_usuario";
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO :"app_usuario";

-- 2. Primer administrador. Contrasena con bcrypt (pgcrypto); debe
--    cambiarla en su primer ingreso.
INSERT INTO usuarios (nombre_completo, correo, rol_id, hash_contrasena,
                      correo_verificado, debe_cambiar_contrasena)
SELECT :'admin_nombre', lower(:'admin_correo'), r.id,
       crypt(:'admin_clave', gen_salt('bf', 12)), true, true
  FROM roles r WHERE r.nombre = 'ADMIN';

INSERT INTO auditoria (usuario_correo, accion, modulo, objeto_tipo, resultado, detalle)
VALUES ('sistema', 'INSTALAR_BASE', 'SISTEMA', 'base', 'EXITOSO',
        jsonb_build_object('admin_inicial', lower(:'admin_correo')));
SQL

echo "Repositorio SCSL: base lista, usuario de aplicacion y administrador creados."

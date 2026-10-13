#!/usr/bin/env bash
# ============================================================
# REPOSITORIO SCSL - Paso 10: cambio de correo.
# El correo es la identidad para ingresar y recuperar la cuenta: solo se
# cambia probando que la persona recibe correo en la direccion nueva.
# El codigo de 6 digitos (proposito CAMBIO_CORREO) guarda la direccion
# nueva en "dato" hasta que se confirma.
#
# Se ejecuta solo al crear la base. En una base que YA tiene datos se
# aplica asi (no borra nada; se puede repetir sin problema):
#   docker exec scsl_bd bash /docker-entrypoint-initdb.d/10_cambio_correo.sh
# ============================================================
set -euo pipefail

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<'SQL'
SET client_min_messages = warning;

ALTER TABLE codigos_verificacion ADD COLUMN IF NOT EXISTS dato VARCHAR(150);  -- correo nuevo pendiente

ALTER TABLE codigos_verificacion DROP CONSTRAINT IF EXISTS codigos_verificacion_proposito_check;
ALTER TABLE codigos_verificacion ADD CONSTRAINT codigos_verificacion_proposito_check
    CHECK (proposito IN ('ACTIVACION', 'RECUPERACION', 'CAMBIO_CORREO'));
ALTER TABLE codigos_verificacion DROP CONSTRAINT IF EXISTS ck_codigos_dato;
ALTER TABLE codigos_verificacion ADD CONSTRAINT ck_codigos_dato
    CHECK (proposito <> 'CAMBIO_CORREO' OR dato ~* '^[^@\s]+@[^@\s]+\.[^@\s]+$');
SQL

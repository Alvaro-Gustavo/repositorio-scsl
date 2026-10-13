-- ============================================================
-- REPOSITORIO SCSL - Prueba de las reglas de negocio.
--
-- Crea datos de ejemplo, prueba cada regla y al final DESHACE todo
-- (ROLLBACK): la base queda igual que antes. Uso con Docker:
--   docker exec -i scsl_bd psql -U postgres -d repositorio_scsl < bd/pruebas/prueba_reglas.sql
-- Si todo esta bien, el ultimo mensaje es: TODAS LAS PRUEBAS PASARON
-- ============================================================
\set ON_ERROR_STOP 1
SET client_min_messages = notice;
BEGIN;

-- Ayudante: ejecuta una sentencia que DEBE fallar con el mensaje esperado.
CREATE FUNCTION pg_temp.debe_fallar(p_sql TEXT, p_mensaje TEXT) RETURNS VOID LANGUAGE plpgsql AS $$
BEGIN
    EXECUTE p_sql;
    RAISE EXCEPTION 'PRUEBA FALLIDA: se esperaba el error "%"', p_mensaje;
EXCEPTION WHEN OTHERS THEN
    IF SQLERRM LIKE 'PRUEBA FALLIDA%' OR position(p_mensaje IN SQLERRM) = 0 THEN
        RAISE EXCEPTION 'PRUEBA FALLIDA: % (se esperaba "%")', SQLERRM, p_mensaje;
    END IF;
    RAISE NOTICE 'ok: rechazado -> %', SQLERRM;
END $$;

CREATE FUNCTION pg_temp.verificar(p_condicion BOOLEAN, p_descripcion TEXT) RETURNS VOID LANGUAGE plpgsql AS $$
BEGIN
    IF NOT coalesce(p_condicion, false) THEN
        RAISE EXCEPTION 'PRUEBA FALLIDA: %', p_descripcion;
    END IF;
    RAISE NOTICE 'ok: %', p_descripcion;
END $$;

-- ---------- Datos de ejemplo ----------
INSERT INTO usuarios (id, nombre_completo, correo, rol_id, hash_contrasena)
SELECT v.id, v.nombre, v.correo, r.id, 'x'
  FROM (VALUES (901, 'Jefe Prueba', 'jefe@prueba.bo', 'JEFE'),
               (902, 'Dra. Zenteno', 'zenteno@prueba.bo', 'ABOGADO'),
               (903, 'Dra. Ampuero', 'ampuero@prueba.bo', 'ABOGADO'),
               (904, 'Secretaria Prueba', 'secretaria@prueba.bo', 'SECRETARIA')) AS v(id, nombre, correo, rol)
  JOIN roles r ON r.nombre = v.rol;

INSERT INTO profesionales (id, nombre_completo, usuario_id) VALUES
    (901, 'DRA. ZENTENO', 902), (902, 'DRA. AMPUERO', 903),
    (903, 'DR. HISTORICO SIN CUENTA', NULL);
INSERT INTO entidades (id, nombre) VALUES (901, 'Gobierno Autónomo Departamental de La Paz');
INSERT INTO tipos_tramite (id, nombre) VALUES (901, 'Verificación de contratos');
INSERT INTO tipos_documento (id, nombre) VALUES (901, 'Informe');

-- ---------- 1. Catalogos sin duplicados ----------
SELECT pg_temp.debe_fallar($$INSERT INTO tipos_documento (nombre) VALUES ('  INFORMÉ ')$$, 'duplicate key');

-- ---------- 2. Registro ----------
SELECT pg_temp.debe_fallar($$INSERT INTO tramites (hoja_ruta, procedencia_id, entidad_id, tipo_tramite_id, asunto, creado_por)
    VALUES ('HR-1', 1, 901, 901, 'Asunto', 902)$$, 'No tiene permiso para registrar');
SELECT pg_temp.debe_fallar($$INSERT INTO tramites (hoja_ruta, procedencia_id, tipo_tramite_id, asunto, creado_por)
    VALUES ('HR-1', 1, 901, 'Asunto', 904)$$, 'ck_tramites_registro_completo');

INSERT INTO tramites (id, hoja_ruta, registro_interno, procedencia_id, entidad_id, tipo_tramite_id, asunto, creado_por)
VALUES ('00000000-0000-0000-0000-000000000001', 'CGE/GSL/INF-006/2026', 'GAAJ/1572', 1, 901, 901,
        'Verificación de contrato de obra con ampliación de plazo', 904);
SELECT pg_temp.verificar((SELECT estado_tramite = 'RECIBIDO' AND anio_gestion = EXTRACT(YEAR FROM current_date)
                            FROM tramites WHERE hoja_ruta = 'CGE/GSL/INF-006/2026'),
                         'tramite nuevo queda RECIBIDO con el anio actual');

-- ---------- 3. Asignacion ----------
SELECT pg_temp.debe_fallar($$UPDATE tramites SET profesional_id = 903, actualizado_por = 904
    WHERE id = '00000000-0000-0000-0000-000000000001'$$, 'cuenta activa');
SELECT pg_temp.debe_fallar($$UPDATE tramites SET profesional_id = 901, actualizado_por = 902
    WHERE id = '00000000-0000-0000-0000-000000000001'$$, 'No tiene permiso para asignar');
UPDATE tramites SET profesional_id = 901, actualizado_por = 904 WHERE id = '00000000-0000-0000-0000-000000000001';
SELECT pg_temp.verificar((SELECT estado_tramite = 'EN_ELABORACION' AND asignado_por = 904 AND fecha_asignacion IS NOT NULL
                            FROM tramites WHERE id = '00000000-0000-0000-0000-000000000001'),
                         'al asignar pasa a EN_ELABORACION y guarda quien asigno');
SELECT pg_temp.verificar((SELECT count(*) = 1 FROM v_pendientes WHERE abogado_usuario_id = 902),
                         'aparece en los pendientes de la abogada');

-- ---------- 4. Conclusion ----------
SELECT pg_temp.debe_fallar($$UPDATE tramites SET estado_tramite = 'CONCLUIDO'
    WHERE id = '00000000-0000-0000-0000-000000000001'$$, 'sube el informe');
SELECT pg_temp.debe_fallar($$INSERT INTO informes (tramite_id, ruta_archivo, nombre_original, tamano_bytes, huella_sha256, subido_por)
    VALUES ('00000000-0000-0000-0000-000000000001', 'a.pdf', 'a.pdf', 10, repeat('a', 64), 902)$$, 'tipo y el numero');
UPDATE tramites SET tipo_documento_id = 901, numero_documento = 'CGE/SCSL/GAAJ/C-166/2026', actualizado_por = 902
 WHERE id = '00000000-0000-0000-0000-000000000001';
SELECT pg_temp.debe_fallar($$INSERT INTO informes (tramite_id, ruta_archivo, nombre_original, tamano_bytes, huella_sha256, subido_por)
    VALUES ('00000000-0000-0000-0000-000000000001', 'a.pdf', 'a.pdf', 10, repeat('a', 64), 903)$$, 'Solo el abogado asignado');
SELECT pg_temp.debe_fallar($$INSERT INTO informes (tramite_id, ruta_archivo, nombre_original, tamano_bytes, huella_sha256, subido_por)
    VALUES ('00000000-0000-0000-0000-000000000001', 'a.pdf', 'a.pdf', 10, repeat('a', 64), 901)$$, 'Solo el abogado asignado');
INSERT INTO informes (tramite_id, ruta_archivo, nombre_original, tamano_bytes, huella_sha256, subido_por, texto_extraido)
VALUES ('00000000-0000-0000-0000-000000000001', '2026/10/a.pdf', 'informe.pdf', 1000, repeat('a', 64), 902,
        'Conclusión: procede la ampliación de plazo conforme al Decreto Supremo 0181.');
SELECT pg_temp.verificar((SELECT estado_tramite = 'CONCLUIDO' AND fecha_salida = current_date AND fecha_conclusion IS NOT NULL
                            FROM tramites WHERE id = '00000000-0000-0000-0000-000000000001'),
                         'al subir el informe queda CONCLUIDO con fecha de salida');
INSERT INTO informes (tramite_id, ruta_archivo, nombre_original, tamano_bytes, huella_sha256, subido_por)
VALUES ('00000000-0000-0000-0000-000000000001', '2026/10/b.pdf', 'informe-v2.pdf', 1200, repeat('b', 64), 902);
SELECT pg_temp.verificar((SELECT count(*) FILTER (WHERE activo) = 1 AND count(*) = 2
                            FROM informes WHERE tramite_id = '00000000-0000-0000-0000-000000000001'),
                         'al resubir queda un solo informe activo y se conserva el anterior');
SELECT pg_temp.debe_fallar($$UPDATE tramites SET profesional_id = 902, actualizado_por = 901
    WHERE id = '00000000-0000-0000-0000-000000000001'$$, 'concluido');

-- ---------- 5. Archivo ----------
SELECT pg_temp.debe_fallar($$UPDATE tramites SET estado_tramite = 'ARCHIVADO', actualizado_por = 904
    WHERE id = '00000000-0000-0000-0000-000000000001'$$, 'No tiene permiso para archivar');
UPDATE tramites SET estado_tramite = 'ARCHIVADO', actualizado_por = 901 WHERE id = '00000000-0000-0000-0000-000000000001';
SELECT pg_temp.verificar((SELECT estado_tramite = 'ARCHIVADO' FROM tramites WHERE id = '00000000-0000-0000-0000-000000000001'),
                         'el jefe archiva un tramite concluido');

-- ---------- 6. Busqueda (sin tildes, incluye el texto del informe activo) ----------
UPDATE informes SET texto_extraido = 'Conclusión: procede la ampliación de plazo conforme al Decreto Supremo 0181.'
 WHERE tramite_id = '00000000-0000-0000-0000-000000000001' AND activo;
SELECT pg_temp.verificar((SELECT count(*) = 1 FROM tramites
                           WHERE vector_busqueda @@ websearch_to_tsquery('es_legal', 'ampliacion decreto 0181')),
                         'la busqueda sin tildes encuentra el texto del informe');
SELECT pg_temp.verificar((SELECT count(*) = 1 FROM tramites WHERE numero_documento ILIKE '%C-166%'),
                         'la busqueda parcial por numero de documento funciona');

-- ---------- 7. Catalogo de prompts ----------
SELECT pg_temp.debe_fallar($$INSERT INTO prompts (titulo, categoria, texto, propuesto_por)
    VALUES ('X', 'CONSULTA', 'texto', 904)$$, 'No tiene permiso para proponer');
SELECT pg_temp.debe_fallar($$INSERT INTO prompts (titulo, categoria, texto, propuesto_por, estado)
    VALUES ('X', 'CONSULTA', 'texto', 902, 'VIGENTE')$$, 'Solo el jefe aprueba');
INSERT INTO prompts (id, titulo, categoria, tipo_documento_id, texto, instrucciones, propuesto_por)
VALUES (901, 'Extraer criterio legal de un informe', 'PRECEDENTE', 901,
        'Actua como abogado de la Contraloria. Del informe que pego a continuacion, redacta el criterio legal aplicado en maximo 5 lineas.',
        'Pegue despues el texto del informe sin datos personales.', 902);
SELECT pg_temp.debe_fallar($$SELECT registrar_uso_prompt(901, 904)$$, 'no esta vigente');
UPDATE prompts SET estado = 'VIGENTE', actualizado_por = 901 WHERE id = 901;
SELECT pg_temp.verificar((SELECT aprobado_por = 901 AND aprobado_en IS NOT NULL FROM prompts WHERE id = 901),
                         'el jefe aprueba el prompt');
SELECT pg_temp.debe_fallar($$UPDATE prompts SET texto = 'otro', actualizado_por = 902 WHERE id = 901$$, 'Solo el jefe modifica');
SELECT registrar_uso_prompt(901, 904, '00000000-0000-0000-0000-000000000001');
SELECT pg_temp.verificar((SELECT usos = 1 FROM prompts WHERE id = 901)
                     AND (SELECT count(*) = 1 FROM auditoria WHERE accion = 'COPIAR_PROMPT' AND usuario_id = 904),
                         'copiar un prompt suma un uso y queda en la auditoria');
SELECT pg_temp.verificar((SELECT count(*) = 1 FROM v_prompts_vigentes WHERE tipo_documento = 'Informe'),
                         'el prompt aparece en el catalogo por tipo de documento');

-- ---------- 8. Precedentes ----------
INSERT INTO tramites (id, hoja_ruta, procedencia_id, entidad_id, tipo_tramite_id, asunto, creado_por)
VALUES ('00000000-0000-0000-0000-000000000002', 'CGE/GSL/INF-010/2026', 1, 901, 901,
        'Ampliación de plazo en contrato de obra pública', 904);
INSERT INTO precedentes (tramite_id, tramite_precedente_id, criterio_legal, relevancia, creado_por)
VALUES ('00000000-0000-0000-0000-000000000002', '00000000-0000-0000-0000-000000000001',
        'Procede la ampliación por causas ajenas al contratista', 'VINCULANTE', 902);
SELECT pg_temp.verificar((SELECT count(*) = 1 FROM cadena_precedentes('00000000-0000-0000-0000-000000000001')
                           WHERE direccion = 'ES_CITADO_POR'),
                         'la cadena de precedentes muestra quien cita al tramite');
SELECT pg_temp.verificar((SELECT count(*) >= 1 FROM tramites_similares('00000000-0000-0000-0000-000000000002')),
                         'tramites similares sugiere el tramite con asunto parecido');
SELECT pg_temp.debe_fallar($$INSERT INTO precedentes (tramite_id, tramite_precedente_id, criterio_legal, relevancia, creado_por)
    VALUES ('00000000-0000-0000-0000-000000000002', '00000000-0000-0000-0000-000000000002', 'x', 'VINCULANTE', 902)$$,
    'ck_precedentes_distintos');

-- ---------- 9. Tablero ----------
SELECT pg_temp.verificar((SELECT concluidos = 1 FROM v_tablero_por_abogado WHERE abogado = 'DRA. ZENTENO'),
                         'el tablero cuenta el concluido de la abogada');

-- ---------- 10. Auditoria inmutable y permisos de la cuenta de la aplicacion ----------
SELECT pg_temp.debe_fallar($$UPDATE auditoria SET accion = 'X'$$, 'no puede modificarse');
SELECT pg_temp.debe_fallar($$DELETE FROM auditoria$$, 'no puede modificarse');
SET LOCAL ROLE scsl_app;
SELECT pg_temp.debe_fallar($$DELETE FROM auditoria$$, 'permission denied');
SELECT pg_temp.debe_fallar($$DELETE FROM tramites$$, 'permission denied');
SELECT pg_temp.debe_fallar($$DROP TABLE prompts$$, 'must be owner');
SELECT pg_temp.verificar((SELECT count(*) = 4 FROM roles), 'la aplicacion puede leer los datos');
RESET ROLE;

DO $$ BEGIN RAISE NOTICE '=== TODAS LAS PRUEBAS PASARON ==='; END $$;
ROLLBACK;

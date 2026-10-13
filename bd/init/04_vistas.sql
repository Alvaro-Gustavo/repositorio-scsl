-- ============================================================
-- REPOSITORIO SCSL - Paso 4 de 6: vistas.
-- Una vista es una consulta guardada con nombre: la aplicacion la
-- lee como si fuera una tabla.
-- ============================================================

-- Tramite con los nombres de sus catalogos: listados, resultados de
-- busqueda, impresion y reportes.
CREATE VIEW v_tramites AS
SELECT t.id, t.hoja_ruta, t.registro_interno, t.anio_gestion,
       pr.nombre AS procedencia, e.nombre AS entidad, tt.nombre AS tipo_tramite,
       t.asunto, pf.nombre_completo AS abogado,
       td.nombre AS tipo_documento, t.numero_documento, t.fecha_salida,
       ar.nombre AS area, t.observaciones,
       t.estado_tramite, t.fecha_asignacion, t.fecha_conclusion,
       EXISTS (SELECT 1 FROM informes i WHERE i.tramite_id = t.id AND i.activo) AS tiene_informe,
       (SELECT count(*) FROM precedentes p WHERE p.tramite_id = t.id) AS cantidad_precedentes,
       t.activo, t.origen_registro,
       t.procedencia_id, t.entidad_id, t.tipo_tramite_id, t.profesional_id, t.tipo_documento_id, t.area_id,
       t.creado_por, t.creado_en, t.actualizado_en
  FROM tramites t
  LEFT JOIN procedencias pr    ON pr.id = t.procedencia_id
  LEFT JOIN entidades e        ON e.id  = t.entidad_id
  LEFT JOIN tipos_tramite tt   ON tt.id = t.tipo_tramite_id
  LEFT JOIN profesionales pf   ON pf.id = t.profesional_id
  LEFT JOIN tipos_documento td ON td.id = t.tipo_documento_id
  LEFT JOIN areas ar           ON ar.id = t.area_id;

-- Bandeja "Mis pendientes" del abogado y control de plazos del jefe.
-- "vencido" se calcula con la clave plazo_dias_tramite de la tabla
-- configuracion (dias calendario). Vacia = sin control de plazo.
CREATE VIEW v_pendientes AS
SELECT t.id, t.hoja_ruta, t.asunto, e.nombre AS entidad, tt.nombre AS tipo_tramite,
       t.profesional_id, pf.nombre_completo AS abogado, pf.usuario_id AS abogado_usuario_id,
       t.fecha_asignacion,
       current_date - t.fecha_asignacion::date AS dias_en_elaboracion,
       COALESCE(current_date - t.fecha_asignacion::date >
                NULLIF((SELECT valor FROM configuracion WHERE clave = 'plazo_dias_tramite'), '')::int,
                false) AS vencido
  FROM tramites t
  JOIN profesionales pf      ON pf.id = t.profesional_id
  LEFT JOIN entidades e      ON e.id  = t.entidad_id
  LEFT JOIN tipos_tramite tt ON tt.id = t.tipo_tramite_id
 WHERE t.activo AND t.estado_tramite = 'EN_ELABORACION';

-- ============================================================
-- TABLERO DEL JEFE (permiso VER_TABLERO)
-- v_tablero_base tiene un renglon por tramite activo; las otras tres
-- lo resumen por abogado, por anio y por tipo de documento.
-- La aplicacion filtra con WHERE (ej. WHERE anio_gestion = 2026).
-- ============================================================
CREATE VIEW v_tablero_base AS
SELECT t.id, t.anio_gestion,
       t.profesional_id, COALESCE(pf.nombre_completo, 'SIN ASIGNAR') AS abogado,
       t.tipo_documento_id, COALESCE(td.nombre, 'SIN TIPO') AS tipo_documento,
       t.tipo_tramite_id, COALESCE(tt.nombre, 'SIN TIPO') AS tipo_tramite,
       t.estado_tramite, t.origen_registro,
       CASE WHEN t.fecha_asignacion IS NOT NULL AND t.fecha_conclusion IS NOT NULL
            THEN t.fecha_conclusion::date - t.fecha_asignacion::date END AS dias_elaboracion,
       CASE WHEN t.estado_tramite = 'EN_ELABORACION' AND t.fecha_asignacion IS NOT NULL
            THEN current_date - t.fecha_asignacion::date END AS dias_en_curso
  FROM tramites t
  LEFT JOIN profesionales pf   ON pf.id = t.profesional_id
  LEFT JOIN tipos_documento td ON td.id = t.tipo_documento_id
  LEFT JOIN tipos_tramite tt   ON tt.id = t.tipo_tramite_id
 WHERE t.activo;

CREATE VIEW v_tablero_por_abogado AS
SELECT profesional_id, abogado,
       count(*) AS total,
       count(*) FILTER (WHERE estado_tramite = 'EN_ELABORACION') AS en_elaboracion,
       count(*) FILTER (WHERE estado_tramite IN ('CONCLUIDO', 'ARCHIVADO')) AS concluidos,
       round(100.0 * count(*) FILTER (WHERE estado_tramite IN ('CONCLUIDO', 'ARCHIVADO')) / count(*), 1) AS porcentaje_avance,
       round(avg(dias_elaboracion), 1) AS promedio_dias_elaboracion,
       max(dias_en_curso) AS dias_pendiente_mas_antiguo
  FROM v_tablero_base
 GROUP BY profesional_id, abogado;

CREATE VIEW v_tablero_por_anio AS
SELECT anio_gestion,
       count(*) AS total,
       count(*) FILTER (WHERE estado_tramite = 'RECIBIDO') AS sin_asignar,
       count(*) FILTER (WHERE estado_tramite = 'EN_ELABORACION') AS en_elaboracion,
       count(*) FILTER (WHERE estado_tramite IN ('CONCLUIDO', 'ARCHIVADO')) AS concluidos,
       round(100.0 * count(*) FILTER (WHERE estado_tramite IN ('CONCLUIDO', 'ARCHIVADO')) / count(*), 1) AS porcentaje_avance,
       round(avg(dias_elaboracion), 1) AS promedio_dias_elaboracion
  FROM v_tablero_base
 GROUP BY anio_gestion;

CREATE VIEW v_tablero_por_tipo_documento AS
SELECT tipo_documento_id, tipo_documento,
       count(*) AS total,
       count(*) FILTER (WHERE estado_tramite = 'RECIBIDO') AS sin_asignar,
       count(*) FILTER (WHERE estado_tramite = 'EN_ELABORACION') AS en_elaboracion,
       count(*) FILTER (WHERE estado_tramite IN ('CONCLUIDO', 'ARCHIVADO')) AS concluidos,
       round(100.0 * count(*) FILTER (WHERE estado_tramite IN ('CONCLUIDO', 'ARCHIVADO')) / count(*), 1) AS porcentaje_avance,
       round(avg(dias_elaboracion), 1) AS promedio_dias_elaboracion
  FROM v_tablero_base
 GROUP BY tipo_documento_id, tipo_documento;

-- Catalogo de prompts que ven los usuarios (solo los vigentes).
CREATE VIEW v_prompts_vigentes AS
SELECT p.id, p.titulo, p.categoria,
       p.tipo_documento_id, COALESCE(td.nombre, 'GENERAL') AS tipo_documento,
       p.texto, p.instrucciones, p.usos, p.aprobado_en
  FROM prompts p
  LEFT JOIN tipos_documento td ON td.id = p.tipo_documento_id
 WHERE p.estado = 'VIGENTE';

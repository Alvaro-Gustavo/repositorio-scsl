# Tablero del jefe (VER_TABLERO) y resumen de la pantalla de inicio.
from fastapi import APIRouter, Depends

from ..bd import conexion, parametro, todos, uno
from ..seguridad import Usuario, requiere, usuario_actual
from ..tramites import lista
from .prompts import SQL_PROMPT

rutas = APIRouter()

# Resumen de v_tablero_base agrupado por una columna (fija, del código).
SQL_GRUPO = '''
SELECT {clave} AS clave, {nombre} AS nombre, count(*)::int AS total,
       count(*) FILTER (WHERE estado_tramite = 'RECIBIDO')::int AS sin_asignar,
       count(*) FILTER (WHERE estado_tramite = 'EN_ELABORACION')::int AS en_elaboracion,
       count(*) FILTER (WHERE estado_tramite IN ('CONCLUIDO', 'ARCHIVADO'))::int AS concluidos,
       round(100.0 * count(*) FILTER (WHERE estado_tramite IN ('CONCLUIDO', 'ARCHIVADO')) / count(*), 1)::float AS porcentaje_avance,
       round(avg(dias_elaboracion), 1)::float AS promedio_dias_elaboracion,
       max(dias_en_curso) AS dias_pendiente_mas_antiguo
  FROM v_tablero_base
 WHERE (%(anio)s::int IS NULL OR anio_gestion = %(anio)s::int)
 GROUP BY 1, 2
 ORDER BY {orden}'''


def _grupo(con, anio, clave, nombre, orden='total DESC'):
    return todos(con, SQL_GRUPO.format(clave=clave, nombre=nombre, orden=orden), {'anio': anio})


@rutas.get('/tablero')
def resumen(anio: str = '', u: Usuario = Depends(requiere('VER_TABLERO')), con=Depends(conexion)):
    anio = int(anio) if anio.isdigit() else None
    plazo = parametro(con, 'plazo_dias_tramite')
    p = {'anio': anio, 'plazo': plazo}
    totales = uno(con, '''
        SELECT count(*)::int AS total,
               count(*) FILTER (WHERE estado_tramite = 'RECIBIDO')::int AS "RECIBIDO",
               count(*) FILTER (WHERE estado_tramite = 'EN_ELABORACION')::int AS "EN_ELABORACION",
               count(*) FILTER (WHERE estado_tramite = 'CONCLUIDO')::int AS "CONCLUIDO",
               count(*) FILTER (WHERE estado_tramite = 'ARCHIVADO')::int AS "ARCHIVADO",
               count(*) FILTER (WHERE anio_gestion = extract(year FROM current_date))::int AS gestion_actual,
               count(*) FILTER (WHERE estado_tramite = 'EN_ELABORACION' AND %(plazo)s::int IS NOT NULL
                                  AND current_date - fecha_asignacion::date > %(plazo)s::int)::int AS vencidos
          FROM tramites WHERE activo AND (%(anio)s::int IS NULL OR anio_gestion = %(anio)s::int)''', p)
    por_mes = todos(con, '''
        SELECT to_char(m, 'YYYY-MM') AS mes,
               (SELECT count(*) FROM tramites t WHERE t.activo AND date_trunc('month', t.creado_en) = m)::int AS registrados,
               (SELECT count(*) FROM tramites t WHERE t.activo AND date_trunc('month', t.fecha_conclusion) = m)::int AS concluidos
          FROM generate_series(date_trunc('month', now()) - interval '11 months', date_trunc('month', now()),
                               interval '1 month') m''')
    vencidos = []
    if plazo is not None:
        vencidos = lista(con, '''t.activo AND t.estado_tramite = 'EN_ELABORACION'
                                 AND current_date - t.fecha_asignacion::date > %(plazo)s
                                 AND (%(anio)s::int IS NULL OR t.anio_gestion = %(anio)s::int)''',
                         {'anio': anio}, 't.fecha_asignacion ASC', con_plazo=True)
    return {
        'plazo_dias': plazo,
        'anios': [f['anio_gestion'] for f in todos(con, 'SELECT DISTINCT anio_gestion FROM tramites ORDER BY 1 DESC')],
        'totales': totales,
        'por_abogado': _grupo(con, anio, 'COALESCE(profesional_id, 0)', 'abogado'),
        'por_anio': _grupo(con, anio, 'anio_gestion', 'anio_gestion::text', 'clave ASC'),
        'por_tipo_documento': _grupo(con, anio, 'COALESCE(tipo_documento_id, 0)',
                                     "CASE WHEN tipo_documento_id IS NULL THEN 'Sin tipo (pendientes)' ELSE tipo_documento END"),
        'por_tipo_tramite': _grupo(con, anio, 'COALESCE(tipo_tramite_id, 0)',
                                   "CASE WHEN tipo_tramite_id IS NULL THEN 'Sin tipo' ELSE tipo_tramite END"),
        'por_mes': por_mes,
        'vencidos': vencidos,
    }


@rutas.get('/inicio')
def inicio(u: Usuario = Depends(usuario_actual), con=Depends(conexion)):
    totales = uno(con, '''
        SELECT count(*) FILTER (WHERE t.activo)::int AS total,
               count(*) FILTER (WHERE t.activo AND t.anio_gestion = extract(year FROM current_date))::int AS gestion_actual,
               count(*) FILTER (WHERE t.activo AND t.estado_tramite = 'EN_ELABORACION')::int AS en_elaboracion,
               count(*) FILTER (WHERE t.activo AND t.estado_tramite = 'RECIBIDO')::int AS por_asignar,
               count(*) FILTER (WHERE t.activo AND date_trunc('month', t.fecha_conclusion) = date_trunc('month', now()))::int AS concluidos_mes,
               (SELECT count(*) FROM prompts WHERE estado = 'VIGENTE')::int AS prompts_vigentes,
               (SELECT count(*) FROM prompts WHERE estado = 'BORRADOR')::int AS prompts_por_revisar
          FROM tramites t''')
    return {
        'rol': u.rol,
        'totales': totales,
        'mis_pendientes': lista(con, "t.activo AND t.estado_tramite = 'EN_ELABORACION' AND pf.usuario_id = %(yo)s",
                                {'yo': u.id}, 't.fecha_asignacion ASC', con_plazo=True),
        'registrados_por_mi': lista(con, 't.activo AND t.creado_por = %(yo)s', {'yo': u.id}, 't.creado_en DESC',
                                    limite=5),
        'recientes': lista(con, 't.activo AND EXISTS (SELECT 1 FROM informes i WHERE i.tramite_id = t.id AND i.activo)',
                           None, 'COALESCE(t.fecha_conclusion, t.fecha_salida::timestamptz) DESC NULLS LAST', limite=5),
        'prompts_mas_usados': todos(con, SQL_PROMPT + " WHERE p.estado = 'VIGENTE' ORDER BY p.usos DESC LIMIT 3"),
    }

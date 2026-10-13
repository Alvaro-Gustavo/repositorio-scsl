# Forma de un trámite en las respuestas (la misma que expandir() del modo simulado).
import uuid

from .bd import parametro, todos, uno
from .errores import ErrorApi
from .seguridad import Usuario

# Columnas del trámite con sus catálogos como {id, nombre} y personas como {id, nombre_completo}.
SQL_TRAMITE = '''
SELECT t.id, t.hoja_ruta, t.registro_interno, t.anio_gestion,
       CASE WHEN pr.id IS NULL THEN NULL ELSE json_build_object('id', pr.id, 'nombre', pr.nombre) END AS procedencia,
       CASE WHEN e.id  IS NULL THEN NULL ELSE json_build_object('id', e.id,  'nombre', e.nombre)  END AS entidad,
       CASE WHEN tt.id IS NULL THEN NULL ELSE json_build_object('id', tt.id, 'nombre', tt.nombre) END AS tipo_tramite,
       t.asunto,
       CASE WHEN pf.id IS NULL THEN NULL
            ELSE json_build_object('id', pf.id, 'nombre_completo', pf.nombre_completo, 'usuario_id', pf.usuario_id) END AS profesional,
       CASE WHEN td.id IS NULL THEN NULL ELSE json_build_object('id', td.id, 'nombre', td.nombre) END AS tipo_documento,
       t.numero_documento, t.fecha_salida,
       CASE WHEN ar.id IS NULL THEN NULL ELSE json_build_object('id', ar.id, 'nombre', ar.nombre) END AS area,
       t.observaciones, t.estado_tramite, t.motivo_baja AS baja_motivo,
       CASE WHEN ua.id IS NULL THEN NULL ELSE json_build_object('id', ua.id, 'nombre_completo', ua.nombre_completo) END AS asignado_por,
       t.fecha_asignacion, t.fecha_conclusion, t.activo, t.origen_registro,
       CASE WHEN uc.id IS NULL THEN NULL ELSE json_build_object('id', uc.id, 'nombre_completo', uc.nombre_completo) END AS creado_por,
       t.creado_en, t.actualizado_en,
       EXISTS (SELECT 1 FROM informes i WHERE i.tramite_id = t.id AND i.activo) AS tiene_informe,
       (SELECT count(*) FROM precedentes p WHERE p.tramite_id = t.id)::int AS cantidad_precedentes
  FROM tramites t
  LEFT JOIN procedencias pr    ON pr.id = t.procedencia_id
  LEFT JOIN entidades e        ON e.id  = t.entidad_id
  LEFT JOIN tipos_tramite tt   ON tt.id = t.tipo_tramite_id
  LEFT JOIN profesionales pf   ON pf.id = t.profesional_id
  LEFT JOIN tipos_documento td ON td.id = t.tipo_documento_id
  LEFT JOIN areas ar           ON ar.id = t.area_id
  LEFT JOIN usuarios ua        ON ua.id = t.asignado_por
  LEFT JOIN usuarios uc        ON uc.id = t.creado_por
'''

# Columnas extra para las bandejas: días en elaboración y si venció el plazo.
SQL_PLAZO = '''(current_date - t.fecha_asignacion::date) AS dias_en_elaboracion,
       COALESCE(current_date - t.fecha_asignacion::date > %(plazo)s, false) AS vencido'''

ACCIONES_HISTORIAL = ('CREAR_TRAMITE', 'EDITAR_TRAMITE', 'ASIGNAR_TRAMITE', 'SUBIR_INFORME',
                      'ARCHIVAR_TRAMITE', 'BAJA_TRAMITE')


def id_valido(id_):
    try:
        return str(uuid.UUID(str(id_)))
    except ValueError:
        raise ErrorApi('El trámite no existe.', 404)


def fila_tramite(con, id_):
    """Fila cruda de la tabla tramites (para verificar reglas)."""
    t = uno(con, '''SELECT t.*, pf.usuario_id AS abogado_usuario_id
                      FROM tramites t LEFT JOIN profesionales pf ON pf.id = t.profesional_id
                     WHERE t.id = %s''', (id_valido(id_),))
    if not t:
        raise ErrorApi('El trámite no existe.', 404)
    return t


def resumen(con, id_):
    t = uno(con, SQL_TRAMITE + ' WHERE t.id = %s', (id_valido(id_),))
    if not t:
        raise ErrorApi('El trámite no existe.', 404)
    return t


def lista(con, donde='TRUE', parametros=None, orden='t.creado_en DESC', con_plazo=False, extra=None,
          limite=None, salto=0):
    """Varios trámites con la forma base. donde/orden/extra son SQL fijo del código, nunca del
    usuario: los valores van siempre como parámetros con nombre."""
    p = dict(parametros or {})
    columnas = [extra] if extra else []
    if con_plazo:
        columnas.append(SQL_PLAZO)
        p['plazo'] = parametro(con, 'plazo_dias_tramite')
    consulta = SQL_TRAMITE
    if columnas:
        consulta = consulta.replace('\n  FROM tramites t', ', ' + ', '.join(columnas) + '\n  FROM tramites t', 1)
    consulta += f' WHERE {donde} ORDER BY {orden}'
    if limite:
        consulta += f' LIMIT {int(limite)} OFFSET {int(salto)}'
    return todos(con, consulta, p)


def permisos_tramite(t, u: Usuario):
    """Qué puede hacer el usuario con el trámite (misma lógica que la base y el frontend)."""
    es_asignado = t['abogado_usuario_id'] is not None and t['abogado_usuario_id'] == u.id
    es_propio = t['creado_por'] == u.id or es_asignado
    activo_sistema = t['activo'] and t['origen_registro'] == 'SISTEMA'
    return {
        'editar': bool(t['activo'] and (u.puede('EDITAR_TODOS') or (u.puede('EDITAR_PROPIOS') and es_propio))
                       and t['estado_tramite'] != 'ARCHIVADO'),
        'asignar': bool(activo_sistema and u.puede('ASIGNAR_TRAMITE')
                        and t['estado_tramite'] in ('RECIBIDO', 'EN_ELABORACION')),
        'concluir': bool(t['activo'] and t['estado_tramite'] in ('EN_ELABORACION', 'CONCLUIDO')
                         and ((es_asignado and u.puede('SUBIR_INFORME')) or u.rol == 'ADMIN')),
        'archivar': bool(activo_sistema and t['estado_tramite'] == 'CONCLUIDO' and u.puede('ARCHIVAR_TRAMITE')),
        'baja': bool(t['activo'] and u.puede('ELIMINAR_LOGICO')),
        'descargar': False,  # se completa con el informe
        'precedentes': bool(t['activo'] and u.puede('GESTIONAR_PRECEDENTES')),
    }


SQL_RESUMEN_OTRO = '''json_build_object('id', o.id, 'hoja_ruta', o.hoja_ruta, 'numero_documento', o.numero_documento,
        'asunto', o.asunto, 'fecha_salida', o.fecha_salida, 'estado_tramite', o.estado_tramite,
        'entidad', CASE WHEN e.id IS NULL THEN NULL ELSE json_build_object('id', e.id, 'nombre', e.nombre) END,
        'tiene_informe', EXISTS (SELECT 1 FROM informes i WHERE i.tramite_id = o.id AND i.activo))'''


def _precedentes(con, id_, campo_propio, campo_otro):
    return todos(con, f'''
        SELECT p.id, {SQL_RESUMEN_OTRO} AS tramite, p.criterio_legal, p.relevancia, p.tipo_relacion, p.origen,
               p.observaciones, p.creado_en,
               json_build_object('id', uc.id, 'nombre_completo', uc.nombre_completo) AS creado_por
          FROM precedentes p
          JOIN tramites o ON o.id = p.{campo_otro}
          LEFT JOIN entidades e ON e.id = o.entidad_id
          JOIN usuarios uc ON uc.id = p.creado_por
         WHERE p.{campo_propio} = %s
         ORDER BY p.creado_en''', (id_,))


def detalle(con, id_, u: Usuario):
    """Trámite completo: informe, precedentes, citado_por, historial y permisos del usuario."""
    t = fila_tramite(con, id_)
    base = resumen(con, id_)
    informe = uno(con, '''
        SELECT i.id, i.nombre_original, i.paginas, i.tamano_bytes, i.subido_en,
               json_build_object('id', us.id, 'nombre_completo', us.nombre_completo) AS subido_por,
               (SELECT count(*) FROM informes x WHERE x.tramite_id = i.tramite_id)::int AS versiones
          FROM informes i JOIN usuarios us ON us.id = i.subido_por
         WHERE i.tramite_id = %s AND i.activo''', (t['id'],))
    historial = todos(con, '''SELECT creado_en AS fecha, accion, usuario_correo AS usuario, detalle
                                FROM auditoria
                               WHERE objeto_tipo = 'tramite' AND objeto_id = %s AND accion = ANY(%s)
                               ORDER BY creado_en DESC, id DESC''', (str(t['id']), list(ACCIONES_HISTORIAL)))
    permisos = permisos_tramite(t, u)
    permisos['descargar'] = bool(informe) and u.puede('DESCARGAR_INFORME')
    return {**base, 'informe': informe,
            'precedentes': _precedentes(con, t['id'], 'tramite_id', 'tramite_precedente_id'),
            'citado_por': _precedentes(con, t['id'], 'tramite_precedente_id', 'tramite_id'),
            'historial': historial, 'permisos': permisos}

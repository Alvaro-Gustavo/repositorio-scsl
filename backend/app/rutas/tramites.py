# Trámites: búsqueda, detalle, registro, edición, asignación, conclusión con PDF,
# archivo, baja, bandejas, similares, informe y precedentes.
# Las reglas del flujo también las verifica la base (triggers): aquí se validan
# antes para dar mensajes claros por campo.
from datetime import date

from fastapi import APIRouter, BackgroundTasks, Body, Depends, File, Form, Query, Response, UploadFile

from .. import contenido, informes
from ..bd import conexion, parametro, todos, uno, valor
from ..errores import ErrorApi, validar
from ..seguridad import Usuario, auditar, requiere, usuario_actual
from .notificaciones import enviar_correos_de_asignacion
from ..tramites import detalle, fila_tramite, id_valido, lista, permisos_tramite, resumen

rutas = APIRouter()

EDITABLES = ('hoja_ruta', 'registro_interno', 'procedencia_id', 'entidad_id', 'tipo_tramite_id', 'asunto',
             'area_id', 'observaciones', 'tipo_documento_id', 'numero_documento', 'fecha_salida')
FILTROS = {'anio': 't.anio_gestion', 'estado': 't.estado_tramite', 'entidad_id': 't.entidad_id',
           'tipo_tramite_id': 't.tipo_tramite_id', 'tipo_documento_id': 't.tipo_documento_id',
           'profesional_id': 't.profesional_id', 'procedencia_id': 't.procedencia_id'}


def _texto(v, maximo=None):
    v = (str(v).strip() if v is not None else '') or None
    return v[:maximo] if v and maximo else v


def _entero(v):
    if v in (None, ''):
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        raise ErrorApi('Uno de los valores elegidos no es válido.', 422)


def _fecha(v, campo='fecha_salida'):
    if v in (None, ''):
        return None
    try:
        return date.fromisoformat(str(v)[:10])
    except ValueError:
        raise ErrorApi('La fecha no es válida.', 422, {campo: 'Use el formato AAAA-MM-DD.'})


def _validar_registro(con, d):
    campos = {}
    if not _texto(d.get('hoja_ruta')):
        campos['hoja_ruta'] = 'Ingrese la hoja de ruta.'
    if not d.get('procedencia_id'):
        campos['procedencia_id'] = 'Seleccione la procedencia.'
    if not d.get('entidad_id'):
        campos['entidad_id'] = 'Seleccione o agregue la entidad.'
    if not d.get('tipo_tramite_id'):
        campos['tipo_tramite_id'] = 'Seleccione el tipo de trámite.'
    maximo = parametro(con, 'asunto_max_caracteres', 500)
    asunto = _texto(d.get('asunto'))
    if not asunto:
        campos['asunto'] = 'Describa el asunto.'
    elif len(asunto) > maximo:
        campos['asunto'] = f'El asunto admite hasta {maximo} caracteres.'
    validar(campos)


# ---------------- Búsqueda y bandejas ----------------
@rutas.get('/tramites')
def buscar(q: str = '', orden: str = '', pagina: int = 1, por_pagina: int = 10,
           auditar_busqueda: str = Query('', alias='auditar'),
           anio: str = '', estado: str = '', entidad_id: str = '', tipo_tramite_id: str = '',
           tipo_documento_id: str = '', profesional_id: str = '', procedencia_id: str = '', en: str = '',
           u: Usuario = Depends(requiere('BUSCAR')), con=Depends(conexion)):
    valores = {'anio': anio, 'estado': estado, 'entidad_id': entidad_id, 'tipo_tramite_id': tipo_tramite_id,
               'tipo_documento_id': tipo_documento_id, 'profesional_id': profesional_id,
               'procedencia_id': procedencia_id}
    condiciones, p = ['t.activo'], {}
    for clave, columna in FILTROS.items():
        if valores[clave]:
            condiciones.append(f'{columna}::text = %({clave})s')
            p[clave] = valores[clave]
    q = q.strip()
    rango = '0'
    if q:
        p['q'] = q
        p['parcial'] = f'%{q}%'
        condiciones.append('''(t.vector_busqueda @@ websearch_to_tsquery('es_legal', %(q)s)
                               OR t.hoja_ruta ILIKE %(parcial)s OR t.numero_documento ILIKE %(parcial)s
                               OR t.registro_interno ILIKE %(parcial)s)''')
        if en == 'contenido':
            # Solo dentro del texto de los informes (peso D del índice).
            condiciones.append("ts_filter(t.vector_busqueda, '{d}') @@ websearch_to_tsquery('es_legal', %(q)s)")
        rango = '''(ts_rank(t.vector_busqueda, websearch_to_tsquery('es_legal', %(q)s))
                    + CASE WHEN t.hoja_ruta ILIKE %(parcial)s OR t.numero_documento ILIKE %(parcial)s THEN 1 ELSE 0 END)'''
    donde = ' AND '.join(condiciones)
    fecha = 'COALESCE(t.fecha_salida, t.creado_en::date)'
    if orden == 'antiguo':
        orden_sql = f'{fecha} ASC, t.creado_en ASC'
    elif orden == 'reciente' or not q:
        orden_sql = f'{fecha} DESC, t.creado_en DESC'
    else:
        orden_sql = f'{rango} DESC, {fecha} DESC'

    por_pagina = max(1, min(100, por_pagina))
    pagina = max(1, pagina)
    total = valor(con, f'SELECT count(*) FROM tramites t WHERE {donde}', p)
    items = lista(con, donde, p, orden_sql, extra=f'{rango}::float AS relevancia',
                  limite=por_pagina, salto=(pagina - 1) * por_pagina) if total else []
    if q and items:
        _agregar_coincidencias(con, items, q)
    if q and auditar_busqueda != 'false':
        auditar(con, u, 'BUSCAR', 'CONSULTA', detalle={'q': q, 'resultados': total})
    return {'items': items, 'total': total, 'pagina': pagina, 'por_pagina': por_pagina,
            'paginas': max(1, -(-total // por_pagina))}


def _agregar_coincidencias(con, items, q):
    """Fragmentos del informe donde aparece lo buscado, con la palabra marcada y su página."""
    informes_ = {f['tramite_id']: f for f in todos(con, '''
        SELECT tramite_id, texto_extraido, paginas FROM informes
         WHERE activo AND texto_extraido IS NOT NULL AND tramite_id = ANY(%s)''', ([t['id'] for t in items],))}
    for t in items:
        i = informes_.get(t['id']) or {}
        r = contenido.fragmentos(i.get('texto_extraido'), q, paginas=i.get('paginas'))
        t['coincidencias_informe'] = r if r['total'] else None


@rutas.get('/tramites/pendientes')
def pendientes(u: Usuario = Depends(usuario_actual), con=Depends(conexion)):
    if u.rol == 'ABOGADO':
        return lista(con, "t.activo AND t.estado_tramite = 'EN_ELABORACION' AND pf.usuario_id = %(yo)s",
                     {'yo': u.id}, 't.fecha_asignacion ASC', con_plazo=True)
    if u.rol in ('JEFE', 'ADMIN'):
        return lista(con, "t.activo AND t.estado_tramite = 'EN_ELABORACION'", None, 't.fecha_asignacion ASC',
                     con_plazo=True)
    return []


@rutas.get('/tramites/por-asignar')
def por_asignar(u: Usuario = Depends(requiere('ASIGNAR_TRAMITE')), con=Depends(conexion)):
    # Los migrados del Excel no siguen el flujo: no se asignan desde aquí.
    return lista(con, "t.activo AND t.estado_tramite = 'RECIBIDO' AND t.origen_registro = 'SISTEMA'", None, 't.creado_en ASC')


# ---------------- Un trámite ----------------
@rutas.get('/tramites/{id_}')
def obtener(id_: str, u: Usuario = Depends(requiere('BUSCAR')), con=Depends(conexion)):
    t = fila_tramite(con, id_)
    if not t['activo'] and not u.puede('ELIMINAR_LOGICO'):
        raise ErrorApi('El trámite fue dado de baja.', 404)
    return detalle(con, id_, u)


@rutas.post('/tramites')
def crear(tareas: BackgroundTasks, datos: dict = Body(...), u: Usuario = Depends(requiere('CREAR_REGISTRO')),
          con=Depends(conexion)):
    _validar_registro(con, datos)
    profesional = _entero(datos.get('profesional_id'))
    if profesional and not u.puede('ASIGNAR_TRAMITE'):
        raise ErrorApi('No tiene permiso para asignar trámites.', 403)
    nuevo = valor(con, '''
        INSERT INTO tramites (hoja_ruta, registro_interno, procedencia_id, entidad_id, tipo_tramite_id, asunto,
                              profesional_id, area_id, observaciones, creado_por)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id''',
        (_texto(datos['hoja_ruta'], 80).upper(), _texto(datos.get('registro_interno'), 50),
         _entero(datos['procedencia_id']), _entero(datos['entidad_id']), _entero(datos['tipo_tramite_id']),
         _texto(datos['asunto']), profesional, _entero(datos.get('area_id')),
         _texto(datos.get('observaciones')), u.id))
    t = resumen(con, nuevo)
    auditar(con, u, 'CREAR_TRAMITE', 'TRAMITES', 'tramite', nuevo, detalle={'hoja_ruta': t['hoja_ruta']})
    if t['profesional']:
        auditar(con, u, 'ASIGNAR_TRAMITE', 'TRAMITES', 'tramite', nuevo,
                detalle={'profesional': t['profesional']['nombre_completo']})
        enviar_correos_de_asignacion(con, nuevo, tareas)
    return t


@rutas.put('/tramites/{id_}')
def actualizar(id_: str, datos: dict = Body(...), u: Usuario = Depends(usuario_actual), con=Depends(conexion)):
    t = fila_tramite(con, id_)
    if not permisos_tramite(t, u)['editar']:
        raise ErrorApi('No tiene permisos para editar este trámite.', 403)
    cambios = {k: datos[k] for k in EDITABLES if k in datos}
    if t['origen_registro'] == 'SISTEMA':
        _validar_registro(con, {**t, **cambios})
    convertir = {
        'hoja_ruta': lambda v: (_texto(v, 80) or '').upper() or None,
        'registro_interno': lambda v: _texto(v, 50), 'asunto': _texto, 'observaciones': _texto,
        'numero_documento': lambda v: (_texto(v, 100) or '').upper() or None,
        'fecha_salida': _fecha,
    }
    valores = {k: convertir.get(k, _entero)(v) for k, v in cambios.items()}
    if valores:
        columnas = ', '.join(f'{k} = %({k})s' for k in valores)
        con.execute(f'UPDATE tramites SET {columnas}, actualizado_por = %(yo)s WHERE id = %(id)s',
                    {**valores, 'yo': u.id, 'id': t['id']})
        auditar(con, u, 'EDITAR_TRAMITE', 'TRAMITES', 'tramite', t['id'], detalle={'campos': list(valores)})
    return detalle(con, id_, u)


@rutas.patch('/tramites/{id_}/asignar')
def asignar(id_: str, tareas: BackgroundTasks, datos: dict = Body(default={}),
            u: Usuario = Depends(requiere('ASIGNAR_TRAMITE')), con=Depends(conexion)):
    t = fila_tramite(con, id_)
    if t['estado_tramite'] in ('CONCLUIDO', 'ARCHIVADO'):
        raise ErrorApi('No se cambia el abogado de un trámite concluido.', 409)
    if not t['activo'] or t['origen_registro'] != 'SISTEMA':
        raise ErrorApi('Este trámite no admite asignación.', 409)
    profesional = _entero(datos.get('profesional_id'))
    con.execute('UPDATE tramites SET profesional_id = %s, actualizado_por = %s WHERE id = %s',
                (profesional, u.id, t['id']))
    r = resumen(con, t['id'])
    auditar(con, u, 'ASIGNAR_TRAMITE', 'TRAMITES', 'tramite', t['id'],
            detalle={'profesional': r['profesional']['nombre_completo'] if r['profesional'] else 'sin asignar'})
    enviar_correos_de_asignacion(con, t['id'], tareas)
    return detalle(con, id_, u)


@rutas.post('/tramites/{id_}/concluir')
def concluir(id_: str, tipo_documento_id: str = Form(''), numero_documento: str = Form(''),
             fecha_salida: str = Form(''), archivo: UploadFile | None = File(None),
             u: Usuario = Depends(usuario_actual), con=Depends(conexion)):
    t = fila_tramite(con, id_)
    if u.rol != 'ADMIN' and (t['abogado_usuario_id'] != u.id or not u.puede('SUBIR_INFORME')):
        raise ErrorApi('Solo el abogado asignado al trámite puede subir el informe.', 403)
    if t['estado_tramite'] not in ('EN_ELABORACION', 'CONCLUIDO') and t['origen_registro'] == 'SISTEMA':
        raise ErrorApi('El trámite debe estar en elaboración para subir el informe.', 409)

    campos = {}
    if not tipo_documento_id:
        campos['tipo_documento_id'] = 'Seleccione el tipo de documento.'
    if not numero_documento.strip():
        campos['numero_documento'] = 'Ingrese el número del documento de respuesta.'
    maximo_mb = parametro(con, 'pdf_max_mb', 50)
    contenido = archivo.file.read(maximo_mb * 1048576 + 1) if archivo else b''
    if not archivo or not contenido:
        campos['archivo'] = 'Adjunte el informe en PDF.'
    elif not (archivo.filename or '').lower().endswith('.pdf') or not contenido.startswith(b'%PDF'):
        campos['archivo'] = 'El archivo debe ser PDF.'
    elif len(contenido) > maximo_mb * 1048576:
        campos['archivo'] = f'El PDF supera {maximo_mb} MB.'
    validar(campos)

    try:
        ruta, huella, paginas, texto = informes.guardar(contenido)
    except ValueError as e:
        raise ErrorApi(str(e), 422, {'archivo': str(e)})
    try:
        # 1) datos de respuesta; 2) el informe (los triggers concluyen el trámite).
        con.execute('''UPDATE tramites SET tipo_documento_id = %s, numero_documento = %s,
                              fecha_salida = COALESCE(%s, fecha_salida), actualizado_por = %s
                        WHERE id = %s''',
                    (_entero(tipo_documento_id), numero_documento.strip().upper()[:100], _fecha(fecha_salida),
                     u.id, t['id']))
        con.execute('''INSERT INTO informes (tramite_id, ruta_archivo, nombre_original, tamano_bytes, huella_sha256,
                                             paginas, texto_extraido, subido_por)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s)''',
                    (t['id'], ruta, (archivo.filename or 'informe.pdf')[:255], len(contenido), huella, paginas,
                     texto or None, u.id))
        version = valor(con, 'SELECT count(*) FROM informes WHERE tramite_id = %s', (t['id'],))
        auditar(con, u, 'SUBIR_INFORME', 'TRAMITES', 'tramite', t['id'],
                detalle={'archivo': archivo.filename, 'version': version, 'sha256': huella})
        return detalle(con, id_, u)
    except Exception:
        informes.borrar(ruta)
        raise


@rutas.patch('/tramites/{id_}/archivar')
def archivar(id_: str, u: Usuario = Depends(requiere('ARCHIVAR_TRAMITE')), con=Depends(conexion)):
    t = fila_tramite(con, id_)
    if t['estado_tramite'] != 'CONCLUIDO':
        raise ErrorApi('Solo se archiva un trámite concluido.', 409)
    con.execute("UPDATE tramites SET estado_tramite = 'ARCHIVADO', actualizado_por = %s WHERE id = %s", (u.id, t['id']))
    auditar(con, u, 'ARCHIVAR_TRAMITE', 'TRAMITES', 'tramite', t['id'])
    return detalle(con, id_, u)


@rutas.patch('/tramites/{id_}/baja')
def dar_de_baja(id_: str, datos: dict = Body(default={}), u: Usuario = Depends(requiere('ELIMINAR_LOGICO')),
                con=Depends(conexion)):
    motivo = _texto(datos.get('motivo'))
    validar({'motivo': 'Obligatorio.'} if not motivo else None)
    t = fila_tramite(con, id_)
    con.execute('UPDATE tramites SET activo = false, motivo_baja = %s, actualizado_por = %s WHERE id = %s',
                (motivo, u.id, t['id']))
    auditar(con, u, 'BAJA_TRAMITE', 'TRAMITES', 'tramite', t['id'], detalle={'motivo': motivo})
    return resumen(con, t['id'])


@rutas.get('/tramites/{id_}/similares')
def similares(id_: str, u: Usuario = Depends(requiere('BUSCAR')), con=Depends(conexion)):
    fila_tramite(con, id_)
    parecidos = todos(con, 'SELECT tramite_id, afinidad FROM tramites_similares(%s, 6)', (id_valido(id_),))
    return [{'tramite': resumen(con, p['tramite_id']), 'afinidad': round(float(p['afinidad']))} for p in parecidos]


# ---------------- Informe ----------------
def _informe_activo(con, id_):
    i = uno(con, 'SELECT * FROM informes WHERE tramite_id = %s AND activo', (id_valido(id_),))
    if not i:
        raise ErrorApi('Este trámite aún no tiene informe.', 404)
    return i


@rutas.get('/tramites/{id_}/informe/paginas')
def paginas_informe(id_: str, u: Usuario = Depends(requiere('VER_INFORME')), con=Depends(conexion)):
    i = _informe_activo(con, id_)
    marca = f'{u.correo} · {uno(con, "SELECT to_char(now(), %s) AS f", ("DD/MM/YYYY HH24:MI",))["f"]}'
    try:
        paginas = informes.paginas_con_marca(i['ruta_archivo'], marca)
    except (OSError, ValueError, RuntimeError):
        raise ErrorApi('No se encontró el archivo del informe en el servidor.', 410)
    auditar(con, u, 'VER_INFORME', 'TRAMITES', 'tramite', i['tramite_id'])
    return {'paginas': paginas, 'marca': u.correo}


@rutas.get('/tramites/{id_}/informe/coincidencias')
def coincidencias_informe(id_: str, q: str = '', u: Usuario = Depends(requiere('VER_INFORME')), con=Depends(conexion)):
    """Dónde aparece q en cada página del informe (para resaltarlo en el visor)."""
    i = _informe_activo(con, id_)
    q = q.strip()[:200]
    if not contenido.terminos(q):
        return {'q': q, 'total': 0, 'paginas': []}
    try:
        paginas = informes.coincidencias(i['ruta_archivo'], q)
    except (OSError, ValueError, RuntimeError):
        raise ErrorApi('No se encontró el archivo del informe en el servidor.', 410)
    auditar(con, u, 'BUSCAR_EN_INFORME', 'TRAMITES', 'tramite', i['tramite_id'], detalle={'q': q})
    return {'q': q, 'total': sum(len(p) for p in paginas), 'paginas': paginas}


@rutas.get('/tramites/{id_}/informe/descargar')
def descargar_informe(id_: str, u: Usuario = Depends(requiere('DESCARGAR_INFORME')), con=Depends(conexion)):
    i = _informe_activo(con, id_)
    try:
        with open(informes.ruta_absoluta(i['ruta_archivo']), 'rb') as f:
            contenido = f.read()
    except (OSError, ValueError):
        raise ErrorApi('No se encontró el archivo del informe en el servidor.', 410)
    auditar(con, u, 'DESCARGAR_INFORME', 'TRAMITES', 'tramite', i['tramite_id'],
            detalle={'archivo': i['nombre_original']})
    nombre = ''.join(c if c.isalnum() or c in '-_. ' else '_' for c in i['nombre_original'])
    return Response(contenido, media_type='application/pdf',
                    headers={'Content-Disposition': f'attachment; filename="{nombre}"',
                             'X-Content-Type-Options': 'nosniff'})


# ---------------- Precedentes ----------------
@rutas.post('/tramites/{id_}/precedentes')
def crear_precedente(id_: str, d: dict = Body(...), u: Usuario = Depends(requiere('GESTIONAR_PRECEDENTES')),
                     con=Depends(conexion)):
    t = fila_tramite(con, id_)
    campos = {}
    if not d.get('tramite_precedente_id'):
        campos['tramite_precedente_id'] = 'Elija el trámite precedente.'
    if not _texto(d.get('criterio_legal')):
        campos['criterio_legal'] = 'Escriba el criterio legal.'
    if d.get('relevancia') not in ('VINCULANTE', 'ORIENTADOR', 'REFERENCIAL'):
        campos['relevancia'] = 'Elija la relevancia.'
    validar(campos)
    otro = fila_tramite(con, d['tramite_precedente_id'])
    if otro['id'] == t['id']:
        raise ErrorApi('Un trámite no puede ser precedente de sí mismo.', 409)
    if valor(con, 'SELECT 1 FROM precedentes WHERE tramite_id = %s AND tramite_precedente_id = %s', (t['id'], otro['id'])):
        raise ErrorApi('Ese precedente ya está vinculado.', 409)
    p = uno(con, '''INSERT INTO precedentes (tramite_id, tramite_precedente_id, criterio_legal, relevancia,
                                             tipo_relacion, origen, observaciones, creado_por)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING *''',
            (t['id'], otro['id'], _texto(d['criterio_legal']), d['relevancia'], d.get('tipo_relacion') or 'APLICA',
             'SIMILITUD' if d.get('origen') == 'SIMILITUD' else 'MANUAL', _texto(d.get('observaciones')), u.id))
    auditar(con, u, 'CREAR_PRECEDENTE', 'PRECEDENTES', 'tramite', t['id'], detalle={'precedente': str(otro['id'])})
    return p


@rutas.delete('/precedentes/{id_}', status_code=204)
def eliminar_precedente(id_: str, u: Usuario = Depends(requiere('GESTIONAR_PRECEDENTES')), con=Depends(conexion)):
    p = uno(con, 'DELETE FROM precedentes WHERE id = %s RETURNING tramite_id, tramite_precedente_id', (id_valido(id_),))
    if p:
        auditar(con, u, 'ELIMINAR_PRECEDENTE', 'PRECEDENTES', 'tramite', p['tramite_id'],
                detalle={'precedente': str(p['tramite_precedente_id'])})
    return Response(status_code=204)

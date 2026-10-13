# Importación del Excel histórico.
#   1) analizar: lee el archivo, reconoce las columnas y señala los datos dudosos.
#   2) ejecutar SIMULACION: hace la migración completa y la deshace (solo cuenta).
#   3) ejecutar DEFINITIVA: migra. Un mismo archivo no se migra dos veces.
# Principios: el Excel no se modifica, no se inventan datos y lo dudoso queda
# como incidencia (tabla incidencias_migracion) para revisión.
import hashlib
import json
import os
import re
import unicodedata
import uuid
from datetime import date, datetime

from fastapi import APIRouter, Body, Depends, File, UploadFile
from openpyxl import load_workbook
from psycopg.types.json import Jsonb

from .. import config
from ..bd import conexion, todos, valor
from ..errores import ErrorApi
from ..seguridad import Usuario, auditar, requiere

rutas = APIRouter()

CARPETA = os.path.join(config.CARPETA_DATOS, 'importaciones')
MAX_MB = 20

# Campo de destino -> (etiqueta, nombres posibles de la columna en el Excel, ya normalizados)
COLUMNAS = {
    'hoja_ruta': ('Hoja de ruta', {'hr', 'h r', 'hoja de ruta', 'hoja ruta', 'n hr', 'nro hr', 'no hr', 'n hoja de ruta'}),
    'registro_interno': ('Registro interno', {'ri', 'r i', 'registro interno', 'reg interno', 'n ri', 'nro ri'}),
    'anio': ('Año de gestión', {'ano', 'anio', 'gestion', 'ano gestion', 'ano de gestion'}),
    'procedencia': ('Procedencia', {'procedencia', 'origen'}),
    'entidad': ('Entidad', {'entidad', 'entidad solicitante', 'institucion', 'entidades'}),
    'tipo_tramite': ('Tipo de trámite', {'tipo de tramite', 'tipo tramite', 'tramite', 'tipo'}),
    'asunto': ('Asunto', {'asunto', 'referencia', 'ref', 'descripcion'}),
    'profesional': ('Abogado', {'profesional', 'abogado', 'abogada', 'responsable', 'asignado', 'asignado a'}),
    'tipo_documento': ('Tipo de documento', {'tipo de documento', 'tipo documento', 'tipo doc', 'documento'}),
    'numero_documento': ('Número de documento', {'doc salida', 'documento de salida', 'n documento', 'nro documento',
                                                 'numero de documento', 'cite', 'n cite', 'doc de salida', 'cite salida'}),
    'fecha_salida': ('Fecha de salida', {'fecha salida', 'fecha de salida', 'fecha'}),
    'observaciones': ('Observaciones', {'observaciones', 'observacion', 'obs'}),
    'area': ('Área o unidad', {'area', 'unidad', 'area o unidad', 'area unidad'}),
}
PROCEDENCIAS = {'interna': 'INTERNA', 'int': 'INTERNA', 'i': 'INTERNA', 'externa': 'EXTERNA', 'ext': 'EXTERNA', 'e': 'EXTERNA'}
CATALOGO_DE = {'entidad': 'entidades', 'tipo_tramite': 'tipos_tramite', 'tipo_documento': 'tipos_documento',
               'area': 'areas', 'profesional': 'profesionales'}


def _norm(texto):
    t = unicodedata.normalize('NFD', str(texto or '')).encode('ascii', 'ignore').decode().lower()
    return ' '.join(re.sub(r'[^a-z0-9]+', ' ', t).split())


def _celda(v):
    if v is None:
        return None
    if isinstance(v, (datetime, date)):
        return v
    v = ' '.join(str(v).split())
    return v or None


def _fecha(v):
    """Fecha de una celda, o None si no se puede leer con seguridad."""
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    m = re.fullmatch(r'(\d{1,2})[/.-](\d{1,2})[/.-](\d{2,4})', str(v).strip())
    if m:
        d, mes, a = (int(x) for x in m.groups())
        a = a + 2000 if a < 100 else a
        try:
            return date(a, mes, d)
        except ValueError:
            return None
    try:
        return date.fromisoformat(str(v).strip()[:10])
    except ValueError:
        return None


def _leer(ruta):
    """Devuelve (hoja, encabezados {campo: indice}, columnas originales, filas [(n_fila, [valores])])."""
    libro = load_workbook(ruta, read_only=True, data_only=True)
    try:
        for hoja in libro.worksheets:
            filas = list(hoja.iter_rows(values_only=True))
            for i, fila in enumerate(filas[:15]):
                encontrados = {}
                for j, celda in enumerate(fila):
                    n = _norm(celda)
                    for campo, (_, nombres) in COLUMNAS.items():
                        if n in nombres and campo not in encontrados:
                            encontrados[campo] = j
                            break
                if len(encontrados) >= 3 and 'asunto' in encontrados:
                    originales = {campo: str(fila[j]).strip() for campo, j in encontrados.items()}
                    datos = [(i + k + 2, [_celda(c) for c in f]) for k, f in enumerate(filas[i + 1:])
                             if any(_celda(c) is not None for c in f)]
                    return hoja.title, encontrados, originales, datos, libro.sheetnames
        raise ErrorApi('No se encontró la fila de encabezados (HR, ASUNTO, ENTIDAD...) en el Excel.', 422,
                       {'archivo': 'No se reconocen las columnas.'})
    finally:
        libro.close()


def _registros(encabezados, filas):
    """Convierte cada fila en un registro con sus incidencias. No inventa datos."""
    registros, vistos = [], {}
    for n, valores in filas:
        r = {campo: (valores[j] if j < len(valores) else None) for campo, j in encabezados.items()}
        incidencias = []
        for campo in ('hoja_ruta', 'registro_interno', 'entidad', 'tipo_tramite', 'asunto', 'profesional',
                      'tipo_documento', 'numero_documento', 'observaciones', 'area', 'procedencia'):
            if isinstance(r.get(campo), (date, datetime)):
                r[campo] = r[campo].strftime('%d/%m/%Y')

        if r.get('fecha_salida') is not None:
            f = _fecha(r['fecha_salida'])
            if f is None:
                incidencias.append(('FECHA_ILEGIBLE', f'Fecha de salida "{r["fecha_salida"]}" no se puede leer; queda vacía.'))
            r['fecha_salida'] = f
        anio = None
        if r.get('anio') is not None:
            m = re.search(r'(19|20)\d{2}', str(r['anio']))
            anio = int(m.group()) if m else None
        if anio is None and r.get('fecha_salida'):
            anio = r['fecha_salida'].year
        if anio is None:
            incidencias.append(('ANIO_VACIO', 'Sin año de gestión ni fecha de salida; se registra con el año actual.'))
        r['anio'] = anio

        if r.get('procedencia'):
            p = PROCEDENCIAS.get(_norm(r['procedencia']))
            if not p:
                incidencias.append(('PROCEDENCIA_AMBIGUA', f'Procedencia "{r["procedencia"]}" no es INTERNA ni EXTERNA; queda vacía.'))
            r['procedencia'] = p
        for campo, tipo in (('hoja_ruta', 'HOJA_RUTA_VACIA'), ('entidad', 'ENTIDAD_VACIA'),
                            ('tipo_tramite', 'TIPO_TRAMITE_VACIO'), ('asunto', 'ASUNTO_VACIO')):
            if campo in encabezados and not r.get(campo):
                incidencias.append((tipo, f'{COLUMNAS[campo][0]} vacío; se migra sin ese dato y queda para revisión.'))
        if r.get('hoja_ruta'):
            r['hoja_ruta'] = str(r['hoja_ruta']).upper()[:80]
            clave = _norm(r['hoja_ruta'])
            if clave in vistos:
                incidencias.append(('HOJA_RUTA_REPETIDA', f'La hoja de ruta se repite en la fila {vistos[clave]} (se migran ambas).'))
            else:
                vistos[clave] = n
        if r.get('profesional'):
            r['profesional'] = str(r['profesional']).upper()[:150]
        registros.append({'fila': n, 'datos': r, 'incidencias': incidencias})
    return registros


def _rutas_analisis(id_):
    if not re.fullmatch(r'[0-9a-f]{32}', id_ or ''):
        raise ErrorApi('El análisis no existe. Vuelva a elegir el archivo.', 404)
    base = os.path.join(CARPETA, id_)
    return base + '.xlsx', base + '.json'


@rutas.post('/importaciones/analizar')
def analizar(archivo: UploadFile | None = File(None), u: Usuario = Depends(requiere('IMPORTAR_EXCEL')),
             con=Depends(conexion)):
    nombre = (archivo.filename if archivo else '') or ''
    if not archivo or not nombre.lower().endswith(('.xlsx', '.xls')):
        raise ErrorApi('Seleccione un archivo Excel (.xlsx).', 422, {'archivo': 'Formato no válido.'})
    if nombre.lower().endswith('.xls'):
        raise ErrorApi('El formato .xls antiguo no se puede leer. Ábralo en Excel y guárdelo como .xlsx.', 422,
                       {'archivo': 'Guárdelo como .xlsx.'})
    contenido = archivo.file.read(MAX_MB * 1048576 + 1)
    if len(contenido) > MAX_MB * 1048576:
        raise ErrorApi(f'El archivo supera {MAX_MB} MB.', 422, {'archivo': 'Archivo muy grande.'})

    id_ = uuid.uuid4().hex
    ruta_xlsx, ruta_json = _rutas_analisis(id_)
    os.makedirs(CARPETA, exist_ok=True)
    with open(ruta_xlsx, 'wb') as f:
        f.write(contenido)
    try:
        hoja, encabezados, originales, filas, hojas = _leer(ruta_xlsx)
    except ErrorApi:
        os.remove(ruta_xlsx)
        raise
    except Exception:
        os.remove(ruta_xlsx)
        raise ErrorApi('No se pudo leer el archivo. Verifique que sea un Excel válido.', 422, {'archivo': 'Archivo dañado.'})

    registros = _registros(encabezados, filas)
    huella = hashlib.sha256(contenido).hexdigest()
    with open(ruta_json, 'w', encoding='utf-8') as f:
        json.dump({'archivo': nombre, 'huella': huella, 'hoja': hoja}, f)

    entidades = {_norm(r['datos']['entidad']) for r in registros if r['datos'].get('entidad')}
    existentes = {f['n'] for f in todos(con, 'SELECT normalizar_texto(nombre) AS n FROM entidades')}
    columnas = []
    for campo, j in encabezados.items():
        completos = sum(1 for r in registros if r['datos'].get(campo) not in (None, ''))
        columnas.append({'excel': originales[campo], 'destino': COLUMNAS[campo][0],
                         'completos': completos, 'vacios': len(registros) - completos})
    con_incidencias = [r for r in registros if r['incidencias']]
    tipos = [tipo for r in registros for tipo, _ in r['incidencias']]
    ya_migrado = valor(con, '''SELECT 1 FROM importaciones_excel
                                WHERE huella_sha256 = %s AND modo = 'DEFINITIVA' AND estado = 'COMPLETADA' ''', (huella,))
    auditar(con, u, 'ANALIZAR_EXCEL', 'IMPORTACION', detalle={'archivo': nombre, 'filas': len(registros)})
    return {
        'id': id_, 'archivo': nombre, 'tamano_bytes': len(contenido), 'huella': huella, 'hojas': hojas,
        'ya_migrado': bool(ya_migrado),
        'resumen': {'filas': len(registros), 'columnas': len(encabezados),
                    'listas': len(registros) - len(con_incidencias), 'con_incidencias': len(con_incidencias),
                    'hojas_ruta_repetidas': tipos.count('HOJA_RUTA_REPETIDA'),
                    'fechas_ilegibles': tipos.count('FECHA_ILEGIBLE'),
                    'entidades_nuevas': len(entidades - existentes)},
        'columnas': columnas,
        'incidencias': [{'fila': r['fila'], 'tipo': t, 'descripcion': d}
                        for r in con_incidencias for t, d in r['incidencias']][:100],
    }


def _catalogo_id(con, cache, campo, nombre):
    if not nombre:
        return None
    tabla = CATALOGO_DE[campo]
    clave = (tabla, _norm(nombre))
    if clave not in cache:
        columna = 'nombre_completo' if tabla == 'profesionales' else 'nombre'
        cache[clave] = valor(con, f'''WITH nuevo AS (
                                          INSERT INTO {tabla} ({columna}) VALUES (%(n)s)
                                          ON CONFLICT (nombre_normalizado) DO NOTHING RETURNING id)
                                      SELECT id FROM nuevo
                                      UNION ALL SELECT id FROM {tabla} WHERE nombre_normalizado = normalizar_texto(%(n)s)
                                      LIMIT 1''', {'n': str(nombre)[:150]})
    return cache[clave]


def _migrar(con, u, registros, importacion_id):
    procedencias = {f['nombre']: f['id'] for f in todos(con, 'SELECT id, nombre FROM procedencias')}
    cache, insertados, rechazados, incidencias = {}, 0, 0, 0
    for r in registros:
        d = r['datos']
        try:
            with con.transaction():  # cada fila en su propio punto de guardado
                ids = {campo: _catalogo_id(con, cache, campo, d.get(campo)) for campo in CATALOGO_DE}
                if d.get('numero_documento') or d.get('fecha_salida'):
                    estado = 'CONCLUIDO'
                elif ids['profesional']:
                    estado = 'EN_ELABORACION'
                else:
                    estado = 'RECIBIDO'
                tramite = valor(con, '''
                    INSERT INTO tramites (hoja_ruta, registro_interno, procedencia_id, entidad_id, tipo_tramite_id, asunto,
                                          profesional_id, tipo_documento_id, numero_documento, fecha_salida,
                                          anio_gestion, estado_tramite, area_id, observaciones, origen_registro,
                                          importacion_id, fila_excel, creado_por)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, COALESCE(%s, extract(year FROM current_date)::int),
                            %s, %s, %s, 'MIGRACION', %s, %s, %s) RETURNING id''',
                    (d.get('hoja_ruta'), (str(d['registro_interno'])[:50] if d.get('registro_interno') else None),
                     procedencias.get(d.get('procedencia')), ids['entidad'], ids['tipo_tramite'], d.get('asunto'),
                     ids['profesional'], ids['tipo_documento'],
                     (str(d['numero_documento']).upper()[:100] if d.get('numero_documento') else None),
                     d.get('fecha_salida'), d.get('anio'), estado, ids['area'], d.get('observaciones'),
                     importacion_id, r['fila'], u.id))
                for tipo, descripcion in r['incidencias']:
                    con.execute('''INSERT INTO incidencias_migracion (importacion_id, fila_excel, tipo, descripcion,
                                                                      datos_origen, tramite_id)
                                   VALUES (%s, %s, %s, %s, %s, %s)''',
                                (importacion_id, r['fila'], tipo, descripcion,
                                 Jsonb({k: (v.isoformat() if isinstance(v, date) else v) for k, v in d.items()}), tramite))
                    incidencias += 1
                insertados += 1
        except Exception as e:  # la fila se rechaza; las demás siguen
            rechazados += 1
            r['error'] = str(e).split('\n')[0][:300]
    return insertados, rechazados


@rutas.post('/importaciones/{id_}/ejecutar')
def ejecutar(id_: str, d: dict = Body(...), u: Usuario = Depends(requiere('IMPORTAR_EXCEL')), con=Depends(conexion)):
    modo = d.get('modo')
    if modo not in ('SIMULACION', 'DEFINITIVA'):
        raise ErrorApi('Modo no válido.', 422)
    ruta_xlsx, ruta_json = _rutas_analisis(id_)
    if not os.path.exists(ruta_json):
        raise ErrorApi('El análisis no existe. Vuelva a elegir el archivo.', 404)
    with open(ruta_json, encoding='utf-8') as f:
        meta = json.load(f)
    if modo == 'DEFINITIVA' and valor(con, '''SELECT 1 FROM importaciones_excel WHERE huella_sha256 = %s
                                                AND modo = 'DEFINITIVA' AND estado = 'COMPLETADA' ''', (meta['huella'],)):
        raise ErrorApi('Este archivo ya se migró. Un mismo Excel no se carga dos veces.', 409)

    _, encabezados, _, filas, _ = _leer(ruta_xlsx)
    registros = _registros(encabezados, filas)
    con_incidencias = sum(1 for r in registros if r['incidencias'])

    def nueva_importacion():
        return valor(con, '''INSERT INTO importaciones_excel (archivo_nombre, huella_sha256, modo, registros_encontrados,
                                                              ejecutado_por)
                             VALUES (%s, %s, %s, %s, %s) RETURNING id''',
                     (meta['archivo'][:255], meta['huella'], modo, len(registros), u.id))

    if modo == 'SIMULACION':
        # Se hace todo dentro de un punto de guardado y se deshace: solo quedan las cifras.
        try:
            with con.transaction():
                insertados, rechazados = _migrar(con, u, registros, nueva_importacion())
                raise _Deshacer()
        except _Deshacer:
            pass
        importacion = nueva_importacion()
        finales = (0, rechazados)
    else:
        importacion = nueva_importacion()
        insertados, rechazados = _migrar(con, u, registros, importacion)
        finales = (insertados, rechazados)

    errores = [{'fila': r['fila'], 'error': r['error']} for r in registros if r.get('error')][:50]
    con.execute('''UPDATE importaciones_excel SET estado = 'COMPLETADA', registros_insertados = %s,
                          registros_rechazados = %s, reporte = %s, finalizado_en = now() WHERE id = %s''',
                (*finales, Jsonb({'incidencias': con_incidencias, 'simulados': insertados, 'errores': errores}),
                 importacion))
    if modo == 'DEFINITIVA':
        auditar(con, u, 'IMPORTAR_EXCEL', 'IMPORTACION', 'importacion', importacion,
                detalle={'archivo': meta['archivo'], 'insertados': insertados, 'rechazados': rechazados})
        for ruta in (ruta_xlsx, ruta_json):
            try:
                os.remove(ruta)
            except OSError:
                pass
    fecha = valor(con, 'SELECT finalizado_en FROM importaciones_excel WHERE id = %s', (importacion,))
    return {'id': id_, 'importacion_id': importacion, 'modo': modo, 'estado': 'COMPLETADA',
            'encontrados': len(registros), 'insertados': finales[0], 'simulados': insertados,
            'rechazados': rechazados, 'incidencias': con_incidencias, 'errores': errores, 'fecha': fecha}


class _Deshacer(Exception):
    pass


@rutas.get('/importaciones')
def historial(u: Usuario = Depends(requiere('IMPORTAR_EXCEL')), con=Depends(conexion)):
    return todos(con, '''SELECT ie.id, ie.archivo_nombre AS archivo, ie.huella_sha256 AS huella, ie.modo, ie.estado,
                                ie.registros_encontrados AS encontrados, ie.registros_insertados AS insertados,
                                ie.registros_rechazados AS rechazados,
                                COALESCE((ie.reporte->>'incidencias')::int, 0) AS incidencias,
                                us.correo AS ejecutado_por, COALESCE(ie.finalizado_en, ie.iniciado_en) AS fecha
                           FROM importaciones_excel ie JOIN usuarios us ON us.id = ie.ejecutado_por
                          ORDER BY ie.iniciado_en DESC''')

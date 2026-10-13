# Catálogos: procedencias, entidades, tipos de trámite, tipos de documento, áreas y profesionales.
from fastapi import APIRouter, Body, Depends
from psycopg import sql

from ..bd import conexion, todos, uno, valor
from ..errores import ErrorApi, validar
from ..seguridad import Usuario, auditar, exigir, usuario_actual

rutas = APIRouter()

# tipo -> (columna del nombre, columna en tramites)
CATALOGOS = {
    'procedencias': ('nombre', 'procedencia_id'),
    'entidades': ('nombre', 'entidad_id'),
    'tipos_tramite': ('nombre', 'tipo_tramite_id'),
    'tipos_documento': ('nombre', 'tipo_documento_id'),
    'areas': ('nombre', 'area_id'),
    'profesionales': ('nombre_completo', 'profesional_id'),
}
# La secretaria puede agregar estos valores mientras registra un trámite.
ALTA_EN_REGISTRO = {'entidades', 'tipos_tramite', 'areas'}


def _catalogo(tipo):
    if tipo not in CATALOGOS:
        raise ErrorApi('Catálogo desconocido.', 404)
    return CATALOGOS[tipo]


def _seleccion(tipo):
    """SELECT de un catálogo con el nombre siempre como 'nombre' y cuántos trámites lo usan."""
    nombre, columna = _catalogo(tipo)
    extra = sql.SQL('')
    if tipo == 'profesionales':
        extra = sql.SQL(''', c.usuario_id,
            CASE WHEN us.id IS NULL THEN NULL
                 ELSE json_build_object('id', us.id, 'nombre_completo', us.nombre_completo) END AS usuario''')
    union = sql.SQL('LEFT JOIN usuarios us ON us.id = c.usuario_id' if tipo == 'profesionales' else '')
    return sql.SQL('''SELECT c.id, c.{nombre} AS nombre, c.activo{extra},
                             (SELECT count(*) FROM tramites t WHERE t.{columna} = c.id)::int AS usos
                        FROM {tabla} c {union}''').format(
        nombre=sql.Identifier(nombre), extra=extra, columna=sql.Identifier(columna),
        tabla=sql.Identifier(tipo), union=union)


def _obtener(con, tipo, id_):
    fila = uno(con, _seleccion(tipo) + sql.SQL(' WHERE c.id = %s'), (id_,))
    if not fila:
        raise ErrorApi('El valor no existe.', 404)
    return fila


@rutas.get('/catalogos/{tipo}')
def listar(tipo: str, inactivos: str = '', u: Usuario = Depends(usuario_actual), con=Depends(conexion)):
    consulta = _seleccion(tipo)
    if inactivos not in ('1', 'true'):
        consulta += sql.SQL(' WHERE c.activo')
    return todos(con, consulta + sql.SQL(' ORDER BY 2'))


@rutas.get('/catalogos/{tipo}/sugerencias')
def sugerir(tipo: str, texto: str = '', u: Usuario = Depends(usuario_actual), con=Depends(conexion)):
    _catalogo(tipo)
    if not texto.strip():
        return []
    nombre = CATALOGOS[tipo][0]
    consulta = sql.SQL('''
        SELECT id, nombre, parecido FROM (
            SELECT c.id, c.{nombre} AS nombre,
                   round(100 * greatest(similarity(c.nombre_normalizado, normalizar_texto(%(t)s)),
                                        CASE WHEN c.nombre_normalizado LIKE '%%' || normalizar_texto(%(t)s) || '%%'
                                             THEN least(1, 0.6 + length(%(t)s) / 200.0) ELSE 0 END))::int AS parecido
              FROM {tabla} c WHERE c.activo) s
         WHERE parecido >= 25 ORDER BY parecido DESC, nombre LIMIT 8''').format(
        nombre=sql.Identifier(nombre), tabla=sql.Identifier(tipo))
    return todos(con, consulta, {'t': texto})


@rutas.post('/catalogos/{tipo}')
def crear(tipo: str, datos: dict = Body(...), u: Usuario = Depends(usuario_actual), con=Depends(conexion)):
    nombre_col, _ = _catalogo(tipo)
    if tipo in ALTA_EN_REGISTRO:
        if not (u.puede('CREAR_REGISTRO') or u.puede('GESTIONAR_CATALOGOS')):
            raise ErrorApi('No tiene permisos para agregar valores.', 403)
    else:
        exigir(u, 'GESTIONAR_CATALOGOS')
    limpio = ' '.join(str(datos.get('nombre') or '').split())
    validar({'nombre': 'Obligatorio.'} if not limpio else None)
    if tipo == 'profesionales':
        limpio = limpio.upper()
    existente = uno(con, sql.SQL('SELECT id, {n} AS nombre FROM {t} WHERE nombre_normalizado = normalizar_texto(%s)').format(
        n=sql.Identifier(nombre_col), t=sql.Identifier(tipo)), (limpio,))
    if existente:
        raise ErrorApi(f'Ya existe "{existente["nombre"]}".', 409, {'nombre': 'Ya existe un valor igual.'},
                       {'existente': existente})
    if tipo == 'profesionales':
        nuevo = valor(con, 'INSERT INTO profesionales (nombre_completo, usuario_id) VALUES (%s, %s) RETURNING id',
                      (limpio, datos.get('usuario_id') or None))
    else:
        nuevo = valor(con, sql.SQL('INSERT INTO {t} (nombre) VALUES (%s) RETURNING id').format(t=sql.Identifier(tipo)),
                      (limpio,))
    auditar(con, u, 'EDITAR_CATALOGO', 'CATALOGOS', tipo, nuevo, detalle={'nombre': limpio, 'operacion': 'crear'})
    return _obtener(con, tipo, nuevo)


@rutas.put('/catalogos/{tipo}/{id_}')
def actualizar(tipo: str, id_: int, datos: dict = Body(...), u: Usuario = Depends(usuario_actual), con=Depends(conexion)):
    nombre_col, _ = _catalogo(tipo)
    exigir(u, 'GESTIONAR_CATALOGOS')
    _obtener(con, tipo, id_)
    cambios = {}
    if 'nombre' in datos:
        limpio = ' '.join(str(datos.get('nombre') or '').split())
        validar({'nombre': 'Obligatorio.'} if not limpio else None)
        if tipo == 'profesionales':
            limpio = limpio.upper()
        repetido = valor(con, sql.SQL('SELECT id FROM {t} WHERE nombre_normalizado = normalizar_texto(%s) AND id <> %s').format(
            t=sql.Identifier(tipo)), (limpio, id_))
        if repetido:
            raise ErrorApi('Ya existe un valor igual.', 409, {'nombre': 'Ya existe.'})
        cambios[nombre_col] = limpio
    if 'activo' in datos:
        cambios['activo'] = bool(datos['activo'])
    if tipo == 'profesionales' and 'usuario_id' in datos:
        cuenta = datos.get('usuario_id') or None
        if cuenta and valor(con, 'SELECT id FROM profesionales WHERE usuario_id = %s AND id <> %s', (cuenta, id_)):
            raise ErrorApi('Esa cuenta ya está vinculada a otro profesional.', 409)
        cambios['usuario_id'] = cuenta
    if cambios:
        con.execute(sql.SQL('UPDATE {t} SET {c} WHERE id = %s').format(
            t=sql.Identifier(tipo),
            c=sql.SQL(', ').join(sql.SQL('{} = %s').format(sql.Identifier(k)) for k in cambios)),
            (*cambios.values(), id_))
        auditar(con, u, 'EDITAR_CATALOGO', 'CATALOGOS', tipo, id_, detalle=datos)
    return _obtener(con, tipo, id_)


@rutas.post('/catalogos/{tipo}/unificar')
def unificar(tipo: str, datos: dict = Body(...), u: Usuario = Depends(usuario_actual), con=Depends(conexion)):
    _catalogo(tipo)
    exigir(u, 'GESTIONAR_CATALOGOS')
    try:
        conservar, eliminar = int(datos.get('conservar')), int(datos.get('eliminar'))
    except (TypeError, ValueError):
        raise ErrorApi('Elija los dos valores.', 422)
    if conservar == eliminar:
        raise ErrorApi('Elija dos valores distintos.', 422)
    _obtener(con, tipo, conservar)
    _obtener(con, tipo, eliminar)
    movidos = valor(con, 'SELECT unificar_catalogo_app(%s, %s, %s, %s)', (u.id, tipo, conservar, eliminar))
    auditar(con, u, 'EDITAR_CATALOGO', 'CATALOGOS', tipo, conservar,
            detalle={'operacion': 'unificar', 'eliminado': eliminar, 'movidos': movidos})
    return {'movidos': movidos}

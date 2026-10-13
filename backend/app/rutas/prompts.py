# Catálogo de prompts: proponen ABOGADO y JEFE; el JEFE aprueba, devuelve y retira.
# Cada copia suma un uso y queda en la auditoría (función registrar_uso_prompt).
from fastapi import APIRouter, Body, Depends, Response

from ..bd import conexion, todos, uno, valor
from ..errores import ErrorApi, validar
from ..seguridad import Usuario, auditar, requiere

rutas = APIRouter()

CATEGORIAS = ('CONSULTA', 'PRECEDENTE', 'JUICIO_VALOR', 'REDACCION', 'REVISION')

SQL_PROMPT = '''
SELECT p.id, p.titulo, p.categoria, p.tipo_documento_id, p.texto, p.instrucciones, p.estado, p.observacion,
       p.usos, p.aprobado_en, p.creado_en, p.actualizado_en,
       CASE WHEN td.id IS NULL THEN NULL ELSE json_build_object('id', td.id, 'nombre', td.nombre) END AS tipo_documento,
       json_build_object('id', up.id, 'nombre_completo', up.nombre_completo) AS propuesto_por,
       CASE WHEN ua.id IS NULL THEN NULL ELSE json_build_object('id', ua.id, 'nombre_completo', ua.nombre_completo) END AS aprobado_por
  FROM prompts p
  LEFT JOIN tipos_documento td ON td.id = p.tipo_documento_id
  JOIN usuarios up ON up.id = p.propuesto_por
  LEFT JOIN usuarios ua ON ua.id = p.aprobado_por
'''


def _prompt(con, id_):
    p = uno(con, SQL_PROMPT + ' WHERE p.id = %s', (id_,))
    if not p:
        raise ErrorApi('El prompt no existe.', 404)
    return p


def _texto(v):
    return (str(v).strip() if v is not None else '') or None


def _validar(con, d, id_=None):
    campos = {}
    titulo = _texto(d.get('titulo'))
    if not titulo:
        campos['titulo'] = 'Ingrese un título.'
    elif valor(con, '''SELECT 1 FROM prompts WHERE estado <> 'RETIRADO' AND id IS DISTINCT FROM %s
                         AND normalizar_texto(titulo) = normalizar_texto(%s)''', (id_, titulo)):
        campos['titulo'] = 'Ya existe un prompt con ese título.'
    if d.get('categoria') not in CATEGORIAS:
        campos['categoria'] = 'Elija la categoría.'
    if not _texto(d.get('texto')):
        campos['texto'] = 'Escriba el texto del prompt.'
    validar(campos)


@rutas.get('/prompts')
def vigentes(tipo_documento_id: str = '', categoria: str = '', q: str = '',
             u: Usuario = Depends(requiere('USAR_PROMPTS')), con=Depends(conexion)):
    condiciones, p = ["p.estado = 'VIGENTE'"], {}
    if tipo_documento_id:
        condiciones.append('(p.tipo_documento_id IS NULL OR p.tipo_documento_id::text = %(td)s)')
        p['td'] = tipo_documento_id
    if categoria:
        condiciones.append('p.categoria = %(cat)s')
        p['cat'] = categoria
    if q.strip():
        condiciones.append("normalizar_texto(p.titulo || ' ' || p.texto) LIKE '%%' || normalizar_texto(%(q)s) || '%%'")
        p['q'] = q.strip()
    return todos(con, SQL_PROMPT + ' WHERE ' + ' AND '.join(condiciones) + ' ORDER BY p.usos DESC, p.titulo', p)


@rutas.get('/prompts/gestion')
def gestion(estado: str = '', u: Usuario = Depends(requiere('PROPONER_PROMPT')), con=Depends(conexion)):
    condiciones, p = ['TRUE'], {}
    if not u.puede('GESTIONAR_PROMPTS'):
        condiciones.append('p.propuesto_por = %(yo)s')
        p['yo'] = u.id
    if estado:
        condiciones.append('p.estado = %(estado)s')
        p['estado'] = estado
    return todos(con, SQL_PROMPT + ' WHERE ' + ' AND '.join(condiciones) + ' ORDER BY p.actualizado_en DESC', p)


@rutas.post('/prompts')
def proponer(d: dict = Body(...), u: Usuario = Depends(requiere('PROPONER_PROMPT')), con=Depends(conexion)):
    _validar(con, d)
    nuevo = valor(con, '''INSERT INTO prompts (titulo, categoria, tipo_documento_id, texto, instrucciones, propuesto_por)
                          VALUES (%s, %s, %s, %s, %s, %s) RETURNING id''',
                  (_texto(d['titulo'])[:150], d['categoria'], d.get('tipo_documento_id') or None, _texto(d['texto']),
                   _texto(d.get('instrucciones')), u.id))
    auditar(con, u, 'PROPONER_PROMPT', 'PROMPTS', 'prompt', nuevo)
    return _prompt(con, nuevo)


@rutas.put('/prompts/{id_}')
def actualizar(id_: int, d: dict = Body(...), u: Usuario = Depends(requiere('PROPONER_PROMPT')), con=Depends(conexion)):
    p = uno(con, 'SELECT * FROM prompts WHERE id = %s', (id_,))
    if not p:
        raise ErrorApi('El prompt no existe.', 404)
    gestiona = u.puede('GESTIONAR_PROMPTS')
    if p['estado'] != 'BORRADOR' and not gestiona:
        raise ErrorApi('Solo el jefe modifica un prompt vigente o retirado.', 403)
    if p['propuesto_por'] != u.id and not gestiona:
        raise ErrorApi('Solo puede editar sus propuestas.', 403)
    nuevo = {**p, **{k: d[k] for k in ('titulo', 'categoria', 'tipo_documento_id', 'texto', 'instrucciones') if k in d}}
    _validar(con, nuevo, id_)
    con.execute('''UPDATE prompts SET titulo = %s, categoria = %s, tipo_documento_id = %s, texto = %s,
                          instrucciones = %s, observacion = CASE WHEN estado = 'BORRADOR' THEN NULL ELSE observacion END,
                          actualizado_por = %s
                    WHERE id = %s''',
                (_texto(nuevo['titulo'])[:150], nuevo['categoria'], nuevo['tipo_documento_id'] or None,
                 _texto(nuevo['texto']), _texto(nuevo['instrucciones']), u.id, id_))
    auditar(con, u, 'EDITAR_PROMPT', 'PROMPTS', 'prompt', id_)
    return _prompt(con, id_)


def _cambiar_estado(con, u, id_, estado, accion, observacion=None):
    _prompt(con, id_)
    con.execute('UPDATE prompts SET estado = %s, observacion = %s, actualizado_por = %s WHERE id = %s',
                (estado, observacion, u.id, id_))
    auditar(con, u, accion, 'PROMPTS', 'prompt', id_, detalle={'observacion': observacion} if observacion else None)
    return _prompt(con, id_)


@rutas.patch('/prompts/{id_}/aprobar')
def aprobar(id_: int, u: Usuario = Depends(requiere('GESTIONAR_PROMPTS')), con=Depends(conexion)):
    return _cambiar_estado(con, u, id_, 'VIGENTE', 'APROBAR_PROMPT')


@rutas.patch('/prompts/{id_}/devolver')
def devolver(id_: int, d: dict = Body(default={}), u: Usuario = Depends(requiere('GESTIONAR_PROMPTS')),
             con=Depends(conexion)):
    observacion = _texto(d.get('observacion'))
    if not observacion:
        raise ErrorApi('Escriba qué debe corregirse.', 422, {'observacion': 'Obligatorio.'})
    return _cambiar_estado(con, u, id_, 'BORRADOR', 'DEVOLVER_PROMPT', observacion)


@rutas.patch('/prompts/{id_}/retirar')
def retirar(id_: int, u: Usuario = Depends(requiere('GESTIONAR_PROMPTS')), con=Depends(conexion)):
    return _cambiar_estado(con, u, id_, 'RETIRADO', 'RETIRAR_PROMPT')


@rutas.post('/prompts/{id_}/uso', status_code=204)
def registrar_uso(id_: int, d: dict = Body(default={}), u: Usuario = Depends(requiere('USAR_PROMPTS')),
                  con=Depends(conexion)):
    tramite = d.get('tramite_id') or None
    if not valor(con, "SELECT 1 FROM prompts WHERE id = %s AND estado = 'VIGENTE'", (id_,)):
        raise ErrorApi('El prompt no existe o no está vigente.', 404)
    if tramite and not valor(con, 'SELECT 1 FROM tramites WHERE id::text = %s', (str(tramite),)):
        tramite = None
    con.execute('SELECT registrar_uso_prompt(%s, %s, %s::uuid, %s)', (id_, u.id, tramite, u.ip))
    return Response(status_code=204)

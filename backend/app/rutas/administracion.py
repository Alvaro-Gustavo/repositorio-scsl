# Usuarios y roles, auditoría, configuración y sitios legales (fuentes externas).
import re
import secrets

from fastapi import APIRouter, Body, Depends, Response

from .. import config
from ..bd import conexion, todos, uno, valor
from ..correo import avisar, emitir_codigo
from ..errores import ErrorApi, validar
from ..seguridad import (SQL_USUARIO, Usuario, auditar, problema_con_correo, requiere, usuario_actual,
                         usuario_publico)

rutas = APIRouter()

ROLES = ('ADMIN', 'JEFE', 'ABOGADO', 'SECRETARIA')


# ---------------- Usuarios ----------------
def _vincular_profesional(con, usuario_id, nombre):
    """Un ABOGADO necesita un profesional vinculado para recibir trámites."""
    if valor(con, 'SELECT 1 FROM profesionales WHERE usuario_id = %s', (usuario_id,)):
        return
    existente = uno(con, 'SELECT id, usuario_id FROM profesionales WHERE nombre_normalizado = normalizar_texto(%s)',
                    (nombre.upper(),))
    if existente and existente['usuario_id'] is None:
        con.execute('UPDATE profesionales SET usuario_id = %s, activo = true WHERE id = %s', (usuario_id, existente['id']))
    elif not existente:
        con.execute('INSERT INTO profesionales (nombre_completo, usuario_id) VALUES (%s, %s)', (nombre.upper(), usuario_id))


@rutas.get('/usuarios')
def listar_usuarios(u: Usuario = Depends(requiere('GESTIONAR_USUARIOS')), con=Depends(conexion)):
    filas = todos(con, SQL_USUARIO + ' ORDER BY u.nombre_completo')
    permisos = {f['nombre']: f['permisos'] for f in todos(con, '''
        SELECT r.nombre, array_agg(p.codigo ORDER BY p.codigo) AS permisos
          FROM roles r JOIN roles_permisos rp ON rp.rol_id = r.id JOIN permisos p ON p.id = rp.permiso_id
         GROUP BY r.nombre''')}
    for f in filas:
        f['permisos'] = permisos.get(f['rol'], [])
    return filas


@rutas.post('/usuarios')
def crear_usuario(d: dict = Body(...), u: Usuario = Depends(requiere('GESTIONAR_USUARIOS')), con=Depends(conexion)):
    nombre = (d.get('nombre_completo') or '').strip()
    correo = (d.get('correo') or '').strip().lower()
    campos = {}
    if not nombre:
        campos['nombre_completo'] = 'Ingrese el nombre.'
    if problema := problema_con_correo(con, correo):
        campos['correo'] = problema
    if d.get('rol') not in ROLES:
        campos['rol'] = 'Elija un rol.'
    validar(campos)
    # La clave inicial es aleatoria e inutilizable: la persona fija la suya al activar la cuenta.
    nuevo = valor(con, '''INSERT INTO usuarios (nombre_completo, correo, cargo, rol_id, hash_contrasena)
                          SELECT %s, %s, %s, r.id, crypt(%s, gen_salt('bf', 8)) FROM roles r WHERE r.nombre = %s
                          RETURNING id''',
                  (nombre[:150], correo, (d.get('cargo') or '').strip()[:120] or None, secrets.token_urlsafe(32),
                   d['rol']))
    if d['rol'] == 'ABOGADO':
        _vincular_profesional(con, nuevo, nombre)
    emitir_codigo(con, nuevo, correo, 'ACTIVACION')
    auditar(con, u, 'CREAR_USUARIO', 'USUARIOS', 'usuario', nuevo, detalle={'correo': correo, 'rol': d['rol']})
    return usuario_publico(con, nuevo)


@rutas.put('/usuarios/{id_}')
def actualizar_usuario(id_: int, d: dict = Body(...), u: Usuario = Depends(requiere('GESTIONAR_USUARIOS')),
                       con=Depends(conexion)):
    actual = usuario_publico(con, id_)
    if not actual:
        raise ErrorApi('El usuario no existe.', 404)
    if d.get('rol') and d['rol'] not in ROLES:
        raise ErrorApi('Elija un rol.', 422, {'rol': 'Rol no válido.'})
    if id_ == u.id and d.get('rol') and d['rol'] != actual['rol']:
        raise ErrorApi('No puede cambiar su propio rol.', 409)
    correo = (d.get('correo') or '').strip().lower() if 'correo' in d else actual['correo'].lower()
    cambia_correo = correo != actual['correo'].lower()
    if cambia_correo:
        if id_ == u.id:
            raise ErrorApi('Cambie su propio correo desde «Mi perfil»: ahí se confirma con un código.', 409)
        if problema := problema_con_correo(con, correo, id_):
            raise ErrorApi(problema, 422, {'correo': problema})
    if 'nombre_completo' in d:
        nombre = (d.get('nombre_completo') or '').strip()
        validar({'nombre_completo': 'Obligatorio.'} if not nombre else None)
        con.execute('UPDATE usuarios SET nombre_completo = %s WHERE id = %s', (nombre[:150], id_))
    if 'cargo' in d:
        con.execute('UPDATE usuarios SET cargo = %s WHERE id = %s', ((d.get('cargo') or '').strip()[:120] or None, id_))
    if d.get('rol') and d['rol'] != actual['rol']:
        con.execute('UPDATE usuarios SET rol_id = (SELECT id FROM roles WHERE nombre = %s) WHERE id = %s', (d['rol'], id_))
        if d['rol'] == 'ABOGADO':
            _vincular_profesional(con, id_, d.get('nombre_completo') or actual['nombre_completo'])
    if cambia_correo:
        _cambiar_correo_por_admin(con, u, actual, correo)
    auditar(con, u, 'EDITAR_USUARIO', 'USUARIOS', 'usuario', id_,
            detalle={k: d[k] for k in ('nombre_completo', 'cargo', 'rol') if k in d})
    return usuario_publico(con, id_)


def _cambiar_correo_por_admin(con, u: Usuario, actual, correo):
    """El correo es la identidad de la cuenta: la persona debe probar que recibe en la dirección nueva.
    La cuenta queda sin activar, se cierran sus sesiones y recibe un código de activación en el correo nuevo
    (al activarla elige una contraseña nueva). A la dirección anterior se le avisa del cambio."""
    id_ = actual['id']
    con.execute('UPDATE usuarios SET correo = %s, correo_verificado = false WHERE id = %s', (correo, id_))
    con.execute('UPDATE sesiones SET revocada_en = now() WHERE usuario_id = %s AND revocada_en IS NULL', (id_,))
    con.execute('''UPDATE codigos_verificacion SET usado_en = now()
                    WHERE usuario_id = %s AND usado_en IS NULL''', (id_,))
    emitir_codigo(con, id_, correo, 'ACTIVACION')
    auditar(con, u, 'CAMBIAR_CORREO', 'USUARIOS', 'usuario', id_,
            detalle={'anterior': actual['correo'], 'nuevo': correo, 'por': 'administrador'})
    avisar(actual['correo'], f'{config.NOMBRE_SISTEMA}: cambió el correo de su cuenta',
           f'El administrador cambió el correo de su cuenta a {correo}. Si no esperaba este cambio, '
           f'comuníquese de inmediato con el administrador del sistema.')


@rutas.patch('/usuarios/{id_}/activo')
def activar_usuario(id_: int, d: dict = Body(...), u: Usuario = Depends(requiere('GESTIONAR_USUARIOS')),
                    con=Depends(conexion)):
    activo = bool(d.get('activo'))
    if id_ == u.id and not activo:
        raise ErrorApi('No puede desactivar su propia cuenta.', 409)
    if not valor(con, 'UPDATE usuarios SET activo = %s WHERE id = %s RETURNING id', (activo, id_)):
        raise ErrorApi('El usuario no existe.', 404)
    if not activo:
        con.execute('UPDATE sesiones SET revocada_en = now() WHERE usuario_id = %s AND revocada_en IS NULL', (id_,))
    auditar(con, u, 'EDITAR_USUARIO', 'USUARIOS', 'usuario', id_, detalle={'activo': activo})
    return usuario_publico(con, id_)


@rutas.post('/usuarios/{id_}/reenviar-activacion')
def reenviar_activacion(id_: int, u: Usuario = Depends(requiere('GESTIONAR_USUARIOS')), con=Depends(conexion)):
    destino = uno(con, 'SELECT id, correo, correo_verificado FROM usuarios WHERE id = %s', (id_,))
    if not destino:
        raise ErrorApi('El usuario no existe.', 404)
    if destino['correo_verificado']:
        raise ErrorApi('La cuenta ya está activada.', 409)
    emitir_codigo(con, id_, destino['correo'], 'ACTIVACION')
    auditar(con, u, 'REENVIAR_ACTIVACION', 'USUARIOS', 'usuario', id_)
    return {'enviado_a': destino['correo']}


@rutas.get('/roles')
def roles(u: Usuario = Depends(usuario_actual), con=Depends(conexion)):
    return todos(con, '''SELECT r.nombre, r.descripcion,
                                COALESCE(array_agg(p.codigo ORDER BY p.codigo) FILTER (WHERE p.codigo IS NOT NULL), '{}') AS permisos
                           FROM roles r
                           LEFT JOIN roles_permisos rp ON rp.rol_id = r.id
                           LEFT JOIN permisos p ON p.id = rp.permiso_id
                          GROUP BY r.id ORDER BY r.id''')


# ---------------- Auditoría ----------------
# Eventos que el navegador puede registrar (impresiones y sitios externos).
EVENTOS_PERMITIDOS = {'IMPRIMIR_CONSULTA', 'ABRIR_FUENTE_EXTERNA', 'ABRIR_ASISTENTE_IA'}


@rutas.get('/auditoria')
def listar_auditoria(usuario_id: str = '', accion: str = '', modulo: str = '', resultado: str = '',
                     desde: str = '', hasta: str = '', pagina: int = 1, por_pagina: int = 20,
                     u: Usuario = Depends(requiere('VER_AUDITORIA')), con=Depends(conexion)):
    condiciones, p = ['TRUE'], {}
    for campo, v in (('usuario_id::text', usuario_id), ('accion', accion), ('modulo', modulo), ('resultado', resultado)):
        if v:
            clave = campo.split(':')[0]
            condiciones.append(f'{campo} = %({clave})s')
            p[clave] = v
    if desde:
        condiciones.append('creado_en >= %(desde)s::date')
        p['desde'] = desde
    if hasta:
        condiciones.append("creado_en < %(hasta)s::date + interval '1 day'")
        p['hasta'] = hasta
    donde = ' AND '.join(condiciones)
    por_pagina = max(1, min(100, por_pagina))
    pagina = max(1, pagina)
    total = valor(con, f'SELECT count(*) FROM auditoria WHERE {donde}', p)
    p.update(limite=por_pagina, salto=(pagina - 1) * por_pagina)
    items = todos(con, f'''SELECT id, creado_en, usuario_id, usuario_correo, accion, modulo, objeto_tipo, objeto_id,
                                  resultado, ip, detalle
                             FROM auditoria WHERE {donde}
                            ORDER BY creado_en DESC, id DESC LIMIT %(limite)s OFFSET %(salto)s''', p)
    return {'items': items, 'total': total, 'pagina': pagina, 'por_pagina': por_pagina,
            'paginas': max(1, -(-total // por_pagina))}


@rutas.post('/auditoria/eventos', status_code=204)
def registrar_evento(d: dict = Body(...), u: Usuario = Depends(usuario_actual), con=Depends(conexion)):
    accion = str(d.get('accion') or '')
    if accion not in EVENTOS_PERMITIDOS:
        raise ErrorApi('Evento no permitido.', 422)
    modulo = re.sub(r'[^A-Z_]', '', str(d.get('modulo') or 'CONSULTA').upper())[:50] or 'CONSULTA'
    detalle = d.get('detalle') if isinstance(d.get('detalle'), dict) else None
    auditar(con, u, accion, modulo, detalle=detalle)
    return Response(status_code=204)


# ---------------- Configuración ----------------
LIBRES = {'prompts_aviso'}          # texto libre
OPCIONALES = {'plazo_dias_tramite', 'prompts_aviso'}  # pueden quedar vacíos


@rutas.get('/configuracion')
def listar_configuracion(u: Usuario = Depends(usuario_actual), con=Depends(conexion)):
    return todos(con, 'SELECT clave, valor, descripcion, actualizado_en FROM configuracion ORDER BY clave')


@rutas.put('/configuracion/{clave}')
def actualizar_configuracion(clave: str, d: dict = Body(...), u: Usuario = Depends(requiere('GESTIONAR_RETENCION')),
                             con=Depends(conexion)):
    if not valor(con, 'SELECT 1 FROM configuracion WHERE clave = %s', (clave,)):
        raise ErrorApi('Parámetro desconocido.', 404)
    v = d.get('valor')
    v = None if v is None or str(v).strip() == '' else str(v).strip()
    if v is None and clave not in OPCIONALES:
        raise ErrorApi('Este parámetro no puede quedar vacío.', 422, {'valor': 'Obligatorio.'})
    if v is not None and clave not in LIBRES and not v.isdigit():
        raise ErrorApi('Ingrese un número entero.', 422, {'valor': 'Solo números.'})
    fila = uno(con, '''UPDATE configuracion SET valor = %s, actualizado_por = %s WHERE clave = %s
                       RETURNING clave, valor, descripcion, actualizado_en''', (v, u.id, clave))
    auditar(con, u, 'EDITAR_CONFIGURACION', 'CONFIGURACION', 'configuracion', clave, detalle={'valor': v})
    return fila


# ---------------- Sitios legales ----------------
URL = re.compile(r'^https?://\S+$', re.I)


def _validar_fuente(d):
    campos = {}
    if not (d.get('nombre') or '').strip():
        campos['nombre'] = 'Ingrese el nombre.'
    if not URL.match(d.get('url') or ''):
        campos['url'] = 'Ingrese una dirección que empiece con http:// o https://'
    busqueda = (d.get('url_busqueda') or '').strip()
    if busqueda and (not URL.match(busqueda) or '{q}' not in busqueda):
        campos['url_busqueda'] = 'Debe empezar con http(s):// e incluir {q}.'
    validar(campos)


@rutas.get('/fuentes')
def listar_fuentes(u: Usuario = Depends(usuario_actual), con=Depends(conexion)):
    return todos(con, 'SELECT * FROM fuentes_externas ORDER BY orden, nombre')


def _valores_fuente(d):
    return ((d.get('nombre') or '').strip()[:120], (d.get('descripcion') or '').strip()[:250] or None,
            d['url'].strip(), (d.get('url_busqueda') or '').strip() or None, int(d.get('orden') or 100))


@rutas.post('/fuentes')
def crear_fuente(d: dict = Body(...), u: Usuario = Depends(requiere('GESTIONAR_CATALOGOS')), con=Depends(conexion)):
    _validar_fuente(d)
    f = uno(con, '''INSERT INTO fuentes_externas (nombre, descripcion, url, url_busqueda, orden)
                    VALUES (%s, %s, %s, %s, %s) RETURNING *''', _valores_fuente(d))
    auditar(con, u, 'EDITAR_CATALOGO', 'CATALOGOS', 'fuentes_externas', f['id'], detalle={'operacion': 'crear'})
    return f


@rutas.put('/fuentes/{id_}')
def actualizar_fuente(id_: int, d: dict = Body(...), u: Usuario = Depends(requiere('GESTIONAR_CATALOGOS')),
                      con=Depends(conexion)):
    actual = uno(con, 'SELECT * FROM fuentes_externas WHERE id = %s', (id_,))
    if not actual:
        raise ErrorApi('El sitio no existe.', 404)
    nuevo = {**actual, **d}
    _validar_fuente(nuevo)
    f = uno(con, '''UPDATE fuentes_externas SET nombre = %s, descripcion = %s, url = %s, url_busqueda = %s, orden = %s,
                           activo = %s
                     WHERE id = %s RETURNING *''', (*_valores_fuente(nuevo), bool(nuevo['activo']), id_))
    auditar(con, u, 'EDITAR_CATALOGO', 'CATALOGOS', 'fuentes_externas', id_, detalle=d)
    return f

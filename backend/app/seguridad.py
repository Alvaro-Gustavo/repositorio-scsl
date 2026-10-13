# Sesiones, permisos y auditoria.
# El token es el id (UUID aleatorio) de la fila en la tabla sesiones; se envia
# como "Authorization: Bearer <token>". La sesion se cierra por inactividad
# (configuracion.sesion_inactividad_minutos) o al llegar a SESION_MAXIMA_HORAS.
import uuid
from dataclasses import dataclass, field

from fastapi import Depends, Request
from psycopg.types.json import Jsonb

from . import config
from .bd import conexion, parametro, todos, uno
from .errores import ErrorApi


@dataclass
class Usuario:
    id: int
    correo: str
    nombre_completo: str
    rol: str
    permisos: set = field(default_factory=set)
    sesion_id: str | None = None
    ip: str | None = None

    def puede(self, permiso):
        return permiso in self.permisos


def ip_cliente(request: Request):
    return (request.headers.get('x-real-ip')
            or (request.headers.get('x-forwarded-for') or '').split(',')[0].strip()
            or (request.client.host if request.client else None))


def permisos_de(con, usuario_id):
    filas = todos(con, '''SELECT p.codigo FROM usuarios u
                            JOIN roles_permisos rp ON rp.rol_id = u.rol_id
                            JOIN permisos p ON p.id = rp.permiso_id
                           WHERE u.id = %s ORDER BY p.codigo''', (usuario_id,))
    return [f['codigo'] for f in filas]


SQL_USUARIO = '''SELECT u.id, u.nombre_completo, u.correo, u.cargo, r.nombre AS rol, u.activo,
                        u.correo_verificado, u.debe_cambiar_contrasena, u.totp_activo,
                        u.bloqueado_hasta, u.ultimo_acceso, u.creado_en
                   FROM usuarios u JOIN roles r ON r.id = u.rol_id'''


def usuario_publico(con, usuario_id):
    """Usuario como lo ve el frontend: datos, rol y lista de permisos."""
    u = uno(con, SQL_USUARIO + ' WHERE u.id = %s', (usuario_id,))
    if not u:
        return None
    u['permisos'] = permisos_de(con, usuario_id)
    return u


def crear_sesion(con, usuario_id, request: Request):
    fila = uno(con, '''INSERT INTO sesiones (usuario_id, expira_en, ip, agente_usuario)
                       VALUES (%s, now() + make_interval(hours => %s), %s, %s) RETURNING id''',
               (usuario_id, config.SESION_MAXIMA_HORAS, ip_cliente(request),
                (request.headers.get('user-agent') or '')[:500]))
    return str(fila['id'])


def _token(request: Request):
    cabecera = request.headers.get('authorization') or ''
    if not cabecera.lower().startswith('bearer '):
        return None
    token = cabecera[7:].strip()
    try:
        return str(uuid.UUID(token))
    except ValueError:
        return None


def usuario_actual(request: Request, con=Depends(conexion)) -> Usuario:
    """Dependencia: exige una sesion vigente y devuelve el usuario."""
    token = _token(request)
    if not token:
        raise ErrorApi('Su sesión expiró. Ingrese nuevamente.', 401)
    minutos = parametro(con, 'sesion_inactividad_minutos', 30)
    s = uno(con, '''SELECT s.id, s.ultimo_uso_en, u.id AS usuario_id, u.correo, u.nombre_completo, u.activo,
                           r.nombre AS rol,
                           (s.revocada_en IS NOT NULL OR s.expira_en < now()
                            OR s.ultimo_uso_en < now() - make_interval(mins => %s)) AS vencida,
                           s.ultimo_uso_en < now() - interval '1 minute' AS renovar
                      FROM sesiones s JOIN usuarios u ON u.id = s.usuario_id JOIN roles r ON r.id = u.rol_id
                     WHERE s.id = %s''', (minutos, token))
    if not s or s['vencida']:
        raise ErrorApi('Su sesión expiró. Ingrese nuevamente.', 401)
    if not s['activo']:
        raise ErrorApi('Su cuenta está desactivada.', 401)
    if s['renovar']:
        con.execute('UPDATE sesiones SET ultimo_uso_en = now() WHERE id = %s', (token,))
    return Usuario(id=s['usuario_id'], correo=s['correo'], nombre_completo=s['nombre_completo'],
                   rol=s['rol'], permisos=set(permisos_de(con, s['usuario_id'])),
                   sesion_id=token, ip=ip_cliente(request))


def requiere(*permisos):
    """Dependencia: exige al menos uno de los permisos indicados."""
    def _dep(u: Usuario = Depends(usuario_actual)) -> Usuario:
        if not any(u.puede(p) for p in permisos):
            raise ErrorApi('No tiene permisos para realizar esta operación.', 403)
        return u
    return _dep


def exigir(u: Usuario, permiso):
    if not u.puede(permiso):
        raise ErrorApi('No tiene permisos para realizar esta operación.', 403)


def auditar(con, u, accion, modulo, objeto_tipo=None, objeto_id=None, resultado='EXITOSO',
            detalle=None, correo=None, usuario_id=None, ip=None):
    """Deja un registro en la auditoria (inmutable)."""
    con.execute('''INSERT INTO auditoria (usuario_id, usuario_correo, accion, modulo, objeto_tipo,
                                          objeto_id, resultado, ip, detalle)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                (u.id if u else usuario_id, u.correo if u else (correo or 'sistema'), accion, modulo,
                 objeto_tipo, None if objeto_id is None else str(objeto_id), resultado,
                 u.ip if u else ip, Jsonb(detalle) if detalle is not None else None))

# Ingreso, sesion, activacion de cuenta, recuperacion de contrasena y perfil.
import pyotp
from fastapi import APIRouter, Body, Depends, Request, Response

from .. import config
from ..bd import conexion, parametro, uno
from ..correo import avisar, emitir_codigo, verificar_codigo
from ..errores import ErrorApi, validar
from ..seguridad import (Usuario, auditar, crear_sesion, ip_cliente, problema_con_correo, usuario_actual,
                         usuario_publico)

rutas = APIRouter()

CLAVE_MINIMA = 10


def validar_clave(clave, campo='clave'):
    clave = clave or ''
    if len(clave) < CLAVE_MINIMA:
        raise ErrorApi(f'La contraseña debe tener al menos {CLAVE_MINIMA} caracteres.', 422,
                       {campo: f'Mínimo {CLAVE_MINIMA} caracteres.'})
    if not (any(c.isalpha() for c in clave) and any(c.isdigit() for c in clave)):
        raise ErrorApi('La contraseña debe combinar letras y números.', 422, {campo: 'Use letras y números.'})


def fijar_clave(con, usuario_id, clave):
    con.execute('''UPDATE usuarios SET hash_contrasena = crypt(%s, gen_salt('bf', 12)),
                          debe_cambiar_contrasena = false, intentos_fallidos = 0, bloqueado_hasta = NULL
                    WHERE id = %s''', (clave, usuario_id))


def secreto_totp(con, usuario_id):
    return uno(con, '''SELECT pgp_sym_decrypt(decode(totp_secreto, 'base64'), %s) AS s
                         FROM usuarios WHERE id = %s AND totp_secreto IS NOT NULL''',
               (config.SECRETO, usuario_id))


def _usuario_por_correo(con, correo):
    return uno(con, 'SELECT * FROM usuarios WHERE lower(correo) = lower(%s)', ((correo or '').strip(),))


@rutas.post('/auth/ingresar')
def ingresar(request: Request, datos: dict = Body(...), con=Depends(conexion)):
    correo = (datos.get('correo') or '').strip().lower()
    clave = datos.get('clave') or ''
    ip = ip_cliente(request)
    u = _usuario_por_correo(con, correo)
    bloqueo = parametro(con, 'ingreso_bloqueo_minutos', 15)

    if u and u['bloqueado_hasta'] and uno(con, 'SELECT %s > now() AS b', (u['bloqueado_hasta'],))['b']:
        auditar(con, None, 'INICIO_SESION_FALLIDO', 'ACCESO', 'usuario', u['id'], 'BLOQUEADO',
                usuario_id=u['id'], correo=u['correo'], ip=ip)
        con.commit()
        raise ErrorApi(f'La cuenta está bloqueada por intentos fallidos. Intente en {bloqueo} minutos.', 423)

    correcta = bool(u) and uno(con, 'SELECT %s = crypt(%s, %s) AS ok',
                               (u['hash_contrasena'], clave, u['hash_contrasena']))['ok']
    if not correcta or not u['activo']:
        if u:
            maximo = parametro(con, 'ingreso_max_intentos', 5)
            con.execute('''UPDATE usuarios
                              SET intentos_fallidos = CASE WHEN intentos_fallidos + 1 >= %s THEN 0 ELSE intentos_fallidos + 1 END,
                                  bloqueado_hasta = CASE WHEN intentos_fallidos + 1 >= %s
                                                         THEN now() + make_interval(mins => %s) ELSE bloqueado_hasta END
                            WHERE id = %s''', (maximo, maximo, bloqueo, u['id']))
            auditar(con, None, 'INICIO_SESION_FALLIDO', 'ACCESO', 'usuario', u['id'], 'FALLIDO',
                    usuario_id=u['id'], correo=u['correo'], ip=ip)
            con.commit()
        raise ErrorApi('Correo o contraseña incorrectos.', 401)

    if not u['correo_verificado']:
        raise ErrorApi('Active su cuenta con el código enviado a su correo.', 403)

    if u['totp_activo']:
        codigo = str(datos.get('codigo_2fa') or '').strip()
        if not codigo:
            raise ErrorApi('Ingrese el código de su aplicación de autenticación.', 400,
                           {'codigo_2fa': 'Ingrese los 6 dígitos de su aplicación.'})
        s = secreto_totp(con, u['id'])
        if not s or not pyotp.TOTP(s['s']).verify(codigo, valid_window=1):
            auditar(con, None, 'INICIO_SESION_FALLIDO', 'ACCESO', 'usuario', u['id'], 'FALLIDO',
                    {'motivo': 'codigo_2fa'}, usuario_id=u['id'], correo=u['correo'], ip=ip)
            con.commit()
            raise ErrorApi('El código de la aplicación no es correcto.', 400, {'codigo_2fa': 'Código incorrecto.'})

    con.execute('UPDATE usuarios SET intentos_fallidos = 0, bloqueado_hasta = NULL, ultimo_acceso = now() WHERE id = %s',
                (u['id'],))
    token = crear_sesion(con, u['id'], request)
    auditar(con, None, 'INICIO_SESION', 'ACCESO', 'usuario', u['id'], usuario_id=u['id'], correo=u['correo'], ip=ip)
    return {'token': token, 'usuario': usuario_publico(con, u['id'])}


@rutas.post('/auth/salir', status_code=204)
def salir(u: Usuario = Depends(usuario_actual), con=Depends(conexion)):
    con.execute('UPDATE sesiones SET revocada_en = now() WHERE id = %s', (u.sesion_id,))
    auditar(con, u, 'CIERRE_SESION', 'ACCESO', 'usuario', u.id)
    return Response(status_code=204)


@rutas.get('/auth/sesion')
def sesion(u: Usuario = Depends(usuario_actual), con=Depends(conexion)):
    return usuario_publico(con, u.id)


@rutas.post('/auth/activar', status_code=204)
def activar(request: Request, datos: dict = Body(...), con=Depends(conexion)):
    u = _usuario_por_correo(con, datos.get('correo'))
    validar_clave(datos.get('clave'))
    if not u or not u['activo'] or not verificar_codigo(con, u['id'], 'ACTIVACION', datos.get('codigo')):
        con.commit()  # conserva el conteo de intentos
        raise ErrorApi('El código no es válido o ya venció.', 400, {'codigo': 'Código incorrecto o vencido.'})
    fijar_clave(con, u['id'], datos['clave'])
    con.execute('UPDATE usuarios SET correo_verificado = true WHERE id = %s', (u['id'],))
    auditar(con, None, 'ACTIVAR_CUENTA', 'ACCESO', 'usuario', u['id'], usuario_id=u['id'], correo=u['correo'],
            ip=ip_cliente(request))
    return Response(status_code=204)


@rutas.post('/auth/recuperar', status_code=204)
def solicitar_recuperacion(datos: dict = Body(...), con=Depends(conexion)):
    # Siempre responde igual, exista o no el correo (no revela quien tiene cuenta).
    u = _usuario_por_correo(con, datos.get('correo'))
    if u and u['activo'] and u['correo_verificado']:
        emitir_codigo(con, u['id'], u['correo'], 'RECUPERACION')
    return Response(status_code=204)


@rutas.post('/auth/restablecer', status_code=204)
def restablecer(request: Request, datos: dict = Body(...), con=Depends(conexion)):
    u = _usuario_por_correo(con, datos.get('correo'))
    validar_clave(datos.get('clave'))
    if not u or not u['activo'] or not verificar_codigo(con, u['id'], 'RECUPERACION', datos.get('codigo')):
        con.commit()
        raise ErrorApi('El código no es válido o ya venció.', 400, {'codigo': 'Código incorrecto o vencido.'})
    fijar_clave(con, u['id'], datos['clave'])
    # Por seguridad se cierran las sesiones abiertas.
    con.execute('UPDATE sesiones SET revocada_en = now() WHERE usuario_id = %s AND revocada_en IS NULL', (u['id'],))
    auditar(con, None, 'RECUPERAR_CONTRASENA', 'ACCESO', 'usuario', u['id'], usuario_id=u['id'],
            correo=u['correo'], ip=ip_cliente(request))
    return Response(status_code=204)


# ---------------- Perfil ----------------
@rutas.put('/perfil')
def actualizar_perfil(datos: dict = Body(...), u: Usuario = Depends(usuario_actual), con=Depends(conexion)):
    nombre = (datos.get('nombre_completo') or '').strip()
    validar({'nombre_completo': 'Obligatorio.'} if not nombre else None)
    con.execute('UPDATE usuarios SET nombre_completo = %s, cargo = %s WHERE id = %s',
                (nombre[:150], (datos.get('cargo') or '').strip()[:120] or None, u.id))
    return usuario_publico(con, u.id)


@rutas.post('/perfil/clave', status_code=204)
def cambiar_clave(datos: dict = Body(...), u: Usuario = Depends(usuario_actual), con=Depends(conexion)):
    if not _clave_correcta(con, u.id, datos.get('actual')):
        raise ErrorApi('La contraseña actual no es correcta.', 400, {'actual': 'No coincide.'})
    validar_clave(datos.get('nueva'), 'nueva')
    if datos.get('nueva') == datos.get('actual'):
        raise ErrorApi('La nueva contraseña debe ser distinta de la actual.', 422, {'nueva': 'Use una distinta.'})
    fijar_clave(con, u.id, datos['nueva'])
    con.execute('UPDATE sesiones SET revocada_en = now() WHERE usuario_id = %s AND id <> %s AND revocada_en IS NULL',
                (u.id, u.sesion_id))
    auditar(con, u, 'CAMBIAR_CONTRASENA', 'ACCESO', 'usuario', u.id)
    return Response(status_code=204)


def _clave_correcta(con, usuario_id, clave):
    return uno(con, 'SELECT hash_contrasena = crypt(%s, hash_contrasena) AS ok FROM usuarios WHERE id = %s',
               (clave or '', usuario_id))['ok']


@rutas.post('/perfil/correo')
def solicitar_cambio_correo(datos: dict = Body(...), u: Usuario = Depends(usuario_actual), con=Depends(conexion)):
    """Paso 1: con la contraseña actual, envía un código a la dirección nueva (prueba que es de la persona)."""
    nuevo = (datos.get('correo') or '').strip().lower()
    if not _clave_correcta(con, u.id, datos.get('clave')):
        auditar(con, u, 'CAMBIAR_CORREO', 'ACCESO', 'usuario', u.id, 'FALLIDO', {'motivo': 'contraseña'})
        con.commit()  # el intento fallido queda en la auditoría
        raise ErrorApi('La contraseña actual no es correcta.', 400, {'clave': 'No coincide.'})
    if nuevo == u.correo.lower():
        raise ErrorApi('Ese ya es su correo.', 422, {'correo': 'Escriba una dirección distinta.'})
    if problema := problema_con_correo(con, nuevo, u.id):
        raise ErrorApi(problema, 422, {'correo': problema})
    emitir_codigo(con, u.id, nuevo, 'CAMBIO_CORREO', dato=nuevo)
    auditar(con, u, 'SOLICITAR_CAMBIO_CORREO', 'ACCESO', 'usuario', u.id, detalle={'nuevo': nuevo})
    return {'enviado_a': nuevo}


@rutas.post('/perfil/correo/confirmar')
def confirmar_cambio_correo(datos: dict = Body(...), u: Usuario = Depends(usuario_actual), con=Depends(conexion)):
    """Paso 2: el código recibido en la dirección nueva confirma el cambio; se cierran las otras sesiones
    y se avisa a la dirección anterior."""
    codigo = verificar_codigo(con, u.id, 'CAMBIO_CORREO', datos.get('codigo'))
    if not codigo:
        con.commit()  # conserva el conteo de intentos
        raise ErrorApi('El código no es válido o ya venció.', 400, {'codigo': 'Código incorrecto o vencido.'})
    nuevo = codigo['dato']
    if problema := problema_con_correo(con, nuevo, u.id):  # alguien pudo tomarlo mientras tanto
        raise ErrorApi(problema, 409, {'codigo': problema})
    con.execute('UPDATE usuarios SET correo = %s WHERE id = %s', (nuevo, u.id))
    con.execute('UPDATE sesiones SET revocada_en = now() WHERE usuario_id = %s AND id <> %s AND revocada_en IS NULL',
                (u.id, u.sesion_id))
    auditar(con, u, 'CAMBIAR_CORREO', 'ACCESO', 'usuario', u.id,
            detalle={'anterior': u.correo, 'nuevo': nuevo, 'por': 'titular'})
    avisar(u.correo, f'{config.NOMBRE_SISTEMA}: cambió el correo de su cuenta',
           f'El correo de su cuenta se cambió a {nuevo}. Si usted no hizo este cambio, comuníquese de inmediato '
           f'con el administrador del sistema.')
    return usuario_publico(con, u.id)


@rutas.post('/perfil/2fa/iniciar')
def iniciar_2fa(u: Usuario = Depends(usuario_actual), con=Depends(conexion)):
    secreto = pyotp.random_base32()
    con.execute('''UPDATE usuarios SET totp_secreto = encode(pgp_sym_encrypt(%s, %s), 'base64'), totp_activo = false
                    WHERE id = %s''', (secreto, config.SECRETO, u.id))
    uri = pyotp.TOTP(secreto).provisioning_uri(name=u.correo, issuer_name=config.NOMBRE_SISTEMA)
    return {'secreto': secreto, 'uri': uri}


@rutas.post('/perfil/2fa/confirmar', status_code=204)
def confirmar_2fa(datos: dict = Body(...), u: Usuario = Depends(usuario_actual), con=Depends(conexion)):
    s = secreto_totp(con, u.id)
    codigo = str(datos.get('codigo') or '').strip()
    if not s or not pyotp.TOTP(s['s']).verify(codigo, valid_window=1):
        raise ErrorApi('El código no es correcto. Revise la hora de su teléfono.', 422, {'codigo': 'Código incorrecto.'})
    con.execute('UPDATE usuarios SET totp_activo = true WHERE id = %s', (u.id,))
    auditar(con, u, 'ACTIVAR_2FA', 'ACCESO', 'usuario', u.id)
    return Response(status_code=204)


@rutas.delete('/perfil/2fa', status_code=204)
def desactivar_2fa(u: Usuario = Depends(usuario_actual), con=Depends(conexion)):
    con.execute('UPDATE usuarios SET totp_activo = false, totp_secreto = NULL WHERE id = %s', (u.id,))
    auditar(con, u, 'DESACTIVAR_2FA', 'ACCESO', 'usuario', u.id)
    return Response(status_code=204)

# Codigos de 6 digitos (activacion, recuperacion y cambio de correo) y su envio por correo.
# El codigo se guarda cifrado con bcrypt; nunca en texto.
import logging
import secrets
import smtplib
from email.message import EmailMessage
from urllib.parse import quote

from . import config
from .bd import uno

log = logging.getLogger('scsl.correo')

VIGENCIA_MINUTOS = {'ACTIVACION': 24 * 60, 'RECUPERACION': 30, 'CAMBIO_CORREO': 30}
MAX_INTENTOS = 5


def enviar(destino, asunto, texto):
    msj = EmailMessage()
    msj['From'] = config.SMTP_REMITENTE
    msj['To'] = destino
    msj['Subject'] = asunto
    msj.set_content(texto)
    with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PUERTO, timeout=20) as s:
        if config.SMTP_TLS:
            s.starttls()
        if config.SMTP_USUARIO:
            s.login(config.SMTP_USUARIO, config.SMTP_CLAVE)
        s.send_message(msj)


def avisar(destino, asunto, texto):
    """Aviso informativo: si no hay SMTP o el envio falla, se registra y la operacion sigue."""
    if not config.SMTP_HOST:
        log.warning('Correo sin configurar (SMTP_HOST vacío). Aviso no enviado a %s: %s', destino, asunto)
        return
    try:
        enviar(destino, asunto, texto)
    except (OSError, smtplib.SMTPException) as e:
        log.error('No se pudo enviar el aviso "%s" a %s: %s', asunto, destino, e)


def emitir_codigo(con, usuario_id, correo, proposito, dato=None, tareas=None):
    """Anula los codigos anteriores, crea uno nuevo y lo envia a `correo`.
    dato: para CAMBIO_CORREO, la direccion nueva que se confirma con el codigo.
    tareas: BackgroundTasks de FastAPI para enviar despues de responder (envios masivos); un
    fallo de envio queda en el log y no deshace la operacion."""
    codigo = f'{secrets.randbelow(10**6):06d}'
    con.execute('''UPDATE codigos_verificacion SET usado_en = now()
                    WHERE usuario_id = %s AND proposito = %s AND usado_en IS NULL''', (usuario_id, proposito))
    con.execute('''INSERT INTO codigos_verificacion (usuario_id, proposito, hash_codigo, expira_en, dato)
                   VALUES (%s, %s, crypt(%s, gen_salt('bf', 8)), now() + make_interval(mins => %s), %s)''',
                (usuario_id, proposito, codigo, VIGENCIA_MINUTOS[proposito], dato))
    if not config.SMTP_HOST:
        log.warning('Correo sin configurar (SMTP_HOST vacío). Código de %s para %s: %s', proposito, correo, codigo)
        return
    if proposito == 'ACTIVACION':
        asunto = f'{config.NOMBRE_SISTEMA}: active su cuenta'
        texto = f'Se creó su cuenta en el {config.NOMBRE_SISTEMA}.\n\n'
        if config.URL_SISTEMA:
            # El codigo va despues de "#": el navegador no lo envia al servidor ni queda en sus registros.
            enlace = f'{config.URL_SISTEMA}/activar#correo={quote(correo)}&codigo={codigo}'
            texto += f'Para activarla abra este enlace y elija su contraseña:\n{enlace}\n\n'
        texto += (f'Código de activación: {codigo}\n\nVence en 24 horas. También puede ingresar a la página '
                  f'"Activar cuenta" con su correo, este código y la contraseña que elija.')
    elif proposito == 'CAMBIO_CORREO':
        asunto = f'{config.NOMBRE_SISTEMA}: confirme su nuevo correo'
        texto = (f'Se pidió usar esta dirección como correo de su cuenta en el {config.NOMBRE_SISTEMA}.\n\n'
                 f'Código de confirmación: {codigo}\n\nVence en 30 minutos. Si usted no lo pidió, ignore este mensaje: '
                 f'el correo de la cuenta no cambia sin este código.')
    else:
        asunto = f'{config.NOMBRE_SISTEMA}: recuperar contraseña'
        texto = (f'Código para restablecer su contraseña: {codigo}\n\nVence en 30 minutos. '
                 f'Si usted no lo pidió, ignore este mensaje.')
    if tareas is not None:
        tareas.add_task(avisar, correo, asunto, texto)
    else:
        enviar(correo, asunto, texto)


def verificar_codigo(con, usuario_id, proposito, codigo):
    """Si el codigo es valido lo marca como usado y devuelve {'dato': ...}; si no, None.
    Cuenta los intentos fallidos."""
    c = uno(con, '''SELECT id, dato, hash_codigo = crypt(%s, hash_codigo) AS correcto
                      FROM codigos_verificacion
                     WHERE usuario_id = %s AND proposito = %s AND usado_en IS NULL
                       AND expira_en > now() AND intentos < %s
                     ORDER BY creado_en DESC LIMIT 1''', (str(codigo or ''), usuario_id, proposito, MAX_INTENTOS))
    if not c:
        return None
    if not c['correcto']:
        con.execute('UPDATE codigos_verificacion SET intentos = intentos + 1 WHERE id = %s', (c['id'],))
        return None
    con.execute('UPDATE codigos_verificacion SET usado_en = now() WHERE id = %s', (c['id'],))
    return {'dato': c['dato']}

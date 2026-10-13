# Codigos de 6 digitos (activacion y recuperacion) y su envio por correo.
# El codigo se guarda cifrado con bcrypt; nunca en texto.
import logging
import secrets
import smtplib
from email.message import EmailMessage

from . import config
from .bd import uno

log = logging.getLogger('scsl.correo')

VIGENCIA_MINUTOS = {'ACTIVACION': 24 * 60, 'RECUPERACION': 30}
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


def emitir_codigo(con, usuario_id, correo, proposito):
    """Anula los codigos anteriores, crea uno nuevo y lo envia."""
    codigo = f'{secrets.randbelow(10**6):06d}'
    con.execute('''UPDATE codigos_verificacion SET usado_en = now()
                    WHERE usuario_id = %s AND proposito = %s AND usado_en IS NULL''', (usuario_id, proposito))
    con.execute('''INSERT INTO codigos_verificacion (usuario_id, proposito, hash_codigo, expira_en)
                   VALUES (%s, %s, crypt(%s, gen_salt('bf', 8)), now() + make_interval(mins => %s))''',
                (usuario_id, proposito, codigo, VIGENCIA_MINUTOS[proposito]))
    if not config.SMTP_HOST:
        log.warning('Correo sin configurar (SMTP_HOST vacío). Código de %s para %s: %s', proposito, correo, codigo)
        return
    if proposito == 'ACTIVACION':
        asunto = f'{config.NOMBRE_SISTEMA}: active su cuenta'
        texto = (f'Se creó su cuenta en el {config.NOMBRE_SISTEMA}.\n\n'
                 f'Código de activación: {codigo}\n\nVence en 24 horas. Ingrese a la página "Activar cuenta" '
                 f'con su correo, este código y la contraseña que elija.')
    else:
        asunto = f'{config.NOMBRE_SISTEMA}: recuperar contraseña'
        texto = (f'Código para restablecer su contraseña: {codigo}\n\nVence en 30 minutos. '
                 f'Si usted no lo pidió, ignore este mensaje.')
    enviar(correo, asunto, texto)


def verificar_codigo(con, usuario_id, proposito, codigo):
    """True si el codigo es valido; lo marca como usado. Cuenta los intentos fallidos."""
    c = uno(con, '''SELECT id, hash_codigo = crypt(%s, hash_codigo) AS correcto
                      FROM codigos_verificacion
                     WHERE usuario_id = %s AND proposito = %s AND usado_en IS NULL
                       AND expira_en > now() AND intentos < %s
                     ORDER BY creado_en DESC LIMIT 1''', (str(codigo or ''), usuario_id, proposito, MAX_INTENTOS))
    if not c:
        return False
    if not c['correcto']:
        con.execute('UPDATE codigos_verificacion SET intentos = intentos + 1 WHERE id = %s', (c['id'],))
        return False
    con.execute('UPDATE codigos_verificacion SET usado_en = now() WHERE id = %s', (c['id'],))
    return True

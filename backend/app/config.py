# Configuracion del backend: todo viene de variables de entorno (docker-compose las toma del .env).
import os


def _texto(nombre, defecto=None, obligatoria=False):
    valor = os.environ.get(nombre, defecto)
    if obligatoria and not valor:
        raise RuntimeError(f'Falta la variable de entorno {nombre}')
    return valor


BD_HOST = _texto('BD_HOST', 'bd')
BD_PUERTO = int(_texto('BD_PUERTO_INTERNO', '5432'))
BD_NOMBRE = _texto('BD_NOMBRE', 'repositorio_scsl')
BD_USUARIO = _texto('APP_BD_USUARIO', 'scsl_app')
BD_CLAVE = _texto('APP_BD_CLAVE', obligatoria=True)

# Clave para cifrar el secreto del segundo factor (2FA) dentro de la base.
SECRETO = _texto('APP_SECRETO', obligatoria=True)

# Carpeta donde se guardan los informes PDF y los Excel en analisis (volumen de Docker).
CARPETA_DATOS = _texto('APP_CARPETA_DATOS', '/datos')

# Duracion maxima de una sesion, aunque haya actividad (horas).
SESION_MAXIMA_HORAS = int(_texto('APP_SESION_MAXIMA_HORAS', '12'))

# Direccion con la que los usuarios abren el sistema (ej. http://scsl.contraloria.local). Se usa en
# los enlaces de los correos; viene de la configuracion, nunca de la peticion (el encabezado Host
# lo controla quien envia la peticion y podria desviar el enlace a otro sitio).
URL_SISTEMA = (_texto('URL_SISTEMA', '') or '').rstrip('/')

# Correo para enviar codigos de activacion y recuperacion. Sin SMTP_HOST,
# el codigo se escribe en el log del contenedor (docker compose logs app).
SMTP_HOST = _texto('SMTP_HOST', '')
SMTP_PUERTO = int(_texto('SMTP_PUERTO', '587') or 587)
SMTP_USUARIO = _texto('SMTP_USUARIO', '')
SMTP_CLAVE = _texto('SMTP_CLAVE', '')
SMTP_REMITENTE = _texto('SMTP_REMITENTE', '') or SMTP_USUARIO
SMTP_TLS = _texto('SMTP_TLS', 'si').lower() in ('si', 'true', '1', 'yes')

NOMBRE_SISTEMA = 'Repositorio SCSL'

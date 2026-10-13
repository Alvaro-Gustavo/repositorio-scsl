# Errores con la forma que espera el frontend: { mensaje, campos? } y su codigo HTTP.
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from psycopg import errors as pg


class ErrorApi(Exception):
    def __init__(self, mensaje, estado=400, campos=None, extra=None):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.estado = estado
        self.campos = campos
        self.extra = extra or {}


def validar(campos):
    """Lanza 422 si hay errores por campo."""
    if campos:
        raise ErrorApi('Revise los campos marcados.', 422, campos)


def _respuesta(estado, mensaje, campos=None, extra=None):
    cuerpo = {'mensaje': mensaje}
    if campos:
        cuerpo['campos'] = campos
    if extra:
        cuerpo.update(extra)
    return JSONResponse(status_code=estado, content=cuerpo)


def registrar_manejadores(app):
    @app.exception_handler(ErrorApi)
    async def _error_api(_: Request, e: ErrorApi):
        return _respuesta(e.estado, e.mensaje, e.campos, e.extra)

    @app.exception_handler(RequestValidationError)
    async def _validacion(_: Request, e: RequestValidationError):
        campos = {str(err['loc'][-1]): 'Dato no válido.' for err in e.errors() if err.get('loc')}
        return _respuesta(422, 'Revise los datos enviados.', campos)

    # Las reglas de negocio de la base (triggers) avisan con RAISE EXCEPTION:
    # su mensaje ya esta escrito para el usuario.
    @app.exception_handler(pg.RaiseException)
    async def _regla(_: Request, e: pg.RaiseException):
        mensaje = e.diag.message_primary or 'Operación no permitida.'
        estado = 403 if 'permiso' in mensaje.lower() or mensaje.startswith(('Solo el ', 'Solo quien')) else 409
        return _respuesta(estado, mensaje)

    @app.exception_handler(pg.UniqueViolation)
    async def _unico(_: Request, e: pg.UniqueViolation):
        return _respuesta(409, 'Ya existe un registro con esos datos.')

    @app.exception_handler(pg.ForeignKeyViolation)
    async def _referencia(_: Request, e: pg.ForeignKeyViolation):
        return _respuesta(422, 'Uno de los valores elegidos no existe.')

    @app.exception_handler(pg.CheckViolation)
    async def _chequeo(_: Request, e: pg.CheckViolation):
        return _respuesta(422, 'Los datos no cumplen las reglas del sistema.', extra={'regla': e.diag.constraint_name})

    @app.exception_handler(pg.InsufficientPrivilege)
    async def _privilegio(_: Request, e: pg.InsufficientPrivilege):
        return _respuesta(403, 'La operación no está permitida para la aplicación.')

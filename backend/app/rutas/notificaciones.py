# Notificaciones del usuario en sesión (campana de la barra superior).
# Las crea la base (trigger notificar_asignacion) al asignar un trámite.
from fastapi import APIRouter, BackgroundTasks, Depends, Response

from .. import config
from ..bd import conexion, todos, valor
from ..correo import enviar
from ..errores import ErrorApi
from ..seguridad import Usuario, usuario_actual

rutas = APIRouter()

SQL_NOTIFICACION = '''
SELECT n.id, n.tipo, n.titulo, n.mensaje, n.tramite_id, n.leida_en, n.creado_en,
       CASE WHEN u.id IS NULL THEN NULL ELSE json_build_object('id', u.id, 'nombre_completo', u.nombre_completo) END AS creado_por
  FROM notificaciones n LEFT JOIN usuarios u ON u.id = n.creado_por
'''


@rutas.get('/notificaciones')
def listar(solo_no_leidas: str = '', u: Usuario = Depends(usuario_actual), con=Depends(conexion)):
    filtro = ' AND n.leida_en IS NULL' if solo_no_leidas in ('1', 'true') else ''
    items = todos(con, SQL_NOTIFICACION + f' WHERE n.usuario_id = %s{filtro} ORDER BY n.creado_en DESC, n.id DESC LIMIT 30',
                  (u.id,))
    no_leidas = valor(con, 'SELECT count(*) FROM notificaciones WHERE usuario_id = %s AND leida_en IS NULL', (u.id,))
    return {'items': items, 'no_leidas': no_leidas}


@rutas.patch('/notificaciones/{id_}/leida', status_code=204)
def marcar_leida(id_: int, u: Usuario = Depends(usuario_actual), con=Depends(conexion)):
    if not valor(con, '''UPDATE notificaciones SET leida_en = COALESCE(leida_en, now())
                          WHERE id = %s AND usuario_id = %s RETURNING id''', (id_, u.id)):
        raise ErrorApi('La notificación no existe.', 404)
    return Response(status_code=204)


@rutas.post('/notificaciones/leer-todas', status_code=204)
def marcar_todas(u: Usuario = Depends(usuario_actual), con=Depends(conexion)):
    con.execute('UPDATE notificaciones SET leida_en = now() WHERE usuario_id = %s AND leida_en IS NULL', (u.id,))
    return Response(status_code=204)


def enviar_correos_de_asignacion(con, tramite_id, tareas: BackgroundTasks):
    """Además del aviso en la campana, envía un correo por cada notificación creada en esta
    transacción (now() es la hora de inicio de la transacción). Solo si hay SMTP configurado."""
    if not config.SMTP_HOST:
        return
    for n in todos(con, '''SELECT u.correo, n.titulo, n.mensaje FROM notificaciones n JOIN usuarios u ON u.id = n.usuario_id
                            WHERE n.tramite_id = %s AND n.creado_en = now()''', (tramite_id,)):
        texto = (f"{n['titulo']}\n\n{n['mensaje'] or ''}\n\n"
                 f"Ingrese al {config.NOMBRE_SISTEMA} para ver el trámite (Mis pendientes).")
        tareas.add_task(_enviar_sin_fallar, n['correo'], f"{config.NOMBRE_SISTEMA}: {n['titulo']}", texto)


def _enviar_sin_fallar(destino, asunto, texto):
    # Un problema con el correo no debe afectar la asignación, que ya quedó guardada.
    try:
        enviar(destino, asunto, texto)
    except Exception:  # noqa: BLE001
        import logging
        logging.getLogger('scsl.correo').exception('No se pudo enviar el aviso de asignación a %s', destino)

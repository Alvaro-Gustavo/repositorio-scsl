# Conexion a PostgreSQL con la cuenta limitada de la aplicacion.
# Cada peticion usa una conexion del pool y una transaccion: si algo falla,
# nada queda a medias.
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from . import config

pool = ConnectionPool(
    conninfo=(f'host={config.BD_HOST} port={config.BD_PUERTO} dbname={config.BD_NOMBRE} '
              f'user={config.BD_USUARIO} password={config.BD_CLAVE} application_name=scsl_app'),
    kwargs={'row_factory': dict_row, 'options': '-c timezone=America/La_Paz'},
    min_size=1, max_size=10, open=False,
)


def conexion():
    """Dependencia de FastAPI: una conexion y una transaccion por peticion."""
    with pool.connection() as con:
        yield con


def todos(con, sql, parametros=None):
    return con.execute(sql, parametros).fetchall()


def uno(con, sql, parametros=None):
    return con.execute(sql, parametros).fetchone()


def valor(con, sql, parametros=None):
    fila = con.execute(sql, parametros).fetchone()
    return None if fila is None else next(iter(fila.values()))


def parametro(con, clave, defecto=None):
    """Lee un valor de la tabla configuracion como entero (o None si esta vacio)."""
    v = valor(con, 'SELECT valor FROM configuracion WHERE clave = %s', (clave,))
    try:
        return int(v) if v not in (None, '') else defecto
    except ValueError:
        return defecto

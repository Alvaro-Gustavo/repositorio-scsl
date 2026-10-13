# Repositorio SCSL - API del backend.
# Implementa el contrato de frontend/src/api/real.js bajo el prefijo /api.
import logging
import os
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI

from . import config, informes
from .bd import pool
from .errores import registrar_manejadores
from .rutas import acceso, administracion, catalogos, importacion, notificaciones, prompts, tablero, tramites

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')


@asynccontextmanager
async def ciclo(_):
    for carpeta in ('informes', 'importaciones'):
        os.makedirs(os.path.join(config.CARPETA_DATOS, carpeta), exist_ok=True)
    pool.open(wait=True, timeout=60)
    threading.Thread(target=informes.separar_paginas_pendientes, args=(pool,), daemon=True).start()
    yield
    pool.close()


app = FastAPI(title='Repositorio SCSL - API', version='1.0.0', lifespan=ciclo,
              docs_url='/api/docs', openapi_url='/api/openapi.json', redoc_url=None)
registrar_manejadores(app)

for modulo in (acceso, catalogos, tramites, prompts, tablero, administracion, importacion, notificaciones):
    app.include_router(modulo.rutas, prefix='/api')


@app.get('/api/salud')
def salud():
    with pool.connection() as con:
        con.execute('SELECT 1')
    return {'estado': 'ok'}

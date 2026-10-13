# ============================================================
# Repositorio SCSL - backend (API en Python con FastAPI)
# Se conecta a la base con la cuenta limitada APP_BD_USUARIO.
# Los informes PDF se guardan en el volumen /datos.
# ============================================================
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1 \
    TZ=America/La_Paz

WORKDIR /srv
COPY requirements.txt .
RUN pip install -r requirements.txt

# Usuario sin privilegios: si alguien vulnerara la API, no es root en el contenedor.
RUN useradd --system --uid 10001 --home /srv scsl \
 && mkdir -p /datos/informes /datos/importaciones && chown -R scsl /datos
COPY app ./app
USER scsl

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/salud', timeout=4)" || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2", "--proxy-headers", "--forwarded-allow-ips", "*"]

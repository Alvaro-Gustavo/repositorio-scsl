#!/usr/bin/env bash
# ============================================================
# REPOSITORIO SCSL - Respaldo completo: base de datos + informes PDF.
#
# Uso (desde la carpeta raiz del proyecto):
#   bash scripts/respaldo.sh
# En el servidor, todos los dias a las 02:00 (crontab -e):
#   0 2 * * * cd /opt/repositorio-scsl && bash scripts/respaldo.sh >> bd/respaldos/respaldo.log 2>&1
#
# Deja en bd/respaldos/:
#   scsl_AAAA-MM-DD_HHMM.dump      base de datos (pg_dump, formato comprimido)
#   archivos_AAAA-MM-DD_HHMM.tgz   volumen scsl_archivos (PDF de los informes)
# y borra los mas antiguos segun RESPALDOS_RETENIDOS (por defecto 30 de cada tipo).
# Copie la carpeta bd/respaldos FUERA del servidor (otro disco o equipo).
# ============================================================
set -euo pipefail

cd "$(dirname "$0")/.."
DESTINO="bd/respaldos"
RETENER="${RESPALDOS_RETENIDOS:-30}"
FECHA="$(date +%Y-%m-%d_%H%M)"
SUPERUSUARIO="$(grep -E '^BD_SUPERUSUARIO=' .env 2>/dev/null | cut -d= -f2)"
SUPERUSUARIO="${SUPERUSUARIO:-postgres}"
PREFIJO="$(grep -E '^PREFIJO=' .env 2>/dev/null | cut -d= -f2)"
PREFIJO="${PREFIJO:-scsl}"            # contenedor ${PREFIJO}_bd y volumen ${PREFIJO}_archivos

mkdir -p "$DESTINO"
echo "[$(date '+%F %T')] Respaldo iniciado"

# 1) Base de datos: se escribe dentro del contenedor en /respaldos (= bd/respaldos del equipo).
docker exec "${PREFIJO}_bd" pg_dump -U "$SUPERUSUARIO" -Fc -d repositorio_scsl -f "/respaldos/scsl_${FECHA}.dump"

# 2) Informes PDF: copia del volumen con un contenedor temporal de solo lectura.
docker run --rm -v "${PREFIJO}_archivos:/datos:ro" -v "$(pwd)/$DESTINO:/r" alpine \
    tar czf "/r/archivos_${FECHA}.tgz" -C /datos .

# 3) Verificacion minima: los archivos existen y no estan vacios.
for f in "$DESTINO/scsl_${FECHA}.dump" "$DESTINO/archivos_${FECHA}.tgz"; do
    if [ ! -s "$f" ]; then
        echo "ERROR: el respaldo $f esta vacio o no se creo" >&2
        exit 1
    fi
done
# El dump debe poder leerse (si esta danado, pg_restore falla aqui y no al necesitarlo).
docker exec "${PREFIJO}_bd" pg_restore --list "/respaldos/scsl_${FECHA}.dump" > /dev/null
tar tzf "$DESTINO/archivos_${FECHA}.tgz" > /dev/null

# 4) Retencion: conserva los ultimos $RETENER de cada tipo.
for patron in 'scsl_*.dump' 'archivos_*.tgz'; do
    ls -1t "$DESTINO"/$patron 2>/dev/null | tail -n +"$((RETENER + 1))" | xargs -r rm -f
done

echo "[$(date '+%F %T')] Respaldo terminado: scsl_${FECHA}.dump y archivos_${FECHA}.tgz"

# Repositorio SCSL — Guía para montarlo en un servidor

Guía paso a paso para instalar el sistema en un servidor de la red interna de la Contraloría, de modo que los
funcionarios entren desde su navegador con una dirección como `http://scsl.contraloria.local`.

Para entender cómo está construido el sistema, vea [ARQUITECTURA.md](ARQUITECTURA.md).

---

## 1. Qué se necesita

### 1.1 Servidor

| Recurso | Mínimo | Recomendado | Por qué |
| --- | --- | --- | --- |
| Sistema operativo | Ubuntu Server 22.04 LTS | **Ubuntu Server 24.04 LTS** | Docker funciona de forma nativa en Linux, con soporte hasta 2029 |
| Procesador | 2 núcleos | 4 núcleos | La conversión de PDF a imágenes usa CPU |
| Memoria RAM | 4 GB | 8 GB | PostgreSQL + backend + Nginx |
| Disco | 60 GB SSD | 150 GB SSD | Sistema, base de datos, informes PDF y respaldos locales |
| Red | IP fija en la red interna | IP fija + nombre DNS interno | Para que todos encuentren el servidor |

Puede ser una máquina virtual (VMware, Hyper-V, Proxmox). **Si la institución solo tiene Windows Server**, lo
recomendado es crear una máquina virtual Linux dentro de él: Docker Desktop no está pensado para servidores.

### 1.2 Lo que debe pedir al área de Sistemas

- [ ] Una **IP fija** para el servidor (ejemplo: `192.168.10.50`).
- [ ] Un **nombre DNS interno** que apunte a esa IP (ejemplo: `scsl.contraloria.local`).
- [ ] Que el **firewall** permita el puerto **80** (y **443** si usarán HTTPS) desde la red interna hacia el servidor.
- [ ] Acceso **SSH** al servidor para el administrador del sistema.
- [ ] Una **cuenta de correo** institucional para enviar los códigos (servidor SMTP, puerto, usuario y clave).
- [ ] **Certificado HTTPS** emitido por la autoridad certificadora interna (opcional, recomendado).
- [ ] Un **destino para copiar los respaldos** fuera del servidor (otro servidor, NAS o disco).

### 1.3 Software (se instala en el paso 3)

Solo **Docker Engine** y el plugin **Docker Compose**. No hace falta instalar PostgreSQL, Python, Node ni Nginx:
vienen dentro de los contenedores.

---

## 2. Preparar el servidor

Conéctese por SSH (`ssh usuario@192.168.10.50`) y ejecute:

```bash
# Actualizar el sistema
sudo apt update && sudo apt upgrade -y

# Zona horaria de Bolivia y hora sincronizada (las fechas de los trámites dependen de esto)
sudo timedatectl set-timezone America/La_Paz
sudo timedatectl set-ntp true
timedatectl            # debe decir: Time zone: America/La_Paz, System clock synchronized: yes

# Firewall: SSH y web solo desde la red interna (ajuste 192.168.0.0/16 a su red)
sudo ufw allow from 192.168.0.0/16 to any port 22 proto tcp
sudo ufw allow from 192.168.0.0/16 to any port 80 proto tcp
sudo ufw allow from 192.168.0.0/16 to any port 443 proto tcp
sudo ufw enable
```

---

## 3. Instalar Docker

Instalación oficial para Ubuntu:

```bash
sudo apt install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Que Docker arranque solo al encender el servidor
sudo systemctl enable --now docker

# Permitir a su usuario usar docker sin sudo (cierre y vuelva a abrir la sesión SSH)
sudo usermod -aG docker $USER

docker --version && docker compose version
```

> **Atención:** Docker publica sus puertos por encima de `ufw`. Por eso el `docker-compose.yml` ya deja la base
> (5433) y pgAdmin (5050) solo en `127.0.0.1`. El único puerto abierto a la red es el de la interfaz web.

---

## 4. Copiar el proyecto al servidor

Ubicación recomendada: `/opt/repositorio-scsl`.

**Opción A — con git** (si el proyecto está en un repositorio interno):

```bash
sudo mkdir -p /opt/repositorio-scsl && sudo chown $USER: /opt/repositorio-scsl
git clone <url-del-repositorio> /opt/repositorio-scsl
```

**Opción B — copiando la carpeta desde su PC** (PowerShell en Windows):

```powershell
# Sin node_modules, dist ni .env
scp -r backend bd frontend docs scripts docker-compose.yml .env.ejemplo .gitattributes .gitignore README.md `
    usuario@192.168.10.50:/opt/repositorio-scsl/
```

Después, en el servidor, confirme que los scripts tienen finales de línea Unix:

```bash
cd /opt/repositorio-scsl
file bd/init/06_seguridad.sh scripts/respaldo.sh   # NO debe decir "CRLF"
# Si dice CRLF:  sudo apt install -y dos2unix && dos2unix bd/init/06_seguridad.sh scripts/respaldo.sh
```

---

## 5. Configurar las claves (`.env`)

```bash
cd /opt/repositorio-scsl
cp .env.ejemplo .env
chmod 600 .env          # solo su usuario puede leerlo

# Genere claves fuertes (copie cada resultado en el .env)
openssl rand -base64 24   # para BD_SUPERCLAVE
openssl rand -base64 24   # para APP_BD_CLAVE
openssl rand -base64 48   # para APP_SECRETO
nano .env
```

| Variable | Valor en el servidor |
| --- | --- |
| `BD_SUPERCLAVE`, `APP_BD_CLAVE`, `APP_SECRETO` | Las claves generadas arriba |
| `ADMIN_CORREO` / `ADMIN_CLAVE` | Correo real del administrador y una clave temporal (se cambia al primer ingreso) |
| `WEB_PUERTO` | `80` (así la dirección no lleva `:8080`) |
| `FRONTEND_MODO` | `real` |
| `SMTP_HOST`, `SMTP_PUERTO`, `SMTP_USUARIO`, `SMTP_CLAVE`, `SMTP_REMITENTE` | Datos del correo que dio Sistemas |
| `PGADMIN_CLAVE` | Una clave fuerte (solo si usará pgAdmin) |

> **Guarde una copia del `.env` en un lugar seguro** (fuera del servidor). Sin `APP_SECRETO` no se pueden validar
> los segundos factores; sin `BD_SUPERCLAVE` no se puede administrar la base.

---

## 6. Levantar el sistema

```bash
cd /opt/repositorio-scsl
docker compose up -d --build        # la primera vez tarda unos minutos (descarga y compila)
docker compose logs -f bd           # espere "Repositorio SCSL: base lista..." y salga con Ctrl+C
docker compose ps                   # bd, app y web deben estar "healthy"
```

Los contenedores tienen `restart: unless-stopped`: **se levantan solos** cuando el servidor se reinicia.

### Comprobaciones

```bash
curl -s http://localhost/api/salud          # debe responder {"estado":"ok"}
docker exec -i scsl_bd psql -U postgres -d repositorio_scsl < bd/pruebas/prueba_reglas.sql 2>&1 | grep PASARON
                                            # debe mostrar: === TODAS LAS PRUEBAS PASARON ===
```

Desde una PC de la red, abra `http://scsl.contraloria.local` (o `http://192.168.10.50`), ingrese con
`ADMIN_CORREO` / `ADMIN_CLAVE` y cambie la clave.

> No ejecute `backend/pruebas/prueba_api.py` en el servidor de producción: crea usuarios y trámites de prueba.

---

## 7. Respaldos automáticos

El script `scripts/respaldo.sh` respalda **la base y los PDF juntos**, verifica que el respaldo se pueda leer y
conserva los últimos 30.

```bash
cd /opt/repositorio-scsl
bash scripts/respaldo.sh            # pruébelo una vez a mano
ls -lh bd/respaldos/

crontab -e                          # y agregue esta línea (todos los días a las 02:00):
0 2 * * * cd /opt/repositorio-scsl && bash scripts/respaldo.sh >> bd/respaldos/respaldo.log 2>&1
```

**Copia fuera del servidor** (obligatorio: si el disco falla, los respaldos locales se pierden con él). Ejemplo a
otro servidor por `rsync`, a las 03:00:

```bash
0 3 * * * rsync -a /opt/repositorio-scsl/bd/respaldos/ respaldos@192.168.10.60:/respaldos/scsl/
```

### Restaurar (en caso de desastre)

```bash
cd /opt/repositorio-scsl
docker compose stop app web
# 1) Base de datos
docker exec scsl_bd pg_restore -U postgres -d repositorio_scsl --clean --if-exists /respaldos/scsl_AAAA-MM-DD_HHMM.dump
# 2) Informes PDF
docker run --rm -v scsl_archivos:/datos -v "$(pwd)/bd/respaldos:/r" alpine \
    sh -c "rm -rf /datos/* && tar xzf /r/archivos_AAAA-MM-DD_HHMM.tgz -C /datos"
docker compose start app web
```

Use siempre un `.dump` y un `.tgz` **de la misma fecha**. Practique la restauración en un equipo de prueba al menos
una vez antes de necesitarla.

---

## 8. HTTPS (recomendado)

Sin HTTPS, las contraseñas viajan sin cifrar por la red interna. Con el certificado que emita Sistemas
(`scsl.crt` y `scsl.key`):

1. Copie los archivos a `/opt/repositorio-scsl/certificados/` (`chmod 600 certificados/scsl.key`).
2. En `frontend/nginx.conf`, agregue un bloque `server` que escuche en `443 ssl` con
   `ssl_certificate /etc/nginx/certificados/scsl.crt;` y `ssl_certificate_key /etc/nginx/certificados/scsl.key;`
   (mismo contenido que el bloque actual), y cambie el bloque del puerto 80 para que solo haga
   `return 301 https://$host$request_uri;`.
3. En `docker-compose.yml`, servicio `web`: publique `"443:443"` además de `"80:80"` y monte
   `./certificados:/etc/nginx/certificados:ro`.
4. `docker compose up -d --build web`.

> Este paso todavía no está probado en el proyecto: hágalo junto con Sistemas, que conoce la autoridad
> certificadora interna, y verifique el acceso desde varias PC antes de anunciarlo.

---

## 9. Operación diaria

| Tarea | Comando |
| --- | --- |
| Estado de los contenedores | `docker compose ps` |
| Ver errores del backend | `docker compose logs --tail 100 app` |
| Códigos de activación (si no hay SMTP) | `docker compose logs app \| grep Código` |
| Reiniciar todo | `docker compose restart` |
| Espacio en disco | `df -h` y `docker system df` |
| Consola SQL | `docker exec -it scsl_bd psql -U postgres -d repositorio_scsl` |

Los logs de Docker tienen tope de 10 MB × 5 archivos por contenedor, así que no llenan el disco.

### Actualizar el sistema a una nueva versión

```bash
cd /opt/repositorio-scsl
bash scripts/respaldo.sh                 # SIEMPRE respaldar antes
git pull                                 # o copie los archivos nuevos
docker compose up -d --build             # reconstruye solo lo que cambió; los datos se conservan
docker compose ps
```

Si la nueva versión trae cambios en la base, vendrán como un script SQL aparte para aplicarlo con
`docker exec -i scsl_bd psql -U postgres -d repositorio_scsl < cambio.sql`.

> **Nunca** use `docker compose down -v` en el servidor: borra la base y todos los PDF.

---

## 10. Lista final antes de entregar

- [ ] `docker compose ps`: los tres contenedores en `healthy`.
- [ ] La prueba de reglas de la base termina con `=== TODAS LAS PRUEBAS PASARON ===`.
- [ ] El sistema abre desde al menos dos PC de la red con el nombre DNS.
- [ ] El administrador cambió su clave inicial y activó el segundo factor (Mi perfil).
- [ ] Se crearon las cuentas de jefe, abogados y secretaria, y llegaron los correos de activación.
- [ ] `scripts/respaldo.sh` está en `crontab` y la copia fuera del servidor funciona.
- [ ] Se probó una restauración en un equipo de prueba.
- [ ] El `.env` está respaldado en un lugar seguro y tiene permisos `600`.
- [ ] El puerto 5433 de la base **no** responde desde otra PC (`Test-NetConnection 192.168.10.50 -Port 5433` debe fallar).
- [ ] Se migró el Excel histórico (Administración → Importar Excel: analizar, probar, migrar).

---

## 11. Problemas frecuentes en el servidor

| Síntoma | Solución |
| --- | --- |
| `permission denied ... docker.sock` | Falta `sudo usermod -aG docker $USER` o cerrar y abrir la sesión SSH |
| `06_seguridad.sh: bad interpreter` | Finales de línea CRLF: `dos2unix bd/init/*.sh scripts/*.sh`, luego `docker compose down -v` (solo en la instalación inicial, sin datos) y `up -d` |
| Desde otra PC no abre | Revise `sudo ufw status`, el DNS y que `WEB_PUERTO=80` |
| Las fechas salen con horas corridas | `timedatectl` debe mostrar `America/La_Paz` |
| No llegan los correos | `docker compose logs app` muestra el error SMTP; revise `SMTP_*` con Sistemas y reinicie `app` |
| El disco se llena | `bd/respaldos/` crece si no se copia y limpia; revise `RESPALDOS_RETENIDOS` y `docker system prune` |

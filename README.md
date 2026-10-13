# Repositorio SCSL

Subcontraloría de Servicios Legales • Repositorio Local Cerrado

Sistema web local para registrar, asignar, concluir y consultar los trámites legales de la Subcontraloría,
con sus informes PDF, precedentes y un catálogo de prompts para que cada doctor trabaje con su propia IA.

Esta guía cubre la **fase 1: base de datos con Docker**. Las fases siguientes (aplicación y servidor web) se
agregan al mismo `docker-compose.yml`.

---

## 1. Qué hay en esta carpeta

```
repositorio-scsl/
├── docker-compose.yml        Define los contenedores (hoy: la base de datos)
├── .env.ejemplo              Plantilla de claves; se copia como .env
├── .gitignore / .gitattributes
└── bd/
    ├── init/                 Se ejecuta UNA vez, al crear la base
    │   ├── 01_extensiones.sql      Extensiones y búsqueda en español sin tildes
    │   ├── 02_tablas.sql           Tablas e índices
    │   ├── 03_reglas.sql           Reglas de negocio (triggers y funciones)
    │   ├── 04_vistas.sql           Consultas guardadas: tablero, pendientes, prompts
    │   ├── 05_datos_iniciales.sql  Roles, permisos, procedencias, fuentes, configuración
    │   └── 06_seguridad.sh         Cuenta de la aplicación y primer administrador
    ├── pruebas/prueba_reglas.sql   Prueba de todas las reglas (no deja datos)
    └── respaldos/                  Aquí se guardan los respaldos
```

**Por qué Docker:** el mismo `docker-compose.yml` levanta la base igual en Windows Server, Linux o una PC de
desarrollo. No se instala PostgreSQL a mano en cada servidor; solo Docker.

**Por qué no hay "versiones":** esta es la base oficial, creada desde cero. Si más adelante hace falta un
cambio, se hará con un script de cambio puntual, nunca rehaciendo la base.

---

## 2. Paso a paso

### Paso 1 — Instalar Docker

| Sistema | Qué instalar |
| --- | --- |
| Windows 10/11 (desarrollo) | Docker Desktop |
| Windows Server | Docker Engine para Windows Server con WSL2 o una VM Linux (consultar con Sistemas) |
| Linux (Ubuntu, Debian…) | `docker` y el plugin `docker compose` |

Comprobar: `docker --version` y `docker compose version`.

### Paso 2 — Configurar las claves

```powershell
cd repositorio-scsl
copy .env.ejemplo .env        # Linux: cp .env.ejemplo .env
```

Abra `.env` y cambie **todas** las claves:

| Variable | Para qué sirve |
| --- | --- |
| `BD_SUPERUSUARIO` / `BD_SUPERCLAVE` | Dueño de la base. Solo para administrarla, nunca para la aplicación |
| `BD_PUERTO` | Puerto en el equipo (5433, para no chocar con un PostgreSQL ya instalado) |
| `APP_BD_USUARIO` / `APP_BD_CLAVE` | Cuenta con la que se conectará la aplicación, con permisos limitados |
| `ADMIN_NOMBRE` / `ADMIN_CORREO` / `ADMIN_CLAVE` | Primer usuario ADMIN del sistema; debe cambiar la clave al ingresar |

**Por qué dos cuentas:** si alguien vulnerara la aplicación, su cuenta no puede borrar tablas, ni la
auditoría, ni trámites. Principio de mínimo privilegio.

### Paso 3 — Crear la base

```powershell
docker compose up -d
docker compose logs -f bd
```

Espere el mensaje `Repositorio SCSL: base lista...` y luego `database system is ready to accept connections`.
Salga de los logs con `Ctrl + C` (el contenedor sigue funcionando).

**Qué pasa por dentro:**

1. Docker descarga la imagen oficial `postgres:16`.
2. Crea el contenedor `scsl_bd` y el volumen `scsl_datos` (donde viven los datos).
3. Como el volumen está vacío, PostgreSQL crea la base `repositorio_scsl` y ejecuta, en orden, los archivos
   de `bd/init/` (01 → 06).
4. La próxima vez que se inicie, el volumen ya tiene datos y **no** vuelve a ejecutar esos archivos.

### Paso 4 — Comprobar que quedó bien

```powershell
docker compose ps                                   # estado "healthy"
docker exec -it scsl_bd psql -U postgres -d repositorio_scsl -c "SELECT nombre FROM roles ORDER BY id;"
```

Debe listar `ADMIN, JEFE, ABOGADO, SECRETARIA`.

### Paso 5 — Probar las reglas de negocio

```powershell
# Windows PowerShell
Get-Content bd\pruebas\prueba_reglas.sql | docker exec -i scsl_bd psql -U postgres -d repositorio_scsl
# Linux
docker exec -i scsl_bd psql -U postgres -d repositorio_scsl < bd/pruebas/prueba_reglas.sql
```

Cada regla imprime `ok: ...`. El último mensaje debe ser `=== TODAS LAS PRUEBAS PASARON ===`. La prueba
deshace todo al final: la base queda vacía como antes.

### Paso 6 — Conectarse con una herramienta visual (opcional)

- **pgAdmin en Docker:** `docker compose --profile herramientas up -d` y abrir http://localhost:5050.
  Registrar servidor: host `bd`, puerto `5432`, usuario y clave de `BD_SUPERUSUARIO`.
- **pgAdmin o DBeaver instalado en su PC:** host `localhost`, puerto `5433`, base `repositorio_scsl`.

---

## 3. Cómo está organizada la base

| Grupo | Tablas | Qué guarda |
| --- | --- | --- |
| Acceso | `roles`, `permisos`, `roles_permisos`, `usuarios`, `sesiones`, `codigos_verificacion` | 4 roles, permisos, usuarios (un rol cada uno), sesiones y códigos de activación/recuperación |
| Catálogos | `procedencias`, `entidades`, `tipos_tramite`, `tipos_documento`, `areas`, `profesionales` | Valores que se repiten. No admiten el mismo valor escrito de otra forma (`INFORME` = `Informé`) |
| Trámites | `tramites`, `informes`, `precedentes` | El trámite (7 campos de registro + 3 de conclusión), su informe PDF y los precedentes con su criterio legal |
| Prompts | `prompts` | Catálogo de instrucciones por tipo de documento para copiar a una IA externa |
| Soporte | `fuentes_externas`, `importaciones_excel`, `incidencias_migracion`, `configuracion`, `auditoria` | Enlaces legales, cargas del Excel, datos dudosos, parámetros y bitácora |

**Formulario del trámite**

| Momento | Quién | Campos |
| --- | --- | --- |
| Registro | Secretaria | `hoja_ruta`, `registro_interno`, `procedencia_id`, `entidad_id`, `tipo_tramite_id`, `asunto`, `profesional_id` |
| Conclusión | Abogado asignado | `tipo_documento_id`, `numero_documento`, informe PDF (`fecha_salida` se llena sola) |
| Automático | La base | `anio_gestion`, `estado_tramite`, `asignado_por`, `fecha_asignacion`, `fecha_conclusion` |
| Opcional | Cualquiera con permiso | `area_id`, `observaciones` |

## 4. Reglas que garantiza la base

Se cumplen aunque alguien escriba directo en la base, sin pasar por la aplicación.

| Regla | Cómo |
| --- | --- |
| Solo SECRETARIA, JEFE o ADMIN registran trámites; hoja de ruta, procedencia, entidad, tipo de trámite y asunto son obligatorios | Trigger + `ck_tramites_registro_completo` |
| Asignar un abogado → `EN_ELABORACION`, con fecha y quién asignó. Solo a abogados con cuenta activa | Trigger `tramites_antes_guardar` |
| Quitar el abogado → vuelve a `RECIBIDO` | Mismo trigger |
| Para subir el informe hay que llenar tipo y número de documento; solo lo sube el abogado asignado (o ADMIN) | Trigger `informes_antes_subir` |
| Subir el informe → `CONCLUIDO`, con fecha de salida | Trigger `informes_despues_subir` |
| Un solo informe activo; el anterior se conserva inactivo | Índice único + trigger |
| Un trámite concluido no vuelve atrás ni cambia de abogado; solo se archiva lo concluido y con permiso | Trigger |
| Prompts: proponen ABOGADO y JEFE; solo el JEFE aprueba, modifica un vigente o retira | Trigger `prompts_antes_guardar` |
| Copiar un prompt suma un uso y queda en la auditoría | Función `registrar_uso_prompt` |
| La auditoría no se modifica ni se borra | Trigger + permisos |
| Los registros migrados del Excel no siguen el flujo y pueden traer vacíos (no se inventan datos) | `origen_registro = 'MIGRACION'` |

**Importante para la aplicación:** en cada `UPDATE` de `tramites` y `prompts` debe enviar `actualizado_por`
con el usuario que hace el cambio; la base lo usa para verificar permisos.

## 5. Consultas útiles

```sql
-- Búsqueda universal (sin tildes, ordenada por relevancia)
SELECT v.*, ts_rank(t.vector_busqueda, q) AS relevancia
  FROM tramites t JOIN v_tramites v ON v.id = t.id,
       websearch_to_tsquery('es_legal', 'ampliacion de plazo') q
 WHERE t.vector_busqueda @@ q AND t.activo
 ORDER BY relevancia DESC LIMIT 20;

-- Búsqueda parcial por código
SELECT * FROM v_tramites WHERE numero_documento ILIKE '%C-166%' OR hoja_ruta ILIKE '%INF-006%';

-- Valores de catálogo parecidos a lo que escribe el usuario
SELECT id, nombre FROM entidades
 WHERE nombre_normalizado % normalizar_texto('gob aut la paz')
 ORDER BY similarity(nombre_normalizado, normalizar_texto('gob aut la paz')) DESC LIMIT 5;

-- Pendientes de un abogado, tablero del jefe, prompts por tipo de documento
SELECT * FROM v_pendientes WHERE abogado_usuario_id = 7;
SELECT * FROM v_tablero_por_abogado;
SELECT * FROM v_prompts_vigentes WHERE tipo_documento IN ('Informe', 'GENERAL');

-- Cadena de precedentes y trámites parecidos
SELECT * FROM cadena_precedentes('<uuid del tramite>');
SELECT * FROM tramites_similares('<uuid del tramite>');

-- Unir dos valores de catálogo que son el mismo (conserva 12, elimina 47)
SELECT unificar_catalogo('entidades', 12, 47);
```

## 6. Operación diaria

| Tarea | Comando |
| --- | --- |
| Iniciar / detener | `docker compose up -d` / `docker compose stop` |
| Ver estado y logs | `docker compose ps` / `docker compose logs -f bd` |
| Respaldo | `docker exec scsl_bd pg_dump -U postgres -Fc -d repositorio_scsl -f /respaldos/scsl_AAAA-MM-DD.dump` |
| Restaurar | `docker exec scsl_bd pg_restore -U postgres -d repositorio_scsl --clean --if-exists /respaldos/<archivo>.dump` |
| Consola SQL | `docker exec -it scsl_bd psql -U postgres -d repositorio_scsl` |

Los respaldos quedan en `bd/respaldos/` del equipo. Cópielos también fuera del servidor.

**Cuidado:** `docker compose down` detiene y quita el contenedor, pero conserva los datos.
`docker compose down -v` **borra el volumen con todos los datos**. Úselo solo en desarrollo, para empezar de cero.

## 7. Problemas frecuentes

| Síntoma | Causa y solución |
| --- | --- |
| `Defina BD_SUPERCLAVE en .env` | Falta el archivo `.env` o una variable. Copie `.env.ejemplo` como `.env` |
| `port is already allocated` | El puerto 5433 está en uso. Cambie `BD_PUERTO` en `.env` |
| `06_seguridad.sh: bad interpreter` o `\r: command not found` | El `.sh` tiene finales de línea de Windows (CRLF). Guárdelo con LF (VS Code: esquina inferior derecha) |
| Cambié un archivo de `bd/init` y no se aplica | Solo corren al crear la base. En desarrollo: `docker compose down -v` y `docker compose up -d` |

## 8. Siguientes fases

1. Migración del Excel histórico (317 registros) a `repositorio_scsl`.
2. Backend (API) en un contenedor `app` conectado con `APP_BD_USUARIO`.
3. Frontend y servidor web HTTPS en un contenedor `web`.

# Repositorio SCSL — Arquitectura y documentación técnica

Sistema web local de la **Subcontraloría de Servicios Legales** (Contraloría General del Estado) para registrar,
asignar, concluir y consultar trámites legales, con sus informes PDF, precedentes, un catálogo de prompts para IA
externa y auditoría completa.

Este documento explica **qué tecnologías usa, cómo está organizado y cómo se relacionan sus partes**.
Para instalarlo en un servidor, vea [DESPLIEGUE_SERVIDOR.md](DESPLIEGUE_SERVIDOR.md).

---

## 1. Vista general

El sistema son **tres contenedores Docker** que se comunican por una red interna:

```
   Navegador del usuario (red interna de la institución)
            │  http://servidor:8080
            ▼
 ┌──────────────────────────┐
 │  web  (scsl_web)         │  Nginx: entrega la interfaz Vue ya compilada
 │  frontend/               │  y reenvía todo lo que empieza con /api/ ──┐
 └──────────────────────────┘                                            │
                                                                         ▼
                                               ┌──────────────────────────────┐
                                               │  app  (scsl_app)             │  Python + FastAPI
                                               │  backend/                    │  valida, aplica permisos,
                                               │  volumen scsl_archivos       │  guarda PDF, audita
                                               └──────────────┬───────────────┘
                                                              │ SQL con la cuenta limitada scsl_app
                                                              ▼
                                               ┌──────────────────────────────┐
                                               │  bd  (scsl_bd)               │  PostgreSQL 16
                                               │  bd/init/  (se ejecuta 1 vez)│  tablas, reglas (triggers),
                                               │  volumen scsl_datos          │  vistas, búsqueda
                                               └──────────────────────────────┘
```

| Capa | Carpeta | Contenedor | Puerto | Responsabilidad |
| --- | --- | --- | --- | --- |
| Presentación | `frontend/` | `scsl_web` | 8080 (publicado) | Pantallas, formularios, navegación por rol |
| Lógica / API | `backend/` | `scsl_app` | 8000 (solo red interna) | Sesiones, permisos, validaciones, PDF, Excel |
| Datos | `bd/` | `scsl_bd` | 5432 (5433 solo en el propio equipo) | Datos, reglas de negocio, búsqueda, auditoría |

**Principio de diseño: defensa en capas.** Cada regla importante se verifica dos veces: en el backend (para dar un
mensaje claro) y en la base de datos (para que se cumpla aunque alguien escriba directo en ella). Ocultar un botón en
la interfaz es solo comodidad, nunca seguridad.

---

## 2. Tecnologías y dependencias

### 2.1 Qué hay que instalar

| Para… | Necesita | Notas |
| --- | --- | --- |
| **Usar o desplegar el sistema** | **Docker Engine 24+ y Docker Compose v2** | Es lo único obligatorio. Todo lo demás viene dentro de las imágenes |
| Desarrollar la interfaz sin Docker | Node.js 22 LTS + npm | `cd frontend && npm install && npm run dev` |
| Desarrollar el backend sin Docker | Python 3.12 | `pip install -r backend/requirements.txt` |
| Ejecutar la prueba de la API | Python 3.10+ y `openpyxl` | `python backend/pruebas/prueba_api.py` |
| Editar el código | VS Code (recomendado) | Extensiones: Vue (Volar), Python, Docker |

### 2.2 Imágenes Docker

| Imagen | Versión | Uso |
| --- | --- | --- |
| `postgres` | 16 | Base de datos |
| `python` | 3.12-slim | Base del backend |
| `node` | 22-alpine | Solo para **compilar** la interfaz (no queda en producción) |
| `nginx` | 1.27-alpine | Servidor web de la interfaz |
| `alpine` | latest | Contenedor temporal del script de respaldo |
| `dpage/pgadmin4` | latest | Opcional: administrar la base desde el navegador |

### 2.3 Base de datos — extensiones de PostgreSQL

| Extensión | Para qué |
| --- | --- |
| `pgcrypto` | UUID aleatorios, contraseñas con **bcrypt** (`crypt`) y cifrado del secreto 2FA (`pgp_sym_encrypt`) |
| `pg_trgm` | Búsqueda parcial (`ILIKE`) rápida y **valores parecidos** ("Gob. Aut. La Paz" ≈ "Gobierno Autónomo de La Paz") |
| `unaccent` | Búsqueda **sin tildes**: "contratacion" encuentra "contratación" |

### 2.4 Backend — librerías de Python (`backend/requirements.txt`)

| Librería | Versión | Para qué |
| --- | --- | --- |
| `fastapi` | 0.115 | Framework web: rutas, validación, documentación automática en `/api/docs` |
| `uvicorn[standard]` | 0.34 | Servidor que ejecuta FastAPI (2 procesos) |
| `python-multipart` | 0.0.20 | Recibir archivos (PDF y Excel) en formularios |
| `psycopg[binary]` | 3.2 | Conector con PostgreSQL |
| `psycopg-pool` | 3.2 | Reutiliza conexiones a la base (hasta 10 por proceso) |
| `pyotp` | 2.9 | Segundo factor de autenticación (códigos de 6 dígitos tipo Google Authenticator) |
| `PyMuPDF` | 1.25 | Leer PDF: contar páginas, extraer texto y convertir páginas en imágenes |
| `Pillow` | 11.2 | Dibujar la **marca de agua** sobre cada página del informe |
| `openpyxl` | 3.1 | Leer el Excel histórico (.xlsx) |

### 2.5 Frontend — librerías de JavaScript (`frontend/package.json`)

| Librería | Versión | Para qué |
| --- | --- | --- |
| `vue` | 3.5 | Framework de la interfaz (componentes con `<script setup>`) |
| `vue-router` | 4.6 | Navegación entre pantallas y control de permisos por ruta |
| `pinia` | 3.0 | Estado compartido: sesión, avisos, catálogos |
| `@lucide/vue` | 1.x | Íconos |
| `@fontsource-variable/source-sans-3` y `source-serif-4` | 5.x | Tipografías incluidas (no se descargan de Internet) |
| `vite` + `@vitejs/plugin-vue` | 7 / 6 | Compilación y servidor de desarrollo |

---

## 3. Carpeta `bd/` — la base de datos

**Para qué sirve:** define la estructura de los datos **y las reglas de negocio**. Es el núcleo del sistema: aunque se
cambiara el backend o la interfaz, las reglas siguen vigentes.

```
bd/
├── init/                     Docker los ejecuta en orden, UNA sola vez (cuando el volumen está vacío)
│   ├── 01_extensiones.sql    Extensiones, normalizar_texto(), búsqueda en español sin tildes (es_legal)
│   ├── 02_tablas.sql         Tablas e índices
│   ├── 03_reglas.sql         Triggers y funciones: el flujo del trámite, permisos, auditoría inmutable
│   ├── 04_vistas.sql         Consultas guardadas: v_tramites, v_pendientes, tablero, prompts vigentes
│   ├── 05_datos_iniciales.sql Roles, permisos, matriz rol-permiso, procedencias, sitios legales, configuración
│   ├── 06_seguridad.sh       Crea la cuenta scsl_app (permisos limitados) y el primer ADMIN
│   └── 07_notificaciones.sh  Tabla notificaciones y trigger que avisa al abogado cuando se le asigna un trámite
├── pruebas/prueba_reglas.sql Prueba todas las reglas y deshace los cambios
└── respaldos/                Destino de los respaldos (no se sube a git)
```

### 3.1 Modelo de datos (resumen)

| Grupo | Tablas | Idea clave |
| --- | --- | --- |
| Acceso | `roles`, `permisos`, `roles_permisos`, `usuarios`, `sesiones`, `codigos_verificacion` | 4 roles fijos; cada usuario tiene un rol; la sesión es una fila con vencimiento |
| Catálogos | `procedencias`, `entidades`, `tipos_tramite`, `tipos_documento`, `areas`, `profesionales` | Columna `nombre_normalizado` única: no se repite el mismo valor escrito distinto |
| Trámites | `tramites`, `informes`, `precedentes` | El trámite pasa por estados; un solo informe activo; precedentes enlazan trámites entre sí |
| Prompts | `prompts` | Borrador → vigente → retirado; cuenta usos |
| Soporte | `fuentes_externas`, `importaciones_excel`, `incidencias_migracion`, `configuracion`, `auditoria` | La auditoría no se puede modificar ni borrar |
| Avisos | `notificaciones` | Un aviso por usuario; lo crea el trigger `notificar_asignacion` |

### 3.2 Lo más significativo del código

**El flujo del trámite vive en un trigger** (`tramites_antes_guardar`, en `03_reglas.sql`):

```
RECIBIDO ──(se asigna abogado)──► EN_ELABORACION ──(el abogado sube el PDF)──► CONCLUIDO ──(jefe archiva)──► ARCHIVADO
```

- Al poner `profesional_id`, la base cambia sola el estado a `EN_ELABORACION` y registra quién y cuándo asignó.
- Subir un informe (`INSERT` en `informes`) dispara otro trigger que concluye el trámite y fija la fecha de salida.
- Un trámite concluido no vuelve atrás ni cambia de abogado. Solo se archiva lo concluido.
- **Cada cambio debe indicar `actualizado_por`**: la base lo usa para verificar el permiso de esa persona con
  `usuario_tiene_permiso(usuario, 'PERMISO')`.

**Búsqueda:** cada trámite tiene `vector_busqueda` (texto indexado con pesos: códigos y asunto pesan más que el
texto del PDF). Se recalcula solo cuando cambia el trámite, su informe, sus precedentes o un nombre de catálogo.

**Seguridad en la base** (`06_seguridad.sh`): la aplicación se conecta como `scsl_app`, que **no puede** borrar
trámites, modificar la auditoría, cambiar la matriz de permisos ni alterar la estructura. Si alguien vulnerara el
backend, igual no podría saltarse esas reglas.

---

## 4. Carpeta `backend/` — la API

**Para qué sirve:** es el intermediario entre la interfaz y la base. Recibe peticiones HTTP, comprueba la sesión y
los permisos, valida los datos, ejecuta el SQL y devuelve JSON. También maneja lo que la base no puede: archivos PDF,
el Excel, la marca de agua, correos y el segundo factor.

```
backend/
├── Dockerfile               Imagen Python 3.12; corre como usuario sin privilegios
├── requirements.txt         Librerías (sección 2.4)
├── app/
│   ├── main.py              Arranque: abre el pool de conexiones, registra las rutas bajo /api
│   ├── config.py            Lee las variables de entorno (.env)
│   ├── bd.py                Pool de conexiones: una conexión y UNA transacción por petición
│   ├── errores.py           Convierte errores en { mensaje, campos } (lo que espera la interfaz)
│   ├── seguridad.py         Sesiones, usuario_actual, requiere('PERMISO'), auditar()
│   ├── correo.py            Códigos de 6 dígitos (guardados con bcrypt) y envío por SMTP
│   ├── tramites.py          Forma del trámite en las respuestas y sus permisos
│   ├── informes.py          Guarda PDF, extrae texto, genera páginas con marca de agua
│   └── rutas/               Un archivo por módulo
│       ├── acceso.py        /auth/* y /perfil/* : ingreso, 2FA, activación, recuperación
│       ├── catalogos.py     /catalogos/* : listar, sugerir parecidos, crear, unificar
│       ├── tramites.py      /tramites/* y /precedentes/* : búsqueda, flujo, PDF
│       ├── prompts.py       /prompts/* : proponer, aprobar, devolver, retirar, registrar uso
│       ├── tablero.py       /tablero y /inicio : indicadores
│       ├── administracion.py /usuarios, /roles, /auditoria, /configuracion, /fuentes
│       ├── notificaciones.py /notificaciones : campana, marcar leídas y correo de asignación
│       └── importacion.py   /importaciones/* : analizar, simular y migrar el Excel
└── pruebas/prueba_api.py    Recorre todo el sistema de punta a punta
```

### 4.1 Lo más significativo del código

**Una petición, una transacción** (`bd.py`). Cada ruta recibe `con=Depends(conexion)`. Si algo falla en cualquier
punto, nada queda a medias: la base vuelve al estado anterior.

**Sesión y permisos como dependencias** (`seguridad.py`):

```python
@rutas.patch('/tramites/{id_}/archivar')
def archivar(id_: str, u: Usuario = Depends(requiere('ARCHIVAR_TRAMITE')), con=Depends(conexion)):
```

`requiere(...)` lee el token `Authorization: Bearer <token>`, busca la fila en `sesiones`, verifica que no haya
vencido por inactividad (30 minutos, configurable) y que el rol del usuario tenga el permiso. Si no, responde 401 o
403 antes de ejecutar nada.

**Los mensajes de la base llegan al usuario** (`errores.py`). Cuando un trigger rechaza algo con
`RAISE EXCEPTION 'Solo se archiva un tramite concluido'`, el backend lo devuelve como `409 { mensaje }` y la interfaz
lo muestra tal cual.

**Informe protegido** (`informes.py`):
1. El PDF se guarda en el volumen `scsl_archivos` con un nombre aleatorio y su huella SHA-256.
2. Para verlo, cada página se convierte en imagen JPEG con una marca de agua diagonal (correo + fecha y hora de
   quien lo mira). El PDF original nunca llega al navegador de quien no tiene `DESCARGAR_INFORME`.

**Importación del Excel** (`importacion.py`): reconoce las columnas por su nombre (HR, ASUNTO, ENTIDAD…), no
inventa datos y marca lo dudoso como *incidencia*. La prueba hace la migración completa y la deshace; la definitiva
no se puede repetir con el mismo archivo (se identifica por su huella).

---

## 5. Carpeta `frontend/` — la interfaz

**Para qué sirve:** es lo que ve y usa cada persona. Muestra solo las opciones que su rol permite y habla con el
backend a través de una única capa (`src/api/`).

```
frontend/
├── Dockerfile, nginx.conf   Compila con Node y sirve con Nginx (cabeceras de seguridad, proxy /api/)
├── public/                  escudo.svg y marca/ (emblema CGE y foto de la pantalla de ingreso)
└── src/
    ├── main.js, App.vue     Arranque de Vue, Pinia y el router
    ├── api/
    │   ├── index.js         Elige el modo: real (backend) o simulado (demostración en el navegador)
    │   ├── real.js          EL CONTRATO: cada función = método + ruta + datos del backend
    │   └── simulado/        Misma API sin servidor, con las mismas reglas (para demos)
    ├── router/index.js      Rutas y permisos por ruta (redirige a /sin-permiso)
    ├── navegacion.js        Menú lateral según el rol
    ├── stores/              sesion (usuario y permisos), avisos, catalogos
    ├── views/               Una carpeta por módulo: acceso, consulta, tramites, prompts, supervision, admin
    ├── components/          Piezas reutilizables: marco/ (menú, barra, Asistentes IA), ui/, tramites/, prompts/…
    ├── composables/utiles.js useCarga, useEnvio, copiarTexto, descargarInforme
    ├── utils/               constantes (estados, roles, ASISTENTES_IA), formatos, enmascarar
    └── styles/              tokens.css (colores y tipografía), base.css, print.css
```

### 5.1 Lo más significativo del código

**Una sola puerta a los datos.** Ninguna pantalla usa `fetch` directo: todas hacen `import { api } from '@/api'`.
Por eso el mismo frontend funciona con el backend real o en modo demostración cambiando `FRONTEND_MODO`.

**Sesión** (`stores/sesion.js`): guarda el token en `sessionStorage` (se borra al cerrar el navegador) y expone
`sesion.puede('PERMISO')` para mostrar u ocultar acciones. Cierra la sesión tras 30 minutos sin actividad.

**Permisos por trámite:** el detalle de un trámite trae `permisos: { editar, asignar, concluir, archivar, ... }`
calculados por el backend; la interfaz solo los obedece.

**Diseño:** todos los colores salen de `styles/tokens.css` (incluido el azul oficial de la CGE `--cge`). La
pantalla de ingreso está en `components/acceso/MarcoAcceso.vue`.

**Notificaciones:** cuando la secretaria (o el jefe) asigna un trámite, el trigger `notificar_asignacion` de la base
crea un aviso para el abogado; si se reasigna, también avisa al anterior. La campana de la barra superior
(`components/marco/Notificaciones.vue`) consulta `/api/notificaciones` cada minuto, muestra el contador y lleva al
trámite. Si hay SMTP configurado, el backend además envía un correo.

**Asistentes de IA:** el sistema no se conecta a ninguna IA. El botón *Asistentes IA* de la barra superior y los
botones *Copiar y abrir en ChatGPT / Gemini* del catálogo de prompts copian el texto y abren la página en otra
pestaña; cada apertura queda en la auditoría. La lista está en `utils/constantes.js` (`ASISTENTES_IA`).

---

## 6. Cómo se relacionan las tres carpetas

### 6.1 Archivos que las unen

| Archivo | Une | Qué define |
| --- | --- | --- |
| `docker-compose.yml` | las tres | Contenedores, volúmenes, variables y el orden de arranque (bd → app → web) |
| `.env` | las tres | Claves y parámetros. **Nunca se sube a git** |
| `frontend/src/api/real.js` | frontend ↔ backend | Contrato de la API: si cambia una respuesta, se actualiza aquí, en `simulado/` y en `backend/app/rutas/` |
| `frontend/nginx.conf` | frontend → backend | Reenvía `/api/` a `app:8000` |
| `bd/init/06_seguridad.sh` | backend → bd | Crea la cuenta `scsl_app` con la que se conecta el backend |
| `bd/init/04_vistas.sql`, funciones de `03_reglas.sql` | backend → bd | Vistas y funciones que el backend consulta (tablero, similares, unificar) |

### 6.2 Ejemplo completo: un abogado concluye un trámite

```
1. frontend  ConcluirTramite.vue        El abogado llena tipo y número de documento y adjunta el PDF
2. frontend  api.tramites.concluir()    POST /api/tramites/{id}/concluir  (multipart + token)
3. web       nginx                      Reenvía a app:8000
4. backend   rutas/tramites.py          ¿Sesión válida? ¿Es el abogado asignado? ¿Es un PDF de menos de 50 MB?
5. backend   informes.guardar()         Guarda el archivo en /datos/informes, calcula SHA-256, páginas y texto
6. bd        UPDATE tramites ...        Trigger: verifica que el trámite siga en elaboración
7. bd        INSERT INTO informes ...   Triggers: desactiva la versión anterior, pasa a CONCLUIDO, fija fecha de salida,
                                        recalcula el índice de búsqueda con el texto del PDF
8. backend   auditar('SUBIR_INFORME')   Registro inmutable en la auditoría
9. backend   detalle()                  Devuelve el trámite actualizado con sus nuevos permisos
10. frontend                            Muestra "Concluido" y el informe en el visor protegido
```

Si cualquier paso falla (por ejemplo, el trigger rechaza), la transacción se deshace y el PDF guardado se borra.

---

## 7. Seguridad (resumen)

| Medida | Dónde |
| --- | --- |
| Contraseñas con bcrypt; bloqueo tras 5 intentos fallidos (15 min) | `seguridad.py`, `acceso.py`, tabla `usuarios` |
| Segundo factor (TOTP) opcional, con el secreto cifrado en la base | `acceso.py` + `APP_SECRETO` |
| Sesiones con vencimiento por inactividad; se revocan al salir, al desactivar al usuario o al restablecer la clave | tabla `sesiones` |
| Permisos verificados en backend **y** en la base | `requiere()` + triggers |
| Cuenta de base con mínimo privilegio | `06_seguridad.sh` |
| Auditoría inmutable de cada acción relevante | trigger `auditoria_inmutable` |
| El backend no publica puertos; la base solo escucha en el propio equipo | `docker-compose.yml` |
| Cabeceras de seguridad (CSP, X-Frame-Options, nosniff) | `frontend/nginx.conf` |
| Informes como imagen con marca de agua; descarga solo con permiso | `informes.py` |
| Contenedor del backend sin usuario root | `backend/Dockerfile` |

---

## 8. Dónde cambiar qué

| Quiero… | Archivo |
| --- | --- |
| Cambiar un plazo, el tamaño máximo del PDF o el aviso de prompts | Pantalla Administración → Configuración (tabla `configuracion`) |
| Agregar o quitar un asistente de IA | `frontend/src/utils/constantes.js` → `ASISTENTES_IA` |
| Cambiar colores o tipografía | `frontend/src/styles/tokens.css` |
| Cambiar el logo o la foto del ingreso | `frontend/public/marca/` |
| Cambiar qué puede hacer cada rol | `bd/init/05_datos_iniciales.sql` (y un script de cambio en una base ya creada) |
| Agregar un endpoint | `backend/app/rutas/` + `frontend/src/api/real.js` + `frontend/src/api/simulado/index.js` |
| Cambiar una regla del flujo | `bd/init/03_reglas.sql` (y su prueba en `bd/pruebas/prueba_reglas.sql`) |

| Probar sin tocar los datos reales | `docker-compose.prueba.yml` (copia aislada en el puerto 8081) + `backend/pruebas/prueba_api.py` |

> **Importante:** los archivos de `bd/init/` solo se ejecutan al **crear** la base. En una base con datos, los
> cambios se aplican con un script SQL puntual (`docker exec -i scsl_bd psql ... < cambio.sql`), nunca borrando el
> volumen.

# Repositorio SCSL — Interfaz web (frontend)

Vue 3 + Vite. Funciona **sin backend** en modo simulado (datos de demostración guardados en el navegador)
y en Docker se conecta al backend real (`FRONTEND_MODO=real`).

## 1. Cómo verla

**Con Docker (recomendado, igual en cualquier servidor):** desde la carpeta raíz `repositorio-scsl`:

```powershell
docker compose up -d --build web
```

Abrir `http://localhost:8080` (o `http://IP-DEL-SERVIDOR:8080` desde los thin clients).

**En su PC para desarrollar** (requiere Node.js 22):

```powershell
cd frontend
npm install
copy .env.ejemplo .env
npm run dev          # http://localhost:5173, recarga al guardar
npm run build        # genera dist/ para producción
```

**Cuentas de demostración** (clave `Demo#2026`, también aparecen como botones en la pantalla de ingreso):

| Rol | Correo |
| --- | --- |
| Administrador | admin@contraloria.gob.bo |
| Jefe | jefe@contraloria.gob.bo |
| Abogada | zenteno@contraloria.gob.bo / ampuero@contraloria.gob.bo |
| Secretaria | secretaria@contraloria.gob.bo |

En demostración, el código de activación y de recuperación es `123456`. El chip "Demostración" de la barra
superior tiene un botón para reiniciar los datos.

## 2. Pantallas

| Ruta | Pantalla | Quién |
| --- | --- | --- |
| `/ingresar`, `/activar`, `/recuperar` | Ingreso, activación de cuenta, recuperación de contraseña | Todos |
| `/` | Inicio según el rol (pendientes, por asignar, indicadores) | Todos |
| `/consulta` | Búsqueda universal con filtros, sitios legales e impresión | Todos |
| `/tramites/:id` | Expediente: recorrido, datos, informe protegido, precedentes, cadena, similares, historial | Todos |
| `/tramites/nuevo`, `/tramites/:id/editar` | Registro (7 campos) y edición | Secretaria, Jefe, Admin |
| `/asignacion` | Trámites por asignar | Secretaria, Jefe, Admin |
| `/pendientes` | Mis pendientes (abogado) / en elaboración (jefe) | Abogado, Jefe, Admin |
| `/tramites/:id/concluir` | Conclusión: 3 campos + PDF | Abogado asignado |
| `/prompts` | Catálogo de prompts: copiar y copiar enmascarado | Todos |
| `/prompts/gestion`, `/prompts/nuevo` | Proponer, revisar, aprobar, devolver, retirar | Abogado propone, Jefe aprueba |
| `/tablero` | Avance por abogado, año, tipo de documento y mes; vencidos | Jefe, Admin |
| `/admin/*` | Usuarios y roles, catálogos y sitios legales, importar Excel, auditoría, configuración | Admin |

## 3. Estructura

```
frontend/
├── src/
│   ├── api/
│   │   ├── index.js          Elige el modo (simulado o real). Las pantallas solo importan de aquí.
│   │   ├── real.js           Llamadas al backend: ES EL CONTRATO DE LA API (método, ruta, datos)
│   │   └── simulado/         Misma API sin backend, con las mismas reglas de negocio
│   ├── components/           marco/ (menú y barra), ui/ (piezas comunes), tramites/, consulta/, prompts/, admin/, acceso/
│   ├── views/                Una carpeta por módulo
│   ├── stores/               sesion (usuario y permisos), avisos, catalogos
│   ├── router/index.js       Rutas y control de permisos por ruta
│   ├── navegacion.js         Menú lateral por rol
│   ├── composables/          useCarga, useEnvio, descargas, impresión, copiar
│   ├── utils/                constantes, formatos de fecha, enmascarar datos
│   └── styles/               tokens.css (colores y tipos), base.css, print.css
├── Dockerfile, nginx.conf    Compilación y servidor web con cabeceras de seguridad
```

## 4. Modo real y modo demostración

- **Real (por defecto con Docker):** `FRONTEND_MODO=real` en el `.env` de la raíz. Nginx envía `/api/` al
  contenedor `app` (backend en `backend/`, puerto 8000 dentro de la red de Docker).
- **Demostración:** `FRONTEND_MODO=simulado` y `docker compose up -d --build web`. No usa el backend; los datos
  viven en el navegador.

El backend cumple el contrato de `src/api/real.js` con respuestas de la misma forma que
`src/api/simulado/index.js`; los errores vienen como `{ mensaje, campos? }` con su código HTTP.

## 5. Seguridad

- Ocultar un botón no es seguridad: el backend debe verificar cada permiso (la base de datos también lo hace).
- El informe se ve como imágenes con marca de agua; el PDF original solo se descarga con `DESCARGAR_INFORME`.
- La sesión se cierra tras 30 minutos sin actividad.
- Quien tiene una contraseña temporal debe cambiarla antes de usar el sistema.
- Nginx envía cabeceras de seguridad (CSP, X-Frame-Options, nosniff). No se cargan recursos de Internet:
  fuentes e iconos van incluidos en la compilación.

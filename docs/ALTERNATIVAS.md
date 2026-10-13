# Repositorio SCSL — Los 3 proyectos alternativos

Para decidir cómo integrar la **asignación según disponibilidad y carga** (lo que hoy hace el sistema de
Google Sheets + WordPress), el proyecto existe en **tres versiones paralelas**. Las tres comparten todo lo anterior
(trámites, informes, notificaciones, asistentes de IA, documentación) y se diferencian solo en esa función.

## 1. Resumen

| | **Base** | **Opción A** | **Opción B** |
| --- | --- | --- | --- |
| Idea | El repositorio tal como estaba | Disponibilidad y carga **dentro** del repositorio | Opción A **+ lee las ausencias de Google Calendar** |
| Carpeta | `Desktop\repositorio-scsl` | `Desktop\repositorio-scsl-opcion-a` | `Desktop\repositorio-scsl-opcion-b` |
| Rama git | `main` (marca `v1.0-base`) | `opcion-a` | `opcion-b` |
| Dirección | http://localhost:8080 | http://localhost:8082 | http://localhost:8083 |
| Base de datos (puerto local) | 5433 | 5435 | 5436 |
| Contenedores | `scsl_*` | `scsla_*` | `scslb_*` (+ `scslb_sincronizador`) |
| Datos | **Los reales** | De prueba (propios) | De prueba (propios) |

Cada proyecto tiene **su propia base de datos y sus propios archivos**: lo que se haga en uno no afecta a los otros.

## 2. Qué hace cada uno al asignar un trámite

| Situación | Base | Opción A | Opción B |
| --- | --- | --- | --- |
| La secretaria ve la carga de cada abogado | Barra simple | Sí, con días del pendiente más antiguo | Igual que A |
| Registrar vacaciones, permisos, bajas, comisiones | No existe | Pantalla **Ausencias del equipo** (a mano) | A mano **o automático desde Google Calendar** |
| Asignar a alguien de vacaciones | Se permite | **Se impide** (regla en la base) | **Se impide** |
| Sugerencia de a quién asignar | No | **★ Sugerido**: presente y con menos carga | Igual que A |
| Asignación automática | No | Botón **Automático** y modo *AUTOMATICA* | Igual que A |
| Avisos de próximas ausencias | No | Sí (14 días) | Sí |
| Necesita internet | No | **No** | Solo **salida** hacia Google (lectura) |
| Configuración extra | — | Ninguna | Cuenta de servicio de Google + cada profesional comparte su calendario |

## 3. Ventajas y riesgos

**Base**
- ✅ Ya funciona y es la más simple.
- ❌ La disponibilidad sigue fuera del repositorio (en Sheets/WordPress) y no se cruzan los datos.

**Opción A — recomendada para empezar**
- ✅ 100 % dentro de la red interna: cumple el principio de repositorio cerrado.
- ✅ Todo queda en la auditoría y con los mismos permisos del sistema.
- ✅ No depende de Google: si cae internet, sigue funcionando.
- ⚠️ Alguien (secretaria o jefe) debe registrar las ausencias en el repositorio.

**Opción B**
- ✅ No se cargan las ausencias dos veces: se toman del calendario que los profesionales ya usan.
- ✅ Si el calendario falla, sigue funcionando como la Opción A (las ausencias manuales siguen activas).
- ⚠️ El servidor necesita salida a internet hacia Google y una credencial (archivo de cuenta de servicio) bien custodiada.
- ⚠️ Depende de que los profesionales anoten bien sus ausencias (día completo, título claro).
- ⚠️ La conexión real con Google solo se puede comprobar con las credenciales de la institución.

**Recomendación:** empezar con la **Opción A** en producción y, si el registro manual de ausencias resulta
pesado, pasar a la **Opción B** (es la misma A más el calendario: no hay que rehacer nada).

## 4. Cómo probarlos

```powershell
# Levantar uno (cada uno en su carpeta)
cd C:\Users\PC\Desktop\repositorio-scsl-opcion-a      # o -opcion-b
docker compose up -d                                   # A: http://localhost:8082   B: http://localhost:8083

# Detenerlo sin perder sus datos de prueba
docker compose stop
```

- En A y B el administrador inicial usa `ADMIN_CORREO` / `ADMIN_CLAVE` del `.env` de **esa carpeta**.
- Las cuentas de prueba creadas por `prueba_api.py` usan la clave `Prueba#Segura2026`
  (por ejemplo `jefe.xxxxxx@prueba.gob.bo`; la lista está en *Administración → Usuarios*).
- Para empezar una opción desde cero: `docker compose down -v` **en la carpeta de esa opción** (nunca en la base).

| Prueba | Base | A | B |
| --- | --- | --- | --- |
| Reglas de la base | `bd/pruebas/prueba_reglas.sql` | + `prueba_disponibilidad.sql` | + `prueba_disponibilidad.sql` |
| API completa | `prueba_api.py` | `$env:SCSL_URL="http://localhost:8082"; $env:SCSL_APP="scsla_app"` | `…8083` y `scslb_app` |
| Calendario | — | — | `docker exec -i scslb_app python - < backend/pruebas/prueba_calendario.py` |

## 5. Cómo están hechas las copias (git)

```
                         ┌── opcion-a ── (A: disponibilidad) ──┬── opcion-b ── (B: + Google Calendar)
 main ── … ── v1.0-base ─┤                                     │
                         └─────────────────────────────────────┘
```

- **Una sola historia de git** y tres carpetas de trabajo (*worktrees*): cada carpeta muestra una rama.
- `git log --oneline --all --graph` (en cualquier carpeta) muestra las tres.
- Ver qué cambia entre ellas: `git diff main opcion-a --stat` o `git diff opcion-a opcion-b --stat`.
- `v1.0-base` es una marca fija: siempre se puede volver a "hasta donde teníamos".

> No borre la carpeta `repositorio-scsl` (la base): ahí vive la carpeta `.git` que comparten las tres.

## 6. Cuando se elija una opción

**Adoptar la Opción A o B en el sistema real** (en la carpeta base, con respaldo previo):

```powershell
cd C:\Users\PC\Desktop\repositorio-scsl
bash scripts/respaldo.sh                     # 1. respaldo
git merge opcion-a                           # 2. o: git merge opcion-b
docker exec scsl_bd bash /docker-entrypoint-initdb.d/08_disponibilidad.sh   # 3. agrega lo nuevo a la base real
docker exec scsl_bd bash /docker-entrypoint-initdb.d/09_calendario.sh       #    (solo opción B)
docker compose up -d --build                 # 4. reconstruye (en B también crea el sincronizador)
```

Los scripts del paso 3 no borran nada y se pueden repetir.

**Descartar una opción** (por ejemplo, la B):

```powershell
cd C:\Users\PC\Desktop\repositorio-scsl-opcion-b
docker compose down -v                       # borra SOLO sus contenedores y datos de prueba
cd ..\repositorio-scsl
git worktree remove ..\repositorio-scsl-opcion-b
git branch -D opcion-b                       # opcional: borra también la rama
```

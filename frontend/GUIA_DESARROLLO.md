# Guía de desarrollo del frontend — Repositorio SCSL

Vue 3 (`<script setup>`, Composition API) + Vite + Vue Router 4 + Pinia 3 + iconos `@lucide/vue`.
Todo el texto de la interfaz en **español**, en tono simple y directo, en minúsculas tipo oración (nada de
etiquetas en MAYÚSCULAS, salvo códigos y nombres de catálogo que ya vienen así). Sin emojis.

## Contexto del negocio

- 4 roles: ADMIN, JEFE, ABOGADO, SECRETARIA. Permisos en `src/api/simulado/semilla.js` (`PERMISOS_POR_ROL`).
- Flujo del trámite: RECIBIDO → (secretaria asigna abogado) EN_ELABORACION → (abogado asignado llena tipo y número
  de documento de respuesta y sube el PDF) CONCLUIDO → (jefe archiva) ARCHIVADO.
- Registro (secretaria, 7 campos): hoja de ruta, registro interno (opcional), procedencia, entidad, tipo de trámite,
  asunto (máx. 500), abogado (opcional al registrar). Opcional en "Más datos": área, observaciones.
- Conclusión (abogado asignado, 3 campos): tipo de documento, número de documento, PDF. Fecha de salida = hoy (editable).
- Solo ADMIN y JEFE descargan informes. Los demás ven el informe en el visor protegido (imágenes con marca de agua).
- Catálogo de prompts: el sistema NO usa IA. Ofrece prompts aprobados por tipo de documento, que el doctor copia
  y pega en su propia IA. Proponen ABOGADO y JEFE; aprueba/devuelve/retira el JEFE. Cada copia se registra.
- Los registros con `origen_registro === 'MIGRACION'` vienen del Excel histórico (pueden tener campos vacíos).

## Reglas de código

- Datos SIEMPRE por `import { api } from '@/api'`. Nunca `fetch` directo. Contrato y formas de respuesta: leer
  `src/api/real.js` (comentarios) y `src/api/simulado/index.js` (implementación; ver `expandir()` para la forma del trámite).
- Permisos en la interfaz: `const sesion = useSesion(); sesion.puede('DESCARGAR_INFORME')`, `sesion.rol`, `sesion.usuario`.
  En el detalle de un trámite usar `tramite.permisos.{editar, asignar, concluir, archivar, baja, descargar, precedentes}`.
- Mensajes: `useAvisos().exito('Trámite registrado')` / `.error(msg)`.
- Formularios: `useEnvio()` de `@/composables/utiles` → `errores` por campo (`errores.value.asunto`), `enviando`, `enviar(fn, msgExito)`.
- Cargas: `useCarga(fn)` → `datos, cargando, error, cargar`.
- Catálogos para filtros/listas: `useCatalogos().obtener('entidades')` (cache) o el componente `CampoCatalogo`.
- Fechas/números: `@/utils/formato` (`formatoFecha`, `formatoFechaHora`, `formatoNumero`, `plural`, `diasDesde`).
- Constantes: `@/utils/constantes` (ESTADOS_TRAMITE, ROLES, CATEGORIAS_PROMPT, ESTADOS_PROMPT, RELEVANCIAS, TIPOS_RELACION, CATALOGOS, ACCIONES_AUDITORIA).
- Colores: SOLO variables de `src/styles/tokens.css`. Nunca hexadecimales en componentes.
- Estilos: reutilizar clases de `src/styles/base.css` (`.pagina`, `.pagina-cabecera`, `.panel`, `.panel-cabecera`,
  `.panel-cuerpo`, `.boton`, `.boton-primario`, `.boton-peligro`, `.boton-fantasma`, `.boton-pequeno`, `.formulario`,
  `.formulario-2`, `.campo`, `.campo-ancho`, `.entrada`, `.seleccion`, `.area-texto`, `.ayuda`, `.error-campo`,
  `.tabla-contenedor`, `.tabla`, `.codigo`, `.codigo-sello`, `.insignia*`, `.mensaje mensaje-*`, `.pestanas/.pestana`,
  `.datos`, `.fila`, `.fila-entre`, `.rejilla-2/3`, `.texto-2/3`, `.no-imprimir`). `<style scoped>` solo para lo propio.
- Accesibilidad: cada campo con `<label for>`, `aria-invalid` con error, botones con texto o `aria-label`.
- Adaptable hasta 360 px de ancho (thin clients y móviles). Sin scroll horizontal salvo tablas en `.tabla-contenedor`.
- No usar `window.alert/confirm`: usar el componente `Modal` para confirmaciones.

## Componentes disponibles

| Componente | Uso |
| --- | --- |
| `@/components/ui/Modal.vue` | `<Modal v-model="abierto" titulo="..." ancho="560px">…<template #pie>botones</template></Modal>` |
| `@/components/ui/CampoCatalogo.vue` | combobox de catálogo con sugerencias y alta en línea: `v-model`, `tipo`, `etiqueta`, `requerido`, `permitir-agregar`, `error`, `ayuda`, `filtro` (fn), evento `cambio` |
| `@/components/ui/EstadoTramite.vue` | `<EstadoTramite :estado="t.estado_tramite" :vencido="t.vencido" />` |
| `@/components/ui/RielEstado.vue` | recorrido de 4 sellos: `<RielEstado :tramite="t" />` |
| `@/components/ui/Paginacion.vue` | `<Paginacion :pagina :paginas :total @cambiar="fn" />` |
| `@/components/ui/EstadoVacio.vue` | `<EstadoVacio :icono="X" titulo="..." texto="...">acciones</EstadoVacio>` |
| `@/components/ui/Cargando.vue` | `<Cargando texto="..." />` |
| `@/components/ui/GraficoBarras.vue` | barras horizontales apiladas: `:filas="[{nombre, valores:{clave:n}}]" :series="[{clave, etiqueta, color:'var(--concluido)'}]"` |
| `@/components/ui/EncabezadoImpresion.vue` | encabezado institucional que solo sale al imprimir |
| `@/components/tramites/TarjetaTramite.vue` | tarjeta de resultado: `:tramite`, `:vencido`, slot `acciones` |
| `@/components/tramites/VisorInforme.vue` | `<VisorInforme v-model="abierto" :tramite="detalle" />` (necesita el detalle con `informe` y `permisos`) |
| `@/composables/utiles.js` | `useCarga`, `useEnvio`, `descargarInforme(t)`, `imprimirConAuditoria(detalle)`, `copiarTexto(texto)` |
| `@/utils/enmascarar.js` | `enmascarar(texto) -> { texto, ocultos }` (para "Copiar enmascarado") |

## Diseño

Identidad institucional sobria: tinta azul oscuro (`--tinta`), azul de acción (`--sello`), fondo gris frío.
Títulos de página en serif (`h1`, `h2` ya lo aplican). El elemento distintivo son los **códigos de documento**
(`.codigo-sello`): úsalos para identificar trámites. Datos en tablas o listas con divisores, no todo en tarjetas.
Movimiento mínimo. Cabecera de página: `<div class="pagina"><header class="pagina-cabecera"><div><h1>…</h1><p>una frase de qué se hace aquí</p></div><div class="pagina-acciones">…</div></header>…</div>`.

## Verificación

- Compilar sin errores: `npm run build`.
- Si cambia una respuesta de la API, actualice los tres lugares a la vez: `src/api/real.js` (contrato),
  `src/api/simulado/index.js` (demostración) y el backend (`backend/app/rutas/`).
- Probar contra el backend real: `docker compose up -d --build` en la raíz y `python backend/pruebas/prueba_api.py`.
- Cuentas de demostración del modo simulado (clave `Demo#2026`): admin@, jefe@, zenteno@ (abogada),
  ampuero@ (abogada), secretaria@ — todas `@contraloria.gob.bo`.

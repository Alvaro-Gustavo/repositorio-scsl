// ============================================================
// Implementacion REAL: llama a la API del backend.
// Este archivo ES el contrato que el backend debe cumplir:
// cada funcion indica metodo, ruta, entrada y salida esperada.
// El modo simulado (./simulado) implementa exactamente las mismas funciones.
// ============================================================
import { ErrorApi } from './errores'

const BASE = (import.meta.env.VITE_API_URL || '/api').replace(/\/$/, '')
let token = null

export function fijarToken(t) { token = t }

async function pedir(metodo, ruta, { cuerpo, consulta, formulario, binario } = {}) {
  const url = new URL(BASE + ruta, window.location.origin)
  if (consulta) {
    for (const [k, v] of Object.entries(consulta)) {
      if (v !== undefined && v !== null && v !== '') url.searchParams.set(k, v)
    }
  }
  const cabeceras = { Accept: binario ? '*/*' : 'application/json' }
  if (token) cabeceras.Authorization = `Bearer ${token}`
  let body
  if (formulario) body = formulario
  else if (cuerpo !== undefined) { cabeceras['Content-Type'] = 'application/json'; body = JSON.stringify(cuerpo) }

  let r
  try {
    r = await fetch(url, { method: metodo, headers: cabeceras, body, credentials: 'same-origin' })
  } catch {
    throw new ErrorApi('No se pudo conectar con el servidor. Verifique la red interna.', 0)
  }
  if (r.status === 204) return null
  if (!r.ok) {
    let datos = {}
    try { datos = await r.json() } catch { /* sin cuerpo */ }
    if (r.status === 401) window.dispatchEvent(new CustomEvent('scsl:sesion-expirada'))
    throw new ErrorApi(datos.mensaje || datos.detail || `Error ${r.status}`, r.status, datos.campos || null)
  }
  if (binario) return r.blob()
  return r.json()
}

const get = (ruta, consulta) => pedir('GET', ruta, { consulta })
const post = (ruta, cuerpo) => pedir('POST', ruta, { cuerpo })
const put = (ruta, cuerpo) => pedir('PUT', ruta, { cuerpo })
const patch = (ruta, cuerpo) => pedir('PATCH', ruta, { cuerpo })
const del = (ruta) => pedir('DELETE', ruta)

export const api = {
  modo: 'real',

  auth: {
    // POST /auth/ingresar {correo, clave, codigo_2fa?} -> {token, usuario}
    ingresar: (datos) => post('/auth/ingresar', datos),
    // POST /auth/salir -> 204
    salir: () => post('/auth/salir'),
    // GET /auth/sesion -> usuario (con rol y permisos[])
    sesion: () => get('/auth/sesion'),
    // POST /auth/activar {correo, codigo, clave} -> 204
    activar: (datos) => post('/auth/activar', datos),
    // POST /auth/recuperar {correo} -> 204 (siempre, exista o no el correo)
    solicitarRecuperacion: (datos) => post('/auth/recuperar', datos),
    // POST /auth/restablecer {correo, codigo, clave} -> 204
    restablecer: (datos) => post('/auth/restablecer', datos)
  },

  perfil: {
    // PUT /perfil {nombre_completo, cargo} -> usuario
    actualizar: (datos) => put('/perfil', datos),
    // POST /perfil/clave {actual, nueva} -> 204
    cambiarClave: (datos) => post('/perfil/clave', datos),
    // POST /perfil/2fa/iniciar -> {secreto, uri}; POST /perfil/2fa/confirmar {codigo}; DELETE /perfil/2fa
    iniciar2fa: () => post('/perfil/2fa/iniciar'),
    confirmar2fa: (codigo) => post('/perfil/2fa/confirmar', { codigo }),
    desactivar2fa: () => del('/perfil/2fa')
  },

  catalogos: {
    // GET /catalogos/{tipo}?inactivos=1 -> [{id, nombre, activo, ...}]
    // tipo: procedencias | entidades | tipos_tramite | tipos_documento | areas | profesionales
    listar: (tipo, { inactivos = false } = {}) => get(`/catalogos/${tipo}`, { inactivos: inactivos ? 1 : '' }),
    // GET /catalogos/{tipo}/sugerencias?texto= -> [{id, nombre, parecido(0-100)}]
    sugerir: (tipo, texto) => get(`/catalogos/${tipo}/sugerencias`, { texto }),
    // POST /catalogos/{tipo} {nombre, usuario_id?} -> valor creado (409 si ya existe: {mensaje, existente})
    crear: (tipo, datos) => post(`/catalogos/${tipo}`, datos),
    // PUT /catalogos/{tipo}/{id} {nombre?, activo?, usuario_id?} -> valor
    actualizar: (tipo, id, datos) => put(`/catalogos/${tipo}/${id}`, datos),
    // POST /catalogos/{tipo}/unificar {conservar, eliminar} -> {movidos}
    unificar: (tipo, conservar, eliminar) => post(`/catalogos/${tipo}/unificar`, { conservar, eliminar })
  },

  tramites: {
    // GET /tramites?q=&anio=&estado=&entidad_id=&tipo_tramite_id=&tipo_documento_id=&profesional_id=&procedencia_id=
    //     &orden=relevancia|reciente|antiguo&pagina=1&por_pagina=10&en=contenido? -> {items[], total, pagina, paginas}
    //     con q, cada item trae coincidencias_informe: {total, fragmentos: [{pagina, partes: [{texto, marca}]}]} | null
    buscar: (filtros) => get('/tramites', filtros),
    // GET /tramites/{id} -> tramite completo (informe, precedentes, citado_por, historial)
    obtener: (id) => get(`/tramites/${id}`),
    // POST /tramites {hoja_ruta, registro_interno, procedencia_id, entidad_id, tipo_tramite_id, asunto,
    //                 profesional_id?, area_id?, observaciones?} -> tramite
    crear: (datos) => post('/tramites', datos),
    // PUT /tramites/{id} {...campos editables} -> tramite
    actualizar: (id, datos) => put(`/tramites/${id}`, datos),
    // PATCH /tramites/{id}/asignar {profesional_id} -> tramite
    asignar: (id, profesional_id) => patch(`/tramites/${id}/asignar`, { profesional_id }),
    // POST /tramites/{id}/concluir multipart: tipo_documento_id, numero_documento, fecha_salida?, archivo(PDF) -> tramite
    concluir: (id, { tipo_documento_id, numero_documento, fecha_salida, archivo }) => {
      const f = new FormData()
      f.set('tipo_documento_id', tipo_documento_id)
      f.set('numero_documento', numero_documento)
      if (fecha_salida) f.set('fecha_salida', fecha_salida)
      f.set('archivo', archivo)
      return pedir('POST', `/tramites/${id}/concluir`, { formulario: f })
    },
    // PATCH /tramites/{id}/archivar -> tramite
    archivar: (id) => patch(`/tramites/${id}/archivar`),
    // PATCH /tramites/{id}/baja {motivo} -> tramite
    darDeBaja: (id, motivo) => patch(`/tramites/${id}/baja`, { motivo }),
    // GET /tramites/pendientes -> [tramite] (los EN_ELABORACION del abogado en sesion; jefe/admin: todos)
    pendientes: () => get('/tramites/pendientes'),
    // GET /tramites/por-asignar -> [tramite] (RECIBIDO)
    porAsignar: () => get('/tramites/por-asignar'),
    // GET /tramites/{id}/similares -> [{tramite, afinidad}]
    similares: (id) => get(`/tramites/${id}/similares`),
    // GET /tramites/{id}/informe/paginas -> {paginas, marca} ; GET /tramites/{id}/informe/paginas/{n} -> imagen PNG con marca de agua
    paginasInforme: (id) => get(`/tramites/${id}/informe/paginas`),
    // GET /tramites/{id}/informe/coincidencias?q= -> {q, total, paginas: [[[x0, y0, x1, y1]] por página, en fracciones 0-1]}
    coincidenciasInforme: (id, q) => get(`/tramites/${id}/informe/coincidencias`, { q }),
    urlPaginaInforme: (id, n) => `${BASE}/tramites/${id}/informe/paginas/${n}`,
    // GET /tramites/{id}/informe/descargar -> PDF (solo DESCARGAR_INFORME)
    descargarInforme: (id) => pedir('GET', `/tramites/${id}/informe/descargar`, { binario: true })
  },

  precedentes: {
    // POST /tramites/{id}/precedentes {tramite_precedente_id, criterio_legal, relevancia, tipo_relacion, observaciones?}
    crear: (tramiteId, datos) => post(`/tramites/${tramiteId}/precedentes`, datos),
    // DELETE /precedentes/{id}
    eliminar: (id) => del(`/precedentes/${id}`)
  },

  prompts: {
    // GET /prompts?tipo_documento_id=&categoria=&q= -> [prompt vigente]
    vigentes: (filtros) => get('/prompts', filtros),
    // GET /prompts/gestion?estado= -> [prompt] (propios para ABOGADO; todos para JEFE)
    gestion: (filtros) => get('/prompts/gestion', filtros),
    // POST /prompts {titulo, categoria, tipo_documento_id?, texto, instrucciones?} -> prompt (BORRADOR)
    proponer: (datos) => post('/prompts', datos),
    // PUT /prompts/{id} {...} -> prompt
    actualizar: (id, datos) => put(`/prompts/${id}`, datos),
    // PATCH /prompts/{id}/aprobar | /devolver {observacion} | /retirar
    aprobar: (id) => patch(`/prompts/${id}/aprobar`),
    devolver: (id, observacion) => patch(`/prompts/${id}/devolver`, { observacion }),
    retirar: (id) => patch(`/prompts/${id}/retirar`),
    // POST /prompts/{id}/uso {tramite_id?} -> 204 (suma uso y audita COPIAR_PROMPT)
    registrarUso: (id, tramite_id) => post(`/prompts/${id}/uso`, { tramite_id })
  },

  tablero: {
    // GET /tablero?anio= -> {totales, por_abogado[], por_anio[], por_tipo_documento[], vencidos[], plazo_dias}
    resumen: (filtros) => get('/tablero', filtros),
    // GET /inicio -> resumen corto segun el rol del usuario
    inicio: () => get('/inicio')
  },

  usuarios: {
    listar: () => get('/usuarios'),
    // POST /usuarios {nombre_completo, correo, cargo, rol} -> usuario (envia codigo de activacion)
    crear: (datos) => post('/usuarios', datos),
    actualizar: (id, datos) => put(`/usuarios/${id}`, datos),
    activar: (id, activo) => patch(`/usuarios/${id}/activo`, { activo }),
    reenviarActivacion: (id) => post(`/usuarios/${id}/reenviar-activacion`),
    // GET /roles -> [{nombre, descripcion, permisos[]}]
    roles: () => get('/roles')
  },

  auditoria: {
    // GET /auditoria?usuario_id=&accion=&modulo=&resultado=&desde=&hasta=&pagina= -> {items, total, pagina, paginas}
    listar: (filtros) => get('/auditoria', filtros),
    // POST /auditoria/eventos {accion, modulo, detalle} (impresiones y fuentes externas)
    registrar: (evento) => post('/auditoria/eventos', evento)
  },

  importacion: {
    // POST /importaciones/analizar multipart archivo -> {id, archivo, huella, resumen, columnas[], muestra[], incidencias[]}
    analizar: (archivo) => { const f = new FormData(); f.set('archivo', archivo); return pedir('POST', '/importaciones/analizar', { formulario: f }) },
    // POST /importaciones/{id}/ejecutar {modo: SIMULACION|DEFINITIVA} -> resultado
    ejecutar: (id, modo) => post(`/importaciones/${id}/ejecutar`, { modo }),
    historial: () => get('/importaciones')
  },

  notificaciones: {
    // GET /notificaciones -> {items: [{id, tipo, titulo, mensaje, tramite_id, leida_en, creado_en, creado_por}], no_leidas}
    listar: () => get('/notificaciones'),
    // PATCH /notificaciones/{id}/leida -> 204
    marcarLeida: (id) => patch(`/notificaciones/${id}/leida`),
    // POST /notificaciones/leer-todas -> 204
    marcarTodas: () => post('/notificaciones/leer-todas')
  },

  configuracion: {
    listar: () => get('/configuracion'),
    actualizar: (clave, valor) => put(`/configuracion/${clave}`, { valor })
  },

  fuentes: {
    listar: () => get('/fuentes'),
    crear: (datos) => post('/fuentes', datos),
    actualizar: (id, datos) => put(`/fuentes/${id}`, datos)
  }
}

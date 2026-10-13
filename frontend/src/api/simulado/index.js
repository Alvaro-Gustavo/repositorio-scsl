// ============================================================
// Implementacion SIMULADA de la API (sin backend).
// Mismas funciones y respuestas que ../real.js. Aplica las mismas reglas
// de negocio que la base de datos para que la interfaz se comporte igual.
// Los datos se guardan en el navegador (localStorage) y se pueden reiniciar.
// ============================================================
import { ErrorApi } from '../errores'
import { crearSemilla, permisosDeRol, ROLES_DEMO, CLAVE_DEMO } from './semilla'

const CLAVE_ALMACEN = 'scsl_demo_v1'
const CLAVE_SESION = 'scsl_demo_sesion'

let bd = cargar()
let usuarioActual = null
try { usuarioActual = JSON.parse(sessionStorage.getItem(CLAVE_SESION) || 'null') } catch { usuarioActual = null }

function cargar() {
  try {
    const guardado = JSON.parse(localStorage.getItem(CLAVE_ALMACEN) || 'null')
    if (guardado?.version === 1) return guardado
  } catch { /* almacen no disponible */ }
  return crearSemilla()
}
function guardar() {
  try { localStorage.setItem(CLAVE_ALMACEN, JSON.stringify(bd)) } catch { /* sin almacen: queda en memoria */ }
}
const esperar = (ms = 180) => new Promise((r) => setTimeout(r, ms + Math.random() * 120))
const copia = (x) => JSON.parse(JSON.stringify(x))
const ahora = () => new Date().toISOString()
const nuevoId = (prefijo) => `${prefijo}-${++bd.secuencia}`
const normalizar = (t) => String(t ?? '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/\s+/g, ' ').trim()

// ---------------- Sesion y permisos ----------------
function yo() {
  if (!usuarioActual) throw new ErrorApi('Su sesión expiró. Ingrese nuevamente.', 401)
  const u = bd.usuarios.find((x) => x.id === usuarioActual.id)
  if (!u || !u.activo) throw new ErrorApi('Su cuenta está desactivada.', 401)
  return u
}
const puede = (u, permiso) => permisosDeRol(u.rol).includes(permiso)
function requiere(permiso) {
  const u = yo()
  if (!puede(u, permiso)) throw new ErrorApi('No tiene permisos para realizar esta operación.', 403)
  return u
}
function auditar(accion, modulo, objeto_tipo = null, objeto_id = null, resultado = 'EXITOSO', detalle = null, usuario = usuarioActual) {
  bd.auditoria.push({
    id: bd.auditoria.length + 1, creado_en: ahora(), usuario_id: usuario?.id ?? null, usuario_correo: usuario?.correo ?? 'sistema',
    accion, modulo, objeto_tipo, objeto_id: objeto_id == null ? null : String(objeto_id), resultado, ip: '127.0.0.1', detalle
  })
}
function usuarioPublico(u) {
  if (!u) return null
  const { clave, ...resto } = u
  return { ...copia(resto), permisos: permisosDeRol(u.rol) }
}
const persona = (id) => {
  const u = bd.usuarios.find((x) => x.id === id)
  return u ? { id: u.id, nombre_completo: u.nombre_completo } : null
}

// ---------------- Catalogos ----------------
const cat = (tipo) => {
  const lista = bd.catalogos[tipo]
  if (!lista) throw new ErrorApi('Catálogo desconocido.', 404)
  return lista
}
const ref = (tipo, id) => {
  if (id == null) return null
  const v = bd.catalogos[tipo].find((x) => x.id === id)
  return v ? { id: v.id, nombre: v.nombre } : null
}
function similitud(a, b) {
  // Similitud por trigramas, como pg_trgm.
  const tri = (s) => { const t = `  ${normalizar(s)} `; const r = new Set(); for (let i = 0; i < t.length - 2; i++) r.add(t.slice(i, i + 3)); return r }
  const x = tri(a); const y = tri(b)
  let comun = 0
  x.forEach((g) => { if (y.has(g)) comun++ })
  return comun / (x.size + y.size - comun || 1)
}

// ---------------- Tramites ----------------
function expandir(t, detalle = false) {
  const prof = t.profesional_id ? bd.catalogos.profesionales.find((p) => p.id === t.profesional_id) : null
  const base = {
    id: t.id, hoja_ruta: t.hoja_ruta, registro_interno: t.registro_interno, anio_gestion: t.anio_gestion,
    procedencia: ref('procedencias', t.procedencia_id), entidad: ref('entidades', t.entidad_id),
    tipo_tramite: ref('tipos_tramite', t.tipo_tramite_id), asunto: t.asunto,
    profesional: prof ? { id: prof.id, nombre_completo: prof.nombre, usuario_id: prof.usuario_id } : null,
    tipo_documento: ref('tipos_documento', t.tipo_documento_id), numero_documento: t.numero_documento,
    fecha_salida: t.fecha_salida, area: ref('areas', t.area_id), observaciones: t.observaciones,
    estado_tramite: t.estado_tramite, baja_motivo: t.baja_motivo || null, asignado_por: persona(t.asignado_por), fecha_asignacion: t.fecha_asignacion,
    fecha_conclusion: t.fecha_conclusion, activo: t.activo, origen_registro: t.origen_registro,
    creado_por: persona(t.creado_por), creado_en: t.creado_en, actualizado_en: t.actualizado_en,
    tiene_informe: !!t.informe,
    cantidad_precedentes: bd.precedentes.filter((p) => p.tramite_id === t.id).length
  }
  if (!detalle) return base
  const u = yo()
  const resumen = (id) => {
    const x = bd.tramites.find((y) => y.id === id)
    return x ? { id: x.id, hoja_ruta: x.hoja_ruta, numero_documento: x.numero_documento, asunto: x.asunto,
      entidad: ref('entidades', x.entidad_id), fecha_salida: x.fecha_salida, tiene_informe: !!x.informe, estado_tramite: x.estado_tramite } : null
  }
  const pre = (p, campo) => ({
    id: p.id, tramite: resumen(p[campo]), criterio_legal: p.criterio_legal, relevancia: p.relevancia,
    tipo_relacion: p.tipo_relacion, origen: p.origen, observaciones: p.observaciones,
    creado_por: persona(p.creado_por), creado_en: p.creado_en
  })
  const esAsignado = prof?.usuario_id === u.id
  const esPropio = t.creado_por === u.id || esAsignado
  const activoSistema = t.activo && t.origen_registro === 'SISTEMA'
  return {
    ...base,
    informe: t.informe ? {
      id: t.informe.id, nombre_original: t.informe.nombre_original, paginas: t.informe.paginas,
      tamano_bytes: t.informe.tamano_bytes, subido_por: persona(t.informe.subido_por), subido_en: t.informe.subido_en,
      versiones: t.informe.versiones
    } : null,
    precedentes: bd.precedentes.filter((p) => p.tramite_id === t.id).map((p) => pre(p, 'tramite_precedente_id')),
    citado_por: bd.precedentes.filter((p) => p.tramite_precedente_id === t.id).map((p) => pre(p, 'tramite_id')),
    historial: bd.auditoria.filter((a) => a.objeto_tipo === 'tramite' && a.objeto_id === t.id
      && ['CREAR_TRAMITE', 'EDITAR_TRAMITE', 'ASIGNAR_TRAMITE', 'SUBIR_INFORME', 'ARCHIVAR_TRAMITE', 'BAJA_TRAMITE'].includes(a.accion))
      .map((a) => ({ fecha: a.creado_en, accion: a.accion, usuario: a.usuario_correo, detalle: a.detalle })).reverse(),
    permisos: {
      editar: t.activo && (puede(u, 'EDITAR_TODOS') || (puede(u, 'EDITAR_PROPIOS') && esPropio)) && t.estado_tramite !== 'ARCHIVADO',
      asignar: activoSistema && puede(u, 'ASIGNAR_TRAMITE') && ['RECIBIDO', 'EN_ELABORACION'].includes(t.estado_tramite),
      concluir: t.activo && ['EN_ELABORACION', 'CONCLUIDO'].includes(t.estado_tramite) && ((esAsignado && puede(u, 'SUBIR_INFORME')) || u.rol === 'ADMIN'),
      archivar: activoSistema && t.estado_tramite === 'CONCLUIDO' && puede(u, 'ARCHIVAR_TRAMITE'),
      baja: t.activo && puede(u, 'ELIMINAR_LOGICO'),
      descargar: !!t.informe && puede(u, 'DESCARGAR_INFORME'),
      precedentes: t.activo && puede(u, 'GESTIONAR_PRECEDENTES')
    }
  }
}
function buscarTramite(id) {
  const t = bd.tramites.find((x) => x.id === id)
  if (!t) throw new ErrorApi('El trámite no existe.', 404)
  return t
}
function textoBuscable(t) {
  return normalizar([
    t.hoja_ruta, t.registro_interno, t.numero_documento, t.asunto, t.observaciones, t.anio_gestion,
    ref('entidades', t.entidad_id)?.nombre, ref('tipos_tramite', t.tipo_tramite_id)?.nombre,
    ref('tipos_documento', t.tipo_documento_id)?.nombre, ref('areas', t.area_id)?.nombre,
    ref('procedencias', t.procedencia_id)?.nombre,
    bd.catalogos.profesionales.find((p) => p.id === t.profesional_id)?.nombre,
    ...bd.precedentes.filter((p) => p.tramite_id === t.id).map((p) => p.criterio_legal),
    t.informe?.texto
  ].filter(Boolean).join(' '))
}
function validarRegistro(d) {
  const campos = {}
  if (!d.hoja_ruta?.trim()) campos.hoja_ruta = 'Ingrese la hoja de ruta.'
  if (!d.procedencia_id) campos.procedencia_id = 'Seleccione la procedencia.'
  if (!d.entidad_id) campos.entidad_id = 'Seleccione o agregue la entidad.'
  if (!d.tipo_tramite_id) campos.tipo_tramite_id = 'Seleccione el tipo de trámite.'
  const max = Number(bd.configuracion.find((c) => c.clave === 'asunto_max_caracteres')?.valor || 500)
  if (!d.asunto?.trim()) campos.asunto = 'Describa el asunto.'
  else if (d.asunto.length > max) campos.asunto = `El asunto admite hasta ${max} caracteres.`
  if (Object.keys(campos).length) throw new ErrorApi('Revise los campos marcados.', 422, campos)
}
// Igual que el trigger notificar_asignacion de la base: avisa al abogado nuevo y al anterior.
function notificarAsignacion(t, anterior, u) {
  bd.notificaciones ||= []
  const cuenta = (pid) => bd.catalogos.profesionales.find((p) => p.id === pid)?.usuario_id
  const aviso = (usuario_id, tipo, titulo, mensaje) => {
    if (!usuario_id || usuario_id === u.id) return
    bd.notificaciones.push({ id: ++bd.secuencia, usuario_id, tipo, titulo, mensaje, tramite_id: t.id, leida_en: null,
      creado_en: ahora(), creado_por: persona(u.id) })
  }
  if (t.profesional_id === anterior) return
  aviso(cuenta(t.profesional_id), 'TRAMITE_ASIGNADO', `Nuevo trámite asignado: ${t.hoja_ruta}`,
    `${t.asunto.slice(0, 300)} — Asignado por ${u.nombre_completo}.`)
  if (anterior) aviso(cuenta(anterior), 'TRAMITE_REASIGNADO', `Trámite reasignado: ${t.hoja_ruta}`,
    `Ya no está a su cargo. Reasignado por ${u.nombre_completo}.`)
}
function aplicarAsignacion(t, profesional_id, u) {
  const anterior = t.profesional_id
  aplicarAsignacionSinAviso(t, profesional_id, u)
  notificarAsignacion(t, anterior, u)
}
function aplicarAsignacionSinAviso(t, profesional_id, u) {
  if (!puede(u, 'ASIGNAR_TRAMITE')) throw new ErrorApi('No tiene permiso para asignar trámites.', 403)
  if (['CONCLUIDO', 'ARCHIVADO'].includes(t.estado_tramite)) throw new ErrorApi('No se cambia el abogado de un trámite concluido.', 409)
  if (!profesional_id) {
    Object.assign(t, { profesional_id: null, estado_tramite: 'RECIBIDO', fecha_asignacion: null, asignado_por: null })
    return
  }
  const p = bd.catalogos.profesionales.find((x) => x.id === Number(profesional_id) && x.activo)
  const cuenta = p && bd.usuarios.find((x) => x.id === p.usuario_id && x.activo && x.rol === 'ABOGADO')
  if (!cuenta) throw new ErrorApi('Solo se asigna a un abogado con cuenta activa en el sistema.', 409)
  Object.assign(t, { profesional_id: p.id, estado_tramite: 'EN_ELABORACION', fecha_asignacion: ahora(), asignado_por: u.id })
}
function paginar(lista, pagina = 1, porPagina = 10) {
  const p = Math.max(1, Number(pagina) || 1)
  const n = Math.max(1, Math.min(100, Number(porPagina) || 10))
  return { items: lista.slice((p - 1) * n, p * n), total: lista.length, pagina: p, paginas: Math.max(1, Math.ceil(lista.length / n)), por_pagina: n }
}
const parametro = (clave, defecto) => Number(bd.configuracion.find((c) => c.clave === clave)?.valor) || defecto
const plazo = () => Number(bd.configuracion.find((c) => c.clave === 'plazo_dias_tramite')?.valor) || null
const diasDesde = (f) => (f ? Math.floor((Date.now() - new Date(f).getTime()) / 86400000) : null)

// Paginas del informe: imagen SVG con marca de agua del usuario (en el backend real sera un PNG).
function paginaSvg(t, n, total, u) {
  const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  const palabras = (n === 1 ? t.informe.texto : `${t.informe.texto} Se recomienda remitir el presente informe a la autoridad competente para su consideración.`).split(' ')
  const lineas = []
  let linea = ''
  for (const w of palabras) { if ((linea + ' ' + w).length > 78) { lineas.push(linea); linea = w } else linea = linea ? `${linea} ${w}` : w }
  if (linea) lineas.push(linea)
  const marca = esc(`${u.correo} · ${new Date().toLocaleString('es-BO')}`)
  const cuerpo = lineas.map((l, i) => `<text x="70" y="${n === 1 ? 300 + i * 26 : 140 + i * 26}" font-size="15">${esc(l)}</text>`).join('')
  const encabezado = n === 1 ? `<text x="420" y="110" text-anchor="middle" font-size="20" font-weight="700">CONTRALORÍA GENERAL DEL ESTADO</text>
    <text x="420" y="140" text-anchor="middle" font-size="15">Subcontraloría de Servicios Legales</text>
    <text x="420" y="200" text-anchor="middle" font-size="17" font-weight="700">${esc(t.tipo_documento_id ? ref('tipos_documento', t.tipo_documento_id).nombre.toUpperCase() : 'INFORME')} ${esc(t.numero_documento || '')}</text>
    <text x="70" y="250" font-size="15">REF.: ${esc(t.asunto.slice(0, 70))}</text>` : ''
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 840 1188" font-family="Georgia, serif" fill="#222">
    <rect width="840" height="1188" fill="#fff"/>${encabezado}${cuerpo}
    <text x="420" y="1140" text-anchor="middle" font-size="13" fill="#666">Página ${n} de ${total}</text>
    <g transform="rotate(-35 420 594)" fill="#1f5fa8" fill-opacity="0.13" font-family="Arial, sans-serif" font-size="30" font-weight="700" text-anchor="middle">
      <text x="420" y="420">${marca}</text><text x="420" y="620">SOLO LECTURA · ${marca}</text><text x="420" y="820">${marca}</text>
    </g></svg>`
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`
}

async function op(fn, ms) {
  await esperar(ms)
  const r = fn()
  guardar()
  return r === undefined ? null : copia(r)
}

// ============================================================
export const api = {
  modo: 'simulado',

  demo: {
    cuentas: () => bd.usuarios.filter((u) => u.activo).map((u) => ({ correo: u.correo, rol: u.rol, nombre: u.nombre_completo })),
    claveDemo: CLAVE_DEMO,
    reiniciar: () => { bd = crearSemilla(); guardar() }
  },

  auth: {
    ingresar: ({ correo, clave }) => op(() => {
      const u = bd.usuarios.find((x) => x.correo.toLowerCase() === String(correo || '').trim().toLowerCase())
      if (u?.bloqueado_hasta && new Date(u.bloqueado_hasta) > new Date()) {
        auditar('INICIO_SESION_FALLIDO', 'ACCESO', 'usuario', u.id, 'BLOQUEADO', null, u)
        throw new ErrorApi(`La cuenta está bloqueada por intentos fallidos. Intente en ${parametro('ingreso_bloqueo_minutos', 15)} minutos.`, 423)
      }
      if (!u || u.clave !== clave || !u.activo) {
        if (u) {
          u.intentos_fallidos = (u.intentos_fallidos || 0) + 1
          if (u.intentos_fallidos >= parametro('ingreso_max_intentos', 5)) { u.bloqueado_hasta = new Date(Date.now() + parametro('ingreso_bloqueo_minutos', 15) * 60000).toISOString(); u.intentos_fallidos = 0 }
          auditar('INICIO_SESION_FALLIDO', 'ACCESO', 'usuario', u.id, 'FALLIDO', null, u)
          guardar()
        }
        throw new ErrorApi('Correo o contraseña incorrectos.', 401)
      }
      if (!u.correo_verificado) throw new ErrorApi('Active su cuenta con el código enviado a su correo.', 403)
      u.intentos_fallidos = 0; u.bloqueado_hasta = null; u.ultimo_acceso = ahora()
      usuarioActual = { id: u.id, correo: u.correo }
      try { sessionStorage.setItem(CLAVE_SESION, JSON.stringify(usuarioActual)) } catch { /* sin almacen */ }
      auditar('INICIO_SESION', 'ACCESO', 'usuario', u.id)
      return { token: `demo-${u.id}`, usuario: usuarioPublico(u) }
    }, 350),
    salir: () => op(() => {
      if (usuarioActual) auditar('CIERRE_SESION', 'ACCESO', 'usuario', usuarioActual.id)
      usuarioActual = null
      try { sessionStorage.removeItem(CLAVE_SESION) } catch { /* sin almacen */ }
    }, 50),
    sesion: () => op(() => usuarioPublico(yo()), 50),
    activar: ({ correo, codigo, clave }) => op(() => {
      const u = bd.usuarios.find((x) => x.correo.toLowerCase() === String(correo).toLowerCase())
      if (!u || String(codigo) !== '123456') throw new ErrorApi('El código no es válido o ya venció.', 400, { codigo: 'Código incorrecto (en demostración use 123456).' })
      if (!clave || clave.length < 10) throw new ErrorApi('La contraseña debe tener al menos 10 caracteres.', 422, { clave: 'Mínimo 10 caracteres.' })
      Object.assign(u, { clave, correo_verificado: true, debe_cambiar_contrasena: false })
    }),
    solicitarRecuperacion: () => op(() => null, 400),
    restablecer: ({ correo, codigo, clave }) => op(() => {
      const u = bd.usuarios.find((x) => x.correo.toLowerCase() === String(correo).toLowerCase())
      if (!u || String(codigo) !== '123456') throw new ErrorApi('El código no es válido o ya venció.', 400, { codigo: 'Código incorrecto (en demostración use 123456).' })
      if (!clave || clave.length < 10) throw new ErrorApi('La contraseña debe tener al menos 10 caracteres.', 422, { clave: 'Mínimo 10 caracteres.' })
      u.clave = clave
      auditar('RECUPERAR_CONTRASENA', 'ACCESO', 'usuario', u.id, 'EXITOSO', null, u)
    })
  },

  perfil: {
    actualizar: ({ nombre_completo, cargo }) => op(() => {
      const u = yo()
      if (!nombre_completo?.trim()) throw new ErrorApi('Ingrese su nombre.', 422, { nombre_completo: 'Obligatorio.' })
      Object.assign(u, { nombre_completo: nombre_completo.trim(), cargo: cargo?.trim() || null })
      return usuarioPublico(u)
    }),
    cambiarClave: ({ actual, nueva }) => op(() => {
      const u = yo()
      if (u.clave !== actual) throw new ErrorApi('La contraseña actual no es correcta.', 400, { actual: 'No coincide.' })
      if (!nueva || nueva.length < 10) throw new ErrorApi('La nueva contraseña debe tener al menos 10 caracteres.', 422, { nueva: 'Mínimo 10 caracteres.' })
      u.clave = nueva; u.debe_cambiar_contrasena = false
    }),
    iniciar2fa: () => op(() => ({ secreto: 'JBSWY3DPEHPK3PXP', uri: 'otpauth://totp/Repositorio%20SCSL?secret=JBSWY3DPEHPK3PXP' })),
    confirmar2fa: (codigo) => op(() => {
      if (!/^\d{6}$/.test(String(codigo))) throw new ErrorApi('Ingrese el código de 6 dígitos de su aplicación.', 422)
      yo().totp_activo = true
    }),
    desactivar2fa: () => op(() => { yo().totp_activo = false })
  },

  catalogos: {
    listar: (tipo, { inactivos = false } = {}) => op(() => {
      yo()
      return cat(tipo).filter((v) => inactivos || v.activo).map((v) => ({
        ...v,
        ...(tipo === 'profesionales' ? { usuario: persona(v.usuario_id) } : {}),
        usos: bd.tramites.filter((t) => t[{ procedencias: 'procedencia_id', entidades: 'entidad_id', tipos_tramite: 'tipo_tramite_id', tipos_documento: 'tipo_documento_id', areas: 'area_id', profesionales: 'profesional_id' }[tipo]] === v.id).length
      })).sort((a, b) => a.nombre.localeCompare(b.nombre, 'es'))
    }, 80),
    sugerir: (tipo, texto) => op(() => {
      yo()
      const q = normalizar(texto)
      if (!q) return []
      return cat(tipo).filter((v) => v.activo)
        .map((v) => ({ id: v.id, nombre: v.nombre, parecido: Math.round(100 * Math.max(similitud(v.nombre, q), normalizar(v.nombre).includes(q) ? 0.6 + q.length / 200 : 0)) }))
        .filter((v) => v.parecido >= 25).sort((a, b) => b.parecido - a.parecido).slice(0, 8)
    }, 60),
    crear: (tipo, { nombre, usuario_id = null }) => op(() => {
      const u = yo()
      if (tipo !== 'entidades' && tipo !== 'tipos_tramite' && tipo !== 'areas') requiere('GESTIONAR_CATALOGOS')
      else if (!puede(u, 'CREAR_REGISTRO') && !puede(u, 'GESTIONAR_CATALOGOS')) throw new ErrorApi('No tiene permisos para agregar valores.', 403)
      const limpio = String(nombre || '').trim().replace(/\s+/g, ' ')
      if (!limpio) throw new ErrorApi('Ingrese el nombre.', 422, { nombre: 'Obligatorio.' })
      const existente = cat(tipo).find((v) => normalizar(v.nombre) === normalizar(limpio))
      if (existente) throw new ErrorApi(`Ya existe "${existente.nombre}".`, 409, { nombre: 'Ya existe un valor igual.' })
      const v = { id: ++bd.secuencia, nombre: tipo === 'profesionales' ? limpio.toUpperCase() : limpio, activo: true, ...(tipo === 'profesionales' ? { usuario_id: usuario_id || null } : {}) }
      cat(tipo).push(v)
      auditar('EDITAR_CATALOGO', 'CATALOGOS', tipo, v.id, 'EXITOSO', { nombre: v.nombre, operacion: 'crear' })
      return v
    }),
    actualizar: (tipo, id, datos) => op(() => {
      requiere('GESTIONAR_CATALOGOS')
      const v = cat(tipo).find((x) => x.id === id)
      if (!v) throw new ErrorApi('El valor no existe.', 404)
      if (datos.nombre !== undefined) {
        const limpio = datos.nombre.trim()
        if (cat(tipo).some((x) => x.id !== id && normalizar(x.nombre) === normalizar(limpio))) throw new ErrorApi('Ya existe un valor igual.', 409, { nombre: 'Ya existe.' })
        v.nombre = limpio
      }
      if (datos.activo !== undefined) v.activo = !!datos.activo
      if (tipo === 'profesionales' && datos.usuario_id !== undefined) {
        if (datos.usuario_id && cat(tipo).some((x) => x.id !== id && x.usuario_id === datos.usuario_id)) throw new ErrorApi('Esa cuenta ya está vinculada a otro profesional.', 409)
        v.usuario_id = datos.usuario_id || null
      }
      auditar('EDITAR_CATALOGO', 'CATALOGOS', tipo, id, 'EXITOSO', datos)
      return v
    }),
    unificar: (tipo, conservar, eliminar) => op(() => {
      requiere('GESTIONAR_CATALOGOS')
      if (conservar === eliminar) throw new ErrorApi('Elija dos valores distintos.', 422)
      const campo = { procedencias: 'procedencia_id', entidades: 'entidad_id', tipos_tramite: 'tipo_tramite_id', tipos_documento: 'tipo_documento_id', areas: 'area_id', profesionales: 'profesional_id' }[tipo]
      let movidos = 0
      bd.tramites.forEach((t) => { if (t[campo] === eliminar) { t[campo] = conservar; movidos++ } })
      if (tipo === 'tipos_documento') bd.prompts.forEach((p) => { if (p.tipo_documento_id === eliminar) p.tipo_documento_id = conservar })
      bd.catalogos[tipo] = cat(tipo).filter((v) => v.id !== eliminar)
      auditar('EDITAR_CATALOGO', 'CATALOGOS', tipo, conservar, 'EXITOSO', { operacion: 'unificar', eliminado: eliminar, movidos })
      return { movidos }
    })
  },

  tramites: {
    buscar: (f = {}) => op(() => {
      requiere('BUSCAR')
      const terminos = normalizar(f.q).split(' ').filter(Boolean)
      let lista = bd.tramites.filter((t) => t.activo)
      const igual = (campo, valor) => valor === undefined || valor === null || valor === '' || String(campo) === String(valor)
      lista = lista.filter((t) => igual(t.anio_gestion, f.anio) && igual(t.estado_tramite, f.estado) && igual(t.entidad_id, f.entidad_id)
        && igual(t.tipo_tramite_id, f.tipo_tramite_id) && igual(t.tipo_documento_id, f.tipo_documento_id)
        && igual(t.profesional_id, f.profesional_id) && igual(t.procedencia_id, f.procedencia_id))
      let conPuntaje = lista.map((t) => ({ t, puntos: 0 }))
      if (terminos.length) {
        conPuntaje = conPuntaje.map(({ t }) => {
          const texto = textoBuscable(t)
          const principal = normalizar([t.hoja_ruta, t.registro_interno, t.numero_documento, t.asunto].join(' '))
          if (!terminos.every((w) => texto.includes(w))) return null
          return { t, puntos: terminos.reduce((s, w) => s + (principal.includes(w) ? 3 : 1), 0) }
        }).filter(Boolean)
        if (f.auditar !== false) auditar('BUSCAR', 'CONSULTA', null, null, 'EXITOSO', { q: f.q, resultados: conPuntaje.length })
      }
      const fecha = (t) => t.fecha_salida || t.creado_en
      if (f.orden === 'antiguo') conPuntaje.sort((a, b) => fecha(a.t).localeCompare(fecha(b.t)))
      else if (f.orden === 'reciente' || !terminos.length) conPuntaje.sort((a, b) => fecha(b.t).localeCompare(fecha(a.t)))
      else conPuntaje.sort((a, b) => b.puntos - a.puntos || fecha(b.t).localeCompare(fecha(a.t)))
      const pag = paginar(conPuntaje, f.pagina, f.por_pagina)
      return { ...pag, items: pag.items.map(({ t, puntos }) => ({ ...expandir(t), relevancia: puntos })) }
    }),
    obtener: (id) => op(() => {
      requiere('BUSCAR')
      const t = buscarTramite(id)
      if (!t.activo && !puede(yo(), 'ELIMINAR_LOGICO')) throw new ErrorApi('El trámite fue dado de baja.', 404)
      return expandir(t, true)
    }),
    crear: (datos) => op(() => {
      const u = requiere('CREAR_REGISTRO')
      validarRegistro(datos)
      const t = {
        id: nuevoId('t'), hoja_ruta: datos.hoja_ruta.trim().toUpperCase(), registro_interno: datos.registro_interno?.trim() || null,
        anio_gestion: new Date().getFullYear(), procedencia_id: Number(datos.procedencia_id), entidad_id: Number(datos.entidad_id),
        tipo_tramite_id: Number(datos.tipo_tramite_id), asunto: datos.asunto.trim(), profesional_id: null,
        tipo_documento_id: null, numero_documento: null, fecha_salida: null,
        area_id: datos.area_id ? Number(datos.area_id) : null, observaciones: datos.observaciones?.trim() || null,
        estado_tramite: 'RECIBIDO', asignado_por: null, fecha_asignacion: null, fecha_conclusion: null,
        activo: true, origen_registro: 'SISTEMA', creado_por: u.id, creado_en: ahora(), actualizado_en: ahora(), informe: null
      }
      if (datos.profesional_id) aplicarAsignacion(t, datos.profesional_id, u)
      bd.tramites.push(t)
      auditar('CREAR_TRAMITE', 'TRAMITES', 'tramite', t.id, 'EXITOSO', { hoja_ruta: t.hoja_ruta })
      if (t.profesional_id) auditar('ASIGNAR_TRAMITE', 'TRAMITES', 'tramite', t.id, 'EXITOSO', { profesional: ref('profesionales', t.profesional_id)?.nombre })
      return expandir(t)
    }, 300),
    actualizar: (id, datos) => op(() => {
      const u = yo()
      const t = buscarTramite(id)
      const det = expandir(t, true)
      if (!det.permisos.editar) throw new ErrorApi('No tiene permisos para editar este trámite.', 403)
      const nuevo = { ...t, ...Object.fromEntries(Object.entries(datos).filter(([k]) =>
        ['hoja_ruta', 'registro_interno', 'procedencia_id', 'entidad_id', 'tipo_tramite_id', 'asunto', 'area_id', 'observaciones', 'tipo_documento_id', 'numero_documento', 'fecha_salida'].includes(k))) }
      if (t.origen_registro === 'SISTEMA') validarRegistro(nuevo)
      Object.assign(t, nuevo, { hoja_ruta: nuevo.hoja_ruta?.trim().toUpperCase(), actualizado_en: ahora() })
      auditar('EDITAR_TRAMITE', 'TRAMITES', 'tramite', t.id, 'EXITOSO', { campos: Object.keys(datos) }, u)
      return expandir(t, true)
    }),
    asignar: (id, profesional_id) => op(() => {
      const u = yo()
      const t = buscarTramite(id)
      aplicarAsignacion(t, profesional_id, u)
      t.actualizado_en = ahora()
      auditar('ASIGNAR_TRAMITE', 'TRAMITES', 'tramite', t.id, 'EXITOSO', { profesional: ref('profesionales', t.profesional_id)?.nombre ?? 'sin asignar' })
      return expandir(t, true)
    }),
    concluir: (id, { tipo_documento_id, numero_documento, fecha_salida, archivo }) => op(() => {
      const u = yo()
      const t = buscarTramite(id)
      const prof = bd.catalogos.profesionales.find((p) => p.id === t.profesional_id)
      if (u.rol !== 'ADMIN' && (prof?.usuario_id !== u.id || !puede(u, 'SUBIR_INFORME'))) throw new ErrorApi('Solo el abogado asignado al trámite puede subir el informe.', 403)
      if (!['EN_ELABORACION', 'CONCLUIDO'].includes(t.estado_tramite)) throw new ErrorApi('El trámite debe estar en elaboración para subir el informe.', 409)
      const campos = {}
      if (!tipo_documento_id) campos.tipo_documento_id = 'Seleccione el tipo de documento.'
      if (!numero_documento?.trim()) campos.numero_documento = 'Ingrese el número del documento de respuesta.'
      const maxMb = Number(bd.configuracion.find((c) => c.clave === 'pdf_max_mb')?.valor || 50)
      if (!archivo) campos.archivo = 'Adjunte el informe en PDF.'
      else if (!/\.pdf$/i.test(archivo.name) || (archivo.type && archivo.type !== 'application/pdf')) campos.archivo = 'El archivo debe ser PDF.'
      else if (archivo.size > maxMb * 1048576) campos.archivo = `El PDF supera ${maxMb} MB.`
      if (Object.keys(campos).length) throw new ErrorApi('Revise los campos marcados.', 422, campos)
      const versiones = (t.informe?.versiones || 0) + 1
      Object.assign(t, {
        tipo_documento_id: Number(tipo_documento_id), numero_documento: numero_documento.trim().toUpperCase(),
        fecha_salida: fecha_salida || t.fecha_salida || new Date().toISOString().slice(0, 10),
        estado_tramite: t.estado_tramite === 'EN_ELABORACION' ? 'CONCLUIDO' : t.estado_tramite,
        fecha_conclusion: t.fecha_conclusion || ahora(), actualizado_en: ahora(),
        informe: { id: nuevoId('inf'), nombre_original: archivo.name, paginas: 3, tamano_bytes: archivo.size, subido_por: u.id, subido_en: ahora(), versiones,
          texto: `${t.asunto}. Informe subido en modo demostración: el texto real se extrae del PDF en el servidor.` }
      })
      auditar('SUBIR_INFORME', 'TRAMITES', 'tramite', t.id, 'EXITOSO', { archivo: archivo.name, version: versiones })
      return expandir(t, true)
    }, 700),
    archivar: (id) => op(() => {
      requiere('ARCHIVAR_TRAMITE')
      const t = buscarTramite(id)
      if (t.estado_tramite !== 'CONCLUIDO') throw new ErrorApi('Solo se archiva un trámite concluido.', 409)
      t.estado_tramite = 'ARCHIVADO'; t.actualizado_en = ahora()
      auditar('ARCHIVAR_TRAMITE', 'TRAMITES', 'tramite', t.id)
      return expandir(t, true)
    }),
    darDeBaja: (id, motivo) => op(() => {
      requiere('ELIMINAR_LOGICO')
      if (!motivo?.trim()) throw new ErrorApi('Indique el motivo de la baja.', 422, { motivo: 'Obligatorio.' })
      const t = buscarTramite(id)
      Object.assign(t, { activo: false, baja_motivo: motivo.trim(), actualizado_en: ahora() })
      auditar('BAJA_TRAMITE', 'TRAMITES', 'tramite', t.id, 'EXITOSO', { motivo })
      return expandir(t)
    }),
    pendientes: () => op(() => {
      const u = yo()
      const p = plazo()
      return bd.tramites.filter((t) => t.activo && t.estado_tramite === 'EN_ELABORACION' && (u.rol === 'ABOGADO'
        ? bd.catalogos.profesionales.find((x) => x.id === t.profesional_id)?.usuario_id === u.id
        : ['JEFE', 'ADMIN'].includes(u.rol)))
        .sort((a, b) => (a.fecha_asignacion || '').localeCompare(b.fecha_asignacion || ''))
        .map((t) => { const d = diasDesde(t.fecha_asignacion); return { ...expandir(t), dias_en_elaboracion: d, vencido: p ? d > p : false } })
    }),
    porAsignar: () => op(() => {
      requiere('ASIGNAR_TRAMITE')
      return bd.tramites.filter((t) => t.activo && t.estado_tramite === 'RECIBIDO' && t.origen_registro === 'SISTEMA').sort((a, b) => a.creado_en.localeCompare(b.creado_en)).map((t) => expandir(t))
    }),
    similares: (id) => op(() => {
      requiere('BUSCAR')
      const t = buscarTramite(id)
      return bd.tramites.filter((x) => x.id !== t.id && x.activo)
        .map((x) => ({ tramite: expandir(x), afinidad: Math.round(100 * similitud(x.asunto, t.asunto)) }))
        .filter((x) => x.afinidad >= 20).sort((a, b) => b.afinidad - a.afinidad).slice(0, 6)
    }),
    paginasInforme: (id) => op(() => {
      const u = requiere('VER_INFORME')
      const t = buscarTramite(id)
      if (!t.informe) throw new ErrorApi('Este trámite aún no tiene informe.', 404)
      auditar('VER_INFORME', 'TRAMITES', 'tramite', t.id)
      return { paginas: Array.from({ length: t.informe.paginas }, (_, i) => paginaSvg(t, i + 1, t.informe.paginas, u)), marca: u.correo }
    }, 400),
    urlPaginaInforme: () => null,
    descargarInforme: (id) => op(() => {
      requiere('DESCARGAR_INFORME')
      const t = buscarTramite(id)
      if (!t.informe) throw new ErrorApi('Este trámite aún no tiene informe.', 404)
      auditar('DESCARGAR_INFORME', 'TRAMITES', 'tramite', t.id, 'EXITOSO', { archivo: t.informe.nombre_original })
      return { demo: true, numero_documento: t.numero_documento || t.hoja_ruta }
    }).then((r) => new Blob([`%PDF-1.4\n% Documento de demostracion: ${r.numero_documento}\n`], { type: 'application/pdf' }))
  },

  precedentes: {
    crear: (tramiteId, d) => op(() => {
      const u = requiere('GESTIONAR_PRECEDENTES')
      buscarTramite(tramiteId)
      const campos = {}
      if (!d.tramite_precedente_id) campos.tramite_precedente_id = 'Elija el trámite precedente.'
      if (!d.criterio_legal?.trim()) campos.criterio_legal = 'Escriba el criterio legal.'
      if (!d.relevancia) campos.relevancia = 'Elija la relevancia.'
      if (Object.keys(campos).length) throw new ErrorApi('Revise los campos marcados.', 422, campos)
      if (d.tramite_precedente_id === tramiteId) throw new ErrorApi('Un trámite no puede ser precedente de sí mismo.', 409)
      if (bd.precedentes.some((p) => p.tramite_id === tramiteId && p.tramite_precedente_id === d.tramite_precedente_id)) throw new ErrorApi('Ese precedente ya está vinculado.', 409)
      const p = { id: nuevoId('p'), tramite_id: tramiteId, tramite_precedente_id: d.tramite_precedente_id, criterio_legal: d.criterio_legal.trim(),
        relevancia: d.relevancia, tipo_relacion: d.tipo_relacion || 'APLICA', origen: d.origen || 'MANUAL', observaciones: d.observaciones?.trim() || null,
        creado_por: u.id, creado_en: ahora() }
      bd.precedentes.push(p)
      auditar('CREAR_PRECEDENTE', 'PRECEDENTES', 'tramite', tramiteId, 'EXITOSO', { precedente: d.tramite_precedente_id })
      return p
    }),
    eliminar: (id) => op(() => {
      requiere('GESTIONAR_PRECEDENTES')
      bd.precedentes = bd.precedentes.filter((p) => p.id !== id)
    })
  },

  prompts: {
    vigentes: (f = {}) => op(() => {
      requiere('USAR_PROMPTS')
      const q = normalizar(f.q)
      return bd.prompts.filter((p) => p.estado === 'VIGENTE'
        && (!f.tipo_documento_id || p.tipo_documento_id === null || String(p.tipo_documento_id) === String(f.tipo_documento_id))
        && (!f.categoria || p.categoria === f.categoria)
        && (!q || normalizar(`${p.titulo} ${p.texto}`).includes(q)))
        .sort((a, b) => b.usos - a.usos).map(expandirPrompt)
    }, 120),
    gestion: (f = {}) => op(() => {
      const u = requiere('PROPONER_PROMPT')
      return bd.prompts.filter((p) => (puede(u, 'GESTIONAR_PROMPTS') || p.propuesto_por === u.id) && (!f.estado || p.estado === f.estado))
        .sort((a, b) => b.actualizado_en.localeCompare(a.actualizado_en)).map(expandirPrompt)
    }),
    proponer: (d) => op(() => {
      const u = requiere('PROPONER_PROMPT')
      validarPrompt(d)
      const p = { id: ++bd.secuencia, titulo: d.titulo.trim(), categoria: d.categoria, tipo_documento_id: d.tipo_documento_id ? Number(d.tipo_documento_id) : null,
        texto: d.texto.trim(), instrucciones: d.instrucciones?.trim() || null, estado: 'BORRADOR', observacion: null, usos: 0,
        propuesto_por: u.id, aprobado_por: null, aprobado_en: null, creado_en: ahora(), actualizado_en: ahora() }
      bd.prompts.push(p)
      auditar('PROPONER_PROMPT', 'PROMPTS', 'prompt', p.id)
      return expandirPrompt(p)
    }),
    actualizar: (id, d) => op(() => {
      const u = requiere('PROPONER_PROMPT')
      const p = bd.prompts.find((x) => x.id === id)
      if (!p) throw new ErrorApi('El prompt no existe.', 404)
      if (p.estado === 'VIGENTE' && !puede(u, 'GESTIONAR_PROMPTS')) throw new ErrorApi('Solo el jefe modifica un prompt vigente.', 403)
      if (p.propuesto_por !== u.id && !puede(u, 'GESTIONAR_PROMPTS')) throw new ErrorApi('Solo puede editar sus propuestas.', 403)
      validarPrompt({ ...p, ...d }, id)
      Object.assign(p, { titulo: d.titulo?.trim() ?? p.titulo, categoria: d.categoria ?? p.categoria,
        tipo_documento_id: d.tipo_documento_id !== undefined ? (d.tipo_documento_id ? Number(d.tipo_documento_id) : null) : p.tipo_documento_id,
        texto: d.texto?.trim() ?? p.texto, instrucciones: d.instrucciones !== undefined ? (d.instrucciones?.trim() || null) : p.instrucciones,
        observacion: p.estado === 'BORRADOR' ? null : p.observacion, actualizado_en: ahora() })
      return expandirPrompt(p)
    }),
    aprobar: (id) => op(() => {
      const u = requiere('GESTIONAR_PROMPTS')
      const p = buscarPrompt(id)
      Object.assign(p, { estado: 'VIGENTE', aprobado_por: u.id, aprobado_en: ahora(), observacion: null, actualizado_en: ahora() })
      auditar('APROBAR_PROMPT', 'PROMPTS', 'prompt', id)
      return expandirPrompt(p)
    }),
    devolver: (id, observacion) => op(() => {
      requiere('GESTIONAR_PROMPTS')
      if (!observacion?.trim()) throw new ErrorApi('Escriba qué debe corregirse.', 422, { observacion: 'Obligatorio.' })
      const p = buscarPrompt(id)
      Object.assign(p, { estado: 'BORRADOR', aprobado_por: null, aprobado_en: null, observacion: observacion.trim(), actualizado_en: ahora() })
      return expandirPrompt(p)
    }),
    retirar: (id) => op(() => {
      requiere('GESTIONAR_PROMPTS')
      const p = buscarPrompt(id)
      Object.assign(p, { estado: 'RETIRADO', actualizado_en: ahora() })
      auditar('RETIRAR_PROMPT', 'PROMPTS', 'prompt', id)
      return expandirPrompt(p)
    }),
    registrarUso: (id, tramite_id = null) => op(() => {
      requiere('USAR_PROMPTS')
      const p = bd.prompts.find((x) => x.id === id && x.estado === 'VIGENTE')
      if (!p) throw new ErrorApi('El prompt no existe o no está vigente.', 404)
      p.usos++
      auditar('COPIAR_PROMPT', 'PROMPTS', 'prompt', id, 'EXITOSO', { tramite_id })
    }, 40)
  },

  tablero: {
    resumen: (f = {}) => op(() => {
      requiere('VER_TABLERO')
      const p = plazo()
      const activos = bd.tramites.filter((t) => t.activo && (!f.anio || String(t.anio_gestion) === String(f.anio)))
      const cuenta = (lista, estado) => lista.filter((t) => (Array.isArray(estado) ? estado.includes(t.estado_tramite) : t.estado_tramite === estado)).length
      const diasElab = (t) => (t.fecha_asignacion && t.fecha_conclusion ? Math.max(0, Math.round((new Date(t.fecha_conclusion) - new Date(t.fecha_asignacion)) / 86400000)) : null)
      const agrupar = (clave, nombre) => {
        const grupos = new Map()
        activos.forEach((t) => { const k = clave(t); if (!grupos.has(k)) grupos.set(k, []); grupos.get(k).push(t) })
        return [...grupos.entries()].map(([k, lista]) => {
          const dias = lista.map(diasElab).filter((d) => d !== null)
          const concl = cuenta(lista, ['CONCLUIDO', 'ARCHIVADO'])
          return { clave: k, nombre: nombre(k), total: lista.length, sin_asignar: cuenta(lista, 'RECIBIDO'), en_elaboracion: cuenta(lista, 'EN_ELABORACION'),
            concluidos: concl, porcentaje_avance: Math.round((1000 * concl) / lista.length) / 10,
            promedio_dias_elaboracion: dias.length ? Math.round((10 * dias.reduce((a, b) => a + b, 0)) / dias.length) / 10 : null,
            dias_pendiente_mas_antiguo: Math.max(0, ...lista.filter((t) => t.estado_tramite === 'EN_ELABORACION').map((t) => diasDesde(t.fecha_asignacion) || 0)) || null }
        })
      }
      const meses = []
      for (let i = 11; i >= 0; i--) {
        const d = new Date(); d.setDate(1); d.setMonth(d.getMonth() - i)
        const m = d.toISOString().slice(0, 7)
        meses.push({ mes: m, registrados: bd.tramites.filter((t) => t.activo && t.creado_en.slice(0, 7) === m).length,
          concluidos: bd.tramites.filter((t) => t.activo && (t.fecha_conclusion || '').slice(0, 7) === m).length })
      }
      return {
        plazo_dias: p,
        anios: [...new Set(bd.tramites.map((t) => t.anio_gestion))].sort((a, b) => b - a),
        totales: { total: activos.length, RECIBIDO: cuenta(activos, 'RECIBIDO'), EN_ELABORACION: cuenta(activos, 'EN_ELABORACION'),
          CONCLUIDO: cuenta(activos, 'CONCLUIDO'), ARCHIVADO: cuenta(activos, 'ARCHIVADO'),
          gestion_actual: activos.filter((t) => t.anio_gestion === new Date().getFullYear()).length,
          vencidos: p ? activos.filter((t) => t.estado_tramite === 'EN_ELABORACION' && diasDesde(t.fecha_asignacion) > p).length : 0 },
        por_abogado: agrupar((t) => t.profesional_id || 0, (k) => (k ? bd.catalogos.profesionales.find((x) => x.id === k)?.nombre : 'SIN ASIGNAR')).sort((a, b) => b.total - a.total),
        por_anio: agrupar((t) => t.anio_gestion, (k) => String(k)).sort((a, b) => a.clave - b.clave),
        por_tipo_documento: agrupar((t) => t.tipo_documento_id || 0, (k) => (k ? ref('tipos_documento', k).nombre : 'Sin tipo (pendientes)')).sort((a, b) => b.total - a.total),
        por_tipo_tramite: agrupar((t) => t.tipo_tramite_id, (k) => ref('tipos_tramite', k)?.nombre || 'Sin tipo').sort((a, b) => b.total - a.total),
        por_mes: meses,
        vencidos: p ? activos.filter((t) => t.estado_tramite === 'EN_ELABORACION' && diasDesde(t.fecha_asignacion) > p)
          .map((t) => ({ ...expandir(t), dias_en_elaboracion: diasDesde(t.fecha_asignacion) })).sort((a, b) => b.dias_en_elaboracion - a.dias_en_elaboracion) : []
      }
    }, 250),
    inicio: () => op(() => {
      const u = yo()
      const p = plazo()
      const activos = bd.tramites.filter((t) => t.activo)
      const mios = activos.filter((t) => t.estado_tramite === 'EN_ELABORACION' && bd.catalogos.profesionales.find((x) => x.id === t.profesional_id)?.usuario_id === u.id)
      const recientes = [...activos].filter((t) => t.informe).sort((a, b) => (b.fecha_conclusion || b.fecha_salida || '').localeCompare(a.fecha_conclusion || a.fecha_salida || '')).slice(0, 5)
      return {
        rol: u.rol,
        totales: { total: activos.length, gestion_actual: activos.filter((t) => t.anio_gestion === new Date().getFullYear()).length,
          en_elaboracion: activos.filter((t) => t.estado_tramite === 'EN_ELABORACION').length,
          por_asignar: activos.filter((t) => t.estado_tramite === 'RECIBIDO').length,
          concluidos_mes: activos.filter((t) => (t.fecha_conclusion || '').slice(0, 7) === new Date().toISOString().slice(0, 7)).length,
          prompts_vigentes: bd.prompts.filter((x) => x.estado === 'VIGENTE').length,
          prompts_por_revisar: bd.prompts.filter((x) => x.estado === 'BORRADOR').length },
        mis_pendientes: mios.map((t) => { const d = diasDesde(t.fecha_asignacion); return { ...expandir(t), dias_en_elaboracion: d, vencido: p ? d > p : false } }),
        registrados_por_mi: activos.filter((t) => t.creado_por === u.id).sort((a, b) => b.creado_en.localeCompare(a.creado_en)).slice(0, 5).map((t) => expandir(t)),
        recientes: recientes.map((t) => expandir(t)),
        prompts_mas_usados: bd.prompts.filter((x) => x.estado === 'VIGENTE').sort((a, b) => b.usos - a.usos).slice(0, 3).map(expandirPrompt)
      }
    })
  },

  usuarios: {
    listar: () => op(() => { requiere('GESTIONAR_USUARIOS'); return bd.usuarios.map(usuarioPublico) }),
    crear: (d) => op(() => {
      requiere('GESTIONAR_USUARIOS')
      const campos = {}
      if (!d.nombre_completo?.trim()) campos.nombre_completo = 'Ingrese el nombre.'
      if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(d.correo || '')) campos.correo = 'Ingrese un correo válido.'
      else if (bd.usuarios.some((u) => u.correo.toLowerCase() === d.correo.toLowerCase())) campos.correo = 'Ya existe un usuario con ese correo.'
      if (!['ADMIN', 'JEFE', 'ABOGADO', 'SECRETARIA'].includes(d.rol)) campos.rol = 'Elija un rol.'
      if (Object.keys(campos).length) throw new ErrorApi('Revise los campos marcados.', 422, campos)
      const u = { id: ++bd.secuencia, nombre_completo: d.nombre_completo.trim(), correo: d.correo.trim().toLowerCase(), cargo: d.cargo?.trim() || null,
        rol: d.rol, clave: CLAVE_DEMO, activo: true, correo_verificado: false, debe_cambiar_contrasena: true, totp_activo: false, ultimo_acceso: null, creado_en: ahora() }
      bd.usuarios.push(u)
      auditar('CREAR_USUARIO', 'USUARIOS', 'usuario', u.id, 'EXITOSO', { correo: u.correo, rol: u.rol })
      return usuarioPublico(u)
    }),
    actualizar: (id, d) => op(() => {
      const yoMismo = requiere('GESTIONAR_USUARIOS')
      const u = bd.usuarios.find((x) => x.id === id)
      if (!u) throw new ErrorApi('El usuario no existe.', 404)
      if (u.id === yoMismo.id && d.rol && d.rol !== u.rol) throw new ErrorApi('No puede cambiar su propio rol.', 409)
      if (d.nombre_completo !== undefined) u.nombre_completo = d.nombre_completo.trim()
      if (d.cargo !== undefined) u.cargo = d.cargo?.trim() || null
      if (d.rol) u.rol = d.rol
      auditar('EDITAR_USUARIO', 'USUARIOS', 'usuario', u.id, 'EXITOSO', d)
      return usuarioPublico(u)
    }),
    activar: (id, activo) => op(() => {
      const yoMismo = requiere('GESTIONAR_USUARIOS')
      if (id === yoMismo.id && !activo) throw new ErrorApi('No puede desactivar su propia cuenta.', 409)
      const u = bd.usuarios.find((x) => x.id === id)
      u.activo = !!activo
      auditar('EDITAR_USUARIO', 'USUARIOS', 'usuario', u.id, 'EXITOSO', { activo })
      return usuarioPublico(u)
    }),
    reenviarActivacion: (id) => op(() => { requiere('GESTIONAR_USUARIOS'); return { enviado_a: bd.usuarios.find((u) => u.id === id)?.correo } }),
    roles: () => op(() => { yo(); return ROLES_DEMO })
  },

  auditoria: {
    listar: (f = {}) => op(() => {
      requiere('VER_AUDITORIA')
      const lista = bd.auditoria.filter((a) => (!f.usuario_id || String(a.usuario_id) === String(f.usuario_id))
        && (!f.accion || a.accion === f.accion) && (!f.modulo || a.modulo === f.modulo) && (!f.resultado || a.resultado === f.resultado)
        && (!f.desde || a.creado_en.slice(0, 10) >= f.desde) && (!f.hasta || a.creado_en.slice(0, 10) <= f.hasta)).reverse()
      return paginar(lista, f.pagina, f.por_pagina || 20)
    }),
    registrar: ({ accion, modulo, detalle }) => op(() => { yo(); auditar(accion, modulo, null, null, 'EXITOSO', detalle || null) }, 20)
  },

  importacion: {
    analizar: (archivo) => op(() => {
      requiere('IMPORTAR_EXCEL')
      if (!archivo || !/\.(xlsx|xls)$/i.test(archivo.name)) throw new ErrorApi('Seleccione un archivo Excel (.xlsx o .xls).', 422, { archivo: 'Formato no válido.' })
      bd.analisis = { ...(bd.analisis || {}), [bd.secuencia + 1]: archivo.name }
      return {
        id: ++bd.secuencia, archivo: archivo.name, tamano_bytes: archivo.size, huella: 'demostracion', hojas: ['Registro'], demo: true,
        resumen: { filas: 317, columnas: 12, listas: 301, con_incidencias: 16, hojas_ruta_repetidas: 9, fechas_ilegibles: 4, entidades_nuevas: 38 },
        columnas: [
          { excel: 'HR', destino: 'Hoja de ruta', completos: 317, vacios: 0 },
          { excel: 'RI', destino: 'Registro interno', completos: 298, vacios: 19 },
          { excel: 'AÑO', destino: 'Año de gestión', completos: 317, vacios: 0 },
          { excel: 'PROCEDENCIA', destino: 'Procedencia', completos: 312, vacios: 5 },
          { excel: 'ENTIDAD', destino: 'Entidad', completos: 315, vacios: 2 },
          { excel: 'TIPO DE TRAMITE', destino: 'Tipo de trámite', completos: 309, vacios: 8 },
          { excel: 'ASUNTO', destino: 'Asunto', completos: 317, vacios: 0 },
          { excel: 'PROFESIONAL', destino: 'Abogado', completos: 311, vacios: 6 },
          { excel: 'DOC. SALIDA', destino: 'Número de documento', completos: 290, vacios: 27 },
          { excel: 'FECHA SALIDA', destino: 'Fecha de salida', completos: 286, vacios: 31 },
          { excel: 'OBSERVACIONES', destino: 'Observaciones', completos: 120, vacios: 197 },
          { excel: 'AREA', destino: 'Área o unidad', completos: 140, vacios: 177 }
        ],
        incidencias: [
          { fila: 14, tipo: 'FECHA_ILEGIBLE', descripcion: 'Fecha de salida "31/02/2025" no existe.' },
          { fila: 37, tipo: 'ENTIDAD_VACIA', descripcion: 'La entidad está vacía; se migra sin entidad y queda para revisión.' },
          { fila: 52, tipo: 'PROCEDENCIA_AMBIGUA', descripcion: 'Procedencia "INT/EXT" no corresponde a INTERNA ni EXTERNA.' },
          { fila: 88, tipo: 'HOJA_RUTA_REPETIDA', descripcion: 'La hoja de ruta se repite en la fila 91 con otro asunto (se migran ambas).' },
          { fila: 140, tipo: 'TIPO_TRAMITE_VACIO', descripcion: 'Tipo de trámite vacío.' }
        ]
      }
    }, 900),
    ejecutar: (id, modo) => op(() => {
      const u = requiere('IMPORTAR_EXCEL')
      const r = { id, modo, estado: 'COMPLETADA', encontrados: 317, insertados: modo === 'DEFINITIVA' ? 317 : 0, simulados: 317, rechazados: 0, incidencias: 16, fecha: ahora(), demo: true }
      if (modo === 'DEFINITIVA') {
        bd.importaciones.push({ id, archivo: bd.analisis?.[id] || 'Excel de demostración', huella: 'demostracion', modo, estado: 'COMPLETADA', encontrados: 317, insertados: 0, rechazados: 0, incidencias: 16, ejecutado_por: u.correo, fecha: ahora() })
        auditar('IMPORTAR_EXCEL', 'IMPORTACION', 'importacion', id, 'EXITOSO', { modo, nota: 'demostración: no se agregaron registros' })
      }
      return r
    }, 1200),
    historial: () => op(() => { requiere('IMPORTAR_EXCEL'); return [...bd.importaciones].reverse() })
  },

  notificaciones: {
    listar: () => op(() => {
      const u = yo()
      const mias = (bd.notificaciones || []).filter((n) => n.usuario_id === u.id).reverse()
      return { items: mias.slice(0, 30), no_leidas: mias.filter((n) => !n.leida_en).length }
    }, 60),
    marcarLeida: (id) => op(() => {
      const n = (bd.notificaciones || []).find((x) => x.id === id && x.usuario_id === yo().id)
      if (!n) throw new ErrorApi('La notificación no existe.', 404)
      n.leida_en ||= ahora()
    }, 30),
    marcarTodas: () => op(() => {
      const u = yo();
      (bd.notificaciones || []).forEach((n) => { if (n.usuario_id === u.id && !n.leida_en) n.leida_en = ahora() })
    }, 30)
  },

  configuracion: {
    listar: () => op(() => { yo(); return bd.configuracion }),
    actualizar: (clave, valor) => op(() => {
      requiere('GESTIONAR_RETENCION')
      const c = bd.configuracion.find((x) => x.clave === clave)
      if (!c) throw new ErrorApi('Parámetro desconocido.', 404)
      if (clave !== 'prompts_aviso' && valor !== '' && valor !== null && !/^\d+$/.test(String(valor))) throw new ErrorApi('Ingrese un número entero.', 422, { valor: 'Solo números.' })
      if (clave !== 'plazo_dias_tramite' && clave !== 'prompts_aviso' && (valor === '' || valor === null)) throw new ErrorApi('Este parámetro no puede quedar vacío.', 422, { valor: 'Obligatorio.' })
      c.valor = valor === '' ? null : String(valor)
      auditar('EDITAR_CONFIGURACION', 'CONFIGURACION', 'configuracion', clave, 'EXITOSO', { valor: c.valor })
      return c
    })
  },

  fuentes: {
    listar: () => op(() => { yo(); return [...bd.fuentes].sort((a, b) => a.orden - b.orden) }, 60),
    crear: (d) => op(() => {
      requiere('GESTIONAR_CATALOGOS')
      validarFuente(d)
      const f = { id: ++bd.secuencia, nombre: d.nombre.trim(), descripcion: d.descripcion?.trim() || null, url: d.url.trim(), url_busqueda: d.url_busqueda?.trim() || null, orden: Number(d.orden) || 100, activo: true }
      bd.fuentes.push(f)
      return f
    }),
    actualizar: (id, d) => op(() => {
      requiere('GESTIONAR_CATALOGOS')
      const f = bd.fuentes.find((x) => x.id === id)
      const nuevo = { ...f, ...d }
      validarFuente(nuevo)
      Object.assign(f, nuevo)
      return f
    })
  }
}

function buscarPrompt(id) {
  const p = bd.prompts.find((x) => x.id === Number(id))
  if (!p) throw new ErrorApi('El prompt no existe.', 404)
  return p
}
function expandirPrompt(p) {
  return { ...p, tipo_documento: ref('tipos_documento', p.tipo_documento_id), propuesto_por: persona(p.propuesto_por), aprobado_por: persona(p.aprobado_por) }
}
function validarPrompt(d, id = null) {
  const campos = {}
  if (!d.titulo?.trim()) campos.titulo = 'Ingrese un título.'
  else if (bd.prompts.some((p) => p.id !== id && p.estado !== 'RETIRADO' && normalizar(p.titulo) === normalizar(d.titulo))) campos.titulo = 'Ya existe un prompt con ese título.'
  if (!d.categoria) campos.categoria = 'Elija la categoría.'
  if (!d.texto?.trim()) campos.texto = 'Escriba el texto del prompt.'
  if (Object.keys(campos).length) throw new ErrorApi('Revise los campos marcados.', 422, campos)
}
function validarFuente(d) {
  const campos = {}
  if (!d.nombre?.trim()) campos.nombre = 'Ingrese el nombre.'
  if (!/^https?:\/\/\S+$/i.test(d.url || '')) campos.url = 'Ingrese una dirección que empiece con http:// o https://'
  if (d.url_busqueda && (!/^https?:\/\/\S+$/i.test(d.url_busqueda) || !d.url_busqueda.includes('{q}'))) campos.url_busqueda = 'Debe empezar con http(s):// e incluir {q}.'
  if (Object.keys(campos).length) throw new ErrorApi('Revise los campos marcados.', 422, campos)
}

/**
 * eSYNAPSE 360 — Cliente API con JWT y refresh automático.
 */
import { avisarEscritura } from './avisos.js'

const BASE = '/api'

const tokens = {
  get access() { return localStorage.getItem('esynapse_access') },
  get refresh() { return localStorage.getItem('esynapse_refresh') },
  set(access, refresh) {
    localStorage.setItem('esynapse_access', access)
    if (refresh) localStorage.setItem('esynapse_refresh', refresh)
  },
  clear() {
    localStorage.removeItem('esynapse_access')
    localStorage.removeItem('esynapse_refresh')
  },
}

// Acceso a los archivos subidos (/media): el servidor entrega una cookie firmada solo para usuarios con sesión; se
// pide al ingresar, al abrir el sistema con sesión y en cada renovación del token.
export function activarArchivos() {
  if (!tokens.access) return Promise.resolve()
  return fetch(`${BASE}/auth/media/`, { method: 'POST', headers: { Authorization: `Bearer ${tokens.access}` } })
    .catch(() => {})
}

// Una sola renovación a la vez: si varias consultas vencen juntas (p. ej. una
// pantalla que carga cinco datos en paralelo), todas esperan la misma. Con
// tokens rotativos, renovar dos veces con el mismo token invalidaba la sesión.
let renovando = null
function refrescarToken() {
  if (!renovando) renovando = renovar().finally(() => { renovando = null })
  return renovando
}

async function renovar() {
  const refresh = tokens.refresh
  if (!refresh) return false
  const r = await fetch(`${BASE}/auth/refresh/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh }),
  })
  if (!r.ok) {
    // Otra pestaña pudo renovarla primero: si ya hay otro token guardado, se usa ese.
    if (tokens.refresh && tokens.refresh !== refresh) return true
    // Solo un refresh rechazado (400/401) cierra la sesión; un 5xx (servidor reiniciándose) no.
    if (r.status === 400 || r.status === 401) tokens.clear()
    return false
  }
  const data = await r.json()
  tokens.set(data.access, data.refresh)
  activarArchivos()
  return true
}

const SESION_EXPIRADA = 'Tu sesión expiró. Vuelve a ingresar.'
function sesionExpirada() {
  window.dispatchEvent(new Event('esynapse:sesion-expirada'))
  const e = new Error(SESION_EXPIRADA)
  e.status = 401
  return e
}

// Doble clic: una escritura idéntica (mismo método, ruta y datos) que ya está en curso no se envía dos veces; las dos
// llamadas reciben la misma respuesta. Evita registros duplicados en todos los formularios.
const enCurso = new Map()

export function apiFetch(path, opciones = {}) {
  const { method = 'GET', body, _reintento = false } = opciones
  if (method === 'GET' || _reintento) return _apiFetch(path, opciones)
  const clave = `${method} ${path} ${body === undefined ? '' : JSON.stringify(body)}`
  if (enCurso.has(clave)) return enCurso.get(clave)
  const p = _apiFetch(path, opciones)
    .then((r) => { avisarEscritura(method, path); return r })   // aviso «Guardado», «Aprobado»…
    .finally(() => enCurso.delete(clave))
  enCurso.set(clave, p)
  return p
}

async function _apiFetch(path, { method = 'GET', body, _reintento = false } = {}) {
  const headers = { 'Content-Type': 'application/json' }
  if (tokens.access) headers.Authorization = `Bearer ${tokens.access}`

  const r = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })

  if (r.status === 401) {
    if (!_reintento && await refrescarToken()) return apiFetch(path, { method, body, _reintento: true })
    throw sesionExpirada()
  }

  if (r.status === 204) return null
  const data = await r.json().catch(() => null)
  if (!r.ok) {
    const error = new Error(
      mensajeError(data)
      || `Error del servidor (HTTP ${r.status}). Verifica que el backend esté actualizado y migrado.`,
    )
    error.status = r.status
    error.data = data
    throw error
  }
  // Listados paginados: si la consulta no pide una página concreta, se traen todas las páginas (las pantallas
  // trabajan con la lista completa; antes se cortaba en los primeros 25 registros sin avisar).
  if (method === 'GET' && data && Array.isArray(data.results) && data.next && !/[?&]page=/.test(path)) {
    const todos = [...data.results]
    let siguiente = data.next
    for (let i = 0; siguiente && i < 200; i += 1) {
      const u = new URL(siguiente, window.location.origin)
      const d = await apiFetch(`${u.pathname.replace(/^\/api/, '')}${u.search}`)
      todos.push(...(d.results || []))
      siguiente = d.next
    }
    return { ...data, next: null, results: todos }
  }
  return data
}

/** Mensaje legible de un error de la API: «detail» o los mensajes por campo
 *  (sin el formato técnico de la respuesta). */
function mensajeError(data) {
  if (!data) return null
  if (typeof data === 'string') return data
  if (data.detail) return data.detail
  if (typeof data !== 'object') return null
  const partes = []
  const recorrer = (v) => {
    if (v == null) return
    if (typeof v === 'string') partes.push(v)
    else if (Array.isArray(v)) v.forEach(recorrer)
    else if (typeof v === 'object') Object.values(v).forEach(recorrer)
  }
  recorrer(data)
  return partes.length ? [...new Set(partes)].join(' ') : null
}

export async function apiUpload(path, formData, { method = 'POST', _reintento = false } = {}) {
  const headers = {}
  if (tokens.access) headers.Authorization = `Bearer ${tokens.access}`
  const r = await fetch(`${BASE}${path}`, { method, headers, body: formData })
  if (r.status === 401) {
    if (!_reintento && await refrescarToken()) return apiUpload(path, formData, { method, _reintento: true })
    throw sesionExpirada()
  }
  if (r.status === 204) return null
  const data = await r.json().catch(() => null)
  if (!r.ok) {
    const error = new Error(
      mensajeError(data)
      || `Error del servidor (HTTP ${r.status}). Verifica que el backend esté actualizado y migrado.`,
    )
    error.status = r.status
    error.data = data
    throw error
  }
  if (!_reintento) avisarEscritura(method, path)
  return data
}

export async function apiBlob(path, { method = 'GET', _reintento = false } = {}) {
  const headers = {}
  if (tokens.access) headers.Authorization = `Bearer ${tokens.access}`
  const r = await fetch(`${BASE}${path}`, { method, headers })
  if (r.status === 401) {
    if (!_reintento && await refrescarToken()) return apiBlob(path, { method, _reintento: true })
    throw sesionExpirada()
  }
  if (!r.ok) {
    // El servidor explica el motivo (p. ej. «La auditoría aún no tiene plan» o falta de permiso).
    const data = await r.json().catch(() => null)
    throw new Error(mensajeError(data) || `No se pudo generar el documento (HTTP ${r.status}).`)
  }
  return r.blob()
}

export const api = {
  async login(username, password) {
    const r = await fetch(`${BASE}/auth/login/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    })
    const data = await r.json().catch(() => null)
    if (!r.ok) throw new Error(data?.detail || 'Credenciales incorrectas')
    tokens.set(data.access, data.refresh)
    await activarArchivos()
    return data
  },
  logout() {
    fetch(`${BASE}/auth/media/`, { method: 'DELETE' }).catch(() => {})
    tokens.clear()
  },
  activarArchivos,
  haySesion() { return Boolean(tokens.access) },
  me: () => apiFetch('/auth/me/'),
  // Usuarios
  usuarios: {
    listar: (params = '') => apiFetch(`/usuarios/${params}`),
    crear: (data) => apiFetch('/usuarios/', { method: 'POST', body: data }),
    editar: (id, data) => apiFetch(`/usuarios/${id}/`, { method: 'PATCH', body: data }),
    editarMultipart: (id, formData) => apiUpload(`/usuarios/${id}/`, formData, { method: 'PATCH' }),
    desactivar: (id) => apiFetch(`/usuarios/${id}/`, { method: 'DELETE' }),
    activar: (id) => apiFetch(`/usuarios/${id}/activar/`, { method: 'POST' }),
    asignarRoles: (id, roles) => apiFetch(`/usuarios/${id}/asignar_roles/`, { method: 'POST', body: { roles } }),
  },
  // Organización y personal (núcleo): áreas, puestos y trabajadores comunes a todo el sistema
  ubigeos: () => apiFetch('/ubigeos/'),
  org: {
    sedes: (params = '') => apiFetch(`/org-sedes/${params}`),
    crearSede: (data) => apiFetch('/org-sedes/', { method: 'POST', body: data }),
    editarSede: (id, data) => apiFetch(`/org-sedes/${id}/`, { method: 'PATCH', body: data }),
    desactivarSede: (id) => apiFetch(`/org-sedes/${id}/`, { method: 'DELETE' }),
    catalogosSedes: () => apiFetch('/org-sedes/catalogos/'),
    crearNivel: (data) => apiFetch('/org-niveles/', { method: 'POST', body: data }),
    editarNivel: (id, data) => apiFetch(`/org-niveles/${id}/`, { method: 'PATCH', body: data }),
    desactivarNivel: (id) => apiFetch(`/org-niveles/${id}/`, { method: 'DELETE' }),
    suministros: (params = '') => apiFetch(`/org-suministros/${params}`),
    crearSuministro: (data) => apiFetch('/org-suministros/', { method: 'POST', body: data }),
    editarSuministro: (id, data) => apiFetch(`/org-suministros/${id}/`, { method: 'PATCH', body: data }),
    desactivarSuministro: (id) => apiFetch(`/org-suministros/${id}/`, { method: 'DELETE' }),
    areas: (params = '') => apiFetch(`/org-areas/${params}`),
    crearArea: (data) => apiFetch('/org-areas/', { method: 'POST', body: data }),
    editarArea: (id, data) => apiFetch(`/org-areas/${id}/`, { method: 'PATCH', body: data }),
    desactivarArea: (id) => apiFetch(`/org-areas/${id}/`, { method: 'DELETE' }),
    catalogos: () => apiFetch('/org-areas/catalogos/'),
    puestos: (params = '') => apiFetch(`/org-puestos/${params}`),
    puesto: (id) => apiFetch(`/org-puestos/${id}/`),
    crearPuesto: (data) => apiFetch('/org-puestos/', { method: 'POST', body: data }),
    editarPuesto: (id, data) => apiFetch(`/org-puestos/${id}/`, { method: 'PATCH', body: data }),
    desactivarPuesto: (id) => apiFetch(`/org-puestos/${id}/`, { method: 'DELETE' }),
    trabajadores: (params = '') => apiFetch(`/org-trabajadores/${params}`),
    trabajador: (id) => apiFetch(`/org-trabajadores/${id}/`),
    crearTrabajador: (data) => apiFetch('/org-trabajadores/', { method: 'POST', body: data }),
    editarTrabajador: (id, data) => apiFetch(`/org-trabajadores/${id}/`, { method: 'PATCH', body: data }),
    accionTrabajador: (id, nombre, data = {}) => apiFetch(`/org-trabajadores/${id}/${nombre}/`, { method: 'POST', body: data }),
    reactivar: (recurso, id) => apiFetch(`/org-${recurso}/${id}/reactivar/`, { method: 'POST', body: {} }),
  },
  // Catálogo gestionable (áreas / laboratorios)
  opcionesCatalogo: {
    listar: (tipo) => apiFetch(`/opciones-catalogo/?tipo=${tipo}`),
    crear: (tipo, nombre) => apiFetch('/opciones-catalogo/', { method: 'POST', body: { tipo, nombre } }),
    editar: (id, data) => apiFetch(`/opciones-catalogo/${id}/`, { method: 'PATCH', body: data }),
    eliminar: (id) => apiFetch(`/opciones-catalogo/${id}/`, { method: 'DELETE' }),
  },
  // Catálogos del módulo Equipos (magnitud con prefijo, clasificación con regla de patrón)
  magnitudesEquipo: {
    listar: () => apiFetch('/magnitudes-equipo/'),
    crear: (nombre) => apiFetch('/magnitudes-equipo/', { method: 'POST', body: { nombre } }),
    editar: (id, data) => apiFetch(`/magnitudes-equipo/${id}/`, { method: 'PATCH', body: data }),
    eliminar: (id) => apiFetch(`/magnitudes-equipo/${id}/`, { method: 'DELETE' }),
  },
  clasificacionesEquipo: {
    listar: () => apiFetch('/clasificaciones-equipo/'),
    crear: (nombre) => apiFetch('/clasificaciones-equipo/', { method: 'POST', body: { nombre } }),
    editar: (id, data) => apiFetch(`/clasificaciones-equipo/${id}/`, { method: 'PATCH', body: data }),
    eliminar: (id) => apiFetch(`/clasificaciones-equipo/${id}/`, { method: 'DELETE' }),
  },
  // Roles
  roles: {
    listar: () => apiFetch('/roles/'),
    crear: (data) => apiFetch('/roles/', { method: 'POST', body: data }),
    editar: (id, data) => apiFetch(`/roles/${id}/`, { method: 'PATCH', body: data }),
    desactivar: (id) => apiFetch(`/roles/${id}/`, { method: 'DELETE' }),
  },
  catalogo: () => apiFetch('/configuracion/catalogo/'),
  // M9 — Solicitudes de Acción Correctiva
  sac: {
    listar: (params = '') => apiFetch(`/sac/${params}`),
    detalle: (id) => apiFetch(`/sac/${id}/`),
    crear: (data) => apiFetch('/sac/', { method: 'POST', body: data }),
    editar: (id, data) => apiFetch(`/sac/${id}/`, { method: 'PATCH', body: data }),
    desactivar: (id) => apiFetch(`/sac/${id}/`, { method: 'DELETE' }),
    pdf: (id) => apiBlob(`/sac/${id}/pdf/`),
    seguimientoPdf: (params = '') => apiBlob(`/sac/seguimiento_pdf/${params}`),
    evaluar: (id, data) => apiFetch(`/sac/${id}/evaluar/`, { method: 'POST', body: data }),
    registrarAnalisis: (id, data) => apiFetch(`/sac/${id}/registrar_analisis/`, { method: 'POST', body: data }),
    agregarAccion: (id, data) => apiFetch(`/sac/${id}/agregar_accion/`, { method: 'POST', body: data }),
    editarAccion: (id, data) => apiFetch(`/sac/${id}/editar_accion/`, { method: 'POST', body: data }),
    quitarAccion: (id, accionId) => apiFetch(`/sac/${id}/quitar_accion/`, { method: 'POST', body: { accion_id: accionId } }),
    reabrirAccion: (id, accionId, motivo) => apiFetch(`/sac/${id}/reabrir_accion/`, { method: 'POST', body: { accion_id: accionId, motivo } }),
    aprobarPlan: (id, verificador) => apiFetch(`/sac/${id}/aprobar_plan/`, { method: 'POST', body: { verificador } }),
    completarAccion: (id, formData) => apiUpload(`/sac/${id}/completar_accion/`, formData),
    verificarEficacia: (id, eficaz, evaluacion) => apiFetch(`/sac/${id}/verificar_eficacia/`, { method: 'POST', body: { eficaz, evaluacion } }),
    resumen: () => apiFetch('/sac/resumen/'),
  },
  // M18 — Quejas
  quejas: {
    listar: (params = '') => apiFetch(`/quejas/${params}`),
    detalle: (id) => apiFetch(`/quejas/${id}/`),
    crear: (data) => apiFetch('/quejas/', { method: 'POST', body: data }),
    editar: (id, data) => apiFetch(`/quejas/${id}/`, { method: 'PATCH', body: data }),
    anular: (id) => apiFetch(`/quejas/${id}/`, { method: 'DELETE' }),
    catalogos: () => apiFetch('/quejas/catalogos/'),
    validar: (id, data) => apiFetch(`/quejas/${id}/validar/`, { method: 'POST', body: data }),
    decidir: (id, data) => apiFetch(`/quejas/${id}/decidir/`, { method: 'POST', body: data }),
    registrarNc: (id, data) => apiFetch(`/quejas/${id}/registrar_nc/`, { method: 'POST', body: data }),
    pasarACierre: (id) => apiFetch(`/quejas/${id}/pasar_a_cierre/`, { method: 'POST', body: {} }),
    cerrar: (id, data) => apiFetch(`/quejas/${id}/cerrar/`, { method: 'POST', body: data }),
    reabrir: (id, motivo) => apiFetch(`/quejas/${id}/reabrir/`, { method: 'POST', body: { motivo } }),
    comunicar: (id, formData) => apiUpload(`/quejas/${id}/comunicar/`, formData),
    adjuntar: (id, formData) => apiUpload(`/quejas/${id}/adjuntar/`, formData),
    quitarAdjunto: (id, adjuntoId) => apiFetch(`/quejas/${id}/quitar_adjunto/`, { method: 'POST', body: { adjunto_id: adjuntoId } }),
    pdf: (id) => apiBlob(`/quejas/${id}/pdf/`),
    seguimientoPdf: (params = '') => apiBlob(`/quejas/seguimiento_pdf/${params}`),
  },
  // M17 — Cambios
  cambios: {
    listar: (params = '') => apiFetch(`/cambios/${params}`),
    detalle: (id) => apiFetch(`/cambios/${id}/`),
    crear: (data) => apiFetch('/cambios/', { method: 'POST', body: data }),
    editar: (id, data) => apiFetch(`/cambios/${id}/`, { method: 'PATCH', body: data }),
    anular: (id) => apiFetch(`/cambios/${id}/`, { method: 'DELETE' }),
    catalogos: () => apiFetch('/cambios/catalogos/'),
    accion: (id, nombre, data = {}) => apiFetch(`/cambios/${id}/${nombre}/`, { method: 'POST', body: data }),
    subir: (id, nombre, formData) => apiUpload(`/cambios/${id}/${nombre}/`, formData),
    pdf: (id) => apiBlob(`/cambios/${id}/pdf/`),
    planificacionPdf: (id) => apiBlob(`/cambios/${id}/planificacion_pdf/`),
    seguimientoPdf: (params = '') => apiBlob(`/cambios/seguimiento_pdf/${params}`),
  },
  // M3 — Riesgos y oportunidades
  riesgos: {
    listar: (params = '') => apiFetch(`/riesgos/${params}`),
    detalle: (id) => apiFetch(`/riesgos/${id}/`),
    crear: (data) => apiFetch('/riesgos/', { method: 'POST', body: data }),
    editar: (id, data) => apiFetch(`/riesgos/${id}/`, { method: 'PATCH', body: data }),
    anular: (id) => apiFetch(`/riesgos/${id}/`, { method: 'DELETE' }),
    catalogos: () => apiFetch('/riesgos/catalogos/'),
    indicadores: () => apiFetch('/riesgos/indicadores/'),
    hallazgosDerivados: () => apiFetch('/riesgos/hallazgos_derivados/'),
    accion: (id, nombre, data = {}) => apiFetch(`/riesgos/${id}/${nombre}/`, { method: 'POST', body: data }),
    subir: (id, nombre, formData) => apiUpload(`/riesgos/${id}/${nombre}/`, formData),
    matrizPdf: (params = '') => apiBlob(`/riesgos/matriz_pdf/${params}`),
  },
  mejoras: {
    listar: (params = '') => apiFetch(`/oportunidades-mejora/${params}`),
    crear: (data) => apiFetch('/oportunidades-mejora/', { method: 'POST', body: data }),
    editar: (id, data) => apiFetch(`/oportunidades-mejora/${id}/`, { method: 'PATCH', body: data }),
    anular: (id) => apiFetch(`/oportunidades-mejora/${id}/`, { method: 'DELETE' }),
    accion: (id, nombre, data = {}) => apiFetch(`/oportunidades-mejora/${id}/${nombre}/`, { method: 'POST', body: data }),
    subir: (id, nombre, formData) => apiUpload(`/oportunidades-mejora/${id}/${nombre}/`, formData),
    matrizPdf: (params = '') => apiBlob(`/oportunidades-mejora/matriz_pdf/${params}`),
  },
  contextoRiesgos: {
    listar: (params = '') => apiFetch(`/contexto-riesgos/${params}`),
    crear: (data) => apiFetch('/contexto-riesgos/', { method: 'POST', body: data }),
    editar: (id, data) => apiFetch(`/contexto-riesgos/${id}/`, { method: 'PATCH', body: data }),
    retirar: (id) => apiFetch(`/contexto-riesgos/${id}/`, { method: 'DELETE' }),
  },
  revisionesRiesgos: {
    listar: (matriz) => apiFetch(`/revisiones-riesgos/?matriz=${matriz}`),
    registrar: (tipo, data) => apiFetch(`/revisiones-riesgos/${tipo}/`, { method: 'POST', body: data }),
  },
  // M2 — Requisitos legales
  legal: {
    requisitos: (params = '') => apiFetch(`/requisitos-legales/${params}`),
    requisito: (id) => apiFetch(`/requisitos-legales/${id}/`),
    crearRequisito: (data) => apiFetch('/requisitos-legales/', { method: 'POST', body: data }),
    editarRequisito: (id, data) => apiFetch(`/requisitos-legales/${id}/`, { method: 'PATCH', body: data }),
    anularRequisito: (id) => apiFetch(`/requisitos-legales/${id}/`, { method: 'DELETE' }),
    accionRequisito: (id, nombre, data = {}) => apiFetch(`/requisitos-legales/${id}/${nombre}/`, { method: 'POST', body: data }),
    catalogos: () => apiFetch('/requisitos-legales/catalogos/'),
    indicadores: () => apiFetch('/requisitos-legales/indicadores/'),
    listaPdf: (ambito) => apiBlob(`/requisitos-legales/lista_pdf/?ambito=${ambito}`),
    obligaciones: (params = '') => apiFetch(`/obligaciones-legales/${params}`),
    crearObligacion: (data) => apiFetch('/obligaciones-legales/', { method: 'POST', body: data }),
    editarObligacion: (id, data) => apiFetch(`/obligaciones-legales/${id}/`, { method: 'PATCH', body: data }),
    bajaObligacion: (id, motivo) => apiFetch(`/obligaciones-legales/${id}/dar_de_baja/`, { method: 'POST', body: { motivo } }),
    evaluaciones: (params = '') => apiFetch(`/evaluaciones-legales/${params}`),
    crearEvaluacion: (data) => apiFetch('/evaluaciones-legales/', { method: 'POST', body: data }),
    anularEvaluacion: (id) => apiFetch(`/evaluaciones-legales/${id}/`, { method: 'DELETE' }),
    resultados: (id, params = '') => apiFetch(`/evaluaciones-legales/${id}/resultados/${params}`),
    evaluar: (id, formData) => apiUpload(`/evaluaciones-legales/${id}/evaluar/`, formData),
    cerrarEvaluacion: (id, password) => apiFetch(`/evaluaciones-legales/${id}/cerrar/`, { method: 'POST', body: { password } }),
    matrizPdf: (ambito, anio) => apiBlob(`/evaluaciones-legales/matriz_pdf/?ambito=${ambito}&anio=${anio || ''}`),
  },
  // M23 — Seguridad y Salud en el Trabajo
  // Capacitación e inducción (Talento humano)
  ambiente: {
    aspectos: (params = '') => apiFetch(`/amb-aspectos/${params}`),
    crearAspecto: (data) => apiFetch('/amb-aspectos/', { method: 'POST', body: data }),
    editarAspecto: (id, data) => apiFetch(`/amb-aspectos/${id}/`, { method: 'PATCH', body: data }),
    retirarAspecto: (id, motivo) => apiFetch(`/amb-aspectos/${id}/retirar/`, { method: 'POST', body: { motivo } }),
    catalogos: () => apiFetch('/amb-aspectos/catalogos/'),
    obligaciones: () => apiFetch('/amb-aspectos/obligaciones/'),
    resumen: () => apiFetch('/amb-aspectos/resumen/'),
    aprobaciones: () => apiFetch('/amb-aspectos/aprobaciones/'),
    aprobar: (data) => apiFetch('/amb-aspectos/aprobar/', { method: 'POST', body: data }),
    aprobarPapel: (fd) => apiUpload('/amb-aspectos/aprobar/', fd),
    matrizPdf: () => apiBlob('/amb-aspectos/pdf/'),
    consumos: (params = '') => apiFetch(`/amb-consumos/${params}`),
    guardarConsumo: (id, fd) => (id ? apiUpload(`/amb-consumos/${id}/`, fd, { method: 'PATCH' }) : apiUpload('/amb-consumos/', fd)),
    quitarConsumo: (id) => apiFetch(`/amb-consumos/${id}/`, { method: 'DELETE' }),
    indicadores: (anio, sede = '') => apiFetch(`/amb-consumos/indicadores/?anio=${anio}${sede ? `&sede=${sede}` : ''}`),
    lecturaAnterior: (suministro, anio, mes, excluir = '') => apiFetch(`/amb-consumos/anterior/?suministro=${suministro}&anio=${anio}&mes=${mes}${excluir ? `&excluir=${excluir}` : ''}`),
    consumo: (id) => apiFetch(`/amb-consumos/${id}/`),
    catalogosResiduos: () => apiFetch('/amb-pesajes/catalogos/'),
    pesajes: (params = '') => apiFetch(`/amb-pesajes/${params}`),
    guardarPesaje: (id, data) => (id ? apiFetch(`/amb-pesajes/${id}/`, { method: 'PATCH', body: data }) : apiFetch('/amb-pesajes/', { method: 'POST', body: data })),
    accionPesaje: (id, accion, data = {}) => apiFetch(`/amb-pesajes/${id}/${accion}/`, { method: 'POST', body: data }),
    pesajePdf: (id) => apiBlob(`/amb-pesajes/${id}/pdf/`),
    resumenResiduos: (anio, sede = '') => apiFetch(`/amb-pesajes/resumen_anual/?anio=${anio}${sede ? `&sede=${sede}` : ''}`),
    disposiciones: (params = '') => apiFetch(`/amb-disposiciones/${params}`),
    guardarDisposicion: (id, fd) => (id ? apiUpload(`/amb-disposiciones/${id}/`, fd, { method: 'PATCH' }) : apiUpload('/amb-disposiciones/', fd)),
    quitarDisposicion: (id) => apiFetch(`/amb-disposiciones/${id}/`, { method: 'DELETE' }),
  },
  tnc: {
    catalogos: () => apiFetch('/tnc/catalogos/'),
    opciones: () => apiFetch('/tnc/opciones/'),
    listar: (params = '') => apiFetch(`/tnc/${params}`),
    detalle: (id) => apiFetch(`/tnc/${id}/`),
    crear: (data) => apiFetch('/tnc/', { method: 'POST', body: data }),
    editar: (id, data) => apiFetch(`/tnc/${id}/`, { method: 'PATCH', body: data }),
    accion: (id, nombre, data = {}) => apiFetch(`/tnc/${id}/${nombre}/`, { method: 'POST', body: data }),
    adjuntar: (id, fd) => apiUpload(`/tnc/${id}/adjuntar/`, fd),
    pdf: (id) => apiBlob(`/tnc/${id}/pdf/`),
  },
  cumplimiento: {
    opciones: () => apiFetch('/cumplimiento/opciones/'),
    matriz: (norma) => apiFetch(`/cumplimiento/matriz/?norma=${norma}`),
    tablero: () => apiFetch('/cumplimiento/tablero/'),
    evaluar: (data) => apiFetch('/cumplimiento/evaluar/', { method: 'POST', body: data }),
    hallazgo: (data) => apiFetch('/cumplimiento/hallazgo/', { method: 'POST', body: data }),
    corte: (data) => apiFetch('/cumplimiento/corte/', { method: 'POST', body: data }),
    pdf: (norma, sede) => apiBlob(`/cumplimiento/pdf/?norma=${norma}&sede=${sede || ''}`),
    crearOtro: (data) => apiFetch('/cumplimiento-otros/', { method: 'POST', body: data }),
    bajaOtro: (id, data) => apiFetch(`/cumplimiento-otros/${id}/baja/`, { method: 'POST', body: data }),
  },
  revision: {
    catalogos: () => apiFetch('/rd-revisiones/catalogos/'),
    revisiones: (params = '') => apiFetch(`/rd-revisiones/${params}`),
    revision: (id) => apiFetch(`/rd-revisiones/${id}/`),
    crear: (data) => apiFetch('/rd-revisiones/', { method: 'POST', body: data }),
    editar: (id, data) => apiFetch(`/rd-revisiones/${id}/`, { method: 'PATCH', body: data }),
    accion: (id, nombre, data = {}) => apiFetch(`/rd-revisiones/${id}/${nombre}/`, { method: 'POST', body: data }),
    informePdf: (id) => apiBlob(`/rd-revisiones/${id}/pdf/`),
    planPdf: (id) => apiBlob(`/rd-revisiones/${id}/plan_pdf/`),
    programa: (anio) => apiFetch(`/rd-programas/anio/?anio=${anio}`),
    crearPrograma: (anio) => apiFetch('/rd-programas/', { method: 'POST', body: { anio } }),
    editarPrograma: (id, data) => apiFetch(`/rd-programas/${id}/`, { method: 'PATCH', body: data }),
    itemPrograma: (id, data) => apiFetch(`/rd-programas/${id}/item/`, { method: 'POST', body: data }),
    programaPdf: (id) => apiBlob(`/rd-programas/${id}/pdf/`),
    acuerdos: (params = '') => apiFetch(`/rd-acuerdos/${params}`),
    seguimiento: (id, fd) => apiUpload(`/rd-acuerdos/${id}/`, fd, { method: 'PATCH' }),
    cerrarAcuerdo: (id, password) => apiFetch(`/rd-acuerdos/${id}/cerrar/`, { method: 'POST', body: { password } }),
  },
  capacitacion: {
    catalogos: () => apiFetch('/cap-programas/catalogos/'),
    programa: (anio) => apiFetch(`/cap-programas/anio/?anio=${anio}`),
    crearPrograma: (anio) => apiFetch('/cap-programas/', { method: 'POST', body: { anio } }),
    accionPrograma: (id, nombre, data = {}) => apiFetch(`/cap-programas/${id}/${nombre}/`, { method: 'POST', body: data }),
    aprobarProgramaPapel: (id, formData) => apiUpload(`/cap-programas/${id}/aprobar/`, formData),
    programaPdf: (id) => apiBlob(`/cap-programas/${id}/pdf/`),
    firmantes: () => apiFetch('/cap-programas/firmantes/'),
    resumen: (anio) => apiFetch(`/cap-programas/resumen/?anio=${anio}`),
    situacion: (anio, trabajador) => apiFetch(`/cap-programas/situacion/?anio=${anio}${trabajador ? `&trabajador=${trabajador}` : ''}`),
    sesiones: (params = '') => apiFetch(`/cap-sesiones/${params}`),
    sesion: (id) => apiFetch(`/cap-sesiones/${id}/`),
    crearSesion: (data) => apiFetch('/cap-sesiones/', { method: 'POST', body: data }),
    editarSesion: (id, data) => apiFetch(`/cap-sesiones/${id}/`, { method: 'PATCH', body: data }),
    accionSesion: (id, nombre, data = {}) => apiFetch(`/cap-sesiones/${id}/${nombre}/`, { method: 'POST', body: data }),
    subirSesion: (id, nombre, formData) => apiUpload(`/cap-sesiones/${id}/${nombre}/`, formData),
    sesionPdf: (id) => apiBlob(`/cap-sesiones/${id}/pdf/`),
    inducciones: (params = '') => apiFetch(`/cap-inducciones/${params}`),
    induccion: (id) => apiFetch(`/cap-inducciones/${id}/`),
    crearInduccion: (data) => apiFetch('/cap-inducciones/', { method: 'POST', body: data }),
    accionInduccion: (id, nombre, data = {}) => apiFetch(`/cap-inducciones/${id}/${nombre}/`, { method: 'POST', body: data }),
    induccionPdf: (id) => apiBlob(`/cap-inducciones/${id}/pdf/`),
    plantillas: () => apiFetch('/cap-plantillas/'),
    editarPlantilla: (id, data) => apiFetch(`/cap-plantillas/${id}/`, { method: 'PATCH', body: data }),
    documentosSig: () => apiFetch('/cap-plantillas/documentos_sig/'),
  },

  sst: {
    filas: (params = '') => apiFetch(`/sst-iperc/${params}`),
    fila: (id) => apiFetch(`/sst-iperc/${id}/`),
    crearFila: (data) => apiFetch('/sst-iperc/', { method: 'POST', body: data }),
    editarFila: (id, data) => apiFetch(`/sst-iperc/${id}/`, { method: 'PATCH', body: data }),
    retirarFila: (id, motivo) => apiFetch(`/sst-iperc/${id}/retirar/`, { method: 'POST', body: { motivo } }),
    catalogos: () => apiFetch('/sst-iperc/catalogos/'),
    resumen: () => apiFetch('/sst-iperc/resumen/'),
    porPuesto: () => apiFetch('/sst-iperc/por_puesto/'),
    porTrabajador: (id) => apiFetch(`/sst-iperc/por_trabajador/?trabajador=${id}`),
    revisarArea: (data) => apiFetch('/sst-iperc/revisar_area/', { method: 'POST', body: data }),
    aprobacionesIperc: () => apiFetch('/sst-iperc/aprobaciones/'),
    aprobarIperc: (data) => apiFetch('/sst-iperc/aprobar_comite/', { method: 'POST', body: data }),
    aprobarIpercPapel: (formData) => apiUpload('/sst-iperc/aprobar_comite/', formData),
    matrizPdf: (area) => apiBlob(`/sst-iperc/matriz_pdf/?area=${encodeURIComponent(area || '')}`),
    ats: (params = '') => apiFetch(`/sst-ats/${params}`),
    unAts: (id) => apiFetch(`/sst-ats/${id}/`),
    crearAts: (data) => apiFetch('/sst-ats/', { method: 'POST', body: data }),
    editarAts: (id, data) => apiFetch(`/sst-ats/${id}/`, { method: 'PATCH', body: data }),
    accionAts: (id, nombre, data = {}) => apiFetch(`/sst-ats/${id}/${nombre}/`, { method: 'POST', body: data }),
    atsPdf: (id) => apiBlob(`/sst-ats/${id}/pdf/`),
    eventos: (params = '') => apiFetch(`/sst-eventos/${params}`),
    evento: (id) => apiFetch(`/sst-eventos/${id}/`),
    crearEvento: (data) => apiFetch('/sst-eventos/', { method: 'POST', body: data }),
    editarEvento: (id, data) => apiFetch(`/sst-eventos/${id}/`, { method: 'PATCH', body: data }),
    accionEvento: (id, nombre, data = {}) => apiFetch(`/sst-eventos/${id}/${nombre}/`, { method: 'POST', body: data }),
    subirEvento: (id, nombre, formData) => apiUpload(`/sst-eventos/${id}/${nombre}/`, formData),
    catalogosEventos: () => apiFetch('/sst-eventos/catalogos/'),
    registroPdf: (id) => apiBlob(`/sst-eventos/${id}/registro_pdf/`),
    informePdf: (id) => apiBlob(`/sst-eventos/${id}/informe_pdf/`),
    enfermedades: (params = '') => apiFetch(`/sst-enfermedades/${params}`),
    crearEnfermedad: (data) => apiFetch('/sst-enfermedades/', { method: 'POST', body: data }),
    editarEnfermedad: (id, data) => apiFetch(`/sst-enfermedades/${id}/`, { method: 'PATCH', body: data }),
    accionEnfermedad: (id, nombre, data = {}) => apiFetch(`/sst-enfermedades/${id}/${nombre}/`, { method: 'POST', body: data }),
    enfermedadPdf: (id) => apiBlob(`/sst-enfermedades/${id}/pdf/`),
    estadisticas: (anio) => apiFetch(`/sst-estadisticas/anio/?anio=${anio}`),
    datosMes: (data) => apiFetch('/sst-estadisticas/datos_mes/', { method: 'POST', body: data }),
    informeEstadisticas: (data) => apiFetch('/sst-estadisticas/informe/', { method: 'POST', body: data }),
    estadisticasPdf: (anio, informe) => apiBlob(`/sst-estadisticas/registro_pdf/?anio=${anio}${informe ? `&informe=${informe}` : ''}`),
    datosEstadisticasPdf: (anio) => apiBlob(`/sst-estadisticas/datos_pdf/?anio=${anio}`),
    recibirAts: (id, formData) => apiUpload(`/sst-ats/${id}/recibir/`, formData),
    atsResumen: () => apiFetch('/sst-ats/resumen/'),
    tipos: () => apiFetch('/sst-ats-tipo/'),
    crearTipo: (data) => apiFetch('/sst-ats-tipo/', { method: 'POST', body: data }),
    editarTipo: (id, data) => apiFetch(`/sst-ats-tipo/${id}/`, { method: 'PATCH', body: data }),
    desactivarTipo: (id) => apiFetch(`/sst-ats-tipo/${id}/`, { method: 'DELETE' }),
    // Inspecciones (inventario, plantillas, inspecciones) y monitoreos
    elementos: (params = '') => apiFetch(`/sst-elementos/${params}`),
    crearElemento: (data) => apiFetch('/sst-elementos/', { method: 'POST', body: data }),
    editarElemento: (id, data) => apiFetch(`/sst-elementos/${id}/`, { method: 'PATCH', body: data }),
    bajaElemento: (id, motivo) => apiFetch(`/sst-elementos/${id}/dar_baja/`, { method: 'POST', body: { motivo } }),
    catalogosInspeccion: () => apiFetch('/sst-elementos/catalogos/'),
    plantillas: (params = '') => apiFetch(`/sst-plantillas/${params}`),
    crearPlantilla: (data) => apiFetch('/sst-plantillas/', { method: 'POST', body: data }),
    editarPlantilla: (id, data) => apiFetch(`/sst-plantillas/${id}/`, { method: 'PATCH', body: data }),
    desactivarPlantilla: (id) => apiFetch(`/sst-plantillas/${id}/`, { method: 'DELETE' }),
    inspecciones: (params = '') => apiFetch(`/sst-inspecciones/${params}`),
    inspeccion: (id) => apiFetch(`/sst-inspecciones/${id}/`),
    crearInspeccion: (data) => apiFetch('/sst-inspecciones/', { method: 'POST', body: data }),
    editarInspeccion: (id, data) => apiFetch(`/sst-inspecciones/${id}/`, { method: 'PATCH', body: data }),
    accionInspeccion: (id, nombre, data = {}) => apiFetch(`/sst-inspecciones/${id}/${nombre}/`, { method: 'POST', body: data }),
    subirInspeccion: (id, nombre, formData) => apiUpload(`/sst-inspecciones/${id}/${nombre}/`, formData),
    inspeccionPdf: (id) => apiBlob(`/sst-inspecciones/${id}/pdf/`),
    programaInspecciones: (anio) => apiFetch(`/sst-inspecciones/programa/?anio=${anio}`),
    resumenInspecciones: () => apiFetch('/sst-inspecciones/resumen/'),
    programaMonitoreos: (anio) => apiFetch(`/sst-programa-monitoreos/anio/?anio=${anio}`),
    crearProgramaMonitoreos: (anio) => apiFetch('/sst-programa-monitoreos/', { method: 'POST', body: { anio } }),
    itemProgramaMonitoreos: (id, data) => apiFetch(`/sst-programa-monitoreos/${id}/item/`, { method: 'POST', body: data }),
    quitarItemMonitoreos: (id, data) => apiFetch(`/sst-programa-monitoreos/${id}/quitar_item/`, { method: 'POST', body: data }),
    programaMonitoreosPdf: (id) => apiBlob(`/sst-programa-monitoreos/${id}/pdf/`),
    monitoreos: (params = '') => apiFetch(`/sst-monitoreos/${params}`),
    crearMonitoreo: (data) => apiFetch('/sst-monitoreos/', { method: 'POST', body: data }),
    editarMonitoreo: (id, data) => apiFetch(`/sst-monitoreos/${id}/`, { method: 'PATCH', body: data }),
    accionMonitoreo: (id, nombre, data = {}) => apiFetch(`/sst-monitoreos/${id}/${nombre}/`, { method: 'POST', body: data }),
    subirMonitoreo: (id, formData) => apiUpload(`/sst-monitoreos/${id}/informe/`, formData),
    monitoreoPdf: (id) => apiBlob(`/sst-monitoreos/${id}/pdf/`),
    recomendaciones: (params = '') => apiFetch(`/sst-recomendaciones/${params}`),
    crearRecomendacion: (data) => apiFetch('/sst-recomendaciones/', { method: 'POST', body: data }),
    editarRecomendacion: (id, data) => apiFetch(`/sst-recomendaciones/${id}/`, { method: 'PATCH', body: data }),
    retirarRecomendacion: (id) => apiFetch(`/sst-recomendaciones/${id}/`, { method: 'DELETE' }),
    recomendacionesPdf: (anio) => apiBlob(`/sst-recomendaciones/programa_pdf/?anio=${anio}`),
    // EPP y vigilancia médica
    eppCatalogo: (params = '') => apiFetch(`/sst-epp-catalogo/${params}`),
    crearEpp: (data) => apiFetch('/sst-epp-catalogo/', { method: 'POST', body: data }),
    editarEpp: (id, data) => apiFetch(`/sst-epp-catalogo/${id}/`, { method: 'PATCH', body: data }),
    desactivarEpp: (id) => apiFetch(`/sst-epp-catalogo/${id}/`, { method: 'DELETE' }),
    catalogosEpp: () => apiFetch('/sst-epp-catalogo/catalogos/'),
    matrizEpp: () => apiFetch('/sst-epp-matriz/'),
    crearPerfilEpp: (data) => apiFetch('/sst-epp-matriz/', { method: 'POST', body: data }),
    editarPerfilEpp: (id, data) => apiFetch(`/sst-epp-matriz/${id}/`, { method: 'PATCH', body: data }),
    requisitosEpp: (id, requisitos) => apiFetch(`/sst-epp-matriz/${id}/requisitos/`, { method: 'POST', body: { requisitos } }),
    desactivarPerfilEpp: (id) => apiFetch(`/sst-epp-matriz/${id}/`, { method: 'DELETE' }),
    matrizEppPdf: () => apiBlob('/sst-epp-matriz/matriz_pdf/'),
    entregasEpp: (params = '') => apiFetch(`/sst-epp-entregas/${params}`),
    entregaEpp: (id) => apiFetch(`/sst-epp-entregas/${id}/`),
    crearEntregaEpp: (data) => apiFetch('/sst-epp-entregas/', { method: 'POST', body: data }),
    editarEntregaEpp: (id, data) => apiFetch(`/sst-epp-entregas/${id}/`, { method: 'PATCH', body: data }),
    accionEntregaEpp: (id, nombre, data = {}) => apiFetch(`/sst-epp-entregas/${id}/${nombre}/`, { method: 'POST', body: data }),
    subirEntregaEpp: (id, nombre, formData) => apiUpload(`/sst-epp-entregas/${id}/${nombre}/`, formData),
    estadoEpp: (trabajador) => apiFetch(`/sst-epp-entregas/estado/?trabajador=${trabajador}`),
    sugerirEpp: (trabajador, campo) => apiFetch(`/sst-epp-entregas/sugerir/?trabajador=${trabajador}${campo ? '&campo=1' : ''}`),
    resumenEpp: () => apiFetch('/sst-epp-entregas/resumen/'),
    restablecerPin: (trabajador) => apiFetch('/sst-epp-entregas/restablecer_pin/', { method: 'POST', body: { trabajador } }),
    entregaEppPdf: (id) => apiBlob(`/sst-epp-entregas/${id}/pdf/`),
    tarjetaEppPdf: (trabajador) => apiBlob(`/sst-epp-entregas/tarjeta_pdf/?trabajador=${trabajador}`),
    emos: (params = '') => apiFetch(`/sst-emo/${params}`),
    emo: (id) => apiFetch(`/sst-emo/${id}/`),
    crearEmo: (data) => apiFetch('/sst-emo/', { method: 'POST', body: data }),
    editarEmo: (id, data) => apiFetch(`/sst-emo/${id}/`, { method: 'PATCH', body: data }),
    accionEmo: (id, nombre, data = {}) => apiFetch(`/sst-emo/${id}/${nombre}/`, { method: 'POST', body: data }),
    subirEmo: (id, formData) => apiUpload(`/sst-emo/${id}/certificado/`, formData),
    emoPdf: (id) => apiBlob(`/sst-emo/${id}/pdf/`),
    vigilancia: () => apiFetch('/sst-emo/vigilancia/'),
    subirAccionEmo: (id, nombre, formData) => apiUpload(`/sst-emo/${id}/${nombre}/`, formData),
    anexo4: () => apiFetch('/sst-emo/anexo4/'),
    registrarAnexo4: (formData) => apiUpload('/sst-emo/registrar_anexo4/', formData),

    // Comité de SST y Programa anual SSOMA
    comiteVigente: () => apiFetch('/sst-comite/vigente/'),
    comites: () => apiFetch('/sst-comite/'),
    crearComite: (data) => apiFetch('/sst-comite/', { method: 'POST', body: data }),
    editarComite: (id, data) => apiFetch(`/sst-comite/${id}/`, { method: 'PATCH', body: data }),
    catalogosComite: () => apiFetch('/sst-comite/catalogos/'),
    accionComite: (id, nombre, data = {}) => apiFetch(`/sst-comite/${id}/${nombre}/`, { method: 'POST', body: data }),
    subirComite: (id, formData) => apiUpload(`/sst-comite/${id}/adjuntar/`, formData),
    reuniones: (params = '') => apiFetch(`/sst-comite-reuniones/${params}`),
    crearReunion: (data) => apiFetch('/sst-comite-reuniones/', { method: 'POST', body: data }),
    editarReunion: (id, data) => apiFetch(`/sst-comite-reuniones/${id}/`, { method: 'PATCH', body: data }),
    accionReunion: (id, nombre, data = {}) => apiFetch(`/sst-comite-reuniones/${id}/${nombre}/`, { method: 'POST', body: data }),
    cerrarReunion: (id, formData) => apiUpload(`/sst-comite-reuniones/${id}/cerrar/`, formData),
    actaPdf: (id) => apiBlob(`/sst-comite-reuniones/${id}/pdf/`),
    acuerdos: (params = '') => apiFetch(`/sst-comite-acuerdos/${params}`),
    seguimientoAcuerdo: (id, data) => apiFetch(`/sst-comite-acuerdos/${id}/seguimiento/`, { method: 'POST', body: data }),
    programaSsoma: (anio) => apiFetch(`/sst-programa-ssoma/anio/?anio=${anio}`),
    crearProgramaSsoma: (data) => apiFetch('/sst-programa-ssoma/', { method: 'POST', body: data }),
    editarProgramaSsoma: (id, data) => apiFetch(`/sst-programa-ssoma/${id}/`, { method: 'PATCH', body: data }),
    accionProgramaSsoma: (id, nombre, data = {}) => apiFetch(`/sst-programa-ssoma/${id}/${nombre}/`, { method: 'POST', body: data }),
    firmantesSsoma: () => apiFetch('/sst-programa-ssoma/firmantes/'),
    aprobarSsomaPapel: (id, fd) => apiUpload(`/sst-programa-ssoma/${id}/aprobar/`, fd),
    programaSsomaPdf: (id) => apiBlob(`/sst-programa-ssoma/${id}/pdf/`),
  },
  // M7 — Procesos
  procesos: {
    listar: (params = '') => apiFetch(`/procesos/${params}`),
    crear: (data) => apiFetch('/procesos/', { method: 'POST', body: data }),
    editar: (id, data) => apiFetch(`/procesos/${id}/`, { method: 'PATCH', body: data }),
    desactivar: (id) => apiFetch(`/procesos/${id}/`, { method: 'DELETE' }),
    reactivar: (id) => apiFetch(`/procesos/${id}/reactivar/`, { method: 'POST', body: {} }),
    catalogos: () => apiFetch('/procesos/catalogos/'),
    mapa: () => apiFetch('/procesos/mapa/'),
    vinculados: (id) => apiFetch(`/procesos/${id}/vinculados/`),
    mapaPdf: () => apiBlob('/procesos/mapa_pdf/'),
    fichas: (params = '') => apiFetch(`/fichas-proceso/${params}`),
    ficha: (id) => apiFetch(`/fichas-proceso/${id}/`),
    crearFicha: (data) => apiFetch('/fichas-proceso/', { method: 'POST', body: data }),
    editarFicha: (id, data) => apiFetch(`/fichas-proceso/${id}/`, { method: 'PATCH', body: data }),
    enviar: (id, password) => apiFetch(`/fichas-proceso/${id}/enviar/`, { method: 'POST', body: { password } }),
    revisar: (id, password) => apiFetch(`/fichas-proceso/${id}/revisar/`, { method: 'POST', body: { password } }),
    aprobar: (id, password) => apiFetch(`/fichas-proceso/${id}/aprobar/`, { method: 'POST', body: { password } }),
    devolver: (id, comentarios) => apiFetch(`/fichas-proceso/${id}/devolver/`, { method: 'POST', body: { comentarios } }),
    nuevaVersion: (id, motivo) => apiFetch(`/fichas-proceso/${id}/nueva_version/`, { method: 'POST', body: { motivo } }),
    fichaPdf: (id) => apiBlob(`/fichas-proceso/${id}/pdf/`),
    avisos: (params = '') => apiFetch(`/avisos-proceso/${params}`),
    crearAviso: (data) => apiFetch('/avisos-proceso/', { method: 'POST', body: data }),
    descartarAviso: (id, motivo) => apiFetch(`/avisos-proceso/${id}/descartar/`, { method: 'POST', body: { motivo } }),
    resultados: (params = '') => apiFetch(`/resultados-indicador/${params}`),
    crearResultado: (data) => apiFetch('/resultados-indicador/', { method: 'POST', body: data }),
    editarResultado: (id, data) => apiFetch(`/resultados-indicador/${id}/`, { method: 'PATCH', body: data }),
    quitarResultado: (id) => apiFetch(`/resultados-indicador/${id}/`, { method: 'DELETE' }),
  },
  // M8 — Hallazgos
  hallazgos: {
    listar: (params = '') => apiFetch(`/hallazgos/${params}`),
    detalle: (id) => apiFetch(`/hallazgos/${id}/`),
    crear: (formData) => apiUpload('/hallazgos/', formData),
    editar: (id, data) => apiFetch(`/hallazgos/${id}/`, { method: 'PATCH', body: data }),
    desactivar: (id) => apiFetch(`/hallazgos/${id}/`, { method: 'DELETE' }),
    reclasificar: (id, tipo, motivo) => apiFetch(`/hallazgos/${id}/reclasificar/`, { method: 'POST', body: { tipo, motivo } }),
    generarSac: (id) => apiFetch(`/hallazgos/${id}/generar_sac/`, { method: 'POST' }),
    sacAbiertas: (id) => apiFetch(`/hallazgos/${id}/sac_abiertas/`),
    vincularSac: (id, sacId) => apiFetch(`/hallazgos/${id}/vincular_sac/`, { method: 'POST', body: { sac_id: sacId } }),
    resumen: () => apiFetch('/hallazgos/resumen/'),
  },
  // M6 — Gestión Documental
  documentos: {
    listar: (params = '') => apiFetch(`/documentos/${params}`),
    detalle: (id) => apiFetch(`/documentos/${id}/`),
    crear: (formData) => apiUpload('/documentos/', formData),
    editar: (id, data) => apiFetch(`/documentos/${id}/`, { method: 'PATCH', body: data }),
    editarFicha: (id, data) => apiFetch(`/documentos/${id}/editar_ficha/`, { method: 'POST', body: data }),
    desactivar: (id) => apiFetch(`/documentos/${id}/`, { method: 'DELETE' }),
    activar: (id) => apiFetch(`/documentos/${id}/activar/`, { method: 'POST' }),
    archivar: (id) => apiFetch(`/documentos/${id}/archivar/`, { method: 'POST' }),
    desarchivar: (id) => apiFetch(`/documentos/${id}/desarchivar/`, { method: 'POST' }),
    enviarRevision: (id, password) => apiFetch(`/documentos/${id}/enviar_revision/`, { method: 'POST', body: { password } }),
    revisar: (id, conforme, comentarios, password, archivoObs) => {
      if (archivoObs) {
        const fd = new FormData()
        fd.append('conforme', conforme ? 'true' : 'false')
        fd.append('comentarios', comentarios)
        fd.append('password', password || '')
        fd.append('archivo_observaciones', archivoObs)
        return apiUpload(`/documentos/${id}/revisar/`, fd)
      }
      return apiFetch(`/documentos/${id}/revisar/`, { method: 'POST', body: { conforme, comentarios, password } })
    },
    aprobar: (id, password) => apiFetch(`/documentos/${id}/aprobar/`, { method: 'POST', body: { password } }),
    aprobarConPdf: (id, formData) => apiUpload(`/documentos/${id}/aprobar/`, formData),
    rechazar: (id, comentarios, archivoObs) => {
      if (archivoObs) {
        const fd = new FormData()
        fd.append('comentarios', comentarios)
        fd.append('archivo_observaciones', archivoObs)
        return apiUpload(`/documentos/${id}/rechazar/`, fd)
      }
      return apiFetch(`/documentos/${id}/rechazar/`, { method: 'POST', body: { comentarios } })
    },
    devolver: (id, comentarios, archivoObs) => {
      if (archivoObs) {
        const fd = new FormData()
        fd.append('comentarios', comentarios)
        fd.append('archivo_observaciones', archivoObs)
        return apiUpload(`/documentos/${id}/devolver/`, fd)
      }
      return apiFetch(`/documentos/${id}/devolver/`, { method: 'POST', body: { comentarios } })
    },
    nuevaVersion: (id, formData) => apiUpload(`/documentos/${id}/nueva_version/`, formData),
    reemplazarArchivo: (id, formData) => apiUpload(`/documentos/${id}/reemplazar_archivo/`, formData),
    porVencer: () => apiFetch('/documentos/por_vencer/'),
    verificarVigencia: (id, vigente, observaciones) => apiFetch(`/documentos/${id}/verificar_vigencia/`, { method: 'POST', body: { vigente, observaciones } }),
    externosPorVerificar: () => apiFetch('/documentos/externos_por_verificar/'),
  },
  auditoria: (params = '') => apiFetch(`/auditoria/${params}`),
  // M10 — Auditorías Internas
  // Devuelve siempre el catálogo completo de la norma: si el servidor responde
  // paginado, recorre todas las páginas y las une.
  requisitosNorma: async (norma) => {
    const primera = await apiFetch(`/requisitos-norma/?norma=${norma}`)
    if (Array.isArray(primera)) return primera
    const filas = [...(primera.results || [])]
    let pagina = 2
    let siguiente = primera.next
    while (siguiente) {
      const d = await apiFetch(`/requisitos-norma/?norma=${norma}&page=${pagina}`)
      filas.push(...(d.results || []))
      siguiente = d.next
      pagina += 1
    }
    return filas
  },
  programasAuditoria: {
    listar: (params = '') => apiFetch(`/programas-auditoria/${params}`),
    detalle: (id) => apiFetch(`/programas-auditoria/${id}/`),
    crear: (data) => apiFetch('/programas-auditoria/', { method: 'POST', body: data }),
    aprobar: (id) => apiFetch(`/programas-auditoria/${id}/aprobar/`, { method: 'POST' }),
    abrirModificacion: (id, motivo) => apiFetch(`/programas-auditoria/${id}/abrir_modificacion/`, { method: 'POST', body: { motivo } }),
    programaPdf: (id) => apiBlob(`/programas-auditoria/${id}/programa_pdf/`),
  },
  auditorias: {
    listar: (params = '') => apiFetch(`/auditorias/${params}`),
    detalle: (id) => apiFetch(`/auditorias/${id}/`),
    crear: (data) => apiFetch('/auditorias/', { method: 'POST', body: data }),
    actualizar: (id, data) => apiFetch(`/auditorias/${id}/`, { method: 'PATCH', body: data }),
    desactivar: (id) => apiFetch(`/auditorias/${id}/`, { method: 'DELETE' }),
    planificar: (id) => apiFetch(`/auditorias/${id}/planificar/`, { method: 'POST' }),
    iniciar: (id) => apiFetch(`/auditorias/${id}/iniciar/`, { method: 'POST' }),
    reprogramar: (id, data) => apiFetch(`/auditorias/${id}/reprogramar/`, { method: 'POST', body: data }),
    agregarIntegrante: (id, data) => apiFetch(`/auditorias/${id}/agregar_integrante/`, { method: 'POST', body: data }),
    quitarIntegrante: (id, integranteId) => apiFetch(`/auditorias/${id}/quitar_integrante/`, { method: 'POST', body: { integrante_id: integranteId } }),
    restaurarIntegrante: (id, integranteId) => apiFetch(`/auditorias/${id}/restaurar_integrante/`, { method: 'POST', body: { integrante_id: integranteId } }),
    registrarActa: (id, data) => apiFetch(`/auditorias/${id}/registrar_acta/`, { method: 'POST', body: data }),
    generarLista: (id, norma) => apiFetch(`/auditorias/${id}/generar_lista/`, { method: 'POST', body: { norma } }),
    evaluarItem: (id, data) => apiFetch(`/auditorias/${id}/evaluar_item/`, { method: 'POST', body: data }),
    registrarHallazgo: (id, data) => apiFetch(`/auditorias/${id}/registrar_hallazgo/`, { method: 'POST', body: data }),
    editarHallazgo: (id, data) => apiFetch(`/auditorias/${id}/editar_hallazgo/`, { method: 'POST', body: data }),
    vincularItems: (id, hallazgoId, itemIds) => apiFetch(`/auditorias/${id}/vincular_items/`, { method: 'POST', body: { hallazgo_id: hallazgoId, item_ids: itemIds } }),
    descartarItems: (id, itemIds, motivo) => apiFetch(`/auditorias/${id}/descartar_items/`, { method: 'POST', body: { item_ids: itemIds, motivo } }),
    reabrirItem: (id, itemId) => apiFetch(`/auditorias/${id}/reabrir_item/`, { method: 'POST', body: { item_id: itemId } }),
    anularHallazgo: (id, hallazgoId) => apiFetch(`/auditorias/${id}/anular_hallazgo/`, { method: 'POST', body: { hallazgo_id: hallazgoId } }),
    terminarEjecucion: (id) => apiFetch(`/auditorias/${id}/terminar_ejecucion/`, { method: 'POST' }),
    validarHallazgos: (id, data) => apiFetch(`/auditorias/${id}/validar_hallazgos/`, { method: 'POST', body: data }),
    cerrar: (id, data) => apiFetch(`/auditorias/${id}/cerrar/`, { method: 'POST', body: data }),
    resumen: () => apiFetch('/auditorias/resumen/'),
    planPdf: (id) => apiBlob(`/auditorias/${id}/plan_pdf/`),
    informePdf: (id) => apiBlob(`/auditorias/${id}/informe_pdf/`),
    actaPdf: (id, tipo) => apiBlob(`/auditorias/${id}/acta_pdf/?tipo=${encodeURIComponent(tipo)}`),
    listaPdf: (id, norma) => apiBlob(`/auditorias/${id}/lista_pdf/?norma=${encodeURIComponent(norma)}`),
  },
  // Formatos PDF del sistema y su vínculo con la lista maestra (caja de control)
  formatosImpresos: {
    listar: () => apiFetch('/formatos-impresos/'),
    vincular: (id, documento) => apiFetch(`/formatos-impresos/${id}/`, { method: 'PATCH', body: { documento: documento || null } }),
  },
  // Candado de aprobación de Auditorías (programa anual e informes de cierre)
  solicitudesAuditoria: {
    listar: (params = '') => apiFetch(`/solicitudes-auditoria/${params}`),
    pendientesCount: () => apiFetch('/solicitudes-auditoria/pendientes_count/'),
    misDevueltasCount: () => apiFetch('/solicitudes-auditoria/mis_devueltas_count/'),
    aprobar: (id, observaciones = '') => apiFetch(`/solicitudes-auditoria/${id}/aprobar/`, { method: 'POST', body: { observaciones } }),
    devolver: (id, observaciones = '') => apiFetch(`/solicitudes-auditoria/${id}/devolver/`, { method: 'POST', body: { observaciones } }),
    rechazar: (id, observaciones = '') => apiFetch(`/solicitudes-auditoria/${id}/rechazar/`, { method: 'POST', body: { observaciones } }),
    reenviar: (id, payload = null) => apiFetch(`/solicitudes-auditoria/${id}/reenviar/`, { method: 'POST', body: payload ? { payload } : {} }),
  },
  // Transversales: buzón de tareas y calendario
  misTareas: () => apiFetch('/mis-tareas/'),
  buscar: (q) => apiFetch(`/buscar/?q=${encodeURIComponent(q)}`),
  calendario: (usuarioId) => apiFetch(`/calendario/${usuarioId ? `?usuario=${usuarioId}` : ''}`),
  // M13 — Equipos
  equipos: {
    listar: (params = '') => apiFetch(`/equipos/${params}`),
    detalle: (id) => apiFetch(`/equipos/${id}/`),
    crear: (data) => apiFetch('/equipos/', { method: 'POST', body: data }),
    actualizar: (id, data) => apiFetch(`/equipos/${id}/`, { method: 'PATCH', body: data }),
    desactivar: (id) => apiFetch(`/equipos/${id}/`, { method: 'DELETE' }),
    registrarCalibracion: (id, formData) => apiUpload(`/equipos/${id}/registrar_calibracion/`, formData),
    marcarInoperativo: (id, motivo) => apiFetch(`/equipos/${id}/marcar_inoperativo/`, { method: 'POST', body: { motivo } }),
    reactivar: (id) => apiFetch(`/equipos/${id}/reactivar/`, { method: 'POST' }),
    darBaja: (id) => apiFetch(`/equipos/${id}/dar_baja/`, { method: 'POST' }),
    agregarRegistro: (id, formData) => apiUpload(`/equipos/${id}/agregar_registro/`, formData),
    subirImagen: (id, formData) => apiUpload(`/equipos/${id}/`, formData, { method: 'PATCH' }),
    fichaPdf: (id) => apiBlob(`/equipos/${id}/ficha_pdf/`),
    bitacoraPdf: (id, tipo, titulo) => apiBlob(`/equipos/${id}/bitacora_pdf/?tipo=${encodeURIComponent(tipo)}&titulo=${encodeURIComponent(titulo || '')}`),
    inventarioPdf: (params = '') => apiBlob(`/equipos/inventario_pdf/${params}`),
    laboratorios: () => apiFetch('/equipos/laboratorios/'),
    programa: (params = '') => apiFetch(`/equipos/programa/${params}`),
    programar: (id, data) => apiFetch(`/equipos/${id}/programar/`, { method: 'POST', body: data }),
    programaPdf: (params = '') => apiBlob(`/equipos/programa_pdf/${params}`),
    eliminarRegistro: (id, registroId) => apiFetch(`/equipos/${id}/eliminar_registro/`, { method: 'POST', body: { registro_id: registroId } }),
    restaurar: (id, entidad, oid) => apiFetch(`/equipos/${id}/restaurar/`, { method: 'POST', body: { entidad, id: oid } }),
    agregarActividad: (id, data) => apiFetch(`/equipos/${id}/agregar_actividad/`, { method: 'POST', body: data }),
    registrarMovimiento: (id, data) => apiFetch(`/equipos/${id}/registrar_movimiento/`, { method: 'POST', body: data }),
    registrarRetorno: (id, data) => apiFetch(`/equipos/${id}/registrar_retorno/`, { method: 'POST', body: data }),
    registrarInforme: (id, formData) => apiUpload(`/equipos/${id}/registrar_informe/`, formData),
    resumen: () => apiFetch('/equipos/resumen/'),
  },
  // M13 — Control de cambios de equipos (solicitudes pendientes de aprobación)
  solicitudesEquipo: {
    listar: (params = '') => apiFetch(`/solicitudes-cambio-equipo/${params}`),
    pendientesCount: () => apiFetch('/solicitudes-cambio-equipo/pendientes_count/'),
    misDevueltasCount: () => apiFetch('/solicitudes-cambio-equipo/mis_devueltas_count/'),
    aprobar: (id, observaciones = '') => apiFetch(`/solicitudes-cambio-equipo/${id}/aprobar/`, { method: 'POST', body: { observaciones } }),
    devolver: (id, observaciones = '') => apiFetch(`/solicitudes-cambio-equipo/${id}/devolver/`, { method: 'POST', body: { observaciones } }),
    rechazar: (id, observaciones = '') => apiFetch(`/solicitudes-cambio-equipo/${id}/rechazar/`, { method: 'POST', body: { observaciones } }),
    reenviar: (id, payload = null) => apiFetch(`/solicitudes-cambio-equipo/${id}/reenviar/`, { method: 'POST', body: payload ? { payload } : {} }),
  },
  cartasTrazabilidad: {
    listar: (params = '') => apiFetch(`/cartas-trazabilidad/${params}`),
    detalle: (id) => apiFetch(`/cartas-trazabilidad/${id}/`),
    crear: (data) => apiFetch('/cartas-trazabilidad/', { method: 'POST', body: data }),
    eliminar: (id) => apiFetch(`/cartas-trazabilidad/${id}/`, { method: 'DELETE' }),
    pdf: (id) => apiBlob(`/cartas-trazabilidad/${id}/carta_pdf/`),
  },
  nodosTrazabilidad: {
    crear: (data) => apiFetch('/nodos-trazabilidad/', { method: 'POST', body: data }),
    editar: (id, data) => apiFetch(`/nodos-trazabilidad/${id}/`, { method: 'PATCH', body: data }),
    eliminar: (id) => apiFetch(`/nodos-trazabilidad/${id}/`, { method: 'DELETE' }),
    rellenarDesdeEquipo: (id) => apiFetch(`/nodos-trazabilidad/${id}/rellenar_desde_equipo/`, { method: 'POST' }),
  },
  // M13 — Intervalo de Calibración (método OIML D10)
  puntosIntervalo: {
    resumen: (params = '') => apiFetch(`/puntos-intervalo/resumen/${params}`),
    crear: (data) => apiFetch('/puntos-intervalo/', { method: 'POST', body: data }),
    editar: (id, data) => apiFetch(`/puntos-intervalo/${id}/`, { method: 'PATCH', body: data }),
    eliminar: (id) => apiFetch(`/puntos-intervalo/${id}/`, { method: 'DELETE' }),
    guardarMatriz: (data) => apiFetch('/puntos-intervalo/guardar_matriz/', { method: 'POST', body: data }),
    pdf: (params = '') => apiBlob(`/puntos-intervalo/intervalo_pdf/${params}`),
  },
  resultadosIntervalo: {
    crear: (data) => apiFetch('/resultados-intervalo/', { method: 'POST', body: data }),
    editar: (id, data) => apiFetch(`/resultados-intervalo/${id}/`, { method: 'PATCH', body: data }),
    eliminar: (id) => apiFetch(`/resultados-intervalo/${id}/`, { method: 'DELETE' }),
  },
  // M12 — Competencia técnica y autorización del personal
  metodosCalibracion: {
    listar: (params = '') => apiFetch(`/metodos-calibracion/${params}`),
    crear: (data) => apiFetch('/metodos-calibracion/', { method: 'POST', body: data }),
    editar: (id, data) => apiFetch(`/metodos-calibracion/${id}/`, { method: 'PATCH', body: data }),
    eliminar: (id) => apiFetch(`/metodos-calibracion/${id}/`, { method: 'DELETE' }),
  },
  controlesValidez: {
    listar: (params = '') => apiFetch(`/controles-validez/${params}`),
    crear: (data) => apiFetch('/controles-validez/', { method: 'POST', body: data }),
    editar: (id, data) => apiFetch(`/controles-validez/${id}/`, { method: 'PATCH', body: data }),
    eliminar: (id) => apiFetch(`/controles-validez/${id}/`, { method: 'DELETE' }),
  },
  autorizaciones: {
    listar: (params = '') => apiFetch(`/autorizaciones/${params}`),
    crear: (data) => apiFetch('/autorizaciones/', { method: 'POST', body: data }),
    editar: (id, data) => apiFetch(`/autorizaciones/${id}/`, { method: 'PATCH', body: data }),
    eliminar: (id) => apiFetch(`/autorizaciones/${id}/`, { method: 'DELETE' }),
    seguimientos: () => apiFetch('/autorizaciones/seguimientos/'),
    pdf: (id) => apiBlob(`/autorizaciones/${id}/autorizacion_pdf/`),
  },
  procesosEntrenamiento: {
    listar: (params = '') => apiFetch(`/procesos-entrenamiento/${params}`),
    crear: (data) => apiFetch('/procesos-entrenamiento/', { method: 'POST', body: data }),
    editar: (id, data) => apiFetch(`/procesos-entrenamiento/${id}/`, { method: 'PATCH', body: data }),
    eliminar: (id) => apiFetch(`/procesos-entrenamiento/${id}/`, { method: 'DELETE' }),
    pdf: (id) => apiBlob(`/procesos-entrenamiento/${id}/entrenamiento_pdf/`),
    subirAdjunto: (formData) => apiUpload('/procesos-entrenamiento/subir_adjunto/', formData),
  },
  evaluacionesSeguimiento: {
    listar: (params = '') => apiFetch(`/evaluaciones-seguimiento/${params}`),
    crear: (data) => apiFetch('/evaluaciones-seguimiento/', { method: 'POST', body: data }),
    editar: (id, data) => apiFetch(`/evaluaciones-seguimiento/${id}/`, { method: 'PATCH', body: data }),
    eliminar: (id) => apiFetch(`/evaluaciones-seguimiento/${id}/`, { method: 'DELETE' }),
    pdf: (id) => apiBlob(`/evaluaciones-seguimiento/${id}/seguimiento_pdf/`),
  },

  solicitudesCompetencia: {
    listar: (params = '') => apiFetch(`/solicitudes-competencia/${params}`),
    pendientesCount: () => apiFetch('/solicitudes-competencia/pendientes_count/'),
    misDevueltasCount: () => apiFetch('/solicitudes-competencia/mis_devueltas_count/'),
    aprobar: (id, observaciones = '') => apiFetch(`/solicitudes-competencia/${id}/aprobar/`, { method: 'POST', body: { observaciones } }),
    devolver: (id, observaciones = '') => apiFetch(`/solicitudes-competencia/${id}/devolver/`, { method: 'POST', body: { observaciones } }),
    rechazar: (id, observaciones = '') => apiFetch(`/solicitudes-competencia/${id}/rechazar/`, { method: 'POST', body: { observaciones } }),
    reenviar: (id, payload = null) => apiFetch(`/solicitudes-competencia/${id}/reenviar/`, { method: 'POST', body: payload ? { payload } : {} }),
  },
  // Configuración del sistema (marca + licenciamiento de módulos)
  // Pública: sin credenciales (un token vencido haría que el servidor la rechace y no cargaría la configuración).
  configPublica: async () => {
    const r = await fetch(`${BASE}/configuracion/publica/`)
    if (!r.ok) throw new Error(`HTTP ${r.status}`)
    return r.json()
  },
  config: {
    obtener: () => apiFetch('/configuracion/sistema/'),
    actualizar: (formData) => apiUpload('/configuracion/sistema/', formData, { method: 'PATCH' }),
    modulos: () => apiFetch('/configuracion/modulos/'),
    toggleModulo: (clave, habilitado) => apiFetch(`/configuracion/modulos/${clave}/toggle/`, { method: 'POST', body: { habilitado } }),
  },
}

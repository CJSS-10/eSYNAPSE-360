/**
 * eSYNAPSE 360 — Cliente API con JWT y refresh automático.
 */
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

async function refrescarToken() {
  const refresh = tokens.refresh
  if (!refresh) return false
  const r = await fetch(`${BASE}/auth/refresh/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh }),
  })
  if (!r.ok) { tokens.clear(); return false }
  const data = await r.json()
  tokens.set(data.access, data.refresh)
  return true
}

export async function apiFetch(path, { method = 'GET', body, _reintento = false } = {}) {
  const headers = { 'Content-Type': 'application/json' }
  if (tokens.access) headers.Authorization = `Bearer ${tokens.access}`

  const r = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })

  if (r.status === 401 && !_reintento && tokens.refresh) {
    const ok = await refrescarToken()
    if (ok) return apiFetch(path, { method, body, _reintento: true })
    window.dispatchEvent(new Event('esynapse:sesion-expirada'))
  }

  if (r.status === 204) return null
  const data = await r.json().catch(() => null)
  if (!r.ok) {
    const error = new Error(
      data?.detail
      || (data && typeof data === 'object' ? JSON.stringify(data) : null)
      || `Error del servidor (HTTP ${r.status}). Verifica que el backend esté actualizado y migrado.`,
    )
    error.status = r.status
    error.data = data
    throw error
  }
  return data
}

export async function apiUpload(path, formData, { method = 'POST', _reintento = false } = {}) {
  const headers = {}
  if (tokens.access) headers.Authorization = `Bearer ${tokens.access}`
  const r = await fetch(`${BASE}${path}`, { method, headers, body: formData })
  if (r.status === 401 && !_reintento && tokens.refresh) {
    const ok = await refrescarToken()
    if (ok) return apiUpload(path, formData, { method, _reintento: true })
    window.dispatchEvent(new Event('esynapse:sesion-expirada'))
  }
  if (r.status === 204) return null
  const data = await r.json().catch(() => null)
  if (!r.ok) {
    const error = new Error(
      data?.detail
      || (data && typeof data === 'object' ? JSON.stringify(data) : null)
      || `Error del servidor (HTTP ${r.status}). Verifica que el backend esté actualizado y migrado.`,
    )
    error.status = r.status
    error.data = data
    throw error
  }
  return data
}

export async function apiBlob(path, { method = 'GET', _reintento = false } = {}) {
  const headers = {}
  if (tokens.access) headers.Authorization = `Bearer ${tokens.access}`
  const r = await fetch(`${BASE}${path}`, { method, headers })
  if (r.status === 401 && !_reintento && tokens.refresh) {
    const ok = await refrescarToken()
    if (ok) return apiBlob(path, { method, _reintento: true })
    window.dispatchEvent(new Event('esynapse:sesion-expirada'))
  }
  if (!r.ok) throw new Error(`No se pudo generar el documento (HTTP ${r.status}).`)
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
    return data
  },
  logout() { tokens.clear() },
  haySesion() { return Boolean(tokens.access) },
  me: () => apiFetch('/auth/me/'),
  // Usuarios
  usuarios: {
    listar: (params = '') => apiFetch(`/usuarios/${params}`),
    crear: (data) => apiFetch('/usuarios/', { method: 'POST', body: data }),
    editar: (id, data) => apiFetch(`/usuarios/${id}/`, { method: 'PATCH', body: data }),
    desactivar: (id) => apiFetch(`/usuarios/${id}/`, { method: 'DELETE' }),
    activar: (id) => apiFetch(`/usuarios/${id}/activar/`, { method: 'POST' }),
    asignarRoles: (id, roles) => apiFetch(`/usuarios/${id}/asignar_roles/`, { method: 'POST', body: { roles } }),
  },
  // Roles
  roles: {
    listar: () => apiFetch('/roles/'),
    crear: (data) => apiFetch('/roles/', { method: 'POST', body: data }),
    editar: (id, data) => apiFetch(`/roles/${id}/`, { method: 'PATCH', body: data }),
    desactivar: (id) => apiFetch(`/roles/${id}/`, { method: 'DELETE' }),
  },
  catalogo: () => apiFetch('/configuracion/catalogo/'),
  // M9 — Solicitudes de Acción Correctiva (SIG-PRO-11)
  sac: {
    listar: (params = '') => apiFetch(`/sac/${params}`),
    detalle: (id) => apiFetch(`/sac/${id}/`),
    crear: (data) => apiFetch('/sac/', { method: 'POST', body: data }),
    desactivar: (id) => apiFetch(`/sac/${id}/`, { method: 'DELETE' }),
    evaluar: (id, data) => apiFetch(`/sac/${id}/evaluar/`, { method: 'POST', body: data }),
    registrarAnalisis: (id, data) => apiFetch(`/sac/${id}/registrar_analisis/`, { method: 'POST', body: data }),
    agregarAccion: (id, data) => apiFetch(`/sac/${id}/agregar_accion/`, { method: 'POST', body: data }),
    aprobarPlan: (id, verificador) => apiFetch(`/sac/${id}/aprobar_plan/`, { method: 'POST', body: { verificador } }),
    completarAccion: (id, formData) => apiUpload(`/sac/${id}/completar_accion/`, formData),
    verificarEficacia: (id, eficaz, evaluacion) => apiFetch(`/sac/${id}/verificar_eficacia/`, { method: 'POST', body: { eficaz, evaluacion } }),
    resumen: () => apiFetch('/sac/resumen/'),
  },
  // M8 — Hallazgos
  hallazgos: {
    listar: (params = '') => apiFetch(`/hallazgos/${params}`),
    detalle: (id) => apiFetch(`/hallazgos/${id}/`),
    crear: (formData) => apiUpload('/hallazgos/', formData),
    editar: (id, data) => apiFetch(`/hallazgos/${id}/`, { method: 'PATCH', body: data }),
    desactivar: (id) => apiFetch(`/hallazgos/${id}/`, { method: 'DELETE' }),
    iniciarAnalisis: (id, analisis) => apiFetch(`/hallazgos/${id}/iniciar_analisis/`, { method: 'POST', body: { analisis } }),
    registrarTratamiento: (id, data) => apiFetch(`/hallazgos/${id}/registrar_tratamiento/`, { method: 'POST', body: data }),
    cerrar: (id, comentarios) => apiFetch(`/hallazgos/${id}/cerrar/`, { method: 'POST', body: { comentarios } }),
    reabrir: (id, justificacion) => apiFetch(`/hallazgos/${id}/reabrir/`, { method: 'POST', body: { justificacion } }),
    generarSac: (id) => apiFetch(`/hallazgos/${id}/generar_sac/`, { method: 'POST' }),
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
  // M10 — Auditorías Internas (SIG-PRO-16)
  requisitosNorma: (norma) => apiFetch(`/requisitos-norma/?norma=${norma}`),
  programasAuditoria: {
    listar: (params = '') => apiFetch(`/programas-auditoria/${params}`),
    detalle: (id) => apiFetch(`/programas-auditoria/${id}/`),
    crear: (data) => apiFetch('/programas-auditoria/', { method: 'POST', body: data }),
    aprobar: (id) => apiFetch(`/programas-auditoria/${id}/aprobar/`, { method: 'POST' }),
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
    registrarActa: (id, data) => apiFetch(`/auditorias/${id}/registrar_acta/`, { method: 'POST', body: data }),
    generarLista: (id, norma) => apiFetch(`/auditorias/${id}/generar_lista/`, { method: 'POST', body: { norma } }),
    evaluarItem: (id, data) => apiFetch(`/auditorias/${id}/evaluar_item/`, { method: 'POST', body: data }),
    registrarHallazgo: (id, data) => apiFetch(`/auditorias/${id}/registrar_hallazgo/`, { method: 'POST', body: data }),
    generarInforme: (id, data) => apiFetch(`/auditorias/${id}/generar_informe/`, { method: 'POST', body: data }),
    cerrar: (id, data) => apiFetch(`/auditorias/${id}/cerrar/`, { method: 'POST', body: data }),
    resumen: () => apiFetch('/auditorias/resumen/'),
  },
  // Transversales: buzón de tareas y calendario
  misTareas: () => apiFetch('/mis-tareas/'),
  calendario: (usuarioId) => apiFetch(`/calendario/${usuarioId ? `?usuario=${usuarioId}` : ''}`),
  // M13 — Equipos (MET-PRO-04)
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
    eliminarRegistro: (id, registroId) => apiFetch(`/equipos/${id}/eliminar_registro/`, { method: 'POST', body: { registro_id: registroId } }),
    agregarActividad: (id, data) => apiFetch(`/equipos/${id}/agregar_actividad/`, { method: 'POST', body: data }),
    registrarMovimiento: (id, data) => apiFetch(`/equipos/${id}/registrar_movimiento/`, { method: 'POST', body: data }),
    registrarRetorno: (id, data) => apiFetch(`/equipos/${id}/registrar_retorno/`, { method: 'POST', body: data }),
    registrarInforme: (id, formData) => apiUpload(`/equipos/${id}/registrar_informe/`, formData),
    resumen: () => apiFetch('/equipos/resumen/'),
  },
  cartasTrazabilidad: {
    listar: (params = '') => apiFetch(`/cartas-trazabilidad/${params}`),
    crear: (data) => apiFetch('/cartas-trazabilidad/', { method: 'POST', body: data }),
  },
  // Configuración del sistema (marca + licenciamiento de módulos)
  configPublica: () => apiFetch('/configuracion/publica/'),
  config: {
    obtener: () => apiFetch('/configuracion/sistema/'),
    actualizar: (formData) => apiUpload('/configuracion/sistema/', formData, { method: 'PATCH' }),
    modulos: () => apiFetch('/configuracion/modulos/'),
    toggleModulo: (clave, habilitado) => apiFetch(`/configuracion/modulos/${clave}/toggle/`, { method: 'POST', body: { habilitado } }),
  },
}

/**
 * Avisos de confirmación (esquina inferior derecha). `avisar(texto, tipo)` se puede llamar desde
 * cualquier parte; el componente Avisos (en el Layout) los muestra. Además, cada escritura exitosa
 * contra la API avisa sola con un texto según la acción (ver `avisarEscritura` en api.js), para que
 * todos los módulos confirmen igual sin tocar cada pantalla.
 */
export function avisar(texto, tipo = 'exito') {
  if (typeof window === 'undefined' || !texto) return
  window.dispatchEvent(new CustomEvent('esynapse:aviso', { detail: { texto, tipo } }))
}

// Escrituras que no son un guardado del usuario (sesión, archivos, consultas): no avisan
const SIN_AVISO = [/^\/auth\//, /^\/buscar\//, /pdf/i, /previsualizar/, /^\/configuracion\/publica/]

// Acción (último tramo de la ruta) → texto del aviso
const POR_ACCION = [
  [/^aprobar/, 'Aprobado'],
  [/^devolver/, 'Devuelto para corrección'],
  [/^rechazar/, 'Rechazado'],
  [/^firmar/, 'Firma registrada'],
  [/^pasar_a_cierre$/, 'Enviado a cierre'],
  [/^cerrar/, 'Cerrado'],
  [/^(reenviar|enviar|enviar_revision|comunicar)$/, 'Enviado'],
  [/^(reactivar|restaurar|restaurar_integrante|desarchivar)$/, 'Restaurado'],
  [/^reabrir/, 'Reabierto'],
  [/^(dar_baja|dar_de_baja|baja|anular\w*|retirar|archivar|descartar\w*|eliminar_registro)$/, 'Dado de baja'],
  [/^quitar/, 'Retirado'],
  [/^(adjuntar|subir_adjunto|reemplazar_archivo)$/, 'Archivo adjuntado'],
  [/^(registrar\w*|agregar\w*|generar\w*|nueva_version|corte|programar|planificar|iniciar)$/, 'Registrado'],
  [/^(verificar\w*|evaluar\w*|validar\w*|decidir|revisar\w*|reclasificar)$/, 'Evaluación registrada'],
]

export function textoEscritura(metodo, ruta) {
  const limpia = (ruta || '').split('?')[0]
  if (SIN_AVISO.some((r) => r.test(limpia))) return null
  const tramos = limpia.split('/').filter(Boolean)
  const ultimo = tramos[tramos.length - 1] || ''
  if (metodo === 'DELETE') return 'Dado de baja'
  if (metodo === 'PATCH' || metodo === 'PUT') return 'Cambios guardados'
  if (metodo === 'POST') {
    const regla = POR_ACCION.find(([r]) => r.test(ultimo))
    if (regla) return regla[1]
    // POST a la colección (/quejas/) = registro nuevo; otras acciones, confirmación genérica
    return /^\d+$/.test(ultimo) || tramos.length <= 1 ? 'Registrado' : 'Guardado'
  }
  return null
}

export function avisarEscritura(metodo, ruta) {
  const texto = textoEscritura(metodo, ruta)
  if (texto) avisar(texto)
}

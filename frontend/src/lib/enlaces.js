import { useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useIsPresent } from 'framer-motion'

/**
 * Enlace directo a un registro: `/modulo?abrir=<id>` abre su ficha al entrar a la pantalla.
 * Lo usan la búsqueda global (Ctrl + K), Mis tareas, la campana y el Tablero. Tras abrirla se
 * quita el parámetro, para que recargar o volver no reabra la ficha.
 */
export function useAbrirDesdeEnlace(abrir) {
  const [params, setParams] = useSearchParams()
  const id = params.get('abrir')
  // Durante la transición de página, la pantalla que sale también dibuja la ruta nueva: solo la
  // instancia que queda (presente) abre la ficha; si no, se abría en la que desaparece.
  const presente = useIsPresent()
  useEffect(() => {
    if (!id || !presente) return
    const n = Number(id)
    if (Number.isFinite(n) && n > 0) Promise.resolve(abrir(n)).catch(() => {})
    const p = new URLSearchParams(params)
    p.delete('abrir')
    setParams(p, { replace: true })
  }, [id, presente])  // eslint-disable-line react-hooks/exhaustive-deps
}

/** Ruta de la pantalla de un registro, con su enlace directo si se conoce el id. */
export const rutaRegistro = (ruta, id) => (id ? `${ruta}?abrir=${id}` : ruta)

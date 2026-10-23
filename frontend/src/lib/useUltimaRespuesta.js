import { useCallback, useRef } from 'react'

/**
 * Evita que una respuesta vieja pise a una nueva en las listas con búsqueda:
 * al escribir rápido salen varias consultas y pueden llegar en desorden (la de
 * «2» después de la de «29783»). Solo se entrega la respuesta de la última
 * consulta; las anteriores quedan sin resolver y se descartan.
 *
 *   const ultima = useUltimaRespuesta()
 *   const datos = await ultima(api.algo.listar(params))
 */
export function useUltimaRespuesta() {
  const contador = useRef(0)
  return useCallback(async (promesa) => {
    const id = ++contador.current
    const resultado = await promesa
    if (id !== contador.current) return new Promise(() => {})
    return resultado
  }, [])
}

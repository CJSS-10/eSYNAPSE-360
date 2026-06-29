import { createContext, useCallback, useContext, useRef, useState } from 'react'
import { AlertTriangle } from 'lucide-react'
import Modal from '../components/Modal.jsx'

const ConfirmContext = createContext(() => Promise.resolve(false))

// Confirmación global con modal con estilo (reemplaza window.confirm).
// Uso:  const confirmar = useConfirm()
//       if (await confirmar({ mensaje: '¿Seguro?' })) { ... }
export function ConfirmProvider({ children }) {
  const [estado, setEstado] = useState(null) // { titulo, mensaje, textoConfirmar, textoCancelar, peligro }
  const resolver = useRef(null)

  const confirmar = useCallback((opts = {}) => {
    return new Promise((resolve) => {
      resolver.current = resolve
      setEstado({
        titulo: opts.titulo || 'Confirmar',
        mensaje: opts.mensaje || '¿Deseas continuar?',
        textoConfirmar: opts.textoConfirmar || 'Confirmar',
        textoCancelar: opts.textoCancelar || 'Cancelar',
        peligro: opts.peligro ?? false,
      })
    })
  }, [])

  const cerrar = (valor) => {
    if (resolver.current) { resolver.current(valor); resolver.current = null }
    setEstado(null)
  }

  return (
    <ConfirmContext.Provider value={confirmar}>
      {children}
      <Modal abierto={!!estado} titulo={estado?.titulo} onCerrar={() => cerrar(false)} ancho="max-w-md">
        {estado && (
          <div>
            <div className="flex items-start gap-3">
              {estado.peligro && (
                <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-red-500/10 text-red-500">
                  <AlertTriangle className="h-5 w-5" />
                </span>
              )}
              <p className="text-sm text-slate-600 dark:text-slate-300">{estado.mensaje}</p>
            </div>
            <div className="mt-6 flex justify-end gap-2">
              <button type="button" onClick={() => cerrar(false)} className="btn-secondary">{estado.textoCancelar}</button>
              <button type="button" autoFocus onClick={() => cerrar(true)}
                className={estado.peligro ? 'btn-danger' : 'btn-primary'}>{estado.textoConfirmar}</button>
            </div>
          </div>
        )}
      </Modal>
    </ConfirmContext.Provider>
  )
}

export const useConfirm = () => useContext(ConfirmContext)

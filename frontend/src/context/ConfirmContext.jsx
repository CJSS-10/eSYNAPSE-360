import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'
import { AlertTriangle } from 'lucide-react'
import Modal from '../components/Modal.jsx'

const ConfirmContext = createContext(() => Promise.resolve(false))

// Confirmación global con modal con estilo (reemplaza window.confirm y window.prompt).
//
// Sí / no:
//   const confirmar = useConfirm()
//   if (await confirmar({ mensaje: '¿Seguro?' })) { ... }
//
// Con campo de texto (reemplaza window.prompt): resuelve con el texto, o null si cancela.
//   const motivo = await confirmar({
//     titulo: 'Modificar programa', mensaje: '…',
//     entrada: { etiqueta: 'Motivo', placeholder: '…', valorInicial: '', obligatorio: true, multilinea: true },
//   })
//   if (motivo === null) return
// Para pedir la contraseña al firmar: entrada: { etiqueta: 'Contraseña', tipo: 'password', obligatorio: true }
export function ConfirmProvider({ children }) {
  const [estado, setEstado] = useState(null)
  const [texto, setTexto] = useState('')
  const resolver = useRef(null)

  const confirmar = useCallback((opts = {}) => {
    return new Promise((resolve) => {
      // Si quedaba otra confirmación abierta, se resuelve como cancelada (no queda esperando para siempre).
      if (resolver.current) resolver.current(opts.entrada ? null : false)
      resolver.current = resolve
      setTexto(opts.entrada?.valorInicial || '')
      setEstado({
        titulo: opts.titulo || 'Confirmar',
        mensaje: opts.mensaje || '¿Deseas continuar?',
        textoConfirmar: opts.textoConfirmar || 'Confirmar',
        textoCancelar: opts.textoCancelar || 'Cancelar',
        peligro: opts.peligro ?? false,
        entrada: opts.entrada || null,
      })
    })
  }, [])

  const cerrar = (valor) => {
    if (resolver.current) { resolver.current(valor); resolver.current = null }
    setEstado(null)
  }
  const conEntrada = Boolean(estado?.entrada)
  const faltaTexto = conEntrada && estado.entrada.obligatorio && !texto.trim()
  const aceptar = () => { if (faltaTexto) return; cerrar(conEntrada ? texto.trim() : true) }
  const cancelar = () => cerrar(conEntrada ? null : false)

  // Enter confirma (en campo de una línea); Escape cancela.
  useEffect(() => {
    if (!estado) return undefined
    const onKey = (e) => {
      if (e.key === 'Escape') cancelar()
      // Enter sobre un botón (p. ej. «Cancelar» o la X con el foco) ejecuta ese botón, no la confirmación.
      if (e.target instanceof HTMLButtonElement) return
      if (e.key === 'Enter' && !(conEntrada && estado.entrada.multilinea)) { e.preventDefault(); aceptar() }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  })  // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <ConfirmContext.Provider value={confirmar}>
      {children}
      <Modal abierto={!!estado} titulo={estado?.titulo} onCerrar={cancelar} ancho="max-w-md">
        {estado && (
          <div>
            <div className="flex items-start gap-3">
              {estado.peligro && (
                <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-red-500/10 text-red-500">
                  <AlertTriangle className="h-5 w-5" />
                </span>
              )}
              <p className="whitespace-pre-line text-sm text-slate-600 dark:text-slate-300">{estado.mensaje}</p>
            </div>
            {conEntrada && (
              <div className="mt-4">
                {estado.entrada.etiqueta && (
                  <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">
                    {estado.entrada.etiqueta}{estado.entrada.obligatorio && <span className="text-red-500"> *</span>}
                  </label>
                )}
                {estado.entrada.multilinea ? (
                  <textarea autoFocus rows={3} className="input-esynapse" placeholder={estado.entrada.placeholder || ''}
                    value={texto} onChange={(e) => setTexto(e.target.value)} />
                ) : (
                  <input autoFocus className="input-esynapse" placeholder={estado.entrada.placeholder || ''}
                    type={estado.entrada.tipo || 'text'} autoComplete={estado.entrada.tipo === 'password' ? 'current-password' : 'off'}
                    value={texto} onChange={(e) => setTexto(e.target.value)} />
                )}
              </div>
            )}
            <div className="mt-6 flex justify-end gap-2">
              <button type="button" onClick={cancelar} className="btn-secondary">{estado.textoCancelar}</button>
              <button type="button" autoFocus={!conEntrada} onClick={aceptar} disabled={faltaTexto}
                className={`${estado.peligro ? 'btn-danger' : 'btn-primary'} disabled:opacity-40`}>{estado.textoConfirmar}</button>
            </div>
          </div>
        )}
      </Modal>
    </ConfirmContext.Provider>
  )
}

export const useConfirm = () => useContext(ConfirmContext)

import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { Maximize2, X } from 'lucide-react'

/**
 * Caja de texto con botón para abrirla en una ventana grande, para redactar o
 * revisar textos largos sin perder espacio en el formulario. El texto se edita
 * en la ventana y se aplica al cerrar con «Listo» (Cancelar lo descarta).
 */
export default function CampoAmpliable({
  value, onChange, placeholder = '', titulo, multilinea = false, rows = 2,
  className = '', disabled = false, required = false,
}) {
  const [abierto, setAbierto] = useState(false)
  const [borrador, setBorrador] = useState('')
  const area = useRef(null)

  useEffect(() => {
    if (abierto && area.current) {
      area.current.focus()
      area.current.setSelectionRange(area.current.value.length, area.current.value.length)
    }
  }, [abierto])

  const abrir = () => { setBorrador(value || ''); setAbierto(true) }
  const listo = () => { onChange(borrador); setAbierto(false) }
  const comun = {
    className: `input-esynapse w-full pr-8 ${className}`, placeholder, disabled, required,
    value: value || '', onChange: (e) => onChange(e.target.value),
  }

  return (
    <div className="relative">
      {multilinea ? <textarea rows={rows} {...comun} /> : <input {...comun} />}
      <button type="button" onClick={abrir} title="Abrir en una ventana más grande"
        className="absolute right-1.5 top-1.5 rounded p-1 text-slate-400 hover:bg-slate-200 hover:text-slate-600 dark:hover:bg-slate-700 dark:hover:text-slate-200">
        <Maximize2 className="h-3.5 w-3.5" />
      </button>
      {abierto && createPortal(
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/50 p-4">
          <div className="card-esynapse w-full max-w-3xl p-5" onClick={(e) => e.stopPropagation()}>
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-base font-semibold">{titulo || placeholder || 'Texto'}</h2>
              <button type="button" onClick={() => setAbierto(false)} className="rounded p-1 text-slate-500 hover:bg-slate-200 dark:hover:bg-slate-800">
                <X className="h-4 w-4" />
              </button>
            </div>
            <textarea ref={area} rows={14} className="input-esynapse w-full text-sm leading-relaxed" placeholder={placeholder}
              disabled={disabled} value={borrador} onChange={(e) => setBorrador(e.target.value)} />
            <div className="mt-3 flex justify-end gap-2">
              <button type="button" onClick={() => setAbierto(false)} className="btn-secondary">Cancelar</button>
              {!disabled && <button type="button" onClick={listo} className="btn-primary">Listo</button>}
            </div>
          </div>
        </div>,
        document.body,
      )}
    </div>
  )
}

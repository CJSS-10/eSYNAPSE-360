import { useEffect, useState } from 'react'
import { Check, Pencil, Plus, Trash2, X } from 'lucide-react'
import { useConfirm } from '../../context/ConfirmContext.jsx'

// Gestión de un catálogo del módulo Equipos (magnitudes o clasificaciones):
// agregar, renombrar y desactivar. Magnitud lleva además un prefijo de código.
export default function GestionCatalogoEquipo({ fuente, titulo, singular, conPrefijo = false, nota, onCambio }) {
  const confirmar = useConfirm()
  const [items, setItems] = useState([])
  const [editId, setEditId] = useState(null)
  const [editNombre, setEditNombre] = useState('')
  const [editPrefijo, setEditPrefijo] = useState('')
  const [nuevoNombre, setNuevoNombre] = useState('')
  const [error, setError] = useState('')

  const cargar = () => fuente.listar().then((d) => setItems(d.results ?? d)).catch((e) => setError(e.message))
  useEffect(() => { cargar() }, [])

  const refrescar = async () => { await cargar(); if (onCambio) onCambio() }

  const agregar = async () => {
    const n = nuevoNombre.trim()
    if (!n) return
    setError('')
    try { await fuente.crear(n); setNuevoNombre(''); await refrescar() }
    catch (e) { setError(e.message || 'No se pudo crear') }
  }

  const guardar = async (it) => {
    const n = editNombre.trim()
    if (!n) return
    setError('')
    const data = { nombre: n }
    if (conPrefijo) data.prefijo = editPrefijo.trim().toUpperCase()
    try { await fuente.editar(it.id, data); setEditId(null); await refrescar() }
    catch (e) { setError(e.message || 'No se pudo guardar') }
  }

  const eliminar = async (it) => {
    const ok = await confirmar({
      titulo: `Quitar ${singular}`,
      mensaje: `¿Quitar "${it.nombre}" de la lista? Los equipos que ya la usan no se ven afectados.`,
      textoConfirmar: 'Quitar',
      peligro: true,
    })
    if (!ok) return
    setError('')
    try { await fuente.eliminar(it.id); await refrescar() }
    catch (e) { setError(e.message || 'No se pudo eliminar') }
  }

  return (
    <div>
      <h3 className="mb-1 text-sm font-semibold text-slate-700 dark:text-slate-200">{titulo}</h3>
      {nota && <p className="mb-2 text-[11px] text-amber-600 dark:text-amber-400">{nota}</p>}
      <ul className="space-y-1.5">
        {items.map((it) => (
          <li key={it.id} className="flex items-center gap-1.5">
            {editId === it.id ? (
              <>
                <input autoFocus className="input-esynapse" value={editNombre}
                  onChange={(e) => setEditNombre(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); guardar(it) } if (e.key === 'Escape') setEditId(null) }} />
                {conPrefijo && (
                  <input className="input-esynapse w-16" value={editPrefijo} title="Prefijo de código"
                    placeholder="Pref." onChange={(e) => setEditPrefijo(e.target.value)} />
                )}
                <button type="button" onClick={() => guardar(it)} title="Guardar" className="btn-primary !px-2.5"><Check className="h-4 w-4" /></button>
                <button type="button" onClick={() => setEditId(null)} title="Cancelar" className="btn-secondary !px-2.5"><X className="h-4 w-4" /></button>
              </>
            ) : (
              <>
                <span className="flex flex-1 items-center gap-2 truncate rounded-lg border border-slate-200 px-3 py-2 text-sm dark:border-slate-700">
                  {it.nombre}
                  {conPrefijo && <span className="text-xs text-slate-400">({it.prefijo})</span>}
                  {it.es_patron && <span className="rounded bg-violet-500/15 px-1.5 py-0.5 text-[10px] text-violet-500">patrón</span>}
                </span>
                <button type="button" onClick={() => { setEditId(it.id); setEditNombre(it.nombre); setEditPrefijo(it.prefijo || '') }}
                  title="Renombrar" className="rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-esynapse-500 dark:hover:bg-slate-800"><Pencil className="h-4 w-4" /></button>
                <button type="button" onClick={() => eliminar(it)} title="Quitar de la lista"
                  className="rounded-lg p-2 text-slate-400 hover:bg-red-500/10 hover:text-red-500"><Trash2 className="h-4 w-4" /></button>
              </>
            )}
          </li>
        ))}
        {items.length === 0 && <li className="text-xs text-slate-400">Aún no hay opciones.</li>}
      </ul>
      <div className="mt-2 flex gap-1.5">
        <input className="input-esynapse" placeholder={`Agregar ${singular}…`} value={nuevoNombre}
          onChange={(e) => setNuevoNombre(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); agregar() } }} />
        <button type="button" onClick={agregar} className="btn-secondary !px-2.5" title="Agregar"><Plus className="h-4 w-4" /></button>
      </div>
      {error && <p className="mt-1 text-[11px] text-red-500">{error}</p>}
    </div>
  )
}

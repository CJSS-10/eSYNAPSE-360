import { useEffect, useState } from 'react'
import { Check, Pencil, Plus, Trash2, X } from 'lucide-react'
import { api } from '../../lib/api.js'
import { useConfirm } from '../../context/ConfirmContext.jsx'

// Gestión de un catálogo (áreas o laboratorios): listar, renombrar,
// desactivar (soft-delete) y agregar nuevas opciones.
export default function GestionCatalogo({ tipo, titulo, singular }) {
  const confirmar = useConfirm()
  const [opciones, setOpciones] = useState([])
  const [editId, setEditId] = useState(null)
  const [editVal, setEditVal] = useState('')
  const [nuevo, setNuevo] = useState('')
  const [error, setError] = useState('')

  const cargar = () =>
    api.opcionesCatalogo.listar(tipo).then((d) => setOpciones(d.results ?? d)).catch((e) => setError(e.message))
  useEffect(() => { cargar() }, [tipo])

  const agregar = async () => {
    const nombre = nuevo.trim()
    if (!nombre) return
    setError('')
    try { await api.opcionesCatalogo.crear(tipo, nombre); setNuevo(''); await cargar() }
    catch (e) { setError(e.message || 'No se pudo crear') }
  }

  const guardar = async (id) => {
    const nombre = editVal.trim()
    if (!nombre) return
    setError('')
    try { await api.opcionesCatalogo.editar(id, { nombre }); setEditId(null); await cargar() }
    catch (e) { setError(e.message || 'No se pudo guardar') }
  }

  const eliminar = async (o) => {
    const ok = await confirmar({
      titulo: `Quitar ${singular || 'opción'}`,
      mensaje: `¿Quitar "${o.nombre}" de la lista? Los usuarios que ya la tengan asignada no se ven afectados.`,
      textoConfirmar: 'Quitar',
      peligro: true,
    })
    if (!ok) return
    setError('')
    try { await api.opcionesCatalogo.eliminar(o.id); await cargar() }
    catch (e) { setError(e.message || 'No se pudo eliminar') }
  }

  return (
    <div>
      <h3 className="mb-2 text-sm font-semibold text-slate-700 dark:text-slate-200">{titulo}</h3>
      <ul className="space-y-1.5">
        {opciones.map((o) => (
          <li key={o.id} className="flex items-center gap-1.5">
            {editId === o.id ? (
              <>
                <input
                  autoFocus
                  className="input-esynapse"
                  value={editVal}
                  onChange={(e) => setEditVal(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); guardar(o.id) } if (e.key === 'Escape') setEditId(null) }}
                />
                <button type="button" onClick={() => guardar(o.id)} title="Guardar" className="btn-primary !px-2.5"><Check className="h-4 w-4" /></button>
                <button type="button" onClick={() => setEditId(null)} title="Cancelar" className="btn-secondary !px-2.5"><X className="h-4 w-4" /></button>
              </>
            ) : (
              <>
                <span className="flex-1 truncate rounded-lg border border-slate-200 px-3 py-2 text-sm dark:border-slate-700">{o.nombre}</span>
                <button type="button" onClick={() => { setEditId(o.id); setEditVal(o.nombre) }} title="Renombrar"
                  className="rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-esynapse-500 dark:hover:bg-slate-800"><Pencil className="h-4 w-4" /></button>
                <button type="button" onClick={() => eliminar(o)} title="Quitar de la lista"
                  className="rounded-lg p-2 text-slate-400 hover:bg-red-500/10 hover:text-red-500"><Trash2 className="h-4 w-4" /></button>
              </>
            )}
          </li>
        ))}
        {opciones.length === 0 && <li className="text-xs text-slate-400">Aún no hay opciones.</li>}
      </ul>
      <div className="mt-2 flex gap-1.5">
        <input
          className="input-esynapse"
          placeholder={`Agregar ${singular || titulo.toLowerCase()}…`}
          value={nuevo}
          onChange={(e) => setNuevo(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); agregar() } }}
        />
        <button type="button" onClick={agregar} className="btn-secondary !px-2.5" title="Agregar"><Plus className="h-4 w-4" /></button>
      </div>
      {error && <p className="mt-1 text-[11px] text-red-500">{error}</p>}
    </div>
  )
}

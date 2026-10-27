import { useCallback, useEffect, useState } from 'react'
import Modal from './Modal.jsx'
import CampoAmpliable from './CampoAmpliable.jsx'
import { hoy } from '../lib/fecha.js'

const inp = 'input-esynapse'
const lbl = 'mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300'

/* Credencial de cada titular según la regla de firma: contraseña de su usuario o PIN personal. */
export function CredencialTitular({ forma, valor, onChange }) {
  const v = valor || {}
  const pin = (k, ph) => <input type="password" inputMode="numeric" autoComplete="off" placeholder={ph} className={`${inp} !py-1 text-xs`} value={v[k] || ''} onChange={(e) => onChange({ ...v, [k]: e.target.value.replace(/\D/g, '').slice(0, 6) })} />
  if (forma === 'usuario') return <input type="password" autoComplete="off" placeholder="Contraseña de su usuario" className={`${inp} !py-1 text-xs`} value={v.clave || ''} onChange={(e) => onChange({ ...v, clave: e.target.value })} />
  if (forma === 'activo') return pin('pin', 'PIN')
  if (forma === 'bloqueado') return <span className="text-[11px] text-red-600">PIN bloqueado: restablézcalo o use el acta en papel</span>
  return <div className="flex gap-1">{pin('pin_nuevo', 'Nuevo PIN')}{pin('pin_confirmacion', 'Confirme')}</div>
}

/**
 * Aprobación por el Comité de SST: firman TODOS los titulares (contraseña de su usuario o PIN), o se adjunta el acta
 * firmada por todos y quien registra firma con su contraseña.
 * Props: titulo, cargar() → {comite, titulares}, enviar(json), enviarPapel(formData), onCerrar, alAprobar(respuesta).
 */
export default function FirmaComite({ titulo, cargar, enviar, enviarPapel, onCerrar, alAprobar }) {
  const [d, setD] = useState(null)
  const [modo, setModo] = useState('pantalla')
  const [f, setF] = useState({ fecha: hoy(), observaciones: '', archivo: null, password: '' })
  const [firmas, setFirmas] = useState({})
  const [err, setErr] = useState('')
  const [enviando, setEnviando] = useState(false)
  const leer = useCallback(() => cargar().then((x) => { setD(x); setFirmas((prev) => Object.fromEntries((x.titulares || []).map((t) => [t.id, prev[t.id] || {}]))) }).catch((e) => setErr(e.message)), [cargar])
  useEffect(() => { leer() }, [leer])
  const registrar = async () => {
    setErr(''); setEnviando(true)
    try {
      let r
      if (modo === 'papel') {
        if (!f.archivo) { setErr('Adjunte el acta firmada por todos los titulares.'); return }
        const fd = new FormData(); fd.append('fecha', f.fecha); fd.append('observaciones', f.observaciones); fd.append('firmantes', JSON.stringify(d.titulares.map((t) => t.id))); fd.append('archivo', f.archivo); fd.append('password', f.password)
        r = await enviarPapel(fd)
      } else {
        const lista = d.titulares.map((t) => { const c = firmas[t.id] || {}; return { miembro: t.id, clave: c.clave, pin: c.pin, pin_nuevo: c.pin_nuevo, pin_confirmacion: c.pin_confirmacion } })
        r = await enviar({ fecha: f.fecha, observaciones: f.observaciones, firmas: lista })
      }
      alAprobar(r)
    } catch (e) { setErr(e.message); leer() } finally { setEnviando(false) }
  }
  return (
    <Modal abierto titulo={titulo} onCerrar={onCerrar} ancho="max-w-4xl">
      <div className="space-y-3 text-sm">
        <p className="text-xs text-slate-500">Lo aprueban <strong>todos los titulares</strong> del Comité de SST{d?.comite ? ` (${d.comite})` : ''}, cada uno con la contraseña de su usuario o, si no tiene usuario, con su PIN; o se adjunta el acta firmada por todos.</p>
        {d && !(d.titulares || []).length && <p className="rounded bg-red-500/10 px-3 py-2 text-xs text-red-600">El comité vigente no tiene titulares registrados (SST › Participación › Comité de SST).</p>}
        <div className="grid gap-3 md:grid-cols-3"><div><label className={lbl}>Fecha de aprobación</label><input type="date" className={inp} value={f.fecha} onChange={(e) => setF({ ...f, fecha: e.target.value })} /></div></div>
        <div className="flex gap-4 text-xs"><label className="flex items-center gap-1"><input type="radio" checked={modo === 'pantalla'} onChange={() => setModo('pantalla')} /> Firman en pantalla</label><label className="flex items-center gap-1"><input type="radio" checked={modo === 'papel'} onChange={() => setModo('papel')} /> Acta firmada en papel</label></div>
        <table className="w-full text-xs"><tbody>{(d?.titulares || []).map((t) => (
          <tr key={t.id} className="border-t border-slate-100 dark:border-slate-800/60"><td className="py-1">{t.nombre}<span className="block text-[10px] text-slate-500">{t.cargo}</span></td>{modo === 'pantalla' && <td className="w-72"><CredencialTitular forma={t.firma} valor={firmas[t.id]} onChange={(v) => setFirmas({ ...firmas, [t.id]: v })} /></td>}</tr>
        ))}</tbody></table>
        {modo === 'papel' && <div className="grid gap-3 md:grid-cols-2"><div><label className={lbl}>Acta firmada (escaneada)</label><input type="file" className="text-xs" onChange={(e) => setF({ ...f, archivo: e.target.files[0] || null })} /></div><div><label className={lbl}>Su contraseña (quien registra)</label><input type="password" autoComplete="current-password" className={inp} value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} /></div></div>}
        <div><label className={lbl}>Observaciones</label><CampoAmpliable multilinea rows={2} value={f.observaciones} onChange={(v) => setF({ ...f, observaciones: v })} /></div>
        {err && <p className="rounded bg-red-500/10 px-3 py-2 text-xs text-red-600 dark:text-red-400">{err}</p>}
        <div className="flex justify-end gap-2"><button className="btn-secondary" onClick={onCerrar}>Cerrar</button><button className="btn-primary" disabled={enviando || !(d?.titulares || []).length} onClick={registrar}>Registrar la aprobación</button></div>
      </div>
    </Modal>
  )
}

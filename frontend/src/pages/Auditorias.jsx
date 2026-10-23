import { useCallback, useEffect, useState } from 'react'
import CampoSugerencias from '../components/CampoSugerencias.jsx'
import { useUltimaRespuesta } from '../lib/useUltimaRespuesta.js'
import {
  ClipboardList, Plus, Search, CheckCircle2, Users, FileText, AlertTriangle, Lock, Maximize2,
} from 'lucide-react'
import Modal from '../components/Modal.jsx'
import BarraPasos from '../components/BarraPasos.jsx'
import BarraEtapa from '../components/BarraEtapa.jsx'
import { api } from '../lib/api.js'
import { OpcionesProcesos, useCatalogoProcesos } from '../components/SelectorProceso.jsx'
import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'
import { useConfig } from '../context/ConfigContext.jsx'
import { useConfirm } from '../context/ConfirmContext.jsx'
import { fechaHora } from '../lib/fecha.js'
import TituloModulo from '../components/ui/TituloModulo.jsx'

const NORMAS = [
  ['sig_integrado', 'Sistema Integrado (9001·14001·45001)'],
  ['iso_9001', 'ISO 9001'], ['iso_14001', 'ISO 14001'],
  ['iso_45001', 'ISO 45001 / Ley 29783'], ['iso_17025', 'NTP ISO/IEC 17025'],
]
const CHIP_NORMA = {
  sig_integrado: 'border-slate-400 bg-slate-500/15 text-slate-600 dark:text-slate-300',
  iso_9001: 'border-esynapse-500 bg-esynapse-600/15 text-esynapse-600 dark:text-esynapse-300',
  iso_14001: 'border-emerald-500 bg-emerald-500/15 text-emerald-600 dark:text-emerald-400',
  iso_45001: 'border-red-500 bg-red-500/15 text-red-600 dark:text-red-400',
  iso_17025: 'border-amber-500 bg-amber-500/15 text-amber-600 dark:text-amber-400',
}
const COLOR_NORMA = {
  'Sistema Integrado (ISO 9001 · 14001 · 45001)': 'bg-slate-500/15 text-slate-600 dark:text-slate-300',
  'ISO 9001': 'bg-esynapse-600/15 text-esynapse-600 dark:text-esynapse-300',
  'ISO 14001': 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400',
  'ISO 45001 / Ley 29783': 'bg-red-500/15 text-red-600 dark:text-red-400',
  'NTP ISO/IEC 17025': 'bg-amber-500/15 text-amber-600 dark:text-amber-400',
}
const MODALIDADES = [['presencial', 'Presencial'], ['remota', 'Remota'], ['hibrido', 'Híbrido']]
const ESTADOS = [
  ['programada', 'Programada'], ['planificada', 'Planificada'], ['apertura', 'Reunión de apertura'],
  ['en_ejecucion', 'En ejecución'], ['conclusiones', 'Conclusiones'], ['reunion_cierre', 'Reunión de cierre'],
  ['en_informe', 'En informe'], ['cerrada', 'Cerrada'],
]
const COLOR_ESTADO = {
  'Programada': 'bg-slate-500/15 text-slate-500 dark:text-slate-400',
  'Planificada': 'bg-amber-500/15 text-amber-600 dark:text-amber-400',
  'Reunión de apertura': 'bg-esynapse-600/15 text-esynapse-600 dark:text-esynapse-300',
  'En ejecución': 'bg-esynapse-600/15 text-esynapse-600 dark:text-esynapse-300',
  'Conclusiones': 'bg-esynapse-600/15 text-esynapse-600 dark:text-esynapse-300',
  'Reunión de cierre': 'bg-esynapse-600/15 text-esynapse-600 dark:text-esynapse-300',
  'En informe': 'bg-violet-500/15 text-violet-600 dark:text-violet-400',
  'Cerrada': 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400',
}
// Secuencia del procedimiento de auditoría interna: un paso por estado.
const PASOS = ['programada', 'planificada', 'apertura', 'en_ejecucion', 'conclusiones', 'reunion_cierre', 'en_informe', 'cerrada']
const NOMBRE_PASO = ['Plan', 'Documentos de trabajo', 'Reunión de apertura', 'Ejecución', 'Conclusiones', 'Reunión de cierre', 'Informe', 'Cerrada']
const NORMA_CORTA = { iso_9001: 'ISO 9001', iso_14001: 'ISO 14001', iso_45001: 'ISO 45001', iso_17025: '17025', sig_integrado: 'SIG' }
const TIPO_SUGERIDO = { no_cumple: 'nc_menor', observa: 'observacion' }
const SECCIONES_ACTA = {
  apertura: ['2. Propósito de la auditoría', '3. Consideraciones del área auditada', '4. Compromisos por parte del área auditada'],
  cierre: ['2. Resultados', '3. Observaciones del equipo auditor', '4. Observaciones de la empresa'],
}
const ROLES = [['lider', 'Auditor líder'], ['auditor', 'Auditor'], ['experto', 'Experto técnico'], ['observador', 'Observador']]
const NOMBRE_ROL = Object.fromEntries(ROLES)
// Cargo sugerido para un integrante externo: el nombre de su rol en la
// auditoría. Se reemplaza solo si el cargo está vacío o es otra sugerencia.
const cargoSugerido = (form, rol) =>
  (form.usuario || (form.cargo && !Object.values(NOMBRE_ROL).includes(form.cargo))) ? form.cargo : NOMBRE_ROL[rol]
const TIPOS_HALLAZGO = [['nc_mayor', 'NC Mayor'], ['nc_menor', 'NC Menor'], ['observacion', 'Observación'], ['odm', 'Oportunidad de Mejora']]
const RESULTADOS = [['pendiente', '—'], ['cumple', 'Cumple'], ['no_cumple', 'No cumple'], ['na', 'N/A'], ['observa', 'Observación']]
const COLOR_RESULTADO = {
  cumple: 'text-emerald-600 dark:text-emerald-400',
  no_cumple: 'text-red-600 dark:text-red-400',
  observa: 'text-amber-600 dark:text-amber-400',
  na: 'text-slate-400',
  pendiente: 'text-slate-400',
}

const FORM_VACIO = { programa: '', tipo: 'programada', clase: 'interna', normas: [], areas_procesos: '', modalidad: 'presencial', mes_programado: '', requisitos_por_norma: {}, observaciones_programa: '' }
const MESES = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Setiembre', 'Octubre', 'Noviembre', 'Diciembre']
// Columnas de normas del programa anual (siempre las cuatro, como en el formato).
const NORMAS_PROGRAMA = [
  ['iso_9001', 'ISO 9001:2015'], ['iso_14001', 'ISO 14001:2015'],
  ['iso_45001', 'ISO 45001:2018'], ['iso_17025', 'NTP ISO/IEC 17025:2017'],
]

// Catálogo de cláusulas por norma, cargado una sola vez por sesión.
// Para elegir cláusulas (programa anual, cronograma) solo interesan capítulos
// y cláusulas con su subtítulo; una cláusula sin subtítulo (17025: 5.1, 6.1…)
// se muestra solo por número, con el texto completo como ayuda al pasar el
// cursor. El texto íntegro va en la lista de verificación y en su PDF.
const catalogoCache = {}
const cargarClausulas = (clave) => {
  if (!catalogoCache[clave]) {
    catalogoCache[clave] = api.requisitosNorma(clave).then((d) => {
      // Solo capítulos y cláusulas (4 y 4.1): los numerales de tercer nivel en
      // adelante (4.1.1, 7.8.2.1) se auditan dentro de su cláusula.
      const nivelDe = (codigo) => String(codigo).replace(/\.$/, '').split('.').length
      const filas = (d.results ?? d).filter((r) => (r.bloque || 'requisitos') === 'requisitos' && nivelDe(r.codigo) <= 2)
      const conSecciones = filas.some((r) => r.es_seccion)
      return filas.map((r) => ({
        ...r,
        etiqueta: r.es_seccion || !conSecciones ? r.titulo : '',
        ayuda: r.es_seccion ? '' : r.titulo,
        nivel: nivelDe(r.codigo) - 1,
      }))
    }).catch(() => [])
  }
  return catalogoCache[clave]
}
const NOMBRE_NORMA_PROGRAMA = Object.fromEntries(NORMAS_PROGRAMA)
const aLista = (texto) => (texto || '').split(',').map((s) => s.trim()).filter(Boolean)
const ordenarClausulas = (arr) => [...arr].sort((a, b) => a.localeCompare(b, undefined, { numeric: true }))

/** Modal para elegir cláusulas de UNA norma (lo usa el cronograma de entrevistas).
 *  Devuelve por onAceptar el texto "4.1, 7.5" o "Todas". */
function ModalClausulas({ clave, valor, sugeridas, onAceptar, onCerrar }) {
  const [items, setItems] = useState([])
  const [sel, setSel] = useState(() => aLista(valor))
  const [filtro, setFiltro] = useState('')
  useEffect(() => { cargarClausulas(clave).then(setItems) }, [clave])
  const todas = sel.includes('Todas')
  const toggle = (c) => setSel((s) => { const l = s.filter((x) => x !== 'Todas'); return l.includes(c) ? l.filter((x) => x !== c) : ordenarClausulas([...l, c]) })
  const visibles = items.filter((r) => !filtro || `${r.codigo} ${r.titulo}`.toLowerCase().includes(filtro.toLowerCase()))
  const sugeridasLista = aLista(sugeridas)
  return (
    <Modal abierto titulo={`Cláusulas — ${NOMBRE_NORMA_PROGRAMA[clave] || clave}`} onCerrar={onCerrar} ancho="max-w-lg">
      <div className="space-y-2">
        <div className="flex flex-wrap items-center gap-2">
          <label className="flex cursor-pointer items-center gap-2 text-xs font-medium">
            <input type="checkbox" className="h-3.5 w-3.5 accent-esynapse-600" checked={todas} onChange={(e) => setSel(e.target.checked ? ['Todas'] : [])} />
            Todas las cláusulas
          </label>
          {sugeridasLista.length > 0 && !todas && (
            <button type="button" onClick={() => setSel(sugeridasLista)} className="text-xs text-esynapse-500 hover:underline" title={sugeridasLista.join(', ')}>
              usar las del programa ({sugeridasLista.includes('Todas') ? 'todas' : sugeridasLista.length})
            </button>
          )}
          <span className="ml-auto text-[11px] text-slate-400">{todas ? 'todas' : sel.length ? `${sel.length} seleccionadas` : 'ninguna'}</span>
          {sel.length > 0 && <button type="button" onClick={() => setSel([])} className="text-xs text-red-500 hover:underline">limpiar</button>}
        </div>
        <input className="input-esynapse !py-1 text-xs" placeholder="buscar cláusula…" disabled={todas} value={filtro} onChange={(e) => setFiltro(e.target.value)} />
        <div className={`max-h-72 space-y-0.5 overflow-y-auto rounded-lg border border-slate-200 p-2 dark:border-slate-800 ${todas ? 'opacity-40' : ''}`}>
          {visibles.map((r) => (
            <label key={r.id} title={r.ayuda} className={`flex cursor-pointer items-start gap-2 text-xs text-slate-700 dark:text-slate-300 ${r.nivel ? 'ml-4' : ''} ${r.es_seccion ? 'mt-1 font-semibold' : ''}`}>
              <input type="checkbox" className="mt-0.5 h-3.5 w-3.5 shrink-0 accent-esynapse-600" disabled={todas}
                checked={sel.includes(r.codigo)} onChange={() => toggle(r.codigo)} />
              <span><span className="font-mono font-medium">{r.codigo}</span> {r.etiqueta}
                {sugeridasLista.includes(r.codigo) && <span className="ml-1 rounded bg-esynapse-600/15 px-1 text-[11px] text-esynapse-600 dark:text-esynapse-300">programa</span>}
              </span>
            </label>
          ))}
          {visibles.length === 0 && <p className="text-[11px] text-slate-400">sin resultados</p>}
        </div>
        <div className="flex justify-end gap-2 pt-1">
          <button type="button" onClick={onCerrar} className="btn-secondary">Cancelar</button>
          <button type="button" onClick={() => onAceptar(sel.join(', '))} className="btn-primary">Aceptar</button>
        </div>
      </div>
    </Modal>
  )
}

/** Selector de cláusulas por norma, de selección múltiple (casillas).
 *  Guarda por norma un texto "4.1, 7.5" (como el formato) o "Todas". */
function SelectorRequisitos({ valor, onChange, disabled, normas = [] }) {
  const [catalogo, setCatalogo] = useState({})
  const [filtro, setFiltro] = useState({})
  // Solo se habilitan las normas marcadas en "Normas / criterios";
  // el Sistema Integrado habilita 9001, 14001 y 45001.
  const habilitadas = new Set(normas.flatMap((n) => (n === 'sig_integrado' ? ['iso_9001', 'iso_14001', 'iso_45001'] : [n])))
  const visibles = NORMAS_PROGRAMA.filter(([clave]) => habilitadas.has(clave))
  useEffect(() => {
    NORMAS_PROGRAMA.forEach(([clave]) => {
      cargarClausulas(clave).then((items) => setCatalogo((c) => ({ ...c, [clave]: items })))
    })
  }, [])
  const lista = (clave) => (valor?.[clave] || '').split(',').map((s) => s.trim()).filter(Boolean)
  const setLista = (clave, arr) => onChange({ ...(valor || {}), [clave]: arr.join(', ') })
  const esTodas = (clave) => lista(clave).includes('Todas')
  const toggle = (clave, codigo) => {
    const l = lista(clave).filter((x) => x !== 'Todas')
    setLista(clave, l.includes(codigo) ? l.filter((x) => x !== codigo) : [...l, codigo].sort((a, b) => a.localeCompare(b, undefined, { numeric: true })))
  }
  if (visibles.length === 0) {
    return <p className="rounded-lg border border-dashed border-slate-300 px-3 py-2 text-[11px] text-slate-400 dark:border-slate-700">Marca primero las normas / criterios de la auditoría para elegir sus cláusulas.</p>
  }
  return (
    <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
      {visibles.map(([clave, nombre]) => {
        const items = (catalogo[clave] || []).filter((r) => !filtro[clave] || `${r.codigo} ${r.titulo}`.toLowerCase().includes(filtro[clave].toLowerCase()))
        const n = lista(clave).filter((x) => x !== 'Todas').length
        return (
          <div key={clave} className={`rounded-lg border p-2 ${CHIP_NORMA[clave]} !bg-transparent`}>
            <div className="mb-1 flex items-center justify-between gap-2">
              <p className="text-[11px] font-semibold">{nombre}</p>
              <span className="flex items-center gap-2 text-[11px] text-slate-500 dark:text-slate-400">
                {esTodas(clave) ? 'todas' : n ? `${n} seleccionadas` : 'sin cláusulas'}
                {!disabled && (esTodas(clave) || n > 0) && (
                  <button type="button" onClick={() => setLista(clave, [])} className="text-red-500 hover:underline" title="Desmarcar todas las cláusulas de esta norma">limpiar</button>
                )}
              </span>
            </div>
            <label className="mb-1 flex cursor-pointer items-center gap-2 text-[11px] font-medium">
              <input type="checkbox" className="h-3.5 w-3.5 accent-esynapse-600" disabled={disabled} checked={esTodas(clave)}
                onChange={(e) => setLista(clave, e.target.checked ? ['Todas'] : [])} />
              Todas las cláusulas
            </label>
            <input className="input-esynapse mb-1 !py-1 text-[11px]" placeholder="buscar…" disabled={disabled || esTodas(clave)}
              value={filtro[clave] || ''} onChange={(e) => setFiltro({ ...filtro, [clave]: e.target.value })} />
            <div className={`max-h-36 space-y-0.5 overflow-y-auto pr-1 ${esTodas(clave) ? 'opacity-40' : ''}`}>
              {items.map((r) => (
                <label key={r.id} title={r.ayuda} className={`flex cursor-pointer items-start gap-2 text-[11px] text-slate-700 dark:text-slate-300 ${r.nivel ? 'ml-4' : ''} ${r.es_seccion ? 'mt-1 font-semibold' : ''}`}>
                  <input type="checkbox" className="mt-0.5 h-3.5 w-3.5 shrink-0 accent-esynapse-600" disabled={disabled || esTodas(clave)}
                    checked={lista(clave).includes(r.codigo)} onChange={() => toggle(clave, r.codigo)} />
                  <span><span className="font-mono font-medium">{r.codigo}</span> {r.etiqueta}</span>
                </label>
              ))}
              {items.length === 0 && <p className="text-[11px] text-slate-500 dark:text-slate-400">sin resultados</p>}
            </div>
          </div>
        )
      })}
    </div>
  )
}

/** Texto de un requisito con la presentación del formato (negritas, viñetas
 *  a) b) c) y sangrías). Solo admite las marcas b, i, u y br del catálogo. */
function TextoRequisito({ item }) {
  const limpiar = (t) => (t || '').replace(/<(?!\/?(b|i|u)>|br\s*\/?>)[^>]*>/gi, '')
  const formato = item?.formato || []
  if (!formato.length) return <p className="whitespace-pre-line">{item?.titulo}</p>
  return (
    <div className="space-y-0.5">
      {formato.map((p, i) => (
        (!p.t && !p.l) ? <div key={i} className="h-2" /> : (
          <div key={i} className="flex gap-1.5" style={{ marginLeft: p.l ? Math.max((p.i || 0) - 14, 0) : (p.i || 0) }}>
            {p.l && <span className="w-4 shrink-0">{p.l}</span>}
            <span className={p.j === 'center' ? 'text-center' : 'text-justify'} dangerouslySetInnerHTML={{ __html: limpiar(p.t) }} />
          </div>
        )
      ))}
    </div>
  )
}

/** Ventana para redactar o revisar un ítem de la lista de verificación con
 *  espacio: requisito completo, documento de referencia, evidencia y conclusión,
 *  con navegación al ítem anterior / siguiente (guarda al moverse). */
function ModalItemLista({ items, itemId, normaNombre, puedeDocRef, puedeEvaluar, onGuardar, onCerrar }) {
  const evaluables = items.filter((x) => !x.es_seccion)
  const [idx, setIdx] = useState(() => Math.max(evaluables.findIndex((x) => x.id === itemId), 0))
  const it = evaluables[idx]
  const inicial = (x) => ({ documento_referencia: x?.documento_referencia || '', evidencia: x?.evidencia || '', resultado: x?.resultado || 'pendiente' })
  const [draft, setDraft] = useState(() => inicial(it))
  const [guardando, setGuardando] = useState(false)
  const [errorItem, setErrorItem] = useState('')
  useEffect(() => { setDraft(inicial(evaluables[idx])); setErrorItem('') }, [idx])  // eslint-disable-line react-hooks/exhaustive-deps
  if (!it) return null
  const cambios = {}
  if (puedeDocRef && draft.documento_referencia !== (it.documento_referencia || '')) cambios.documento_referencia = draft.documento_referencia
  if (puedeEvaluar && draft.evidencia !== (it.evidencia || '')) cambios.evidencia = draft.evidencia
  if (puedeEvaluar && draft.resultado !== (it.resultado || 'pendiente')) cambios.resultado = draft.resultado
  const sucio = Object.keys(cambios).length > 0
  const guardarY = async (siguiente) => {
    setErrorItem('')
    if (sucio) {
      setGuardando(true)
      try { await onGuardar(it.id, cambios) } catch (e) { setErrorItem(e.message); setGuardando(false); return }
      setGuardando(false)
    }
    siguiente()
  }
  const seguimiento = it.bloque === 'seguimiento'
  return (
    <Modal abierto titulo={`${normaNombre} · ${seguimiento ? 'Ítem de seguimiento' : (/^\d+$/.test(it.codigo || '') ? 'Pregunta N.°' : 'Requisito')} ${it.codigo}`} onCerrar={onCerrar} ancho="max-w-3xl">
      <div className="space-y-3 text-sm">
        <div className="max-h-56 overflow-y-auto rounded-lg bg-slate-500/5 p-3 text-xs leading-relaxed text-slate-700 dark:text-slate-200">
          <TextoRequisito item={it} />
        </div>
        <div>
          <label className="mb-1 block text-[11px] font-medium text-slate-500 dark:text-slate-400">Documento de referencia</label>
          <textarea className="input-esynapse text-xs" rows={2} disabled={!puedeDocRef} placeholder="Procedimiento, registro, instructivo…"
            value={draft.documento_referencia} onChange={(e) => setDraft({ ...draft, documento_referencia: e.target.value })} />
        </div>
        <div>
          <label className="mb-1 block text-[11px] font-medium text-slate-500 dark:text-slate-400">Evaluación / evidencias</label>
          <textarea className="input-esynapse text-xs" rows={7} disabled={!puedeEvaluar}
            placeholder={puedeEvaluar ? 'Evidencia objetiva revisada: registros, entrevistas, observaciones…' : 'Se registra durante la ejecución, después de la reunión de apertura.'}
            value={draft.evidencia} onChange={(e) => setDraft({ ...draft, evidencia: e.target.value })} />
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <label className="text-[11px] font-medium text-slate-500 dark:text-slate-400">Conclusión</label>
          <select className={`input-esynapse w-40 !py-1 text-xs font-medium ${COLOR_RESULTADO[draft.resultado]}`} disabled={!puedeEvaluar}
            value={draft.resultado} onChange={(e) => setDraft({ ...draft, resultado: e.target.value })}>
            {RESULTADOS.map(([v, n]) => <option key={v} value={v}>{v === 'pendiente' ? 'Sin evaluar' : n}</option>)}
          </select>
          <span className="ml-auto text-[11px] text-slate-400">Ítem {idx + 1} de {evaluables.length}{sucio ? ' · cambios sin guardar' : ''}</span>
        </div>
        {['no_cumple', 'observa'].includes(it.resultado) && (
          <p className="rounded-lg bg-amber-500/10 px-3 py-1.5 text-[11px] text-amber-700 dark:text-amber-400">
            {it.hallazgo_codigo ? `Registrado en el hallazgo ${it.hallazgo_codigo}.`
              : it.motivo_descarte ? `No genera hallazgo: ${it.motivo_descarte}`
                : 'Pendiente de clasificar en la sección Hallazgos.'}
          </p>
        )}
        {errorItem && <p className="rounded-lg bg-red-500/10 px-3 py-2 text-xs text-red-500">{errorItem}</p>}
        <div className="flex flex-wrap justify-between gap-2 border-t border-slate-200 pt-3 dark:border-slate-800">
          <button disabled={idx === 0 || guardando} onClick={() => guardarY(() => setIdx(idx - 1))} className="btn-secondary !py-1.5 text-xs disabled:opacity-40">← Anterior</button>
          <div className="flex gap-2">
            <button onClick={() => guardarY(onCerrar)} disabled={guardando} className="btn-secondary !py-1.5 text-xs">{sucio ? 'Guardar y cerrar' : 'Cerrar'}</button>
            <button disabled={idx === evaluables.length - 1 || guardando} onClick={() => guardarY(() => setIdx(idx + 1))} className="btn-primary !py-1.5 text-xs disabled:opacity-40">
              {sucio ? 'Guardar y siguiente →' : 'Siguiente →'}
            </button>
          </div>
        </div>
      </div>
    </Modal>
  )
}

/** Ventana para registrar, corregir o leer un hallazgo con espacio para redactar. */
function ModalHallazgo({ inicial, soloLectura, titulo, origen = [], onGuardar, onCerrar }) {
  const [h, setH] = useState({ tipo: inicial?.tipo || 'nc_menor', requisito: inicial?.requisito || '', descripcion: inicial?.descripcion || '' })
  const [guardando, setGuardando] = useState(false)
  const [errorH, setErrorH] = useState('')
  const destino = ['nc_mayor', 'nc_menor'].includes(h.tipo)
    ? 'Se tratará por acción correctiva.'
    : 'Se tratará por riesgos y oportunidades (sin acción correctiva).'
  const guardar = async () => {
    if (!h.descripcion.trim()) { setErrorH('Describe el hallazgo.'); return }
    setGuardando(true); setErrorH('')
    try { await onGuardar(h); onCerrar() } catch (e) { setErrorH(e.message) } finally { setGuardando(false) }
  }
  return (
    <Modal abierto titulo={titulo} onCerrar={onCerrar} ancho="max-w-2xl">
      <div className="space-y-3 text-sm">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="mb-1 block text-[11px] font-medium text-slate-500 dark:text-slate-400">Tipo</label>
            <select className="input-esynapse text-xs" disabled={soloLectura} value={h.tipo} onChange={(e) => setH({ ...h, tipo: e.target.value })}>
              {TIPOS_HALLAZGO.map(([v, n]) => <option key={v} value={v}>{n}</option>)}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-[11px] font-medium text-slate-500 dark:text-slate-400">Requisito</label>
            <input className="input-esynapse text-xs" disabled={soloLectura} placeholder="Ej.: NTP ISO/IEC 17025 6.4.13" value={h.requisito} onChange={(e) => setH({ ...h, requisito: e.target.value })} />
          </div>
        </div>
        <p className="text-[11px] text-slate-500 dark:text-slate-400">{destino}</p>
        {origen.length > 0 && (
          <p className="rounded-lg bg-slate-500/5 px-3 py-1.5 text-[11px] text-slate-600 dark:text-slate-300">
            Origen en la lista de verificación: {origen.map((x) => `${NORMA_CORTA[x.norma] || x.norma} ${x.codigo}`).join(' · ')}
          </p>
        )}
        <div>
          <label className="mb-1 block text-[11px] font-medium text-slate-500 dark:text-slate-400">Descripción del hallazgo y evidencia</label>
          <textarea className="input-esynapse text-xs leading-relaxed" rows={9} disabled={soloLectura}
            placeholder="Qué se encontró, qué requisito no se cumple y la evidencia objetiva que lo sustenta (registro, entrevista, observación)."
            value={h.descripcion} onChange={(e) => { setH({ ...h, descripcion: e.target.value }); setErrorH('') }} />
        </div>
        {errorH && <p className="rounded-lg bg-red-500/10 px-3 py-2 text-xs text-red-500">{errorH}</p>}
        <div className="flex justify-end gap-2 border-t border-slate-200 pt-3 dark:border-slate-800">
          <button onClick={onCerrar} className="btn-secondary !py-1.5 text-xs">{soloLectura ? 'Cerrar' : 'Cancelar'}</button>
          {!soloLectura && <button onClick={guardar} disabled={guardando} className="btn-primary !py-1.5 text-xs">Guardar hallazgo</button>}
        </div>
      </div>
    </Modal>
  )
}

// Columnas de requisitos del cronograma de entrevistas (una por norma, como en el formato).
const REQ_CRONO = [
  ['req_9001', 'ISO 9001:2015'], ['req_14001', 'ISO 14001:2015'],
  ['req_45001', 'ISO 45001:2018'], ['req_17025', 'NTP ISO/IEC 17025:2017'],
]
const CRONO_VACIO = {
  fecha: '', hora: '', area: '', req_9001: '', req_14001: '', req_45001: '', req_17025: '',
  modalidad: 'presencial', tic: '', auditor: '', auditado: '',
}

export default function Auditorias() {
  const { tienePermiso } = useAuth()
  const catalogoProcesos = useCatalogoProcesos()
  const { config } = useConfig()
  // Datos de la empresa que imprime el bloque "1. Datos del laboratorio" del plan.
  const faltanDatosEmpresa = [
    !(config?.subtitulo || '').trim() && 'nombre de la empresa',
    !(config?.direccion || '').trim() && 'dirección',
    !(config?.responsable_sig || '').trim() && 'responsable del SIG',
  ].filter(Boolean)
  const [items, setItems] = useState([])
  const [usuarios, setUsuarios] = useState([])
  const [programas, setProgramas] = useState([])
  const [buscar, setBuscar] = useState('')
  const [estado, setEstado] = useState('')
  const [modalCrear, setModalCrear] = useState(false)
  const [modalPrograma, setModalPrograma] = useState(false)
  const [anioNuevo, setAnioNuevo] = useState(new Date().getFullYear())
  const [programaSel, setProgramaSel] = useState('')
  const [reprog, setReprog] = useState({ mes: '', motivo: '' })
  const [aviso, setAviso] = useState('')
  const [pickCrono, setPickCrono] = useState(null)   // { i, k, clave } celda de cláusulas abierta en el cronograma
  // Candado de aprobación (programa anual e informes de cierre)
  const [pendientes, setPendientes] = useState([]); const [modalPend, setModalPend] = useState(false)
  const [misSolic, setMisSolic] = useState([]); const [modalMis, setModalMis] = useState(false); const [misDevueltas, setMisDevueltas] = useState(0)
  const confirmar = useConfirm()
  const [detalle, setDetalle] = useState(null)
  const [form, setForm] = useState(FORM_VACIO)
  const [error, setError] = useState('')
  // edición de datos generales
  const [gen, setGen] = useState({})
  const [equipoForm, setEquipoForm] = useState({ usuario: '', nombre_externo: '', rol: 'auditor', cargo: '' })
  const [informe, setInforme] = useState({ lugar: '', personas_entrevistadas: '', fortalezas: '', debilidades: '', conclusiones: '' })
  const [listaAbierta, setListaAbierta] = useState(null)
  const [actaForm, setActaForm] = useState({ tipo: 'apertura', contenido: '', seccion3: '', observaciones_auditado: '', participantes: [] })
  const [vista, setVista] = useState(0)          // paso que se está viendo
  const [itemAbierto, setItemAbierto] = useState(null) // { clave, id } ítem de lista en la ventana de edición
  const [hallModal, setHallModal] = useState(null)     // { modo: 'nuevo' | 'editar' | 'ver', h, items }
  const [pendSel, setPendSel] = useState([])           // ítems pendientes de clasificar seleccionados

  const ultima = useUltimaRespuesta()
  const cargar = useCallback(async () => {
    const p = new URLSearchParams()
    if (buscar) p.set('buscar', buscar)
    if (estado) p.set('estado', estado)
    if (programaSel === 'sin') p.set('sin_programa', '1')
    else if (programaSel) p.set('programa', programaSel)
    const d = await ultima(api.auditorias.listar(`?${p}`))
    setItems(d.results ?? d)
  }, [buscar, estado, programaSel])

  useEffect(() => { cargar().catch(() => {}) }, [cargar])
  useEffect(() => {
    api.usuarios.listar().then((d) => setUsuarios(d.results ?? d)).catch(() => {})
    api.programasAuditoria.listar().then((d) => setProgramas(d.results ?? d)).catch(() => {})
  }, [])

  const abrir = async (id) => {
    setError('')
    const d = await api.auditorias.detalle(id)
    setDetalle(d)
    setGen({
      objetivo: d.objetivo || '', alcance: d.alcance || '', criterios: d.criterios || '',
      documentos_referencia: d.documentos_referencia || '',
      fecha_elaboracion_plan: d.fecha_elaboracion_plan || '',
      modalidad: d.modalidad || 'presencial', observaciones_plan: d.observaciones_plan || '',
      cronograma_entrevistas: d.cronograma_entrevistas || [],
      clase: d.clase || 'interna', requisitos_por_norma: d.requisitos_por_norma || {},
      observaciones_programa: d.observaciones_programa || '',
    })
    setReprog({ mes: '', motivo: '' })
    setInforme({ lugar: d.lugar || '', personas_entrevistadas: d.personas_entrevistadas || '',
      fortalezas: d.fortalezas || '', debilidades: d.debilidades || '', conclusiones: d.conclusiones || '' })
    setEquipoForm({ usuario: '', nombre_externo: '', rol: (d.equipo || []).some((m) => m.rol === 'lider') ? 'auditor' : 'lider', cargo: '' })
    setActaForm({ tipo: 'apertura', contenido: '', seccion3: '', observaciones_auditado: '', participantes: [] })
    setListaAbierta(null)
    setItemAbierto(null)
    setHallModal(null)
    setPendSel([])
  }

  const refrescar = async () => {
    await cargar()
    if (detalle) setDetalle(await api.auditorias.detalle(detalle.id))
    api.programasAuditoria.listar().then((d) => setProgramas(d.results ?? d)).catch(() => {})
  }
  const accion = async (fn) => { setError(''); try { await fn(); await refrescar() } catch (e) { setError(e.message) } }

  // --- Candado de aprobación ---
  const puedeAprobarAud = tienePermiso('auditorias', 'aprobar')
  const cargarPendientes = () => { if (!puedeAprobarAud) return; api.solicitudesAuditoria.listar('?estado=pendiente').then((d) => setPendientes(d.results ?? d)).catch(() => {}) }
  const cargarMis = () => {
    api.solicitudesAuditoria.listar('?estado=todas&mias=1').then((d) => setMisSolic(d.results ?? d)).catch(() => {})
    api.solicitudesAuditoria.misDevueltasCount().then((d) => setMisDevueltas(d.devueltas || 0)).catch(() => {})
  }
  useEffect(() => { cargarPendientes(); cargarMis() }, [])  // eslint-disable-line react-hooks/exhaustive-deps
  const avisoPendiente = async (resp) => {
    if (resp?.pendiente) {
      cargarPendientes(); cargarMis()
      await confirmar({ titulo: 'Pendiente de aprobación', mensaje: resp.detail || 'Quedó pendiente de aprobación por un supervisor.', textoConfirmar: 'Entendido', textoCancelar: 'Cerrar' })
      return true
    }
    return false
  }
  const resolver = async (s, tipo) => {
    let obs = ''
    if (tipo === 'aprobar') { if (!await confirmar({ titulo: 'Aprobar', mensaje: `¿Aprobar "${s.resumen}" de ${s.solicitante}?`, textoConfirmar: 'Aprobar' })) return }
    else {
      obs = await confirmar({
        titulo: tipo === 'devolver' ? 'Devolver para corrección' : 'Rechazar solicitud',
        mensaje: `"${s.resumen}" — solicitado por ${s.solicitante}.`,
        textoConfirmar: tipo === 'devolver' ? 'Devolver' : 'Rechazar', peligro: tipo === 'rechazar',
        entrada: { etiqueta: tipo === 'devolver' ? 'Qué debe corregir' : 'Motivo del rechazo', multilinea: true, obligatorio: tipo === 'devolver' },
      })
      if (obs === null) return
    }
    try {
      if (tipo === 'aprobar') await api.solicitudesAuditoria.aprobar(s.id)
      else if (tipo === 'devolver') await api.solicitudesAuditoria.devolver(s.id, obs)
      else await api.solicitudesAuditoria.rechazar(s.id, obs)
      cargarPendientes(); await refrescar()
    } catch (e) { setError(e.message) }
  }
  const reenviar = async (s) => {
    let payload = null
    if (s.entidad === 'informe_auditoria') {
      if (!await confirmar({
        titulo: 'Reenviar el cierre', textoConfirmar: 'Reenviar',
        mensaje: `${s.observaciones ? `Motivo de la devolución: ${s.observaciones}. ` : ''}Corrige el informe (lugar, entrevistados, fortalezas, debilidades) antes de reenviar; las conclusiones ya se comunicaron en la reunión de cierre y no cambian.`,
      })) return
      payload = {}
    } else if (!await confirmar({ titulo: 'Reenviar', mensaje: `¿Reenviar "${s.resumen}" para aprobación?`, textoConfirmar: 'Reenviar' })) return
    try { await api.solicitudesAuditoria.reenviar(s.id, payload); cargarMis(); cargarPendientes() } catch (e) { setError(e.message) }
  }
  const aprobarPrograma = async (id) => {
    setError('')
    try { const r = await api.programasAuditoria.aprobar(id); if (!await avisoPendiente(r)) await refrescar() }
    catch (e) { setError(e.message) }
  }
  const modificarPrograma = async (p) => {
    const motivo = await confirmar({
      titulo: `Modificar el programa ${p.anio}`,
      mensaje: `El programa está aprobado (revisión ${p.revision || 0}). Al abrirlo para modificación dejará de estar bloqueado y deberá aprobarse de nuevo; la nueva aprobación será la revisión ${(p.revision || 0) + 1}.`,
      textoConfirmar: 'Abrir para modificación',
      entrada: { etiqueta: 'Motivo de la modificación', placeholder: 'Ej.: se agrega auditoría al laboratorio de Masa', multilinea: true, obligatorio: true },
    })
    if (motivo === null) return
    setError('')
    try { await api.programasAuditoria.abrirModificacion(p.id, motivo); await refrescar() }
    catch (e) { setError(e.message) }
  }
  const programaActual = programas.find((p) => String(p.id) === String(programaSel))
  // Normas de la auditoría abierta (el Sistema Integrado habilita 9001, 14001 y 45001) para el cronograma.
  const normasCrono = new Set((detalle?.normas_aplicables || []).flatMap((n) => (n === 'sig_integrado' ? ['iso_9001', 'iso_14001', 'iso_45001'] : [n])))
  const ESTADO_PROG = { borrador: ['Borrador', 'bg-slate-500/15 text-slate-500 dark:text-slate-400'], en_modificacion: ['En modificación', 'bg-amber-500/15 text-amber-600 dark:text-amber-400'], aprobado: ['Aprobado · solo lectura', 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400'] }
  const setCrono = (i, campo, valor) => setGen((g) => ({
    ...g,
    cronograma_entrevistas: (g.cronograma_entrevistas || []).map((x, j) => (j === i ? { ...x, [campo]: valor } : x)),
  }))
  const abrirPdf = async (promesa) => {
    setError('')
    try {
      const blob = await promesa
      const url = URL.createObjectURL(blob)
      window.open(url, '_blank')
      setTimeout(() => URL.revokeObjectURL(url), 60000)
    } catch (e) { setError(e.message) }
  }

  const crearPrograma = async () => {
    setError('')
    try {
      await api.programasAuditoria.crear({ anio: Number(anioNuevo) })
      setModalPrograma(false)
      setProgramas((await api.programasAuditoria.listar()).results ?? [])
    } catch (e) { setError(e.message) }
  }

  const crear = async (e) => {
    e.preventDefault()
    setError('')
    try {
      const datos = { ...form, normas_aplicables: form.normas }
      delete datos.normas
      if (!datos.programa) delete datos.programa
      if (!datos.mes_programado) delete datos.mes_programado
      await api.auditorias.crear(datos)
      setModalCrear(false); setForm(FORM_VACIO); await cargar()
    } catch (e2) { setError(e2.message) }
  }

  const guardarGenerales = async () => {
    const datos = { ...gen }
    if (!datos.fecha_elaboracion_plan) datos.fecha_elaboracion_plan = null
    await api.auditorias.actualizar(detalle.id, datos)
  }

  const paso = (d) => PASOS.indexOf(d?.estado)
  const puedeEditar = tienePermiso('auditorias', 'editar')
  // Un solo auditor líder, definido en el equipo auditor.
  const hayLider = (detalle?.equipo || []).some((m) => m.rol === 'lider')
  const puedeAprobar = tienePermiso('auditorias', 'aprobar')
  // Etapas abiertas según el estado (las calcula el servidor): una etapa
  // cerrada se muestra, pero no se edita.
  const et = detalle?.etapas_abiertas || {}
  const edProg = puedeEditar && !!et.programa && detalle?.programa_estado !== 'aprobado'
  const edPlan = puedeEditar && !!et.plan
  const edDocs = puedeEditar && !!et.documentos
  const edAper = puedeEditar && !!et.apertura
  const edEjec = puedeEditar && !!et.ejecucion
  const edConc = puedeEditar && !!et.conclusiones
  const edCierre = puedeEditar && !!et.cierre
  const edInf = puedeEditar && !!et.informe
  const puedeReprog = puedeEditar && ['programada', 'planificada'].includes(detalle?.estado)
  const SoloLectura = ({ cuando, texto }) => cuando ? null : (
    <span className="rounded bg-slate-500/15 px-1.5 py-0.5 text-[11px] font-medium text-slate-500 dark:text-slate-400" title={texto}>solo lectura</span>
  )


  // Al abrir la auditoría o al avanzar de etapa, se muestra la etapa en curso.
  useEffect(() => { if (detalle) setVista(Math.max(PASOS.indexOf(detalle.estado), 0)) }, [detalle?.id, detalle?.estado])  // eslint-disable-line react-hooks/exhaustive-deps
  // El formulario de acta se carga con el acta del paso (apertura o cierre).
  useEffect(() => {
    if (!detalle) return
    const tipo = vista === 2 ? 'apertura' : vista === 5 ? 'cierre' : null
    if (!tipo) return
    const ac = (detalle.actas || []).find((x) => x.tipo === tipo)
    setActaForm({ tipo, contenido: ac?.contenido || '', seccion3: ac?.seccion3 || '', observaciones_auditado: ac?.observaciones_auditado || '', participantes: ac?.participantes || [] })
  }, [vista, detalle?.id])  // eslint-disable-line react-hooks/exhaustive-deps

  // --- Acciones que avanzan la secuencia ---
  const avanzar = async ({ titulo, mensaje, textoConfirmar, fn }) => {
    if (!await confirmar({ titulo, mensaje, textoConfirmar })) return
    await accion(fn)
  }
  const aprobarPlan = () => avanzar({
    titulo: 'Aprobar y comunicar el plan', textoConfirmar: 'Aprobar plan',
    mensaje: 'El plan, el equipo auditor y el cronograma quedarán de solo lectura y se comunicarán a las áreas involucradas. Sigue la preparación de los documentos de trabajo.',
    fn: async () => { await guardarGenerales(); await api.auditorias.planificar(detalle.id) },
  })
  const iniciarEjecucion = () => avanzar({
    titulo: 'Iniciar la ejecución', textoConfirmar: 'Iniciar',
    mensaje: 'Los documentos de trabajo quedarán listos. El siguiente paso es la reunión de apertura: sin su acta no se evalúa la lista ni se registran hallazgos.',
    fn: () => api.auditorias.iniciar(detalle.id),
  })
  const registrarActa = (tipo) => avanzar({
    titulo: tipo === 'apertura' ? 'Registrar el acta de apertura' : 'Registrar el acta de cierre', textoConfirmar: 'Registrar acta',
    mensaje: tipo === 'apertura'
      ? 'El acta no se podrá modificar después. Con ella inicia la ejecución de la auditoría.'
      : 'El acta no se podrá modificar después. Los hallazgos comunicados quedan congelados y sigue el informe.',
    fn: () => api.auditorias.registrarActa(detalle.id, { ...actaForm, tipo }),
  })
  const terminarEjecucion = () => avanzar({
    titulo: 'Terminar la ejecución', textoConfirmar: 'Terminar ejecución',
    mensaje: 'La evaluación de la lista quedará de solo lectura. Sigue la reunión del equipo auditor para consolidar y clasificar los hallazgos.',
    fn: () => api.auditorias.terminarEjecucion(detalle.id),
  })
  const validarHallazgos = () => avanzar({
    titulo: 'Validar los hallazgos', textoConfirmar: 'Validar',
    mensaje: 'Los hallazgos y las conclusiones quedarán listos para presentarse en la reunión de cierre.',
    fn: () => api.auditorias.validarHallazgos(detalle.id, { conclusiones: informe.conclusiones }),
  })
  const cerrarAuditoria = async () => {
    if (!await confirmar({
      titulo: puedeAprobar ? 'Entregar el informe y cerrar' : 'Enviar el cierre a aprobación', textoConfirmar: puedeAprobar ? 'Cerrar auditoría' : 'Enviar',
      mensaje: 'El informe se entrega al Gerente SIG junto con los registros de la auditoría. Al cerrarse, todo queda de solo lectura.',
    })) return
    setError('')
    try {
      await api.auditorias.actualizar(detalle.id, { lugar: informe.lugar, personas_entrevistadas: informe.personas_entrevistadas, fortalezas: informe.fortalezas, debilidades: informe.debilidades })
      const r = await api.auditorias.cerrar(detalle.id, {})
      if (!await avisoPendiente(r)) await refrescar()
    } catch (e) { setError(e.message) }
  }
  const descartarHallazgo = async (h) => {
    if (!await confirmar({ titulo: 'Descartar hallazgo', mensaje: `¿Descartar ${h.codigo}? Úsalo cuando no se sostiene con evidencia objetiva. Queda registrado como anulado.`, textoConfirmar: 'Descartar', peligro: true })) return
    await accion(() => api.auditorias.anularHallazgo(detalle.id, h.id))
  }

  const renderListas = (modo) => (
    <div className="space-y-2">
                {(detalle.normas_aplicables || []).filter((clave) => modo === 'preparacion' || (detalle.listas || []).some((l) => l.norma === clave)).map((clave) => {
                  const lista = (detalle.listas || []).find((l) => l.norma === clave)
                  const nombre = NORMAS.find((n) => n[0] === clave)?.[1] || clave
                  return (
                    <div key={clave} className="rounded-lg border border-slate-100 dark:border-slate-800/60">
                      <div className="flex items-center justify-between px-2 py-1.5">
                        <span className={`whitespace-nowrap rounded px-1.5 py-0.5 text-[11px] font-medium ${CHIP_NORMA[clave]}`}>{nombre}</span>
                        {lista ? (
                          <div className="flex items-center gap-3">
                            <button onClick={() => setListaAbierta(listaAbierta === clave ? null : clave)} className="text-xs text-esynapse-500 hover:underline">
                              {listaAbierta === clave ? 'ocultar' : `ver (${lista.avance})`}
                            </button>
                            <button onClick={() => abrirPdf(api.auditorias.listaPdf(detalle.id, clave))} className="text-xs text-esynapse-500 hover:underline flex items-center gap-1">
                              <FileText className="h-3.5 w-3.5" /> PDF
                            </button>
                          </div>
                        ) : (edDocs && (
                          <button onClick={() => accion(() => api.auditorias.generarLista(detalle.id, clave))} className="text-xs text-esynapse-500 hover:underline">generar lista</button>
                        ))}
                      </div>
                      {lista && listaAbierta === clave && (
                        <div className="max-h-72 space-y-0.5 overflow-y-auto border-t border-slate-100 p-2 dark:border-slate-800/60">
                          {lista.items.some((it) => it.bloque === 'seguimiento') && (
                            <p className="pb-1 text-[11px] font-semibold text-slate-600 dark:text-slate-300">Ítems para considerar en las auditorías internas de seguimiento</p>
                          )}
                          {[...lista.items.filter((it) => it.bloque === 'seguimiento'), ...lista.items.filter((it) => it.bloque !== 'seguimiento')].map((it, idx, arr) => it.es_seccion ? (
                            <p key={it.id} className={`pt-1 text-[11px] font-semibold text-slate-600 dark:text-slate-300 ${idx > 0 && arr[idx - 1].bloque === 'seguimiento' && it.bloque !== 'seguimiento' ? 'mt-2 border-t border-slate-200 pt-2 dark:border-slate-700' : ''}`}>{it.codigo} {it.titulo}</p>
                          ) : (
                            <div key={it.id} className={`grid grid-cols-12 items-center gap-1 text-[11px] ${idx > 0 && arr[idx - 1].bloque === 'seguimiento' && it.bloque !== 'seguimiento' ? 'mt-2 border-t border-slate-200 pt-2 dark:border-slate-700' : ''}`}>
                              <button type="button" onClick={() => setItemAbierto({ clave, id: it.id })} title="Abrir para redactar o revisar"
                                className={`${modo === 'preparacion' ? 'col-span-8' : 'col-span-5'} flex items-start gap-1 text-left text-slate-600 hover:text-esynapse-600 dark:text-slate-400 dark:hover:text-esynapse-300`}>
                                <Maximize2 className="mt-0.5 h-3 w-3 shrink-0 opacity-60" />
                                <span className="min-w-0">
                                  <span className="line-clamp-3 whitespace-pre-line">{it.codigo} {it.titulo}</span>
                                  {['no_cumple', 'observa'].includes(it.resultado) && (
                                    <span className={`mt-0.5 inline-block rounded px-1 text-[11px] ${it.hallazgo_codigo ? 'bg-slate-500/15 text-slate-600 dark:text-slate-300' : it.motivo_descarte ? 'bg-slate-500/10 text-slate-400' : 'bg-amber-500/15 text-amber-700 dark:text-amber-400'}`}>
                                      {it.hallazgo_codigo ? `→ ${it.hallazgo_codigo}` : it.motivo_descarte ? 'sin hallazgo' : 'pendiente de clasificar'}
                                    </span>
                                  )}
                                </span>
                              </button>
                              <input key={`dr-${it.id}-${it.documento_referencia || ''}`} disabled={!(edDocs || edEjec)} defaultValue={it.documento_referencia} placeholder="doc. ref."
                                onBlur={(e) => { if (e.target.value !== (it.documento_referencia || '')) accion(() => api.auditorias.evaluarItem(detalle.id, { item_id: it.id, documento_referencia: e.target.value })) }}
                                className={`input-esynapse ${modo === 'preparacion' ? 'col-span-4' : 'col-span-2'} !py-0.5 text-[11px]`} />
                              {modo !== 'preparacion' && (<>
                                <input key={`ev-${it.id}-${it.evidencia || ''}`} disabled={!edEjec} defaultValue={it.evidencia} placeholder="evaluación / evidencia"
                                  onBlur={(e) => { if (e.target.value !== (it.evidencia || '')) accion(() => api.auditorias.evaluarItem(detalle.id, { item_id: it.id, evidencia: e.target.value })) }}
                                  className="input-esynapse col-span-3 !py-0.5 text-[11px]" />
                                <select disabled={!edEjec} value={it.resultado}
                                  onChange={(e) => accion(() => api.auditorias.evaluarItem(detalle.id, { item_id: it.id, resultado: e.target.value }))}
                                  className={`input-esynapse col-span-2 !py-0.5 text-[11px] font-medium ${COLOR_RESULTADO[it.resultado]}`}>
                                  {RESULTADOS.map(([v, n]) => <option key={v} value={v}>{n}</option>)}
                                </select>
                              </>)}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )
                })}
      {(detalle.listas || []).length === 0 && !edDocs && <p className="text-xs text-slate-400">No se preparó lista de verificación (es opcional).</p>}
    </div>
  )

  // Ítems de la lista evaluados No cumple / Observación que aún no tienen
  // decisión: registrar hallazgo, sumarlos a uno existente o descartarlos.
  const renderPendientes = (editable) => {
    const pend = detalle.pendientes_clasificar || []
    if (!pend.length) return null
    const sel = pend.filter((x) => pendSel.includes(x.id))
    const marcar = (id) => setPendSel((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]))
    const registrar = () => {
      const base = sel.length ? sel : []
      setHallModal({
        modo: 'nuevo', items: base,
        h: {
          tipo: TIPO_SUGERIDO[base[0]?.resultado] || 'nc_menor',
          requisito: base.map((x) => x.referencia || `${NORMA_CORTA[x.norma] || x.norma} ${x.codigo}`).join(', '),
          descripcion: base.map((x) => x.evidencia).filter(Boolean).join('\n\n'),
        },
      })
    }
    const descartar = async () => {
      const motivo = await confirmar({
        titulo: 'No genera hallazgo', textoConfirmar: 'Descartar',
        mensaje: `${sel.length} ítem(s) evaluados como No cumple u Observación no generarán hallazgo.`,
        entrada: { etiqueta: 'Motivo', placeholder: 'Ej.: la evidencia no lo sustenta; ya está cubierto por otro hallazgo', multilinea: true, obligatorio: true },
      })
      if (motivo === null) return
      await accion(async () => { await api.auditorias.descartarItems(detalle.id, sel.map((x) => x.id), motivo); setPendSel([]) })
    }
    const sumar = async (hallazgoId) => {
      if (!hallazgoId) return
      await accion(async () => { await api.auditorias.vincularItems(detalle.id, Number(hallazgoId), sel.map((x) => x.id)); setPendSel([]) })
    }
    return (
      <div className="space-y-1.5 rounded-lg border border-amber-500/40 bg-amber-500/5 p-2">
        <p className="text-[11px] font-semibold text-amber-700 dark:text-amber-400">
          Pendientes de clasificar ({pend.length}) · ítems de la lista evaluados como No cumple u Observación
        </p>
        {pend.map((x) => (
          <label key={x.id} className="flex cursor-pointer items-start gap-2 rounded px-1 py-1 text-xs hover:bg-amber-500/10">
            {editable && <input type="checkbox" className="mt-0.5 h-3.5 w-3.5 accent-esynapse-600" checked={pendSel.includes(x.id)} onChange={() => marcar(x.id)} />}
            <span className="min-w-0 flex-1">
              <span className="font-mono font-medium">{NORMA_CORTA[x.norma] || x.norma} {x.codigo}</span>
              <span className={`ml-1 font-medium ${COLOR_RESULTADO[x.resultado]}`}>{x.resultado === 'no_cumple' ? 'No cumple' : 'Observación'}</span>
              <span className="block truncate text-slate-500 dark:text-slate-400">{x.evidencia || 'sin evidencia registrada'}</span>
            </span>
          </label>
        ))}
        {editable && (
          <div className="flex flex-wrap items-center gap-2 border-t border-amber-500/20 pt-1.5">
            <span className="text-[11px] text-slate-500 dark:text-slate-400">{sel.length ? `${sel.length} seleccionado(s):` : 'Selecciona uno o varios ítems para decidir.'}</span>
            <button disabled={!sel.length} onClick={registrar} className="btn-primary !py-1 text-xs disabled:opacity-40"><Plus className="h-3.5 w-3.5" /> Registrar como hallazgo</button>
            {(detalle.hallazgos || []).length > 0 && (
              <select disabled={!sel.length} value="" onChange={(e) => sumar(e.target.value)} className="input-esynapse w-52 !py-1 text-xs disabled:opacity-40">
                <option value="">Sumar a hallazgo existente…</option>
                {detalle.hallazgos.map((h) => <option key={h.id} value={h.id}>{h.codigo} · {h.tipo_display}</option>)}
              </select>
            )}
            <button disabled={!sel.length} onClick={descartar} className="btn-secondary !py-1 text-xs disabled:opacity-40">No genera hallazgo</button>
          </div>
        )}
      </div>
    )
  }

  const renderHallazgos = (editable, consolidar = false) => (
    <div className="space-y-2 rounded-lg border border-slate-200 p-3 dark:border-slate-800">
      <div className="flex items-center justify-between">
        <p className="flex items-center gap-1 text-xs font-semibold text-slate-500 dark:text-slate-400">
          <AlertTriangle className="h-3.5 w-3.5" /> Hallazgos <SoloLectura cuando={editable || !puedeEditar} texto="Los hallazgos ya se comunicaron o la etapa no está abierta" /></p>
        {editable && tienePermiso('auditorias', 'crear') && (
          <button onClick={() => setHallModal({ modo: 'nuevo' })} className="btn-secondary !py-1 text-xs"><Plus className="h-3.5 w-3.5" /> Registrar hallazgo</button>
        )}
      </div>
      {renderPendientes(editable)}
      {(detalle.hallazgos || []).map((h) => (
        <div key={h.id} className="rounded-lg border border-slate-100 px-2 py-1.5 text-xs dark:border-slate-800/60">
          <div className="flex flex-wrap items-center gap-1">
            <span className="font-mono font-medium">{h.codigo}</span> · <span className="font-medium">{h.tipo_display}</span>
            {h.requisito && <span className="text-slate-400">· {h.requisito}</span>}
            {h.tratamiento_display && <span className="rounded bg-slate-500/15 px-1 py-0.5 text-[11px] text-slate-600 dark:text-slate-300">→ {h.tratamiento_display}</span>}
            <span className="ml-auto flex gap-3">
              {editable && consolidar ? (<>
                <button onClick={() => setHallModal({ modo: 'editar', h })} className="text-esynapse-500 hover:underline">editar</button>
                <button onClick={() => descartarHallazgo(h)} className="text-red-500 hover:underline">descartar</button>
              </>) : (
                <button onClick={() => setHallModal({ modo: 'ver', h })} className="text-esynapse-500 hover:underline">ver</button>
              )}
            </span>
          </div>
          <p className="line-clamp-2 whitespace-pre-line text-slate-500 dark:text-slate-400">{h.descripcion}</p>
          {(h.items || []).length > 0 && (
            <p className="mt-0.5 text-[11px] text-slate-500 dark:text-slate-400">Origen: {h.items.map((x) => `${NORMA_CORTA[x.norma] || x.norma} ${x.codigo}`).join(' · ')}</p>
          )}
        </div>
      ))}
      {(detalle.hallazgos || []).length === 0 && <p className="text-xs text-slate-400">Sin hallazgos.</p>}
    </div>
  )

  const renderActa = (tipo) => {
    const reg = (detalle.actas || []).find((x) => x.tipo === tipo)
    const editable = tipo === 'apertura' ? edAper : edCierre
    const [s2, s3, s4] = SECCIONES_ACTA[tipo]
    const campos = [['contenido', s2], ['seccion3', s3], ['observaciones_auditado', s4]]
    const setPart = (i, campo, valor) => setActaForm({ ...actaForm, participantes: actaForm.participantes.map((x, j) => (j === i ? { ...x, [campo]: valor } : x)) })
    return (
      <div className="space-y-2 rounded-lg border border-slate-200 p-3 dark:border-slate-800">
        <div className="flex items-center justify-between">
          <p className="flex items-center gap-2 text-xs font-semibold text-slate-500 dark:text-slate-400">
            {tipo === 'apertura' ? 'Acta de reunión de apertura' : 'Acta de reunión de cierre'}
            <SoloLectura cuando={editable || !puedeEditar} texto="El acta ya fue registrada" /></p>
          {reg && (
            <button onClick={() => abrirPdf(api.auditorias.actaPdf(detalle.id, tipo))} className="flex items-center gap-1 text-xs text-esynapse-500 hover:underline">
              <FileText className="h-3.5 w-3.5" /> PDF del acta
            </button>
          )}
        </div>
        {editable ? (<>
          <div className="flex items-center gap-3">
            <span className="text-[11px] font-semibold text-slate-500 dark:text-slate-400">1. Participantes</span>
            <button type="button" onClick={() => setActaForm({ ...actaForm, participantes: [
              ...(actaForm.participantes || []),
              ...(detalle.equipo || []).map((m) => ({ nombre: m.nombre, condicion: 'Equipo auditor', cargo: m.cargo || '' })),
            ] })} className="text-xs text-esynapse-500 hover:underline">+ cargar equipo auditor</button>
            <button type="button" onClick={() => setActaForm({ ...actaForm, participantes: [...(actaForm.participantes || []), { nombre: '', condicion: 'Auditado', cargo: '' }] })}
              className="text-xs text-esynapse-500 hover:underline">+ participante</button>
          </div>
          {(actaForm.participantes || []).map((pp, i) => (
            <div key={i} className="grid grid-cols-12 items-center gap-1">
              <input className="input-esynapse col-span-5 !py-1 text-xs" placeholder="Nombre" value={pp.nombre} onChange={(e) => setPart(i, 'nombre', e.target.value)} />
              <select className="input-esynapse col-span-3 !py-1 text-xs" value={pp.condicion} onChange={(e) => setPart(i, 'condicion', e.target.value)}>
                <option>Equipo auditor</option><option>Auditado</option>
              </select>
              <input className="input-esynapse col-span-3 !py-1 text-xs" placeholder="Cargo" value={pp.cargo} onChange={(e) => setPart(i, 'cargo', e.target.value)} />
              <button type="button" onClick={() => setActaForm({ ...actaForm, participantes: actaForm.participantes.filter((_, j) => j !== i) })}
                className="col-span-1 text-xs text-red-500 hover:underline">×</button>
            </div>
          ))}
          {campos.map(([k, etiqueta]) => (
            <textarea key={k} className="input-esynapse !py-1.5 text-xs" rows={2} placeholder={etiqueta}
              value={actaForm[k]} onChange={(e) => setActaForm({ ...actaForm, [k]: e.target.value })} />
          ))}
          <BarraEtapa titulo={tipo === 'apertura' ? 'Cerrar la reunión de apertura' : 'Cerrar la reunión de cierre'}
            nota={tipo === 'apertura' ? 'El acta no se modifica después; con ella inicia la evaluación.' : 'El acta no se modifica después; sigue el informe.'}
            bloqueo={!(actaForm.participantes || []).some((x) => (x.nombre || '').trim()) ? 'Registre los participantes de la reunión.'
              : !actaForm.contenido.trim() ? 'Complete el contenido del acta.' : ''}
            botones={[{ texto: tipo === 'apertura' ? 'Registrar acta de apertura' : 'Registrar acta de cierre', accion: () => registrarActa(tipo) }]} />
        </>) : reg ? (
          <div className="space-y-2 text-xs">
            <div>
              <p className="text-[11px] font-semibold text-slate-500 dark:text-slate-400">1. Participantes</p>
              {(reg.participantes || []).map((pp, i) => <p key={i} className="text-slate-600 dark:text-slate-300">{pp.nombre} · {pp.condicion}{pp.cargo ? ` · ${pp.cargo}` : ''}</p>)}
            </div>
            {campos.map(([k, etiqueta]) => (
              <div key={k}>
                <p className="text-[11px] font-semibold text-slate-500 dark:text-slate-400">{etiqueta}</p>
                <p className="whitespace-pre-line text-slate-600 dark:text-slate-300">{reg[k] || '—'}</p>
              </div>
            ))}
          </div>
        ) : <p className="text-xs text-slate-400">Sin acta registrada.</p>}
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <TituloModulo seccion="Sistema de gestión" titulo="Auditorías internas" descripcion="Programa anual y ejecución de cada auditoría, desde el plan hasta el informe." />
        </div>
        <div className="flex flex-wrap gap-2">
          {puedeAprobarAud && (
            <button onClick={() => { cargarPendientes(); setModalPend(true) }} className="btn-secondary">Cambios pendientes
              {pendientes.length > 0 && <span className="ml-1 inline-flex h-5 min-w-[1.25rem] items-center justify-center rounded-full bg-amber-500 px-1 text-xs font-semibold text-white">{pendientes.length}</span>}
            </button>
          )}
          {tienePermiso('auditorias', 'editar') && (
            <button onClick={() => { cargarMis(); setModalMis(true) }} className="btn-secondary">Mis solicitudes
              {misDevueltas > 0 && <span className="ml-1 inline-flex h-5 min-w-[1.25rem] items-center justify-center rounded-full bg-violet-500 px-1 text-xs font-semibold text-white">{misDevueltas}</span>}
            </button>
          )}
          {tienePermiso('auditorias', 'crear') && (
            <button onClick={() => { setAnioNuevo(new Date().getFullYear()); setError(''); setModalPrograma(true) }} className="btn-secondary">
              <Plus className="h-4 w-4" /> Programa anual
            </button>
          )}
          {tienePermiso('auditorias', 'crear') && (
            <button onClick={() => { setForm({ ...FORM_VACIO, programa: programaActual && programaActual.estado !== 'aprobado' ? String(programaActual.id) : '' }); setError(''); setModalCrear(true) }} className="btn-primary">
              <Plus className="h-4 w-4" /> Nueva auditoría
            </button>
          )}
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <div className="relative">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          <input className="input-esynapse w-64 pl-9" placeholder="Buscar código, área, objetivo…"
            value={buscar} onChange={(e) => setBuscar(e.target.value)} />
        </div>
        <select className="input-esynapse w-52" value={estado} onChange={(e) => setEstado(e.target.value)}>
          <option value="">Todos los estados</option>
          {ESTADOS.map(([v, n]) => <option key={v} value={v}>{n}</option>)}
        </select>
        <div className="ml-auto flex items-center gap-2">
          <select className="input-esynapse w-56" value={programaSel} onChange={(e) => setProgramaSel(e.target.value)} title="Filtra la lista por programa anual">
            <option value="">Todos los programas</option>
            {programas.map((p) => <option key={p.id} value={p.id}>Programa {p.anio} — {ESTADO_PROG[p.estado]?.[0]?.split(' ·')[0] || p.estado}{p.revision ? ` (rev. ${p.revision})` : ''}</option>)}
            <option value="sin">Sin programa (extraordinarias)</option>
          </select>
          {programaActual && (
            <span className={`whitespace-nowrap rounded px-1.5 py-0.5 text-[11px] font-medium ${ESTADO_PROG[programaActual.estado]?.[1] || ''}`}
              title={programaActual.estado === 'aprobado' ? `Aprobado por ${programaActual.aprobado_por_nombre || '—'}` : programaActual.motivo_modificacion ? `Motivo: ${programaActual.motivo_modificacion}` : ''}>
              {ESTADO_PROG[programaActual.estado]?.[0] || programaActual.estado}{programaActual.revision ? ` · rev. ${programaActual.revision}` : ''}
            </span>
          )}
          <button disabled={!programaActual} onClick={() => abrirPdf(api.programasAuditoria.programaPdf(programaActual.id))}
            className="btn-secondary !py-2 text-xs disabled:opacity-40" title="PDF del programa anual de auditorías">
            <FileText className="h-4 w-4" /> PDF
          </button>
          {programaActual && tienePermiso('auditorias', 'editar') && programaActual.estado !== 'aprobado' && (
            <button onClick={() => aprobarPrograma(programaSel)} className="btn-primary !py-2 text-xs"
              title={puedeAprobarAud ? 'Aprobar el programa anual (quedará de solo lectura)' : 'Enviar el programa anual a aprobación'}>
              <CheckCircle2 className="h-4 w-4" /> {puedeAprobarAud ? 'Aprobar programa' : 'Enviar a aprobación'}
            </button>
          )}
          {programaActual && tienePermiso('auditorias', 'editar') && programaActual.estado === 'aprobado' && (
            <button onClick={() => modificarPrograma(programaActual)} className="btn-secondary !py-2 text-xs"
              title="Abrir el programa para cambios (requerirá nueva aprobación)">
              Modificar programa
            </button>
          )}
        </div>
      </div>

      <div className="card-esynapse overflow-x-auto">
        <table className="tabla-sig w-full text-sm">
          <thead>
            <tr className="border-b border-slate-200 text-slate-500 dark:border-slate-800 dark:text-slate-400">
              <th className="px-4 py-3">Código</th>
              <th className="px-4 py-3 text-center">Programa</th>
              <th className="px-4 py-3 text-center">Normas</th>
              <th className="px-4 py-3">Áreas / procesos</th>
              <th className="px-4 py-3 text-center">Modalidad</th>
              <th className="px-4 py-3">Líder</th>
              <th className="px-4 py-3 text-center">Estado</th>
              <th className="px-4 py-3 text-right">Hallazgos</th>
            </tr>
          </thead>
          <tbody>
            {items.map((a) => (
              <tr key={a.id} onClick={() => abrir(a.id)}
                className="cursor-pointer border-b border-slate-100 transition last:border-0 hover:bg-slate-50 dark:border-slate-800/60 dark:hover:bg-slate-800/40">
                <td className="px-4 py-3 font-mono text-xs font-medium">
                  {a.codigo}
                  {a.clase === 'externa' && <span className="ml-1 rounded bg-amber-500/15 px-1 py-0.5 font-sans text-[11px] text-amber-600 dark:text-amber-400">externa</span>}
                </td>
                <td className="px-4 py-3 text-xs text-center">
                  {a.programa_anio
                    ? <span className={`whitespace-nowrap rounded px-1.5 py-0.5 text-[11px] font-medium ${a.programa_estado === 'aprobado' ? 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400' : 'bg-slate-500/15 text-slate-500 dark:text-slate-400'}`} title={a.programa_estado === 'aprobado' ? 'Programa aprobado' : 'Programa en borrador / modificación'}>{a.programa_anio}</span>
                    : <span className="text-slate-400">sin programa</span>}
                </td>
                <td className="px-4 py-3 text-center">
                  <div className="flex flex-wrap gap-1">
                    {(a.normas_display || []).map((n) => (
                      <span key={n} className={`whitespace-nowrap rounded px-1.5 py-0.5 text-[11px] font-medium ${COLOR_NORMA[n] || 'bg-slate-200 text-slate-600'}`}>{n}</span>
                    ))}
                  </div>
                </td>
                <td className="max-w-xs truncate px-4 py-3" title={a.areas_procesos}>{a.areas_procesos || '—'}</td>
                <td className="px-4 py-3 text-slate-500 dark:text-slate-400 text-center">{a.modalidad_display}</td>
                <td className="px-4 py-3 text-slate-500 dark:text-slate-400">{a.auditor_lider_nombre || '—'}</td>
                <td className="px-4 py-3 text-center">
                  <span className={`whitespace-nowrap rounded px-1.5 py-0.5 text-[11px] font-medium ${COLOR_ESTADO[a.estado_display] || 'bg-slate-500/15'}`}>{a.estado_display}</span>
                </td>
                <td className="px-4 py-3 text-xs text-right">{a.hallazgos_count > 0 ? a.hallazgos_count : '—'}</td>
              </tr>
            ))}
            {items.length === 0 && <tr><td colSpan={8} className="px-4 py-8 text-center text-slate-400">Sin auditorías{programaActual ? ` en el Programa ${programaActual.anio}` : ''}</td></tr>}
          </tbody>
        </table>
      </div>

      {/* Crear programa anual */}
      <Modal abierto={modalPrograma} titulo="Nuevo programa anual de auditorías" onCerrar={() => setModalPrograma(false)} ancho="max-w-md">
        <div className="space-y-3">
          <p className="text-xs text-slate-500 dark:text-slate-400">El programa anual agrupa las auditorías del año.</p>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">Año</label>
            <input type="number" className="input-esynapse" value={anioNuevo} onChange={(e) => setAnioNuevo(e.target.value)} />
          </div>
          {error && <p className="rounded-lg bg-red-500/10 px-3 py-2 text-xs text-red-500">{error}</p>}
          <div className="flex justify-end gap-2">
            <button onClick={() => setModalPrograma(false)} className="btn-secondary">Cancelar</button>
            <button onClick={crearPrograma} className="btn-primary">Crear programa</button>
          </div>
        </div>
      </Modal>

      {/* Crear auditoría */}
      <Modal abierto={modalCrear} titulo="Nueva auditoría interna" onCerrar={() => setModalCrear(false)}>
        <form onSubmit={crear} className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">Programa anual{form.tipo === 'programada' && <span className="text-red-500"> *</span>}</label>
              <select className="input-esynapse" value={form.programa} onChange={(e) => setForm({ ...form, programa: e.target.value })}>
                <option value="">{form.tipo === 'programada' ? '— Elige el programa —' : '— Sin programa (extraordinaria) —'}</option>
                {programas.map((p) => <option key={p.id} value={p.id}>{p.anio}{p.estado === 'aprobado' ? ' (aprobado · solo lectura)' : p.estado === 'en_modificacion' ? ' (en modificación)' : ''}</option>)}
              </select>
              {programas.find((p) => String(p.id) === String(form.programa))?.estado === 'aprobado' && (
                <p className="mt-1 text-[11px] text-amber-600 dark:text-amber-400">Este programa está aprobado: no admite nuevas auditorías. Usa "Modificar programa" en la pantalla principal.</p>
              )}
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">Tipo</label>
              <select className="input-esynapse" value={form.tipo} onChange={(e) => setForm({ ...form, tipo: e.target.value })}>
                <option value="programada">Programada</option>
                <option value="extraordinaria">Extraordinaria</option>
              </select>
            </div>
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">Clase</label>
            <div className="flex gap-2">
              {[['interna', 'Interna (la ejecuta el SIG)', 'border-esynapse-500 bg-esynapse-600/15 text-esynapse-600 dark:text-esynapse-300'],
                ['externa', 'Externa (INACAL / certificadora)', 'border-amber-500 bg-amber-500/15 text-amber-600 dark:text-amber-400']].map(([v, n, cls]) => (
                <label key={v} className={`cursor-pointer rounded-lg border px-2.5 py-1.5 text-xs transition ${form.clase === v ? cls : 'border-slate-300 text-slate-600 dark:border-slate-700 dark:text-slate-300'}`}>
                  <input type="radio" className="hidden" checked={form.clase === v} onChange={() => setForm({ ...form, clase: v })} />{n}
                </label>
              ))}
            </div>
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">Normas / criterios</label>
            <div className="flex flex-wrap gap-2">
              {NORMAS.map(([clave, nombre]) => (
                <label key={clave} className={`cursor-pointer rounded-lg border px-2.5 py-1.5 text-xs transition ${
                  form.normas.includes(clave) ? CHIP_NORMA[clave] : 'border-slate-300 text-slate-600 dark:border-slate-700 dark:text-slate-300'}`}>
                  <input type="checkbox" className="hidden" checked={form.normas.includes(clave)}
                    onChange={(e) => {
                      // Sistema Integrado y las normas ISO sueltas se excluyen (evita listas duplicadas).
                      const ISO_SIG = ['iso_9001', 'iso_14001', 'iso_45001']
                      let normas = form.normas.filter((n) => n !== clave)
                      if (e.target.checked) {
                        if (clave === 'sig_integrado') normas = normas.filter((n) => !ISO_SIG.includes(n))
                        if (ISO_SIG.includes(clave)) normas = normas.filter((n) => n !== 'sig_integrado')
                        normas = [...normas, clave]
                      }
                      setForm({ ...form, normas })
                    }} />
                  {nombre}
                </label>
              ))}
            </div>
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">Requisitos a auditar por norma (cláusulas)</label>
            <SelectorRequisitos valor={form.requisitos_por_norma} normas={form.normas} onChange={(v) => setForm({ ...form, requisitos_por_norma: v })} />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">Proceso / áreas a auditar</label>
            <textarea className="input-esynapse" rows={2} value={form.areas_procesos} onChange={(e) => setForm({ ...form, areas_procesos: e.target.value })} />
            <select className="input-esynapse mt-1 !py-1 text-xs" value=""
              onChange={(e) => { const v = e.target.value; if (v) setForm({ ...form, areas_procesos: form.areas_procesos ? `${form.areas_procesos}, ${v}` : v }) }}>
              <option value="">+ Agregar un proceso del catálogo…</option>
              <OpcionesProcesos procesos={catalogoProcesos} />
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">Modalidad</label>
              <select className="input-esynapse" value={form.modalidad} onChange={(e) => setForm({ ...form, modalidad: e.target.value })}>
                {MODALIDADES.map(([v, n]) => <option key={v} value={v}>{n}</option>)}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">Mes programado</label>
              <select className="input-esynapse" value={form.mes_programado} onChange={(e) => setForm({ ...form, mes_programado: e.target.value })}>
                <option value="">— mes —</option>
                {MESES.map((m, i) => <option key={m} value={i + 1}>{m}</option>)}
              </select>
            </div>
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">Observaciones (programa anual)</label>
            <input className="input-esynapse" value={form.observaciones_programa} onChange={(e) => setForm({ ...form, observaciones_programa: e.target.value })} />
          </div>
          {error && <p className="rounded-lg bg-red-500/10 px-3 py-2 text-xs text-red-500">{error}</p>}
          <div className="flex justify-end gap-2">
            <button type="button" onClick={() => setModalCrear(false)} className="btn-secondary">Cancelar</button>
            <button type="submit" className="btn-primary disabled:opacity-40"
              disabled={(form.tipo === 'programada' && !form.programa) || programas.find((p) => String(p.id) === String(form.programa))?.estado === 'aprobado'}>Crear auditoría</button>
          </div>
        </form>
      </Modal>

      {/* Detalle */}
      <Modal abierto={Boolean(detalle)} titulo={detalle ? `${detalle.codigo} — Auditoría interna` : ''} onCerrar={() => setDetalle(null)} panel ancho="max-w-4xl">
        {detalle && (
          <div className="space-y-4 text-sm">
            {/* Pasos del procedimiento: solo se muestra la etapa elegida; las
                anteriores se consultan en solo lectura y las futuras no se abren. */}
            <BarraPasos pasos={NOMBRE_PASO} actual={paso(detalle)} vista={vista} onElegir={setVista} />

            {/* Contexto siempre visible */}
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-lg border border-slate-200 px-3 py-2 text-[11px] text-slate-500 dark:border-slate-800 dark:text-slate-400">
              <span className="font-mono font-semibold text-slate-700 dark:text-slate-200">{detalle.codigo}</span>
              <span>{detalle.programa_anio ? `Programa ${detalle.programa_anio}` : 'Sin programa'}</span>
              {(detalle.normas_display || []).map((n) => (
                <span key={n} className={`whitespace-nowrap rounded px-1.5 py-0.5 text-[11px] font-medium ${COLOR_NORMA[n] || 'bg-slate-200'}`}>{n}</span>
              ))}
              <span>Área: <strong className="font-medium text-slate-700 dark:text-slate-200">{detalle.areas_procesos || '—'}</strong></span>
              <span>Líder: <strong className="font-medium text-slate-700 dark:text-slate-200">{detalle.auditor_lider_nombre || '—'}</strong></span>
              <span className={`ml-auto whitespace-nowrap rounded px-1.5 py-0.5 text-[11px] font-medium ${COLOR_ESTADO[detalle.estado_display] || 'bg-slate-500/15'}`}>{detalle.estado_display}</span>
            </div>

            {vista < paso(detalle) && (
              <div className="flex items-center gap-2 rounded-lg bg-slate-500/10 px-3 py-2 text-xs text-slate-600 dark:text-slate-300">
                <Lock className="h-3.5 w-3.5" /> Consultando una etapa cerrada · solo lectura
                <button onClick={() => setVista(paso(detalle))} className="ml-auto text-esynapse-500 hover:underline">Volver a la etapa actual</button>
              </div>
            )}

            {/* 1. Plan de auditoría (incluye los datos del programa anual y el equipo auditor) */}
            {vista === 0 && (<>
            {/* Programa anual: clase, requisitos por norma, meses y observaciones */}
            <div className="space-y-2 rounded-lg border border-slate-200 p-3 dark:border-slate-800">
              <div className="flex flex-wrap items-center gap-2">
                <p className="text-xs font-semibold text-slate-500 dark:text-slate-400">Programa anual</p>
                <SoloLectura cuando={edProg || !puedeEditar} texto="Etapa cerrada: el plan ya fue aprobado" />
                {!edProg ? (
                  <span className="rounded bg-slate-500/15 px-1.5 py-0.5 text-[11px] font-medium text-slate-600 dark:text-slate-300"
                    title={!et.programa ? 'Ya planificada: el código figura en el plan, no se cambia de programa' : undefined}>
                    {detalle.programa_anio ? `Programa ${detalle.programa_anio}` : 'Sin programa'}</span>
                ) : (
                  <select className="input-esynapse w-44 !py-0.5 text-[11px]" value={detalle.programa || ''} title="Mover la auditoría a otro programa anual (el código toma el año del programa destino)"
                    onChange={(e) => accion(() => api.auditorias.actualizar(detalle.id, { programa: e.target.value ? Number(e.target.value) : null }))}>
                    <option value="">Sin programa (extraordinaria)</option>
                    {programas.filter((p) => p.estado !== 'aprobado' || String(p.id) === String(detalle.programa)).map((p) => (
                      <option key={p.id} value={p.id}>Programa {p.anio}{p.estado === 'aprobado' ? ' (aprobado)' : ''}</option>
                    ))}
                  </select>
                )}
                <span className={`whitespace-nowrap rounded px-1.5 py-0.5 text-[11px] font-medium ${detalle.clase === 'externa' ? 'bg-amber-500/15 text-amber-600 dark:text-amber-400' : 'bg-esynapse-600/15 text-esynapse-600 dark:text-esynapse-300'}`}>
                  {detalle.clase === 'externa' ? 'Auditoría externa' : 'Auditoría interna'}
                </span>
                <span className="ml-auto text-[11px] text-slate-500 dark:text-slate-400">
                  Programado: <strong>{detalle.mes_programado ? MESES[detalle.mes_programado - 1] : '—'}</strong>
                  {detalle.mes_reprogramado && <> · Reprogramado: <strong>{MESES[detalle.mes_reprogramado - 1]}</strong></>}
                  {detalle.fecha_inicio && <> · Ejecutado: <strong>{MESES[Number(detalle.fecha_inicio.slice(5, 7)) - 1]}</strong></>}
                </span>
              </div>
              {detalle.programa_estado === 'aprobado' && (
                <p className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-3 py-1.5 text-[11px] text-emerald-700 dark:text-emerald-300">
                  Programa anual {detalle.programa_anio} aprobado: proceso, clase, cláusulas, mes programado y observaciones son de solo lectura. Reprogramar sí está permitido (queda en la fila "Reprogramado"). Para cambiar el programa, usa "Modificar programa".
                </p>
              )}
              <SelectorRequisitos valor={gen.requisitos_por_norma} disabled={!edProg} normas={detalle.normas_aplicables || []}
                onChange={(v) => setGen({ ...gen, requisitos_por_norma: v })} />
              <input className="input-esynapse" placeholder="Observaciones (programa anual)" disabled={!edProg}
                value={gen.observaciones_programa} onChange={(e) => setGen({ ...gen, observaciones_programa: e.target.value })} />
              {puedeReprog && (
                <div className="grid grid-cols-12 items-end gap-2">
                  <select className="input-esynapse col-span-3 !py-1.5 text-xs" value={reprog.mes} onChange={(e) => setReprog({ ...reprog, mes: e.target.value })}>
                    <option value="">Reprogramar a…</option>
                    {MESES.map((m, i) => <option key={m} value={i + 1}>{m}</option>)}
                  </select>
                  <input className="input-esynapse col-span-7 !py-1.5 text-xs" placeholder="Motivo de la reprogramación" value={reprog.motivo}
                    onChange={(e) => setReprog({ ...reprog, motivo: e.target.value })} />
                  <button disabled={!reprog.mes || !reprog.motivo.trim()}
                    onClick={() => accion(async () => { await api.auditorias.reprogramar(detalle.id, { mes_programado: reprog.mes, motivo: reprog.motivo }); setReprog({ mes: '', motivo: '' }) })}
                    className="btn-secondary col-span-2 !px-2 !py-1.5 text-xs disabled:opacity-40">Reprogramar</button>
                </div>
              )}
              {detalle.reprogramada && detalle.motivo_reprogramacion && (
                <p className="text-[11px] text-amber-600 dark:text-amber-400">Reprogramada: {detalle.motivo_reprogramacion}</p>
              )}
            </div>

            {/* Datos generales / planificación */}
            <div className="space-y-2 rounded-lg border border-slate-200 p-3 dark:border-slate-800">
              <div className="flex items-center justify-between">
                <p className="flex items-center gap-2 text-xs font-semibold text-slate-500 dark:text-slate-400">Plan de auditoría
                  <SoloLectura cuando={edPlan || !puedeEditar} texto="Etapa cerrada: el plan ya fue aprobado" /></p>
                <button onClick={() => abrirPdf(api.auditorias.planPdf(detalle.id))} className="text-xs text-esynapse-500 hover:underline flex items-center gap-1">
                  <FileText className="h-3.5 w-3.5" /> PDF del plan
                </button>
              </div>
              {faltanDatosEmpresa.length > 0 && (
                <p className="rounded-lg bg-amber-500/10 px-3 py-2 text-[11px] text-amber-700 dark:text-amber-400">
                  El bloque "Datos del laboratorio" del PDF saldrá incompleto: falta {faltanDatosEmpresa.join(', ')}.
                  Se completa una sola vez en <Link to="/configuracion" className="font-semibold underline">Configuración → Identidad</Link>.
                </p>
              )}
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="mb-1 block text-[11px] font-medium text-slate-500 dark:text-slate-400">Auditoría interna N°</label>
                  <input className="input-esynapse font-mono" value={detalle.codigo} disabled readOnly />
                </div>
                <div>
                  <label className="mb-1 block text-[11px] font-medium text-slate-500 dark:text-slate-400">Fecha de elaboración del plan</label>
                  <input type="date" className="input-esynapse" disabled={!edPlan} title="Si se deja vacía, se toma la fecha en que se planifica la auditoría"
                    value={gen.fecha_elaboracion_plan} onChange={(e) => setGen({ ...gen, fecha_elaboracion_plan: e.target.value })} />
                </div>
              </div>
              <textarea className="input-esynapse" rows={2} placeholder="Objetivo" disabled={!edPlan}
                value={gen.objetivo} onChange={(e) => setGen({ ...gen, objetivo: e.target.value })} />
              <textarea className="input-esynapse" rows={2} placeholder="Alcance" disabled={!edPlan}
                value={gen.alcance} onChange={(e) => setGen({ ...gen, alcance: e.target.value })} />
              <div>
                <p className="mb-1 text-[11px] text-slate-500 dark:text-slate-400">
                  <span className="font-semibold">Criterios (normas):</span>{' '}
                  {(detalle.normas_display || []).length
                    ? (detalle.normas_display || []).join(' · ')
                    : 'sin normas seleccionadas'}
                </p>
                <div>
                  <input className="input-esynapse" placeholder="Otro(s) criterios: p. ej. ISO 50001, ISO/IEC 27001, ISO 31000" disabled={!edPlan}
                    title="Normas o requisitos adicionales a auditar. Se imprime en la casilla OTRO(S) del plan"
                    value={gen.criterios} onChange={(e) => setGen({ ...gen, criterios: e.target.value })} />
                </div>
              </div>
              <textarea className="input-esynapse" rows={2} placeholder="Documentos de referencia (manual, procedimientos, directrices…)" disabled={!edPlan}
                value={gen.documentos_referencia} onChange={(e) => setGen({ ...gen, documentos_referencia: e.target.value })} />

              {/* Cronograma de entrevistas (sección 4 del plan de auditoría) */}
              <div className="rounded-lg border border-slate-100 p-2 dark:border-slate-800/60">
                <div className="mb-1 flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-500 dark:text-slate-400">4. Cronograma de entrevistas</span>
                  {edPlan && (
                    <button type="button" onClick={() => setGen({ ...gen, cronograma_entrevistas: [...(gen.cronograma_entrevistas || []), { ...CRONO_VACIO, modalidad: gen.modalidad || 'presencial' }] })}
                      className="text-xs text-esynapse-500 hover:underline">+ entrevista</button>
                  )}
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[980px] border-collapse text-[11px]">
                    <thead>
                      <tr className="bg-[#1E3A5C] text-white">
                        <th rowSpan={2} className="border border-slate-600 px-1 py-1">Fecha</th>
                        <th rowSpan={2} className="border border-slate-600 px-1 py-1">Hora</th>
                        <th rowSpan={2} className="border border-slate-600 px-1 py-1">Proceso / área a evaluar</th>
                        <th colSpan={4} className="border border-slate-600 px-1 py-1">Requisitos</th>
                        <th rowSpan={2} className="border border-slate-600 px-1 py-1">Modalidad de auditoría</th>
                        <th rowSpan={2} className="border border-slate-600 px-1 py-1">TIC</th>
                        <th rowSpan={2} className="border border-slate-600 px-1 py-1">Auditor / experto técnico</th>
                        <th rowSpan={2} className="border border-slate-600 px-1 py-1">Auditado</th>
                        {edPlan && <th rowSpan={2} className="border border-slate-600 px-1 py-1" />}
                      </tr>
                      <tr className="bg-[#1E3A5C] text-white">
                        {REQ_CRONO.map(([, n]) => <th key={n} className="border border-slate-600 px-1 py-1 font-medium">{n}</th>)}
                      </tr>
                    </thead>
                    <tbody>
                      {(gen.cronograma_entrevistas || []).map((e, i) => {
                        const dis = !edPlan
                        const celda = 'input-esynapse !rounded-none !border-0 !bg-transparent !px-1 !py-1 text-[11px] w-full'
                        return (
                          <tr key={i} className="border-b border-slate-200 dark:border-slate-800">
                            <td className="border border-slate-200 dark:border-slate-800"><input type="date" disabled={dis} className={`${celda} min-w-[9rem]`} title="Elegir fecha" value={e.fecha || ''} onChange={(ev) => setCrono(i, 'fecha', ev.target.value)} /></td>
                            <td className="border border-slate-200 dark:border-slate-800"><input type="time" disabled={dis} className={`${celda} min-w-[6.5rem]`} title="Elegir hora" value={e.hora || ''} onChange={(ev) => setCrono(i, 'hora', ev.target.value)} /></td>
                            <td className="border border-slate-200 dark:border-slate-800"><input disabled={dis} className={celda} placeholder="Proceso / área" value={e.area || ''} onChange={(ev) => setCrono(i, 'area', ev.target.value)} /></td>
                            {REQ_CRONO.map(([k]) => {
                              const clave = k.replace('req_', 'iso_')
                              const aplica = normasCrono.has(clave)
                              return (
                                <td key={k} className={`border border-slate-200 dark:border-slate-800 ${!aplica ? 'bg-slate-100/60 dark:bg-slate-800/40' : ''}`}>
                                  <button type="button" disabled={dis || !aplica}
                                    onClick={() => setPickCrono({ i, k, clave })}
                                    title={!aplica ? 'Norma fuera del alcance de esta auditoría' : 'Elegir cláusulas'}
                                    className={`w-full px-1 py-1 text-left text-[11px] ${e[k] ? 'text-slate-800 dark:text-slate-100' : 'text-slate-400'} disabled:cursor-not-allowed`}>
                                    {!aplica ? '—' : (e[k] || 'elegir…')}
                                  </button>
                                </td>
                              )
                            })}
                            <td className="border border-slate-200 dark:border-slate-800">
                              <select disabled={dis} className={celda} value={e.modalidad || 'presencial'} onChange={(ev) => setCrono(i, 'modalidad', ev.target.value)}>
                                <option value="presencial">In situ</option><option value="remota">Remoto</option><option value="hibrido">Híbrido</option>
                              </select>
                            </td>
                            <td className="border border-slate-200 dark:border-slate-800"><input disabled={dis} className={celda} placeholder="Teams, Zoom…" value={e.tic || ''} onChange={(ev) => setCrono(i, 'tic', ev.target.value)} /></td>
                            <td className="border border-slate-200 dark:border-slate-800"><CampoSugerencias compacto disabled={dis} className={celda} placeholder="Auditor" value={e.auditor || ''} opciones={(detalle.equipo || []).map((m) => m.nombre)} onChange={(v) => setCrono(i, 'auditor', v)} /></td>
                            <td className="border border-slate-200 dark:border-slate-800"><CampoSugerencias compacto disabled={dis} className={celda} placeholder="Auditado" value={e.auditado || ''} opciones={usuarios.map((u) => u.nombre_completo)} onChange={(v) => setCrono(i, 'auditado', v)} /></td>
                            {!dis && (
                              <td className="border border-slate-200 text-center dark:border-slate-800">
                                <button type="button" onClick={() => setGen({ ...gen, cronograma_entrevistas: gen.cronograma_entrevistas.filter((_, j) => j !== i) })}
                                  className="px-1 text-red-500 hover:underline">×</button>
                              </td>
                            )}
                          </tr>
                        )
                      })}
                      {(gen.cronograma_entrevistas || []).length === 0 && (
                        <tr><td colSpan={12} className="px-2 py-3 text-center text-slate-400">Sin entrevistas programadas. Usa “+ entrevista”.</td></tr>
                      )}
                    </tbody>
                  </table>
                </div>
                <p className="mt-1 text-[11px] text-slate-500 dark:text-slate-400">Se guarda con “Guardar datos”. Auditor sugiere el equipo auditor; auditado sugiere el personal registrado.</p>
              </div>

              <div className="grid grid-cols-2 gap-2">
              </div>
              <textarea className="input-esynapse" rows={2} placeholder="Observaciones del plan" disabled={!edPlan}
                value={gen.observaciones_plan} onChange={(e) => setGen({ ...gen, observaciones_plan: e.target.value })} />

              {edPlan && (
                <div className="flex justify-end gap-2">
                  <button onClick={() => accion(guardarGenerales)} className="btn-secondary !py-1.5 text-xs">Guardar datos</button>
                </div>
              )}
              {detalle.fecha_aprobacion_plan && (
                <p className="text-[11px] text-emerald-600 dark:text-emerald-400">Plan aprobado por {detalle.plan_aprobado_por_nombre || '—'} el {fechaHora(detalle.fecha_aprobacion_plan)}.</p>
              )}
            </div>

            {/* Equipo auditor */}
            <div className="space-y-2 rounded-lg border border-slate-200 p-3 dark:border-slate-800">
              <p className="flex items-center gap-1 text-xs font-semibold text-slate-500 dark:text-slate-400"><Users className="h-3.5 w-3.5" /> Equipo auditor <SoloLectura cuando={edPlan || !puedeEditar} texto="Etapa cerrada: el plan ya fue aprobado" /></p>
              {(detalle.equipo || []).map((m) => (
                <div key={m.id} className="flex items-center justify-between text-xs">
                  <span><strong>{m.rol_display}:</strong> {m.nombre} {m.cargo && `· ${m.cargo}`}</span>
                  {edPlan && (
                    <button onClick={() => accion(() => api.auditorias.quitarIntegrante(detalle.id, m.id))} className="text-red-500 hover:underline">quitar</button>
                  )}
                </div>
              ))}
              {(detalle.equipo || []).length === 0 && <p className="text-xs text-slate-400">Sin integrantes aún.</p>}
              {edPlan && !hayLider && (
                <p className="text-[11px] text-amber-600 dark:text-amber-400">Agregue al auditor líder con el rol "Auditor líder": es quien figura en el plan, las actas y el informe. Sin él no se aprueba el plan.</p>
              )}
              {edPlan && (
                <div className="grid grid-cols-12 items-end gap-2">
                  <select className="input-esynapse col-span-3 !py-1.5 text-xs" value={equipoForm.rol}
                    onChange={(e) => setEquipoForm({ ...equipoForm, rol: e.target.value, cargo: cargoSugerido(equipoForm, e.target.value) })}>
                    {ROLES.map(([v, n]) => <option key={v} value={v} disabled={v === 'lider' && hayLider}>{n}{v === 'lider' && hayLider ? ' (ya asignado)' : ''}</option>)}
                  </select>
                  <select className="input-esynapse col-span-4 !py-1.5 text-xs" value={equipoForm.usuario}
                    onChange={(e) => { const u = usuarios.find((x) => String(x.id) === e.target.value); setEquipoForm({ ...equipoForm, usuario: e.target.value, nombre_externo: '', cargo: u?.cargo || '' }) }}>
                    <option value="">— Interno —</option>
                    {usuarios.map((u) => <option key={u.id} value={u.id}>{u.nombre_completo}</option>)}
                  </select>
                  <input className="input-esynapse col-span-3 !py-1.5 text-xs" placeholder="o externo" value={equipoForm.nombre_externo}
                    onChange={(e) => { const f = { ...equipoForm, nombre_externo: e.target.value, usuario: '' }; setEquipoForm({ ...f, cargo: cargoSugerido(f, f.rol) }) }} />
                  <input className="input-esynapse col-span-10 !py-1.5 text-xs" placeholder="Cargo (interno: el registrado; externo: su rol en la auditoría)" value={equipoForm.cargo}
                    onChange={(e) => setEquipoForm({ ...equipoForm, cargo: e.target.value })} />
                  <button disabled={!equipoForm.usuario && !equipoForm.nombre_externo}
                    onClick={() => accion(async () => {
                      const d = { ...equipoForm }; if (!d.usuario) delete d.usuario
                      const r = await api.auditorias.agregarIntegrante(detalle.id, d)
                      setAviso(r?.aviso || '')
                      setEquipoForm({ usuario: '', nombre_externo: '', rol: 'auditor', cargo: '' })
                    })}
                    className="btn-secondary col-span-2 !px-2 !py-1.5 text-xs"><Plus className="h-3.5 w-3.5" /></button>
                </div>
              )}
              {aviso && (
                <div className="flex items-start gap-2 rounded-lg border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-xs text-amber-700 dark:text-amber-300">
                  <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                  <span>{aviso}</span>
                  <button onClick={() => setAviso('')} className="ml-auto text-amber-600 hover:underline dark:text-amber-400">cerrar</button>
                </div>
              )}
            </div>

            {edPlan && (
              <BarraEtapa titulo="Cerrar la planificación: aprobar y comunicar el plan"
                nota="Lo aprueba el auditor líder (o quien tiene permiso de aprobar). El plan, el equipo y el cronograma quedan de solo lectura."
                bloqueo={!(gen.objetivo || '').trim() || !(gen.alcance || '').trim() ? 'Defina el objetivo y el alcance de la auditoría.'
                  : !hayLider ? 'Agregue al auditor líder en el Equipo auditor.'
                    : !(gen.cronograma_entrevistas || []).some((e) => e.fecha || e.area) ? 'Registre al menos una entrevista en el cronograma.' : ''}
                botones={[{ texto: 'Aprobar y comunicar plan', accion: aprobarPlan }]} />
            )}
            </>)}

            {/* 2. Documentos de trabajo */}
            {vista === 1 && (
              <div className="space-y-2 rounded-lg border border-slate-200 p-3 dark:border-slate-800">
                <p className="flex items-center gap-2 text-xs font-semibold text-slate-500 dark:text-slate-400">Documentos de trabajo
                  <SoloLectura cuando={edDocs || !puedeEditar} texto="Etapa cerrada: la ejecución ya inició" /></p>
                <p className="text-[11px] text-slate-500 dark:text-slate-400">
                  La lista de verificación es opcional. Aquí se preparan sus ítems y el documento de referencia de cada uno;
                  la evaluación se registra en la ejecución, después de la reunión de apertura.
                </p>
                {renderListas('preparacion')}
                {edDocs && (
                  <BarraEtapa titulo="Cerrar la preparación de los documentos de trabajo"
                    nota="Sigue la reunión de apertura; la lista se evalúa después de su acta."
                    botones={[{ texto: 'Iniciar ejecución', accion: iniciarEjecucion }]} />
                )}
              </div>
            )}

            {/* 3. Reunión de apertura */}
            {vista === 2 && renderActa('apertura')}

            {/* 4. Ejecución: evaluación y hallazgos */}
            {vista === 3 && (<>
              <div className="space-y-2 rounded-lg border border-slate-200 p-3 dark:border-slate-800">
                <p className="flex items-center gap-2 text-xs font-semibold text-slate-500 dark:text-slate-400">Evaluación de la lista de verificación
                  <SoloLectura cuando={edEjec || !puedeEditar} texto="Etapa cerrada: la ejecución terminó" /></p>
                {renderListas('evaluacion')}
              </div>
              {renderHallazgos(edEjec)}
              {edEjec && (
                <BarraEtapa titulo="Cerrar la ejecución"
                  nota="La evaluación de la lista queda de solo lectura; sigue la consolidación de los hallazgos."
                  botones={[{ texto: 'Terminar ejecución', accion: terminarEjecucion }]} />
              )}
            </>)}

            {/* 5. Conclusiones: consolidar y clasificar hallazgos */}
            {vista === 4 && (<>
              <p className="text-[11px] text-slate-500 dark:text-slate-400">
                El equipo auditor revisa que cada hallazgo esté sustentado en evidencia objetiva, lo clasifica y determina el grado de conformidad.
                Lo validado aquí es lo que se presenta en la reunión de cierre.
              </p>
              {renderHallazgos(edConc, true)}
              <div className="space-y-2 rounded-lg border border-slate-200 p-3 dark:border-slate-800">
                <p className="flex items-center gap-2 text-xs font-semibold text-slate-500 dark:text-slate-400">Conclusiones de la auditoría
                  <SoloLectura cuando={edConc || !puedeEditar} texto="Etapa cerrada: ya se presentaron en la reunión de cierre" /></p>
                <textarea className="input-esynapse" rows={3} disabled={!edConc} placeholder="Grado de conformidad del SIG respecto a los criterios de auditoría"
                  value={informe.conclusiones} onChange={(e) => setInforme({ ...informe, conclusiones: e.target.value })} />
              </div>
              {edConc && (
                <BarraEtapa titulo="Cerrar la consolidación: validar los hallazgos"
                  nota="Los hallazgos y las conclusiones quedan listos para la reunión de cierre."
                  bloqueo={(detalle.pendientes_clasificar || []).length > 0
                    ? `Quedan ${detalle.pendientes_clasificar.length} ítem(s) de la lista evaluados como No cumple u Observación sin clasificar.`
                    : !(informe.conclusiones || '').trim() ? 'Escriba las conclusiones de la auditoría.' : ''}
                  botones={[{ texto: 'Validar hallazgos', accion: validarHallazgos }]} />
              )}
            </>)}

            {/* 6. Reunión de cierre */}
            {vista === 5 && (<>
              {renderHallazgos(false)}
              {renderActa('cierre')}
            </>)}

            {/* 7. Informe y entrega al Gerente SIG */}
            {vista === 6 && (
              <div className="space-y-2 rounded-lg border border-violet-500/30 bg-violet-500/5 p-3">
                <div className="flex items-center justify-between">
                  <p className="flex items-center gap-1 text-xs font-semibold text-violet-600 dark:text-violet-400"><FileText className="h-3.5 w-3.5" /> Informe de auditoría <SoloLectura cuando={edInf || !puedeEditar} texto="Auditoría cerrada" /></p>
                  <button onClick={() => abrirPdf(api.auditorias.informePdf(detalle.id))} className="text-xs text-violet-600 dark:text-violet-400 hover:underline flex items-center gap-1">
                    <FileText className="h-3.5 w-3.5" /> PDF del informe
                  </button>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <input className="input-esynapse" placeholder="Lugar donde se realizó la auditoría" disabled={!edInf}
                    value={informe.lugar} onChange={(e) => setInforme({ ...informe, lugar: e.target.value })} />
                  <input className="input-esynapse" placeholder="Personas entrevistadas" disabled={!edInf}
                    value={informe.personas_entrevistadas} onChange={(e) => setInforme({ ...informe, personas_entrevistadas: e.target.value })} />
                </div>
                <textarea className="input-esynapse" rows={2} placeholder="Fortalezas" disabled={!edInf} value={informe.fortalezas} onChange={(e) => setInforme({ ...informe, fortalezas: e.target.value })} />
                <textarea className="input-esynapse" rows={2} placeholder="Debilidades" disabled={!edInf} value={informe.debilidades} onChange={(e) => setInforme({ ...informe, debilidades: e.target.value })} />
                <div className="rounded-lg bg-slate-500/5 px-3 py-2 text-xs">
                  <p className="mb-0.5 text-[11px] font-semibold text-slate-500 dark:text-slate-400">Conclusiones (validadas en la etapa de conclusiones)</p>
                  <p className="whitespace-pre-line text-slate-700 dark:text-slate-200">{detalle.conclusiones || '—'}</p>
                </div>
                {edInf && (
                  <div className="flex justify-end">
                    <button onClick={() => accion(() => api.auditorias.actualizar(detalle.id, { lugar: informe.lugar, personas_entrevistadas: informe.personas_entrevistadas, fortalezas: informe.fortalezas, debilidades: informe.debilidades }))} className="btn-secondary !py-1.5 text-xs">Guardar informe</button>
                  </div>
                )}
                {edInf && (
                  <BarraEtapa titulo={puedeAprobar ? 'Cerrar la auditoría: entregar el informe' : 'Enviar el cierre de la auditoría a aprobación'}
                    nota="El informe se entrega al Gerente SIG con los registros de la auditoría; todo queda de solo lectura."
                    bloqueo={!(detalle.conclusiones || '').trim() ? 'La auditoría no tiene conclusiones validadas.' : ''}
                    botones={[{ texto: puedeAprobar ? 'Entregar informe y cerrar' : 'Enviar cierre a aprobación', accion: cerrarAuditoria }]} />
                )}
              </div>
            )}

            {/* Cerrada: registros emitidos */}
            {vista === 7 && (
              <div className="space-y-3 rounded-lg border border-emerald-500/30 bg-emerald-500/5 p-3">
                <p className="text-xs text-emerald-700 dark:text-emerald-300">
                  Auditoría cerrada{detalle.fecha_informe ? ` el ${fechaHora(detalle.fecha_informe)}` : ''}. Todos sus registros son de solo lectura.
                  Las no conformidades siguen en Acciones correctivas; las observaciones y oportunidades de mejora, en riesgos y oportunidades.
                </p>
                <div className="flex flex-wrap gap-2">
                  <button onClick={() => abrirPdf(api.auditorias.planPdf(detalle.id))} className="btn-secondary !py-1 text-xs"><FileText className="h-3.5 w-3.5" /> Plan</button>
                  <button onClick={() => abrirPdf(api.auditorias.actaPdf(detalle.id, 'apertura'))} className="btn-secondary !py-1 text-xs"><FileText className="h-3.5 w-3.5" /> Acta de apertura</button>
                  {(detalle.listas || []).map((l) => (
                    <button key={l.id} onClick={() => abrirPdf(api.auditorias.listaPdf(detalle.id, l.norma))} className="btn-secondary !py-1 text-xs"><FileText className="h-3.5 w-3.5" /> Lista {NORMAS.find((n) => n[0] === l.norma)?.[1] || l.norma}</button>
                  ))}
                  <button onClick={() => abrirPdf(api.auditorias.actaPdf(detalle.id, 'cierre'))} className="btn-secondary !py-1 text-xs"><FileText className="h-3.5 w-3.5" /> Acta de cierre</button>
                  <button onClick={() => abrirPdf(api.auditorias.informePdf(detalle.id))} className="btn-secondary !py-1 text-xs"><FileText className="h-3.5 w-3.5" /> Informe</button>
                </div>
                {renderHallazgos(false)}
              </div>
            )}

            {error && <p className="rounded-lg bg-red-500/10 px-3 py-2 text-xs text-red-500">{error}</p>}
          </div>
        )}
      </Modal>

      {/* Ventana de registro / edición / lectura de un hallazgo */}
      {hallModal && detalle && (
        <ModalHallazgo
          inicial={hallModal.h}
          origen={hallModal.items || hallModal.h?.items || []}
          soloLectura={hallModal.modo === 'ver'}
          titulo={hallModal.modo === 'nuevo' ? 'Registrar hallazgo' : `${hallModal.h.codigo} · ${hallModal.h.tipo_display}`}
          onGuardar={async (h) => {
            if (hallModal.modo === 'nuevo') {
              await api.auditorias.registrarHallazgo(detalle.id, { ...h, item_ids: (hallModal.items || []).map((x) => x.id) })
              setPendSel([])
            }
            else await api.auditorias.editarHallazgo(detalle.id, { hallazgo_id: hallModal.h.id, ...h })
            await refrescar()
          }}
          onCerrar={() => setHallModal(null)} />
      )}

      {/* Ventana de edición de un ítem de la lista de verificación */}
      {itemAbierto && detalle && (() => {
        const lista = (detalle.listas || []).find((l) => l.norma === itemAbierto.clave)
        if (!lista) return null
        const ordenados = [...lista.items.filter((x) => x.bloque === 'seguimiento'), ...lista.items.filter((x) => x.bloque !== 'seguimiento')]
        return (
          <ModalItemLista items={ordenados} itemId={itemAbierto.id}
            normaNombre={NORMAS.find((n) => n[0] === itemAbierto.clave)?.[1] || itemAbierto.clave}
            puedeDocRef={edDocs || edEjec} puedeEvaluar={edEjec}
            onGuardar={async (id, cambios) => { await api.auditorias.evaluarItem(detalle.id, { item_id: id, ...cambios }); await refrescar() }}
            onCerrar={() => setItemAbierto(null)} />
        )
      })()}

      {/* Selector de cláusulas para una celda del cronograma de entrevistas */}
      {pickCrono && (
        <ModalClausulas clave={pickCrono.clave}
          valor={(gen.cronograma_entrevistas || [])[pickCrono.i]?.[pickCrono.k] || ''}
          sugeridas={gen.requisitos_por_norma?.[pickCrono.clave] || ''}
          onCerrar={() => setPickCrono(null)}
          onAceptar={(texto) => { setCrono(pickCrono.i, pickCrono.k, texto); setPickCrono(null) }} />
      )}

      {/* Bandeja: cambios pendientes de aprobación (programa anual, cierres de informe) */}
      <Modal abierto={modalPend} titulo="Cambios pendientes de aprobación" onCerrar={() => setModalPend(false)} ancho="max-w-2xl">
        {pendientes.length === 0 ? <p className="py-6 text-center text-sm text-slate-400">No hay cambios pendientes.</p> : (
          <div className="space-y-2">
            {pendientes.map((s) => (
              <div key={s.id} className="flex items-start justify-between gap-3 rounded-lg border border-slate-200 p-3 dark:border-slate-700">
                <div>
                  <p className="text-sm font-medium">{s.resumen || `${s.operacion_display} · ${s.entidad_display}`}</p>
                  <p className="text-xs text-slate-500 dark:text-slate-400">Solicitado por {s.solicitante} · {fechaHora(s.created_at)}</p>
                  {s.payload?.conclusiones && <p className="mt-1 text-xs text-slate-600 dark:text-slate-300"><span className="font-medium">Conclusiones propuestas:</span> {s.payload.conclusiones}</p>}
                </div>
                <div className="flex shrink-0 gap-2">
                  <button onClick={() => resolver(s, 'aprobar')} className="btn-primary !py-1">Aprobar</button>
                  <button onClick={() => resolver(s, 'devolver')} className="btn-secondary !py-1">Devolver</button>
                  <button onClick={() => resolver(s, 'rechazar')} className="btn-danger !py-1">Rechazar</button>
                </div>
              </div>
            ))}
          </div>
        )}
      </Modal>

      <Modal abierto={modalMis} titulo="Mis solicitudes de aprobación" onCerrar={() => setModalMis(false)} ancho="max-w-2xl">
        {misSolic.length === 0 ? <p className="py-6 text-center text-sm text-slate-400">No has enviado solicitudes.</p> : (
          <div className="space-y-2">
            {misSolic.map((s) => {
              const cls = { pendiente: 'bg-amber-500/15 text-amber-600 dark:text-amber-400', aprobada: 'bg-green-500/15 text-green-600 dark:text-green-400', devuelta: 'bg-violet-500/15 text-violet-600 dark:text-violet-400', rechazada: 'bg-red-500/15 text-red-600 dark:text-red-400' }[s.estado] || 'bg-slate-500/15 text-slate-500'
              return (
                <div key={s.id} className="flex items-start justify-between gap-3 rounded-lg border border-slate-200 p-3 dark:border-slate-700">
                  <div>
                    <p className="text-sm font-medium">{s.resumen}</p>
                    <p className="text-xs text-slate-500 dark:text-slate-400">Enviado {fechaHora(s.created_at)}</p>
                    {s.observaciones && <p className="mt-1 text-xs text-slate-600 dark:text-slate-300"><span className="font-medium">Motivo:</span> {s.observaciones}</p>}
                  </div>
                  <div className="flex shrink-0 flex-col items-end gap-2">
                    <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${cls}`}>{s.estado_display}</span>
                    {s.estado === 'devuelta' && <button onClick={() => reenviar(s)} className="btn-primary !py-1">Corregir y reenviar</button>}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </Modal>
    </div>
  )
}

import { useEffect, useState } from 'react'
import Modal from './Modal.jsx'

// Tablas de consulta del procedimiento de Control de Trabajos y Salidas No Conformes (versión 01):
// Tabla N° 1 (Anexo 1) responsabilidades y autoridades, Tabla N° 2 (Anexo 2) niveles de riesgo y acciones.
// Texto fiel al procedimiento; si el procedimiento cambia de versión, se actualiza aquí.

const TABLA1 = [
  {
    cargo: 'Gerente SIG',
    responsabilidades: [
      { texto: 'Decidir sobre la aceptabilidad de un TNC o SNC.' },
      {
        texto: 'Definir la primera respuesta del área administrativa (corrección) frente al reporte de un TNC o SNC y ejecutarla rápidamente.',
        casos: [
          ['Si aún no se ha enviado la documentación:', 'Ordenar la retención del documento.'],
          ['Si ya se envió la documentación:', 'Notificar al cliente y anular el servicio si fuera necesario.'],
        ],
      },
      {
        texto: 'Evaluar participativamente la importancia del TNC o SNC para determinar la necesidad de una acción correctiva.',
        casos: [
          ['Si no amerita solicitar una acción correctiva:', 'Cerrar el Registro de Trabajos y Salidas No Conformes y archivarlo.'],
          ['Si amerita solicitar una acción correctiva:', 'Cuando podría volver a ocurrir el TNC o SNC o exista duda acerca del cumplimiento de las operaciones del laboratorio con su propio Sistema Integrado de Gestión, cerrar el Registro de Trabajos y Salidas No Conformes, archivarlo y velar por el cumplimiento del procedimiento de Gestión de No Conformidades y Acciones Correctivas.'],
        ],
      },
    ],
    autoridades: [
      'Solicitar a los colaboradores del área pertinente la ejecución de la primera respuesta ante un TNC o SNC, ej.: detención del proceso administrativo para el servicio en cuestión.',
      'Solicitar que el laboratorio asuma costos de la interrupción o anulación de envío de entregables al cliente.',
      'Proponer alternativas de solución al cliente, así como evaluar la factibilidad de la propuesta de solución del cliente (si aplica) y hacer que se ejecute, ej.: anular la calibración sólo de los equipos con TNC o SNC y proseguir con los equipos conformes.',
      'Coordinar la anulación del servicio (si aplica); la devolución del monto cancelado la gestiona el Gerente Comercial.',
      'Decidir en función a su evaluación si un TNC o SNC amerita una solicitud de acción correctiva.',
      'Convocar a reuniones de coordinación o de retroalimentación (si es necesario).',
      'Autorizar la reanudación del trabajo.',
    ],
  },
  {
    cargo: 'Gerente Técnico y Jefe de Laboratorio',
    responsabilidades: [
      { texto: 'Decidir sobre la aceptabilidad de un TNC o SNC.' },
      { texto: 'Definir la primera respuesta del área técnica (corrección) frente al reporte de un TNC o SNC y ejecutarla rápidamente.' },
      { texto: 'Notificar al cliente y anular el servicio si fuera necesario.' },
      {
        texto: 'Definir la corrección y corregir el TNC o SNC.',
        casos: [
          ['Si el TNC o SNC implica aspectos netamente técnicos:', 'Definir la corrección y corregir el TNC o SNC.'],
          ['Si el TNC o SNC implica aspectos técnicos y administrativos:', 'Definir la corrección y corregir el TNC o SNC con apoyo del Gerente SIG.'],
        ],
      },
    ],
    autoridades: [
      'Solicitar a los metrólogos la ejecución de la primera respuesta ante un TNC o SNC, ej.: detención de la calibración para los equipos en cuestión.',
      'Solicitar a los metrólogos la ejecución de la corrección ante un TNC o SNC, cuando es netamente técnica, ej.: regulación de las condiciones de temperatura para cumplir con el rango de tolerancia establecido.',
      'Solicitar apoyo al Área SIG para la ejecución de la corrección ante un TNC o SNC que implique aspectos técnicos y administrativos, ej.: solicitar el apoyo para la comunicación con el cliente.',
      'Decidir la necesidad de adquisiciones y solicitarlas.',
      'Retener certificados, interrumpir y reanudar las actividades, asignando al personal responsable para ello.',
      'Retroalimentar la gestión del Gerente SIG.',
      'Autorizar la reanudación del trabajo.',
    ],
  },
]

// Niveles con la escala única del sistema: Alto rojo · Medio ámbar · Bajo verde.
const TABLA2 = [
  {
    nivel: 'Alto', badge: 'badge badge-rojo',
    criterios: [
      'Afecta o puede afectar la validez de resultados ya emitidos o entregados al cliente.',
      'Compromete la competencia técnica del laboratorio o el alcance acreditado.',
    ],
    ejemplo: 'patrón fuera de tolerancia usado en calibraciones emitidas; calibración ejecutada por personal sin autorización vigente; certificado entregado con error en resultados o incertidumbre.',
    acciones: [
      'Detención inmediata del trabajo.',
      'Identificación del equipo o patrón como «fuera de servicio».',
      'Retención de los certificados no entregados.',
      'Análisis de impacto retroactivo.',
      'Notificación formal al cliente de los certificados entregados afectados y, de corresponder, anulación y reemisión.',
      'Reanudación solo con autorización del Gerente Técnico o Jefe de Laboratorio.',
    ],
    sac: 'Obligatoria.',
  },
  {
    nivel: 'Medio', badge: 'badge badge-ambar',
    criterios: [
      'Afecta el trabajo en curso o una salida aún no entregada, sin afectar resultados ya emitidos.',
      'Salida entregada con errores que no alteran los resultados (datos del cliente o del equipo).',
      'Incumple un requisito del SIG o acordado con el cliente sin afectar la validez de los resultados.',
    ],
    ejemplo: 'condiciones ambientales fuera de rango durante una calibración en curso; desviación del método detectada antes de emitir; certificado entregado con error en la razón social.',
    acciones: [
      'Detención del trabajo afectado.',
      'Repetición del trabajo o corrección del documento.',
      'Retención del certificado hasta su corrección.',
      'Análisis de impacto retroactivo, si la causa pudo afectar trabajos anteriores.',
      'Notificación al cliente si la salida ya fue entregada o si cambia la fecha o el alcance acordados.',
    ],
    sac: 'Obligatoria si puede volver a ocurrir o existe duda sobre el cumplimiento del SIG; en otro caso, corrección.',
  },
  {
    nivel: 'Bajo', badge: 'badge badge-verde',
    criterios: [
      'No afecta la validez de los resultados ni la competencia técnica y se corrige antes de que la salida llegue al cliente.',
    ],
    ejemplo: 'error de digitación detectado en la revisión del certificado; registro incompleto subsanable.',
    acciones: ['Corrección y registro en el Registro de Trabajos y Salidas No Conformes.'],
    sac: 'No, salvo tres (03) eventos similares en doce (12) meses.',
  },
]

const Lista = ({ items }) => (
  <ul className="list-disc space-y-1 pl-4 text-left">{items.map((x) => <li key={x}>{x}</li>)}</ul>
)

function Tabla1() {
  return (
    <table className="tabla-ficha w-full text-xs">
      <thead><tr><th className="w-40">Cargo</th><th>Tiene la responsabilidad de</th><th>Tiene autoridad para</th></tr></thead>
      <tbody>
        {TABLA1.map((f) => (
          <tr key={f.cargo} className="align-top">
            <td className="text-left font-semibold">{f.cargo}</td>
            <td className="text-left">
              <ul className="list-disc space-y-1.5 pl-4">
                {f.responsabilidades.map((r) => (
                  <li key={r.texto}>{r.texto}
                    {r.casos && (
                      <div className="mt-1 space-y-1">
                        {r.casos.map(([si, haz]) => <p key={si} className="pl-1"><span className="italic">{si}</span> {haz}</p>)}
                      </div>
                    )}
                  </li>
                ))}
              </ul>
            </td>
            <td><Lista items={f.autoridades} /></td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function Tabla2() {
  return (
    <>
      <table className="tabla-ficha w-full text-xs">
        <thead><tr><th className="w-20">Nivel</th><th>Criterios (basta con que se cumpla uno)</th><th>Acciones</th><th className="w-44">Solicitud de acción correctiva</th></tr></thead>
        <tbody>
          {TABLA2.map((f) => (
            <tr key={f.nivel} className="align-top">
              <td className="text-center"><span className={f.badge}>{f.nivel}</span></td>
              <td className="text-left"><Lista items={f.criterios} /><p className="mt-1.5 text-slate-500"><span className="italic">Ej.:</span> {f.ejemplo}</p></td>
              <td><Lista items={f.acciones} /></td>
              <td className="text-left">{f.sac}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="mt-2 text-[11px] text-slate-500">Ante duda entre dos niveles, se asigna el mayor. El Área SIG confirma el nivel en la evaluación de la importancia.</p>
    </>
  )
}

const TITULOS = {
  1: 'Tabla N° 1 · Asignación de responsabilidades y autoridades para la gestión del TNC y SNC',
  2: 'Tabla N° 2 · Niveles de riesgo y acciones para el TNC y SNC',
}

/** Ventana de consulta con las tablas del procedimiento. `tabla`: 1, 2 o null (cerrada). */
export default function TablasTNC({ tabla, onCerrar }) {
  const [actual, setActual] = useState(tabla || 2)
  useEffect(() => { if (tabla) setActual(tabla) }, [tabla])
  return (
    <Modal abierto={Boolean(tabla)} titulo="Tablas del procedimiento de trabajos y salidas no conformes" onCerrar={onCerrar} ancho="max-w-5xl">
      <div className="mb-3 flex flex-wrap gap-1">
        {[1, 2].map((n) => (
          <button key={n} type="button" onClick={() => setActual(n)}
            className={`rounded-lg px-3 py-1.5 text-xs font-medium ${actual === n ? 'bg-esynapse-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300'}`}>
            Tabla N° {n}
          </button>
        ))}
      </div>
      <p className="mb-2 text-sm font-semibold">{TITULOS[actual]}</p>
      {actual === 1 ? <Tabla1 /> : <Tabla2 />}
    </Modal>
  )
}

/** Enlace pequeño para abrir una tabla desde una etiqueta o una nota. */
export const VerTabla = ({ n, onAbrir, texto }) => (
  <button type="button" onClick={(e) => { e.preventDefault(); e.stopPropagation(); onAbrir(n) }}
    className="text-[11px] font-medium text-esynapse-500 hover:underline">{texto || `Ver Tabla N° ${n}`}</button>
)

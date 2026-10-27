// Elementos gráficos de la marca (decorativos, ocultos a lectores de pantalla): la señal de
// calibración que se desplaza, la regla graduada y el dial con su aguja. Solo en el Tablero y
// en la pantalla de ingreso.

const ONDA = 'M0 60 C40 30 80 30 120 60' + Array.from({ length: 15 }, (_, i) => {
  const x = 120 + i * 120
  return ` S${x + 80} ${i % 2 ? 30 : 90} ${x + 120} 60`
}).join('')

export function Senal({ className = '', color = '#8eaddf' }) {
  return (
    <svg aria-hidden="true" width="1920" height="120" viewBox="0 0 1920 120" className={`pointer-events-none ${className}`}>
      <path className="mov-senal" d={ONDA} fill="none" stroke={color} strokeWidth="2" />
    </svg>
  )
}

export function Regla({ className = '' }) {
  return (
    <svg aria-hidden="true" width="100%" height="16" className={`pointer-events-none ${className}`}>
      <defs>
        <pattern id="esy-regla" width="24" height="16" patternUnits="userSpaceOnUse">
          <path d="M0 0v14M12 0v8" stroke="#ffffff" strokeWidth="1" />
        </pattern>
      </defs>
      <rect width="100%" height="16" fill="url(#esy-regla)" />
    </svg>
  )
}

export function Dial({ className = '' }) {
  return (
    <svg aria-hidden="true" width="520" height="520" viewBox="0 0 520 520" className={`pointer-events-none ${className}`}>
      <g className="mov-anillo">
        <circle cx="260" cy="260" r="230" fill="none" stroke="#5f88cc" strokeOpacity=".35" strokeWidth="1" />
        <circle cx="260" cy="260" r="230" fill="none" stroke="#bacdec" strokeOpacity=".5" strokeWidth="10" strokeDasharray="1.5 22.6" />
      </g>
      <circle cx="260" cy="260" r="170" fill="none" stroke="#8eaddf" strokeOpacity=".35" strokeWidth="1" />
      <path d="M90 300 A172 172 0 0 1 430 300" fill="none" stroke="#5ee0a0" strokeOpacity=".55" strokeWidth="6" strokeLinecap="round" strokeDasharray="260 600" />
      <path d="M90 300 A172 172 0 0 1 430 300" fill="none" stroke="#fcd68a" strokeOpacity=".5" strokeWidth="6" strokeLinecap="round" strokeDasharray="0 270 70 600" />
      <g className="mov-aguja"><path d="M260 260 L260 120" stroke="#ffffff" strokeWidth="3" strokeLinecap="round" /></g>
      <circle cx="260" cy="260" r="9" fill="#ffffff" />
    </svg>
  )
}

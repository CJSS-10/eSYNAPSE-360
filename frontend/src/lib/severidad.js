// Escala de severidad única del sistema: cinco niveles. Cada módulo conserva los nombres de
// su metodología (riesgos y oportunidades, IPERC, análisis de trabajo seguro), pero el mismo
// nivel tiene siempre el mismo color. El nombre del nivel va siempre escrito: el color nunca
// es la única señal. «chip» es la etiqueta; «celda» es el relleno sólido de los mapas de calor.
export const SEVERIDAD = {
  1: { chip: 'bg-[#E3F3EA] text-[#1E6B43] dark:bg-[#173329] dark:text-[#93D6AE]', celda: 'bg-[#8FD0A9] text-[#0F3D24]' },
  2: { chip: 'bg-[#EEF4D6] text-[#4E5E0E] dark:bg-[#2A3214] dark:text-[#CFE08A]', celda: 'bg-[#C8DB7A] text-[#2F3A05]' },
  3: { chip: 'bg-[#FDF1D8] text-[#8A5300] dark:bg-[#3A2D14] dark:text-[#F2C879]', celda: 'bg-[#F4C64E] text-[#3D2600]' },
  4: { chip: 'bg-[#FCE3D2] text-[#9C3D0B] dark:bg-[#3D2214] dark:text-[#F5AE80]', celda: 'bg-[#EE8A4A] text-[#3A1503]' },
  5: { chip: 'bg-[#F9D9D9] text-[#A61B1B] dark:bg-[#3A1C24] dark:text-[#F2A3A3]', celda: 'bg-[#C62828] text-white' },
}

// [nombre, clases de etiqueta, clases de celda] para armar los mapas de nivel de cada módulo.
export const sev = (n, nombre) => [nombre, SEVERIDAD[n].chip, SEVERIDAD[n].celda]

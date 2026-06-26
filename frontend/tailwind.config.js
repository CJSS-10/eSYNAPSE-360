/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        // Paleta eSYNAPSE 360 — laboratorio: azul metrología + acentos
        esynapse: {
          50: '#eef6ff', 100: '#d9eaff', 200: '#bcdbff', 300: '#8ec4ff',
          400: '#59a3ff', 500: '#3380fc', 600: '#1d60f1', 700: '#154bde',
          800: '#173eb4', 900: '#19398d', 950: '#142456',
        },
      },
    },
  },
  plugins: [],
}

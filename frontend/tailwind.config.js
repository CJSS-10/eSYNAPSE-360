/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['IBM Plex Sans', 'system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'sans-serif'],
        condensada: ['IBM Plex Sans Condensed', 'IBM Plex Sans', 'system-ui', 'sans-serif'],
        mono: ['IBM Plex Mono', 'ui-monospace', 'Consolas', 'monospace'],   // códigos de registro
      },
      colors: {
        // Azul Metrindust (ADR-0007): 600 es el color principal (botones, enlaces, elemento activo)
        esynapse: {
          50: '#eef3fb', 100: '#dce6f6', 200: '#bacdec', 300: '#8eaddf',
          400: '#5f88cc', 500: '#3a69b6', 600: '#1f4e9b', 700: '#1a4385',
          800: '#17396f', 900: '#142f5a', 950: '#0d1e3b',
        },
        // Modo oscuro azul marino en lugar de casi negro (fondo, superficies y bordes)
        slate: { 800: '#22324a', 900: '#142133', 950: '#0d1724' },
      },
      boxShadow: {
        card: '0 1px 2px 0 rgb(15 23 42 / 0.04), 0 1px 3px 0 rgb(15 23 42 / 0.06)',
        'card-hover': '0 4px 12px -2px rgb(15 23 42 / 0.10), 0 2px 6px -2px rgb(15 23 42 / 0.08)',
        pop: '0 10px 30px -10px rgb(15 23 42 / 0.25)',
      },
      keyframes: {
        shimmer: { '100%': { transform: 'translateX(100%)' } },
        'fade-in-up': {
          '0%': { opacity: '0', transform: 'translateY(6px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
      animation: {
        'fade-in-up': 'fade-in-up .28s ease-out both',
      },
    },
  },
  plugins: [],
}

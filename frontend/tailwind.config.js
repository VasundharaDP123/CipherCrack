/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        display: ['Outfit', 'Inter', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
      colors: {
        cyber: {
          950: '#030712',
          900: '#0a0f1d',
          850: '#111827',
          800: '#1f2937',
          700: '#374151',
          600: '#4b5563',
        },
        matrix: {
          300: '#6ee7b7',
          400: '#34d399',
          500: '#00ff87',
          600: '#059669',
        },
        solar: {
          400: '#fb923c',
          500: '#f97316',
          600: '#ea580c',
        },
        neon: {
          lime: '#00ff87',
          amber: '#f59e0b',
          orange: '#f97316',
          rose: '#ff2a6d',
          violet: '#a855f7',
          cyan: '#06b6d4',
        },
      },
      boxShadow: {
        'glow-matrix': '0 0 30px -5px rgba(0, 255, 135, 0.35)',
        'glow-solar': '0 0 30px -5px rgba(249, 115, 22, 0.35)',
        'glow-violet': '0 0 30px -5px rgba(168, 85, 247, 0.35)',
        'card-cyber': '0 10px 40px -15px rgba(0, 0, 0, 0.8), 0 0 20px 0 rgba(0, 255, 135, 0.08)',
      },
    },
  },
  plugins: [],
}

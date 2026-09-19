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
          950: '#0b0a10',
          900: '#121019',
          850: '#191624',
          800: '#221e31',
          700: '#312b45',
          600: '#463e62',
        },
        glow: { DEFAULT: '#f59e0b', dim: '#d97706', muted: 'rgba(245, 158, 11, 0.15)' },
        neon: {
          amber: '#f59e0b',
          gold: '#fbbf24',
          emerald: '#10b981',
          rose: '#ff2a6d',
          violet: '#a855f7',
          coral: '#ff6b6b',
        },
      },
      keyframes: {
        pop: { '0%': { transform: 'scale(1)' }, '50%': { transform: 'scale(1.22)' }, '100%': { transform: 'scale(1)' } },
        pulseGlow: { '0%, 100%': { opacity: '0.6' }, '50%': { opacity: '1' } },
        shimmer: { '0%': { backgroundPosition: '-200% 0' }, '100%': { backgroundPosition: '200% 0' } },
      },
      animation: {
        pop: 'pop 320ms ease-out',
        pulseGlow: 'pulseGlow 2s infinite ease-in-out',
        shimmer: 'shimmer 2.5s infinite linear',
      },
    },
  },
  plugins: [],
}

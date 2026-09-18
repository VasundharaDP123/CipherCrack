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
          950: '#050811',
          900: '#090e1c',
          850: '#0f172a',
          800: '#131e36',
          700: '#1e2d4d',
          600: '#2c3e66',
        },
        glow: { DEFAULT: '#00f2fe', dim: '#08b6ce', muted: 'rgba(0, 242, 254, 0.15)' },
        neon: {
          cyan: '#00f2fe',
          purple: '#9d4edd',
          emerald: '#10b981',
          amber: '#f59e0b',
          pink: '#ff007f',
          blue: '#3b82f6',
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

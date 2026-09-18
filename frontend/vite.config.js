import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // The backend runs on 5000; proxying keeps the frontend origin-relative
    // so no CORS or hard-coded hostname ever reaches the components.
    //
    // `changeOrigin` is deliberately OFF.  It rewrites the Origin header to the
    // proxy target, so the browser's real origin (localhost:5173) arrives at
    // Flask-SocketIO as 127.0.0.1:5000 -- which is not in its allowed list, and
    // every live-solve connection gets refused with no visible error beyond an
    // empty page.  Passing the true origin through is what lets the handshake
    // succeed.
    proxy: {
      '/api': { target: 'http://127.0.0.1:5000' },
      '/socket.io': { target: 'http://127.0.0.1:5000', ws: true },
    },
  },
})

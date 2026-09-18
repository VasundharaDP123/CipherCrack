import { io } from 'socket.io-client'

// One shared connection for the whole app; the Crack page and the Challenge
// page both stream over it, never at the same time.
let socket = null

export function getSocket() {
  if (!socket) {
    const isDev = typeof window !== 'undefined' && window.location.port === '5173'
    const target = isDev ? `http://${window.location.hostname}:5000` : '/'
    socket = io(target, {
      transports: ['polling', 'websocket'],
      autoConnect: true,
      reconnection: true,
      reconnectionAttempts: 10,
      reconnectionDelay: 1000,
    })
  }
  return socket
}

export const LETTERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

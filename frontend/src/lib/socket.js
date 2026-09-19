import { io } from 'socket.io-client'

// One shared connection for the whole app; the Crack page and the Challenge
// page both stream over it, never at the same time.
let socket = null

export function getSocket() {
  if (!socket) {
    socket = io({
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

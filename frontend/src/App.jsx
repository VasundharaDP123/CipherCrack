import { useEffect, useState } from 'react'
import { NavLink, Navigate, Route, Routes } from 'react-router-dom'
import {
  Lock, KeyRound, Search, Sliders, Trophy, Swords, ShieldCheck, Database, Cpu, Wifi, WifiOff,
} from 'lucide-react'
import { api } from './lib/api'

import Arena from './pages/Arena.jsx'
import Challenge from './pages/Challenge.jsx'
import Crack from './pages/Crack.jsx'
import Encrypt from './pages/Encrypt.jsx'
import Identify from './pages/Identify.jsx'
import Playground from './pages/Playground.jsx'

const PAGES = [
  { to: '/crack', label: 'Crack Live', icon: KeyRound, tag: 'Live MCMC' },
  { to: '/encrypt', label: 'Encrypt Lab', icon: Lock, tag: 'Generator' },
  { to: '/identify', label: 'Cipher Identifier', icon: Search, tag: 'RF & AdaBoost' },
  { to: '/playground', label: 'MCMC Playground', icon: Sliders, tag: 'Sampling' },
  { to: '/arena', label: 'Algorithm Arena', icon: Swords, tag: 'Benchmarks' },
  { to: '/challenge', label: 'Challenge Mode', icon: Trophy, tag: 'Race AI' },
]

function Header({ health }) {
  return (
    <header className="sticky top-0 z-40 border-b border-zinc-800/80 bg-zinc-950/85 backdrop-blur-xl shadow-lg shadow-black/50">
      <div className="mx-auto flex max-w-7xl flex-col gap-3.5 px-4 sm:px-6 py-3.5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 via-purple-500 to-pink-500 p-0.5 shadow-glow">
              <div className="flex h-full w-full items-center justify-center rounded-[10px] bg-zinc-950">
                <ShieldCheck className="h-5 w-5 text-indigo-400" />
              </div>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-display text-xl font-extrabold tracking-tight bg-gradient-to-r from-zinc-100 via-indigo-200 to-purple-300 bg-clip-text text-transparent">
                  CipherCrack
                </span>
                <span className="rounded-md bg-indigo-500/10 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-indigo-400 border border-indigo-500/20 font-display">
                  v2.0 Enterprise
                </span>
              </div>
              <p className="hidden text-xs font-medium text-zinc-400 sm:block">
                MCMC &amp; HMM Unsupervised Cipher Breaking &amp; Cryptanalysis Engine
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {health ? (
              <>
                <div className="hidden sm:inline-flex chip font-mono">
                  <Database className="h-3.5 w-3.5 text-indigo-400" />
                  {(health.language_model.bigrams_counted / 1e6).toFixed(1)}M bigrams
                </div>
                <div className="hidden sm:inline-flex chip font-mono">
                  <Cpu className="h-3.5 w-3.5 text-purple-400" />
                  RF {health.identifier_ready ? `${(health.identifier_accuracy * 100).toFixed(1)}%` : 'offline'}
                </div>
                <div className="chip-glow font-mono">
                  <span className="relative flex h-2 w-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-400"></span>
                  </span>
                  Backend Live
                </div>
              </>
            ) : (
              <div className="chip border-amber-500/30 bg-amber-500/10 text-amber-300 font-mono">
                <WifiOff className="h-3.5 w-3.5 animate-pulse text-amber-400" />
                Connecting API…
              </div>
            )}
          </div>
        </div>

        <nav className="flex gap-1.5 overflow-x-auto pb-1 scrollbar-none">
          {PAGES.map((page) => {
            const Icon = page.icon
            return (
              <NavLink
                key={page.to}
                to={page.to}
                className={({ isActive }) =>
                  `flex items-center gap-2 whitespace-nowrap rounded-xl px-3.5 py-2 text-xs font-semibold tracking-wide transition-all duration-200 font-display ${
                    isActive
                      ? 'bg-gradient-to-r from-indigo-500/20 to-purple-500/20 text-indigo-300 border border-indigo-500/30 shadow-sm shadow-indigo-950/50'
                      : 'text-zinc-400 hover:bg-zinc-800/60 hover:text-zinc-200 border border-transparent'
                  }`
                }
              >
                <Icon className="h-4 w-4" />
                <span>{page.label}</span>
              </NavLink>
            )
          })}
        </nav>
      </div>
    </header>
  )
}

export default function App() {
  const [health, setHealth] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    api.health().then(setHealth).catch((e) => setError(e.message))
  }, [])

  return (
    <div className="min-h-screen flex flex-col bg-[#09090b]">
      <Header health={health} />

      {error && (
        <div className="mx-auto mt-4 max-w-7xl px-4 sm:px-6 w-full">
          <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 text-xs font-medium text-amber-200 shadow-lg shadow-amber-950/20 flex items-center gap-3">
            <WifiOff className="h-5 w-5 text-amber-400 shrink-0" />
            <div>
              Cannot connect to Flask backend API ({error}). Make sure backend server is active on port 5000: <code className="font-mono text-indigo-300">python app.py</code> in <code className="font-mono text-indigo-300">backend/</code>.
            </div>
          </div>
        </div>
      )}

      <main className="mx-auto max-w-7xl px-4 sm:px-6 py-6 flex-1 w-full">
        <Routes>
          <Route path="/" element={<Navigate to="/crack" replace />} />
          <Route path="/encrypt" element={<Encrypt />} />
          <Route path="/crack" element={<Crack />} />
          <Route path="/identify" element={<Identify />} />
          <Route path="/playground" element={<Playground />} />
          <Route path="/arena" element={<Arena />} />
          <Route path="/challenge" element={<Challenge />} />
          <Route path="*" element={<Navigate to="/crack" replace />} />
        </Routes>
      </main>

      <footer className="border-t border-zinc-800/60 bg-zinc-950/60 backdrop-blur-md py-6 mt-10 text-xs text-zinc-500">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 flex flex-col sm:flex-row items-center justify-between gap-4 text-center sm:text-left">
          <div>
            <p className="font-medium text-zinc-400">CipherCrack — Live MCMC &amp; HMM Substitution Cipher Cryptanalysis Workspace</p>
            <p className="mt-1 text-[11px] text-zinc-600">
              Built with NumPy, Flask-SocketIO &amp; React for BAI702. Bigram language model trained on Gutenberg corpus.
            </p>
          </div>
          <div className="flex items-center gap-3 font-mono text-[11px] text-zinc-400">
            <span className="chip">26! ~ 4x10^26 search space</span>
          </div>
        </div>
      </footer>
    </div>
  )
}

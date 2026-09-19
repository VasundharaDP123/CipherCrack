import { useEffect, useState } from 'react'
import { NavLink, Navigate, Route, Routes } from 'react-router-dom'
import {
  Lock, KeyRound, Search, Sliders, Trophy, Swords, ShieldCheck, Database, Cpu, WifiOff, Sparkles
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
  { to: '/identify', label: 'Cipher Identifier', icon: Search, tag: 'RF & ML' },
  { to: '/playground', label: 'MCMC Playground', icon: Sliders, tag: 'Sampling' },
  { to: '/arena', label: 'Algorithm Arena', icon: Swords, tag: 'Benchmarks' },
  { to: '/challenge', label: 'Challenge Mode', icon: Trophy, tag: 'Race AI' },
]

function Header({ health }) {
  return (
    <header className="sticky top-0 z-40 border-b border-cyber-800/80 bg-cyber-950/90 backdrop-blur-2xl shadow-card-cyber">
      <div className="mx-auto flex max-w-7xl flex-col gap-3.5 px-4 sm:px-6 py-3.5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-matrix-500 via-solar-500 to-neon-violet p-0.5 shadow-glow-matrix">
              <div className="flex h-full w-full items-center justify-center rounded-[10px] bg-cyber-950">
                <ShieldCheck className="h-6 w-6 text-matrix-500 glow-text-matrix" />
              </div>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-display text-2xl font-black tracking-tight bg-gradient-to-r from-matrix-300 via-solar-400 to-neon-violet bg-clip-text text-transparent">
                  CipherCrack
                </span>
                <span className="chip-matrix font-mono font-bold text-[10px] uppercase">
                  v2.0 MCMC Core
                </span>
              </div>
              <p className="hidden text-xs font-medium text-slate-400 sm:block">
                Autonomous Cryptanalysis Engine • Metropolis-Hastings MCMC &amp; Random Forest Classifier
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {health ? (
              <>
                <div className="hidden sm:inline-flex chip-matrix font-mono">
                  <Database className="h-3.5 w-3.5 text-matrix-400" />
                  {(health.language_model.bigrams_counted / 1e6).toFixed(1)}M Bigrams
                </div>
                <div className="hidden sm:inline-flex chip-solar font-mono">
                  <Cpu className="h-3.5 w-3.5 text-solar-400" />
                  RF {health.identifier_ready ? `${(health.identifier_accuracy * 100).toFixed(1)}%` : 'offline'}
                </div>
                <div className="chip-matrix font-mono">
                  <span className="relative flex h-2 w-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-matrix-500 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-matrix-500"></span>
                  </span>
                  Engine Online
                </div>
              </>
            ) : (
              <div className="chip-solar font-mono">
                <WifiOff className="h-3.5 w-3.5 animate-pulse text-solar-400" />
                Connecting API…
              </div>
            )}
          </div>
        </div>

        <nav className="flex gap-2 overflow-x-auto pb-1 scrollbar-none">
          {PAGES.map((page) => {
            const Icon = page.icon
            return (
              <NavLink
                key={page.to}
                to={page.to}
                className={({ isActive }) =>
                  `flex items-center gap-2 whitespace-nowrap rounded-xl px-4 py-2 text-xs font-bold tracking-wide transition-all duration-200 font-display ${
                    isActive
                      ? 'bg-gradient-to-r from-matrix-500/20 via-solar-500/20 to-neon-violet/20 text-matrix-300 border border-matrix-500/40 shadow-glow-matrix'
                      : 'text-slate-400 hover:bg-cyber-800/60 hover:text-slate-200 border border-transparent'
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
    <div className="min-h-screen flex flex-col bg-cyber-950 text-slate-100">
      <Header health={health} />

      {error && (
        <div className="mx-auto mt-4 max-w-7xl px-4 sm:px-6 w-full">
          <div className="rounded-xl border border-solar-500/40 bg-solar-500/10 p-4 text-xs font-medium text-solar-400 shadow-glow-solar flex items-center gap-3">
            <WifiOff className="h-5 w-5 text-solar-500 shrink-0" />
            <div>
              Cannot connect to Flask backend API ({error}). Make sure backend server is active on port 5000: <code className="font-mono text-matrix-400">python app.py</code> in <code className="font-mono text-matrix-400">backend/</code>.
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

      <footer className="border-t border-cyber-800/80 bg-cyber-950/90 backdrop-blur-md py-6 mt-12 text-xs text-slate-500">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 flex flex-col sm:flex-row items-center justify-between gap-4 text-center sm:text-left">
          <div>
            <p className="font-semibold text-slate-300 flex items-center justify-center sm:justify-start gap-1.5">
              <Sparkles className="h-4 w-4 text-matrix-500" />
              CipherCrack — Autonomous Cryptanalysis &amp; MCMC Substitution Decipherment
            </p>
            <p className="mt-1 text-[11px] text-slate-500">
              Powered by Metropolis-Hastings MCMC, N-gram Language Modeling &amp; Machine Learning Classifiers.
            </p>
          </div>
          <div className="flex items-center gap-3 font-mono text-[11px]">
            <span className="chip-matrix">26! ≈ 4.03×10²⁶ Key Space</span>
          </div>
        </div>
      </footer>
    </div>
  )
}

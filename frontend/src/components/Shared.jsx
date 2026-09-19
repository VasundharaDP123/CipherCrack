import { motion } from 'framer-motion'
import { AlertTriangle, Loader2, BarChart2 } from 'lucide-react'
import {
  Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis, Legend,
} from 'recharts'
import { LETTERS } from '../lib/socket'

export const ENGLISH_FREQUENCIES = {
  A: 8.17, B: 1.49, C: 2.78, D: 4.25, E: 12.70, F: 2.23, G: 2.02, H: 6.09, I: 6.96,
  J: 0.15, K: 0.77, L: 4.03, M: 2.41, N: 6.75, O: 7.51, P: 1.93, Q: 0.10, R: 5.99,
  S: 6.33, T: 9.06, U: 2.76, V: 0.98, W: 2.36, X: 0.15, Y: 1.97, Z: 0.07,
}

export function computeFrequencies(text) {
  if (!text) return {}
  const cleaned = text.toUpperCase().replace(/[^A-Z]/g, '')
  const total = cleaned.length || 1
  const counts = {}
  for (const ch of cleaned) {
    counts[ch] = (counts[ch] || 0) + 1
  }
  const freqs = {}
  for (const ch of LETTERS) {
    freqs[ch] = Number((((counts[ch] || 0) / total) * 100).toFixed(2))
  }
  return freqs
}

export function FrequencyHistogram({ text, title = 'Letter Frequency Analysis', label = 'Observed Frequency' }) {
  const freqs = computeFrequencies(text)
  const data = LETTERS.split('').map((letter) => ({
    letter,
    Observed: freqs[letter] || 0,
    English: ENGLISH_FREQUENCIES[letter] || 0,
  }))

  return (
    <div className="card space-y-3">
      <div className="flex items-center justify-between border-b border-cyber-800/80 pb-2.5">
        <h2 className="text-xs font-bold uppercase tracking-widest text-slate-300 font-display flex items-center gap-2">
          <BarChart2 className="h-4 w-4 text-matrix-400" />
          {title}
        </h2>
        <span className="chip-matrix font-mono text-[11px]">
          A–Z Monogram Spectrum
        </span>
      </div>

      <div className="h-52 w-full rounded-xl border border-cyber-800 bg-cyber-950/90 p-2">
        {text ? (
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} margin={{ top: 10, right: 15, bottom: 5, left: -20 }}>
              <CartesianGrid stroke="#1f2937" strokeDasharray="3 3" vertical={false} />
              <XAxis
                dataKey="letter"
                tick={{ fill: '#94a3b8', fontSize: 10, fontFamily: 'monospace' }}
                stroke="#374151"
                interval={0}
              />
              <YAxis
                tick={{ fill: '#94a3b8', fontSize: 10, fontFamily: 'monospace' }}
                stroke="#374151"
                unit="%"
              />
              <Tooltip
                contentStyle={{
                  background: '#0a0f1d',
                  border: '1px solid rgba(0, 255, 135, 0.4)',
                  borderRadius: 12,
                  fontSize: 12,
                  fontFamily: 'monospace',
                  boxShadow: '0 0 15px rgba(0, 255, 135, 0.2)',
                }}
                formatter={(v, name) => [`${v}%`, name]}
              />
              <Legend
                wrapperStyle={{ fontSize: 11, fontFamily: 'monospace', paddingTop: 4 }}
              />
              <Bar dataKey="Observed" name={label} fill="#00ff87" radius={[4, 4, 0, 0]} />
              <Bar dataKey="English" name="Standard English %" fill="#a855f7" radius={[4, 4, 0, 0]} fillOpacity={0.6} />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <div className="flex h-full items-center justify-center text-xs text-slate-500 italic">
            Provide text input to render frequency histogram…
          </div>
        )}
      </div>
    </div>
  )
}

export function PageHeader({ title, blurb, children, icon: Icon }) {
  return (
    <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-cyber-800/80 pb-5">
      <div>
        <div className="flex items-center gap-3">
          {Icon && (
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-matrix-500/10 border border-matrix-500/30 text-matrix-400 shadow-glow-matrix">
              <Icon className="h-6 w-6 text-matrix-400" />
            </div>
          )}
          <h1 className="font-display text-2xl sm:text-3xl font-black tracking-tight text-slate-100">
            {title}
          </h1>
        </div>
        {blurb && <p className="mt-2 max-w-3xl text-sm leading-relaxed text-slate-400">{blurb}</p>}
      </div>
      {children && <div className="flex flex-wrap items-center gap-2.5 shrink-0">{children}</div>}
    </div>
  )
}

export function Stat({ label, value, sub, tone = 'default', icon: Icon }) {
  const tones = {
    default: 'text-slate-100 border-cyber-800 bg-cyber-950/80',
    good: 'text-matrix-400 border-matrix-500/30 bg-matrix-500/10 shadow-glow-matrix',
    warn: 'text-solar-400 border-solar-500/30 bg-solar-500/10 shadow-glow-solar',
    accent: 'text-matrix-300 border-matrix-500/30 bg-matrix-500/10 shadow-glow-matrix',
    purple: 'text-neon-violet border-neon-violet/30 bg-neon-violet/10 shadow-glow-violet',
  }

  const valueTones = {
    default: 'text-slate-100',
    good: 'text-matrix-400 glow-text-matrix',
    warn: 'text-solar-400 glow-text-solar',
    accent: 'text-matrix-300 glow-text-matrix',
    purple: 'text-purple-300 glow-text-violet',
  }

  return (
    <div className={`rounded-xl border p-4 backdrop-blur-md transition-all duration-200 ${tones[tone]}`}>
      <div className="flex items-center justify-between">
        <div className="text-[10px] font-bold uppercase tracking-widest text-slate-400 font-display">
          {label}
        </div>
        {Icon && <Icon className={`h-4 w-4 ${valueTones[tone]}`} />}
      </div>
      <div className={`mt-1.5 font-mono text-2xl font-black tabular-nums tracking-tight ${valueTones[tone]}`}>
        {value}
      </div>
      {sub && <div className="mt-1 text-[11px] font-medium text-slate-400">{sub}</div>}
    </div>
  )
}

export function Spinner({ label = 'computing' }) {
  return (
    <span className="inline-flex items-center gap-2 text-xs font-semibold text-matrix-400 bg-matrix-500/10 border border-matrix-500/30 px-3 py-1.5 rounded-full shadow-glow-matrix">
      <Loader2 className="h-3.5 w-3.5 animate-spin text-matrix-400" />
      {label}
    </span>
  )
}

export function ErrorNote({ error }) {
  if (!error) return null
  return (
    <div className="flex items-start gap-3 rounded-xl border border-rose-500/40 bg-rose-500/10 p-4 text-xs font-medium text-rose-300 shadow-lg shadow-rose-950/20">
      <AlertTriangle className="h-4 w-4 text-rose-400 shrink-0 mt-0.5" />
      <div className="leading-relaxed">{String(error)}</div>
    </div>
  )
}

export function KeyGrid({ decryptionKey, previousKey, truthKey }) {
  if (!decryptionKey) return null
  return (
    <div className="grid grid-cols-[repeat(13,minmax(0,1fr))] gap-1.5">
      {LETTERS.split('').map((cipherLetter, index) => {
        const guess = decryptionKey[index]
        const changed = previousKey && previousKey[index] !== guess
        const correct = truthKey ? truthKey[index] === guess : null

        const tone =
          correct === null
            ? changed
              ? 'border-solar-500/60 bg-solar-500/20 text-solar-300 shadow-glow-solar'
              : 'border-cyber-800 bg-cyber-950/90 text-slate-200'
            : correct
              ? 'border-matrix-500/60 bg-matrix-500/20 text-matrix-300 shadow-glow-matrix font-bold'
              : 'border-rose-500/40 bg-rose-500/10 text-rose-300'

        return (
          <motion.div
            key={cipherLetter}
            animate={changed ? { scale: [1, 1.25, 1], zIndex: 10 } : { scale: 1, zIndex: 1 }}
            transition={{ duration: 0.28 }}
            className={`rounded-lg border px-1 py-1.5 text-center transition-all ${tone}`}
            title={`ciphertext ${cipherLetter} decodes to ${guess}`}
          >
            <div className="text-[9px] font-bold uppercase tracking-wider text-slate-400 font-display">
              {cipherLetter}
            </div>
            <div className="font-mono text-sm font-black leading-tight mt-0.5">{guess}</div>
          </motion.div>
        )
      })}
    </div>
  )
}

export function LiveText({ text, previous, truth, limit = 900 }) {
  if (!text) {
    return <div className="font-mono text-xs text-slate-500 italic">Waiting for solver telemetry stream…</div>
  }
  const shown = text.slice(0, limit)
  return (
    <div className="font-mono text-xs leading-relaxed tracking-wider break-words">
      {shown.split('').map((character, index) => {
        const changed = previous && previous[index] !== character
        const correct = truth ? truth[index] === character : null
        let className = 'text-slate-200'
        if (correct === true) className = 'text-matrix-400 font-bold glow-text-matrix'
        else if (correct === false) className = 'text-slate-500'
        if (changed) className += ' bg-solar-500/30 text-solar-300 rounded px-0.5 animate-pulse'
        return (
          <span key={index} className={className}>
            {character}
          </span>
        )
      })}
      {text.length > limit && <span className="text-slate-500 font-sans italic"> … (+{text.length - limit} more characters)</span>}
    </div>
  )
}

export function Field({ label, hint, children }) {
  return (
    <div>
      <label className="label">
        {label}
        {hint && <span className="ml-1.5 font-normal normal-case tracking-normal text-slate-500 text-[11px]">{hint}</span>}
      </label>
      {children}
    </div>
  )
}

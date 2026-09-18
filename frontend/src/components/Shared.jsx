import { motion } from 'framer-motion'
import { AlertTriangle, Loader2 } from 'lucide-react'
import { LETTERS } from '../lib/socket'

export function PageHeader({ title, blurb, children, icon: Icon }) {
  return (
    <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-slate-800/80 pb-5">
      <div>
        <div className="flex items-center gap-3">
          {Icon && (
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-400">
              <Icon className="h-5 w-5" />
            </div>
          )}
          <h1 className="font-display text-2xl sm:text-3xl font-extrabold tracking-tight text-white">
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
    default: 'text-slate-100 border-slate-800/80 bg-cyber-950/60',
    good: 'text-emerald-400 border-emerald-500/20 bg-emerald-500/5',
    warn: 'text-amber-400 border-amber-500/20 bg-amber-500/5',
    accent: 'text-cyan-400 border-cyan-500/20 bg-cyan-500/5',
    purple: 'text-purple-400 border-purple-500/20 bg-purple-500/5',
  }

  const valueTones = {
    default: 'text-slate-100',
    good: 'text-emerald-400',
    warn: 'text-amber-400',
    accent: 'text-cyan-400',
    purple: 'text-purple-400',
  }

  return (
    <div className={`rounded-xl border p-3.5 backdrop-blur-md transition-all duration-200 ${tones[tone]}`}>
      <div className="flex items-center justify-between">
        <div className="text-[10px] font-bold uppercase tracking-widest text-slate-500 font-display">
          {label}
        </div>
        {Icon && <Icon className={`h-4 w-4 ${valueTones[tone]}`} />}
      </div>
      <div className={`mt-1 font-mono text-xl font-extrabold tabular-nums tracking-tight ${valueTones[tone]}`}>
        {value}
      </div>
      {sub && <div className="mt-0.5 text-[11px] font-medium text-slate-500">{sub}</div>}
    </div>
  )
}

export function Spinner({ label = 'computing' }) {
  return (
    <span className="inline-flex items-center gap-2 text-xs font-medium text-cyan-400 bg-cyan-500/10 border border-cyan-500/20 px-3 py-1.5 rounded-full">
      <Loader2 className="h-3.5 w-3.5 animate-spin text-cyan-400" />
      {label}
    </span>
  )
}

export function ErrorNote({ error }) {
  if (!error) return null
  return (
    <div className="flex items-start gap-3 rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-xs font-medium text-rose-200 shadow-lg shadow-rose-950/20">
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
              ? 'border-cyan-400 bg-cyan-500/20 text-cyan-200 shadow-sm shadow-cyan-500/30'
              : 'border-slate-700/60 bg-cyber-950/80 text-slate-200'
            : correct
              ? 'border-emerald-500/50 bg-emerald-500/15 text-emerald-200'
              : 'border-rose-500/40 bg-rose-500/10 text-rose-300'

        return (
          <motion.div
            key={cipherLetter}
            animate={changed ? { scale: [1, 1.25, 1], zIndex: 10 } : { scale: 1, zIndex: 1 }}
            transition={{ duration: 0.28 }}
            className={`rounded-lg border px-1 py-1.5 text-center transition-all ${tone}`}
            title={`ciphertext ${cipherLetter} decodes to ${guess}`}
          >
            <div className="text-[9px] font-bold uppercase tracking-wider text-slate-500 font-display">
              {cipherLetter}
            </div>
            <div className="font-mono text-sm font-extrabold leading-tight mt-0.5">{guess}</div>
          </motion.div>
        )
      })}
    </div>
  )
}

export function LiveText({ text, previous, truth, limit = 900 }) {
  if (!text) {
    return <div className="font-mono text-xs text-slate-600 italic">Waiting for backend solver telemetry stream…</div>
  }
  const shown = text.slice(0, limit)
  return (
    <div className="font-mono text-xs leading-relaxed tracking-wider break-words">
      {shown.split('').map((character, index) => {
        const changed = previous && previous[index] !== character
        const correct = truth ? truth[index] === character : null
        let className = 'text-slate-200'
        if (correct === true) className = 'text-emerald-400 font-semibold'
        else if (correct === false) className = 'text-slate-500'
        if (changed) className += ' bg-cyan-500/30 text-cyan-200 rounded px-0.5 animate-pulse'
        return (
          <span key={index} className={className}>
            {character}
          </span>
        )
      })}
      {text.length > limit && <span className="text-slate-600 font-sans italic"> … (+{text.length - limit} more characters)</span>}
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

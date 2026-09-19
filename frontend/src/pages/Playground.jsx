import { useEffect, useState } from 'react'
import {
  Sliders, Sparkles, Layers, Activity, CheckCircle2, AlertCircle, BookOpen, Compass, LineChart as LineChartIcon,
} from 'lucide-react'
import {
  CartesianGrid, Line, LineChart, ResponsiveContainer, Scatter, ScatterChart,
  Tooltip, XAxis, YAxis, ZAxis,
} from 'recharts'
import { api } from '../lib/api'
import { ErrorNote, PageHeader, Spinner, Stat } from '../components/Shared'

const PRESETS = [
  { label: 'Far Too Small (0.05)', value: 0.05 },
  { label: 'Small (0.30)', value: 0.3 },
  { label: 'Optimal (1.60)', value: 1.6 },
  { label: 'Too Large (8.00)', value: 8 },
]

function verdict(rate) {
  if (rate == null) return null
  if (rate > 0.7)
    return {
      tone: 'warn',
      title: 'High Acceptance Rate (>70%) — Over-Sampling',
      text: 'Steps are too small; the proposal chain moves at a crawl and takes thousands of iterations to traverse between Gaussian peaks.',
    }
  if (rate < 0.08)
    return {
      tone: 'warn',
      title: 'Low Acceptance Rate (<8%) — High Rejection',
      text: 'Steps are too large; proposals frequently land in zero-density regions, causing the chain to freeze in place for long stretches.',
    }
  return {
    tone: 'good',
    title: 'Optimal Acceptance Rate (~23.4%) — Optimal Mixing',
    text: 'Random-walk Metropolis-Hastings theory proves 0.234 acceptance maximizes independent entropy per sample step.',
  }
}

export default function Playground() {
  const [stepSize, setStepSize] = useState(1.6)
  const [data, setData] = useState(null)
  const [comparison, setComparison] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  async function sample(step = stepSize) {
    setBusy(true)
    setError(null)
    try {
      setData(await api.playgroundSample({ step_size: Number(step), n_samples: 4000, seed: 1 }))
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  useEffect(() => {
    sample(1.6)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function compare() {
    setBusy(true)
    try {
      setComparison(await api.playgroundCompare({ step_size: Number(stepSize), n_samples: 4000 }))
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  const note = verdict(data?.acceptance_rate)
  const trace = data?.trace_x.map((x, i) => ({ i, x })) ?? []

  return (
    <div>
      <PageHeader
        title="MCMC Playground"
        blurb="Interactive 2D Metropolis-Hastings Gaussian mixture sampler. Demonstrates how step size controls chain mixing, proposal acceptance, and Effective Sample Size (ESS)."
        icon={Sliders}
      />

      <div className="grid gap-6 lg:grid-cols-[380px,1fr]">
        {/* Left Column: Interactive Controls & Telemetry */}
        <div className="space-y-5">
          <div className="card space-y-5">
            <div className="flex items-center justify-between border-b border-cyber-800/80 pb-3">
              <h2 className="text-xs font-bold uppercase tracking-widest text-slate-300 font-display flex items-center gap-2">
                <Sliders className="h-4 w-4 text-solar-400" />
                Proposal Step Size (Standard Dev)
              </h2>
              <span className="chip-solar font-mono text-xs font-bold">
                σ = {Number(stepSize).toFixed(2)}
              </span>
            </div>

            <div>
              <input
                type="range"
                min="0.05"
                max="10"
                step="0.05"
                value={stepSize}
                onChange={(e) => setStepSize(e.target.value)}
                onMouseUp={(e) => sample(e.target.value)}
                onTouchEnd={(e) => sample(stepSize)}
                className="w-full accent-solar-500 cursor-pointer h-2 bg-cyber-950 rounded-lg border border-cyber-800"
              />
              <p className="mt-2 text-xs text-slate-500 leading-relaxed">
                Release slider to resample 4,000 steps from the 2D Gaussian mixture.
              </p>
            </div>

            <div className="grid grid-cols-2 gap-2">
              {PRESETS.map((preset) => (
                <button
                  key={preset.value}
                  className={`chip justify-center py-2 text-xs font-semibold cursor-pointer transition ${
                    Number(stepSize) === preset.value
                      ? 'chip-solar font-bold'
                      : 'hover:border-cyber-700 hover:text-slate-200'
                  }`}
                  onClick={() => {
                    setStepSize(preset.value)
                    sample(preset.value)
                  }}
                >
                  {preset.label}
                </button>
              ))}
            </div>

            <div className="flex items-center gap-3 pt-2">
              <button className="btn-primary flex-1" onClick={() => sample()} disabled={busy}>
                <Sparkles className="h-4 w-4" />
                Resample Chain
              </button>
              <button className="btn-violet" onClick={compare} disabled={busy}>
                <Layers className="h-4 w-4 text-purple-300" />
                vs emcee
              </button>
            </div>
            {busy && <Spinner label="drawing MCMC samples..." />}
            <ErrorNote error={error} />
          </div>

          {/* Stat Diagnostics */}
          {data && (
            <div className="card space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <Stat
                  label="Acceptance Rate"
                  value={`${(data.acceptance_rate * 100).toFixed(1)}%`}
                  tone={note?.tone === 'good' ? 'good' : 'warn'}
                  icon={Activity}
                />
                <Stat
                  label="Post Burn-In"
                  value={data.n_samples.toLocaleString()}
                  sub="samples drawn"
                  icon={CheckCircle2}
                />
                <Stat
                  label="ESS (Dimension X)"
                  value={data.effective_sample_size[0].toFixed(0)}
                  sub={`${(data.ess_per_sample[0] * 100).toFixed(1)}% efficient`}
                  tone="accent"
                />
                <Stat
                  label="ESS (Dimension Y)"
                  value={data.effective_sample_size[1].toFixed(0)}
                  sub={`${(data.ess_per_sample[1] * 100).toFixed(1)}% efficient`}
                  tone="purple"
                />
              </div>

              {note && (
                <div
                  className={`rounded-xl border p-3.5 text-xs font-medium leading-relaxed space-y-1 ${
                    note.tone === 'good'
                      ? 'border-matrix-500/40 bg-matrix-500/10 text-matrix-300 shadow-glow-matrix'
                      : 'border-solar-500/40 bg-solar-500/10 text-solar-300 shadow-glow-solar'
                  }`}
                >
                  <div className="font-bold font-display flex items-center gap-1.5 text-sm">
                    {note.tone === 'good' ? (
                      <CheckCircle2 className="h-4 w-4 text-matrix-400" />
                    ) : (
                      <AlertCircle className="h-4 w-4 text-solar-400" />
                    )}
                    {note.title}
                  </div>
                  <div>{note.text}</div>
                </div>
              )}
            </div>
          )}

          {/* Library Comparison with emcee */}
          {comparison && (
            <div className="card space-y-3">
              <div className="flex items-center justify-between border-b border-cyber-800/80 pb-3">
                <h2 className="text-xs font-bold uppercase tracking-widest text-slate-300 font-display flex items-center gap-2">
                  <Layers className="h-4 w-4 text-neon-violet" />
                  Library Comparison (emcee)
                </h2>
                <span className="chip-violet font-mono text-[11px]">
                  Ensemble MCMC
                </span>
              </div>
              <table className="w-full text-xs border-collapse">
                <thead>
                  <tr className="border-b border-cyber-800 text-slate-500 font-display uppercase tracking-wider text-[10px]">
                    <th className="p-2 text-left">Sampler</th>
                    <th className="p-2 text-right">Acceptance</th>
                    <th className="p-2 text-right">ESS (X / Y)</th>
                  </tr>
                </thead>
                <tbody>
                  {comparison.results.map((row) => (
                    <tr key={row.sampler} className="border-b border-cyber-800/60 font-mono">
                      <td className="p-2 font-sans font-semibold text-slate-300">{row.sampler}</td>
                      <td className="p-2 text-right font-bold text-solar-400">
                        {row.error ? '—' : `${(row.acceptance_rate * 100).toFixed(1)}%`}
                      </td>
                      <td className="p-2 text-right text-slate-400">
                        {row.error
                          ? 'Error'
                          : row.effective_sample_size.map((v) => v.toFixed(0)).join(' / ')}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Right Column: 2D Scatter Map & 1D Trace Plot */}
        <div className="space-y-5">
          {/* 2D Mixture Density Plot */}
          <div className="card space-y-3">
            <div className="flex items-center justify-between border-b border-cyber-800/80 pb-3">
              <h2 className="text-xs font-bold uppercase tracking-widest text-slate-300 font-display flex items-center gap-2">
                <Compass className="h-4 w-4 text-solar-400" />
                2D Metropolis-Hastings Chain Trajectory
              </h2>
              <span className="chip-matrix font-mono text-[11px]">Target: 3-Gaussian Mixture</span>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              Solar Orange dots show accepted 2D sample locations. Matrix Lime crosses show true Gaussian mixture means.
            </p>
            <div className="h-[340px] w-full rounded-xl border border-cyber-800 bg-cyber-950/90 p-2">
              {data && (
                <ResponsiveContainer width="100%" height="100%">
                  <ScatterChart margin={{ top: 10, right: 15, bottom: 5, left: -20 }}>
                    <CartesianGrid stroke="#1f2937" strokeDasharray="3 3" />
                    <XAxis
                      type="number"
                      dataKey="0"
                      domain={[-6, 6]}
                      tick={{ fill: '#94a3b8', fontSize: 10, fontFamily: 'monospace' }}
                      stroke="#374151"
                    />
                    <YAxis
                      type="number"
                      dataKey="1"
                      domain={[-6, 6]}
                      tick={{ fill: '#94a3b8', fontSize: 10, fontFamily: 'monospace' }}
                      stroke="#374151"
                    />
                    <ZAxis range={[6, 6]} />
                    <Tooltip
                      contentStyle={{
                        background: '#0a0f1d',
                        border: '1px solid rgba(249, 115, 22, 0.4)',
                        borderRadius: 12,
                        fontSize: 12,
                        fontFamily: 'monospace',
                        boxShadow: '0 0 15px rgba(249, 115, 22, 0.2)',
                      }}
                      formatter={(v) => (typeof v === 'number' ? v.toFixed(2) : v)}
                    />
                    <Scatter data={data.samples} fill="#f97316" fillOpacity={0.45} />
                    <Scatter
                      data={data.components.map((c) => ({ 0: c.mean[0], 1: c.mean[1] }))}
                      fill="#00ff87"
                      shape="cross"
                    />
                  </ScatterChart>
                </ResponsiveContainer>
              )}
            </div>
          </div>

          {/* 1D Trace Plot */}
          <div className="card space-y-3">
            <div className="flex items-center justify-between border-b border-cyber-800/80 pb-3">
              <h2 className="text-xs font-bold uppercase tracking-widest text-slate-300 font-display flex items-center gap-2">
                <LineChartIcon className="h-4 w-4 text-matrix-400" />
                1D Coordinate Chain Trace Plot (X-Axis Mixing)
              </h2>
              <span className="chip-matrix font-mono text-[11px]">First 400 Steps</span>
            </div>
            <div className="h-40 w-full rounded-xl border border-cyber-800 bg-cyber-950/90 p-2">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={trace} margin={{ top: 5, right: 15, bottom: 5, left: -20 }}>
                  <CartesianGrid stroke="#1f2937" strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="i" tick={{ fill: '#94a3b8', fontSize: 10, fontFamily: 'monospace' }} stroke="#374151" />
                  <YAxis tick={{ fill: '#94a3b8', fontSize: 10, fontFamily: 'monospace' }} stroke="#374151" />
                  <Line
                    type="monotone"
                    dataKey="x"
                    stroke="#00ff87"
                    strokeWidth={1.5}
                    dot={false}
                    isAnimationActive={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Box-Muller Theoretical Card */}
          <div className="card-violet space-y-2">
            <div className="text-xs font-bold uppercase tracking-widest text-purple-300 font-display flex items-center gap-2">
              <BookOpen className="h-4 w-4 text-neon-violet" />
              Box-Muller Gaussian Random Number Generator
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              Every proposal step is generated from scratch using exact Box-Muller transforms:
            </p>
            <div className="font-mono text-xs bg-cyber-950 p-3 rounded-xl border border-neon-violet/30 text-purple-200">
              R = sqrt(-2 ln U₁), θ = 2π U₂ &nbsp;→&nbsp; Z₁ = R cos(θ), Z₂ = R sin(θ)
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

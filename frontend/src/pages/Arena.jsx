import { useEffect, useState } from 'react'
import {
  Swords, Play, BarChart3, Database, Sliders, FileText, CheckCircle2, Trophy, Clock, Activity, AlertCircle,
} from 'lucide-react'
import {
  Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { api } from '../lib/api'
import { ErrorNote, Field, PageHeader, Spinner, Stat } from '../components/Shared'

const SAMPLE_TEXT =
  'It is a truth universally acknowledged that a single man in possession of a ' +
  'good fortune must be in want of a wife. However little known the feelings or ' +
  'views of such a man may be on his first entering a neighbourhood, this truth ' +
  'is so well fixed in the minds of the surrounding families that he is ' +
  'considered the rightful property of some one or other of their daughters.'

export default function Arena() {
  const [plaintext, setPlaintext] = useState(SAMPLE_TEXT)
  const [length, setLength] = useState(400)
  const [puzzle, setPuzzle] = useState(null)
  const [rows, setRows] = useState(null)
  const [target, setTarget] = useState(null)
  const [history, setHistory] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    api.arenaResults().then(setHistory).catch(() => {})
  }, [])

  async function run() {
    setBusy(true)
    setError(null)
    setRows(null)
    try {
      const trimmed = plaintext.slice(0, Number(length))
      const made = await api.encrypt({ text: trimmed, cipher: 'substitution' })
      setPuzzle(made)
      const outcome = await api.arenaRun({
        ciphertext: made.ciphertext,
        plaintext: made.plaintext,
        cipher_type: 'substitution',
      })
      setRows(outcome.results)
      setTarget(outcome.target_score_per_char)
      api.arenaResults().then(setHistory).catch(() => {})
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  const chartData =
    rows?.filter((r) => !r.error).map((r) => ({
      name: r.solver.replace(/_/g, ' '),
      accuracy: (r.accuracy ?? 0) * 100,
      seconds: r.elapsed,
    })) ?? []

  return (
    <div>
      <PageHeader
        title="Algorithm Arena"
        blurb="Head-to-head benchmark across all 5 solvers (MCMC, HMM, Hill Climbing, Steepest Ascent, Frequency Analysis) on identical ciphertexts. Standardizes scores under the shared 27x27 bigram language model."
        icon={Swords}
      >
        <button className="btn-primary shadow-lg shadow-indigo-500/25" onClick={run} disabled={busy}>
          <Play className="h-4 w-4 fill-current" />
          {busy ? 'Evaluating Solvers...' : 'Run Arena Benchmark'}
        </button>
      </PageHeader>

      <div className="grid gap-6 lg:grid-cols-[380px,1fr]">
        {/* Left Column: Benchmark Controls */}
        <div className="space-y-5">
          <div className="card space-y-4">
            <div className="flex items-center justify-between border-b border-zinc-800/80 pb-3">
              <h2 className="text-xs font-bold uppercase tracking-widest text-zinc-300 font-display flex items-center gap-2">
                <FileText className="h-4 w-4 text-indigo-400" />
                Benchmark Plaintext Input
              </h2>
              <span className="chip text-[11px] font-mono">Substitution</span>
            </div>

            <Field label="Plaintext Passage">
              <textarea
                className="input h-36 leading-relaxed"
                value={plaintext}
                onChange={(e) => setPlaintext(e.target.value)}
              />
            </Field>

            <Field label="Passage Length Limit" hint="(short texts test algorithm bounds)">
              <div className="flex items-center justify-between mb-1">
                <span className="text-[10px] font-bold uppercase text-zinc-500 font-display">Character Cutoff</span>
                <span className="font-mono text-xs font-bold text-indigo-400">{length} chars</span>
              </div>
              <input
                type="range"
                min="60"
                max={Math.max(plaintext.length, 100)}
                step="20"
                value={length}
                onChange={(e) => setLength(e.target.value)}
                className="w-full accent-indigo-500 cursor-pointer h-2 bg-zinc-950 rounded-lg border border-zinc-800"
              />
            </Field>

            {busy && <Spinner label="Running all 5 solvers in parallel..." />}
            <ErrorNote error={error} />

            <div className="rounded-xl border border-zinc-800 bg-zinc-950/60 p-3.5 text-xs text-zinc-400 leading-relaxed space-y-1">
              <strong className="text-zinc-200">Syllabus Insight:</strong> Above ~300 chars, all algorithms reach near 100%. Under 100 chars, MCMC maintains high accuracy while Hill Climbing drops into local optima and Frequency Analysis fails entirely.
            </div>
          </div>

          {puzzle && (
            <div className="card space-y-2">
              <div className="text-xs font-bold uppercase tracking-widest text-zinc-400 font-display">
                Generated Ciphertext ({puzzle.length} chars)
              </div>
              <div className="font-mono text-xs max-h-36 overflow-auto break-words rounded-xl border border-zinc-800 bg-zinc-950 p-3 text-indigo-300 leading-relaxed">
                {puzzle.ciphertext}
              </div>
            </div>
          )}
        </div>

        {/* Right Column: Charts, Comparison Table & Output Inspector */}
        <div className="space-y-5">
          {rows ? (
            <>
              {/* Accuracy Chart */}
              <div className="card space-y-4">
                <div className="flex items-center justify-between border-b border-zinc-800/80 pb-3">
                  <h2 className="text-xs font-bold uppercase tracking-widest text-zinc-300 font-display flex items-center gap-2">
                    <BarChart3 className="h-4 w-4 text-indigo-400" />
                    Decoded Accuracy (%) Across Solvers
                  </h2>
                  <span className="chip border-indigo-500/30 bg-indigo-500/10 text-indigo-300 font-mono text-[11px]">
                    Ground Truth Evaluation
                  </span>
                </div>

                <div className="h-56 w-full rounded-xl border border-zinc-800/80 bg-zinc-950/80 p-2">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={chartData} margin={{ top: 10, right: 15, bottom: 5, left: -20 }}>
                      <CartesianGrid stroke="#27272a" strokeDasharray="3 3" vertical={false} />
                      <XAxis
                        dataKey="name"
                        tick={{ fill: '#71717a', fontSize: 10, fontFamily: 'monospace' }}
                        stroke="#3f3f46"
                        interval={0}
                      />
                      <YAxis
                        domain={[0, 100]}
                        tick={{ fill: '#71717a', fontSize: 10, fontFamily: 'monospace' }}
                        stroke="#3f3f46"
                        unit="%"
                      />
                      <Tooltip
                        contentStyle={{
                          background: '#121215',
                          border: '1px solid rgba(99, 102, 241, 0.3)',
                          borderRadius: 12,
                          fontSize: 12,
                          fontFamily: 'monospace',
                        }}
                        formatter={(v, n) =>
                          n === 'accuracy' ? [`${v.toFixed(1)}%`, 'Letter Accuracy'] : [v, n]
                        }
                      />
                      <Bar dataKey="accuracy" radius={[6, 6, 0, 0]}>
                        {chartData.map((row, index) => (
                          <Cell
                            key={index}
                            fill={row.accuracy >= 95 ? '#10b981' : row.accuracy >= 50 ? '#6366f1' : '#f43f5e'}
                          />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Detailed Results Table */}
              <div className="card space-y-4 overflow-x-auto">
                <div className="flex items-center justify-between border-b border-zinc-800/80 pb-3">
                  <h2 className="text-xs font-bold uppercase tracking-widest text-zinc-300 font-display flex items-center gap-2">
                    <Trophy className="h-4 w-4 text-purple-400" />
                    Solver Performance Comparison Table
                  </h2>
                  {target != null && (
                    <span className="chip border-purple-500/30 bg-purple-500/10 text-purple-300 font-mono text-[11px]">
                      True Plaintext Fitness: {target.toFixed(3)} / char
                    </span>
                  )}
                </div>

                <table className="w-full text-xs border-collapse">
                  <thead>
                    <tr className="border-b border-zinc-800 text-zinc-500 font-display uppercase tracking-wider text-[10px]">
                      <th className="p-2.5 text-left">Solver</th>
                      <th className="p-2.5 text-right">Accuracy</th>
                      <th className="p-2.5 text-right">Score / Char</th>
                      <th className="p-2.5 text-right">Iterations</th>
                      <th className="p-2.5 text-right">Time (s)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((row) => (
                      <tr key={row.solver} className="border-b border-zinc-800/40 font-mono">
                        <td className="p-2.5 font-sans font-semibold text-zinc-200">{row.label || row.solver}</td>
                        {row.error ? (
                          <td className="p-2.5 text-rose-400 font-sans italic" colSpan={4}>
                            {row.error}
                          </td>
                        ) : (
                          <>
                            <td
                              className={`p-2.5 text-right font-bold ${
                                row.accuracy >= 0.95
                                  ? 'text-emerald-400'
                                  : row.accuracy >= 0.50
                                    ? 'text-amber-400'
                                    : 'text-rose-400'
                              }`}
                            >
                              {(row.accuracy * 100).toFixed(1)}%
                            </td>
                            <td className="p-2.5 text-right text-zinc-400">
                              {row.score_per_char?.toFixed(3)}
                            </td>
                            <td className="p-2.5 text-right text-zinc-400">
                              {row.iterations.toLocaleString()}
                            </td>
                            <td className="p-2.5 text-right text-zinc-300 font-bold">
                              {row.elapsed.toFixed(2)}s
                            </td>
                          </>
                        )}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Output Inspection per Solver */}
              <div className="card space-y-4">
                <div className="text-xs font-bold uppercase tracking-widest text-zinc-300 font-display border-b border-zinc-800/80 pb-2.5">
                  Decoded Plaintext Inspection per Solver
                </div>
                <div className="space-y-3">
                  {rows
                    .filter((r) => !r.error)
                    .map((row) => (
                      <div key={row.solver} className="rounded-xl border border-zinc-800 bg-zinc-950 p-3 space-y-1.5">
                        <div className="flex items-center justify-between text-xs">
                          <span className="font-bold font-display text-zinc-200">{row.label}</span>
                          <span className="font-mono text-[11px] text-zinc-500">
                            Key: <span className="text-indigo-300 font-bold">{row.key}</span>
                          </span>
                        </div>
                        <div className="font-mono text-xs max-h-20 overflow-auto text-zinc-300 leading-relaxed">
                          {row.plaintext}
                        </div>
                      </div>
                    ))}
                </div>
              </div>
            </>
          ) : (
            !busy && (
              <div className="card flex flex-col items-center justify-center py-16 text-center text-zinc-500 space-y-3">
                <div className="h-12 w-12 rounded-full bg-zinc-950 border border-zinc-800 flex items-center justify-center text-zinc-600">
                  <Swords className="h-6 w-6" />
                </div>
                <p className="text-sm">Click <strong className="text-zinc-300">Run Arena Benchmark</strong> to generate a ciphertext and run all 5 solvers head-to-head.</p>
              </div>
            )
          )}

          {/* SQLite Run History Summary */}
          {history?.summary?.length > 0 && (
            <div className="card space-y-3">
              <div className="flex items-center justify-between border-b border-zinc-800/80 pb-3">
                <h2 className="text-xs font-bold uppercase tracking-widest text-zinc-300 font-display flex items-center gap-2">
                  <Database className="h-4 w-4 text-indigo-400" />
                  SQLite Benchmark Execution History
                </h2>
                <span className="chip border-indigo-500/30 bg-indigo-500/10 text-indigo-300 font-mono text-[11px]">
                  Aggregated Run Statistics
                </span>
              </div>
              <table className="w-full text-xs border-collapse">
                <thead>
                  <tr className="border-b border-zinc-800 text-zinc-500 font-display uppercase tracking-wider text-[10px]">
                    <th className="p-2 text-left">Solver</th>
                    <th className="p-2 text-right">Total Runs</th>
                    <th className="p-2 text-right">Mean Accuracy</th>
                    <th className="p-2 text-right">Mean Elapsed</th>
                  </tr>
                </thead>
                <tbody>
                  {history.summary.map((row) => (
                    <tr key={row.solver} className="border-b border-zinc-800/40 font-mono">
                      <td className="p-2 font-sans font-semibold text-zinc-300">{row.solver}</td>
                      <td className="p-2 text-right text-zinc-400">{row.runs}</td>
                      <td className="p-2 text-right font-bold text-emerald-400">
                        {((row.mean_accuracy ?? 0) * 100).toFixed(1)}%
                      </td>
                      <td className="p-2 text-right text-zinc-300">
                        {row.mean_seconds.toFixed(2)}s
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

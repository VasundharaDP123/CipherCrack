import { useEffect, useMemo, useRef, useState } from 'react'
import { useLocation } from 'react-router-dom'
import {
  Play, Square, Search, Activity, Gauge, Zap, Clock, Grid, FileText, CheckCircle2, ShieldAlert, KeyRound, Radio,
} from 'lucide-react'
import {
  CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { api } from '../lib/api'
import { getSocket } from '../lib/socket'
import {
  ErrorNote, Field, KeyGrid, LiveText, PageHeader, Spinner, Stat,
} from '../components/Shared'

const DEMO =
  'YH YR M HNZHT ZAYUWNRMBBK MGLAVXBWCSWC HTMH M RYASBW JMA YA ' +
  'OVRRWRRYVA VF M SVVC FVNHZAW JZRH IW YA XMAH VF M XYFW TVXWUWN ' +
  'BYHHBW LAVXA HTW FWWBYASR VN UYWXR VF RZGT M JMA JMK IW VA TYR ' +
  'FYNRH WAHWNYAS M AWYSTIVZNTVVC HTYR HNZHT YR RV XWBB FYQWC YA HTW ' +
  'JYACR VF HTW RZNNVZACYAS FMJYBYWR HTMH TW YR GVARYCWNWC HTW ' +
  'NYSTHFZB ONVOWNHK VF RVJW VAW VN VHTWN VF HTWYN CMZSTHWNR'

export default function Crack() {
  const location = useLocation()
  const [ciphertext, setCiphertext] = useState(location.state?.ciphertext || DEMO)
  const [plaintext, setPlaintext] = useState(location.state?.plaintext || '')
  const [solver, setSolver] = useState('mcmc')
  const [proposal, setProposal] = useState('random_swap')
  const [iterations, setIterations] = useState(10000)
  const [restarts, setRestarts] = useState(10)
  const [catalogue, setCatalogue] = useState(null)

  const [running, setRunning] = useState(false)
  const [progress, setProgress] = useState(null)
  const [previous, setPrevious] = useState(null)
  const [history, setHistory] = useState([])
  const [done, setDone] = useState(null)
  const [error, setError] = useState(null)
  const [guess, setGuess] = useState(null)
  const [connected, setConnected] = useState(false)

  const previousRef = useRef(null)

  useEffect(() => {
    api.catalogue().then(setCatalogue).catch((e) => setError(e.message))
  }, [])

  useEffect(() => {
    const socket = getSocket()

    const onProgress = (update) => {
      setPrevious(previousRef.current)
      previousRef.current = update
      setProgress(update)
      setHistory((rows) => [
        ...rows.slice(-400),
        {
          iteration: update.iteration,
          score: update.score_per_char,
          best: update.best_score_per_char ?? update.score_per_char,
          accuracy: update.accuracy != null ? update.accuracy * 100 : null,
        },
      ])
    }
    const onDone = (payload) => {
      setDone(payload)
      setRunning(false)
    }
    const onError = (payload) => {
      setError(payload.error)
      setRunning(false)
    }
    const onStopped = () => setRunning(false)

    const onConnect = () => {
      setConnected(true)
      setError(null)
    }
    const onDisconnect = () => setConnected(false)
    const onConnectError = (e) => {
      setConnected(false)
      setRunning(false)
      setError(`Cannot reach the solver stream (${e.message}). Is the backend running?`)
    }

    setConnected(socket.connected)
    socket.on('connect', onConnect)
    socket.on('disconnect', onDisconnect)
    socket.on('connect_error', onConnectError)
    socket.on('crack_progress', onProgress)
    socket.on('crack_done', onDone)
    socket.on('crack_error', onError)
    socket.on('crack_stopped', onStopped)
    return () => {
      socket.off('connect', onConnect)
      socket.off('disconnect', onDisconnect)
      socket.off('connect_error', onConnectError)
      socket.off('crack_progress', onProgress)
      socket.off('crack_done', onDone)
      socket.off('crack_error', onError)
      socket.off('crack_stopped', onStopped)
    }
  }, [])

  function start() {
    setError(null)
    setDone(null)
    setHistory([])
    setProgress(null)
    setPrevious(null)
    previousRef.current = null
    setRunning(true)

    getSocket().emit('start_crack', {
      ciphertext,
      plaintext: plaintext || null,
      solver,
      options: {
        proposal,
        iterations: Number(iterations),
        restarts: Number(restarts),
      },
    })
  }

  function stop() {
    getSocket().emit('stop_crack')
  }

  async function identify() {
    setError(null)
    try {
      setGuess(await api.identify({ text: ciphertext }))
    } catch (e) {
      setError(e.message)
    }
  }

  const current = done || progress
  const text = done?.plaintext ?? progress?.text
  const keyString = done?.key ?? progress?.key
  const accuracy = done?.accuracy ?? progress?.accuracy
  const supportsProposal = solver === 'mcmc' || solver === 'hill_climbing'

  const iterationCount = done?.iterations ?? progress?.iteration ?? 0
  const restartIndex = done ? done.restarts - 1 : progress?.restart

  const cleanedTruth = useMemo(
    () => (plaintext ? plaintext.toUpperCase().replace(/[^A-Z]+/g, ' ').trim() : ''),
    [plaintext],
  )

  return (
    <div>
      <PageHeader
        title="Crack Live"
        blurb="Watch monoalphabetic substitution ciphers break in real-time over Socket.IO streams. Evaluates 50,000+ key proposals per second using NumPy bigram log-likelihoods."
        icon={KeyRound}
      >
        <div className="flex gap-2.5">
          {running ? (
            <button className="btn-danger shadow-lg shadow-rose-500/25" onClick={stop}>
              <Square className="h-4 w-4 fill-current" />
              Stop Solver
            </button>
          ) : (
            <button className="btn-primary shadow-lg shadow-indigo-500/25" onClick={start} disabled={!ciphertext.trim()}>
              <Play className="h-4 w-4 fill-current" />
              Start Live Solve
            </button>
          )}
          <button className="btn-ghost" onClick={identify}>
            <Search className="h-4 w-4 text-purple-400" />
            Identify Cipher
          </button>
        </div>
      </PageHeader>

      <div className="grid gap-6 lg:grid-cols-[380px,1fr]">
        {/* Controls Column */}
        <div className="space-y-5">
          <div className="card space-y-4">
            <div className="flex items-center justify-between border-b border-zinc-800/80 pb-3">
              <h2 className="text-xs font-bold uppercase tracking-widest text-zinc-300 font-display flex items-center gap-2">
                <FileText className="h-4 w-4 text-indigo-400" />
                Solver Configuration
              </h2>
              <span className="chip text-[11px] font-mono">27x27 Bigram Model</span>
            </div>

            <Field label="Ciphertext Input">
              <textarea
                className="input h-32 leading-relaxed"
                value={ciphertext}
                onChange={(e) => setCiphertext(e.target.value)}
                placeholder="Paste ciphertext to decrypt..."
              />
            </Field>

            <Field label="Known Ground Truth Plaintext" hint="(optional — live accuracy scoring)">
              <textarea
                className="input h-16 leading-relaxed"
                value={plaintext}
                onChange={(e) => setPlaintext(e.target.value)}
                placeholder="Leave blank if unknown"
              />
            </Field>

            <div className="grid grid-cols-2 gap-3 pt-1">
              <Field label="Algorithm">
                <select
                  className="input cursor-pointer font-sans text-xs"
                  value={solver}
                  onChange={(e) => setSolver(e.target.value)}
                >
                  {catalogue?.solvers
                    .filter((s) => s.streams)
                    .map((s) => (
                      <option key={s.name} value={s.name} className="bg-zinc-950 text-zinc-100">
                        {s.label}
                      </option>
                    ))}
                </select>
              </Field>

              <Field label="Proposal Strategy">
                <select
                  className="input cursor-pointer font-sans text-xs"
                  value={proposal}
                  disabled={!supportsProposal}
                  onChange={(e) => setProposal(e.target.value)}
                >
                  {catalogue?.proposals.map((p) => (
                    <option key={p.name} value={p.name} className="bg-zinc-950 text-zinc-100">
                      {p.label}
                    </option>
                  ))}
                </select>
              </Field>

              <Field label={solver === 'hmm' ? 'EM Steps' : 'Iterations'}>
                <input
                  className="input"
                  type="number"
                  min="100"
                  step="1000"
                  value={iterations}
                  onChange={(e) => setIterations(e.target.value)}
                />
              </Field>

              <Field label="Restarts">
                <input
                  className="input"
                  type="number"
                  min="1"
                  max="20"
                  value={restarts}
                  onChange={(e) => setRestarts(e.target.value)}
                />
              </Field>
            </div>

            <div className="rounded-xl border border-zinc-800 bg-zinc-950/60 p-3 text-xs text-zinc-400 leading-relaxed">
              {catalogue?.solvers.find((s) => s.name === solver)?.blurb}
            </div>
          </div>

          {/* Cipher Identifier Result */}
          {guess && (
            <div className="card space-y-3.5 border-purple-500/20 bg-purple-500/5">
              <div className="flex items-center justify-between border-b border-purple-500/20 pb-2.5">
                <span className="text-xs font-bold uppercase tracking-widest text-purple-300 font-display flex items-center gap-1.5">
                  <Search className="h-3.5 w-3.5 text-purple-400" />
                  Random Forest Classifier
                </span>
                <span className="chip border-purple-500/30 bg-purple-500/10 text-purple-200 font-mono text-[11px]">
                  {(guess.confidence * 100).toFixed(1)}% confidence
                </span>
              </div>
              <div className="flex items-baseline justify-between">
                <span className="text-xl font-extrabold font-display text-white capitalize">{guess.prediction}</span>
                <span className="text-xs text-zinc-400">Class Probability</span>
              </div>
              <div className="space-y-2">
                {guess.probabilities.map((row) => (
                  <div key={row.cipher} className="flex items-center gap-2 text-xs">
                    <span className="w-24 text-zinc-400 font-medium capitalize">{row.cipher}</span>
                    <div className="h-2 flex-1 overflow-hidden rounded-full bg-zinc-950 border border-zinc-800">
                      <div
                        className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-purple-500 transition-all duration-300"
                        style={{ width: `${row.probability * 100}%` }}
                      />
                    </div>
                    <span className="w-12 text-right font-mono text-zinc-300">
                      {(row.probability * 100).toFixed(0)}%
                    </span>
                  </div>
                ))}
              </div>
              {guess.prediction !== 'substitution' && (
                <div className="flex items-start gap-2 rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-200">
                  <ShieldAlert className="h-4 w-4 text-amber-400 shrink-0 mt-0.5" />
                  <div>
                    This text is predicted to be <strong className="text-amber-300 capitalize">{guess.prediction}</strong>. Solvers expect monoalphabetic substitution.
                  </div>
                </div>
              )}
            </div>
          )}

          <ErrorNote error={error} />
        </div>

        {/* Live Decryption Dashboard */}
        <div className="space-y-5">
          <div className="card space-y-4">
            <div className="flex items-center justify-between border-b border-zinc-800/80 pb-3">
              <h2 className="text-xs font-bold uppercase tracking-widest text-zinc-300 font-display flex items-center gap-2">
                <Activity className="h-4 w-4 text-indigo-400" />
                Live Telemetry &amp; Convergence Graph
              </h2>
              <div className="flex items-center gap-3">
                {running && <Spinner label="evaluating steps..." />}
                <div
                  className={`chip font-mono text-[11px] ${
                    connected
                      ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300'
                      : 'border-rose-500/30 bg-rose-500/10 text-rose-300'
                  }`}
                >
                  <Radio className={`h-3 w-3 ${connected ? 'animate-pulse text-emerald-400' : 'text-rose-400'}`} />
                  {connected ? 'Socket Live' : 'Offline'}
                </div>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <Stat
                label="Iterations"
                value={iterationCount.toLocaleString()}
                sub={restartIndex != null ? `restart #${restartIndex + 1}` : 'initial chain'}
                icon={Gauge}
              />
              <Stat
                label="Score / Char"
                value={
                  current
                    ? (current.best_score_per_char ?? current.score_per_char).toFixed(3)
                    : '—'
                }
                sub="log P(text | key)"
                tone="accent"
                icon={Activity}
              />
              <Stat
                label="Accuracy"
                value={accuracy != null ? `${(accuracy * 100).toFixed(1)}%` : '—'}
                sub={accuracy != null ? 'correct letters' : 'requires plaintext'}
                tone={accuracy >= 0.95 ? 'good' : accuracy != null ? 'warn' : 'default'}
                icon={CheckCircle2}
              />
              <Stat
                label="Elapsed Time"
                value={`${(done?.elapsed_wall ?? current?.elapsed ?? 0).toFixed(1)}s`}
                sub={
                  done
                    ? `${Math.round(done.iterations / Math.max(done.elapsed, 1e-6)).toLocaleString()} it/s`
                    : 'running...'
                }
                icon={Clock}
              />
            </div>

            {/* Recharts Convergence Plot */}
            <div className="mt-2 h-52 w-full rounded-xl border border-zinc-800/80 bg-zinc-950/80 p-2">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={history} margin={{ top: 10, right: 15, bottom: 5, left: -20 }}>
                  <CartesianGrid stroke="#27272a" strokeDasharray="3 3" vertical={false} />
                  <XAxis
                    dataKey="iteration"
                    tick={{ fill: '#71717a', fontSize: 10, fontFamily: 'monospace' }}
                    stroke="#3f3f46"
                  />
                  <YAxis
                    tick={{ fill: '#71717a', fontSize: 10, fontFamily: 'monospace' }}
                    stroke="#3f3f46"
                    domain={['auto', 'auto']}
                  />
                  <Tooltip
                    contentStyle={{
                      background: '#121215',
                      border: '1px solid rgba(99, 102, 241, 0.3)',
                      borderRadius: 12,
                      fontSize: 12,
                      fontFamily: 'monospace',
                      boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.5)',
                    }}
                    formatter={(value, name) => [
                      typeof value === 'number' ? value.toFixed(4) : value,
                      name === 'score' ? 'Current Iteration' : 'Best Key Log-Likelihood',
                    ]}
                  />
                  <Line
                    type="monotone"
                    dataKey="score"
                    name="score"
                    stroke="#818cf8"
                    strokeWidth={1.5}
                    dot={false}
                    isAnimationActive={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="best"
                    name="best"
                    stroke="#10b981"
                    strokeWidth={2}
                    dot={false}
                    isAnimationActive={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Interactive Key Grid */}
          <div className="card space-y-3">
            <div className="flex items-center justify-between border-b border-zinc-800/80 pb-2.5">
              <h2 className="text-xs font-bold uppercase tracking-widest text-zinc-300 font-display flex items-center gap-2">
                <Grid className="h-4 w-4 text-indigo-400" />
                Substitution Key Matrix (A–Z)
              </h2>
              <span className="text-[11px] text-zinc-500 font-mono">Cell scale effect on proposal swaps</span>
            </div>
            <KeyGrid decryptionKey={keyString} previousKey={previous?.key} />
          </div>

          {/* Decoded Text Viewer */}
          <div className="card space-y-3">
            <div className="flex items-center justify-between border-b border-zinc-800/80 pb-2.5">
              <h2 className="text-xs font-bold uppercase tracking-widest text-zinc-300 font-display flex items-center gap-2">
                <Zap className="h-4 w-4 text-emerald-400" />
                Live Decoded Plaintext Stream
              </h2>
              {done && (
                <span className="chip border-emerald-500/30 bg-emerald-500/10 text-emerald-300 font-mono text-[11px]">
                  {done.stopped_early ? 'Terminated Early' : 'Complete'} &middot; {done.iterations.toLocaleString()} Iterations
                </span>
              )}
            </div>
            <div className="max-h-64 overflow-auto rounded-xl border border-zinc-800 bg-zinc-950 p-4">
              <LiveText text={text} previous={previous?.text} truth={cleanedTruth || null} />
            </div>

            {done?.viterbi_text && (
              <div className="mt-4 space-y-2 pt-2 border-t border-zinc-800/80">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold uppercase tracking-widest text-purple-300 font-display">
                    Viterbi Max-Likelihood Path (HMM State Sequence)
                  </span>
                  <span className="chip border-purple-500/30 bg-purple-500/10 text-purple-300 font-mono text-[11px]">
                    Dynamic Programming
                  </span>
                </div>
                <div className="max-h-28 overflow-auto rounded-xl border border-purple-500/20 bg-purple-500/5 p-3.5">
                  <LiveText text={done.viterbi_text} truth={cleanedTruth || null} />
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

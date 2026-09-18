import { useEffect, useMemo, useRef, useState } from 'react'
import {
  Trophy, Bot, Sparkles, Clock, Award, User, CheckCircle2, Save, Play, RefreshCw, Zap,
} from 'lucide-react'
import { api } from '../lib/api'
import { getSocket, LETTERS } from '../lib/socket'
import { ErrorNote, PageHeader, Spinner, Stat } from '../components/Shared'

const DIFFICULTIES = ['easy', 'medium', 'hard']

function accuracyOf(guess, truth) {
  let correct = 0
  let total = 0
  for (let i = 0; i < truth.length; i += 1) {
    if (truth[i] === ' ') continue
    total += 1
    if (guess[i] === truth[i]) correct += 1
  }
  return total ? correct / total : 0
}

export default function Challenge() {
  const [difficulty, setDifficulty] = useState('medium')
  const [puzzle, setPuzzle] = useState(null)
  const [mapping, setMapping] = useState({})
  const [selected, setSelected] = useState(null)
  const [startedAt, setStartedAt] = useState(null)
  const [now, setNow] = useState(Date.now())
  const [finished, setFinished] = useState(null)

  const [aiRunning, setAiRunning] = useState(false)
  const [aiProgress, setAiProgress] = useState(null)
  const [aiResult, setAiResult] = useState(null)

  const [board, setBoard] = useState(null)
  const [player, setPlayer] = useState('')
  const [error, setError] = useState(null)
  const [saved, setSaved] = useState(false)
  const tick = useRef(null)

  useEffect(() => {
    api.leaderboard().then(setBoard).catch(() => {})
  }, [])

  useEffect(() => {
    tick.current = setInterval(() => setNow(Date.now()), 250)
    return () => clearInterval(tick.current)
  }, [])

  useEffect(() => {
    const socket = getSocket()
    const onProgress = (u) => setAiProgress(u)
    const onDone = (payload) => {
      setAiResult(payload)
      setAiRunning(false)
    }
    const onError = (payload) => {
      setError(payload.error)
      setAiRunning(false)
    }
    socket.on('crack_progress', onProgress)
    socket.on('crack_done', onDone)
    socket.on('crack_error', onError)
    return () => {
      socket.off('crack_progress', onProgress)
      socket.off('crack_done', onDone)
      socket.off('crack_error', onError)
    }
  }, [])

  async function newGame(level = difficulty) {
    setError(null)
    setSaved(false)
    setFinished(null)
    setAiResult(null)
    setAiProgress(null)
    setSelected(null)
    try {
      const fresh = await api.newChallenge(level)
      setPuzzle(fresh)
      setMapping({ ...fresh.hints })
      setStartedAt(Date.now())
    } catch (e) {
      setError(e.message)
    }
  }

  const decoded = useMemo(() => {
    if (!puzzle) return ''
    return puzzle.ciphertext
      .split('')
      .map((ch) => (ch === ' ' ? ' ' : mapping[ch] || '·'))
      .join('')
  }, [puzzle, mapping])

  const humanAccuracy = puzzle ? accuracyOf(decoded, puzzle.plaintext) : 0
  const elapsed = startedAt && !finished ? (now - startedAt) / 1000 : finished?.seconds ?? 0

  useEffect(() => {
    if (!puzzle || finished || !startedAt) return
    if (humanAccuracy >= 0.999) {
      setFinished({ seconds: (Date.now() - startedAt) / 1000, accuracy: humanAccuracy })
    }
  }, [humanAccuracy, puzzle, finished, startedAt])

  function assign(plainLetter) {
    if (!selected) return
    setMapping((current) => {
      const next = { ...current }
      for (const [cipher, plain] of Object.entries(next)) {
        if (plain === plainLetter) delete next[cipher]
      }
      next[selected] = plainLetter
      return next
    })
    setSelected(null)
  }

  function clearLetter(cipherLetter) {
    setMapping((current) => {
      const next = { ...current }
      delete next[cipherLetter]
      return next
    })
  }

  function raceAI() {
    if (!puzzle) return
    setAiRunning(true)
    setAiResult(null)
    getSocket().emit('start_crack', {
      ciphertext: puzzle.ciphertext,
      plaintext: puzzle.plaintext,
      solver: 'mcmc',
      cipher_type: 'substitution',
      options: { iterations: 10000, restarts: 10, proposal: 'random_swap' },
    })
  }

  async function saveScore() {
    try {
      const body = await api.addScore({
        player: player || 'anonymous',
        text_length: puzzle.length,
        difficulty: puzzle.difficulty,
        human_seconds: finished?.seconds ?? elapsed,
        human_accuracy: humanAccuracy,
        ai_seconds: aiResult?.elapsed ?? null,
        ai_accuracy: aiResult?.accuracy ?? null,
      })
      setBoard({ ...board, scores: body.scores })
      setSaved(true)
    } catch (e) {
      setError(e.message)
    }
  }

  const usedPlain = new Set(Object.values(mapping))
  const cipherLetters = puzzle
    ? [...new Set(puzzle.ciphertext.replace(/ /g, '').split(''))].sort()
    : []

  return (
    <div>
      <PageHeader
        title="Challenge Mode"
        blurb="Race head-to-head against MCMC AI to break substitution ciphers manually. Build your substitution key letter by letter or launch the AI solver concurrently."
        icon={Trophy}
      >
        <div className="flex gap-2.5">
          <select
            className="input cursor-pointer font-sans text-xs w-36 capitalize"
            value={difficulty}
            onChange={(e) => {
              setDifficulty(e.target.value)
              newGame(e.target.value)
            }}
          >
            {DIFFICULTIES.map((d) => (
              <option key={d} value={d} className="bg-cyber-950 text-slate-100 capitalize">
                {d} difficulty
              </option>
            ))}
          </select>
          <button className="btn-primary shadow-lg shadow-cyan-500/25" onClick={() => newGame()}>
            <RefreshCw className="h-4 w-4" />
            New Challenge Puzzle
          </button>
        </div>
      </PageHeader>

      <ErrorNote error={error} />

      {!puzzle ? (
        <div className="card flex flex-col items-center justify-center py-20 text-center text-slate-500 space-y-3">
          <div className="h-12 w-12 rounded-full bg-cyber-950 border border-slate-800 flex items-center justify-center text-slate-600">
            <Trophy className="h-6 w-6 text-amber-400" />
          </div>
          <p className="text-sm">Click <strong className="text-slate-300">New Challenge Puzzle</strong> to initiate the race.</p>
        </div>
      ) : (
        <div className="grid gap-6 lg:grid-cols-[1fr,360px]">
          {/* Main Board Column */}
          <div className="space-y-5">
            <div className="card space-y-4">
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                <Stat label="Your Time" value={`${elapsed.toFixed(1)}s`} icon={Clock} tone="accent" />
                <Stat
                  label="Your Accuracy"
                  value={`${(humanAccuracy * 100).toFixed(0)}%`}
                  tone={humanAccuracy >= 0.95 ? 'good' : 'warn'}
                  icon={CheckCircle2}
                />
                <Stat
                  label="AI Solver Time"
                  value={aiResult ? `${aiResult.elapsed.toFixed(2)}s` : aiRunning ? 'Solving...' : '—'}
                  tone="purple"
                  icon={Bot}
                />
                <Stat
                  label="AI Accuracy"
                  value={
                    aiResult?.accuracy != null
                      ? `${(aiResult.accuracy * 100).toFixed(0)}%`
                      : aiProgress?.accuracy != null
                        ? `${(aiProgress.accuracy * 100).toFixed(0)}%`
                        : '—'
                  }
                  tone="purple"
                  icon={Award}
                />
              </div>

              {finished && (
                <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-4 text-xs font-semibold text-emerald-200 flex items-center gap-3">
                  <CheckCircle2 className="h-5 w-5 text-emerald-400 shrink-0" />
                  <div>
                    Puzzle solved in <strong className="text-white">{finished.seconds.toFixed(1)}s</strong>!
                    {aiResult &&
                      (finished.seconds < aiResult.elapsed
                        ? ' Victory! You outpaced the MCMC AI solver.'
                        : ` AI finished in ${aiResult.elapsed.toFixed(2)}s.`)}
                  </div>
                </div>
              )}

              <div>
                <div className="text-[10px] font-bold uppercase tracking-widest text-slate-500 font-display mb-1.5">
                  Ciphertext Challenge
                </div>
                <div className="font-mono text-xs max-h-36 overflow-auto break-words rounded-xl border border-slate-800 bg-cyber-950 p-4 text-cyan-300 leading-relaxed">
                  {puzzle.ciphertext}
                </div>
              </div>

              <div>
                <div className="text-[10px] font-bold uppercase tracking-widest text-slate-500 font-display mb-1.5">
                  Your Decoded Output Stream
                </div>
                <div className="font-mono text-xs max-h-36 overflow-auto break-words rounded-xl border border-slate-800 bg-cyber-950 p-4 leading-relaxed">
                  {decoded.split('').map((ch, i) => (
                    <span
                      key={i}
                      className={
                        ch === '·'
                          ? 'text-slate-700'
                          : puzzle.plaintext[i] === ch
                            ? 'text-emerald-400 font-semibold'
                            : 'text-rose-400'
                      }
                    >
                      {ch}
                    </span>
                  ))}
                </div>
              </div>
            </div>

            {/* Substitution Mapping Controls */}
            <div className="card space-y-4">
              <div>
                <div className="text-xs font-bold uppercase tracking-widest text-slate-300 font-display flex items-center justify-between border-b border-slate-800/80 pb-2.5">
                  <span>1. Select Ciphertext Letter</span>
                  {selected && <span className="text-cyan-400 font-mono text-[11px]">Selected: [{selected}]</span>}
                </div>
                <div className="flex flex-wrap gap-2 pt-3">
                  {cipherLetters.map((letter) => (
                    <button
                      key={letter}
                      onClick={() => setSelected(letter === selected ? null : letter)}
                      onDoubleClick={() => clearLetter(letter)}
                      className={`font-mono text-xs rounded-lg border px-2.5 py-1.5 transition-all cursor-pointer ${
                        selected === letter
                          ? 'border-cyan-400 bg-cyan-500/20 text-cyan-200 font-bold shadow-md shadow-cyan-500/30'
                          : mapping[letter]
                            ? 'border-purple-500/30 bg-purple-500/10 text-purple-200 font-semibold'
                            : 'border-slate-800 bg-cyber-950 text-slate-400 hover:border-slate-700 hover:text-slate-200'
                      }`}
                      title="Double-click to clear mapping"
                    >
                      {letter}
                      <span className="ml-1 text-[10px] text-cyan-400 font-bold">
                        →{mapping[letter] || '·'}
                      </span>
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <div className="text-xs font-bold uppercase tracking-widest text-slate-300 font-display border-b border-slate-800/80 pb-2.5">
                  2. Assign Target Plaintext Letter
                </div>
                <div className="flex flex-wrap gap-2 pt-3">
                  {LETTERS.split('').map((letter) => (
                    <button
                      key={letter}
                      disabled={!selected}
                      onClick={() => assign(letter)}
                      className={`font-mono text-xs rounded-lg border px-3 py-1.5 transition-all disabled:opacity-30 disabled:cursor-not-allowed ${
                        usedPlain.has(letter)
                          ? 'border-pink-500/30 bg-pink-500/10 text-pink-300 font-bold'
                          : 'border-slate-800 bg-cyber-950 text-slate-300 hover:bg-slate-800 hover:text-white cursor-pointer'
                      }`}
                    >
                      {letter}
                    </button>
                  ))}
                </div>
                <p className="mt-2 text-[11px] text-slate-500">
                  Pink letters are already mapped. Double-click a cipher letter to remove mapping.
                </p>
              </div>
            </div>
          </div>

          {/* Right Column: Race AI & Leaderboard */}
          <div className="space-y-5">
            <div className="card space-y-4">
              <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
                <h2 className="text-xs font-bold uppercase tracking-widest text-slate-300 font-display flex items-center gap-2">
                  <Bot className="h-4 w-4 text-purple-400" />
                  Race Against AI Solver
                </h2>
                <span className="chip border-purple-500/30 bg-purple-500/10 text-purple-300 font-mono text-[11px]">
                  MCMC Metropolis
                </span>
              </div>
              <button className="btn-secondary w-full py-3" onClick={raceAI} disabled={aiRunning}>
                <Zap className="h-4 w-4" />
                {aiRunning ? 'AI Solving in Progress...' : 'Launch Concurrent AI Solver'}
              </button>
              {aiRunning && <Spinner label={`MCMC step ${aiProgress?.iteration ?? 0}`} />}
              {aiProgress && (
                <div className="font-mono text-xs max-h-24 overflow-auto rounded-xl border border-slate-800 bg-cyber-950 p-3 text-slate-400 leading-relaxed">
                  {aiProgress.text?.slice(0, 200)}
                </div>
              )}
            </div>

            {(finished || humanAccuracy > 0.5) && (
              <div className="card space-y-3 border-emerald-500/20 bg-emerald-500/5">
                <div className="text-xs font-bold uppercase tracking-widest text-emerald-300 font-display flex items-center gap-1.5">
                  <Award className="h-4 w-4 text-emerald-400" />
                  Save Score to Leaderboard
                </div>
                <input
                  className="input"
                  placeholder="Enter your player handle..."
                  value={player}
                  onChange={(e) => setPlayer(e.target.value)}
                  maxLength={40}
                />
                <button className="btn-primary w-full py-2.5" onClick={saveScore} disabled={saved}>
                  <Save className="h-4 w-4" />
                  {saved ? 'Score Registered!' : 'Save Score'}
                </button>
              </div>
            )}

            {/* Leaderboard Table */}
            <div className="card space-y-3">
              <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
                <h2 className="text-xs font-bold uppercase tracking-widest text-slate-300 font-display flex items-center gap-2">
                  <Trophy className="h-4 w-4 text-amber-400" />
                  Global Leaderboard
                </h2>
                <span className="chip border-amber-500/30 bg-amber-500/10 text-amber-300 font-mono text-[11px]">
                  SQLite Storage
                </span>
              </div>
              {board?.scores?.length ? (
                <table className="w-full text-xs border-collapse">
                  <thead>
                    <tr className="border-b border-slate-800 text-slate-500 font-display uppercase tracking-wider text-[10px]">
                      <th className="p-2 text-left">Player</th>
                      <th className="p-2 text-right">Accuracy</th>
                      <th className="p-2 text-right">Time</th>
                      <th className="p-2 text-right">Winner</th>
                    </tr>
                  </thead>
                  <tbody>
                    {board.scores.map((row) => (
                      <tr key={row.id} className="border-b border-slate-800/40 font-mono">
                        <td className="p-2 font-sans font-semibold text-slate-300">{row.player}</td>
                        <td className="p-2 text-right text-emerald-400 font-bold">
                          {(row.human_accuracy * 100).toFixed(0)}%
                        </td>
                        <td className="p-2 text-right text-slate-400">
                          {row.human_seconds.toFixed(0)}s
                        </td>
                        <td
                          className={`p-2 text-right font-sans capitalize font-semibold ${
                            row.winner === 'human' ? 'text-emerald-400' : 'text-slate-500'
                          }`}
                        >
                          {row.winner}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <p className="text-xs text-slate-500 italic py-2">No leaderboard entries recorded yet.</p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

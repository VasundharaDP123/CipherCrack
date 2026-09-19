import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Lock, Dices, Copy, Check, ArrowRight, RotateCcw, Key, FileText, Sparkles,
} from 'lucide-react'
import { api } from '../lib/api'
import { ErrorNote, Field, PageHeader, Stat } from '../components/Shared'

const SAMPLE =
  'Meet me at midnight by the old oak tree and bring the lantern with you, ' +
  'because the path through the woods is darker than you remember and the ' +
  'bridge has been out since the storm last winter.'

export default function Encrypt() {
  const [catalogue, setCatalogue] = useState(null)
  const [text, setText] = useState(SAMPLE)
  const [cipher, setCipher] = useState('substitution')
  const [key, setKey] = useState('')
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [copied, setCopied] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    api.catalogue().then(setCatalogue).catch((e) => setError(e.message))
  }, [])

  const info = catalogue?.ciphers.find((c) => c.name === cipher)

  async function run() {
    setError(null)
    try {
      setResult(await api.encrypt({ text, cipher, key: key || null }))
    } catch (e) {
      setError(e.message)
    }
  }

  async function roll() {
    try {
      const { key: fresh } = await api.randomKey(cipher)
      setKey(fresh)
    } catch (e) {
      setError(e.message)
    }
  }

  function copy() {
    if (!result?.ciphertext) return
    navigator.clipboard?.writeText(result.ciphertext)
    setCopied(true)
    setTimeout(() => setCopied(false), 1400)
  }

  function sendToCrack() {
    if (!result?.ciphertext) return
    navigate('/crack', {
      state: { ciphertext: result.ciphertext, plaintext: result.plaintext },
    })
  }

  return (
    <div>
      <PageHeader
        title="Encrypt Lab"
        blurb="Create encrypted puzzles using classical ciphers (Caesar, Substitution, Vigenère, Transposition). Hand the generated ciphertext straight to the solvers."
        icon={Lock}
      />

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Input Configuration */}
        <div className="card space-y-5">
          <div className="flex items-center justify-between border-b border-cyber-800/80 pb-3">
            <h2 className="text-sm font-bold uppercase tracking-widest text-slate-300 font-display flex items-center gap-2">
              <FileText className="h-4 w-4 text-solar-400" />
              1. Plaintext Message
            </h2>
            <button
              className="text-xs text-slate-400 hover:text-solar-400 flex items-center gap-1 transition"
              onClick={() => setText(SAMPLE)}
            >
              <RotateCcw className="h-3.5 w-3.5" />
              Reset Sample
            </button>
          </div>

          <Field label="Plaintext Body">
            <textarea
              className="input h-40 resize-y leading-relaxed"
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Type your plaintext message here..."
            />
          </Field>

          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Cipher Algorithm">
              <select
                className="input cursor-pointer font-sans"
                value={cipher}
                onChange={(e) => {
                  setCipher(e.target.value)
                  setKey('')
                }}
              >
                {catalogue?.ciphers.map((c) => (
                  <option key={c.name} value={c.name} className="bg-cyber-950 text-slate-100">
                    {c.label}
                  </option>
                ))}
              </select>
            </Field>

            <Field label="Decryption Key" hint={info?.key_hint || 'leave empty for random'}>
              <div className="flex gap-2">
                <input
                  className="input tracking-wider"
                  value={key}
                  onChange={(e) => setKey(e.target.value.toUpperCase())}
                  placeholder="AUTO-RANDOM"
                />
                <button
                  className="btn-ghost shrink-0 px-3"
                  onClick={roll}
                  type="button"
                  title="Generate Random Key"
                >
                  <Dices className="h-4 w-4 text-solar-400" />
                  Roll
                </button>
              </div>
            </Field>
          </div>

          <div className="pt-2 flex flex-wrap gap-3">
            <button className="btn-primary flex-1 py-3" onClick={run}>
              <Sparkles className="h-4 w-4" />
              Generate Encrypted Ciphertext
            </button>
          </div>

          <ErrorNote error={error} />
        </div>

        {/* Generated Output Puzzle */}
        <div className="card space-y-5">
          <div className="flex items-center justify-between border-b border-cyber-800/80 pb-3">
            <h2 className="text-sm font-bold uppercase tracking-widest text-slate-300 font-display flex items-center gap-2">
              <Key className="h-4 w-4 text-neon-violet" />
              2. Encrypted Output Puzzle
            </h2>
            {result && (
              <span className="chip-violet font-mono text-[11px]">
                Ready for Cryptanalysis
              </span>
            )}
          </div>

          {!result ? (
            <div className="flex flex-col items-center justify-center py-16 text-center text-slate-500 space-y-3">
              <div className="h-12 w-12 rounded-full bg-cyber-950 border border-cyber-800 flex items-center justify-center text-slate-600">
                <Lock className="h-6 w-6" />
              </div>
              <p className="text-sm">Configure your message on the left and click <strong className="text-slate-300">Generate</strong> to inspect the ciphertext output.</p>
            </div>
          ) : (
            <div className="space-y-5">
              <div className="grid grid-cols-3 gap-3">
                <Stat label="Cipher Type" value={result.cipher} tone="purple" />
                <Stat label="Length" value={result.length} sub="characters" tone="warn" />
                <Stat
                  label="Log-Prob / Char"
                  value={result.score_per_char.toFixed(2)}
                  sub="English fitness"
                  tone={result.score_per_char > -3.5 ? 'good' : 'warn'}
                />
              </div>

              <div>
                <Field label="Key Used">
                  <div className="font-mono text-xs break-all rounded-xl border border-neon-violet/30 bg-neon-violet/10 p-3 text-purple-200 font-black tracking-wider shadow-glow-violet">
                    {result.key}
                  </div>
                </Field>
              </div>

              <div>
                <Field label="Ciphertext Output">
                  <div className="font-mono text-xs max-h-48 overflow-auto break-words rounded-xl border border-cyber-800 bg-cyber-950 p-4 leading-relaxed text-solar-400 font-bold glow-text-solar">
                    {result.ciphertext}
                  </div>
                </Field>
              </div>

              <div className="flex flex-wrap gap-3 pt-2">
                <button className="btn-primary flex-1 py-3" onClick={sendToCrack}>
                  <span>Send to Crack Live</span>
                  <ArrowRight className="h-4 w-4" />
                </button>
                <button className="btn-ghost py-3" onClick={copy}>
                  {copied ? (
                    <>
                      <Check className="h-4 w-4 text-matrix-400" />
                      Copied!
                    </>
                  ) : (
                    <>
                      <Copy className="h-4 w-4" />
                      Copy Text
                    </>
                  )}
                </button>
              </div>

              <div className="rounded-xl border border-cyber-800 bg-cyber-950/60 p-3.5 text-xs text-slate-400 leading-relaxed">
                <strong className="text-slate-300">Note:</strong> Transposition ciphers strip whitespace and non-alpha characters. Monoalphabetic substitution and Caesar preserve word spaces, providing structural hints for statistical bigram scoring.
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

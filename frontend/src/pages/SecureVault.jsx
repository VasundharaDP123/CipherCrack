import { useState, useCallback } from 'react'
import {
  ShieldCheck, Cpu, KeyRound, Lock, Copy, Check, Dices, RefreshCw,
  Eye, EyeOff, ChevronRight, ArrowRight, Sparkles, AlertTriangle,
} from 'lucide-react'
import { api } from '../lib/api'
import { ErrorNote, Field, PageHeader, Stat, Spinner } from '../components/Shared'

/* ─────────────────────────────────────────────────────────────── helpers ── */

const SAMPLE_MSG =
  'The quick brown fox jumps over the lazy dog near the river bank at dawn.'

function useCopy() {
  const [copied, setCopied] = useState(false)
  const copy = useCallback((text) => {
    navigator.clipboard?.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 1400)
  }, [])
  return [copied, copy]
}

function CopyBtn({ text, className = '' }) {
  const [copied, copy] = useCopy()
  return (
    <button
      className={`btn-ghost px-3 py-2 text-xs shrink-0 ${className}`}
      onClick={() => copy(text)}
      title="Copy to clipboard"
    >
      {copied ? (
        <><Check className="h-3.5 w-3.5 text-matrix-400" /> Copied</>
      ) : (
        <><Copy className="h-3.5 w-3.5" /> Copy</>
      )}
    </button>
  )
}

function MonoBox({ value, label, tone = 'default', truncate = 260 }) {
  const [expand, setExpand] = useState(false)
  const tones = {
    default:  'border-cyber-800 bg-cyber-950 text-slate-300',
    green:    'border-matrix-500/40 bg-matrix-500/10 text-matrix-300 shadow-glow-matrix',
    orange:   'border-solar-500/40  bg-solar-500/10  text-solar-300  shadow-glow-solar',
    violet:   'border-neon-violet/40 bg-neon-violet/10 text-purple-200 shadow-glow-violet',
  }
  const shown = (!expand && value && value.length > truncate)
    ? value.slice(0, truncate) + '…'
    : value || ''
  return (
    <div className="space-y-1">
      {label && <div className="label">{label}</div>}
      <div className={`relative rounded-xl border p-3 font-mono text-xs leading-relaxed break-all ${tones[tone]}`}>
        {shown}
        {value && value.length > truncate && (
          <button
            className="ml-1 text-slate-500 hover:text-slate-300 underline text-[11px]"
            onClick={() => setExpand(e => !e)}
          >
            {expand ? 'collapse' : `+${value.length - truncate} more`}
          </button>
        )}
      </div>
    </div>
  )
}

/* ═══════════════════════════════════════════════ TASK 1-A  Vigenère Tab ═══ */

const SAMPLE_KEYWORD = 'CIPHER'

function vigenereShifts(keyword) {
  const kw = keyword.toUpperCase().replace(/[^A-Z]/g, '')
  return kw.split('').map(c => ({ letter: c, shift: c.charCodeAt(0) - 65 }))
}

export function VigenereSection() {
  const [keyword, setKeyword]   = useState(SAMPLE_KEYWORD)
  const [plaintext, setPlain]   = useState(SAMPLE_MSG)
  const [ciphertext, setCipher] = useState('')
  const [decInput, setDecInput] = useState('')
  const [decResult, setDecResult] = useState('')
  const [encResult, setEncResult] = useState(null)
  const [loading, setLoading]   = useState(false)
  const [loadingDec, setLoadingDec] = useState(false)
  const [error, setError]       = useState(null)
  const [decError, setDecError] = useState(null)

  async function rollKey() {
    try {
      const { key } = await api.randomKey('vigenere')
      setKeyword(key)
    } catch (e) { setError(e.message) }
  }

  async function encrypt() {
    if (!plaintext.trim()) return setError('Plaintext is required')
    if (!keyword.trim())   return setError('Keyword is required')
    setLoading(true); setError(null)
    try {
      const r = await api.encrypt({ text: plaintext, cipher: 'vigenere', key: keyword })
      setEncResult(r)
      setCipher(r.ciphertext)
      setDecInput(r.ciphertext)
    } catch (e) { setError(e.message) }
    finally { setLoading(false) }
  }

  async function decrypt() {
    if (!decInput.trim()) return setDecError('Ciphertext is required')
    if (!keyword.trim())  return setDecError('Keyword is required')
    setLoadingDec(true); setDecError(null)
    try {
      const r = await api.decrypt({ text: decInput, cipher: 'vigenere', key: keyword })
      setDecResult(r.plaintext)
    } catch (e) { setDecError(e.message) }
    finally { setLoadingDec(false) }
  }

  const shifts = vigenereShifts(keyword)

  return (
    <div className="space-y-6">
      {/* Theory banner */}
      <div className="rounded-2xl border border-matrix-500/30 bg-gradient-to-r from-matrix-500/10 via-cyber-900 to-cyber-900 p-5 flex flex-col sm:flex-row gap-4">
        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-matrix-500/20 border border-matrix-500/30 shadow-glow-matrix">
          <KeyRound className="h-6 w-6 text-matrix-400" />
        </div>
        <div className="space-y-1">
          <p className="font-display font-bold text-sm text-matrix-300">
            Polyalphabetic Substitution — Vigenère Cipher (1553)
          </p>
          <p className="text-xs text-slate-400 leading-relaxed">
            Unlike Caesar's single shift, Vigenère applies a <em>cycling keyword</em> so each letter of the
            plaintext is shifted by a <em>different</em> amount. For keyword <strong className="text-matrix-400">{keyword || 'KEY'}</strong>,
            the same plaintext letter encrypts to a different ciphertext letter each time it appears,
            defeating simple frequency analysis. Key space: 26<sup>k</sup> where k = keyword length.
          </p>
        </div>
      </div>

      {/* Keyword + shift table */}
      <div className="card space-y-4">
        <h3 className="text-xs font-bold uppercase tracking-widest text-slate-300 font-display">
          Keyword Configuration — Shift Table
        </h3>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Keyword (cycling shifts)">
            <div className="flex gap-2">
              <input
                className="input tracking-widest uppercase"
                value={keyword}
                onChange={e => setKeyword(e.target.value.toUpperCase().replace(/[^A-Z]/g, ''))}
                placeholder="e.g. CIPHER"
                maxLength={20}
              />
              <button className="btn-ghost shrink-0 px-3" onClick={rollKey} title="Random keyword">
                <Dices className="h-4 w-4 text-matrix-400" /> Roll
              </button>
            </div>
          </Field>
          <div className="flex flex-col justify-end">
            <div className="label">Shift Values per Position</div>
            <div className="flex flex-wrap gap-1.5 mt-1">
              {shifts.length > 0 ? shifts.map((s, i) => (
                <div key={i} className="flex flex-col items-center rounded-lg border border-matrix-500/30 bg-matrix-500/10 px-2.5 py-1.5 min-w-[40px]">
                  <span className="font-mono text-sm font-black text-matrix-300">{s.letter}</span>
                  <span className="font-mono text-[10px] text-slate-400">+{s.shift}</span>
                </div>
              )) : (
                <span className="text-xs text-slate-500 italic">Enter a keyword above</span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Encrypt + Decrypt panels */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Encrypt */}
        <div className="card space-y-4">
          <h3 className="text-xs font-bold uppercase tracking-widest text-matrix-400 font-display border-b border-cyber-800/80 pb-2">
            ① Encrypt Plaintext → Ciphertext
          </h3>
          <Field label="Plaintext Message">
            <textarea
              className="input h-28 resize-y leading-relaxed"
              value={plaintext}
              onChange={e => setPlain(e.target.value)}
              placeholder="Type your message…"
            />
          </Field>
          <button className="btn-primary w-full py-2.5" onClick={encrypt} disabled={loading}>
            {loading ? <Spinner label="encrypting…" /> : <><Lock className="h-4 w-4" /> Encrypt with Vigenère</>}
          </button>
          <ErrorNote error={error} />
          {encResult && (
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <Stat label="Key Used" value={encResult.key} tone="accent" />
                <Stat label="Length" value={encResult.length} sub="characters" tone="default" />
              </div>
              <div className="flex items-end gap-2">
                <div className="flex-1">
                  <MonoBox label="Ciphertext Output" value={ciphertext} tone="orange" />
                </div>
                <CopyBtn text={ciphertext} />
              </div>
              <button
                className="text-xs text-solar-400 hover:text-solar-300 flex items-center gap-1 transition"
                onClick={() => setDecInput(ciphertext)}
              >
                <ArrowRight className="h-3.5 w-3.5" /> Use in Decrypt panel
              </button>
            </div>
          )}
        </div>

        {/* Decrypt */}
        <div className="card space-y-4">
          <h3 className="text-xs font-bold uppercase tracking-widest text-neon-violet font-display border-b border-cyber-800/80 pb-2">
            ② Decrypt Ciphertext → Plaintext
          </h3>
          <Field label="Ciphertext Input">
            <textarea
              className="input h-28 resize-y leading-relaxed font-mono"
              value={decInput}
              onChange={e => setDecInput(e.target.value)}
              placeholder="Paste ciphertext here…"
            />
          </Field>
          <button className="btn-primary w-full py-2.5" onClick={decrypt} disabled={loadingDec}>
            {loadingDec ? <Spinner label="decrypting…" /> : <><KeyRound className="h-4 w-4" /> Decrypt with Vigenère</>}
          </button>
          <ErrorNote error={decError} />
          {decResult && (
            <div className="space-y-3">
              <div className="flex items-end gap-2">
                <div className="flex-1">
                  <MonoBox label="Recovered Plaintext" value={decResult} tone="green" />
                </div>
                <CopyBtn text={decResult} />
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

/* ═══════════════════════════════════════════════ TASK 1-B  AES-256 Tab ════ */

export function AesSection() {
  const [bits, setBits]         = useState(256)
  const [aesKey, setAesKey]     = useState('')
  const [plaintext, setPlain]   = useState(SAMPLE_MSG)
  const [ciphertext, setCipher] = useState('')
  const [decInput, setDecInput] = useState('')
  const [decInput2, setDecKey]  = useState('')
  const [decResult, setDecResult] = useState(null)
  const [encResult, setEncResult] = useState(null)
  const [loadingKey, setLKey]   = useState(false)
  const [loadingEnc, setLEnc]   = useState(false)
  const [loadingDec, setLDec]   = useState(false)
  const [encError, setEncErr]   = useState(null)
  const [decError, setDecErr]   = useState(null)

  async function genKey() {
    setLKey(true)
    try {
      const r = await api.aesKeygen(bits)
      setAesKey(r.key)
      setDecKey(r.key)
    } catch (e) { setEncErr(e.message) }
    finally { setLKey(false) }
  }

  async function encryptAES() {
    if (!plaintext.trim()) return setEncErr('Plaintext is required')
    if (!aesKey.trim())    return setEncErr('Generate or paste a key first')
    setLEnc(true); setEncErr(null)
    try {
      const r = await api.aesEncrypt({ plaintext, key: aesKey })
      setEncResult(r)
      setCipher(r.ciphertext)
      setDecInput(r.ciphertext)
      setDecKey(aesKey)
    } catch (e) { setEncErr(e.message) }
    finally { setLEnc(false) }
  }

  async function decryptAES() {
    if (!decInput.trim()) return setDecErr('Ciphertext is required')
    if (!decInput2.trim()) return setDecErr('Key is required')
    setLDec(true); setDecErr(null)
    try {
      const r = await api.aesDecrypt({ ciphertext: decInput, key: decInput2 })
      setDecResult(r)
    } catch (e) { setDecErr(e.message) }
    finally { setLDec(false) }
  }

  const BIT_OPTS = [128, 192, 256]

  return (
    <div className="space-y-6">
      {/* Theory banner */}
      <div className="rounded-2xl border border-solar-500/30 bg-gradient-to-r from-solar-500/10 via-cyber-900 to-cyber-900 p-5 flex flex-col sm:flex-row gap-4">
        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-solar-500/20 border border-solar-500/30 shadow-glow-solar">
          <Cpu className="h-6 w-6 text-solar-400" />
        </div>
        <div className="space-y-1">
          <p className="font-display font-bold text-sm text-solar-300">
            AES-256 · Advanced Encryption Standard (FIPS 197, 2001)
          </p>
          <p className="text-xs text-slate-400 leading-relaxed">
            AES is a symmetric block cipher operating on 128-bit blocks with 128/192/<strong className="text-solar-400">256-bit</strong> keys
            (10/12/14 rounds). CBC mode chains each block with the previous ciphertext block (XOR) before
            encryption, using a random IV per message. PKCS7 padding handles arbitrary-length messages.
            Key space: 2²⁵⁶ ≈ 10⁷⁷ — brute-force impossible by any classical computer.
          </p>
        </div>
      </div>

      {/* Key management */}
      <div className="card space-y-4">
        <h3 className="text-xs font-bold uppercase tracking-widest text-slate-300 font-display border-b border-cyber-800/80 pb-2">
          Key Management
        </h3>
        <div className="grid gap-4 sm:grid-cols-3">
          <div>
            <div className="label">Key Size</div>
            <div className="flex rounded-xl overflow-hidden border border-cyber-800">
              {BIT_OPTS.map(b => (
                <button
                  key={b}
                  className={`flex-1 py-2 text-xs font-bold font-mono transition-all ${
                    bits === b
                      ? 'bg-solar-500/30 text-solar-300 border-solar-500/40'
                      : 'text-slate-400 hover:bg-cyber-800/60 hover:text-slate-200'
                  }`}
                  onClick={() => setBits(b)}
                >
                  {b}-bit
                </button>
              ))}
            </div>
          </div>
          <div className="sm:col-span-2">
            <Field label="AES Key (hex)">
              <div className="flex gap-2">
                <input
                  className="input font-mono text-xs tracking-wider"
                  value={aesKey}
                  onChange={e => setAesKey(e.target.value.trim())}
                  placeholder={`${bits / 4} hex chars (${bits}-bit key)`}
                />
                <button className="btn-ghost shrink-0 px-3" onClick={genKey} disabled={loadingKey}>
                  {loadingKey ? <RefreshCw className="h-4 w-4 animate-spin text-solar-400" /> : <><Dices className="h-4 w-4 text-solar-400" /> Gen</>}
                </button>
              </div>
            </Field>
          </div>
        </div>
        {aesKey && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <Stat label="Algorithm" value={`AES-${bits}`} tone="warn" />
            <Stat label="Mode" value="CBC" tone="warn" />
            <Stat label="Block Size" value="128 bit" sub="16 bytes" tone="default" />
            <Stat label="Padding" value="PKCS7" tone="default" />
          </div>
        )}
      </div>

      {/* Encrypt + Decrypt */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Encrypt */}
        <div className="card space-y-4">
          <h3 className="text-xs font-bold uppercase tracking-widest text-solar-400 font-display border-b border-cyber-800/80 pb-2">
            ① AES Encrypt
          </h3>
          <Field label="Plaintext">
            <textarea
              className="input h-28 resize-y leading-relaxed"
              value={plaintext}
              onChange={e => setPlain(e.target.value)}
              placeholder="Your message…"
            />
          </Field>
          <button className="btn-primary w-full py-2.5" onClick={encryptAES} disabled={loadingEnc}>
            {loadingEnc ? <Spinner label="encrypting…" /> : <><Lock className="h-4 w-4" /> Encrypt with AES-{bits}</>}
          </button>
          <ErrorNote error={encError} />
          {encResult && (
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <Stat label="Plaintext Len" value={encResult.plaintext_length} sub="chars" tone="default" />
                <Stat label="Ciphertext Len" value={encResult.ciphertext_length} sub="base64 chars" tone="warn" />
              </div>
              <div className="flex items-end gap-2">
                <div className="flex-1">
                  <MonoBox label="Base64 Ciphertext (IV + Data)" value={ciphertext} tone="orange" truncate={200} />
                </div>
                <CopyBtn text={ciphertext} />
              </div>
              <p className="text-[11px] text-slate-500 leading-relaxed">
                First 24 base64 chars encode the random 16-byte IV.
                Remaining bytes are the AES-CBC ciphertext. A fresh IV is used every encryption.
              </p>
            </div>
          )}
        </div>

        {/* Decrypt */}
        <div className="card space-y-4">
          <h3 className="text-xs font-bold uppercase tracking-widest text-neon-violet font-display border-b border-cyber-800/80 pb-2">
            ② AES Decrypt
          </h3>
          <Field label="Base64 Ciphertext">
            <textarea
              className="input h-28 resize-y leading-relaxed font-mono text-xs"
              value={decInput}
              onChange={e => setDecInput(e.target.value)}
              placeholder="Paste base64 ciphertext…"
            />
          </Field>
          <Field label="AES Key (hex)">
            <input
              className="input font-mono text-xs"
              value={decInput2}
              onChange={e => setDecKey(e.target.value)}
              placeholder="Same key used for encryption"
            />
          </Field>
          <button className="btn-primary w-full py-2.5" onClick={decryptAES} disabled={loadingDec}>
            {loadingDec ? <Spinner label="decrypting…" /> : <><KeyRound className="h-4 w-4" /> Decrypt</>}
          </button>
          <ErrorNote error={decError} />
          {decResult && (
            <div className="space-y-3">
              <div className="flex items-end gap-2">
                <div className="flex-1">
                  <MonoBox label="Recovered Plaintext" value={decResult.plaintext} tone="green" />
                </div>
                <CopyBtn text={decResult.plaintext} />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <Stat label="Key Bits" value={`${decResult.key_bits}-bit`} tone="good" />
                <Stat label="Mode" value={decResult.mode} tone="good" />
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

/* ═══════════════════════════════════════════════ TASK 2  RSA Hybrid Tab ═══ */

function PemBox({ label, value, warning }) {
  const [show, setShow] = useState(false)
  const [copied, copy] = useCopy()
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between">
        <div className="label">{label}</div>
        <div className="flex gap-2">
          {value && (
            <button className="text-xs text-slate-400 hover:text-slate-200 flex items-center gap-1 transition" onClick={() => setShow(s => !s)}>
              {show ? <><EyeOff className="h-3.5 w-3.5" /> Hide</> : <><Eye className="h-3.5 w-3.5" /> Reveal</>}
            </button>
          )}
          {value && (
            <button className="text-xs text-slate-400 hover:text-matrix-400 flex items-center gap-1 transition" onClick={() => copy(value)}>
              {copied ? <><Check className="h-3.5 w-3.5 text-matrix-400" /> Copied</> : <><Copy className="h-3.5 w-3.5" /> Copy</>}
            </button>
          )}
        </div>
      </div>
      {warning && (
        <div className="flex items-center gap-2 text-[11px] text-rose-400 font-medium">
          <AlertTriangle className="h-3.5 w-3.5 shrink-0" /> {warning}
        </div>
      )}
      <div className="rounded-xl border border-cyber-800 bg-cyber-950 p-3 font-mono text-[11px] leading-relaxed text-slate-400 max-h-28 overflow-auto break-all">
        {!value ? (
          <span className="italic text-slate-600">Generate a key pair in Step 1 first…</span>
        ) : show ? value : (
          <span className="text-slate-600">{'•'.repeat(48)} (hidden — click Reveal)</span>
        )}
      </div>
    </div>
  )
}

function StepBadge({ n, label, color = 'matrix' }) {
  const colors = {
    matrix: 'bg-matrix-500/20 border-matrix-500/40 text-matrix-300',
    solar:  'bg-solar-500/20  border-solar-500/40  text-solar-300',
    violet: 'bg-neon-violet/20 border-neon-violet/40 text-purple-300',
  }
  return (
    <div className={`flex items-center gap-2.5 rounded-xl border px-4 py-2.5 ${colors[color]}`}>
      <span className="font-mono text-2xl font-black tabular-nums">{n}</span>
      <span className="font-display font-bold text-sm">{label}</span>
    </div>
  )
}

export function HybridSection() {
  const [keyPair, setKeyPair]     = useState(null)
  const [message, setMessage]     = useState(SAMPLE_MSG)
  const [customPub, setCustomPub] = useState('')
  const [customPriv, setCustomPriv] = useState('')
  const [bundle, setBundle]       = useState(null)
  const [decBundle, setDecBundle] = useState('')
  const [decPriv, setDecPriv]     = useState('')
  const [decResult, setDecResult] = useState(null)

  const [lKey, setLKey]     = useState(false)
  const [lEnc, setLEnc]     = useState(false)
  const [lDec, setLDec]     = useState(false)
  const [keyErr, setKeyErr] = useState(null)
  const [encErr, setEncErr] = useState(null)
  const [decErr, setDecErr] = useState(null)

  const pubKey  = customPub  || keyPair?.public_key  || ''
  const privKey = customPriv || keyPair?.private_key || ''

  async function genKeys() {
    setLKey(true); setKeyErr(null); setBundle(null); setDecResult(null)
    try {
      const r = await api.hybridKeygen(2048)
      setKeyPair(r)
      setCustomPub('')
      setCustomPriv('')
    } catch (e) { setKeyErr(e.message) }
    finally { setLKey(false) }
  }

  async function hybridEncrypt() {
    if (!message.trim()) return setEncErr('Message is required')
    if (!pubKey.trim())  return setEncErr('Generate or paste a public key first')
    setLEnc(true); setEncErr(null); setDecResult(null)
    try {
      const r = await api.hybridEncrypt({ plaintext: message, public_key: pubKey })
      setBundle(r)
      setDecBundle(JSON.stringify(r, null, 2))
      setDecPriv(privKey)
    } catch (e) { setEncErr(e.message) }
    finally { setLEnc(false) }
  }

  async function hybridDecrypt() {
    setLDec(true); setDecErr(null)
    try {
      let bundleObj
      try { bundleObj = JSON.parse(decBundle) } catch { return setDecErr('Bundle must be valid JSON') }
      const r = await api.hybridDecrypt({ bundle: bundleObj, private_key: decPriv })
      setDecResult(r)
    } catch (e) { setDecErr(e.message) }
    finally { setLDec(false) }
  }

  return (
    <div className="space-y-6">
      {/* Theory banner */}
      <div className="rounded-2xl border border-neon-violet/30 bg-gradient-to-r from-neon-violet/10 via-cyber-900 to-cyber-900 p-5 flex flex-col sm:flex-row gap-4">
        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-neon-violet/20 border border-neon-violet/40 shadow-glow-violet">
          <ShieldCheck className="h-6 w-6 text-neon-violet" />
        </div>
        <div className="space-y-1">
          <p className="font-display font-bold text-sm text-purple-200">
            Simple Hybrid System — RSA-2048 + AES-256 (This is how HTTPS/TLS works)
          </p>
          <p className="text-xs text-slate-400 leading-relaxed">
            RSA alone can only encrypt ≤214 bytes (key-size limit with OAEP). The <strong className="text-purple-300">hybrid
            solution</strong>: generate a random AES-256 session key, encrypt the message with AES (fast, unlimited length),
            then encrypt <em>only the 32-byte session key</em> with RSA-2048. The receiver uses their RSA private key
            to recover the session key, then uses it to decrypt the message. This gives both RSA security and AES speed.
          </p>
        </div>
      </div>

      {/* Visual flow diagram */}
      <div className="rounded-2xl border border-cyber-800 bg-cyber-950/60 p-5">
        <h3 className="text-xs font-bold uppercase tracking-widest text-slate-400 font-display mb-4">Hybrid Encryption Flow</h3>
        <div className="flex flex-wrap items-center gap-2 text-xs font-mono">
          {[
            { label: 'Plaintext', color: 'text-slate-300' },
            null,
            { label: 'AES-256-CBC', color: 'text-solar-400', sub: '(random session key)' },
            null,
            { label: 'AES Ciphertext', color: 'text-solar-300' },
          ].map((item, i) => item === null
            ? <ChevronRight key={i} className="h-4 w-4 text-slate-600" />
            : (
              <div key={i} className={`rounded-lg border border-cyber-800 bg-cyber-950 px-3 py-2 ${item.color}`}>
                {item.label}
                {item.sub && <div className="text-[10px] text-slate-500">{item.sub}</div>}
              </div>
            )
          )}
        </div>
        <div className="flex flex-wrap items-center gap-2 text-xs font-mono mt-2 ml-4">
          <div className="text-slate-600">Session Key</div>
          <ChevronRight className="h-4 w-4 text-slate-600" />
          <div className="rounded-lg border border-neon-violet/30 bg-neon-violet/10 px-3 py-2 text-purple-300">
            RSA-2048 OAEP <div className="text-[10px] text-slate-500">(public key)</div>
          </div>
          <ChevronRight className="h-4 w-4 text-slate-600" />
          <div className="rounded-lg border border-neon-violet/30 bg-neon-violet/10 px-3 py-2 text-purple-300">
            Sealed Key
          </div>
          <span className="text-slate-600">→ Bundle = {'{Sealed Key + IV + AES Ciphertext}'}</span>
        </div>
      </div>

      {/* Step 1: Key Generation */}
      <div className="card space-y-4">
        <StepBadge n="1" label="Generate RSA-2048 Key Pair" color="matrix" />
        <p className="text-xs text-slate-400">
          Creates a 2048-bit RSA key pair. The <strong className="text-matrix-400">public key</strong> is shared openly
          (used to encrypt). The <strong className="text-rose-400">private key</strong> is kept secret (used to decrypt).
        </p>
        <button className="btn-primary py-3 px-6" onClick={genKeys} disabled={lKey}>
          {lKey ? <Spinner label="generating RSA-2048…" /> : <><Sparkles className="h-4 w-4" /> Generate RSA-2048 Key Pair</>}
        </button>
        <ErrorNote error={keyErr} />
        {keyPair && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <Stat label="Key Size" value={`${keyPair.bits}-bit`} tone="good" />
              <Stat label="Public Exponent" value={`e = ${keyPair.public_exponent}`} tone="default" />
              <Stat label="Modulus Bits" value={keyPair.modulus_bits} tone="default" />
              <Stat label="Gen Time" value={`${keyPair.key_gen_seconds}s`} tone="warn" />
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <PemBox label="Public Key (PEM) — safe to share" value={keyPair.public_key} />
              <PemBox
                label="Private Key (PEM) — keep secret"
                value={keyPair.private_key}
                warning="Never share this key. Used only for decryption."
              />
            </div>
            <div className="rounded-xl border border-cyber-800 bg-cyber-950/60 p-3 font-mono text-[11px] text-slate-500">
              <span className="text-matrix-400">Modulus prefix: </span>{keyPair.modulus_hex_prefix}
            </div>
          </div>
        )}
      </div>

      {/* Step 2: Encrypt */}
      <div className="card space-y-4">
        <StepBadge n="2" label="Hybrid Encrypt (Public Key)" color="solar" />
        <p className="text-xs text-slate-400">
          A fresh AES-256 session key is randomly generated for this message only.
          The message is encrypted with AES-256-CBC, then the session key is sealed with RSA-2048 OAEP.
        </p>
        <Field label="Message to Encrypt">
          <textarea
            className="input h-24 resize-y leading-relaxed"
            value={message}
            onChange={e => setMessage(e.target.value)}
          />
        </Field>
        <Field label="RSA Public Key (PEM)">
          <textarea
            className="input h-20 resize-y font-mono text-xs leading-relaxed"
            value={pubKey}
            onChange={e => setCustomPub(e.target.value)}
            placeholder={keyPair ? '← auto-filled from Step 1' : 'Generate keys in Step 1, or paste a PEM public key…'}
            readOnly={!!keyPair && !customPub}
          />
        </Field>
        <button className="btn-primary w-full py-3" onClick={hybridEncrypt} disabled={lEnc}>
          {lEnc ? <Spinner label="hybrid-encrypting…" /> : <><Lock className="h-4 w-4" /> Hybrid Encrypt Message</>}
        </button>
        <ErrorNote error={encErr} />
        {bundle && (
          <div className="space-y-3">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <Stat label="Msg Length" value={`${bundle.message_length} chars`} tone="default" />
              <Stat label="AES Key" value={`${bundle.aes_key_bits}-bit`} tone="warn" />
              <Stat label="RSA Key" value={`${bundle.rsa_bits}-bit`} tone="warn" />
              <Stat label="AES Key Preview" value={bundle.aes_key_hex_prefix} tone="default" />
            </div>
            <div className="rounded-xl border border-solar-500/30 bg-cyber-950 p-4 space-y-2">
              <div className="text-[11px] font-bold text-solar-400 font-display uppercase tracking-wider mb-2">
                Encrypted Bundle (JSON)
              </div>
              <div className="font-mono text-[11px] text-slate-400 space-y-1.5">
                <div><span className="text-solar-400">"rsa_encrypted_key"</span><span className="text-slate-600">:</span> <span className="text-purple-300">{bundle.rsa_encrypted_key.slice(0, 60)}…</span></div>
                <div><span className="text-solar-400">"iv"</span><span className="text-slate-600">:</span> <span className="text-matrix-300">{bundle.iv}</span></div>
                <div><span className="text-solar-400">"aes_ciphertext"</span><span className="text-slate-600">:</span> <span className="text-slate-300">{bundle.aes_ciphertext.slice(0, 60)}…</span></div>
              </div>
            </div>
            <div className="flex items-center justify-between">
              <button
                className="text-xs text-solar-400 hover:text-solar-300 flex items-center gap-1 transition"
                onClick={() => setDecBundle(JSON.stringify(bundle, null, 2))}
              >
                <ArrowRight className="h-3.5 w-3.5" /> Send to Step 3 (Decrypt)
              </button>
              <CopyBtn text={JSON.stringify(bundle)} />
            </div>
          </div>
        )}
      </div>

      {/* Step 3: Decrypt */}
      <div className="card space-y-4">
        <StepBadge n="3" label="Hybrid Decrypt (Private Key)" color="violet" />
        <p className="text-xs text-slate-400">
          The RSA private key unseals the AES session key from the bundle.
          The recovered session key then decrypts the AES-CBC ciphertext to restore the original message.
        </p>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="RSA Private Key (PEM)">
            <textarea
              className="input h-32 resize-y font-mono text-xs leading-relaxed"
              value={decPriv}
              onChange={e => setDecPriv(e.target.value)}
              placeholder={keyPair ? '← auto-filled from Step 1' : 'Paste your RSA private key (PEM)…'}
            />
          </Field>
          <Field label="Bundle JSON (from Step 2)">
            <textarea
              className="input h-32 resize-y font-mono text-[11px] leading-relaxed"
              value={decBundle}
              onChange={e => setDecBundle(e.target.value)}
              placeholder={'{\n  "rsa_encrypted_key": "…",\n  "iv": "…",\n  "aes_ciphertext": "…"\n}'}
            />
          </Field>
        </div>
        <button className="btn-primary w-full py-3" onClick={hybridDecrypt} disabled={lDec}>
          {lDec ? <Spinner label="decrypting…" /> : <><KeyRound className="h-4 w-4" /> Hybrid Decrypt Bundle</>}
        </button>
        <ErrorNote error={decErr} />
        {decResult && (
          <div className="space-y-3">
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              <Stat label="Status" value="✓ SUCCESS" tone="good" />
              <Stat label="AES Key Recovered" value={`${decResult.aes_key_bits}-bit`} tone="good" />
              <Stat label="Message Length" value={`${decResult.message_length} chars`} tone="default" />
            </div>
            <div className="rounded-xl border border-matrix-500/30 bg-cyber-950 p-3 font-mono text-[11px] text-slate-400">
              <span className="text-matrix-400">Recovered AES key: </span>
              {decResult.aes_key_hex.slice(0, 32)}…
            </div>
            <div className="flex items-end gap-2">
              <div className="flex-1">
                <MonoBox label="✓ Decrypted Plaintext" value={decResult.plaintext} tone="green" />
              </div>
              <CopyBtn text={decResult.plaintext} />
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

/* ═══════════════════════════════════════════════════ Main Page Component ═══ */

const TABS = [
  {
    id: 'vigenere',
    label: 'Vigenère Cipher',
    badge: 'Task 1 · Classical',
    icon: KeyRound,
    activeClass: 'bg-matrix-500/20 text-matrix-300 border-matrix-500/40 shadow-glow-matrix',
    chipClass: 'chip-matrix',
  },
  {
    id: 'aes',
    label: 'AES-256',
    badge: 'Task 1 · Modern Symmetric',
    icon: Cpu,
    activeClass: 'bg-solar-500/20 text-solar-300 border-solar-500/40 shadow-glow-solar',
    chipClass: 'chip-solar',
  },
  {
    id: 'hybrid',
    label: 'RSA Hybrid System',
    badge: 'Task 2 · Public-Key',
    icon: ShieldCheck,
    activeClass: 'bg-neon-violet/20 text-purple-300 border-neon-violet/40 shadow-glow-violet',
    chipClass: 'chip-violet',
  },
]

export default function SecureVault() {
  const [active, setActive] = useState('vigenere')

  return (
    <div>
      <PageHeader
        title="Secure Vault"
        blurb="Assignment implementations — Task 1: Vigenère cipher (classical) + AES-256 (modern symmetric); Task 2: Simple Hybrid System (RSA-2048 + AES-256 session key)."
        icon={Lock}
      >
        <span className="chip-matrix font-mono text-[11px]">DSP_BAD703</span>
      </PageHeader>

      {/* Tab bar */}
      <div className="flex flex-wrap gap-2 mb-6 border-b border-cyber-800/80 pb-4">
        {TABS.map(tab => {
          const Icon = tab.icon
          const isActive = active === tab.id
          return (
            <button
              key={tab.id}
              id={`tab-${tab.id}`}
              onClick={() => setActive(tab.id)}
              className={`flex items-center gap-2.5 rounded-xl border px-4 py-2.5 text-sm font-bold font-display transition-all duration-200 ${
                isActive
                  ? tab.activeClass
                  : 'border-transparent text-slate-400 hover:bg-cyber-800/60 hover:text-slate-200'
              }`}
            >
              <Icon className="h-4 w-4" />
              <span>{tab.label}</span>
              <span className={`font-mono font-normal text-[10px] px-2 py-0.5 rounded-full border ${
                isActive ? 'bg-black/20 border-current/30' : 'border-cyber-800 bg-cyber-900 text-slate-500'
              }`}>
                {tab.badge}
              </span>
            </button>
          )
        })}
      </div>

      {/* Content */}
      {active === 'vigenere' && <VigenereSection />}
      {active === 'aes'      && <AesSection />}
      {active === 'hybrid'   && <HybridSection />}
    </div>
  )
}

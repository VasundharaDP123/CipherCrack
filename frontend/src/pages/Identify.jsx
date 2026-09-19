import { useEffect, useState } from 'react'
import {
  Search, Cpu, PieChart, BarChart3, Layers, Table, CheckCircle2, Sparkles, FileText, Activity, Compass,
} from 'lucide-react'
import {
  CartesianGrid, Cell, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis,
} from 'recharts'
import { api } from '../lib/api'
import { ErrorNote, Field, PageHeader, Spinner, Stat } from '../components/Shared'

const CLUSTER_COLOURS = ['#f59e0b', '#10b981', '#ff2a6d', '#a855f7']

export default function Identify() {
  const [text, setText] = useState('')
  const [model, setModel] = useState('forest')
  const [result, setResult] = useState(null)
  const [clusters, setClusters] = useState(null)
  const [metrics, setMetrics] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    api.clusters(600).then(setClusters).catch(() => {})
    api.identifierMetrics().then(setMetrics).catch(() => {})
  }, [])

  async function run() {
    if (!text.trim()) return
    setBusy(true)
    setError(null)
    try {
      setResult(await api.identify({ text, model }))
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  async function sample(cipher) {
    setError(null)
    try {
      const made = await api.encrypt({
        text:
          'The quick brown fox jumps over the lazy dog while the patient student ' +
          'considers whether the index of coincidence will give the answer away ' +
          'before any search is even attempted at all this evening.',
        cipher,
      })
      setText(made.ciphertext)
      setResult(await api.identify({ text: made.ciphertext, model }))
    } catch (e) {
      setError(e.message)
    }
  }

  const forestReport = metrics?.metrics?.forest
  const adaReport = metrics?.metrics?.adaboost

  return (
    <div>
      <PageHeader
        title="Cipher Identifier"
        blurb="Classifies unknown ciphertexts using a 49-feature extraction pipeline. Compares Random Forest decision trees against AdaBoost decision stumps and 2D K-Means cluster maps."
        icon={Search}
      />

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Left Column: Classification Input & Results */}
        <div className="space-y-5">
          <div className="card space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
              <h2 className="text-xs font-bold uppercase tracking-widest text-slate-300 font-display flex items-center gap-2">
                <FileText className="h-4 w-4 text-amber-400" />
                Input Ciphertext Analysis
              </h2>
              <span className="chip text-[11px] font-mono">Statistical Features</span>
            </div>

            <Field label="Ciphertext to Classify">
              <textarea
                className="input h-36 leading-relaxed"
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder="Paste any unknown ciphertext..."
              />
            </Field>

            <div className="flex flex-wrap items-end gap-3 pt-1">
              <Field label="Classifier Model">
                <select
                  className="input cursor-pointer font-sans text-xs w-56"
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                >
                  <option value="forest" className="bg-cyber-950">Random Forest (From Scratch)</option>
                  <option value="adaboost" className="bg-cyber-950">AdaBoost Stumps (From Scratch)</option>
                </select>
              </Field>
              <button className="btn-primary" onClick={run} disabled={busy || !text.trim()}>
                <Sparkles className="h-4 w-4" />
                Classify Cipher
              </button>
              {busy && <Spinner label="extracting features..." />}
            </div>

            <div>
              <div className="label">Quick Preset Samples</div>
              <div className="flex flex-wrap gap-2">
                {['caesar', 'substitution', 'vigenere', 'transposition'].map((name) => (
                  <button
                    key={name}
                    className="chip hover:border-amber-500/40 hover:text-amber-300 capitalize cursor-pointer transition"
                    onClick={() => sample(name)}
                  >
                    {name}
                  </button>
                ))}
              </div>
            </div>

            <ErrorNote error={error} />
          </div>

          {/* Result Card */}
          {result && (
            <div className="card space-y-5 border-amber-500/30 bg-cyber-900/90 shadow-xl shadow-amber-950/20">
              <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
                <div>
                  <div className="text-[10px] font-bold uppercase tracking-widest text-slate-500 font-display">
                    Predicted Class
                  </div>
                  <div className="font-display text-2xl font-extrabold capitalize text-white flex items-center gap-2">
                    {result.prediction}
                    <CheckCircle2 className="h-5 w-5 text-amber-400" />
                  </div>
                </div>
                <Stat
                  label="Confidence"
                  value={`${(result.confidence * 100).toFixed(1)}%`}
                  tone={result.confidence > 0.8 ? 'good' : 'warn'}
                />
              </div>

              {/* Probability Bars */}
              <div className="space-y-2.5">
                <div className="text-[11px] font-bold uppercase tracking-widest text-slate-400 font-display">
                  Class Probability Distribution
                </div>
                {result.probabilities.map((row) => (
                  <div key={row.cipher} className="flex items-center gap-2.5 text-xs">
                    <span className="w-28 text-slate-400 font-medium capitalize">{row.cipher}</span>
                    <div className="h-2.5 flex-1 overflow-hidden rounded-full bg-cyber-950 border border-slate-800">
                      <div
                        className="h-full rounded-full bg-gradient-to-r from-amber-400 via-rose-500 to-purple-500 transition-all duration-500"
                        style={{ width: `${row.probability * 100}%` }}
                      />
                    </div>
                    <span className="w-14 text-right font-mono font-bold text-slate-200">
                      {(row.probability * 100).toFixed(1)}%
                    </span>
                  </div>
                ))}
              </div>

              {/* Extracted Key Features */}
              <div>
                <div className="text-[11px] font-bold uppercase tracking-widest text-slate-400 font-display mb-2.5">
                  Extracted Statistical Features
                </div>
                <div className="grid grid-cols-2 gap-2.5 text-xs sm:grid-cols-3">
                  {Object.entries(result.features)
                    .slice(0, 9)
                    .map(([name, value]) => (
                      <div
                        key={name}
                        className="rounded-xl border border-slate-800/80 bg-cyber-950/80 p-2.5"
                      >
                        <div className="truncate text-[10px] font-bold uppercase tracking-wider text-slate-500 font-display">
                          {name.replace(/_/g, ' ')}
                        </div>
                        <div className="font-mono text-xs font-bold text-amber-300 mt-0.5">
                          {value.toFixed(4)}
                        </div>
                      </div>
                    ))}
                </div>
              </div>

              {/* Model Comparison Breakdown */}
              <div className="grid grid-cols-2 gap-3 text-xs pt-1">
                <div className="rounded-xl border border-slate-800 bg-cyber-950/60 p-3 space-y-1">
                  <div className="text-[10px] font-bold uppercase tracking-widest text-slate-400 font-display mb-1.5">
                    Random Forest Verdict
                  </div>
                  {Object.entries(result.forest_probabilities).map(([k, v]) => (
                    <div key={k} className="flex justify-between text-slate-400 capitalize font-mono text-[11px]">
                      <span>{k}</span>
                      <span className="text-slate-200 font-bold">{(v * 100).toFixed(1)}%</span>
                    </div>
                  ))}
                </div>
                <div className="rounded-lg border border-slate-800 bg-cyber-950/60 p-3 space-y-1">
                  <div className="text-[10px] font-bold uppercase tracking-widest text-slate-400 font-display mb-1.5">
                    AdaBoost Stumps Verdict
                  </div>
                  {Object.entries(result.adaboost_probabilities).map(([k, v]) => (
                    <div key={k} className="flex justify-between text-slate-400 capitalize font-mono text-[11px]">
                      <span>{k}</span>
                      <span className="text-slate-200 font-bold">{(v * 100).toFixed(1)}%</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Right Column: K-Means Scatter Map & Test Evaluation */}
        <div className="space-y-5">
          {/* K-Means PCA Cluster Map */}
          <div className="card space-y-3">
            <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
              <h2 className="text-xs font-bold uppercase tracking-widest text-slate-300 font-display flex items-center gap-2">
                <Compass className="h-4 w-4 text-purple-400" />
                Unsupervised K-Means PCA Map
              </h2>
              {clusters?.silhouette != null && (
                <span className="chip border-purple-500/30 bg-purple-500/10 text-purple-300 font-mono text-[11px]">
                  Silhouette: {clusters.silhouette.toFixed(3)}
                </span>
              )}
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              Ciphertexts projected onto 2D PCA space. Color indicates K-Means clusters discovered without labels. Hover points to view ground truth.
            </p>
            <div className="h-72 w-full rounded-xl border border-slate-800/80 bg-cyber-950/80 p-2">
              {clusters ? (
                <ResponsiveContainer width="100%" height="100%">
                  <ScatterChart margin={{ top: 10, right: 15, bottom: 5, left: -20 }}>
                    <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" />
                    <XAxis
                      type="number"
                      dataKey="x"
                      tick={{ fill: '#64748b', fontSize: 10, fontFamily: 'monospace' }}
                      stroke="#334155"
                    />
                    <YAxis
                      type="number"
                      dataKey="y"
                      tick={{ fill: '#64748b', fontSize: 10, fontFamily: 'monospace' }}
                      stroke="#334155"
                    />
                    <Tooltip
                      cursor={{ stroke: 'rgba(255, 255, 255, 0.2)' }}
                      contentStyle={{
                        background: '#090e1c',
                        border: '1px solid rgba(157, 78, 221, 0.3)',
                        borderRadius: 12,
                        fontSize: 12,
                        fontFamily: 'monospace',
                      }}
                      formatter={(value, name, entry) => [
                        entry.payload.label,
                        `Cluster ${entry.payload.cluster}`,
                      ]}
                    />
                    <Scatter data={clusters.points} fillOpacity={0.75}>
                      {clusters.points.map((point, index) => (
                        <Cell key={index} fill={CLUSTER_COLOURS[point.cluster % 4]} />
                      ))}
                    </Scatter>
                    {result && (
                      <Scatter
                        data={[result.projection]}
                        fill="#ffffff"
                        shape="star"
                        legendType="star"
                      />
                    )}
                  </ScatterChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex h-full items-center justify-center text-xs text-slate-500 italic">
                  Loading K-Means cluster points...
                </div>
              )}
            </div>
          </div>

          {/* Test Performance Metrics & Confusion Matrix */}
          {metrics && forestReport && (
            <div className="card space-y-4">
              <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
                <h2 className="text-xs font-bold uppercase tracking-widest text-slate-300 font-display flex items-center gap-2">
                  <BarChart3 className="h-4 w-4 text-emerald-400" />
                  Held-Out Benchmark Performance
                </h2>
                <span className="chip border-emerald-500/30 bg-emerald-500/10 text-emerald-300 font-mono text-[11px]">
                  2,000 Test Passages
                </span>
              </div>

              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                <Stat
                  label="Random Forest"
                  value={`${(forestReport.accuracy * 100).toFixed(1)}%`}
                  sub="test accuracy"
                  tone="good"
                />
                <Stat
                  label="AdaBoost"
                  value={`${(adaReport.accuracy * 100).toFixed(1)}%`}
                  sub="test accuracy"
                  tone="purple"
                />
                <Stat
                  label="OOB Score"
                  value={`${(metrics.metrics.oob_score * 100).toFixed(1)}%`}
                  sub="out-of-bag error"
                  tone="accent"
                />
                <Stat
                  label="Macro F1"
                  value={forestReport.macro_f1.toFixed(3)}
                  sub="balanced f1"
                />
              </div>

              {/* Confusion Matrix */}
              <div className="overflow-x-auto pt-2">
                <div className="text-[11px] font-bold uppercase tracking-widest text-slate-400 font-display mb-2">
                  Confusion Matrix (Random Forest) — Rows are True Class
                </div>
                <table className="w-full text-xs border-collapse">
                  <thead>
                    <tr className="border-b border-slate-800 text-slate-500 font-display uppercase tracking-wider text-[10px]">
                      <th className="p-2 text-left">Actual \ Pred</th>
                      {forestReport.classes.map((c) => (
                        <th key={c} className="p-2 text-center capitalize">
                          {c}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {forestReport.confusion_matrix.map((row, i) => (
                      <tr key={i} className="border-b border-slate-800/40">
                        <td className="p-2 font-semibold text-slate-300 capitalize">{forestReport.classes[i]}</td>
                        {row.map((value, j) => (
                          <td
                            key={j}
                            className={`p-2 text-center font-mono font-bold ${
                              i === j ? 'bg-emerald-500/20 text-emerald-300' : 'text-slate-500'
                            }`}
                          >
                            {value}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Feature Importances */}
              <div className="pt-2">
                <div className="text-[11px] font-bold uppercase tracking-widest text-slate-400 font-display mb-2.5">
                  Top Gini Feature Importances
                </div>
                <div className="space-y-2">
                  {metrics.top_features.slice(0, 6).map((row) => (
                    <div key={row.feature} className="flex items-center gap-2 text-xs">
                      <span className="w-40 truncate text-slate-400 font-mono text-[11px]">
                        {row.feature.replace(/_/g, ' ')}
                      </span>
                      <div className="h-2 flex-1 overflow-hidden rounded-full bg-cyber-950 border border-slate-800">
                        <div
                          className="h-full rounded-full bg-gradient-to-r from-amber-400 to-rose-500"
                          style={{ width: `${(row.importance / metrics.top_features[0].importance) * 100}%` }}
                        />
                      </div>
                      <span className="w-14 text-right font-mono text-slate-400">
                        {row.importance.toFixed(3)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

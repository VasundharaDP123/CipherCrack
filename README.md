# CipherCrack

Breaks substitution ciphers live in the browser, using MCMC sampling and Hidden
Markov Models. A substitution cipher has 26! ≈ 4×10²⁶ possible keys, so brute
force is hopeless; CipherCrack instead scores how English-like a guess looks and
improves it step by step.

Machine Learning II (BAI702) group project.

---

## Run it

Two terminals. **Backend:**

```bash
cd backend
pip install -r requirements.txt
python -m scripts.build_corpus          # downloads the Gutenberg books (~10 MB)
python -m scripts.build_language_model  # builds the 27x27 bigram model
python -m scripts.build_dataset         # generates 8,000 labelled ciphertexts
python -m scripts.train_identifier      # trains the forest / AdaBoost / K-Means
python app.py                           # http://127.0.0.1:5000
```

**Frontend:**

```bash
cd frontend
npm install
npm run dev                             # http://localhost:5173
```

Open **http://localhost:5173**. Vite proxies `/api` and `/socket.io` to the
backend, so nothing needs configuring.

The four build steps only need running once — their output is cached in
`backend/data/`. After that, `python app.py` is all you need.

### Tests

```bash
cd backend && python -m pytest          # 63 tests
```

### Command-line demos

```bash
python -m scripts.bench_mcmc --all-proposals   # crack a cipher, time every proposal
python -m scripts.bench_hmm                    # HMM correctness checks + a solve
```

---

## What it does

| Page | What you do | Algorithms behind it |
|---|---|---|
| **Encrypt Lab** | Write a message, pick a cipher, get a puzzle | Caesar, Substitution, Vigenère, Transposition |
| **Crack Live** | Paste ciphertext, watch the key lock in | MCMC or HMM, streamed over Socket.IO |
| **Cipher Identifier** | Paste anything, get the cipher type | Random Forest, AdaBoost, K-Means |
| **MCMC Playground** | Drag the step size, see mixing change | Metropolis–Hastings, Box–Muller |
| **Algorithm Arena** | Run every solver on one cipher | MCMC, HMM, hill climbing, frequency analysis |
| **Challenge Mode** | Race the AI, land on a leaderboard | MCMC solver, SQLite |

---

## Results measured on this build

**Cracking a 400-character substitution cipher** (10 restarts × 10,000 iterations):

| Proposal | Accuracy | Throughput | Acceptance |
|---|---|---|---|
| Random swap | 99.7% | 83,000 it/s | 1.7% |
| Frequency-guided | 99.7% | 99,000 it/s | 4.8% |
| Three-letter cycle | 99.7% | 71,000 it/s | 1.4% |
| Adaptive | 99.7% | 48,000 it/s | 2.8% |

The whole solve takes 1–2 seconds. The single remaining error is typically a
rare letter such as X or Z that appears once or not at all — there is simply no
evidence in the text to place it.

**Restarts matter more than iterations.** Measured over 16 runs on the same
400-character cipher:

| Setting | Reaches ≥95% | Time |
|---|---|---|
| 5 restarts × 10,000 | 81% (13/16) | 0.75s |
| **10 restarts × 10,000** (the default) | **100%** (16/16) | 1.49s |
| 10 restarts × 20,000 | 100% (16/16) | 3.47s |

Doubling the restarts buys reliability; doubling the iterations buys nothing.
A chain that is going to get stuck gets stuck early, so it is better to start
again than to keep walking.

**Cipher identifier**, 8,000 samples, 80/20 stratified split:

| Model | Accuracy | Macro F1 |
|---|---|---|
| Random Forest (from scratch) | **98.6%** | 0.986 |
| Random Forest (scikit-learn) | 98.5% | 0.985 |
| AdaBoost (from scratch) | 97.4% | 0.974 |
| AdaBoost (scikit-learn) | 97.4% | 0.974 |

The from-scratch forest edges out the library one, and the from-scratch AdaBoost
reproduces scikit-learn's confusion matrix *cell for cell* — a strong sign the
SAMME implementation is right. Out-of-bag accuracy: 98.5%. K-Means silhouette:
0.30 with no labels at all.

**Solvers on the same 400-character cipher:**

| Solver | Accuracy | Score/char | Time |
|---|---|---|---|
| MCMC | 99.7% | −2.355 | 0.66s |
| Hill climbing | 99.7% | −2.355 | 0.47s |
| Steepest ascent | 99.7% | −2.355 | 0.22s |
| HMM (Baum–Welch) | 85.5% | −3.184 | 11.2s |
| Frequency analysis | 34.0% | −3.338 | 0.00s |

(The true plaintext scores −2.360 per character, so MCMC has essentially
recovered it.)

### Honest limitations

- **Short texts fail.** Below ~100 characters there are too few letter pairs to
  tell English from near-English, and every solver degrades. The Arena page lets
  you drag the length down and watch it happen.
- **Baum–Welch plateaus.** It reliably reaches ~85% and stops, confusing letters
  that sit in similar bigram contexts (S/J, M/B, D/X). Extra restarts do **not**
  help — measured, not assumed: EM runs downhill into the same optimum from
  essentially any start. This matches the decipherment literature; sampling
  beats EM here.
- **Hill climbing is competitive on easy inputs.** On a 400-character cipher with
  five restarts it matches MCMC. The gap only opens on shorter texts and fewer
  restarts, which is where the Arena comparison is worth running.

---

## How the solving works

### The scoring model

The English model is a 27×27 table of letter-pair log-probabilities (A–Z plus
space) counted from six public-domain books, Laplace-smoothed and row-normalised.
A key's score is the sum of `log P(next | current)` over the decoded text.
English scores about −2.38 per character; random letters score about −5.20.

### Why it is fast

Scoring is done three ways, each faster than the last:

1. **Walk the text** — O(n) per key.
2. **Bigram counts** — the score depends only on *how many times* each cipher
   pair occurs, so precompute the ciphertext's own 27×27 count matrix and every
   evaluation becomes a fixed-size reduction, independent of message length.
3. **Only what moved** — a swap changes only the terms whose row or column is one
   of the two swapped letters: about 40 terms instead of 729.

Step 3 is written in **plain Python, not NumPy**, and that is deliberate. At
27×27 a NumPy call is dominated by dispatch overhead rather than arithmetic, so
forty list lookups beat a handful of array operations. Measured on this machine:

| Method | Throughput |
|---|---|
| Incremental delta (plain Python) | 141,000 it/s |
| Full rescore (plain Python) | 26,000 it/s |
| Full rescore (NumPy) | 18,000 it/s |

That is a 24× end-to-end speedup over the obvious NumPy implementation, and the
delta is exact — it agrees with a full rescore to ~2×10⁻¹², which is asserted in
the test suite for all four proposals.

### Proposal distributions

Three of the four are built to be **exactly symmetric**, so the plain Metropolis
acceptance rule `min(1, exp(Δ))` stays valid without a Hastings correction:

- **Random swap** — picks an unordered pair uniformly; reversing means picking
  the same pair.
- **Frequency-guided** — weights pairs by closeness in *observed ciphertext*
  frequency rank. Those ranks belong to the message, not the key, so the
  distribution never changes as the chain moves. Swapping two symbols of similar
  frequency is a low-risk move, which is why its acceptance rate is ~3× higher.
- **Three-letter cycle** — three symbols uniformly, then one of two rotation
  directions at 50/50. Mixed 50/50 with plain swaps, since pure cycles can never
  make the single correction a swap makes.
- **Adaptive** — genuinely asymmetric. Validity is restored by *freezing* the
  weights after a burn-in (the diminishing-adaptation condition).

### The HMM

| | |
|---|---|
| hidden states | the 27 plaintext symbols |
| observations | the 27 ciphertext symbols |
| transitions `A` | the English bigram model — **known, held fixed** |
| emissions `B` | the key — **unknown, learned** |

Only `B` is estimated, which is what makes the problem tractable: English letter
order is not a mystery, and re-learning it from a few hundred characters would
throw away good information. Because `A` is fixed, the M-step needs only the
per-state posteriors γ and never the pairwise ξ.

The forward pass uses **scaling rather than logs** (each column normalised, the
normaliser kept) so the arithmetic stays in fast BLAS; the log-likelihood is
recovered exactly as `−Σ log cₜ`. Viterbi *does* run in log space, because it
only ever adds. All three are verified in the tests against independent slow
reference implementations.

---

## Layout

```
backend/
  app.py                  Flask + Socket.IO entry point
  db.py                   SQLite: runs, leaderboard
  api/routes.py           REST endpoints
  api/sockets.py          live solver streaming
  ciphers/                caesar, substitution, vigenere, transposition
  ml/
    language_model.py     27x27 bigram scorer
    scoring.py            three-tier key scoring (the speed story)
    mcmc.py               Metropolis-Hastings chain
    proposals.py          the four proposal distributions
    rng.py                batched random draws
    hmm.py                forward, backward, Baum-Welch, Viterbi
    tree.py               CART decision tree + stump
    forest.py             random forest + out-of-bag scoring
    adaboost.py           SAMME AdaBoost
    kmeans.py             K-Means, vector quantization, silhouette
    gaussian.py           Box-Muller + the Playground sampler
    features.py           cipher fingerprints
    identifier.py         the trained bundle
    metrics.py            confusion matrix, P/R/F1, splits
  baselines/              frequency analysis, hill climbing
  scripts/                corpus, dataset, training, benchmarks
  tests/                  63 tests
frontend/src/pages/       Encrypt, Crack, Identify, Playground, Arena, Challenge
```

## API

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/encrypt` | Encrypt with a chosen cipher and key |
| POST | `/api/identify` | Cipher type and class probabilities |
| POST | `/api/crack` | Blocking solve |
| POST | `/api/arena/run` | Run several solvers on one ciphertext |
| GET | `/api/arena/results` | Saved comparison runs |
| POST | `/api/playground/sample` | MCMC samples for a given step size |
| GET/POST | `/api/leaderboard` | Challenge Mode scores |
| GET | `/api/challenge/new` | A fresh puzzle |
| Socket.IO | `start_crack` → `crack_progress` → `crack_done` | Live solving |
| Socket.IO | `stop_crack` | Cancel a running solver |

Progress frames are throttled to at most one every 50 ms. Without that the MCMC
solver emits several hundred frames a second — faster than the transport can
drain them and far faster than anyone can read.

---

## Data

Training books (bigram model, HMM transitions) and test books (evaluation
passages, identifier dataset) are **kept strictly separate**, so no evaluation
number is contaminated by text the model was trained on.

- Train: *Pride and Prejudice*, *War and Peace*, *Sherlock Holmes*,
  *Frankenstein*, *A Tale of Two Cities*, *Jane Eyre* — 6.8 MB
- Test: *Alice in Wonderland*, *Great Expectations*, *Dracula*, *Moby Dick* — 3.2 MB

## References

- Diaconis, *The Markov Chain Monte Carlo Revolution* (2009)
- Knight et al., *Unsupervised Analysis for Decipherment Problems* (2006)
- Zhu et al., *Multi-class AdaBoost* (2009) — the SAMME algorithm

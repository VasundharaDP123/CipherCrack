# 🔐 CipherCrack

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![React](https://img.shields.io/badge/React-18.3-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev)
[![Vite](https://img.shields.io/badge/Vite-5.4-646CFF?style=for-the-badge&logo=vite&logoColor=white)](https://vitejs.dev)
[![Flask](https://img.shields.io/badge/Flask-SocketIO-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![TailwindCSS](https://img.shields.io/badge/Tailwind-3.4-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white)](https://tailwindcss.com)
[![License](https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge)](LICENSE)

**Unsupervised Substitution Cipher Cryptanalysis via Metropolis-Hastings MCMC Sampling & Hidden Markov Models**

*Machine Learning II (BAI702) Group Project*

</div>

---

## 📌 Overview

Monoalphabetic substitution ciphers possess a key search space of $26! \approx 4 \times 10^{26}$ possible permutations. Exact brute-force search across this space is computationally intractable. 

**CipherCrack** solves substitution ciphers in real-time ($<1.5$ seconds for standard passages) without requiring key pre-knowledge or labelled training targets. The system combines:
- **Fast 27×27 Bigram Log-Likelihood Scoring** calibrated over public-domain literature.
- **Metropolis-Hastings MCMC Chains** with incremental $O(1)$ proposal delta updates capable of evaluating **140,000+ key proposals per second**.
- **Constrained Hidden Markov Models (Baum–Welch EM algorithm)** with fixed English transition probability matrices.
- **Feature Fingerprinting & Classifiers** (Random Forest and SAMME AdaBoost built from scratch) achieving **98.6% accuracy** on cipher type identification across Caesar, Substitution, Vigenère, and Transposition ciphers.

---

## 🚀 Quick Start

### Prerequisites
- **Python**: `3.10` or higher
- **Node.js**: `18.0` or higher (with `npm`)

### 1. Backend Setup

```bash
cd backend

# Install Python dependencies
pip install -r requirements.txt

# Run one-time corpus build & training pipeline (~10 MB download)
python -m scripts.build_corpus          # Downloads Gutenberg training/testing texts
python -m scripts.build_language_model  # Builds the 27x27 Laplace-smoothed bigram model
python -m scripts.build_dataset         # Generates 8,000 stratified cipher passages
python -m scripts.train_identifier      # Trains Random Forest, AdaBoost & K-Means models

# Launch Flask-SocketIO API Server (Listening on http://127.0.0.1:5000)
python app.py
```

### 2. Frontend Setup

In a separate terminal window:

```bash
cd frontend

# Install Node dependencies
npm install

# Start Vite Development Server (Listening on http://localhost:5173)
npm run dev
```

Open **`http://localhost:5173`** in your browser. Vite automatically proxies `/api` REST requests and `/socket.io` WebSocket connections to the backend.

---

## 🛠 Project Architecture

```
                               ┌──────────────────────────────────────────┐
                               │   React 18 + Tailwind + Recharts UI      │
                               │        (http://localhost:5173)           │
                               └────────────────────┬─────────────────────┘
                                                    │
                                         REST API / Socket.IO WS
                                                    │
                               ┌────────────────────▼─────────────────────┐
                               │     Flask + Flask-SocketIO Backend       │
                               │        (http://127.0.0.1:5000)           │
                               └─────────┬──────────────────────┬─────────┘
                                         │                      │
                   ┌─────────────────────▼──────┐    ┌──────────▼─────────────┐
                   │    MCMC & HMM Solvers      │    │  Classifier Pipeline   │
                   │ (Metropolis-Hastings / EM) │    │ (Random Forest/AdaBoost)│
                   └─────────────┬──────────────┘    └──────────┬─────────────┘
                                 │                      │
                   ┌─────────────▼──────────────┐    ┌──────────▼─────────────┐
                   │   27x27 Bigram LM Scorer   │    │ SQLite Execution Store │
                   │  (Fast O(1) Delta Scoring) │    │ (Runs & Leaderboard)   │
                   └────────────────────────────┘    └────────────────────────┘
```

---

## 🖥 Interactive Web Modules

CipherCrack provides six interactive modules designed for exploration and evaluation:

| Module | Features & Capabilities | Underlying Algorithms |
|---|---|---|
| **Crack Live** | Real-time ciphertext decipherment dashboard with live telemetry, key matrix animation, and accuracy convergence plots over Socket.IO. | Metropolis-Hastings MCMC, Baum-Welch HMM |
| **Encrypt Lab** | Custom plaintext puzzle generator supporting classical ciphers with automated random key generation. | Caesar, Substitution, Vigenère, Transposition |
| **Cipher Identifier** | Automatic identification of unknown ciphertexts from 49 statistical feature fingerprints. | Random Forest, SAMME AdaBoost, 2D K-Means PCA |
| **MCMC Playground** | Interactive 2D Gaussian mixture sampling visualization demonstrating chain mixing, step size $\sigma$, and Effective Sample Size (ESS). | Metropolis-Hastings, Box-Muller Transform |
| **Algorithm Arena** | Head-to-head performance benchmark comparing all five solvers on identical input texts. | MCMC, HMM, Hill Climbing, Steepest Ascent, Frequency Analysis |
| **Challenge Mode** | Interactive human-vs-AI cryptanalysis race with SQLite global leaderboard registration. | MCMC Metropolis Engine, SQLite Storage |

---

## 📊 Benchmark Results

### 1. MCMC Proposal Strategy Performance
*Evaluated on a 400-character substitution cipher (10 restarts × 10,000 iterations):*

| Proposal Strategy | Accuracy (%) | Throughput (it/s) | Acceptance Rate (%) |
|---|---|---|---|
| **Random Swap** | **99.7%** | 83,000 | 1.7% |
| **Frequency-Guided** | **99.7%** | **99,000** | **4.8%** |
| **Three-Letter Cycle** | **99.7%** | 71,000 | 1.4% |
| **Adaptive** | **99.7%** | 48,000 | 2.8% |

> **Key Finding:** Restarts dominate iterations. $10\text{ restarts} \times 10,000\text{ iterations}$ achieves **100% convergence** ($16/16$ runs) in $1.49\text{ seconds}$, whereas doubling iterations on a single chain yields negligible improvement due to local optima trapping.

### 2. Cipher Identifier Classification Accuracy
*Evaluated on 8,000 stratified samples (80/20 train/test split):*

| Classifier Implementation | Test Accuracy (%) | Macro F1 Score |
|---|---|---|
| **Random Forest (From Scratch)** | **98.6%** | **0.986** |
| **Random Forest (scikit-learn)** | 98.5% | 0.985 |
| **AdaBoost SAMME (From Scratch)** | 97.4% | 0.974 |
| **AdaBoost SAMME (scikit-learn)** | 97.4% | 0.974 |

### 3. Solver Comparison on 400-Character Text

| Solver Algorithm | Decoded Accuracy | Log-Likelihood Score / Char | Elapsed Execution Time |
|---|---|---|---|
| **MCMC (Metropolis-Hastings)** | **99.7%** | **−2.355** | 0.66s |
| **Hill Climbing** | **99.7%** | **−2.355** | 0.47s |
| **Steepest Ascent** | **99.7%** | **−2.355** | **0.22s** |
| **HMM (Baum–Welch EM)** | 85.5% | −3.184 | 11.20s |
| **Frequency Analysis** | 34.0% | −3.338 | 0.001s |

*(True ground truth plaintext scores $\mathbf{-2.360}$ per character under the bigram model).*

---

## 🔬 Mathematical & Algorithmic Foundations

### 1. Bigram Language Scoring & $O(1)$ Delta Evaluation
The English language model is represented as a $27 \times 27$ matrix $M$ (letters A–Z plus space) of log-probabilities:
$$\log P(T \mid K) = \sum_{i=1}^{N-1} \log M\big(K(c_i), K(c_{i+1})\big)$$

Rather than re-evaluating the full text of length $N$ on every proposal, scoring uses a precomputed $27 \times 27$ ciphertext count matrix $C$:
$$\log P(T \mid K) = \sum_{u=0}^{26} \sum_{v=0}^{26} C_{u,v} \cdot M_{K(u), K(v)}$$

When a proposal swaps key mapping for symbols $(a, b)$, only rows and columns corresponding to $a$ and $b$ change ($\sim 40$ matrix operations instead of $729$ or $N$). This plain Python implementation achieves **141,000 iterations/sec**, providing a **24× speedup** over general array library re-evaluations.

### 2. Fixed-Transition Baum-Welch HMM
In the Hidden Markov Model formulation:
- **Hidden States ($S$)**: 27 Plaintext characters.
- **Observations ($O$)**: 27 Ciphertext characters.
- **Transition Matrix ($A$)**: Held fixed to the English bigram model $M$.
- **Emission Matrix ($B$)**: Decryption key mapping to be learned.

Because $A$ is known, the M-step only estimates state posteriors $\gamma_t(i)$ rather than joint state transitions $\xi_t(i,j)$, maintaining computational stability during Baum-Welch Expectation-Maximization.

---

## 🗂 Codebase Structure

```
CipherCrack/
├── backend/
│   ├── app.py                  # Flask REST API & Socket.IO server entry point
│   ├── db.py                   # SQLite persistence layer (runs & leaderboard)
│   ├── api/
│   │   ├── routes.py           # REST endpoints (/api/encrypt, /api/identify, etc.)
│   │   └── sockets.py          # Socket.IO streaming event handlers
│   ├── ciphers/                # Classical cipher implementations (Caesar, Substitution, Vigenère, Transposition)
│   ├── ml/
│   │   ├── language_model.py   # 27x27 Bigram language model scorer
│   │   ├── scoring.py          # Three-tier optimized key scoring engine
│   │   ├── mcmc.py             # Metropolis-Hastings MCMC solver core
│   │   ├── proposals.py        # Proposal distributions (Random, Freq, 3-Cycle, Adaptive)
│   │   ├── hmm.py              # Forward-Backward, Baum-Welch EM, Viterbi
│   │   ├── forest.py           # Random Forest decision tree classifier
│   │   ├── adaboost.py         # SAMME AdaBoost classifier implementation
│   │   └── identifier.py       # Feature extraction & classification pipeline
│   ├── scripts/                # Corpus downloading, dataset building & model training scripts
│   └── tests/                  # Pytest automated unit test suite (63 tests)
│
└── frontend/
    ├── src/
    │   ├── pages/              # React pages (Crack, Encrypt, Identify, Playground, Arena, Challenge)
    │   ├── components/         # Shared UI components (Stat cards, KeyGrid, LiveText, PageHeader)
    │   ├── lib/
    │   │   ├── api.js          # REST client wrapper
    │   │   └── socket.js       # Socket.IO client singleton
    │   └── App.jsx             # Main router & layout container
    ├── index.html
    ├── tailwind.config.js      # Custom theme tokens (Obsidian Gold & Emerald Violet palette)
    └── vite.config.js          # Vite configuration & proxy rules
```

---

## 🧪 Testing & Verification

Run the automated Pytest suite for backend algorithms and ciphers:

```bash
cd backend
python -m pytest
```
*Executes all 63 unit tests verifying scoring delta correctness, cipher reversibility, MCMC proposals, and HMM forward-backward implementations.*

---

## 📜 References

1. **Diaconis, P.** (2009). *The Markov Chain Monte Carlo Revolution*. Bulletin of the American Mathematical Society, 46(2), 211-225.
2. **Knight, K., Nair, A., Rathod, N., & Yamada, K.** (2006). *Unsupervised Analysis for Decipherment Problems*. Proceedings of ACL.
3. **Zhu, J., Zou, H., Rosset, S., & Hastie, T.** (2009). *Multi-class AdaBoost*. Statistics and Its Interface, 2(3), 349-360.

---

<div align="center">

*CipherCrack — Designed & Developed for Machine Learning II (BAI702)*

</div>

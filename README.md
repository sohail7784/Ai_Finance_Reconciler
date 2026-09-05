<div align="center">

# AI Finance Reconciler ( An Ai Finance Controller Agent)
### An AI agent that reconciles your bank and Razorpay records — and tells you exactly why every mismatch happened.

**Built for the Razorpay Buildathon 2026 — AI Finance Controller Track**

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![Flask](https://img.shields.io/badge/Backend-Flask-black?logo=flask)
![AI](https://img.shields.io/badge/AI-NVIDIA%20NIM-76b900?logo=nvidia)
![Status](https://img.shields.io/badge/Status-Hackathon%20Submission-success)

</div>

---

## 😩 The Problem

Every business that takes payments through a gateway ends up with **two independent
stories about the same money** — one told by the **bank**, one told by **Razorpay**.

They almost never match perfectly:

- 💳 Processing fees get silently deducted
- 🧾 GST gets applied on top of that fee
- 🔁 Refunds go out and come back
- ✍️ Reference numbers get mistyped (`TXN1O4763` vs `TXN104763` — spot the difference?)

Somewhere, a finance team member is opening Excel right now, lining up two exports
side by side, and manually checking hundreds of rows — one by one. It's slow. It's
tedious. And under deadline pressure, it's exactly the kind of task where mistakes
slip through.

**This project builds an AI agent that does that entire job in seconds — and instead
of just flagging "these don't match," it tells you *why*, with a confidence score
you can actually trust.**

---

## ✨ What Makes This Different

Most reconciliation tools are either **100% manual** (slow, human-dependent) or
**100% black-box AI** (expensive, inconsistent, hard to trust). This agent takes a
third path:

> **Free rule-based logic handles the easy 85%. AI is used only where it actually
> adds value — reasoning through the ambiguous 15%.**

That means:
- ⚡ Fast — most transactions match instantly, with zero API cost
- 🎯 Honest — unresolved cases stay unresolved; we never fake a 100% match rate
- 🧠 Explainable — every AI decision comes with a plain-English reason and a
  confidence score, never a bare "yes/no"

---

## 🧭 How It Works — The Pipeline

```
┌─────────────────────┐     ┌──────────────────────────┐
│   🏦 Bank Statement   │     │  💳 Razorpay Settlement    │
│   (CSV: date, amount, │     │  (CSV: date, amount,      │
│    reference, balance)│     │   order_id, fee, GST)     │
└──────────┬───────────┘     └────────────┬──────────────┘
           │                              │
           └───────────────┬──────────────┘
                            ▼
              ┌──────────────────────────┐
              │     ⚙️ RULE ENGINE          │
              │  (free, instant, no AI)   │
              │  Matches on amount, date  │
              │  & reference number       │
              └─────────────┬─────────────┘
                            │
             ┌──────────────┴───────────────┐
             ▼                              ▼
   ┌───────────────────┐         ┌───────────────────────┐
   │   ✅ MATCHED         │         │   ❓ UNMATCHED           │
   │ Clean / Fee / GST /  │         │  Sent to the AI Agent  │
   │ Refund pairs         │         │  for deeper reasoning  │
   └───────────────────┘         └───────────┬───────────┘
                                              ▼
                                ┌───────────────────────────┐
                                │      🧠 AI AGENT             │
                                │  Finds same-date / similar- │
                                │  amount candidates, reasons │
                                │  about typos, delays, or    │
                                │  genuine gaps                │
                                └─────────────┬─────────────┘
                                              ▼
                                ┌───────────────────────────┐
                                │   📋 EXPLAINED REPORT        │
                                │  Verdict + Reason +          │
                                │  Confidence Score, for every │
                                │  single transaction           │
                                └───────────────────────────┘
```

### Step by step:

1. **Load** — Two CSVs (synthetic, realistic bank + Razorpay settlement data) are
   read into the engine.
2. **Auto-match** — A pure Python rule engine checks amount + date + reference
   instantly. It also recognizes standard 2% processing fees, 18% GST-on-fee
   deductions, and refund pairs (a credit followed by a matching debit).
3. **AI reasoning** — Whatever the rules genuinely can't explain gets handed to an
   LLM (via NVIDIA NIM), along with a short list of same-date / similar-amount
   candidates. The AI decides: is this a reference typo, a timing delay, or a truly
   unexplained gap — and says so in plain English with a confidence score.
4. **Report** — A live dashboard shows the full breakdown (donut chart, category
   counts, month-by-month trend, detailed table), a live "AI reasoning console"
   that streams the agent's thought process in real time, and a chatbot that
   answers natural-language questions about the data.

---

## 🖥️ What's Inside the App

| Page | What it shows |
|---|---|
| **Home** | The problem, the pipeline, and why this design was chosen |
| **Dashboard** | Live analytics — donut chart, category bar chart, matched-vs-unmatched trend line, detailed table — auto-refreshes if data changes |
| **AI Agent** | Run the agent on any batch size (slider scales up to the full unmatched count), watch it reason live in a terminal-style console, see per-batch confidence stats, and chat with it directly |

---

## 🛠️ Tech Stack

| Layer | Tech |
|---|---|
| Data generation | Python, pandas, Faker |
| Reconciliation engine | Pure Python (rule-based, zero AI cost) |
| AI reasoning | NVIDIA NIM (OpenAI-compatible API) |
| Backend | Flask + Flask-CORS |
| Frontend | HTML / CSS / vanilla JavaScript (no framework — fast, dependency-free) |
| Charts | Hand-rolled SVG (donut, bar, line) — no external chart library needed |

---

## 📁 Project Structure

```
Finance_Reconciliation_Agent/
├── data/
│   ├── bank_statement.csv
│   └── razorpay_settlement.csv
├── src/
│   ├── reconciliation.py       # Rule-based matching engine
│   └── llm_helper.py           # AI reasoning layer (NVIDIA NIM)
├── web/
│   └── index.html              # Frontend — Home / Dashboard / AI Agent
├── backend.py                  # Flask API connecting frontend to the engine
├── generate_data.py            # Synthetic data generator (edge cases included)
├── .env                        # API key (not committed)
└── README.md
```

---

## 🚀 How to Run This

### 1. Clone & set up the environment
```bash
git clone <your-repo-url>
cd Finance_Reconciliation_Agent
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux
```

### 2. Install dependencies
```bash
pip install pandas faker flask flask-cors openai python-dotenv
```

### 3. Add your API key
Create a `.env` file in the project root:
```
NVIDIA_API_KEY=your_nvidia_nim_api_key_here
```
(Get a free key at [build.nvidia.com](https://build.nvidia.com))

### 4. Generate the synthetic dataset
```bash
mkdir data
python generate_data.py
```
This creates realistic bank & Razorpay CSVs — including clean matches, fee
deductions, GST deductions, refund pairs, reference typos, and missing entries.

### 5. Start the backend
```bash
python backend.py
```
Leave this running — it serves the reconciliation + AI API on `http://127.0.0.1:5000`.

### 6. Open the app
Open `web/index.html` directly in your browser (double-click it, or right-click →
Open with → your browser). **Do not** open the backend's own URL — that's an API,
not the website.

---

## 🔍 A Peek at the Reasoning

Here's what the AI agent actually says when it catches a typo:

> **Transaction:** `TXN1O4763`, ₹21,762.02, 2026-04-01
> **Candidate found:** `TXN104763`, same amount, same date
> **Verdict:** ✅ MATCH FOUND (95% confidence)
> **Reason:** *"Reference number typo (O vs 0), but amount and date match exactly —
> indicating the same transaction."*

No hallucination, no guessing — grounded reasoning over the actual candidate data,
every time.

---

## 🔮 What I'd Build Next

- **Self-learning rules** — if the agent notices the same typo pattern (e.g. `O`↔`0`)
  recurring, it should propose a permanent rule instead of re-solving it with AI
  every time
- **Multi-transaction anomaly detection** — spotting systemic issues (e.g. "12
  transactions from the same date all show a fee mismatch") instead of judging one
  transaction at a time
- **Cash-flow forecasting** — using matched settlement history to project the next
  week's expected inflow

---

<div align="center">

**Built with ☕ and a lot of API-model-name debugging for the Razorpay Buildathon.**

</div>

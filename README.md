# StitchCheck — Knitting Pattern Tech Editor

> Grammarly for knitting patterns — with real stitch math.

StitchCheck parses knitting patterns, validates stitch counts, detects errors, and reviews formatting — like a compiler for knitting instructions.

## Features

- **File Upload**: Upload `.docx`, `.pdf`, or `.txt` pattern files
- **Stitch Count Validation**: Row-by-row stitch math verification
- **Multi-Size Support**: Parse and validate all sizes independently
- **Repeat Block Math**: Validate that repeat blocks divide evenly
- **Cross-Row Consistency**: Detect stitch count jumps between rows
- **Grammar & Terminology**: Flag typos, US/UK term mixing, bracket imbalance
- **Format Checks**: Verify presence of standard pattern sections
- **AI-Enhanced Mode** (optional): [Grok 4 via Replicate](https://replicate.com/xai/grok-4/api) (or xAI direct) reads the **full pattern** — every paragraph, explanations between rows, and in-between steps — for accurate stitch math and grammar review

## Architecture

```
backend/                  # Python FastAPI
├── main.py               # API endpoints
├── models/pattern.py     # Data models (Pattern, Section, Row, Operation)
├── parser/
│   ├── text_extractor.py # .docx / .pdf / .txt extraction
│   ├── pattern_parser.py # Full pattern → structured data
│   ├── stitch_parser.py  # Stitch instruction tokenizer
│   └── size_parser.py    # Multi-size value parsing
├── services/
│   ├── llm_service.py    # Grok (xAI) / Replicate API (parse + grammar)
│   └── llm_enhanced_parser.py  # Merge LLM output into pattern model
└── validator/
    ├── stitch_counter.py # Row-by-row stitch simulation
    └── format_checker.py # Grammar, terminology, format checks

frontend/                 # React + Vite
└── src/
    ├── App.jsx
    └── components/
        ├── FileUpload.jsx
        ├── ResultsView.jsx
        ├── SummaryCards.jsx
        ├── SizeSelector.jsx
        ├── PatternView.jsx
        └── ErrorList.jsx
```

## Quick Start

### Backend

```bash
cd backend
pip install -r requirements.txt
```

Optional — enable AI-enhanced parsing (Grok 4 via Replicate by default):

```bash
# Create backend/.env with your Replicate API token (Grok 4 is the default model)
echo "REPLICATE_API_TOKEN=your_token_here" > backend/.env
# Optional: default model is xai/grok-4; override if needed
# echo "REPLICATE_MODEL=xai/grok-4" >> backend/.env

# Or use xAI API directly (no Replicate) by setting only:
# echo "XAI_API_KEY=your_xai_key" > backend/.env
```

Then:

```bash
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 in your browser.

## Production deployment (Vercel for frontend + backend)

This repo is set up to run **both** the React frontend and the FastAPI backend on **Vercel**:

- **Build:** builds the frontend; output is `frontend/dist`.
- **API:** `api/analyze.py`, `api/analyze-text.py`, and `api/health.py` run the FastAPI backend so `/api/analyze`, `/api/analyze-text`, and `/api/health` work on the same host. `vercel.json` sets **maxDuration: 300** (5 min) for the analyze routes so the LLM (Replicate/Grok) can finish before the function times out.

No `VITE_API_URL` is needed (same origin). In the Vercel project, set **Environment Variables**: `REPLICATE_API_TOKEN` (and optionally `REPLICATE_MODEL`) for AI-enhanced mode.

**504 Gateway Timeout?** The backend calls Replicate (Grok), which can take 2–6+ minutes. On **Vercel Hobby** the function limit is 10s, so you’ll get 504. Use a **Pro** plan (or higher) so the 5‑minute limit applies, or move the backend to **Railway** (recommended, see below).

### Backend on Railway (recommended if not on Vercel Pro)

No request time limit — the API runs as a normal web process, so 2–6 minute Replicate calls are fine. Frontend stays on Vercel.

1. **Create a Railway project** at [railway.app](https://railway.app) and connect this repo.
2. **Set the service root** to the `backend` folder (Railway dashboard → your service → Settings → **Root Directory** = `backend`).
3. **Add env vars** in Railway (Variables): `REPLICATE_API_TOKEN` (and optionally `REPLICATE_MODEL=xai/grok-4`). No need to commit `.env`.
4. **Deploy** — Railway will use `backend/requirements.txt` and run `uvicorn main:app --host 0.0.0.0 --port $PORT`. It will assign a public URL (e.g. `https://your-app.up.railway.app`).
5. **Point the frontend at it** — In your **Vercel** project (the frontend), add an env var: **Name** `VITE_API_URL`, **Value** your Railway URL with no trailing slash (e.g. `https://your-app.up.railway.app`). Redeploy the frontend so the build picks it up.

Then disable or remove the Vercel API (so only the frontend is on Vercel): either delete the `api/` folder and rely on `VITE_API_URL`, or leave `api/` in place and keep `VITE_API_URL` set so the app calls Railway instead of same-origin `/api`.

## API

### POST /api/analyze
Upload a `.docx`, `.pdf`, or `.txt` file for analysis. Query param: `use_llm=true` (default) or `use_llm=false`.

### POST /api/analyze-text
Send raw pattern text as JSON: `{ "text": "...", "use_llm": true }`. If `REPLICATE_API_TOKEN` or `XAI_API_KEY` is set, AI-enhanced full-pattern parsing (Grok 4 via Replicate by default) and grammar review run when `use_llm` is true.

### GET /api/health
Returns `{ "status": "ok", "llm_available": true/false }`.

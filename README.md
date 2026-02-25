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
- **AI-Enhanced Mode** (optional): Replicate LLM (Llama 3 70B) for better parsing of natural-language instructions and extra grammar review

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
│   ├── llm_service.py    # Replicate API calls (parse + grammar)
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

Optional — enable AI-enhanced parsing and grammar review (Replicate):

```bash
# Create backend/.env with your Replicate API token
echo "REPLICATE_API_TOKEN=your_token_here" > backend/.env
# Optional: use 8B model (cheaper, less accurate) instead of 70B
# echo "REPLICATE_MODEL=meta/meta-llama-3-8b-instruct" >> backend/.env
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

## API

### POST /api/analyze
Upload a `.docx`, `.pdf`, or `.txt` file for analysis. Query param: `use_llm=true` (default) or `use_llm=false`.

### POST /api/analyze-text
Send raw pattern text as JSON: `{ "text": "...", "use_llm": true }`. If `REPLICATE_API_TOKEN` is set, AI-enhanced parsing and grammar review run when `use_llm` is true.

### GET /api/health
Returns `{ "status": "ok", "llm_available": true/false }`.

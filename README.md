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
Upload a `.docx`, `.pdf`, or `.txt` file for analysis.

### POST /api/analyze-text
Send raw pattern text as JSON `{ "text": "..." }`.

### GET /api/health
Health check endpoint.

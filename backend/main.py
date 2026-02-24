from __future__ import annotations
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from parser.text_extractor import extract_text, clean_text
from parser.pattern_parser import parse_pattern
from validator.stitch_counter import validate_pattern
from validator.format_checker import check_format, check_grammar

app = FastAPI(title="Knitting Tech Editor", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _pattern_to_dict(pattern) -> dict:
    sections = []
    for section in pattern.sections:
        rows = []
        for row in section.rows:
            rows.append({
                "number": row.number,
                "raw_text": row.raw_text,
                "side": row.side,
                "is_round": row.is_round,
                "expected_sts": row.expected_sts,
                "calculated_sts": row.calculated_sts,
                "errors": row.errors,
                "warnings": row.warnings,
                "is_repeat_ref": row.is_repeat_ref,
                "operations_count": len(row.operations),
                "repeat_blocks_count": len(row.repeat_blocks),
            })
        sections.append({
            "name": section.name,
            "rows": rows,
        })

    stitch_errors = [e for e in pattern.errors if e["type"] == "stitch_count"]
    repeat_errors = [e for e in pattern.errors if "repeat" in e.get("message", "").lower()]
    consistency_warnings = [w for w in pattern.warnings if w["type"] == "consistency"]

    return {
        "sizes": pattern.sizes,
        "cast_on_counts": pattern.cast_on_counts,
        "sections": sections,
        "materials": pattern.materials,
        "gauge": pattern.gauge,
        "finished_measurements": pattern.finished_measurements,
        "abbreviations": pattern.abbreviations,
        "notes": pattern.notes,
        "errors": pattern.errors,
        "warnings": pattern.warnings,
        "grammar_issues": pattern.grammar_issues,
        "format_issues": pattern.format_issues,
        "summary": {
            "stitch_count_errors": len(stitch_errors),
            "repetition_mismatches": len(repeat_errors),
            "consistency_warnings": len(consistency_warnings),
            "grammar_issues": len(pattern.grammar_issues),
            "format_warnings": len(pattern.format_issues),
            "total_rows_parsed": sum(len(s.rows) for s in pattern.sections),
            "total_sizes": len(pattern.sizes),
        },
    }


@app.post("/api/analyze")
async def analyze_pattern(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(400, "No file provided")

    ext = file.filename.rsplit(".", 1)[-1].lower()
    if ext not in ("docx", "pdf", "txt"):
        raise HTTPException(400, f"Unsupported file type: .{ext}. Use .docx, .pdf, or .txt")

    contents = await file.read()
    try:
        raw_text = extract_text(file.filename, contents)
    except Exception as e:
        raise HTTPException(400, f"Failed to extract text: {e}")

    raw_text = clean_text(raw_text)

    pattern = parse_pattern(raw_text)
    pattern = validate_pattern(pattern)
    pattern.format_issues = check_format(pattern)
    pattern.grammar_issues = check_grammar(pattern)

    return JSONResponse(_pattern_to_dict(pattern))


@app.post("/api/analyze-text")
async def analyze_text(body: dict):
    raw_text = body.get("text", "")
    if not raw_text.strip():
        raise HTTPException(400, "No text provided")

    raw_text = clean_text(raw_text)
    pattern = parse_pattern(raw_text)
    pattern = validate_pattern(pattern)
    pattern.format_issues = check_format(pattern)
    pattern.grammar_issues = check_grammar(pattern)

    return JSONResponse(_pattern_to_dict(pattern))


@app.get("/api/health")
async def health():
    return {"status": "ok"}

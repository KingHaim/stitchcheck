from __future__ import annotations
import sys
import os
import logging

sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from parser.text_extractor import extract_text, clean_text
from parser.pattern_parser import parse_pattern
from validator.stitch_counter import validate_pattern
from validator.format_checker import check_format, check_grammar
from services.llm_enhanced_parser import enhance_pattern_with_llm
from services.llm_service import llm_grammar_review, is_llm_available

# LLM grammar messages we skip (known false positives)
_LLM_GRAMMAR_BLOCKLIST = frozenset({
    "duplicate table of content",
    "duplicate table of contents",
})

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Knitting Tech Editor", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)


def _run_pipeline(raw_text: str, use_llm: bool = True) -> dict:
    raw_text = clean_text(raw_text)

    pattern = parse_pattern(raw_text)

    llm_used = False
    if use_llm:
        try:
            pattern = enhance_pattern_with_llm(pattern)
            llm_used = True
            logger.info("LLM-enhanced parsing complete")
        except Exception as e:
            logger.warning(f"LLM parsing failed, falling back to deterministic: {e}")

    pattern = validate_pattern(pattern)
    pattern.format_issues = check_format(pattern)
    pattern.grammar_issues = check_grammar(pattern)

    if use_llm:
        try:
            llm_issues = llm_grammar_review(raw_text)
            if llm_issues:
                existing_messages = {g["message"].lower() for g in pattern.grammar_issues}
                added = 0
                for issue in llm_issues:
                    if not isinstance(issue, dict) or not issue.get("message"):
                        continue
                    msg_lower = issue["message"].lower()
                    if msg_lower in existing_messages:
                        continue
                    if any(blocked in msg_lower for blocked in _LLM_GRAMMAR_BLOCKLIST):
                        continue
                    issue.setdefault("type", "grammar")
                    issue.setdefault("severity", "warning")
                    issue["source"] = "llm"
                    pattern.grammar_issues.append(issue)
                    added += 1
                logger.info(f"LLM grammar review: {len(llm_issues)} found, {added} new added")
        except Exception as e:
            logger.warning(f"LLM grammar review failed: {e}")

    return _pattern_to_dict(pattern, llm_used)


def _pattern_to_dict(pattern, llm_used: bool = False) -> dict:
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
        "llm_enhanced": llm_used,
        "summary": {
            "stitch_count_errors": len(stitch_errors),
            "repetition_mismatches": len(repeat_errors),
            "consistency_warnings": len(consistency_warnings),
            "grammar_issues": len(pattern.grammar_issues),
            "format_warnings": len(pattern.format_issues),
            "total_rows_parsed": sum(len(s.rows) for s in pattern.sections),
            "total_sizes": len(pattern.sizes),
            "llm_enhanced": llm_used,
        },
    }


@app.get("/")
async def root():
    return {"status": "ok", "service": "StitchCheck API", "docs": "/docs"}

@app.options("/api/analyze")
@app.options("/api/analyze-text")
async def options_analyze():
    return {}

@app.post("/api/analyze")
async def analyze_pattern(
    file: UploadFile = File(...),
    use_llm: bool = Query(True, description="Enable LLM-enhanced parsing"),
):
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

    return JSONResponse(_run_pipeline(raw_text, use_llm=use_llm))


@app.post("/api/analyze-text")
async def analyze_text(body: dict):
    raw_text = body.get("text", "")
    use_llm = body.get("use_llm", True)
    if not raw_text.strip():
        raise HTTPException(400, "No text provided")

    return JSONResponse(_run_pipeline(raw_text, use_llm=use_llm))


@app.get("/api/health")
async def health():
    return {"status": "ok", "llm_available": is_llm_available()}

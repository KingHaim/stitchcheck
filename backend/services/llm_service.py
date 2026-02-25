from __future__ import annotations
import json
import os
import re
import logging
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Replicate: default to Grok 4 (https://replicate.com/xai/grok-4/api); fallback to xAI direct if no token
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")
REPLICATE_MODEL = os.getenv("REPLICATE_MODEL", "xai/grok-4")
XAI_API_KEY = os.getenv("XAI_API_KEY")
XAI_MODEL = os.getenv("XAI_MODEL", "grok-2")

# Full-pattern prompt: read EVERYTHING — rows, explanations between them, in-between steps, construction
PARSE_SYSTEM_PROMPT = """You are a knitting pattern expert. Read the ENTIRE pattern from start to finish.

Do NOT only look at lines that say "Row N:" or "Rnd N:". You must also read:
- Explanatory paragraphs between rows (what is being shaped, why, construction notes)
- Instructions that happen BETWEEN numbered rows (e.g. "divide for legs", "cast on 8 at underarm", "place marker at beg of rnd", "slip sts to holder")
- Any prose that sets up the next row or changes stitch count

Use this full context to understand what each row does and what the overall construction is. Then output a single JSON object.

Output structure (output raw JSON only, no markdown or extra text):

{
  "sizes": ["XS", "S", "M", ...],
  "cast_on": [57, 61, 65, ...],
  "sections": ["Ribbing", "Body", ...],
  "rows": [
    {"number": 1, "side": "WS", "is_round": false, "is_work_even": false, "operations": [{"op": "p", "count": 1}], "repeat_blocks": [{"operations": [{"op": "k", "count": 1}, {"op": "p", "count": 1}], "repeat_to_end": true, "repeat_count": null, "until_sts_remain": null}], "expected_sts": [57, 61, ...]}
  ],
  "between_steps": [
    {"after_row": 1, "description": "Cast on 8 sts at underarm", "cast_on_extra": 8},
    {"after_row": 5, "description": "Divide for legs; place half on holder"}
  ]
}

Rules:
- Valid ops: k, p, sl, sm, pm, k2tog, ssk, p2tog, yo, m1, m1l, m1r, kfb, bo, co, sk2p, k3tog
- "work even" or "work as established" → is_work_even: true, operations: []
- expected_sts: from "(42 sts)" or "— 42 sts" at end of row, as array per size; null if not stated
- between_steps: only steps that change stitch count or clearly set up the next row (cast on extra, divide, place markers before next row). Use cast_on_extra (number) when the pattern says to cast on N more stitches. Omit if nothing between rows.
- Infer row meaning from surrounding explanation (e.g. "increase round" in the paragraph above Row 2 means Row 2 has increases).
- Output raw JSON only. No markdown. No explanation before or after."""

GRAMMAR_SYSTEM_PROMPT = """You are a knitting pattern proofreader. Output ONLY a JSON array.

Review the pattern for: typos, US/UK term mixing, abbreviation inconsistency, unclear instructions, unbalanced brackets.

Output format — a JSON array (use [] if no issues):
[{"line": 1, "severity": "warning", "type": "grammar", "message": "description", "raw_text": "the text", "suggestion": "fix"}]

Output raw JSON only. No markdown. No explanation. No text before or after the JSON array."""


def _call_grok(system_prompt: str, user_prompt: str) -> str | None:
    """Call xAI Grok API (OpenAI-compatible)."""
    if not XAI_API_KEY:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=XAI_API_KEY, base_url="https://api.x.ai/v1")
        response = client.chat.completions.create(
            model=XAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=8192,
            temperature=0.1,
        )
        choice = response.choices[0] if response.choices else None
        if choice and choice.message and choice.message.content:
            return choice.message.content.strip()
        return None
    except Exception as e:
        logger.warning(f"Grok (xAI) call failed: {e}")
        return None


def _call_replicate(system_prompt: str, user_prompt: str) -> str | None:
    """Call Replicate API — default model xai/grok-4 (Grok 4)."""
    if not REPLICATE_API_TOKEN:
        return None
    try:
        import replicate
        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        output = replicate.run(
            REPLICATE_MODEL,
            input={
                "prompt": full_prompt,
                "max_tokens": 8192,
                "temperature": 0.1,
            },
        )
        result = "".join(output) if hasattr(output, "__iter__") and not isinstance(output, str) else str(output)
        return result.strip()
    except Exception as e:
        logger.warning(f"Replicate call failed: {e}")
        return None


def _call_llm(system_prompt: str, user_prompt: str) -> str | None:
    """Use Replicate (Grok 4 by default) if token set, else xAI direct API."""
    out = _call_replicate(system_prompt, user_prompt)
    if out is not None:
        logger.info(f"LLM: using Replicate ({REPLICATE_MODEL})")
        return out
    out = _call_grok(system_prompt, user_prompt)
    if out is not None:
        logger.info("LLM: using Grok (xAI direct)")
        return out
    logger.warning("No LLM provider available (set REPLICATE_API_TOKEN or XAI_API_KEY)")
    return None


def _extract_json(text: str) -> Optional[dict | list]:
    """Robust JSON extraction from LLM output that may contain extra text."""
    if not text:
        return None

    json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if json_match:
        text = json_match.group(1).strip()

    for start_char, end_char in [("{", "}"), ("[", "]")]:
        start = text.find(start_char)
        if start == -1:
            continue
        depth = 0
        end_pos = -1
        in_string = False
        escape_next = False
        for i in range(start, len(text)):
            ch = text[i]
            if escape_next:
                escape_next = False
                continue
            if ch == '\\':
                escape_next = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == start_char:
                depth += 1
            elif ch == end_char:
                depth -= 1
                if depth == 0:
                    end_pos = i
                    break
        if end_pos > start:
            candidate = text[start : end_pos + 1]
            candidate = re.sub(r',\s*([}\]])', r'\1', candidate)
            try:
                return json.loads(candidate)
            except json.JSONDecodeError as e:
                logger.debug(f"JSON parse failed: {e}, trying cleanup")
                candidate = candidate.replace("'", '"')
                candidate = re.sub(r'(\w+)\s*:', r'"\1":', candidate)
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    pass
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        logger.warning(f"Could not extract JSON from LLM output: {text[:300]}")
        return None


def llm_parse_pattern(raw_text: str) -> Optional[dict]:
    """Parse full pattern (rows + explanations + in-between steps) into structured JSON."""
    prompt = (
        "Parse this knitting pattern using the full text. "
        "Read every paragraph and instruction, not only Row/Rnd lines. "
        "Include between_steps for any cast-on extra or setup between rows.\n\n"
        f"{raw_text}"
    )
    result = _call_llm(PARSE_SYSTEM_PROMPT, prompt)
    if not result:
        return None
    parsed = _extract_json(result)
    if isinstance(parsed, dict):
        rows = parsed.get("rows", [])
        between = parsed.get("between_steps", [])
        logger.info(f"LLM parsed pattern: {len(rows)} rows, {len(parsed.get('sizes', []))} sizes, {len(between)} between_steps")
        return parsed
    if isinstance(parsed, list) and parsed and isinstance(parsed[0], dict):
        logger.info("LLM returned list instead of dict, wrapping as rows")
        return {"rows": parsed, "between_steps": []}
    return None


def llm_grammar_review(raw_text: str) -> Optional[list[dict]]:
    lines = raw_text.split("\n")
    numbered = "\n".join(f"Line {i+1}: {line}" for i, line in enumerate(lines) if line.strip())
    prompt = f"Review this knitting pattern for issues. Return a JSON array:\n\n{numbered}"
    result = _call_llm(GRAMMAR_SYSTEM_PROMPT, prompt)
    if not result:
        return None
    parsed = _extract_json(result)
    if isinstance(parsed, list):
        valid = [item for item in parsed if isinstance(item, dict) and "message" in item]
        logger.info(f"LLM grammar review found {len(valid)} issues")
        return valid
    if isinstance(parsed, dict):
        if "issues" in parsed:
            return [i for i in parsed["issues"] if isinstance(i, dict)]
        if "message" in parsed:
            return [parsed]
        for v in parsed.values():
            if isinstance(v, list):
                valid = [i for i in v if isinstance(i, dict) and "message" in i]
                if valid:
                    return valid
        return None
    return None


def is_llm_available() -> bool:
    """True if Grok or Replicate is configured."""
    return bool(XAI_API_KEY or REPLICATE_API_TOKEN)

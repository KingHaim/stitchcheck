from __future__ import annotations
import json
import os
import re
import logging
from typing import Optional

import replicate
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

REPLICATE_MODEL = os.getenv("REPLICATE_MODEL", "meta/meta-llama-3-70b-instruct")

PARSE_SYSTEM_PROMPT = """You are a knitting pattern parser that outputs ONLY JSON.

Given knitting pattern text, return a single JSON object with this exact structure:

{"sizes": ["XS", "S"], "cast_on": [57, 61], "sections": ["Ribbing"], "rows": [{"number": 1, "side": "WS", "is_round": false, "is_work_even": false, "operations": [{"op": "p", "count": 1}], "repeat_blocks": [{"operations": [{"op": "p", "count": 1}, {"op": "k", "count": 1}], "repeat_to_end": true, "repeat_count": null, "until_sts_remain": null}], "expected_sts": [57]}]}

Rules:
- Valid ops: k, p, sl, k2tog, ssk, p2tog, yo, m1, m1l, m1r, kfb, bo, co, sk2p, k3tog
- "work even" or "work as established" → is_work_even: true, operations: []
- "decrease N sts evenly" → N operations of k2tog
- expected_sts: extract from "(42 sts)" at end of row, as integer list; null if not stated
- Output raw JSON only. No markdown. No explanation. No text before or after the JSON."""

GRAMMAR_SYSTEM_PROMPT = """You are a knitting pattern proofreader. Output ONLY a JSON array.

Review the pattern for: typos, US/UK term mixing, abbreviation inconsistency, unclear instructions, unbalanced brackets.

Output format — a JSON array (use [] if no issues):
[{"line": 1, "severity": "warning", "type": "grammar", "message": "description", "raw_text": "the text", "suggestion": "fix"}]

Output raw JSON only. No markdown. No explanation. No text before or after the JSON array."""


def _call_llm(system_prompt: str, user_prompt: str) -> str | None:
    token = os.getenv("REPLICATE_API_TOKEN")
    if not token:
        logger.warning("No REPLICATE_API_TOKEN set, skipping LLM call")
        return None

    try:
        output = replicate.run(
            REPLICATE_MODEL,
            input={
                "prompt": f"[INST]{system_prompt}\n\n{user_prompt}[/INST]",
                "max_tokens": 4096,
                "temperature": 0.05,
                "top_p": 0.9,
            },
        )
        result = "".join(output)
        logger.debug(f"LLM raw output ({len(result)} chars): {result[:500]}")
        return result.strip()
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
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
    prompt = f"Parse this knitting pattern into the JSON format specified:\n\n{raw_text}"
    result = _call_llm(PARSE_SYSTEM_PROMPT, prompt)
    if not result:
        return None
    parsed = _extract_json(result)
    if isinstance(parsed, dict):
        logger.info(f"LLM parsed pattern: {len(parsed.get('rows', []))} rows, {len(parsed.get('sizes', []))} sizes")
        return parsed
    if isinstance(parsed, list):
        if parsed and isinstance(parsed[0], dict):
            logger.info("LLM returned list instead of dict, wrapping as rows")
            return {"rows": parsed}
        logger.warning(f"LLM parse returned list of non-dicts: {str(parsed)[:200]}")
        return None
    logger.warning(f"LLM parse returned unexpected type: {type(parsed)}")
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
            logger.info("LLM grammar returned single issue as dict, wrapping in list")
            return [parsed]
        values_lists = [v for v in parsed.values() if isinstance(v, list)]
        if values_lists:
            items = values_lists[0]
            valid = [i for i in items if isinstance(i, dict) and "message" in i]
            if valid:
                logger.info(f"LLM grammar: extracted {len(valid)} issues from dict wrapper")
                return valid
        logger.warning(f"LLM grammar returned dict without recognizable issues: {list(parsed.keys())}")
        return None
    logger.warning(f"LLM grammar review returned unexpected type: {type(parsed)}")
    return None

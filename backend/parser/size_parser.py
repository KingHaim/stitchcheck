from __future__ import annotations
import re


def parse_size_definitions(text: str) -> list[str]:
    """Extract size labels from a line like 'Sizes: XS (S, M, L, XL, 2XL, 3XL)'."""
    m = re.search(
        r"sizes?\s*:\s*(.+)",
        text,
        re.IGNORECASE,
    )
    if not m:
        return []

    raw = m.group(1).strip()
    raw = raw.replace("(", ",").replace(")", ",")
    sizes = [s.strip() for s in re.split(r"[,/]+", raw) if s.strip()]
    return sizes


def parse_multi_size_values(text: str) -> list[int]:
    """
    Parse a multi-size value line into a list of integers.

    Accepts formats like:
      57, (57), 61, (69), 69, (77), 77
      57 (57, 61, 69, 69, 77, 77)
      57 (57) 61 (69) 69 (77) 77
      57, 57, 61, 69, 69, 77, 77
    """
    cleaned = text.replace("(", " ").replace(")", " ")
    cleaned = re.sub(r"[,;]+", " ", cleaned)
    cleaned = re.sub(r"\b(?:sts?|stitches?|CO|cast\s*on)\b", " ", cleaned, flags=re.IGNORECASE)
    numbers = re.findall(r"\b(\d+)\b", cleaned)
    return [int(n) for n in numbers]


def parse_cast_on_line(text: str) -> list[int]:
    """Parse a cast-on line to extract stitch counts per size."""
    m = re.search(r"(?:CO|cast\s*on)\s+(.+?)(?:\bsts?\b|$)", text, re.IGNORECASE)
    if m:
        return parse_multi_size_values(m.group(1))
    return parse_multi_size_values(text)


def map_sizes_to_counts(sizes: list[str], counts: list[int]) -> dict[str, int]:
    """Map size labels to their cast-on counts. Generate labels if needed."""
    if not sizes:
        sizes = [f"Size{i + 1}" for i in range(len(counts))]
    elif len(sizes) < len(counts):
        for i in range(len(sizes), len(counts)):
            sizes.append(f"Size{i + 1}")

    result: dict[str, int] = {}
    for i, count in enumerate(counts):
        if i < len(sizes):
            result[sizes[i]] = count
    return result


# Patterns for stitch-count assertions anywhere in the document (not just row lines)
# [56, 60, 66] st or [56, 60, 66, 68, 76, 84 st for each leg]
_ASSERTION_BRACKET = re.compile(
    r"\[\s*([\d\s,]+)\s+(?:st(?:s|itches)?\.?)(?:\s+[^\]]*)?\]|\[\s*([\d\s,]+)\s*\]\s*(?:st(?:s|itches)?\.?)",
    re.IGNORECASE,
)
_ASSERTION_PAREN = re.compile(
    r"\(\s*([\d\s,]+)\s*\)\s*(?:st(?:s|itches)?|st\.)",
    re.IGNORECASE,
)
_ASSERTION_DASH = re.compile(
    r"[-–—]\s*([\d\s,]+)\s*st(?:s|itches)?\s*\.?\s*$",
    re.IGNORECASE,
)


def extract_all_stitch_assertions(text: str) -> list[dict]:
    """
    Scan the full document for stitch-count assertions (e.g. [56, 60, 66] st, — 112 sts).
    Returns list of {line: int, counts: list[int], raw_text: str}.
    """
    results: list[dict] = []
    lines = text.split("\n")
    seen_at_line: dict[int, str] = {}  # avoid duplicate (line, raw) from same line

    for line_num, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped:
            continue
        # Skip lines that are "remain" context (e.g. "X sts remain on needle")
        if re.search(r"sts?\s+remain|remain\s+on", stripped, re.IGNORECASE):
            continue
        # Bracketed list: [56, 60, 66, 68, 76, 84] st — skip "X st increased/decreased" (that's change, not total)
        for m in _ASSERTION_BRACKET.finditer(stripped):
            raw = m.group(0)
            if re.search(r"increased?|decreased?", raw, re.IGNORECASE):
                continue
            key = (line_num, raw)
            if key in seen_at_line:
                continue
            seen_at_line[key] = raw
            nums = (m.group(1) or m.group(2) or "").strip()
            counts = parse_multi_size_values(nums) if nums else []
            if counts:
                results.append({"line": line_num, "counts": counts, "raw_text": raw})
        # Parenthetical: (108, 116, 124) sts — only if clearly stitch count (not "4st increased")
        for m in _ASSERTION_PAREN.finditer(stripped):
            raw = m.group(0)
            key = (line_num, raw)
            if key in seen_at_line:
                continue
            # Skip "Nst increased" style
            if re.search(r"increased?|decreased?", raw, re.IGNORECASE):
                continue
            seen_at_line[key] = raw
            counts = parse_multi_size_values(m.group(1))
            if counts:
                results.append({"line": line_num, "counts": counts, "raw_text": raw})
        # Dash at end: — 112 sts
        m = _ASSERTION_DASH.search(stripped)
        if m:
            raw = m.group(0)
            key = (line_num, raw)
            if key not in seen_at_line:
                seen_at_line[key] = raw
                counts = parse_multi_size_values(m.group(1))
                if counts:
                    results.append({"line": line_num, "counts": counts, "raw_text": raw})

    return results


def extract_stated_stitch_count(text: str) -> list[int] | None:
    """
    Extract stated stitch count from end-of-row markers like '(42 sts)' or '— 42 sts'.
    Only matches when it's clearly the row's result count, not e.g. "[108, 116...] st remain"
    or "Knit 4, 4, 4, 6, 6, 6 st" in the middle of instructions.
    """
    text = text.strip()
    # Ignore lines that say "remain" (e.g. "[108, 116...] st remain on the needles")
    if re.search(r"sts?\s+remain|remain\s+on", text, re.IGNORECASE):
        return None

    # Explicit end-of-row: "— 108 sts" or "— 108, 116, 128 sts" at end of line
    m = re.search(r"[-–—]\s*([\d\s,()]+)\s*sts?\s*\.?\s*$", text, re.IGNORECASE)
    if m:
        return parse_multi_size_values(m.group(1))

    # Parenthetical at end: "(108 sts)" or "(4st increased)" — only (X sts) not (Xst increased)
    tail = text[-55:] if len(text) > 55 else text
    m = re.search(r"\(\s*([\d\s,]+)\s*sts?\s*\)\s*$", tail, re.IGNORECASE)
    if m:
        return parse_multi_size_values(m.group(1))

    return None

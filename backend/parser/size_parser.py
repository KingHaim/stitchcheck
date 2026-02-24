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


def extract_stated_stitch_count(text: str) -> list[int] | None:
    """
    Extract stated stitch count from end-of-row markers like '(42 sts)' or '[42 sts]'.
    Supports multi-size counts.
    """
    m = re.search(r"[\(\[]([\d\s,()]+)\s*sts?\s*[\)\]]", text, re.IGNORECASE)
    if m:
        return parse_multi_size_values(m.group(1))

    m = re.search(r"[-–—]\s*([\d\s,()]+)\s*sts?\s*\.?\s*$", text, re.IGNORECASE)
    if m:
        return parse_multi_size_values(m.group(1))

    return None

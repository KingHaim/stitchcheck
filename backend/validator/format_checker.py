from __future__ import annotations
import re
from models.pattern import Pattern


_US_UK_TERMS = {
    "tension": "gauge",
    "moss stitch": "seed stitch",
    "stocking stitch": "stockinette",
    "colour": "color",
    "cast off": "bind off",
}

_COMMON_TYPOS = {
    "knt": "knit",
    "prrl": "purl",
    "slp": "slip",
    "caston": "cast on",
    "bindoff": "bind off",
    "yran over": "yarn over",
    "k2tg": "k2tog",
    "k2 tg": "k2tog",
    "yoknit": "yo, knit",
    "stiches": "stitches",
    "guage": "gauge",
    "stockingette": "stockinette",
    "gague": "gauge",
    "incease": "increase",
    "decease": "decrease",
    "repeatfrom": "repeat from",
}

_REQUIRED_SECTIONS = [
    ("materials", r"materials?\s*:", "Materials section"),
    ("gauge", r"gauge|tension", "Gauge section"),
    ("measurements", r"finished\s+measurements?|dimensions?", "Finished measurements"),
    ("abbreviations", r"abbreviations?", "Abbreviations section"),
    ("instructions", r"(?:row|rnd|round)\s+\d+", "Pattern instructions"),
]


def check_format(pattern: Pattern) -> list[dict]:
    issues: list[dict] = []
    text_lower = pattern.raw_text.lower()

    for section_id, regex, label in _REQUIRED_SECTIONS:
        if not re.search(regex, text_lower, re.IGNORECASE):
            issues.append({
                "type": "format",
                "severity": "warning",
                "message": f"Missing: {label}",
            })

    return issues


def check_grammar(pattern: Pattern) -> list[dict]:
    issues: list[dict] = []
    lines = pattern.raw_text.split("\n")

    for line_num, line in enumerate(lines, 1):
        line_lower = line.lower()

        for typo, correction in _COMMON_TYPOS.items():
            if re.search(r"\b" + re.escape(typo) + r"\b", line_lower, re.IGNORECASE):
                issues.append({
                    "type": "grammar",
                    "severity": "warning",
                    "line": line_num,
                    "message": f'Possible typo: "{typo}" → did you mean "{correction}"?',
                    "raw_text": line.strip(),
                })

        for uk_term, us_term in _US_UK_TERMS.items():
            if uk_term in line_lower:
                issues.append({
                    "type": "terminology",
                    "severity": "info",
                    "line": line_num,
                    "message": f'UK term "{uk_term}" found — US equivalent is "{us_term}"',
                    "raw_text": line.strip(),
                })

        _check_abbreviation_consistency(line, line_num, issues)

    # Bracket/parenthesis balance: check once on full text to avoid false positives from multi-line lists
    _check_bracket_balance_document(pattern.raw_text, issues)

    return issues


def _check_bracket_balance_document(text: str, issues: list[dict]) -> None:
    """Check bracket balance on the full document; report once per type if unbalanced."""
    for open_ch, close_ch, name in [("(", ")", "parentheses"), ("[", "]", "brackets"), ("{", "}", "braces")]:
        if text.count(open_ch) != text.count(close_ch):
            issues.append({
                "type": "grammar",
                "severity": "warning",
                "line": None,
                "message": f"Unbalanced {name} in document (check that all {open_ch} have a matching {close_ch})",
                "raw_text": "",
            })


def _check_abbreviation_consistency(line: str, line_num: int, issues: list[dict]) -> None:
    # Skip glossary/abbreviations lines: "K2TOG: Knit two...", "P2tog tbl: Purl 2...", "k5into1: Knit into..." — mixing is intentional
    stripped = line.strip()
    if re.match(r"^[A-Za-z0-9*/]+(?:\s+[a-z]+)?:\s*.+", stripped):
        return
    has_full_knit = bool(re.search(r"\bknit\b", line, re.IGNORECASE))
    has_abbr_k = bool(re.search(r"\bk\d", line, re.IGNORECASE))
    if has_full_knit and has_abbr_k:
        issues.append({
            "type": "terminology",
            "severity": "info",
            "line": line_num,
            "message": 'Mixed use of "knit" and "k" abbreviation in same line',
            "raw_text": line.strip(),
        })

    has_full_purl = bool(re.search(r"\bpurl\b", line, re.IGNORECASE))
    has_abbr_p = bool(re.search(r"\bp\d", line, re.IGNORECASE))
    if has_full_purl and has_abbr_p:
        issues.append({
            "type": "terminology",
            "severity": "info",
            "line": line_num,
            "message": 'Mixed use of "purl" and "p" abbreviation in same line',
            "raw_text": line.strip(),
        })

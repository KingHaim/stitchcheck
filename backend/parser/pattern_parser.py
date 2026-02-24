from __future__ import annotations
import re
from models.pattern import Pattern, Section, Row
from parser.stitch_parser import parse_row_instructions
from parser.size_parser import (
    parse_size_definitions,
    parse_cast_on_line,
    map_sizes_to_counts,
    extract_stated_stitch_count,
    parse_multi_size_values,
)

_ROW_PATTERN = re.compile(
    r"^(?:Row|Rnd|Round)\s+(\d+)\s*(?:\(([RW]S)\))?\s*:\s*(.+)",
    re.IGNORECASE,
)

_CO_PATTERN = re.compile(
    r"(?:CO|Cast\s*on)\s+",
    re.IGNORECASE,
)

_SECTION_PATTERN = re.compile(
    r"^(?:#{1,3}\s+|=+\s*)?([A-Z][A-Za-z\s]+)(?:\s*=+)?\s*$",
)

_WORK_UNTIL_PATTERN = re.compile(
    r"work\s+(?:as\s+above|as\s+established|even)\s+until",
    re.IGNORECASE,
)

_SIZES_PATTERN = re.compile(
    r"sizes?\s*:",
    re.IGNORECASE,
)

_GAUGE_PATTERN = re.compile(r"gauge\s*:", re.IGNORECASE)
_MATERIALS_PATTERN = re.compile(r"materials?\s*:", re.IGNORECASE)
_MEASUREMENTS_PATTERN = re.compile(r"finished\s+measurements?\s*:", re.IGNORECASE)
_ABBREVIATIONS_PATTERN = re.compile(r"abbreviations?\s*:", re.IGNORECASE)
_NOTES_PATTERN = re.compile(r"notes?\s*:", re.IGNORECASE)


def parse_pattern(text: str) -> Pattern:
    pattern = Pattern(raw_text=text)
    lines = text.split("\n")

    current_section = Section(name="Main")
    pattern.sections.append(current_section)

    sizes_found = False
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        i += 1

        if not line:
            continue

        if _SIZES_PATTERN.search(line):
            pattern.sizes = parse_size_definitions(line)
            sizes_found = True
            continue

        if _GAUGE_PATTERN.search(line):
            pattern.gauge = line
            continue
        if _MATERIALS_PATTERN.search(line):
            pattern.materials = line
            continue
        if _MEASUREMENTS_PATTERN.search(line):
            pattern.finished_measurements = line
            continue
        if _ABBREVIATIONS_PATTERN.search(line):
            pattern.abbreviations = line
            continue
        if _NOTES_PATTERN.search(line) and not current_section.rows:
            pattern.notes = line
            continue

        if _CO_PATTERN.search(line):
            counts = parse_cast_on_line(line)
            if counts:
                if not pattern.sizes:
                    pattern.sizes = [f"Size{j + 1}" for j in range(len(counts))]
                pattern.cast_on_counts = map_sizes_to_counts(pattern.sizes, counts)

                co_row = Row(
                    number=0,
                    raw_text=line,
                    expected_sts={s: c for s, c in pattern.cast_on_counts.items()},
                    calculated_sts={s: c for s, c in pattern.cast_on_counts.items()},
                )
                current_section.rows.append(co_row)
            continue

        m_section = _SECTION_PATTERN.match(line)
        if m_section and not _ROW_PATTERN.match(line):
            name = m_section.group(1).strip()
            if len(name) > 3 and not any(
                kw in name.lower()
                for kw in ("row", "rnd", "round", "repeat", "next")
            ):
                current_section = Section(name=name)
                pattern.sections.append(current_section)
                continue

        if _WORK_UNTIL_PATTERN.search(line):
            row = Row(
                raw_text=line,
                is_repeat_ref=True,
                segment_label=line,
            )
            current_section.rows.append(row)
            continue

        m_row = _ROW_PATTERN.match(line)
        if m_row:
            row_num = int(m_row.group(1))
            side = m_row.group(2).upper() if m_row.group(2) else None
            instruction_text = m_row.group(3).strip()
            is_round = line.lower().startswith("rnd") or line.lower().startswith("round")

            stated = extract_stated_stitch_count(instruction_text)
            expected_sts = None
            if stated and pattern.sizes:
                expected_sts = map_sizes_to_counts(pattern.sizes, stated)
            elif stated:
                expected_sts = {f"Size{j + 1}": v for j, v in enumerate(stated)}

            flat_ops, repeat_blocks = parse_row_instructions(instruction_text)

            row = Row(
                number=row_num,
                raw_text=line,
                side=side,
                is_round=is_round,
                operations=flat_ops,
                repeat_blocks=repeat_blocks,
                expected_sts=expected_sts,
            )
            current_section.rows.append(row)
            continue

    pattern.sections = [s for s in pattern.sections if s.rows or s.notes]
    if not pattern.sections:
        pattern.sections = [Section(name="Main")]

    return pattern

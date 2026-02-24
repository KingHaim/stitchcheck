# Knitting Tech Editing App — Functional Specification

## Overview

This document defines the core features and logic for a knitting **tech editing** application focused on:

* Stitch count validation (primary feature)
* Logical consistency across rows/rounds
* Multi-size pattern parsing
* Formatting and grammar review
* Uploading Word/PDF patterns

The goal is to act like a **compiler for knitting patterns**: parse instructions, model stitch math, and detect inconsistencies automatically.

---

## Core Concept

The app does not just read text. It:

1. Parses knitting instructions into structured data.
2. Converts instructions into mathematical operations.
3. Simulates stitch flow row by row.
4. Validates expected stitch counts and pattern coherence.

Example:

```
Row 5: k3, *k2tog, k5* repeat to end (42 sts)
```

Internal representation (conceptual):

```
START = previous_row_sts
OPERATION = repeat block (-1 every 7 sts)
EXPECTED_END = 42
```

---

## Input Handling

### Supported Uploads

* `.docx` (Word)
* `.pdf`

### Extraction Goals

* Plain text
* Tables
* Headings / sections
* Row / round blocks
* Size definitions

---

## Multi-Size Parsing (Critical)

Patterns often contain multiple sizes in one line.

Example input:

```
CO 57, (57), 61, (69), 69, (77), 77 st
```

### Expected Parsing Result

```
CO_counts = [57, 57, 61, 69, 69, 77, 77]
```

### Normalization Rules

Accept common variants:

* `57 (57, 61, 69, 69, 77, 77)`
* `57 (57) 61 (69) 69 (77) 77`
* `57, 57, 61, 69, 69, 77, 77`
* `CO 57 (57, 61, 69, 69, 77, 77) sts`

### Size Mapping

If the pattern defines sizes, e.g.:

```
Sizes: XS (S, M, L, XL, 2XL, 3XL)
```

Map values automatically.

If no sizes are declared:

* assign temporary labels: Size1..SizeN
* allow user confirmation/edit.

---

## Stitch Language Parser

The parser must recognize stitch operations and their math effects.

### Examples

| Instruction       | Effect on stitch count |
| ----------------- | ---------------------- |
| k, p, sl          | 0                      |
| k2tog, ssk        | -1                     |
| yo, m1l, m1r, kfb | +1                     |
| work even         | 0                      |

### Control Flow Instructions

* repeat from * to *
* repeat N times
* until X sts remain
* work as established / work as above

These must be interpreted as loops or state transitions.

---

## Stitch Count Validator (Primary Feature)

For each row and each size:

1. Start with previous stitch count.
2. Apply operations in order.
3. Calculate resulting stitch count.
4. Compare with stated count (if provided).

### Example Output

```
ERROR: Row 12
Expected: 64 sts
Calculated: 66 sts
```

---

## Example: Ribbing Logic

Input:

```
Row 1 (WS): *P1, K1*, repeat until 1 st is left, p1
Row 2 (RS): *K1, P1*, repeat until 1 st is left, k1
```

Validation logic:

* Consume stitches in blocks of 2.
* Stop when 1 stitch remains.
* Execute final stitch.
* Total consumed must equal starting stitch count.
* Stitch count remains unchanged.

The validator must test this for **each size** independently.

---

## Section / Segment Tracking

Patterns include non-row instructions such as:

```
Work as above until ribbing measures 1.5 cm.
```

Behavior:

* Mark as repeat segment.
* No stitch count changes unless explicitly stated.
* Preserve current stitch count state.

Example timeline:

* Segment A: Cast on + Ribbing
* Segment B: Raglan setup
* Segment C: Increase rounds

---

## Raglan / Marker Logic

When instructions include marker placement:

```
place markers for raglan
```

The app should:

* Detect upcoming stitch distribution.
* Validate that all section counts sum to total stitches.
* Flag mismatches immediately.

---

## Cross-Row Consistency Checks

Detect issues such as:

* Row N ends with 50 sts.
* Row N+1 instructions assume 48 sts.

Output:

```
ERROR: Row 9 starts with incompatible stitch count.
```

---

## Repetition Math Validation

Example:

```
*k2, p2* repeat 10 times
```

Validation:

* One repeat consumes 4 stitches.
* Total consumed = 40 stitches.
* Must match available stitches.

---

## Multi-Size Validation Engine

All checks run per size.

Recommended UX:

* Size toggle (XS / S / M / L / XL / etc.)
* Rendered single-size view for debugging.

Example materialized view:

```
Selected size: M
CO 61 sts
Row 1 ...
Row 2 ...
```

---

## Grammar and Terminology Checks

AI-assisted checks:

* Grammar and typos
* US vs UK knitting terms
* Inconsistent abbreviations
* Punctuation and bracket balance

Examples:

* "knt" -> possible typo for "knit"
* mixed "purl" and "p" notation inconsistently

---

## Format Validation (Professional Tech Editing)

Check for presence and structure of:

* Materials
* Gauge
* Finished measurements
* Abbreviations
* Notes
* Pattern instructions

Warnings only (non-blocking).

---

## Reporting

Generate a structured report:

* Stitch count errors
* Repeat mismatches
* Logic inconsistencies
* Grammar issues
* Formatting warnings

Example summary:

```
14 stitch count errors
3 repetition mismatches
6 grammar issues
2 terminology inconsistencies
```

---

## Architecture (Suggested)

### Deterministic Engine

* Parser (Python)
* Stitch dictionary
* Row simulation engine
* Math validator

### AI Layer

* Grammar review
* Formatting suggestions
* Human-readable explanations

Rule: stitch math must remain deterministic (non-AI).

---

## Data Model (Conceptual)

```
Pattern
  sizes[]
  sections[]

Section
  rows[]

Row
  operations[]
  expected_sts

Operation
  type
  count_effect
  repeat_logic
```

---

## MVP Scope

Must-have:

* Upload Word/PDF
* Extract rows
* Parse multi-size cast-on lines
* Validate increases/decreases
* Detect stitch count mismatches
* Produce error report

Nice-to-have (v2):

* Raglan smart validation
* Lace pattern logic warnings
* Auto-rewrite suggestions
* Export corrected pattern

---

## One-Line Product Positioning

> Grammarly for knitting patterns — with real stitch math.

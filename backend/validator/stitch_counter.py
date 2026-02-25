from __future__ import annotations
from models.pattern import Pattern, Row, RepeatBlock, OperationType
from parser.size_parser import extract_all_stitch_assertions


def _calculate_repeat_block(
    block: RepeatBlock,
    available_sts: int,
) -> tuple[int, str | None]:
    """
    Returns (net stitch change, error_message_or_None).
    """
    consumed_per = block.stitches_consumed_per_repeat()
    net_per = block.net_stitches_per_repeat()

    if consumed_per == 0:
        return 0, None

    if block.repeat_count is not None:
        total_consumed = consumed_per * block.repeat_count
        if total_consumed > available_sts:
            return 0, (
                f"Repeat block consumes {consumed_per} sts x {block.repeat_count} = "
                f"{total_consumed} sts, but only {available_sts} available"
            )
        return net_per * block.repeat_count, None

    if block.until_sts_remain is not None:
        workable = available_sts - block.until_sts_remain
        if workable < 0:
            return 0, (
                f"'Until {block.until_sts_remain} sts remain' but only {available_sts} available"
            )
        if consumed_per == 0:
            return 0, "Repeat block consumes 0 stitches — infinite loop"

        repeats = workable // consumed_per
        if repeats == 0:
            return 0, None
        leftover = workable - (repeats * consumed_per)
        if leftover != 0:
            return (
                net_per * repeats,
                f"Repeat block does not divide evenly: {workable} workable sts / "
                f"{consumed_per} per repeat = {repeats} repeats with {leftover} leftover",
            )
        return net_per * repeats, None

    if block.repeat_to_end:
        if consumed_per == 0:
            return 0, "Repeat-to-end block consumes 0 stitches — infinite loop"
        repeats = available_sts // consumed_per
        leftover = available_sts % consumed_per
        if leftover != 0:
            return (
                net_per * repeats,
                f"Repeat-to-end does not divide evenly: {available_sts} sts / "
                f"{consumed_per} per repeat = {repeats} repeats with {leftover} leftover",
            )
        return net_per * repeats, None

    return net_per, None


def calculate_row_stitches(
    row: Row,
    starting_sts: int,
    size: str,
) -> tuple[int, list[str], list[str]]:
    """
    Calculate the ending stitch count for a row given the starting count.
    Returns (ending_count, errors, warnings).
    """
    errors: list[str] = []
    warnings: list[str] = []

    if row.is_repeat_ref:
        return starting_sts, errors, warnings

    if row.cast_on_extra is not None:
        return starting_sts + row.cast_on_extra, errors, warnings

    if any(op.op_type == OperationType.WORK_EVEN for op in row.operations):
        return starting_sts, errors, warnings

    net_change = 0
    sts_accounted = 0

    for op in row.operations:
        net_change += op.total_effect
        sts_accounted += op.stitches_consumed * op.count

    remaining_for_repeats = starting_sts - sts_accounted

    for block in row.repeat_blocks:
        block_change, block_error = _calculate_repeat_block(block, remaining_for_repeats)
        net_change += block_change
        consumed_this_block = block.stitches_consumed_per_repeat()
        if block.repeat_count is not None:
            remaining_for_repeats -= consumed_this_block * block.repeat_count
        elif block.repeat_to_end:
            if consumed_this_block > 0:
                repeats = remaining_for_repeats // consumed_this_block
                remaining_for_repeats -= consumed_this_block * repeats
        elif block.until_sts_remain is not None:
            remaining_for_repeats = block.until_sts_remain

        if block_error:
            if "does not divide evenly" in block_error or "leftover" in block_error:
                warnings.append(block_error)
            else:
                errors.append(block_error)

    ending = starting_sts + net_change

    # Cast-on row (Row 0) defines the starting count; don't report mismatch there
    if row.number == 0:
        if row.expected_sts and size in row.expected_sts:
            ending = row.expected_sts[size]
        return max(ending, 0), errors, warnings

    if row.expected_sts and size in row.expected_sts:
        expected = row.expected_sts[size]
        # Skip false positives when "expected" is clearly stale:
        # 1) Expected equals starting count but this row has inc/dec → expected is pre-row count.
        # 2) This row has no inc/dec but expected < ending → expected is from before a previous increase.
        if expected == starting_sts and net_change != 0:
            pass  # skip
        elif net_change == 0 and expected < ending:
            pass  # skip: expected is likely pre–increase-round count
        elif ending != expected:
            if net_change > 0:
                errors.append(
                    f"Stitch count mismatch: calculated {ending} sts (includes +{net_change} from increases in this row), pattern states {expected} sts — pattern may need updating."
                )
            elif net_change < 0:
                errors.append(
                    f"Stitch count mismatch: calculated {ending} sts (includes {net_change} from decreases in this row), pattern states {expected} sts"
                )
            else:
                errors.append(
                    f"Stitch count mismatch: calculated {ending} sts, pattern states {expected} sts"
                )

    return max(ending, 0), errors, warnings


def validate_pattern(pattern: Pattern) -> Pattern:
    """Run stitch-count validation across all rows and sizes."""
    if not pattern.sizes:
        pattern.sizes = ["Size1"]
    if not pattern.cast_on_counts:
        pattern.cast_on_counts = {s: 0 for s in pattern.sizes}

    for size in pattern.sizes:
        current_sts = pattern.cast_on_counts.get(size, 0)

        for section in pattern.sections:
            for row in section.rows:
                ending, row_errors, row_warnings = calculate_row_stitches(
                    row, current_sts, size
                )

                if row.calculated_sts is None:
                    row.calculated_sts = {}
                row.calculated_sts[size] = ending
                # Row 0 (cast-on): use expected_sts as authority so next row has correct starting count
                if row.number == 0 and row.expected_sts and size in row.expected_sts:
                    row.calculated_sts[size] = row.expected_sts[size]
                    current_sts = row.expected_sts[size]
                    continue

                for err in row_errors:
                    row_label = f"Row {row.number}" if row.number is not None else "Instruction"
                    pattern.errors.append({
                        "type": "stitch_count",
                        "size": size,
                        "row": row.number,
                        "row_label": row_label,
                        "message": err,
                        "raw_text": row.raw_text,
                    })
                    row.errors.append(f"[{size}] {err}")

                for warn in row_warnings:
                    row_label = f"Row {row.number}" if row.number is not None else "Instruction"
                    pattern.warnings.append({
                        "type": "stitch_count_warning",
                        "size": size,
                        "row": row.number,
                        "row_label": row_label,
                        "message": warn,
                        "raw_text": row.raw_text,
                    })
                    row.warnings.append(f"[{size}] {warn}")

                current_sts = ending

    _check_cross_row_consistency(pattern)
    _check_document_stitch_assertions(pattern)
    return pattern


def _check_document_stitch_assertions(pattern: Pattern) -> None:
    """
    Check every stitch-count assertion in the full document (not just Row N: lines)
    against the computed count at that line. Reports mismatches.
    """
    if not pattern.sizes:
        return
    # Build (line_number, row, calculated_sts) in document order for assertion checks
    row_line_sts: list[tuple[int, Row, dict[str, int]]] = []
    for section in pattern.sections:
        for row in section.rows:
            if row.line_number is not None and row.calculated_sts:
                row_line_sts.append((row.line_number, row, dict(row.calculated_sts)))
    row_line_sts.sort(key=lambda x: x[0])

    assertions = extract_all_stitch_assertions(pattern.raw_text)
    for a in assertions:
        line_num = a["line"]
        counts = a["counts"]
        raw_snippet = a["raw_text"]
        # Which row's count applies? Last row that starts at or before this line
        applied_row: Row | None = None
        applied_sts: dict[str, int] | None = None
        for ln, row, sts in row_line_sts:
            if ln <= line_num:
                applied_row = row
                applied_sts = sts
            else:
                break
        if applied_sts is None:
            continue
        # Skip if this assertion is on the same line as a row (already validated as row expected_sts)
        if applied_row and applied_row.line_number == line_num:
            continue
        # Map assertion counts to sizes
        if len(counts) == len(pattern.sizes):
            stated = {pattern.sizes[i]: counts[i] for i in range(len(pattern.sizes))}
        elif len(counts) == 1:
            stated = {s: counts[0] for s in pattern.sizes}
        else:
            continue
        for size in pattern.sizes:
            calc = applied_sts.get(size)
            exp = stated.get(size)
            if calc is not None and exp is not None and calc != exp:
                row_label = f"Line {line_num}"
                if applied_row and applied_row.number is not None:
                    row_label = f"Row {applied_row.number} (pattern states count at line {line_num})"
                pattern.errors.append({
                    "type": "stitch_count",
                    "size": size,
                    "row": applied_row.number if applied_row else None,
                    "row_label": row_label,
                    "message": f"Stated count in pattern ({raw_snippet}) is {exp} sts but computed count at this point is {calc} sts",
                    "raw_text": raw_snippet,
                    "line": line_num,
                })


def _check_cross_row_consistency(pattern: Pattern) -> None:
    """Detect cross-row stitch count jumps that indicate errors."""
    for size in pattern.sizes:
        prev_row: Row | None = None
        for section in pattern.sections:
            for row in section.rows:
                if row.is_repeat_ref:
                    continue
                if prev_row is not None and row.calculated_sts and prev_row.calculated_sts:
                    prev_end = prev_row.calculated_sts.get(size, 0)
                    curr_end = row.calculated_sts.get(size, 0)
                    if row.expected_sts and size in row.expected_sts:
                        pass
                    elif (
                        not row.operations
                        and not row.repeat_blocks
                        and curr_end != prev_end
                    ):
                        pattern.warnings.append({
                            "type": "consistency",
                            "size": size,
                            "row": row.number,
                            "message": (
                                f"Row {row.number} has no parsed operations but stitch count "
                                f"changed from {prev_end} to {curr_end}"
                            ),
                            "raw_text": row.raw_text,
                        })
                prev_row = row

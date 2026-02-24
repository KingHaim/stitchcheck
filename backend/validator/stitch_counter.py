from __future__ import annotations
from models.pattern import Pattern, Row, RepeatBlock, OperationType


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

    if row.expected_sts and size in row.expected_sts:
        expected = row.expected_sts[size]
        if ending != expected:
            errors.append(
                f"Stitch count mismatch: calculated {ending} sts, expected {expected} sts"
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
    return pattern


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

"""
Merges LLM-parsed structured data into the deterministic pattern model.

The LLM handles natural-language understanding (the messy part),
then we feed its structured output into the deterministic stitch math engine.
"""
from __future__ import annotations
import logging
from typing import Optional

from models.pattern import (
    Pattern, Section, Row, Operation, RepeatBlock,
    OperationType, STITCH_EFFECTS,
)
from parser.size_parser import map_sizes_to_counts
from services.llm_service import llm_parse_pattern

logger = logging.getLogger(__name__)

_OP_MAP = {
    "k": OperationType.KNIT,
    "p": OperationType.PURL,
    "sl": OperationType.SLIP,
    "k2tog": OperationType.K2TOG,
    "ssk": OperationType.SSK,
    "p2tog": OperationType.P2TOG,
    "ssp": OperationType.SSP,
    "sk2p": OperationType.SK2P,
    "s2kp": OperationType.S2KP,
    "k3tog": OperationType.K3TOG,
    "p3tog": OperationType.P3TOG,
    "yo": OperationType.YO,
    "m1": OperationType.M1,
    "m1l": OperationType.M1L,
    "m1r": OperationType.M1R,
    "kfb": OperationType.KFB,
    "pfb": OperationType.KFB,
    "bo": OperationType.BIND_OFF,
    "co": OperationType.CAST_ON,
}


def _stitches_consumed(op_str: str) -> int:
    s = op_str.lower()
    if s in ("yo", "m1", "m1l", "m1r", "m1p"):
        return 0
    if s in ("k2tog", "ssk", "p2tog", "ssp"):
        return 2
    if s in ("sk2p", "s2kp", "k3tog", "p3tog", "cdd"):
        return 3
    if s in ("kfb", "pfb"):
        return 1
    return 1


def _build_operation(op_dict: dict) -> Optional[Operation]:
    op_str = op_dict.get("op", "").lower().strip()
    count = op_dict.get("count", 1)
    if not op_str:
        return None
    if isinstance(count, str):
        try:
            count = int(count)
        except ValueError:
            count = 1

    op_type = _OP_MAP.get(op_str, OperationType.UNKNOWN)
    effect = STITCH_EFFECTS.get(op_str, 0)
    consumed = _stitches_consumed(op_str)

    return Operation(
        raw=f"{op_str}{count}" if count > 1 else op_str,
        op_type=op_type,
        count=count,
        count_effect=effect,
        stitches_consumed=consumed,
    )


def _build_repeat_block(block_dict: dict) -> Optional[RepeatBlock]:
    ops = []
    for op_dict in block_dict.get("operations", []):
        op = _build_operation(op_dict)
        if op:
            ops.append(op)
    if not ops:
        return None

    return RepeatBlock(
        operations=ops,
        repeat_to_end=block_dict.get("repeat_to_end", False),
        repeat_count=block_dict.get("repeat_count"),
        until_sts_remain=block_dict.get("until_sts_remain"),
        raw=str(block_dict),
    )


def enhance_pattern_with_llm(pattern: Pattern) -> Pattern:
    """
    Call the LLM to parse the raw pattern text, then merge the structured
    output into the existing Pattern object. Falls back gracefully if
    the LLM fails or returns unexpected data.
    """
    llm_result = llm_parse_pattern(pattern.raw_text)
    if not llm_result:
        logger.info("LLM parsing unavailable, using deterministic parser only")
        return pattern

    if llm_result.get("sizes") and not pattern.sizes:
        pattern.sizes = llm_result["sizes"]

    if llm_result.get("cast_on") and not pattern.cast_on_counts:
        counts = llm_result["cast_on"]
        if isinstance(counts, list):
            pattern.cast_on_counts = map_sizes_to_counts(pattern.sizes, counts)

    llm_rows = llm_result.get("rows", [])
    if not isinstance(llm_rows, list):
        llm_rows = []

    llm_row_map: dict[int, dict] = {}
    for lr in llm_rows:
        if isinstance(lr, dict) and lr.get("number") is not None:
            try:
                llm_row_map[int(lr["number"])] = lr
            except (ValueError, TypeError):
                pass

    for section in pattern.sections:
        for row in section.rows:
            if row.number is None or row.number not in llm_row_map:
                continue

            lr = llm_row_map[row.number]

            has_det_ops = bool(row.operations) or bool(row.repeat_blocks)
            has_llm_ops = bool(lr.get("operations")) or bool(lr.get("repeat_blocks"))

            if lr.get("is_work_even") and not any(
                op.op_type == OperationType.WORK_EVEN for op in row.operations
            ):
                row.operations = [Operation(
                    raw="work even",
                    op_type=OperationType.WORK_EVEN,
                    count=1,
                    count_effect=0,
                    stitches_consumed=0,
                )]
                row.repeat_blocks = []
                continue

            if not has_det_ops and has_llm_ops:
                new_ops = []
                for op_dict in lr.get("operations", []):
                    op = _build_operation(op_dict)
                    if op:
                        new_ops.append(op)
                row.operations = new_ops

                new_blocks = []
                for block_dict in lr.get("repeat_blocks", []):
                    block = _build_repeat_block(block_dict)
                    if block:
                        new_blocks.append(block)
                row.repeat_blocks = new_blocks

            if lr.get("expected_sts") and not row.expected_sts:
                sts_list = lr["expected_sts"]
                if isinstance(sts_list, list) and sts_list:
                    row.expected_sts = map_sizes_to_counts(
                        pattern.sizes, [int(s) for s in sts_list if str(s).isdigit()]
                    )

            if lr.get("side") and not row.side:
                row.side = lr["side"]

    llm_sections = llm_result.get("sections", [])
    if isinstance(llm_sections, list):
        existing_names = {s.name.lower() for s in pattern.sections}
        for sec_name in llm_sections:
            if isinstance(sec_name, str) and sec_name.lower() not in existing_names:
                pattern.warnings.append({
                    "type": "llm_insight",
                    "message": f"LLM detected section: {sec_name}",
                })

    # Merge between_steps: insert virtual rows after the row they refer to (full-pattern context)
    between_steps = llm_result.get("between_steps", [])
    if not isinstance(between_steps, list):
        between_steps = []
    steps_by_after: dict[int, list[dict]] = {}
    for step in between_steps:
        if not isinstance(step, dict):
            continue
        after = step.get("after_row")
        if after is None:
            continue
        try:
            after = int(after)
        except (TypeError, ValueError):
            continue
        cast_extra = step.get("cast_on_extra")
        if cast_extra is not None:
            try:
                cast_extra = int(cast_extra)
            except (TypeError, ValueError):
                cast_extra = None
        if cast_extra is not None and cast_extra > 0:
            steps_by_after.setdefault(after, []).append({
                "cast_on_extra": cast_extra,
                "description": step.get("description", ""),
            })

    for section in pattern.sections:
        new_rows: list[Row] = []
        for row in section.rows:
            new_rows.append(row)
            row_num = row.number
            if row_num is not None and row_num in steps_by_after:
                for step in steps_by_after[row_num]:
                    extra_row = Row(
                        raw_text=step.get("description", "") or f"Cast on {step['cast_on_extra']} more sts",
                        cast_on_extra=step["cast_on_extra"],
                    )
                    new_rows.append(extra_row)
        section.rows = new_rows

    return pattern

from __future__ import annotations
import re
from models.pattern import (
    Operation, OperationType, RepeatBlock,
    STITCH_EFFECTS,
)

STITCH_ALIASES: dict[str, str] = {
    "knit": "k",
    "purl": "p",
    "slip": "sl",
    "slip 1": "sl1",
    "slip marker": "sm",
    "place marker": "pm",
    "k2 tog": "k2tog",
    "k 2 tog": "k2tog",
    "p2 tog": "p2tog",
    "p 2 tog": "p2tog",
    "k3 tog": "k3tog",
    "p3 tog": "p3tog",
    "kfab": "kfb",
    "m 1 l": "m1l",
    "m 1 r": "m1r",
    "m 1": "m1",
    "make 1 left": "m1l",
    "make 1 right": "m1r",
    "yarn over": "yo",
    "bind off": "bo",
    "cast on": "co",
}

_STITCH_PATTERN = re.compile(
    r"""
    (?P<op>
        k3tog|p3tog|k2tog|p2tog|ssk|ssp|sk2p|s2kp|cdd|
        kfb|pfb|m1l|m1r|m1p|m1|yo|
        sl1|sl|wyif|wyib|sm|pm|
        bo|co|
        k|p
    )
    (?P<count>\d+)?
    """,
    re.IGNORECASE | re.VERBOSE,
)


def _op_type_from_str(s: str) -> OperationType:
    s_lower = s.lower()
    mapping = {
        "k": OperationType.KNIT,
        "p": OperationType.PURL,
        "sl": OperationType.SLIP,
        "sl1": OperationType.SLIP,
        "sm": OperationType.SLIP,
        "pm": OperationType.SLIP,
        "k2tog": OperationType.K2TOG,
        "ssk": OperationType.SSK,
        "p2tog": OperationType.P2TOG,
        "ssp": OperationType.SSP,
        "sk2p": OperationType.SK2P,
        "s2kp": OperationType.S2KP,
        "k3tog": OperationType.K3TOG,
        "p3tog": OperationType.P3TOG,
        "cdd": OperationType.SK2P,
        "yo": OperationType.YO,
        "m1": OperationType.M1,
        "m1l": OperationType.M1L,
        "m1r": OperationType.M1R,
        "m1p": OperationType.M1,
        "kfb": OperationType.KFB,
        "pfb": OperationType.KFB,
        "bo": OperationType.BIND_OFF,
        "co": OperationType.CAST_ON,
    }
    return mapping.get(s_lower, OperationType.UNKNOWN)


def _stitches_consumed_per_one(op_str: str) -> int:
    """How many stitches from the needle does one instance of this op consume."""
    s = op_str.lower()
    if s in ("yo", "m1", "m1l", "m1r", "m1p", "sm", "pm"):
        return 0
    if s in ("k2tog", "ssk", "p2tog", "ssp"):
        return 2
    if s in ("sk2p", "s2kp", "k3tog", "p3tog", "cdd"):
        return 3
    if s in ("kfb", "pfb"):
        return 1
    return 1


def parse_stitch(token: str) -> Operation | None:
    token = token.strip().rstrip(",").strip()
    if not token:
        return None

    for alias, canonical in STITCH_ALIASES.items():
        if token.lower() == alias:
            token = canonical

    m = _STITCH_PATTERN.match(token.strip())
    if not m:
        return None

    op_str = m.group("op").lower()
    count = int(m.group("count")) if m.group("count") else 1

    if op_str in ("k", "p", "sl") and m.group("count"):
        count = int(m.group("count"))
    elif op_str in ("bo", "co") and m.group("count"):
        count = int(m.group("count"))

    effect = STITCH_EFFECTS.get(op_str, 0)
    consumed = _stitches_consumed_per_one(op_str)

    return Operation(
        raw=token,
        op_type=_op_type_from_str(op_str),
        count=count,
        count_effect=effect,
        stitches_consumed=consumed,
    )


_REPEAT_BLOCK_PATTERN = re.compile(
    r"\*([^*]+)\*\s*(?:,?\s*repeat\s+)?(?:(?:(\d+)\s*times)|(?:to\s+end)|(?:across)|(?:until\s+(\d+)\s+sts?\s+remain))?",
    re.IGNORECASE,
)

_REPEAT_FROM_PATTERN = re.compile(
    r"repeat\s+from\s+\*\s*(?:to\s+end|across|(\d+)\s+times|until\s+(\d+)\s+sts?\s+remain)?",
    re.IGNORECASE,
)


def parse_repeat_block(text: str) -> RepeatBlock | None:
    m = _REPEAT_BLOCK_PATTERN.search(text)
    if not m:
        return None

    inner = m.group(1).strip()
    ops = parse_instruction_segment(inner)
    if not ops:
        return None

    block = RepeatBlock(operations=ops, raw=text)

    if m.group(2):
        block.repeat_count = int(m.group(2))
    elif m.group(3):
        block.until_sts_remain = int(m.group(3))
    else:
        block.repeat_to_end = True

    return block


def parse_instruction_segment(text: str) -> list[Operation]:
    tokens = re.split(r",\s*|\s+", text.strip())
    ops: list[Operation] = []
    i = 0
    while i < len(tokens):
        token = tokens[i].strip().rstrip(",")
        if not token:
            i += 1
            continue
        op = parse_stitch(token)
        if op:
            ops.append(op)
            # If next token is a bare number, merge as count for k/p (e.g. "Knit 4" or multi-size "4, 4, 4, 6, 6, 6")
            if ops and op.op_type in (OperationType.KNIT, OperationType.PURL) and i + 1 < len(tokens):
                next_tok = tokens[i + 1].strip().rstrip(",")
                if next_tok.isdigit():
                    n = int(next_tok)
                    if n >= 1:
                        ops[-1].count = n
                        ops[-1].raw = f"{op.raw.rstrip('0123456789')}{n}".strip() or op.raw
                    i += 1
        else:
            # "slip marker" / "place marker": if last op was sl/slip, treat "marker" as sm
            if token.lower() == "marker" and ops and ops[-1].raw.lower() in ("sl", "slip"):
                ops[-1].raw = "sm"
                ops[-1].count_effect = STITCH_EFFECTS.get("sm", 0)
                ops[-1].stitches_consumed = _stitches_consumed_per_one("sm")
            # skip filler words and "st" after numbers
        i += 1
    return ops


def parse_row_instructions(text: str) -> tuple[list[Operation], list[RepeatBlock]]:
    text = text.strip()

    work_even = re.search(r"work\s+even", text, re.IGNORECASE)
    if work_even:
        return [Operation(
            raw="work even",
            op_type=OperationType.WORK_EVEN,
            count=1,
            count_effect=0,
            stitches_consumed=0,
        )], []

    repeat_blocks: list[RepeatBlock] = []
    remaining = text

    for m in _REPEAT_BLOCK_PATTERN.finditer(text):
        block = parse_repeat_block(m.group(0))
        if block:
            repeat_blocks.append(block)
            remaining = remaining.replace(m.group(0), " __REPEAT__ ", 1)

    parts = remaining.split("__REPEAT__")
    flat_ops: list[Operation] = []
    for part in parts:
        flat_ops.extend(parse_instruction_segment(part))

    return flat_ops, repeat_blocks

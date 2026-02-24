from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class OperationType(str, Enum):
    KNIT = "k"
    PURL = "p"
    SLIP = "sl"
    K2TOG = "k2tog"
    SSK = "ssk"
    P2TOG = "p2tog"
    SSP = "ssp"
    SK2P = "sk2p"
    S2KP = "s2kp"
    K3TOG = "k3tog"
    P3TOG = "p3tog"
    YO = "yo"
    M1L = "m1l"
    M1R = "m1r"
    M1 = "m1"
    KFB = "kfb"
    PFB = "pfb"
    WORK_EVEN = "work_even"
    BIND_OFF = "bo"
    CAST_ON = "co"
    REPEAT_BLOCK = "repeat_block"
    UNKNOWN = "unknown"


STITCH_EFFECTS: dict[str, int] = {
    "k": 0,
    "p": 0,
    "sl": 0,
    "sl1": 0,
    "wyif": 0,
    "wyib": 0,
    "k2tog": -1,
    "ssk": -1,
    "p2tog": -1,
    "ssp": -1,
    "sk2p": -2,
    "s2kp": -2,
    "k3tog": -2,
    "p3tog": -2,
    "cdd": -2,
    "yo": 1,
    "m1": 1,
    "m1l": 1,
    "m1r": 1,
    "m1p": 1,
    "kfb": 1,
    "pfb": 1,
    "kll": 1,
    "krl": 1,
    "work_even": 0,
    "bo": -1,
}


@dataclass
class Operation:
    raw: str
    op_type: OperationType
    count: int = 1
    count_effect: int = 0
    stitches_consumed: int = 0

    @property
    def total_effect(self) -> int:
        return self.count_effect * self.count

    @property
    def total_consumed(self) -> int:
        return self.stitches_consumed * self.count


@dataclass
class RepeatBlock:
    operations: list[Operation] = field(default_factory=list)
    repeat_count: Optional[int] = None
    repeat_to_end: bool = False
    until_sts_remain: Optional[int] = None
    raw: str = ""

    @property
    def single_pass_effect(self) -> int:
        return sum(op.total_effect for op in self.operations)

    @property
    def single_pass_consumed(self) -> int:
        return sum(
            max(op.stitches_consumed, abs(min(0, op.count_effect))) * op.count + max(0, op.count_effect) * 0
            for op in self.operations
        )

    def net_stitches_per_repeat(self) -> int:
        return sum(op.total_effect for op in self.operations)

    def stitches_consumed_per_repeat(self) -> int:
        consumed = 0
        for op in self.operations:
            if op.op_type in (OperationType.YO, OperationType.M1L, OperationType.M1R, OperationType.M1):
                consumed += 0
            elif op.op_type == OperationType.KFB:
                consumed += 1 * op.count
            elif op.op_type in (OperationType.K2TOG, OperationType.SSK, OperationType.P2TOG, OperationType.SSP):
                consumed += 2 * op.count
            elif op.op_type in (OperationType.SK2P, OperationType.S2KP, OperationType.K3TOG, OperationType.P3TOG):
                consumed += 3 * op.count
            else:
                consumed += 1 * op.count
        return consumed


@dataclass
class Row:
    number: Optional[int] = None
    raw_text: str = ""
    side: Optional[str] = None  # RS or WS
    is_round: bool = False
    operations: list[Operation] = field(default_factory=list)
    repeat_blocks: list[RepeatBlock] = field(default_factory=list)
    expected_sts: Optional[dict[str, int]] = None  # size -> count
    calculated_sts: Optional[dict[str, int]] = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    is_repeat_ref: bool = False  # "work as established"
    segment_label: Optional[str] = None


@dataclass
class Section:
    name: str = ""
    rows: list[Row] = field(default_factory=list)
    notes: str = ""
    is_repeat_segment: bool = False


@dataclass
class Pattern:
    raw_text: str = ""
    sizes: list[str] = field(default_factory=list)
    cast_on_counts: dict[str, int] = field(default_factory=dict)
    sections: list[Section] = field(default_factory=list)
    materials: Optional[str] = None
    gauge: Optional[str] = None
    finished_measurements: Optional[str] = None
    abbreviations: Optional[str] = None
    notes: Optional[str] = None
    errors: list[dict] = field(default_factory=list)
    warnings: list[dict] = field(default_factory=list)
    grammar_issues: list[dict] = field(default_factory=list)
    format_issues: list[dict] = field(default_factory=list)

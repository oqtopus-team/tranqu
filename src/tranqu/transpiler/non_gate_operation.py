"""The single definition of which operations are not counted as gates.

Gate counts reported in ``TranspileResult.stats`` must mean the same thing no
matter which transpiler produced them. Each entry of :data:`COUNTERPARTS` names
one kind of non-gate operation together with how every supported library
represents it, so the decision of what counts as a gate is made here and only
here.

Adding a kind of non-gate operation means adding an entry, which forces its
counterpart in every library to be stated -- including stating that a library
has none.
"""

from enum import Enum, auto, unique
from typing import NamedTuple

from pytket import OpType  # type: ignore[attr-defined]
from qiskit.circuit.controlflow import (  # type: ignore[import-untyped]
    CONTROL_FLOW_OP_NAMES,
)


@unique
class NonGateOperation(Enum):
    """A kind of operation that is not counted as a gate."""

    MEASURE = auto()
    RESET = auto()
    BARRIER = auto()
    DELAY = auto()
    INITIALIZE = auto()
    CONTROL_FLOW = auto()


class Counterparts(NamedTuple):
    """How one non-gate operation is represented in each supported library.

    An empty collection means the library has no counterpart for it.
    """

    qiskit_names: frozenset[str]
    tket_op_types: frozenset[OpType]


COUNTERPARTS: dict[NonGateOperation, Counterparts] = {
    NonGateOperation.MEASURE: Counterparts(
        qiskit_names=frozenset({"measure"}),
        tket_op_types=frozenset({OpType.Measure}),
    ),
    NonGateOperation.RESET: Counterparts(
        qiskit_names=frozenset({"reset"}),
        tket_op_types=frozenset({OpType.Reset}),
    ),
    NonGateOperation.BARRIER: Counterparts(
        qiskit_names=frozenset({"barrier"}),
        tket_op_types=frozenset({OpType.Barrier}),
    ),
    NonGateOperation.DELAY: Counterparts(
        qiskit_names=frozenset({"delay"}),
        # tket has no delay operation.
        tket_op_types=frozenset(),
    ),
    NonGateOperation.INITIALIZE: Counterparts(
        qiskit_names=frozenset({"initialize"}),
        # tket has no initialize operation.
        tket_op_types=frozenset(),
    ),
    NonGateOperation.CONTROL_FLOW: Counterparts(
        # 'if_else', 'for_loop', 'while_loop', 'switch_case'
        qiskit_names=frozenset(CONTROL_FLOW_OP_NAMES),
        tket_op_types=frozenset({OpType.Conditional}),
    ),
}

QISKIT_NON_GATE_OPERATION_NAMES: frozenset[str] = frozenset(
    name for counterparts in COUNTERPARTS.values() for name in counterparts.qiskit_names
)

TKET_NON_GATE_OP_TYPES: frozenset[OpType] = frozenset(
    op_type
    for counterparts in COUNTERPARTS.values()
    for op_type in counterparts.tket_op_types
)

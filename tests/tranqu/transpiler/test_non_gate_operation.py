from pytket import OpType  # type: ignore[attr-defined]

from tranqu.transpiler.non_gate_operation import (
    COUNTERPARTS,
    QISKIT_NON_GATE_OPERATION_NAMES,
    TKET_NON_GATE_OP_TYPES,
    NonGateOperation,
)


def test_every_non_gate_operation_states_its_counterparts() -> None:
    # Adding a kind of non-gate operation must force its counterpart in every
    # library to be stated, so that the two stats extractors cannot drift apart.
    assert set(COUNTERPARTS) == set(NonGateOperation)


def test_measurement_is_not_a_gate_in_either_library() -> None:
    assert "measure" in QISKIT_NON_GATE_OPERATION_NAMES
    assert OpType.Measure in TKET_NON_GATE_OP_TYPES

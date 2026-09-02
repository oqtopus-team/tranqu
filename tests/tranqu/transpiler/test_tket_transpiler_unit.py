from pytket import Circuit  # type: ignore[attr-defined]

from tranqu.transpiler.tket_transpiler import TketTranspiler


def _apply_minimal_pass(circuit: Circuit, optimization_level: int) -> Circuit:
    return TketTranspiler._apply_minimal_pass(circuit, optimization_level)  # ruff: ignore[private-member-access]


def test_apply_minimal_pass_returns_original_circuit_at_level_zero() -> None:
    circuit = Circuit(1)

    result = _apply_minimal_pass(circuit, 0)

    assert result is circuit


def test_apply_minimal_pass_level_two_reduces_redundant_gates() -> None:
    circuit = Circuit(1)
    circuit.X(0)
    circuit.X(0)

    result = _apply_minimal_pass(circuit, 2)

    assert result is circuit
    assert result.n_gates == 0
    assert result.depth() == 0

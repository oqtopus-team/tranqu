import pytest
from qiskit import QuantumCircuit  # type: ignore[import-untyped]

from tranqu import Tranqu


@pytest.fixture
def tranqu() -> Tranqu:
    return Tranqu()


def _circuit_with_measurements() -> QuantumCircuit:
    circuit = QuantumCircuit(2, 2)
    circuit.h(0)
    circuit.cx(0, 1)
    circuit.measure(0, 0)
    circuit.measure(1, 1)
    return circuit


def _stats_before(tranqu: Tranqu, transpiler_lib: str) -> dict[str, int]:
    result = tranqu.transpile(
        _circuit_with_measurements(),
        program_lib="qiskit",
        transpiler_lib=transpiler_lib,
        transpiler_options={"optimization_level": 0},
    )
    return result.to_dict()["stats"]["before"]


def test_stats_before_is_independent_of_transpiler_lib(tranqu: Tranqu) -> None:
    # stats.before describes the circuit the caller passed in. The transpiler
    # has not touched it, so the reported statistics must not depend on which
    # transpiler library was selected.
    assert _stats_before(tranqu, "qiskit") == _stats_before(tranqu, "tket")

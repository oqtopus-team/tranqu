from collections.abc import Sequence
from typing import Any, NoReturn

import pytest
from pytket import Circuit  # type: ignore[attr-defined]
from pytket.architecture import Architecture  # type: ignore[attr-defined]
from pytket.backends import Backend  # type: ignore[attr-defined]
from pytket.backends.backend import (  # type: ignore[attr-defined]
    BackendInfo,
    CircuitStatus,
    ResultHandle,
)
from pytket.circuit import OpType  # type: ignore[attr-defined]

from tranqu import Tranqu
from tranqu.program_converter import (
    Openqasm3ToTketProgramConverter,
)
from tranqu.transpiler import TketTranspiler


class TestBackend(Backend):
    _ERROR_MESSAGE = "This backend is for testing only"

    def __init__(self) -> None:
        self._architecture = Architecture([(0, 1)])
        self._backend_info = BackendInfo(
            name="test_device",
            device_name="test_device",
            architecture=self._architecture,
            version="1.0.0",
            gate_set={OpType.CX},
        )

    @property
    def backend_info(self) -> BackendInfo:
        return self._backend_info

    @property
    def required_predicates(self) -> NoReturn:
        raise NotImplementedError(self._ERROR_MESSAGE)

    def rebase_pass(self) -> NoReturn:
        raise NotImplementedError(self._ERROR_MESSAGE)

    def default_compilation_pass(
        self, optimisation_level: int | None = None
    ) -> NoReturn:
        raise NotImplementedError(self._ERROR_MESSAGE)

    def process_circuits(
        self,
        circuits: Sequence[Circuit],
        n_shots: int | Sequence[int | None] | None = None,
        valid_check: bool = True,  # noqa: FBT001, FBT002
        **kwargs: Any,
    ) -> NoReturn:
        raise NotImplementedError(self._ERROR_MESSAGE)

    def get_result(self, handle: ResultHandle, **kwargs: Any) -> NoReturn:
        raise NotImplementedError(self._ERROR_MESSAGE)

    @property
    def _result_id_type(self) -> tuple[type[str]]:
        return (str,)

    def circuit_status(self, handle: ResultHandle) -> CircuitStatus:
        raise NotImplementedError(self._ERROR_MESSAGE)


@pytest.fixture
def tranqu() -> Tranqu:
    return Tranqu()


def test_tranqu_transpile_returns_qasm3_string(tranqu: Tranqu) -> None:
    """Verify that tranqu.transpile() returns OpenQASM 3.0 string output."""
    qasm = """
        OPENQASM 3.0;
    """
    result = tranqu.transpile(
        program=qasm,
        program_lib="openqasm3",
        transpiler_lib="tket",
    )

    assert isinstance(result.transpiled_program, str)
    assert "OPENQASM 3.0" in result.transpiled_program


def test_tranqu_tracks_statistics_before_transpilation(tranqu: Tranqu) -> None:
    """Verify that statistics before transpilation are correctly tracked."""
    qasm = """
        OPENQASM 3.0;
        include "stdgates.inc";
        qubit[2] q;
        h q[0];
        x q[0];
        cx q[0], q[1];
    """
    result = tranqu.transpile(
        program=qasm,
        program_lib="openqasm3",
        transpiler_lib="tket",
    )

    assert "before" in result.stats
    before_stats = result.stats["before"]

    assert "n_qubits" in before_stats
    assert before_stats["n_qubits"] == 2

    assert "n_gates" in before_stats
    assert before_stats["n_gates"] == 3

    assert "depth" in before_stats
    assert before_stats["depth"] == 3

    assert before_stats["n_gates_1q"] == 2
    assert before_stats["n_gates_2q"] == 1


def test_tranqu_tracks_statistics_after_transpilation(tranqu: Tranqu) -> None:
    """Verify that statistics after transpilation are correctly tracked."""
    qasm = """
        OPENQASM 3.0;
        include "stdgates.inc";
        qubit[2] q;
        h q[0];
        x q[0];
        cx q[0], q[1];
    """
    result = tranqu.transpile(
        program=qasm,
        program_lib="openqasm3",
        transpiler_lib="tket",
    )

    assert "after" in result.stats
    after_stats = result.stats["after"]

    assert "n_gates" in after_stats
    assert isinstance(after_stats["n_gates"], int)

    assert "depth" in after_stats
    assert isinstance(after_stats["depth"], int)

    assert "n_gates_1q" in after_stats
    assert isinstance(after_stats["n_gates_1q"], int)

    assert "n_gates_2q" in after_stats
    assert isinstance(after_stats["n_gates_2q"], int)

    assert result.stats["before"]["n_qubits"] == result.stats["after"]["n_qubits"]
    assert result.stats["before"]["n_gates"] >= result.stats["after"]["n_gates"]
    assert result.stats["before"]["depth"] >= result.stats["after"]["depth"]


def test_tranqu_optimizes_hadamard_identity(tranqu: Tranqu) -> None:
    """Verify that HH = I optimization is performed using tranqu.transpile()."""
    qasm = """
        OPENQASM 3.0;
        include "stdgates.inc";
        qubit[1] q;
        h q[0];
        h q[0];
    """
    result = tranqu.transpile(
        program=qasm,
        program_lib="openqasm3",
        transpiler_lib="tket",
    )

    assert result.stats["after"]["n_gates"] == 0


def test_tranqu_with_basic_optimization(tranqu: Tranqu) -> None:
    """Verify optimization with basic synthesis level using tranqu.transpile()."""
    qasm = """
        OPENQASM 3.0;
        include "stdgates.inc";
        qubit[1] q;
        x q[0];
        x q[0];
    """
    result = tranqu.transpile(
        program=qasm,
        program_lib="openqasm3",
        transpiler_lib="tket",
        transpiler_options={"optimization_level": TketTranspiler.OPT_LEVEL_SYNTHESIS},
    )

    assert result.stats["after"]["n_gates"] == 0


def test_tranqu_respects_device_connectivity(tranqu: Tranqu) -> None:
    """Verify that transpiler respects device connectivity constraints using
    tranqu.transpile()."""
    input_qasm = """
        OPENQASM 3.0;
        include "stdgates.inc";
        qubit[2] q;
        cx q[1], q[0];
    """
    device = TestBackend()

    result = tranqu.transpile(
        program=input_qasm,
        program_lib="openqasm3",
        transpiler_lib="tket",
        transpiler_options={"optimization_level": 2},
        device=device,
        device_lib="tket",
    )

    transpiled_circuit = result.transpiled_program

    assert "cx" in transpiled_circuit, "Expected CX gate in transpiled circuit"

    converter = Openqasm3ToTketProgramConverter()
    tket_circuit = converter.convert(transpiled_circuit)

    commands = tket_circuit.get_commands()
    assert len(commands) == 1, f"Expected exactly 1 gate, but got {len(commands)}"

    cx_commands = [cmd for cmd in commands if cmd.op.type == OpType.CX]
    assert len(cx_commands) == 1, (
        f"Expected exactly 1 CX gate, but got {len(cx_commands)}"
    )

    cx_cmd = cx_commands[0]
    qubit_indices = [q.index[0] for q in cx_cmd.qubits]
    assert qubit_indices == [0, 1], (
        f"Expected CNOT from qubit 0 to 1, but got {qubit_indices}"
    )

    qubit_mapping = result.virtual_physical_mapping["qubit_mapping"]
    assert qubit_mapping == {0: 0, 1: 1}

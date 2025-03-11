from collections.abc import Sequence
from typing import Any, NoReturn

from pytket import Circuit  # type: ignore[attr-defined]
from pytket.architecture import Architecture  # type: ignore[attr-defined]
from pytket.backends import Backend  # type: ignore[attr-defined]
from pytket.backends.backend import (  # type: ignore[attr-defined]
    BackendInfo,
    CircuitStatus,
    ResultHandle,
)
from pytket.circuit import OpType  # type: ignore[attr-defined]
from qiskit_ibm_runtime.fake_provider import (  # type: ignore[import-untyped]
    FakeSantiagoV2,
)

from tranqu import Tranqu
from tranqu.program_converter import (
    Openqasm3ToTketProgramConverter,
)
from tranqu.transpiler import TketTranspiler


def test_tranqu_optimizes_hadamard_identity() -> None:
    """Verify that HH = I optimization is performed using tranqu.transpile()."""
    qasm = """
        OPENQASM 3.0;
        include "stdgates.inc";
        qubit[1] q;
        h q[0];
        h q[0];
    """
    tranqu = Tranqu()

    result = tranqu.transpile(
        program=qasm,
        program_lib="openqasm3",
        transpiler_lib="tket",
    )

    assert isinstance(result.transpiled_program, str)
    assert result.stats["before"]["n_gates"] == 2
    assert result.stats["after"]["n_gates"] == 0


def test_tranqu_with_basic_optimization() -> None:
    """Verify optimization with basic synthesis level using tranqu.transpile()."""
    qasm = """
        OPENQASM 3.0;
        include "stdgates.inc";
        qubit[1] q;
        x q[0];
        x q[0];
    """
    tranqu = Tranqu()

    result = tranqu.transpile(
        program=qasm,
        program_lib="openqasm3",
        transpiler_lib="tket",
        transpiler_options={"optimization_level": TketTranspiler.OPT_LEVEL_SYNTHESIS},
    )

    assert isinstance(result.transpiled_program, str)
    assert result.stats["before"]["n_gates"] == 2
    assert result.stats["after"]["n_gates"] == 0


def test_tranqu_respects_device_connectivity() -> None:
    """Verify that transpiler respects device connectivity constraints using
    tranqu.transpile()."""
    input_qasm = """
        OPENQASM 3.0;
        include "stdgates.inc";
        qubit[2] q;
        cx q[1], q[0];
    """
    # FakeSantiagoV2は0→1方向のCNOTのみをサポート
    device = FakeSantiagoV2()
    tranqu = Tranqu()

    result = tranqu.transpile(
        program=input_qasm,
        program_lib="openqasm3",
        transpiler_lib="tket",
        transpiler_options={"optimization_level": 2},
        device=device,
        device_lib="qiskit",
    )

    transpiled_circuit = result.transpiled_program
    assert isinstance(transpiled_circuit, str)


def test_tket_transpiler_respects_device_connectivity() -> None:
    """Verify that transpiler respects device connectivity constraints."""
    input_qasm = """
        OPENQASM 3.0;
        include "stdgates.inc";
        qubit[2] q;
        cx q[1], q[0];
    """
    transpiler = TketTranspiler("tket")
    converter = Openqasm3ToTketProgramConverter()
    circuit = converter.convert(input_qasm)

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

    device = TestBackend()
    result = transpiler.transpile(
        circuit,
        options={"optimization_level": 2},
        device=device,
    )

    transpiled_circuit = result.transpiled_program
    commands = transpiled_circuit.get_commands()
    assert len(commands) == 1, f"Expected 1 gate, but got {len(commands)}"
    command = commands[0]
    assert command.op.type == OpType.CX, f"Expected CX gate, but got {command.op.type}"
    qubit_indices = [q.index[0] for q in command.qubits]
    assert qubit_indices == [
        0,
        1,
    ], f"Expected CNOT from qubit 0 to 1, but got {qubit_indices}"

    qubit_mapping = result.virtual_physical_mapping["qubit_mapping"]
    assert qubit_mapping == {0: 0, 1: 1}

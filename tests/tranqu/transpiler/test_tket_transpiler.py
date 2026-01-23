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
from pytket.passes import (  # type: ignore[attr-defined]
    DecomposeBoxes,
    DefaultMappingPass,
    SequencePass,
)
from qiskit import QuantumCircuit  # type: ignore[import-untyped]

from tranqu import Tranqu


class BackendForTest(Backend):
    _ERROR_MESSAGE = "This backend is for testing only"

    def __init__(self) -> None:
        self._architecture = Architecture([(0, 1)])
        self._backend_info = BackendInfo(
            name="test_device",
            device_name="test_device",
            architecture=self._architecture,
            version="1.0.0",
            gate_set=set(),
        )
        self.last_optimisation_level: int | None = None

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
    ) -> SequencePass:
        self.last_optimisation_level = optimisation_level
        return SequencePass([DecomposeBoxes()])

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


class BackendWithMappingPass(Backend):
    _ERROR_MESSAGE = "This backend is for testing only"

    def __init__(self) -> None:
        self._architecture = Architecture([(1, 2)])
        self._backend_info = BackendInfo(
            name="mapped_device",
            device_name="mapped_device",
            architecture=self._architecture,
            version="1.0.0",
            gate_set=set(),
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
    ) -> SequencePass:
        _ = optimisation_level
        return SequencePass([DefaultMappingPass(self._architecture)])

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

    before_stats = result.stats["before"]

    assert before_stats["n_qubits"] == 2
    assert before_stats["n_gates"] == 3
    assert before_stats["depth"] == 3
    assert before_stats["n_gates_1q"] == 2
    assert before_stats["n_gates_2q"] == 1


def test_tranqu_tracks_statistics_after_transpilation(tranqu: Tranqu) -> None:
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

    after_stats = result.stats["after"]

    assert isinstance(after_stats["n_gates"], int)
    assert isinstance(after_stats["depth"], int)
    assert isinstance(after_stats["n_gates_1q"], int)
    assert isinstance(after_stats["n_gates_2q"], int)
    assert result.stats["before"]["n_qubits"] == result.stats["after"]["n_qubits"]


def test_tranqu_transpile_qiskit_program_with_tket_transpiler(
    tranqu: Tranqu,
) -> None:
    circuit = QuantumCircuit(2)
    circuit.h(0)
    circuit.cx(0, 1)

    result = tranqu.transpile(
        program=circuit,
        program_lib="qiskit",
        transpiler_lib="tket",
    )

    assert isinstance(result.transpiled_program, QuantumCircuit)
    assert result.stats["before"]["n_qubits"] == 2
    assert result.stats["after"]["n_qubits"] == 2
    assert set(result.virtual_physical_mapping["qubit_mapping"].keys()) == {0, 1}


def test_tranqu_transpile_tket_program_with_tket_transpiler(
    tranqu: Tranqu,
) -> None:
    circuit = Circuit(2)

    result = tranqu.transpile(
        program=circuit,
        program_lib="tket",
        transpiler_lib="tket",
    )

    assert isinstance(result.transpiled_program, Circuit)
    assert result.virtual_physical_mapping["qubit_mapping"] == {0: 0, 1: 1}


def test_tranqu_uses_device_default_compilation_pass(tranqu: Tranqu) -> None:
    qasm = """
        OPENQASM 3.0;
        include "stdgates.inc";
        qubit[2] q;
        cx q[0], q[1];
    """
    device = BackendForTest()

    result = tranqu.transpile(
        program=qasm,
        program_lib="openqasm3",
        transpiler_lib="tket",
        transpiler_options={"optimization_level": 2},
        device=device,
        device_lib="tket",
    )

    assert device.last_optimisation_level == 2
    assert result.virtual_physical_mapping["qubit_mapping"] == {0: 0, 1: 1}


def test_tranqu_returns_device_mapping(tranqu: Tranqu) -> None:
    qasm = """
        OPENQASM 3.0;
        include "stdgates.inc";
        qubit[2] q;
        cx q[0], q[1];
    """
    device = BackendWithMappingPass()

    result = tranqu.transpile(
        program=qasm,
        program_lib="openqasm3",
        transpiler_lib="tket",
        device=device,
        device_lib="tket",
    )

    mapping = result.virtual_physical_mapping["qubit_mapping"]
    assert set(mapping.keys()) == {0, 1}
    assert set(mapping.values()) == {1, 2}
    assert mapping != {0: 0, 1: 1}


def test_tranqu_rejects_unsupported_optimization_level(tranqu: Tranqu) -> None:
    with pytest.raises(ValueError, match="Invalid optimization level"):
        tranqu.transpile(
            program=Circuit(1),
            program_lib="tket",
            transpiler_lib="tket",
            transpiler_options={"optimization_level": 3},
        )

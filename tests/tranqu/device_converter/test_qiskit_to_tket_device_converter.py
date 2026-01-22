from collections.abc import Sequence
from typing import Any

import pytest
from pytket.backends import Backend  # type: ignore[attr-defined]
from pytket.backends.backend import (  # type: ignore[attr-defined]
    Circuit,
    ResultHandle,
)
from pytket.circuit import OpType  # type: ignore[attr-defined]
from pytket.passes import BasePass  # type: ignore[import-untyped]
from pytket.unit_id import Node  # type: ignore[attr-defined]
from qiskit.providers import BackendV2, Options  # type: ignore[import-untyped]
from qiskit.transpiler import CouplingMap, Target  # type: ignore[import-untyped]

from tranqu.device_converter import DeviceConverterError, QiskitToTketDeviceConverter


class TestQiskitToTketDeviceConverter:
    def setup_method(self):
        self.converter = QiskitToTketDeviceConverter()

    def test_convert_valid_device(self):
        qiskit_backend = MockQiskitBackend()

        result = self.converter.convert(qiskit_backend)

        assert isinstance(result, Backend)

    def test_convert_invalid_device(self):
        invalid_backend = None

        with pytest.raises(DeviceConverterError):
            self.converter.convert(invalid_backend)

    def test_convert_builds_architecture_from_coupling_map(self):
        coupling_map = CouplingMap([[0, 1], [1, 2]])
        qiskit_backend = MockQiskitBackend(
            coupling_map=coupling_map,
            num_qubits=3,
        )

        result = self.converter.convert(qiskit_backend)

        architecture = result.backend_info.architecture
        assert architecture is not None
        assert set(architecture.get_adjacent_nodes(Node(0))) == {Node(1)}
        assert set(architecture.get_adjacent_nodes(Node(1))) == {Node(0), Node(2)}
        assert set(architecture.get_adjacent_nodes(Node(2))) == {Node(1)}

    def test_convert_falls_back_to_fully_connected_architecture(self):
        qiskit_backend = MockQiskitBackend(coupling_map=None, num_qubits=3)

        result = self.converter.convert(qiskit_backend)

        architecture = result.backend_info.architecture
        assert architecture is not None
        assert set(architecture.get_adjacent_nodes(Node(0))) == {Node(1), Node(2)}
        assert set(architecture.get_adjacent_nodes(Node(1))) == {Node(0), Node(2)}
        assert set(architecture.get_adjacent_nodes(Node(2))) == {Node(0), Node(1)}

    def test_convert_maps_operation_names_to_gate_set(self):
        qiskit_backend = MockQiskitBackend(
            operation_names=["cx", "x", "rz", "id", "unknown"],
        )

        result = self.converter.convert(qiskit_backend)

        gate_set = result.backend_info.gate_set
        assert OpType.CX in gate_set
        assert OpType.X in gate_set
        assert OpType.Rz in gate_set
        if hasattr(OpType, "noop"):
            assert OpType.noop in gate_set
        assert all("unknown" not in str(op).lower() for op in gate_set)


class MockQiskitBackend(BackendV2):
    """Mock class for Qiskit's BackendV2."""

    _CONVERSION_ONLY_ERROR = "This backend is for conversion only"

    def __init__(
        self,
        coupling_map: CouplingMap | None = None,
        num_qubits: int | None = None,
        operation_names: list[str] | None = None,
    ) -> None:
        """Initialize the backend."""
        super().__init__(name="mock_device", backend_version="0.0.1")
        self._target = Target()
        self._coupling_map = coupling_map
        self._num_qubits = num_qubits
        self._operation_names = operation_names or []

    @property
    def max_circuits(self) -> int:
        """Return the maximum number of circuits that can be run simultaneously."""
        return 1024

    @property
    def target(self) -> Target:
        """Return the target information of the backend."""
        return self._target

    @property
    def coupling_map(self) -> CouplingMap | None:  # type: ignore[override]
        return self._coupling_map

    @property
    def num_qubits(self) -> int | None:  # type: ignore[override]
        return self._num_qubits

    @property
    def operation_names(self) -> list[str]:  # type: ignore[override]
        return list(self._operation_names)

    def run(self, _run_input: Any, **_options: Any) -> None:
        """Execute circuits (mock implementation).

        Args:
            _run_input: Quantum circuit to execute.
            **_options: Execution options.
        """
        raise NotImplementedError(self._CONVERSION_ONLY_ERROR)

    @classmethod
    def _default_options(cls) -> Options:
        """Return default options.

        Returns:
            Options: Default options for the backend.
        """
        return Options()

    @property
    def _result_id_type(
        self,
    ) -> tuple[
        type[int] | type[float] | type[complex] | type[str] | type[bool] | type[bytes],
        ...,
    ]:
        """Return the type of result ID."""
        return (str,)

    def process_circuit(
        self,
        circuit: Circuit,
        n_shots: int | None = None,
        valid_check: bool = True,  # noqa: FBT001, FBT002
        **kwargs: Any,
    ) -> ResultHandle:
        """Process a circuit (not used in this converter)."""
        raise NotImplementedError(self._CONVERSION_ONLY_ERROR)

    def process_circuits(
        self,
        circuits: Sequence[Circuit],
        n_shots: int | Sequence[int] | None = None,
        valid_check: bool = True,  # noqa: FBT001, FBT002
        **kwargs: Any,
    ) -> list[ResultHandle]:
        """Process multiple circuits (not used in this converter)."""
        raise NotImplementedError(self._CONVERSION_ONLY_ERROR)

    def default_compilation_pass(
        self, optimisation_level: int | None = None
    ) -> BasePass:
        """Return default compilation settings."""
        raise NotImplementedError(self._CONVERSION_ONLY_ERROR)

    def rebase_pass(self) -> BasePass:
        """Return rebase settings."""
        raise NotImplementedError(self._CONVERSION_ONLY_ERROR)

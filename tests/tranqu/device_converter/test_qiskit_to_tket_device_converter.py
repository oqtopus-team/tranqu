from collections.abc import Sequence
from typing import Any

import pytest
from pytket.backends import Backend  # type: ignore[import-untyped]
from pytket.backends.backend import (  # type: ignore[import-untyped]
    Circuit,
    ResultHandle,
)
from pytket.passes import BasePass  # type: ignore[import-untyped]
from qiskit.providers import BackendV2, Options  # type: ignore[import-untyped]
from qiskit.transpiler import Target  # type: ignore[import-untyped]

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


class MockQiskitBackend(BackendV2):
    """Mock class for Qiskit's BackendV2."""

    _CONVERSION_ONLY_ERROR = "This backend is for conversion only"

    def __init__(self) -> None:
        """Initialize the backend."""
        super().__init__(name="mock_device", backend_version="0.0.1")
        self._target = Target()

    @property
    def max_circuits(self) -> int:
        """Return the maximum number of circuits that can be run simultaneously."""
        return 1024

    @property
    def target(self) -> Target:
        """Return the target information of the backend."""
        return self._target

    def run(self, _run_input: Any, **_options: Any) -> None:
        """Execute circuits (mock implementation).

        Args:
            _run_input: Quantum circuit to execute.
            **_options: Execution options.
        """
        return

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

    def default_compilation_pass(self, optimisation_level: int = ...) -> BasePass:
        """Return default compilation settings."""
        raise NotImplementedError(self._CONVERSION_ONLY_ERROR)

    def rebase_pass(self) -> BasePass:
        """Return rebase settings."""
        raise NotImplementedError(self._CONVERSION_ONLY_ERROR)

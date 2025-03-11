from collections.abc import Sequence
from typing import Any

from pytket.backends import Backend  # type: ignore[import-untyped]
from pytket.backends.backend import (  # type: ignore[import-untyped]
    BackendInfo,  # type: ignore[import-untyped]
    CircuitStatus,
    ResultHandle,
)
from pytket.circuit import Circuit  # type: ignore[import-untyped]
from pytket.passes import BasePass  # type: ignore[import-untyped]
from pytket.predicates import Predicate  # type: ignore[import-untyped]
from qiskit.providers import BackendV2  # type: ignore[import-untyped]

from . import DeviceConverter, DeviceConverterError


class QiskitToTketDeviceConverter(DeviceConverter):
    """Converter that transforms Qiskit backends to tket device information."""

    _CONVERSION_ONLY_ERROR = "This backend is for conversion only"

    @staticmethod
    def convert(device: BackendV2) -> Backend:
        """Convert a Qiskit backend to a tket Backend.

        Args:
            device: Source Qiskit backend.

        Returns:
            Converted tket Backend.

        Raises:
            DeviceConverterError.invalid_backend_type: If the input is not a
                BackendV2 instance.

        """
        if not isinstance(device, BackendV2):
            raise DeviceConverterError.invalid_backend_type()

        class ConvertedBackend(Backend):
            """A converted tket backend."""

            _CONVERSION_ONLY_ERROR = "This backend is for conversion only"

            backend_info = BackendInfo(
                name=device.name,
                device_name=device.name,
                version=device.backend_version,
                architecture=device.coupling_map,
                gate_set=device.operation_names,
            )

            @property
            def _result_id_type(
                self,
            ) -> tuple[
                type[int]
                | type[float]
                | type[complex]
                | type[str]
                | type[bool]
                | type[bytes],
                ...,
            ]:
                """Return the type of result ID."""
                return (str,)

            def circuit_status(self, handle: ResultHandle) -> CircuitStatus:
                """Return circuit execution status (not used in this converter)."""
                raise NotImplementedError(self._CONVERSION_ONLY_ERROR)

            def process_circuit(
                self,
                circuit: Circuit,
                n_shots: int | None = ...,
                valid_check: bool = ...,  # noqa: FBT001
                **kwargs: Any,  # noqa: ANN401
            ) -> ResultHandle:
                """Process a circuit (not used in this converter)."""
                raise NotImplementedError(self._CONVERSION_ONLY_ERROR)

            def process_circuits(
                self,
                circuits: Sequence[Circuit],
                n_shots: int | Sequence[int] | None = ...,
                valid_check: bool = ...,  # noqa: FBT001
                **kwargs: Any,  # noqa: ANN401
            ) -> list[ResultHandle]:
                """Process multiple circuits (not used in this converter)."""
                raise NotImplementedError(self._CONVERSION_ONLY_ERROR)

            def run(self) -> ResultHandle:
                """Execute circuits (not used in this converter)."""
                raise NotImplementedError(self._CONVERSION_ONLY_ERROR)

            @property
            def required_predicates(self) -> list[Predicate]:
                """Return required predicates."""
                return []

            def default_compilation_pass(
                self, optimisation_level: int = ...
            ) -> BasePass:
                """Return default compilation settings."""
                raise NotImplementedError(self._CONVERSION_ONLY_ERROR)

            def rebase_pass(self) -> BasePass:
                """Return rebase settings."""
                raise NotImplementedError(self._CONVERSION_ONLY_ERROR)

        return ConvertedBackend()

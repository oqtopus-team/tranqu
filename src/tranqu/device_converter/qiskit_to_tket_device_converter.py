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
from qiskit.providers import BackendV2  # type: ignore[import-untyped]

from .device_converter import DeviceConverter
from .device_converter_manager import DeviceConverterError

# Error messages
CONVERSION_ONLY_ERROR = "This backend is for conversion only"


class QiskitToTketDeviceConverter(DeviceConverter):
    """Converter that transforms Qiskit backends to tket device information."""

    @staticmethod
    def convert(device: BackendV2) -> Backend:  # noqa: C901
        """Convert a Qiskit device to a tket device.

        Args:
            device (BackendV2): Qiskit device to convert.

        Returns:
            Backend: Converted tket device.

        Raises:
            DeviceConverterError: If the device is not a BackendV2 instance.

        """
        if not isinstance(device, BackendV2):
            error_message = f"Expected BackendV2, got {type(device)}"
            raise DeviceConverterError(error_message)

        class ConvertedBackend(Backend):
            """Backend converted from Qiskit device."""

            def __init__(self) -> None:
                self._architecture = Architecture(device.coupling_map.get_edges())
                self._backend_info = BackendInfo(
                    name=device.name,
                    device_name=device.name,
                    architecture=self._architecture,
                    version="1.0.0",
                    gate_set=device.operation_names,
                )

            @property
            def backend_info(self) -> BackendInfo:
                return self._backend_info

            @property
            def required_predicates(self) -> NoReturn:
                raise NotImplementedError(CONVERSION_ONLY_ERROR)

            def rebase_pass(self) -> NoReturn:
                raise NotImplementedError(CONVERSION_ONLY_ERROR)

            def default_compilation_pass(
                self, optimisation_level: int | None = None
            ) -> NoReturn:
                raise NotImplementedError(CONVERSION_ONLY_ERROR)

            def process_circuits(
                self,
                circuits: Sequence[Circuit],
                n_shots: int | Sequence[int | None] | None = None,
                valid_check: bool = True,  # noqa: FBT001, FBT002
                **kwargs: Any,  # noqa: ANN401
            ) -> NoReturn:
                raise NotImplementedError(CONVERSION_ONLY_ERROR)

            def get_result(self, handle: ResultHandle, **kwargs: Any) -> NoReturn:  # noqa: ANN401
                raise NotImplementedError(CONVERSION_ONLY_ERROR)

            @property
            def _result_id_type(self) -> tuple[type[str]]:
                return (str,)

            def circuit_status(self, handle: ResultHandle) -> CircuitStatus:
                raise NotImplementedError(CONVERSION_ONLY_ERROR)

        return ConvertedBackend()

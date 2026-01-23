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
from pytket.passes import (  # type: ignore[attr-defined]
    AASRouting,
    AutoRebase,
    DecomposeBoxes,
    DefaultMappingPass,
    SequencePass,
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
                self._architecture = _build_architecture(device)
                self._gate_set = _convert_gate_set(device.operation_names)
                version = getattr(device, "backend_version", None)
                if not version:
                    version = getattr(device, "version", None)
                if not version:
                    version = "1.0.0"
                self._backend_info = BackendInfo(
                    name=device.name,
                    device_name=device.name,
                    architecture=self._architecture,
                    version=version,
                    gate_set=self._gate_set,
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
            ) -> SequencePass:
                _ = optimisation_level
                passes = [DecomposeBoxes()]
                if self._architecture is not None:
                    passes.extend([
                        DefaultMappingPass(self._architecture),
                        AASRouting(self._architecture),
                    ])
                if self._gate_set:
                    passes.append(AutoRebase(self._gate_set))
                return SequencePass(passes)

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


def _build_architecture(device: BackendV2) -> Architecture | None:
    coupling_map = device.coupling_map
    if coupling_map:
        return Architecture(coupling_map.get_edges())

    if hasattr(device, "num_qubits") and device.num_qubits:
        # Assume full connectivity when coupling_map is absent (unconstrained).
        qubits = list(range(device.num_qubits))
        edges = [(i, j) for i in qubits for j in qubits if i < j]
        return Architecture(edges)

    return None


def _convert_gate_set(operation_names: Sequence[str]) -> set[OpType]:
    return {
        optype
        for name in operation_names
        if (optype := _to_tket_optype(name)) is not None
    }


def _to_tket_optype(name: str) -> OpType | None:
    normalized = name.replace("-", "").replace("_", "").strip()
    candidates = [normalized.upper(), normalized.capitalize(), normalized]
    for candidate in candidates:
        if hasattr(OpType, candidate):
            return getattr(OpType, candidate)
    if normalized in {"id", "i"} and hasattr(OpType, "noop"):
        return OpType.noop
    return None

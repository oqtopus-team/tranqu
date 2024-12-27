from typing import Any

from .device_converter import DeviceConverterManager
from .device_type_manager import DeviceTypeManager
from .program_converter import ProgramConverterManager
from .program_type_manager import ProgramTypeManager
from .tranqu_error import TranquError
from .transpile_result import TranspileResult
from .transpiler import TranspilerManager


class TranspilerDispatcherError(TranquError):
    """Base class for errors related to the transpiler dispatcher."""


class ProgramLibResolutionError(TranspilerDispatcherError):
    """Error raised when program library cannot be resolved."""


class ProgramNotSpecifiedError(TranspilerDispatcherError):
    """Error raised when no program is specified."""


class ProgramLibNotSpecifiedError(TranspilerDispatcherError):
    """Error raised when no program library is specified."""


class TranspilerLibNotSpecifiedError(TranspilerDispatcherError):
    """Error raised when no transpiler library is specified."""


class DeviceNotSpecifiedError(TranspilerDispatcherError):
    """Error raised when a device library is specified but no device is specified."""


class ProgramConversionPathNotFoundError(TranspilerDispatcherError):
    """Error raised when no conversion path is found for the program."""


class DeviceConversionPathNotFoundError(TranspilerDispatcherError):
    """Error raised when no conversion path is found for the device."""


class TranspilerDispatcher:
    """A dispatcher class that executes quantum circuit transpilation.

    Manages the integrated handling of circuit conversion between different
    quantum computing libraries and the utilization of various transpiler libraries.

    Supports conversion through Qiskit as an intermediate format when direct conversion
    between programs is not available.

    Args:
        transpiler_manager (TranspilerManager): Manages the selection and
            execution of transpilers.
        program_converter_manager (ProgramConverterManager): Handles conversion of
            quantum programs between different libraries.
        device_converter_manager (DeviceConverterManager): Handles conversion of
            device specifications between different libraries.
        program_type_manager (ProgramTypeManager): Manages detection of program types
            and their corresponding libraries.
        device_type_manager (DeviceTypeManager): Manages detection of device types
            and their corresponding libraries.

    """

    def __init__(
        self,
        transpiler_manager: TranspilerManager,
        program_converter_manager: ProgramConverterManager,
        device_converter_manager: DeviceConverterManager,
        program_type_manager: ProgramTypeManager,
        device_type_manager: DeviceTypeManager,
    ) -> None:
        self._transpiler_manager = transpiler_manager
        self._program_converter_manager = program_converter_manager
        self._device_converter_manager = device_converter_manager
        self._program_type_manager = program_type_manager
        self._device_type_manager = device_type_manager

    def dispatch(  # noqa: PLR0913 PLR0917
        self,
        program: Any,  # noqa: ANN401
        program_lib: str | None,
        transpiler_lib: str | None,
        transpiler_options: dict[str, Any] | None,
        device: Any | None,  # noqa: ANN401
        device_lib: str | None,
    ) -> TranspileResult:
        """Execute transpilation of a quantum circuit.

        Args:
            program (Any): The quantum circuit to be transpiled
            program_lib (str): Name of the library for the input circuit
                (e.g., "qiskit")
            transpiler_lib (str | None): Name of the transpiler library to use
            transpiler_options (dict | None): Options to be passed to the transpiler
            device (Any | None): Target device (optional)
            device_lib (str | None): Name of the device library (optional)

        Returns:
            TranspileResult: Object containing the transpilation results

        Raises:
            ProgramNotSpecifiedError: Raised when no program is specified.

        """
        if program is None:
            msg = "No program specified. Please specify a valid quantum circuit."
            raise ProgramNotSpecifiedError(msg)

        selected_transpiler_lib = self._select_transpiler_lib(transpiler_lib)
        resolved_program_lib = self._resolve_program_lib(program, program_lib)
        resolved_device_lib = self._resolve_device_lib(device, device_lib)
        transpiler = self._transpiler_manager.fetch_transpiler(selected_transpiler_lib)

        if resolved_program_lib != transpiler.program_lib:
            converted_program = self._convert_program(
                program, from_lib=resolved_program_lib, to_lib=transpiler.program_lib
            )
        else:
            converted_program = program

        converted_device = self._convert_device(
            device, from_lib=resolved_device_lib, to_lib=selected_transpiler_lib
        )

        result = transpiler.transpile(
            converted_program,
            transpiler_options,
            converted_device,
        )

        if transpiler.program_lib != resolved_program_lib:
            result.transpiled_program = self._convert_program(
                result.transpiled_program,
                from_lib=transpiler.program_lib,
                to_lib=resolved_program_lib,
            )

        return result

    def _select_transpiler_lib(self, transpiler_lib: str | None) -> str:
        selected_lib = transpiler_lib

        if selected_lib is None:
            selected_lib = self._transpiler_manager.get_default_transpiler_lib()

        if selected_lib is None:
            msg = "No transpiler library specified. Please specify a transpiler to use."
            raise TranspilerLibNotSpecifiedError(msg)

        return selected_lib

    def _resolve_program_lib(self, program: Any, program_lib: str | None) -> str:  # noqa: ANN401
        if program_lib is None:
            resolved_lib = self._program_type_manager.resolve_lib(program)
        else:
            resolved_lib = program_lib

        if resolved_lib is None:
            msg = (
                "Could not resolve program library. Please either "
                "specify program_lib or register the program type "
                "using register_program_type()."
            )
            raise ProgramLibResolutionError(msg)

        return resolved_lib

    def _resolve_device_lib(
        self,
        device: Any | None,  # noqa: ANN401
        device_lib: str | None,
    ) -> str | None:
        if device is None and device_lib is not None:
            msg = "Device library is specified but no device is specified."
            raise DeviceNotSpecifiedError(msg)

        if device_lib is None:
            resolved_lib = self._device_type_manager.resolve_lib(device)
        else:
            resolved_lib = device_lib

        return resolved_lib

    def _convert_program(self, program: Any, *, from_lib: str, to_lib: str) -> Any:  # noqa: ANN401
        if self._can_convert_program_directly(from_lib=from_lib, to_lib=to_lib):
            direct_converter = self._program_converter_manager.fetch_converter(
                from_lib=from_lib,
                to_lib=to_lib,
            )
            return direct_converter.convert(program)

        if not self._can_convert_program_via_qiskit(from_lib=from_lib, to_lib=to_lib):
            msg = (
                f"No ProgramConverter path found to convert from {from_lib} to {to_lib}"
            )
            raise ProgramConversionPathNotFoundError(msg)

        to_qiskit_converter = self._program_converter_manager.fetch_converter(
            from_lib, "qiskit"
        )
        from_qiskit_converter = self._program_converter_manager.fetch_converter(
            "qiskit", to_lib
        )

        qiskit_program = to_qiskit_converter.convert(program)
        return from_qiskit_converter.convert(qiskit_program)

    def _can_convert_program_directly(self, *, from_lib: str, to_lib: str) -> bool:
        return self._program_converter_manager.has_converter(
            from_lib=from_lib, to_lib=to_lib
        )

    def _can_convert_program_via_qiskit(self, *, from_lib: str, to_lib: str) -> bool:
        can_convert_to_qiskit = self._program_converter_manager.has_converter(
            from_lib=from_lib,
            to_lib="qiskit",
        )
        can_convert_to_target = self._program_converter_manager.has_converter(
            from_lib="qiskit",
            to_lib=to_lib,
        )
        return can_convert_to_qiskit and can_convert_to_target

    def _convert_device(
        self,
        device: Any | None,  # noqa: ANN401
        *,
        from_lib: str | None,
        to_lib: str,
    ) -> Any | None:  # noqa: ANN401
        if device is None:
            return None

        if from_lib is None:
            return device

        if self._can_convert_device_directly(from_lib=from_lib, to_lib=to_lib):
            direct_converter = self._device_converter_manager.fetch_converter(
                from_lib,
                to_lib,
            )
            return direct_converter.convert(device)

        if not self._can_convert_device_via_qiskit(from_lib=from_lib, to_lib=to_lib):
            msg = (
                f"No DeviceConverter path found to convert from {from_lib} to {to_lib}"
            )
            raise DeviceConversionPathNotFoundError(msg)

        to_qiskit_converter = self._device_converter_manager.fetch_converter(
            from_lib, "qiskit"
        )
        from_qiskit_converter = self._device_converter_manager.fetch_converter(
            "qiskit", to_lib
        )
        qiskit_device = to_qiskit_converter.convert(device)
        return from_qiskit_converter.convert(qiskit_device)

    def _can_convert_device_directly(self, *, from_lib: str, to_lib: str) -> bool:
        return self._device_converter_manager.has_converter(from_lib, to_lib)

    def _can_convert_device_via_qiskit(self, *, from_lib: str, to_lib: str) -> bool:
        can_convert_to_qiskit = self._device_converter_manager.has_converter(
            from_lib,
            "qiskit",
        )
        can_convert_to_target = self._device_converter_manager.has_converter(
            "qiskit",
            to_lib,
        )

        return can_convert_to_qiskit and can_convert_to_target

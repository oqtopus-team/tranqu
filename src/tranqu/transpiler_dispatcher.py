from typing import Any

from .device_converter import DeviceConverterManager
from .program_converter import ProgramConverterManager
from .tranqu_error import TranquError
from .transpile_result import TranspileResult
from .transpiler import TranspilerManager


class TranspilerDispatcherError(TranquError):
    """Base class for errors related to the transpiler dispatcher."""


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

    """

    def __init__(
        self,
        transpiler_manager: TranspilerManager,
        program_converter_manager: ProgramConverterManager,
        device_converter_manager: DeviceConverterManager,
    ) -> None:
        self._transpiler_manager = transpiler_manager
        self._program_converter_manager = program_converter_manager
        self._device_converter_manager = device_converter_manager

    def dispatch(  # noqa: PLR0913 PLR0917
        self,
        program: Any,  # noqa: ANN401
        program_lib: str,
        transpiler_lib: str,
        transpiler_options: dict | None,
        device: Any | None,  # noqa: ANN401
        device_lib: str | None,
    ) -> TranspileResult:
        """Execute transpilation of a quantum circuit.

        Args:
            program (Any): The quantum circuit to be transpiled
            program_lib (str): Name of the library for the input circuit
                (e.g., "qiskit")
            transpiler_lib (str): Name of the transpiler library to use
            transpiler_options (dict | None): Options to be passed to the transpiler
            device (Any | None): Target device (optional)
            device_lib (str | None): Name of the device library (optional)

        Returns:
            TranspileResult: Object containing the transpilation results

        Raises:
            ProgramNotSpecifiedError: Raised when no program is specified.
            ProgramLibNotSpecifiedError: Raised when no program library is specified.
            TranspilerLibNotSpecifiedError: Raised when no transpiler library
                is specified.
            DeviceNotSpecifiedError: Raised when a device library is specified
                but no device is specified.

        """
        if program is None:
            msg = "No program specified. Please specify a valid quantum circuit."
            raise ProgramNotSpecifiedError(msg)
        if program_lib is None:
            msg = "No program library specified. Please specify a program format "
            "('qiskit', 'openqasm3', 'tket', etc.)."
            raise ProgramLibNotSpecifiedError(msg)
        if transpiler_lib is None:
            msg = "No transpiler library specified. Please specify a transpiler to use "
            "('qiskit', 'tket', etc.)."
            raise TranspilerLibNotSpecifiedError(msg)
        if device_lib is not None and device is None:
            msg = "Device library is specified but no device is specified. "
            "Please specify a device."
            raise DeviceNotSpecifiedError(msg)

        transpiler = self._transpiler_manager.fetch_transpiler(transpiler_lib)

        converted_program = self._convert_program(program, program_lib, transpiler_lib)
        converted_device = self._convert_device(device, device_lib, transpiler_lib)

        transpile_result = transpiler.transpile(
            converted_program,
            transpiler_options,
            converted_device,
        )

        transpile_result.transpiled_program = self._convert_program(
            transpile_result.transpiled_program,
            transpiler_lib,
            program_lib,
        )

        return transpile_result

    def _convert_program(self, program: Any, from_lib: str, to_lib: Any) -> Any:  # noqa: ANN401
        if self._program_converter_manager.has_converter(from_lib, to_lib):
            return self._program_converter_manager.fetch_converter(
                from_lib,
                to_lib,
            ).convert(program)

        can_convert_to_qiskit = self._program_converter_manager.has_converter(
            from_lib,
            "qiskit",
        )
        can_convert_to_target = self._program_converter_manager.has_converter(
            "qiskit",
            to_lib,
        )
        if not (can_convert_to_qiskit and can_convert_to_target):
            msg = f"No ProgramConverter path found to convert from {from_lib} to {to_lib}"  # noqa: E501
            raise ProgramConversionPathNotFoundError(msg)

        return self._program_converter_manager.fetch_converter(
            "qiskit",
            to_lib,
        ).convert(
            self._program_converter_manager.fetch_converter(from_lib, "qiskit").convert(
                program,
            ),
        )

    def _convert_device(
        self,
        device: Any | None,  # noqa: ANN401
        from_lib: str | None,
        to_lib: Any,  # noqa: ANN401
    ) -> Any | None:  # noqa: ANN401
        if device is None or from_lib is None:
            return device

        if self._device_converter_manager.has_converter(from_lib, to_lib):
            return self._device_converter_manager.fetch_converter(
                from_lib,
                to_lib,
            ).convert(device)

        can_convert_to_qiskit = self._device_converter_manager.has_converter(
            from_lib,
            "qiskit",
        )
        can_convert_to_target = self._device_converter_manager.has_converter(
            "qiskit",
            to_lib,
        )
        if not (can_convert_to_qiskit and can_convert_to_target):
            msg = f"No DeviceConverter path found to convert from {from_lib} to {to_lib}"  # noqa: E501
            raise DeviceConversionPathNotFoundError(msg)

        return self._device_converter_manager.fetch_converter("qiskit", to_lib).convert(
            self._device_converter_manager.fetch_converter(from_lib, "qiskit").convert(
                device,
            ),
        )

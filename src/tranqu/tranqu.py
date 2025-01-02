"""Provides classes and functions for executing the transpilation of quantum circuits.

Users can perform flexible transpilation using the `transpile()` method.
For example, quantum circuit programs in Qiskit or OpenQASM3 can be transpiled
using a transpiler different from the program's format (such as Tket's transpiler).

For instance, when transpiling a Qiskit quantum circuit program with Tket's transpiler,
Tranqu automates the following processes:

1. Automatically converts the Qiskit program to Tket format.
2. If there is device information (referred to as a backend object in Qiskit),
    it also automatically converts this to Qiskit format.
3. The program and device information converted to Tket format
    are used to transpile with Tket.
4. The transpilation result and various statistical information
    are returned as a `TranspileResult`.

Example:
    To convert a Qiskit circuit using the Tket transpiler,
    use the `transpile()` method as follows:

        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.cx(0, 1)

        tranqu = Tranqu()

        result = tranqu.transpile(
            circuit, program_lib="qiskit", transpiler_lib="tket")

Additionally, it is possible to incorporate user-defined transpilers.
This module also provides a series of methods for this purpose.

- `register_default_transpiler_lib()`: Registers the default transpiler library.
- `register_transpiler()`: Registers a custom transpiler to Tranqu.
- `register_program_converter()`: Registers a converter (`ProgramConverter`)
    for quantum circuit programs. When registering a custom transpiler,
    it is necessary to also register bidirectional program converters.
- `register_device_converter()`: Registers a converter (`DeviceConverter`)
    for quantum machine device information.
    This is also necessary when registering a custom transpiler.

Example:
    To transpile Qiskit code using a user-defined transpiler
    (let's call it EnigmaTranspiler), you need to register the transpiler,
    ProgramConverters, and DeviceConverters as follows:

        tranqu = Tranqu()
        tranqu.register_transpiler("enigma", EnigmaTranspiler())

        # Enable mutual conversion between Qiskit and Enigma program formats
        tranqu.register_program_converter("qiskit", "enigma",
                                          QiskitToEnigmaProgramConverter())
        tranqu.register_program_converter("enigma", "qiskit",
                                          EnigmaToQiskitProgramConverter())

        # Enable mutual conversion between Qiskit devices and Enigma device formats
        tranqu.register_device_converter("qiskit", "enigma",
                                         QiskitToEnigmaDeviceConverter())
        tranqu.register_device_converter("enigma", "qiskit",
                                         EnigmaToQiskitDeviceConverter())

        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.cx(0, 1)

        result = tranqu.transpile(circuit, program_lib="qiskit",
                                  transpiler_lib="enigma",
                                  device=FakeSantiagoV2(), device_lib="qiskit")

With these mechanisms, users can flexibly perform conversions
between different quantum program formats and optimize quantum circuits
using their own transpilers.

"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pytket import Circuit as TketCircuit
from qiskit import QuantumCircuit as QiskitCircuit  # type: ignore[import-untyped]
from qiskit.providers import BackendV2  # type: ignore[import-untyped]

from .device_converter import (
    DeviceConverter,
    DeviceConverterManager,
    OqtopusToOuquTpDeviceConverter,
    OqtoqusToQiskitDeviceConverter,
    QiskitToOuquTpDeviceConverter,
)
from .device_type_manager import DeviceTypeManager
from .program_converter import (
    Openqasm3ToQiskitProgramConverter,
    Openqasm3ToTketProgramConverter,
    ProgramConverter,
    ProgramConverterManager,
    QiskitToOpenqasm3ProgramConverter,
    QiskitToTketProgramConverter,
    TketToOpenqasm3ProgramConverter,
    TketToQiskitProgramConverter,
)
from .program_type_manager import ProgramTypeManager
from .transpiler import OuquTpTranspiler, QiskitTranspiler, TranspilerManager
from .transpiler_dispatcher import TranspilerDispatcher

if TYPE_CHECKING:
    from .transpile_result import TranspileResult


class Tranqu:
    """Manage the transpilation of quantum circuits.

    Handles converters for transforming between different quantum program formats and
    transpilers for optimizing quantum circuits.
    """

    def __init__(self) -> None:
        self._program_converter_manager = ProgramConverterManager()
        self._device_converter_manager = DeviceConverterManager()
        self._transpiler_manager = TranspilerManager()
        self._program_type_manager = ProgramTypeManager()
        self._device_type_manager = DeviceTypeManager()

        self._register_builtin_program_converters()
        self._register_builtin_device_converters()
        self._register_builtin_transpilers()
        self._register_builtin_program_types()
        self._register_builtin_device_types()

    def transpile(  # noqa: PLR0913
        self,
        program: Any,  # noqa: ANN401
        program_lib: str | None = None,
        transpiler_lib: str | None = None,
        *,
        transpiler_options: dict[str, Any] | None = None,
        device: Any | None = None,  # noqa: ANN401
        device_lib: str | None = None,
    ) -> TranspileResult:
        """Transpile the program using the specified transpiler.

        Args:
            program (Any): The program to be transformed.
            program_lib (str | None): The library or format of the program. If None,
                will attempt to detect based on program type.
            transpiler_lib (str | None): The name of the transpiler to be used.
            transpiler_options (dict[str, Any]): Options passed to the transpiler.
            device (Any | None): Information about the device on which
                the program will be executed.
            device_lib (str | None): Specifies the type of the device.

        Returns:
            TranspileResult: The result of the transpilation.

        """
        dispatcher = TranspilerDispatcher(
            self._transpiler_manager,
            self._program_converter_manager,
            self._device_converter_manager,
            self._program_type_manager,
            self._device_type_manager,
        )

        return dispatcher.dispatch(
            program,
            program_lib,
            transpiler_lib,
            transpiler_options,
            device,
            device_lib,
        )

    def register_default_transpiler_lib(
        self,
        default_transpiler_lib: str,
        *,
        allow_override: bool = False,
    ) -> None:
        """Register the default transpiler library.

        Args:
            default_transpiler_lib (str): The name of the default transpiler library
                to register.
            allow_override (bool): When True, allows overwriting of existing default
                transpiler lib.

        """
        self._transpiler_manager.register_default_transpiler_lib(
            default_transpiler_lib, allow_override=allow_override
        )

    def register_transpiler(
        self,
        transpiler_lib: str,
        transpiler: Any,  # noqa: ANN401
        *,
        allow_override: bool = False,
    ) -> None:
        """Register a transpiler for optimizing quantum circuits.

        This method allows you to register a transpiler for optimizing quantum circuits.

        Args:
            transpiler_lib (str): The name of the transpiler library.
            transpiler (Any): The transpiler to be registered.
            allow_override (bool): When True, allows overwriting of existing transpilers

        """
        self._transpiler_manager.register_transpiler(
            transpiler_lib,
            transpiler,
            allow_override=allow_override,
        )

    def register_program_converter(
        self,
        from_program_lib: str,
        to_program_lib: str,
        converter: ProgramConverter,
        *,
        allow_override: bool = False,
    ) -> None:
        """Register a program converter.

        This method allows you to register a converter for transforming
        between different program types.

        Args:
            from_program_lib (str): The identifier for the source program type of
                the converter to be registered.
            to_program_lib (str): The identifier for the target program type of
                the converter to be registered.
            converter (ProgramConverter): The program converter to be registered
                (subclass of ProgramConverter).
            allow_override (bool): When True, allows overwriting of existing converters.
                Defaults to False.

        Examples:
            To register a converter that transforms from "foo" to "bar", you can call:

                tranqu.register_program_converter(
                    "foo", "bar",
                    FooToBarProgramConverter)

        """
        self._program_converter_manager.register_converter(
            from_program_lib,
            to_program_lib,
            converter,
            allow_override=allow_override,
        )

    def register_device_converter(
        self,
        from_device_lib: str,
        to_device_lib: str,
        converter: DeviceConverter,
        *,
        allow_override: bool = False,
    ) -> None:
        """Register a device converter.

        This method allows you to register a converter for transforming
        between different device types.

        Args:
            from_device_lib (str): The identifier for the source device type of
                the converter to be registered.
            to_device_lib (str): The identifier for the target device type of
                the converter to be registered.
            converter (DeviceConverter): The device converter to be registered
                (subclass of DeviceConverter).
            allow_override (bool): When True, allows overwriting of existing converters.
                Defaults to False.

        Examples:
            To register a converter that transforms from "foo" to "bar", you would call:

                tranqu.register_device_converter("foo", "bar", FooToBarDeviceConverter)

        """
        self._device_converter_manager.register_converter(
            from_device_lib,
            to_device_lib,
            converter,
            allow_override=allow_override,
        )

    def register_program_type(
        self,
        program_lib: str,
        program_type: type,
        *,
        allow_override: bool = False,
    ) -> None:
        """Register a mapping between a program type and its library identifier.

        This method allows automatic detection of the program library based on the
        program's type when calling transpile().

        Args:
            program_lib (str): The identifier for the program library
              (e.g., "qiskit", "tket")
            program_type (type): The type class to be associated with the library
            allow_override (bool): When True, allows overwriting of existing type
                registrations. Defaults to False.

        Examples:
            To register Qiskit's QuantumCircuit type:
                tranqu.register_program_type("qiskit", QuantumCircuit)

        """
        self._program_type_manager.register_type(
            program_lib,
            program_type,
            allow_override=allow_override,
        )

    def register_device_type(
        self,
        device_lib: str,
        device_type: type,
        *,
        allow_override: bool = False,
    ) -> None:
        """Register a mapping between a device type and its library identifier.

        This method enables automatic detection of the device library based on
        the device type when calling transpile().

        Args:
            device_lib (str): The identifier for the device library
              (e.g., "qiskit", "oqtopus")
            device_type (type): The type class to be associated with the library
            allow_override (bool): When True, allows overwriting of existing type
                registrations. Defaults to False.

        Examples:
            To register Qiskit's backend type:
                tranqu.register_device_type("qiskit", BackendV2)

        """
        self._device_type_manager.register_type(
            device_lib,
            device_type,
            allow_override=allow_override,
        )

    def _register_builtin_program_converters(self) -> None:
        self.register_program_converter(
            "openqasm3",
            "qiskit",
            Openqasm3ToQiskitProgramConverter(),
        )
        self.register_program_converter(
            "openqasm3",
            "qiskit-passes",
            Openqasm3ToQiskitProgramConverter(),
        )
        self.register_program_converter(
            "openqasm3",
            "tket",
            Openqasm3ToTketProgramConverter(),
        )
        self.register_program_converter(
            "qiskit",
            "openqasm3",
            QiskitToOpenqasm3ProgramConverter(),
        )
        self.register_program_converter(
            "qiskit-passes",
            "openqasm3",
            QiskitToOpenqasm3ProgramConverter(),
        )
        self.register_program_converter(
            "qiskit",
            "tket",
            QiskitToTketProgramConverter(),
        )
        self.register_program_converter(
            "tket",
            "openqasm3",
            TketToOpenqasm3ProgramConverter(),
        )
        self.register_program_converter(
            "tket",
            "qiskit",
            TketToQiskitProgramConverter(),
        )

    def _register_builtin_device_converters(self) -> None:
        self.register_device_converter(
            "oqtopus",
            "qiskit",
            OqtoqusToQiskitDeviceConverter(),
        )
        self.register_device_converter(
            "oqtopus",
            "ouqu-tp",
            OqtopusToOuquTpDeviceConverter(),
        )
        self.register_device_converter(
            "qiskit",
            "ouqu-tp",
            QiskitToOuquTpDeviceConverter(),
        )

    def _register_builtin_transpilers(self) -> None:
        self.register_transpiler("qiskit", QiskitTranspiler(program_lib="qiskit"))
        self.register_transpiler("ouqu-tp", OuquTpTranspiler(program_lib="openqasm3"))

    def _register_builtin_program_types(self) -> None:
        self.register_program_type("qiskit", QiskitCircuit)
        self.register_program_type("tket", TketCircuit)

    def _register_builtin_device_types(self) -> None:
        self.register_device_type("qiskit", BackendV2)

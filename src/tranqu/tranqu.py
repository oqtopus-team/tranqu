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

import copy
import importlib
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pytket import Circuit  # type: ignore[attr-defined]
from qiskit import QuantumCircuit  # type: ignore[import-untyped]
from qiskit.providers import BackendV2  # type: ignore[import-untyped]

from .device_converter import (
    DeviceConverter,
    DeviceConverterManager,
    OqtopusToOuquTpDeviceConverter,
    OqtoqusToQiskitDeviceConverter,
    QiskitToOuquTpDeviceConverter,
    QiskitToTketDeviceConverter,
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
from .transpiler import (
    OuquTpTranspiler,
    QiskitTranspiler,
    TketTranspiler,
    TranspilerManager,
)
from .transpiler_dispatcher import TranspilerDispatcher

if TYPE_CHECKING:  # pragma: no cover
    from .transpile_result import TranspileResult

import yaml

"""
try:
    import yaml  # type: ignore[import-untyped]
except ModuleNotFoundError:  # pragma: no cover
    yaml = None
"""


class Tranqu:
    """Manage the transpilation of quantum circuits.

    Handles converters for transforming between different quantum program formats and
    transpilers for optimizing quantum circuits.
    """

    def __init__(
        self,
        *,
        config_path: str | Path | None = None,
    ) -> None:
        self._program_converter_manager = ProgramConverterManager()
        self._device_converter_manager = DeviceConverterManager()
        self._transpiler_manager = TranspilerManager()
        self._program_type_manager = ProgramTypeManager()
        self._device_type_manager = DeviceTypeManager()
        self._loaded_config: dict[str, Any] | None = None
        self._loaded_config_path: Path | None = None
        self._default_transpile: dict[str, Any] = {
            "program_lib": None,
            "transpiler_lib": None,
            "transpiler_options": None,
        }

        self._config_log: dict[str, Any] = {
            "default_transpiler_lib": None,
            "transpilers": [],
            "program_converters": [],
            "device_converters": [],
            "program_types": [],
            "device_types": [],
        }

        if config_path is None:
            self._register_builtin_program_converters()
            self._register_builtin_device_converters()
            self._register_builtin_transpilers()
            self._register_builtin_program_types()
            self._register_builtin_device_types()
            self._loaded_config = {"use_builtins": True}
            self._loaded_config_path = None
        else:
            self.load(config_path=config_path, reset=False)

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
            transpiler_options (dict[str, Any] | None): Options passed to the transpiler
            device (Any | None): Information about the device on which
                the program will be executed.
            device_lib (str | None): Specifies the type of the device.

        Returns:
            TranspileResult: The result of the transpilation.

        """
        default_program_lib = self._default_transpile.get("program_lib")
        default_transpiler_lib = self._default_transpile.get("transpiler_lib")
        default_options = self._default_transpile.get("transpiler_options")

        if program_lib is None and isinstance(default_program_lib, str):
            program_lib = default_program_lib
        if transpiler_lib is None and isinstance(default_transpiler_lib, str):
            transpiler_lib = default_transpiler_lib

        if transpiler_options is None:
            if isinstance(default_options, dict):
                transpiler_options = dict(default_options)
        elif isinstance(default_options, dict):
            transpiler_options = {**default_options, **transpiler_options}

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
            default_transpiler_lib,
            allow_override=allow_override,
        )
        self._config_log["default_transpiler_lib"] = default_transpiler_lib

    def register_transpiler(
        self,
        transpiler_lib: str,
        transpiler: Any,  # noqa: ANN401
        *,
        allow_override: bool = False,
    ) -> None:
        """Register a transpiler for optimizing quantum circuits.

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

        Args:
            from_program_lib (str): The identifier for the source program type.
            to_program_lib (str): The identifier for the target program type.
            converter (ProgramConverter): The converter to register.
            allow_override (bool): When True, allows overwriting of existing converters.

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

        Args:
            from_device_lib (str): The identifier for the source device type.
            to_device_lib (str): The identifier for the target device type.
            converter (DeviceConverter): The converter to register.
            allow_override (bool): When True, allows overwriting of existing converters.

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
        """Register a mapping between a program type and its library identifier."""
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
        """Register a mapping between a device type and its library identifier."""
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
        self.register_device_converter(
            "qiskit",
            "tket",
            QiskitToTketDeviceConverter(),
        )

    def _register_builtin_transpilers(self) -> None:
        self.register_transpiler("qiskit", QiskitTranspiler(program_lib="qiskit"))
        self.register_transpiler("ouqu-tp", OuquTpTranspiler(program_lib="openqasm3"))
        self.register_transpiler("tket", TketTranspiler(program_lib="tket"))

    def _register_builtin_program_types(self) -> None:
        self.register_program_type("qiskit", QuantumCircuit)
        self.register_program_type("tket", Circuit)

    def _register_builtin_device_types(self) -> None:
        self.register_device_type("qiskit", BackendV2)

    def load(self, *, config_path: str | Path, reset: bool = True) -> None:
        """Load configuration from a YAML file."""
        config = self._read_yaml(config_path)

        default_transpile_raw = config.get("default_transpile")
        if default_transpile_raw is None:
            default_transpile: dict[str, object] = {}
        else:
            default_transpile = self._require_dict(
                default_transpile_raw,
                "default_transpile",
            )

        self._default_transpile["program_lib"] = self._require_optional_str(
            default_transpile.get("program_lib"),
            "default_transpile.program_lib",
        )
        self._default_transpile["transpiler_lib"] = self._require_optional_str(
            default_transpile.get("transpiler_lib"),
            "default_transpile.transpiler_lib",
        )
        self._default_transpile["transpiler_options"] = self._require_optional_dict(
            default_transpile.get("transpiler_options"),
            "default_transpile.transpiler_options",
        )

        if reset:
            self._program_converter_manager = ProgramConverterManager()
            self._device_converter_manager = DeviceConverterManager()
            self._transpiler_manager = TranspilerManager()
            self._program_type_manager = ProgramTypeManager()
            self._device_type_manager = DeviceTypeManager()
            self._config_log = {
                "default_transpiler_lib": None,
                "transpilers": [],
                "program_converters": [],
                "device_converters": [],
                "program_types": [],
                "device_types": [],
            }

        self._loaded_config = copy.deepcopy(config)
        self._loaded_config_path = Path(config_path)

        use_builtins = self._require_bool(
            config.get("use_builtins", False),
            "use_builtins",
        )
        if use_builtins:
            self._register_builtin_program_converters()
            self._register_builtin_device_converters()
            self._register_builtin_transpilers()
            self._register_builtin_program_types()
            self._register_builtin_device_types()

        default_lib = config.get("default_transpiler_lib")
        if default_lib is not None:
            default_lib_str = self._require_str(
                default_lib,
                "default_transpiler_lib",
            )
            self.register_default_transpiler_lib(
                default_lib_str,
                allow_override=True,
            )

        self._apply_transpilers(
            self._require_list(config.get("transpilers", []), "transpilers")
        )
        self._apply_program_converters(
            self._require_list(
                config.get("program_converters", []),
                "program_converters",
            )
        )
        self._apply_device_converters(
            self._require_list(
                config.get("device_converters", []),
                "device_converters",
            )
        )
        self._apply_program_types(
            self._require_list(config.get("program_types", []), "program_types")
        )
        self._apply_device_types(
            self._require_list(config.get("device_types", []), "device_types")
        )

    def save(self, *, config_path: str | Path) -> None:
        """Save the last loaded configuration to a YAML file."""
        if self._loaded_config is None:
            config: dict[str, Any] = {"use_builtins": True}
        else:
            config = copy.deepcopy(self._loaded_config)

        if self._config_log["default_transpiler_lib"] is not None:
            config["default_transpiler_lib"] = self._config_log[
                "default_transpiler_lib"
            ]

        self._write_yaml(config_path, config)

    @staticmethod
    def _read_yaml(path: str | Path) -> dict[str, Any]:
        if yaml is None:  # pragma: no cover
            message = "YAML support requires PyYAML (pip install pyyaml)."
            raise ModuleNotFoundError(message)
        with Path(path).open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)  # type: ignore[union-attr]
        if not isinstance(data, dict):
            message = "YAML root must be a mapping/dict."
            raise TypeError(message)
        return data

    @staticmethod
    def _write_yaml(path: str | Path, data: dict[str, Any]) -> None:
        if yaml is None:  # pragma: no cover
            message = "YAML support requires PyYAML (pip install pyyaml)."
            raise ModuleNotFoundError(message)
        with Path(path).open("w", encoding="utf-8") as f:
            yaml.safe_dump(  # type: ignore[union-attr]
                data,
                f,
                sort_keys=False,
                default_flow_style=False,
                allow_unicode=True,
            )

    @staticmethod
    def _require_bool(value: object, name: str) -> bool:
        if not isinstance(value, bool):
            message = f"{name} must be a bool."
            raise TypeError(message)
        return value

    @staticmethod
    def _require_str(value: object, name: str) -> str:
        if not isinstance(value, str):
            message = f"{name} must be a str."
            raise TypeError(message)
        return value

    @staticmethod
    def _require_optional_str(value: object, name: str) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            message = f"{name} must be a str or None."
            raise TypeError(message)
        return value

    @staticmethod
    def _require_dict(value: object, name: str) -> dict[str, object]:
        if not isinstance(value, dict):
            message = f"{name} must be a dict."
            raise TypeError(message)
        return value

    @staticmethod
    def _require_optional_dict(value: object, name: str) -> dict[str, object] | None:
        if value is None:
            return None
        if not isinstance(value, dict):
            message = f"{name} must be a dict or None."
            raise TypeError(message)
        return value

    @staticmethod
    def _require_list(value: object, name: str) -> list[object]:
        if not isinstance(value, list):
            message = f"{name} must be a list."
            raise TypeError(message)
        return value

    @staticmethod
    def _import_symbol(ref: str) -> Any:  # noqa: ANN401
        if ":" not in ref:
            message = "Invalid import ref: expected 'module:Symbol'"
            raise ValueError(message)
        mod_name, sym = ref.split(":", 1)

        allowed_prefixes = ("tranqu.", "qiskit", "pytket")
        if not mod_name.startswith(allowed_prefixes):
            message = f"Import is not allowed: {mod_name}"
            raise ValueError(message)

        mod = importlib.import_module(mod_name)
        return getattr(mod, sym)

    def _instantiate_factory(self, factory: dict[str, object]) -> Any:  # noqa: ANN401
        factory_dict = self._require_dict(factory, "factory")

        import_ref_raw = factory_dict.get("import")
        if import_ref_raw is None:
            message = "factory.import is required (no builtin mapping table)"
            raise ValueError(message)
        import_ref = self._require_str(import_ref_raw, "factory.import")

        kwargs_raw = factory_dict.get("kwargs")
        if kwargs_raw is None:
            kwargs: dict[str, object] = {}
        else:
            kwargs = self._require_dict(kwargs_raw, "factory.kwargs")

        cls = self._import_symbol(import_ref)
        return cls(**kwargs)

    def _resolve_type_spec(self, spec: dict[str, object]) -> type:
        spec_dict = self._require_dict(spec, "type")
        import_ref_raw = spec_dict.get("import")
        if import_ref_raw is None:
            message = "type.import is required (no builtin mapping table)"
            raise ValueError(message)
        import_ref = self._require_str(import_ref_raw, "type.import")
        t = self._import_symbol(import_ref)
        if not isinstance(t, type):
            message = f"Imported symbol is not a type: {import_ref}"
            raise TypeError(message)
        return t

    def _apply_transpilers(self, items: list[object]) -> None:
        for item in items:
            item_dict = self._require_dict(item, "each transpiler item")
            lib = self._require_str(item_dict.get("lib"), "transpilers[].lib")
            allow_override = self._require_bool(
                item_dict.get("allow_override", False),
                "transpilers[].allow_override",
            )
            factory = self._require_dict(
                item_dict.get("factory"),
                "transpilers[].factory",
            )
            transpiler = self._instantiate_factory(factory)
            self.register_transpiler(lib, transpiler, allow_override=allow_override)

    def _apply_program_converters(self, items: list[object]) -> None:
        for item in items:
            item_dict = self._require_dict(item, "each program_converter item")
            src = self._require_str(item_dict.get("from"), "program_converters[].from")
            dst = self._require_str(item_dict.get("to"), "program_converters[].to")
            allow_override = self._require_bool(
                item_dict.get("allow_override", False),
                "program_converters[].allow_override",
            )
            factory = self._require_dict(
                item_dict.get("factory"),
                "program_converters[].factory",
            )
            conv = self._instantiate_factory(factory)
            if not isinstance(conv, ProgramConverter):
                message = "factory must create a ProgramConverter"
                raise TypeError(message)
            self.register_program_converter(
                src,
                dst,
                conv,
                allow_override=allow_override,
            )

    def _apply_device_converters(self, items: list[object]) -> None:
        for item in items:
            item_dict = self._require_dict(item, "each device_converter item")
            src = self._require_str(item_dict.get("from"), "device_converters[].from")
            dst = self._require_str(item_dict.get("to"), "device_converters[].to")
            allow_override = self._require_bool(
                item_dict.get("allow_override", False),
                "device_converters[].allow_override",
            )
            factory = self._require_dict(
                item_dict.get("factory"),
                "device_converters[].factory",
            )
            conv = self._instantiate_factory(factory)
            if not isinstance(conv, DeviceConverter):
                message = "factory must create a DeviceConverter"
                raise TypeError(message)
            self.register_device_converter(
                src,
                dst,
                conv,
                allow_override=allow_override,
            )

    def _apply_program_types(self, items: list[object]) -> None:
        for item in items:
            item_dict = self._require_dict(item, "each program_type item")
            lib = self._require_str(item_dict.get("lib"), "program_types[].lib")
            allow_override = self._require_bool(
                item_dict.get("allow_override", False),
                "program_types[].allow_override",
            )
            type_spec = self._require_dict(
                item_dict.get("type"),
                "program_types[].type",
            )
            program_type = self._resolve_type_spec(type_spec)
            self.register_program_type(lib, program_type, allow_override=allow_override)

    def _apply_device_types(self, items: list[object]) -> None:
        for item in items:
            item_dict = self._require_dict(item, "each device_type item")
            lib = self._require_str(item_dict.get("lib"), "device_types[].lib")
            allow_override = self._require_bool(
                item_dict.get("allow_override", False),
                "device_types[].allow_override",
            )
            type_spec = self._require_dict(
                item_dict.get("type"),
                "device_types[].type",
            )
            device_type = self._resolve_type_spec(type_spec)
            self.register_device_type(lib, device_type, allow_override=allow_override)

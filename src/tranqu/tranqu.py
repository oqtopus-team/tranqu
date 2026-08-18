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
import yaml  # type: ignore[import-untyped]


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

        self._config_log = self._empty_config_log()

        if config_path is None:
            self._register_builtins()
        else:
            self.load(config_path=config_path)

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
        self._config_log["transpilers"][transpiler_lib] = {
            "class": self._class_path(transpiler),
            "args": self._infer_constructor_args(transpiler),
        }

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
        key = (from_program_lib, to_program_lib)
        self._config_log["program_converters"][key] = {
            "from": from_program_lib,
            "to": to_program_lib,
            "class": self._class_path(converter),
            "args": self._infer_constructor_args(converter),
        }

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
        key = (from_device_lib, to_device_lib)
        self._config_log["device_converters"][key] = {
            "from": from_device_lib,
            "to": to_device_lib,
            "class": self._class_path(converter),
            "args": self._infer_constructor_args(converter),
        }

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
        self._config_log["program_types"][program_lib] = {
            "type": self._class_path(program_type),
        }

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
            To register Qiskit's Backend type:
                tranqu.register_device_type("qiskit", BackendV2)

        """
        self._device_type_manager.register_type(
            device_lib,
            device_type,
            allow_override=allow_override,
        )
        self._config_log["device_types"][device_lib] = {
            "type": self._class_path(device_type),
        }

    def _register_builtins(self) -> None:
        self._register_builtin_program_converters()
        self._register_builtin_device_converters()
        self._register_builtin_transpilers()
        self._register_builtin_program_types()
        self._register_builtin_device_types()

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

    def _reset_registration_state(self) -> None:
        self._program_converter_manager = ProgramConverterManager()
        self._device_converter_manager = DeviceConverterManager()
        self._transpiler_manager = TranspilerManager()
        self._program_type_manager = ProgramTypeManager()
        self._device_type_manager = DeviceTypeManager()
        self._config_log = self._empty_config_log()
        self._default_transpile = {
            "program_lib": None,
            "transpiler_lib": None,
            "transpiler_options": None,
        }
        self._loaded_config = None
        self._loaded_config_path = None

    def _apply_config(self, config: dict[str, Any]) -> None:
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

        self._apply_transpilers(
            self._require_dict(
                config.get("transpilers", {}),
                "transpilers",
            )
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
            self._require_dict(
                config.get("program_types", {}),
                "program_types",
            )
        )
        self._apply_device_types(
            self._require_dict(
                config.get("device_types", {}),
                "device_types",
            )
        )

        default_lib = config.get("default_transpiler_lib")
        if default_lib is not None:
            self.register_default_transpiler_lib(
                self._require_str(
                    default_lib,
                    "default_transpiler_lib",
                )
            )

    def _replace_registration_state(self, other: Tranqu) -> None:
        self._program_converter_manager = other._program_converter_manager
        self._device_converter_manager = other._device_converter_manager
        self._transpiler_manager = other._transpiler_manager
        self._program_type_manager = other._program_type_manager
        self._device_type_manager = other._device_type_manager

        self._config_log = other._config_log
        self._default_transpile = other._default_transpile
        self._loaded_config = other._loaded_config
        self._loaded_config_path = other._loaded_config_path

    def load(self, *, config_path: str | Path) -> None:
        """Load configuration from a YAML file."""
        config = self._read_yaml(config_path)

        candidate = Tranqu()
        candidate._reset_registration_state()
        candidate._apply_config(config)

        candidate._loaded_config = copy.deepcopy(config)
        candidate._loaded_config_path = Path(config_path)

        self._replace_registration_state(candidate)

    @staticmethod
    def _serialize_transpilers(
        entries: dict[str, dict[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        result: dict[str, dict[str, Any]] = {}

        for lib, entry in entries.items():
            item: dict[str, Any] = {
                "class": entry["class"],
            }

            if entry["args"]:
                item["args"] = copy.deepcopy(entry["args"])

            result[lib] = item
        return result

    @staticmethod
    def _serialize_types(
        entries: dict[str, dict[str, Any]],
    ) -> dict[str, dict[str, str]]:
        return {lib: {"type": entry["type"]} for lib, entry in entries.items()}

    @staticmethod
    def _serialize_converters(
        entries: dict[tuple[str, str], dict[str, Any]],
    ) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []

        for entry in entries.values():
            item: dict[str, Any] = {
                "from": entry["from"],
                "to": entry["to"],
                "class": entry["class"],
            }

            if entry["args"]:
                item["args"] = copy.deepcopy(entry["args"])

            result.append(item)
        return result

    def _build_save_config(self) -> dict[str, Any]:
        config: dict[str, Any] = {
            "program_converters": self._serialize_converters(
                self._config_log["program_converters"]
            ),
            "device_converters": self._serialize_converters(
                self._config_log["device_converters"]
            ),
            "transpilers": self._serialize_transpilers(self._config_log["transpilers"]),
            "program_types": self._serialize_types(self._config_log["program_types"]),
            "device_types": self._serialize_types(self._config_log["device_types"]),
        }

        if any(value is not None for value in self._default_transpile.values()):
            config["default_transpile"] = copy.deepcopy(self._default_transpile)

        default_transpiler_lib = self._config_log["default_transpiler_lib"]
        if default_transpiler_lib is not None:
            config["default_transpiler_lib"] = default_transpiler_lib

        return config

    def save(self, *, config_path: str | Path) -> None:
        """Save all registered objects, including built-ins, to a YAML file."""
        self._write_yaml(
            config_path,
            self._build_save_config(),
        )

    @staticmethod
    def _empty_config_log() -> dict[str, Any]:
        return {
            "default_transpiler_lib": None,
            "program_converters": {},
            "device_converters": {},
            "transpilers": {},
            "program_types": {},
            "device_types": {},
        }

    @staticmethod
    def _class_path(value: object | type[Any]) -> str:
        cls = value if isinstance(value, type) else type(value)

        if cls is QuantumCircuit:
            return "qiskit.QuantumCircuit"
        if cls is Circuit:
            return "pytket.Circuit"
        if cls is BackendV2:
            return "qiskit.providers.BackendV2"

        module = cls.__module__

        if module.startswith("tranqu.program_converter."):
            module = "tranqu.program_converter"
        elif module.startswith("tranqu.device_converter."):
            module = "tranqu.device_converter"
        elif module.startswith("tranqu.transpiler."):
            module = "tranqu.transpiler"

        return f"{module}.{cls.__qualname__}"

    @staticmethod
    def _infer_constructor_args(value: object) -> dict[str, Any]:
        program_lib = getattr(value, "program_lib", None)
        if isinstance(program_lib, str):
            return {"program_lib": program_lib}

        return {}

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
        if ":" in ref:
            mod_name, sym = ref.split(":", 1)
        else:
            mod_name, sym = ref.rsplit(".", 1)

        allowed_prefixes = ("tranqu.", "qiskit", "pytket")
        if not mod_name.startswith(allowed_prefixes):
            message = f"Import is not allowed: {mod_name}"
            raise ValueError(message)

        mod = importlib.import_module(mod_name)
        return getattr(mod, sym)

    def _instantiate_class_spec(self, spec: dict[str, object]) -> Any:  # noqa: ANN401
        class_path = self._require_str(spec.get("class"), "class")
        args = self._require_dict(spec.get("args", {}), "args")

        cls = self._import_symbol(class_path)
        return cls(**args)

    def _resolve_type_spec(self, spec: object) -> type:
        type_path = self._require_str(spec, "type")
        resolved = self._import_symbol(type_path)

        if not isinstance(resolved, type):
            message = f"Imported symbol is not a type: {type_path}"
            raise TypeError(message)

        return resolved

    def _apply_transpilers(self, items: dict[str, object]) -> None:
        for lib, raw_spec in items.items():
            spec = self._require_dict(raw_spec, f"transpilers.{lib}")
            transpiler = self._instantiate_class_spec(spec)

            self.register_transpiler(lib, transpiler)

            self._config_log["transpilers"][lib] = {
                "class": self._require_str(
                    spec.get("class"), f"transpilers.{lib}.class"
                ),
                "args": self._require_dict(
                    spec.get("args", {}), f"transpilers.{lib}.args"
                ),
            }

    def _apply_program_converters(self, items: list[object]) -> None:
        for item in items:
            spec = self._require_dict(item, "each program_converter item")

            src = self._require_str(spec.get("from"), "program_converters[].from")
            dst = self._require_str(spec.get("to"), "program_converters[].to")
            converter = self._instantiate_class_spec(spec)

            if not isinstance(converter, ProgramConverter):
                message = "class must create a ProgramConverter"
                raise TypeError(message)

            self.register_program_converter(src, dst, converter)

            key = (src, dst)
            self._config_log["program_converters"][key] = {
                "from": src,
                "to": dst,
                "class": self._require_str(
                    spec.get("class"), "program_converters[].class"
                ),
                "args": self._require_dict(
                    spec.get("args", {}), "program_converters[].args"
                ),
            }

    def _apply_device_converters(self, items: list[object]) -> None:
        for item in items:
            spec = self._require_dict(
                item,
                "each device_converter item",
            )

            src = self._require_str(
                spec.get("from"),
                "device_converters[].from",
            )
            dst = self._require_str(
                spec.get("to"),
                "device_converters[].to",
            )
            converter = self._instantiate_class_spec(spec)

            if not isinstance(converter, DeviceConverter):
                message = "class must create a DeviceConverter"
                raise TypeError(message)

            self.register_device_converter(
                src,
                dst,
                converter,
            )

            key = (src, dst)
            self._config_log["device_converters"][key] = {
                "from": src,
                "to": dst,
                "class": self._require_str(
                    spec.get("class"),
                    "device_converters[].class",
                ),
                "args": copy.deepcopy(
                    self._require_dict(
                        spec.get("args", {}),
                        "device_converters[].args",
                    )
                ),
            }

    def _apply_program_types(self, items: dict[str, object]) -> None:
        for lib, raw_spec in items.items():
            spec = self._require_dict(raw_spec, f"program_types.{lib}")
            program_type = self._resolve_type_spec(spec.get("type"))

            self.register_program_type(lib, program_type)

            self._config_log["program_types"][lib] = {
                "type": self._require_str(
                    spec.get("type"), f"program_types.{lib}.type"
                ),
            }

    def _apply_device_types(self, items: dict[str, object]) -> None:
        for lib, raw_spec in items.items():
            spec = self._require_dict(
                raw_spec,
                f"device_types.{lib}",
            )
            type_path = self._require_str(
                spec.get("type"),
                f"device_types.{lib}.type",
            )
            device_type = self._resolve_type_spec(type_path)

            self.register_device_type(
                lib,
                device_type,
            )

            self._config_log["device_types"][lib] = {
                "type": type_path,
            }

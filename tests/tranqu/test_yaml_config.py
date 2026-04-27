from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
import yaml
from qiskit import QuantumCircuit  # type: ignore[import-untyped]
from qiskit.providers import BackendV2  # type: ignore[import-untyped]

from tranqu.device_converter import DeviceConverter
from tranqu.program_converter import ProgramConverter
from tranqu.tranqu import Tranqu

# aaa

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path


class DummyProgramConverter(ProgramConverter):
    def convert(self, program: object, _device: object | None = None) -> object:
        return program


class DummyDeviceConverter(DeviceConverter):
    def convert(self, device: object) -> object:
        return device


class SpyRecords:
    def __init__(self) -> None:
        self.program_converters: list[tuple[str, str, ProgramConverter, bool]] = []
        self.device_converters: list[tuple[str, str, DeviceConverter, bool]] = []
        self.device_types: list[tuple[str, type, bool]] = []
        self.transpilers: list[tuple[str, object, bool]] = []


class DummyTranspiler:
    pass


def make_spy_register_program_converter(
    records: SpyRecords,
) -> Callable[..., None]:
    original = Tranqu.register_program_converter

    def spy_register_program_converter(
        self: Tranqu,
        from_program_lib: str,
        to_program_lib: str,
        converter: ProgramConverter,
        *,
        allow_override: bool = False,
    ) -> None:
        records.program_converters.append((
            from_program_lib,
            to_program_lib,
            converter,
            allow_override,
        ))
        original(
            self,
            from_program_lib,
            to_program_lib,
            converter,
            allow_override=allow_override,
        )

    return spy_register_program_converter


def make_spy_register_device_converter(
    records: SpyRecords,
) -> Callable[..., None]:
    original = Tranqu.register_device_converter

    def spy_register_device_converter(
        self: Tranqu,
        from_device_lib: str,
        to_device_lib: str,
        converter: DeviceConverter,
        *,
        allow_override: bool = False,
    ) -> None:
        records.device_converters.append((
            from_device_lib,
            to_device_lib,
            converter,
            allow_override,
        ))
        original(
            self,
            from_device_lib,
            to_device_lib,
            converter,
            allow_override=allow_override,
        )

    return spy_register_device_converter


def make_spy_register_device_type(
    records: SpyRecords,
) -> Callable[..., None]:
    original = Tranqu.register_device_type

    def spy_register_device_type(
        self: Tranqu,
        device_lib: str,
        device_type: type,
        *,
        allow_override: bool = False,
    ) -> None:
        records.device_types.append((device_lib, device_type, allow_override))
        original(
            self,
            device_lib,
            device_type,
            allow_override=allow_override,
        )

    return spy_register_device_type


def make_spy_register_transpiler(records: SpyRecords) -> Callable[..., None]:
    original = Tranqu.register_transpiler

    def spy_register_transpiler(
        self: Tranqu,
        transpiler_lib: str,
        transpiler: object,
        *,
        allow_override: bool = False,
    ) -> None:
        records.transpilers.append((transpiler_lib, transpiler, allow_override))
        original(
            self,
            transpiler_lib,
            transpiler,
            allow_override=allow_override,
        )

    return spy_register_transpiler


def assert_custom_converters_and_device_type_records(records: SpyRecords) -> None:
    assert records.transpilers
    transpiler_lib, transpiler, transpiler_allow_override = records.transpilers[-1]
    assert transpiler_lib == "dummy"
    assert isinstance(transpiler, DummyTranspiler)
    assert transpiler_allow_override is True

    assert records.program_converters
    program_src, program_dst, program_converter, program_allow_override = (
        records.program_converters[-1]
    )
    assert program_src == "qiskit"
    assert program_dst == "dummy"
    assert isinstance(program_converter, DummyProgramConverter)
    assert program_allow_override is True

    assert records.device_converters
    device_src, device_dst, device_converter, device_allow_override = (
        records.device_converters[-1]
    )
    assert device_src == "qiskit"
    assert device_dst == "dummy"
    assert isinstance(device_converter, DummyDeviceConverter)
    assert device_allow_override is True

    assert records.device_types
    lib, device_type, allow_override = records.device_types[-1]
    assert lib == "qiskit"
    assert device_type.__name__ == "BackendV2"
    assert allow_override is True


def test_load_with_use_builtins_true(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
use_builtins: true
""".strip(),
        encoding="utf-8",
    )

    tranqu = Tranqu()
    tranqu.load(config_path=config_path, reset=True)

    assert tranqu._loaded_config is not None  # noqa: SLF001
    assert tranqu._loaded_config["use_builtins"] is True  # noqa: SLF001


def test_load_with_default_transpile(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
use_builtins: true
default_transpile:
  program_lib: qiskit
  transpiler_lib: qiskit
  transpiler_options:
    optimization_level: 2
    seed_transpiler: 123
""".strip(),
        encoding="utf-8",
    )

    tranqu = Tranqu()
    tranqu.load(config_path=config_path, reset=True)

    assert tranqu._default_transpile["program_lib"] == "qiskit"  # noqa: SLF001
    assert tranqu._default_transpile["transpiler_lib"] == "qiskit"  # noqa: SLF001
    assert tranqu._default_transpile["transpiler_options"] == {  # noqa: SLF001
        "optimization_level": 2,
        "seed_transpiler": 123,
    }


def test_save_preserves_loaded_yaml(tmp_path: Path) -> None:
    src_path = tmp_path / "input.yaml"
    dst_path = tmp_path / "output.yaml"

    src_path.write_text(
        """
use_builtins: true
default_transpiler_lib: qiskit
default_transpile:
  program_lib: qiskit
  transpiler_lib: qiskit
  transpiler_options:
    optimization_level: 1
""".strip(),
        encoding="utf-8",
    )

    tranqu = Tranqu(config_path=src_path)
    tranqu.save(config_path=dst_path)

    with dst_path.open("r", encoding="utf-8") as f:
        saved = yaml.safe_load(f)

    assert saved["use_builtins"] is True
    assert saved["default_transpiler_lib"] == "qiskit"
    assert saved["default_transpile"] == {
        "program_lib": "qiskit",
        "transpiler_lib": "qiskit",
        "transpiler_options": {
            "optimization_level": 1,
        },
    }


def test_save_reflects_updated_default_transpiler_lib(tmp_path: Path) -> None:
    src_path = tmp_path / "input.yaml"
    dst_path = tmp_path / "output.yaml"

    src_path.write_text(
        """
use_builtins: true
""".strip(),
        encoding="utf-8",
    )

    tranqu = Tranqu(config_path=src_path)
    tranqu.register_default_transpiler_lib("qiskit", allow_override=True)
    tranqu.save(config_path=dst_path)

    with dst_path.open("r", encoding="utf-8") as f:
        saved = yaml.safe_load(f)

    assert saved["default_transpiler_lib"] == "qiskit"


def test_save_without_loaded_config_writes_builtin_default(tmp_path: Path) -> None:
    dst_path = tmp_path / "output.yaml"

    tranqu = Tranqu()
    tranqu.save(config_path=dst_path)

    with dst_path.open("r", encoding="utf-8") as f:
        saved = yaml.safe_load(f)

    assert saved == {"use_builtins": True}


def test_load_rejects_non_bool_use_builtins(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
use_builtins: 1
""".strip(),
        encoding="utf-8",
    )

    tranqu = Tranqu()
    with pytest.raises(TypeError, match=r"use_builtins must be a bool"):
        tranqu.load(config_path=config_path, reset=True)


def test_load_rejects_non_bool_allow_override_in_program_types(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
program_types:
  - lib: qiskit
    allow_override: 0
    type:
      import: qiskit.circuit:QuantumCircuit
""".strip(),
        encoding="utf-8",
    )

    tranqu = Tranqu()
    with pytest.raises(
        TypeError,
        match=r"program_types\[\]\.allow_override must be a bool",
    ):
        tranqu.load(config_path=config_path, reset=True)


def test_load_rejects_non_bool_allow_override_in_program_converters(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
program_converters:
  - from: a
    to: b
    allow_override: 1
    factory:
      import: tranqu.tranqu:Tranqu
""".strip(),
        encoding="utf-8",
    )

    tranqu = Tranqu()
    with pytest.raises(
        TypeError,
        match=r"program_converters\[\]\.allow_override must be a bool",
    ):
        tranqu.load(config_path=config_path, reset=True)


def test_load_rejects_non_bool_allow_override_in_device_converters(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
device_converters:
  - from: a
    to: b
    allow_override: 1
    factory:
      import: tranqu.tranqu:Tranqu
""".strip(),
        encoding="utf-8",
    )

    tranqu = Tranqu()
    with pytest.raises(
        TypeError,
        match=r"device_converters\[\]\.allow_override must be a bool",
    ):
        tranqu.load(config_path=config_path, reset=True)


def test_load_rejects_non_bool_allow_override_in_device_types(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
device_types:
  - lib: qiskit
    allow_override: 1
    type:
      import: qiskit.providers:BackendV2
""".strip(),
        encoding="utf-8",
    )

    tranqu = Tranqu()
    with pytest.raises(
        TypeError,
        match=r"device_types\[\]\.allow_override must be a bool",
    ):
        tranqu.load(config_path=config_path, reset=True)


def test_load_rejects_non_str_default_transpiler_lib(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
default_transpiler_lib: 123
""".strip(),
        encoding="utf-8",
    )

    tranqu = Tranqu()
    with pytest.raises(TypeError, match=r"default_transpiler_lib must be a str"):
        tranqu.load(config_path=config_path, reset=True)


def test_load_rejects_non_dict_default_transpile(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
default_transpile: 123
""".strip(),
        encoding="utf-8",
    )

    tranqu = Tranqu()
    with pytest.raises(TypeError, match=r"default_transpile must be a dict"):
        tranqu.load(config_path=config_path, reset=True)


def test_load_rejects_non_dict_default_transpile_options(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
default_transpile:
  transpiler_options: 123
""".strip(),
        encoding="utf-8",
    )

    tranqu = Tranqu()
    with pytest.raises(
        TypeError,
        match=r"default_transpile\.transpiler_options must be a dict or None",
    ):
        tranqu.load(config_path=config_path, reset=True)


def test_load_rejects_non_str_default_transpile_program_lib(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
default_transpile:
  program_lib: 123
""".strip(),
        encoding="utf-8",
    )

    tranqu = Tranqu()
    with pytest.raises(
        TypeError,
        match=r"default_transpile\.program_lib must be a str or None",
    ):
        tranqu.load(config_path=config_path, reset=True)


def test_load_rejects_non_str_default_transpile_transpiler_lib(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
default_transpile:
  transpiler_lib: 123
""".strip(),
        encoding="utf-8",
    )

    tranqu = Tranqu()
    with pytest.raises(
        TypeError,
        match=r"default_transpile\.transpiler_lib must be a str or None",
    ):
        tranqu.load(config_path=config_path, reset=True)


def test_load_rejects_non_list_transpilers(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
transpilers: 123
""".strip(),
        encoding="utf-8",
    )

    tranqu = Tranqu()
    with pytest.raises(TypeError, match=r"transpilers must be a list"):
        tranqu.load(config_path=config_path, reset=True)


def test_load_rejects_non_dict_factory_kwargs(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
transpilers:
  - lib: dummy
    allow_override: false
    factory:
      import: tranqu.transpiler.qiskit_transpiler:QiskitTranspiler
      kwargs: 1
""".strip(),
        encoding="utf-8",
    )

    tranqu = Tranqu()
    with pytest.raises(TypeError, match=r"factory\.kwargs must be a dict"):
        tranqu.load(config_path=config_path, reset=True)


def test_load_rejects_missing_factory_import_in_transpilers(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
transpilers:
  - lib: dummy
    allow_override: false
    factory: {}
""".strip(),
        encoding="utf-8",
    )

    tranqu = Tranqu()
    with pytest.raises(
        ValueError,
        match=r"factory\.import is required \(no builtin mapping table\)",
    ):
        tranqu.load(config_path=config_path, reset=True)


def test_load_rejects_non_str_factory_import(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
transpilers:
  - lib: dummy
    allow_override: false
    factory:
      import: 123
""".strip(),
        encoding="utf-8",
    )

    tranqu = Tranqu()
    with pytest.raises(TypeError, match=r"factory\.import must be a str"):
        tranqu.load(config_path=config_path, reset=True)


def test_load_rejects_invalid_import_ref(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
program_types:
  - lib: bad
    allow_override: false
    type:
      import: qiskit.circuit.QuantumCircuit
""".strip(),
        encoding="utf-8",
    )

    tranqu = Tranqu()
    with pytest.raises(ValueError, match=r"Invalid import ref"):
        tranqu.load(config_path=config_path, reset=True)


def test_load_rejects_disallowed_import_prefix(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
program_types:
  - lib: bad
    allow_override: false
    type:
      import: os:path
""".strip(),
        encoding="utf-8",
    )

    tranqu = Tranqu()
    with pytest.raises(ValueError, match=r"Import is not allowed"):
        tranqu.load(config_path=config_path, reset=True)


def test_load_rejects_non_type_import_in_program_types(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
program_types:
  - lib: bad
    allow_override: false
    type:
      import: qiskit.circuit:library
""".strip(),
        encoding="utf-8",
    )

    tranqu = Tranqu()
    with pytest.raises(TypeError, match=r"Imported symbol is not a type"):
        tranqu.load(config_path=config_path, reset=True)


def test_load_rejects_missing_type_import_in_device_types(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
device_types:
  - lib: qiskit
    allow_override: false
    type: {}
""".strip(),
        encoding="utf-8",
    )

    tranqu = Tranqu()
    with pytest.raises(
        ValueError,
        match=r"type\.import is required \(no builtin mapping table\)",
    ):
        tranqu.load(config_path=config_path, reset=True)


def test_load_rejects_non_program_converter_factory_result(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
program_converters:
  - from: qiskit
    to: dummy
    allow_override: false
    factory:
      import: tranqu.tranqu:Tranqu
""".strip(),
        encoding="utf-8",
    )

    tranqu = Tranqu()
    with pytest.raises(TypeError, match=r"factory must create a ProgramConverter"):
        tranqu.load(config_path=config_path, reset=True)


def test_load_rejects_non_device_converter_factory_result(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
device_converters:
  - from: qiskit
    to: dummy
    allow_override: false
    factory:
      import: tranqu.tranqu:Tranqu
""".strip(),
        encoding="utf-8",
    )

    tranqu = Tranqu()
    with pytest.raises(TypeError, match=r"factory must create a DeviceConverter"):
        tranqu.load(config_path=config_path, reset=True)


def test_round_trip_with_program_type_registration(tmp_path: Path) -> None:
    src_path = tmp_path / "input.yaml"
    dst_path = tmp_path / "output.yaml"

    src_path.write_text(
        """
use_builtins: false
program_types:
  - lib: qiskit
    allow_override: false
    type:
      import: qiskit.circuit:QuantumCircuit
""".strip(),
        encoding="utf-8",
    )

    tranqu = Tranqu()
    tranqu.load(config_path=src_path, reset=True)
    tranqu.save(config_path=dst_path)

    with dst_path.open("r", encoding="utf-8") as f:
        saved = yaml.safe_load(f)

    assert saved["use_builtins"] is False
    assert saved["program_types"] == [
        {
            "lib": "qiskit",
            "allow_override": False,
            "type": {
                "import": "qiskit.circuit:QuantumCircuit",
            },
        }
    ]


def test_load_registers_custom_program_and_device_converters_and_device_type(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
use_builtins: false
program_converters:
  - from: qiskit
    to: dummy
    allow_override: true
    factory:
      import: tranqu.test_yaml_config:DummyProgramConverter
device_converters:
  - from: qiskit
    to: dummy
    allow_override: true
    factory:
      import: tranqu.test_yaml_config:DummyDeviceConverter
device_types:
  - lib: qiskit
    allow_override: true
    type:
      import: qiskit.providers:BackendV2
transpilers:
  - lib: dummy
    allow_override: true
    factory:
      import: tranqu.test_yaml_config:DummyTranspiler
""".strip(),
        encoding="utf-8",
    )

    records = SpyRecords()

    def fake_import_symbol(ref: str) -> object:
        if ref == "tranqu.test_yaml_config:DummyProgramConverter":
            return DummyProgramConverter
        if ref == "tranqu.test_yaml_config:DummyDeviceConverter":
            return DummyDeviceConverter
        if ref == "tranqu.test_yaml_config:DummyTranspiler":
            return DummyTranspiler
        if ref == "qiskit.providers:BackendV2":
            return BackendV2
        pytest.fail(f"unexpected import ref: {ref}")

    monkeypatch.setattr(Tranqu, "_import_symbol", staticmethod(fake_import_symbol))
    monkeypatch.setattr(
        Tranqu,
        "register_program_converter",
        make_spy_register_program_converter(records),
    )
    monkeypatch.setattr(
        Tranqu,
        "register_device_converter",
        make_spy_register_device_converter(records),
    )
    monkeypatch.setattr(
        Tranqu,
        "register_device_type",
        make_spy_register_device_type(records),
    )
    monkeypatch.setattr(
        Tranqu,
        "register_transpiler",
        make_spy_register_transpiler(records),
    )

    tranqu = Tranqu()
    tranqu.load(config_path=config_path, reset=True)

    assert_custom_converters_and_device_type_records(records)


def test_read_yaml_rejects_non_mapping_root(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text("- item\n", encoding="utf-8")

    with pytest.raises(TypeError, match=r"YAML root must be a mapping/dict"):
        Tranqu().load(config_path=config_path, reset=True)


def test_transpile_uses_default_program_and_transpiler_lib(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tranqu = Tranqu()
    tranqu._default_transpile = {  # noqa: SLF001
        "program_lib": "qiskit",
        "transpiler_lib": "qiskit",
        "transpiler_options": {"optimization_level": 1},
    }

    captured: dict[str, object] = {}

    def fake_dispatch(*args: object) -> dict[str, object]:
        (
            _,
            program,
            program_lib,
            transpiler_lib,
            transpiler_options,
            device,
            device_lib,
        ) = args
        captured["program"] = program
        captured["program_lib"] = program_lib
        captured["transpiler_lib"] = transpiler_lib
        captured["transpiler_options"] = transpiler_options
        captured["device"] = device
        captured["device_lib"] = device_lib
        return {"ok": True}

    monkeypatch.setattr(
        "tranqu.tranqu.TranspilerDispatcher.dispatch",
        fake_dispatch,
    )

    circuit = QuantumCircuit(2)
    circuit.h(0)
    circuit.cx(0, 1)

    result = tranqu.transpile(program=circuit)

    assert result == {"ok": True}
    assert captured["program"] is circuit
    assert captured["program_lib"] == "qiskit"
    assert captured["transpiler_lib"] == "qiskit"
    assert captured["transpiler_options"] == {"optimization_level": 1}
    assert captured["device"] is None
    assert captured["device_lib"] is None


def test_transpile_merges_default_transpiler_options(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tranqu = Tranqu()
    tranqu._default_transpile = {  # noqa: SLF001
        "program_lib": "qiskit",
        "transpiler_lib": "qiskit",
        "transpiler_options": {"optimization_level": 1},
    }

    captured: dict[str, object] = {}

    def fake_dispatch(*args: object) -> dict[str, object]:
        (
            _,
            program,
            program_lib,
            transpiler_lib,
            transpiler_options,
            device,
            device_lib,
        ) = args
        captured["program"] = program
        captured["program_lib"] = program_lib
        captured["transpiler_lib"] = transpiler_lib
        captured["transpiler_options"] = transpiler_options
        captured["device"] = device
        captured["device_lib"] = device_lib
        return {"ok": True}

    monkeypatch.setattr(
        "tranqu.tranqu.TranspilerDispatcher.dispatch",
        fake_dispatch,
    )

    circuit = QuantumCircuit(2)
    circuit.h(0)
    circuit.cx(0, 1)

    result = tranqu.transpile(
        program=circuit,
        transpiler_options={"seed_transpiler": 123},
    )

    assert result == {"ok": True}
    assert captured["program"] is circuit
    assert captured["program_lib"] == "qiskit"
    assert captured["transpiler_lib"] == "qiskit"
    assert captured["transpiler_options"] == {
        "optimization_level": 1,
        "seed_transpiler": 123,
    }
    assert captured["device"] is None
    assert captured["device_lib"] is None


def test_transpile_copies_default_transpiler_options(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tranqu = Tranqu()
    default_options = {"optimization_level": 1}
    tranqu._default_transpile = {  # noqa: SLF001
        "program_lib": "qiskit",
        "transpiler_lib": "qiskit",
        "transpiler_options": default_options,
    }

    captured: dict[str, object] = {}

    def fake_dispatch(*args: object) -> dict[str, object]:
        captured["transpiler_options"] = args[4]
        return {"ok": True}

    monkeypatch.setattr(
        "tranqu.tranqu.TranspilerDispatcher.dispatch",
        fake_dispatch,
    )

    circuit = QuantumCircuit(1)
    result = tranqu.transpile(program=circuit)

    assert result == {"ok": True}
    assert captured["transpiler_options"] == {"optimization_level": 1}
    assert captured["transpiler_options"] is not default_options

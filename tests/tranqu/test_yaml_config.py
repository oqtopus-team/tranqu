from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
import yaml  # type: ignore[import]

from tranqu.program_converter.program_converter import ProgramConverter
from tranqu.tranqu import Tranqu

if TYPE_CHECKING:
    from pathlib import Path


class ProgramConverterWithArgs(ProgramConverter):
    def __init__(self, program_lib: str) -> None:
        self.program_lib = program_lib

    def convert(self, program: Any) -> Any:
        return program


def _write_yaml(path: Path, data: object) -> None:
    path.write_text(
        yaml.safe_dump(
            data,
            sort_keys=False,
            allow_unicode=True,
        ),
        encoding="utf-8",
    )


def _read_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file)

    assert isinstance(data, dict)
    return data


def _minimal_qiskit_transpiler_config() -> dict[str, object]:
    return {
        "program_converters": [],
        "device_converters": [],
        "transpilers": {
            "qiskit": {
                "class": "tranqu.transpiler.QiskitTranspiler",
                "args": {
                    "program_lib": "qiskit",
                },
            },
        },
        "program_types": {},
        "device_types": {},
    }


def test_save_writes_all_builtin_registrations(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"

    Tranqu().save(config_path=config_path)

    saved = _read_yaml(config_path)

    assert len(saved["program_converters"]) == 8
    assert len(saved["device_converters"]) == 4
    assert len(saved["transpilers"]) == 3
    assert len(saved["program_types"]) == 2
    assert len(saved["device_types"]) == 1


def test_save_does_not_write_use_builtins(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"

    Tranqu().save(config_path=config_path)

    saved = _read_yaml(config_path)

    assert "use_builtins" not in saved


def test_save_does_not_write_unconfigured_default_transpiler(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "config.yaml"

    Tranqu().save(config_path=config_path)

    saved = _read_yaml(config_path)

    assert "default_transpiler_lib" not in saved


def test_save_writes_registered_default_transpiler(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"

    tranqu = Tranqu()
    tranqu.register_default_transpiler_lib("tket")
    tranqu.save(config_path=config_path)

    saved = _read_yaml(config_path)

    assert saved["default_transpiler_lib"] == "tket"


def test_saved_program_converter_format(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"

    Tranqu().save(config_path=config_path)

    saved = _read_yaml(config_path)
    converters = saved["program_converters"]

    assert isinstance(converters, list)
    assert converters[0] == {
        "from": "openqasm3",
        "to": "qiskit",
        "class": ("tranqu.program_converter.Openqasm3ToQiskitProgramConverter"),
    }


def test_saved_device_converter_format(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"

    Tranqu().save(config_path=config_path)

    saved = _read_yaml(config_path)
    converters = saved["device_converters"]

    assert isinstance(converters, list)
    assert converters[0] == {
        "from": "oqtopus",
        "to": "qiskit",
        "class": ("tranqu.device_converter.OqtoqusToQiskitDeviceConverter"),
    }


def test_saved_transpiler_format(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"

    Tranqu().save(config_path=config_path)

    saved = _read_yaml(config_path)

    assert saved["transpilers"]["qiskit"] == {
        "class": "tranqu.transpiler.QiskitTranspiler",
        "args": {
            "program_lib": "qiskit",
        },
    }
    assert saved["transpilers"]["ouqu-tp"] == {
        "class": "tranqu.transpiler.OuquTpTranspiler",
        "args": {
            "program_lib": "openqasm3",
        },
    }
    assert saved["transpilers"]["tket"] == {
        "class": "tranqu.transpiler.TketTranspiler",
        "args": {
            "program_lib": "tket",
        },
    }


def test_saved_program_type_format(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"

    Tranqu().save(config_path=config_path)

    saved = _read_yaml(config_path)

    assert saved["program_types"] == {
        "qiskit": {
            "type": "qiskit.QuantumCircuit",
        },
        "tket": {
            "type": "pytket.Circuit",
        },
    }


def test_saved_device_type_format(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"

    Tranqu().save(config_path=config_path)

    saved = _read_yaml(config_path)

    assert saved["device_types"] == {
        "qiskit": {
            "type": "qiskit.providers.BackendV2",
        },
    }


def test_save_load_save_round_trip(tmp_path: Path) -> None:
    first_path = tmp_path / "first.yaml"
    second_path = tmp_path / "second.yaml"

    Tranqu().save(config_path=first_path)

    loaded = Tranqu(config_path=first_path)
    loaded.save(config_path=second_path)

    assert _read_yaml(first_path) == _read_yaml(second_path)


def test_constructor_with_config_uses_only_yaml_contents(
    tmp_path: Path,
) -> None:
    input_path = tmp_path / "input.yaml"
    output_path = tmp_path / "output.yaml"

    _write_yaml(
        input_path,
        _minimal_qiskit_transpiler_config(),
    )

    tranqu = Tranqu(config_path=input_path)
    tranqu.save(config_path=output_path)

    saved = _read_yaml(output_path)

    assert set(saved["transpilers"]) == {"qiskit"}
    assert saved["program_converters"] == []
    assert saved["device_converters"] == []
    assert saved["program_types"] == {}
    assert saved["device_types"] == {}


def test_load_discards_existing_builtin_registrations(
    tmp_path: Path,
) -> None:
    input_path = tmp_path / "input.yaml"
    output_path = tmp_path / "output.yaml"

    _write_yaml(
        input_path,
        _minimal_qiskit_transpiler_config(),
    )

    tranqu = Tranqu()
    tranqu.load(config_path=input_path)
    tranqu.save(config_path=output_path)

    saved = _read_yaml(output_path)

    assert set(saved["transpilers"]) == {"qiskit"}
    assert saved["program_converters"] == []
    assert saved["device_converters"] == []
    assert saved["program_types"] == {}
    assert saved["device_types"] == {}


def test_load_and_save_default_transpiler_lib(tmp_path: Path) -> None:
    input_path = tmp_path / "input.yaml"
    output_path = tmp_path / "output.yaml"

    config = _minimal_qiskit_transpiler_config()
    config["default_transpiler_lib"] = "qiskit"
    _write_yaml(input_path, config)

    tranqu = Tranqu(config_path=input_path)
    tranqu.save(config_path=output_path)

    saved = _read_yaml(output_path)

    assert saved["default_transpiler_lib"] == "qiskit"


def test_load_program_type(tmp_path: Path) -> None:
    input_path = tmp_path / "input.yaml"
    output_path = tmp_path / "output.yaml"

    _write_yaml(
        input_path,
        {
            "program_types": {
                "qiskit": {
                    "type": "qiskit.QuantumCircuit",
                },
            },
        },
    )

    tranqu = Tranqu(config_path=input_path)
    tranqu.save(config_path=output_path)

    saved = _read_yaml(output_path)

    assert saved["program_types"] == {
        "qiskit": {
            "type": "qiskit.QuantumCircuit",
        },
    }


def test_load_device_type(tmp_path: Path) -> None:
    input_path = tmp_path / "input.yaml"
    output_path = tmp_path / "output.yaml"

    _write_yaml(
        input_path,
        {
            "device_types": {
                "qiskit": {
                    "type": "qiskit.providers.BackendV2",
                },
            },
        },
    )

    tranqu = Tranqu(config_path=input_path)
    tranqu.save(config_path=output_path)

    saved = _read_yaml(output_path)

    assert saved["device_types"] == {
        "qiskit": {
            "type": "qiskit.providers.BackendV2",
        },
    }


def test_load_program_converter(tmp_path: Path) -> None:
    input_path = tmp_path / "input.yaml"
    output_path = tmp_path / "output.yaml"

    converter = {
        "from": "openqasm3",
        "to": "qiskit",
        "class": ("tranqu.program_converter.Openqasm3ToQiskitProgramConverter"),
    }

    _write_yaml(
        input_path,
        {
            "program_converters": [converter],
        },
    )

    tranqu = Tranqu(config_path=input_path)
    tranqu.save(config_path=output_path)

    saved = _read_yaml(output_path)

    assert saved["program_converters"] == [converter]


def test_load_device_converter(tmp_path: Path) -> None:
    input_path = tmp_path / "input.yaml"
    output_path = tmp_path / "output.yaml"

    converter = {
        "from": "qiskit",
        "to": "tket",
        "class": ("tranqu.device_converter.QiskitToTketDeviceConverter"),
    }

    _write_yaml(
        input_path,
        {
            "device_converters": [converter],
        },
    )

    tranqu = Tranqu(config_path=input_path)
    tranqu.save(config_path=output_path)

    saved = _read_yaml(output_path)

    assert saved["device_converters"] == [converter]


def test_load_preserves_transpiler_args(tmp_path: Path) -> None:
    input_path = tmp_path / "input.yaml"
    output_path = tmp_path / "output.yaml"

    config = _minimal_qiskit_transpiler_config()
    _write_yaml(input_path, config)

    tranqu = Tranqu(config_path=input_path)
    tranqu.save(config_path=output_path)

    saved = _read_yaml(output_path)

    assert saved["transpilers"]["qiskit"]["args"] == {
        "program_lib": "qiskit",
    }


def test_load_rejects_non_mapping_yaml_root(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    _write_yaml(config_path, ["not", "a", "mapping"])

    with pytest.raises(
        TypeError,
        match="YAML root must be a mapping/dict",
    ):
        Tranqu(config_path=config_path)


@pytest.mark.parametrize(
    ("field", "invalid_value", "expected_message"),
    [
        (
            "transpilers",
            [],
            "transpilers must be a dict",
        ),
        (
            "program_converters",
            {},
            "program_converters must be a list",
        ),
        (
            "device_converters",
            {},
            "device_converters must be a list",
        ),
        (
            "program_types",
            [],
            "program_types must be a dict",
        ),
        (
            "device_types",
            [],
            "device_types must be a dict",
        ),
    ],
)
def test_load_rejects_invalid_top_level_section_types(
    tmp_path: Path,
    field: str,
    invalid_value: object,
    expected_message: str,
) -> None:
    config_path = tmp_path / "config.yaml"

    _write_yaml(
        config_path,
        {
            field: invalid_value,
        },
    )

    with pytest.raises(TypeError, match=expected_message):
        Tranqu(config_path=config_path)


def test_load_rejects_non_string_transpiler_class(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "config.yaml"

    _write_yaml(
        config_path,
        {
            "transpilers": {
                "qiskit": {
                    "class": 123,
                    "args": {},
                },
            },
        },
    )

    with pytest.raises(TypeError, match="class must be a str"):
        Tranqu(config_path=config_path)


def test_load_rejects_non_dict_transpiler_args(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "config.yaml"

    _write_yaml(
        config_path,
        {
            "transpilers": {
                "qiskit": {
                    "class": "tranqu.transpiler.QiskitTranspiler",
                    "args": 123,
                },
            },
        },
    )

    with pytest.raises(TypeError, match="args must be a dict"):
        Tranqu(config_path=config_path)


def test_load_rejects_program_converter_without_from(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "config.yaml"

    _write_yaml(
        config_path,
        {
            "program_converters": [
                {
                    "to": "qiskit",
                    "class": (
                        "tranqu.program_converter.Openqasm3ToQiskitProgramConverter"
                    ),
                },
            ],
        },
    )

    with pytest.raises(
        TypeError,
        match=r"program_converters\[\]\.from must be a str",
    ):
        Tranqu(config_path=config_path)


def test_load_rejects_device_converter_without_to(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "config.yaml"

    _write_yaml(
        config_path,
        {
            "device_converters": [
                {
                    "from": "qiskit",
                    "class": ("tranqu.device_converter.QiskitToTketDeviceConverter"),
                },
            ],
        },
    )

    with pytest.raises(
        TypeError,
        match=r"device_converters\[\]\.to must be a str",
    ):
        Tranqu(config_path=config_path)


def test_load_rejects_non_converter_program_class(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "config.yaml"

    _write_yaml(
        config_path,
        {
            "program_converters": [
                {
                    "from": "qiskit",
                    "to": "dummy",
                    "class": "tranqu.transpiler.QiskitTranspiler",
                    "args": {
                        "program_lib": "qiskit",
                    },
                },
            ],
        },
    )

    with pytest.raises(
        TypeError,
        match="class must create a ProgramConverter",
    ):
        Tranqu(config_path=config_path)


def test_load_rejects_non_converter_device_class(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "config.yaml"

    _write_yaml(
        config_path,
        {
            "device_converters": [
                {
                    "from": "qiskit",
                    "to": "dummy",
                    "class": "tranqu.transpiler.QiskitTranspiler",
                    "args": {
                        "program_lib": "qiskit",
                    },
                },
            ],
        },
    )

    with pytest.raises(
        TypeError,
        match="class must create a DeviceConverter",
    ):
        Tranqu(config_path=config_path)


def test_load_rejects_non_string_program_type(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "config.yaml"

    _write_yaml(
        config_path,
        {
            "program_types": {
                "qiskit": {
                    "type": 123,
                },
            },
        },
    )

    with pytest.raises(TypeError, match="type must be a str"):
        Tranqu(config_path=config_path)


def test_load_rejects_non_string_device_type(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "config.yaml"

    _write_yaml(
        config_path,
        {
            "device_types": {
                "qiskit": {
                    "type": 123,
                },
            },
        },
    )

    with pytest.raises(
        TypeError,
        match=r"device_types\.qiskit\.type must be a str",
    ):
        Tranqu(config_path=config_path)


def test_load_rejects_non_dict_default_transpile(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "config.yaml"

    _write_yaml(
        config_path,
        {
            "default_transpile": 123,
        },
    )

    with pytest.raises(
        TypeError,
        match="default_transpile must be a dict",
    ):
        Tranqu(config_path=config_path)


def test_load_rejects_non_dict_default_transpiler_options(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "config.yaml"

    _write_yaml(
        config_path,
        {
            "default_transpile": {
                "transpiler_options": 123,
            },
        },
    )

    with pytest.raises(
        TypeError,
        match=(
            r"default_transpile\.transpiler_options "
            r"must be a dict or None"
        ),
    ):
        Tranqu(config_path=config_path)


def test_default_transpile_is_applied(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "config.yaml"

    _write_yaml(
        config_path,
        {
            "default_transpile": {
                "program_lib": "qiskit",
                "transpiler_lib": "qiskit",
                "transpiler_options": {
                    "optimization_level": 2,
                },
            },
        },
    )

    captured: dict[str, object] = {}
    expected_result = object()

    def fake_dispatch(*args: object) -> object:
        (
            _self,
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
        return expected_result

    monkeypatch.setattr(
        "tranqu.tranqu.TranspilerDispatcher.dispatch",
        fake_dispatch,
    )

    program = object()
    tranqu = Tranqu(config_path=config_path)

    result = tranqu.transpile(program)

    assert result is expected_result
    assert captured == {
        "program": program,
        "program_lib": "qiskit",
        "transpiler_lib": "qiskit",
        "transpiler_options": {
            "optimization_level": 2,
        },
        "device": None,
        "device_lib": None,
    }


def test_explicit_transpiler_options_override_defaults(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "config.yaml"

    _write_yaml(
        config_path,
        {
            "default_transpile": {
                "transpiler_options": {
                    "optimization_level": 1,
                    "seed_transpiler": 123,
                },
            },
        },
    )

    captured: dict[str, object] = {}

    def fake_dispatch(
        _self: object,
        _program: object,
        _program_lib: str | None,
        _transpiler_lib: str | None,
        transpiler_options: dict[str, object] | None,
        _device: object | None,
        _device_lib: str | None,
    ) -> object:
        captured["transpiler_options"] = transpiler_options
        return object()

    monkeypatch.setattr(
        "tranqu.tranqu.TranspilerDispatcher.dispatch",
        fake_dispatch,
    )

    tranqu = Tranqu(config_path=config_path)
    tranqu.transpile(
        object(),
        transpiler_options={
            "optimization_level": 3,
        },
    )

    assert captured["transpiler_options"] == {
        "optimization_level": 3,
        "seed_transpiler": 123,
    }


@pytest.mark.parametrize(
    ("field", "expected_message"),
    [
        (
            "program_lib",
            r"default_transpile\.program_lib must be a str or None",
        ),
        (
            "transpiler_lib",
            r"default_transpile\.transpiler_lib must be a str or None",
        ),
    ],
)
def test_load_rejects_non_string_default_transpile_library(
    tmp_path: Path,
    field: str,
    expected_message: str,
) -> None:
    config_path = tmp_path / "config.yaml"

    _write_yaml(
        config_path,
        {
            "default_transpile": {
                field: 123,
            },
        },
    )

    with pytest.raises(TypeError, match=expected_message):
        Tranqu(config_path=config_path)


def test_load_rejects_imported_symbol_that_is_not_type(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "config.yaml"

    _write_yaml(
        config_path,
        {
            "program_types": {
                "invalid": {
                    "type": "qiskit.__version__",
                },
            },
        },
    )

    with pytest.raises(
        TypeError,
        match="Imported symbol is not a type",
    ):
        Tranqu(config_path=config_path)


def test_save_includes_default_transpiler_lib(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"

    tranqu = Tranqu()
    tranqu.register_default_transpiler_lib("tket")
    tranqu.save(config_path=config_path)

    saved = _read_yaml(config_path)

    assert saved["default_transpiler_lib"] == "tket"


def test_load_failure_preserves_existing_state(tmp_path: Path) -> None:
    before_path = tmp_path / "before.yaml"
    invalid_path = tmp_path / "invalid.yaml"
    after_path = tmp_path / "after.yaml"

    tranqu = Tranqu()
    tranqu.register_default_transpiler_lib("tket")
    tranqu.save(config_path=before_path)

    _write_yaml(
        invalid_path,
        {
            "transpilers": {
                "qiskit": {
                    "class": "tranqu.transpiler.QiskitTranspiler",
                    "args": {
                        "program_lib": "qiskit",
                    },
                },
            },
            "program_converters": "invalid",
            "device_converters": [],
            "program_types": {},
            "device_types": {},
        },
    )

    with pytest.raises(
        TypeError,
        match="program_converters must be a list",
    ):
        tranqu.load(config_path=invalid_path)

    tranqu.save(config_path=after_path)

    assert _read_yaml(after_path) == _read_yaml(before_path)


def test_save_converter_includes_args(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"

    tranqu = Tranqu()
    tranqu.register_program_converter(
        "foo",
        "bar",
        ProgramConverterWithArgs(program_lib="foo"),
    )

    tranqu.save(config_path=config_path)

    saved = _read_yaml(config_path)

    converter = next(
        item
        for item in saved["program_converters"]
        if item["from"] == "foo" and item["to"] == "bar"
    )

    assert converter["args"] == {
        "program_lib": "foo",
    }


def test_save_includes_default_transpile(tmp_path: Path) -> None:
    input_path = tmp_path / "input.yaml"
    output_path = tmp_path / "output.yaml"

    _write_yaml(
        input_path,
        {
            "default_transpile": {
                "program_lib": "qiskit",
                "transpiler_lib": "qiskit",
                "transpiler_options": {
                    "optimization_level": 1,
                },
            },
        },
    )

    tranqu = Tranqu(config_path=input_path)
    tranqu.save(config_path=output_path)

    saved = _read_yaml(output_path)

    assert saved["default_transpile"] == {
        "program_lib": "qiskit",
        "transpiler_lib": "qiskit",
        "transpiler_options": {
            "optimization_level": 1,
        },
    }

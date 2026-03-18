# tests/tranqu/test_yaml_config.py

from __future__ import annotations

from pathlib import Path

import pytest

from tranqu.tranqu import Tranqu


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

    assert tranqu._loaded_config is not None
    assert tranqu._loaded_config["use_builtins"] is True


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

    assert tranqu._default_transpile["program_lib"] == "qiskit"
    assert tranqu._default_transpile["transpiler_lib"] == "qiskit"
    assert tranqu._default_transpile["transpiler_options"] == {
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

    saved = Tranqu._read_yaml(dst_path)

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

    saved = Tranqu._read_yaml(dst_path)
    assert saved["default_transpiler_lib"] == "qiskit"


def test_load_rejects_non_bool_use_builtins(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
use_builtins: 1
""".strip(),
        encoding="utf-8",
    )

    tranqu = Tranqu()
    with pytest.raises(TypeError, match="use_builtins must be a bool"):
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


def test_load_rejects_non_str_default_transpiler_lib(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
default_transpiler_lib: 123
""".strip(),
        encoding="utf-8",
    )

    tranqu = Tranqu()
    with pytest.raises(TypeError, match="default_transpiler_lib must be a str"):
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
    with pytest.raises(TypeError, match="default_transpile must be a dict"):
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
        match="default_transpile.transpiler_options must be a dict or None",
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
    with pytest.raises(TypeError, match="transpilers must be a list"):
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
    with pytest.raises(TypeError, match="factory.kwargs must be a dict"):
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
    with pytest.raises(TypeError, match="factory.import must be a str"):
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
    with pytest.raises(ValueError, match="Import is not allowed"):
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

    saved = Tranqu._read_yaml(dst_path)

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

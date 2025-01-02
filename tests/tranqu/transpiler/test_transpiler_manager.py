from typing import Any

import pytest

from tranqu import Tranqu
from tranqu.program_converter import ProgramConverter
from tranqu.transpile_result import TranspileResult
from tranqu.transpiler import (
    DefaultTranspilerLibAlreadyRegisteredError,
    Transpiler,
    TranspilerAlreadyRegisteredError,
    TranspilerManager,
    TranspilerNotFoundError,
)

qasm_code = """
OPENQASM 3.0;
include "stdgates.inc";

qubit q;

h q;
h q;
"""


class NopTranspiler(Transpiler):
    def transpile(
        self,
        program: Any,
        _transpiler_options: dict | None = None,
        _device: Any | None = None,
        _device_lib: str | None = None,
    ) -> TranspileResult:
        return TranspileResult(program, {}, {})


class NopToQasm3Converter(ProgramConverter):
    def convert(self, _program: Any) -> Any:
        return qasm_code


class Qasm3ToNopConverter(ProgramConverter):
    def convert(self, _program: Any) -> Any:
        return "NOP"


class TestTranspilerManager:
    def test_transpile_qasm3_with_nop_transpiler(self):
        tranqu = Tranqu()

        tranqu.register_transpiler("nop", NopTranspiler(program_lib="nop"))
        tranqu.register_program_converter("nop", "openqasm3", NopToQasm3Converter())
        tranqu.register_program_converter("openqasm3", "nop", Qasm3ToNopConverter())
        result = tranqu.transpile(
            qasm_code, program_lib="openqasm3", transpiler_lib="nop"
        )

        assert result.transpiled_program.strip() == qasm_code.strip()

    def test_register_default_transpiler_lib(self):
        manager = TranspilerManager()
        assert manager.get_default_transpiler_lib() == None  # noqa: E711

        manager.register_default_transpiler_lib("nop")
        assert manager.get_default_transpiler_lib() == "nop"

    def test_register_default_transpiler_lib_already_registered(self):
        manager = TranspilerManager()

        manager.register_default_transpiler_lib("nop")

        with pytest.raises(DefaultTranspilerLibAlreadyRegisteredError):
            manager.register_default_transpiler_lib("nop")

    def test_register_default_transpiler_lib_already_registered_allow_override(self):
        manager = TranspilerManager()

        manager.register_default_transpiler_lib("nop")
        manager.register_default_transpiler_lib("nop", allow_override=True)

    def test_register_transpiler_already_registered(self):
        manager = TranspilerManager()

        manager.register_transpiler("nop", NopTranspiler(program_lib="nop"))

        with pytest.raises(TranspilerAlreadyRegisteredError):
            manager.register_transpiler("nop", NopTranspiler(program_lib="nop"))

    def test_fetch_transpiler_not_found(self):
        manager = TranspilerManager()

        with pytest.raises(TranspilerNotFoundError):
            manager.fetch_transpiler("non_existent_transpiler")

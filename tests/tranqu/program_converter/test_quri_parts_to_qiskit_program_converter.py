# mypy: disable-error-code="import-untyped"

from qiskit import QuantumCircuit
from quri_parts.circuit import Program  # type: ignore

from tranqu.program_converter import QuripartsToQiskitProgramConverter


class TestQuripartsToQiskitProgramConverter:
    def setup_method(self):
        self.converter = QuripartsToQiskitProgramConverter()

    def test_convert_valid_program(self):
        program = Program()

        result = self.converter.convert(program)

        assert isinstance(result, QuantumCircuit)

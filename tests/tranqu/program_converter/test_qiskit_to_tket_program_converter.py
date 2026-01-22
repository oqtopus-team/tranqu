# mypy: disable-error-code="import-untyped"

from pytket import Circuit  # type: ignore[attr-defined]
from qiskit import QuantumCircuit  # type: ignore[import-untyped]

from tranqu.program_converter import QiskitToTketProgramConverter


class TestQiskitToTketProgramConverter:
    def setup_method(self):
        self.converter = QiskitToTketProgramConverter()

    def test_convert_valid_qasm3(self):
        circuit = QuantumCircuit(1)
        circuit.h(0)

        result = self.converter.convert(circuit)

        assert isinstance(result, Circuit)

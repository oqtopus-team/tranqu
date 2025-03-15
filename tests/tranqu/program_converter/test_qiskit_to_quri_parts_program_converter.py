# mypy: disable-error-code="import-untyped"

from qiskit import QuantumCircuit
from quri_parts.circuit import Program

from tranqu.program_converter import QiskitToQuripartsProgramConverter


class TestQiskitToQuripartsProgramConverter:
    def setup_method(self):
        self.converter = QiskitToQuripartsProgramConverter()

    def test_convert_valid_qiskit_circuit(self):
        circuit = QuantumCircuit(1)
        circuit.h(0)

        result = self.converter.convert(circuit)

        assert isinstance(result, Program)

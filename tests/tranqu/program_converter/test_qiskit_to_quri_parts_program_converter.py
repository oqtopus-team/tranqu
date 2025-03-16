# mypy: disable-error-code="import-untyped"

from qiskit import QuantumCircuit
from quri_parts.circuit import Program  # type: ignore

from tranqu.program_converter import QiskitToQuriPartsProgramConverter


class TestQiskitToQuriPartsProgramConverter:
    def setup_method(self):
        self.converter = QiskitToQuriPartsProgramConverter()

    def test_convert_valid_qiskit_circuit(self):
        circuit = QuantumCircuit(1)
        circuit.h(0)

        result = self.converter.convert(circuit)

        assert isinstance(result, Program)

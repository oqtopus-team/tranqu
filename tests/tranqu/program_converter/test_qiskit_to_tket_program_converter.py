# mypy: disable-error-code="import-untyped"

from pytket import Circuit as TketCircuit
from qiskit import QuantumCircuit as QiskitCircuit

from tranqu.program_converter import QiskitToTketProgramConverter


class TestQiskitToTketProgramConverter:
    def setup_method(self):
        self.converter = QiskitToTketProgramConverter()

    def test_convert_valid_qasm3(self):
        circuit = QiskitCircuit(1)
        circuit.h(0)

        result = self.converter.convert(circuit)

        assert isinstance(result, TketCircuit)

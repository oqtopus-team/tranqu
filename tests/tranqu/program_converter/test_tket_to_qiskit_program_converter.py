# mypy: disable-error-code="import-untyped"

from pytket import Circuit as TketCircuit
from qiskit import QuantumCircuit as QiskitCircuit

from tranqu.program_converter import TketToQiskitProgramConverter


class TestTketToQiskitProgramConverter:
    def setup_method(self):
        self.converter = TketToQiskitProgramConverter()

    def test_convert_valid_qasm3(self):
        circuit = TketCircuit(1)
        circuit.H(0)

        result = self.converter.convert(circuit)

        assert isinstance(result, QiskitCircuit)

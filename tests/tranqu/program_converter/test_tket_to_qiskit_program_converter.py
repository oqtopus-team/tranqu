# mypy: disable-error-code="import-untyped"

from pytket import Circuit  # type: ignore[attr-defined]
from qiskit import QuantumCircuit  # type: ignore[import-untyped]

from tranqu.program_converter import TketToQiskitProgramConverter


class TestTketToQiskitProgramConverter:
    def setup_method(self):
        self.converter = TketToQiskitProgramConverter()

    def test_convert_valid_qasm3(self):
        circuit = Circuit(1)
        circuit.H(0)

        result = self.converter.convert(circuit)

        assert isinstance(result, QuantumCircuit)

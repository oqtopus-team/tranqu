from qiskit import QuantumCircuit  # type: ignore[import-untyped]

from tranqu.program_converter import QiskitToOuquTpProgramConverter


class TestQiskitToOuquTpProgramConverter:
    def setup_method(self):
        self.converter = QiskitToOuquTpProgramConverter()

    def test_convert(self):
        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.cx(0, 1)

        result = self.converter.convert(circuit)

        expected_code = """
OPENQASM 3.0;
include "stdgates.inc";
qubit[2] q;
h q[0];
cx q[0], q[1];
    """
        assert result.strip() == expected_code.strip()

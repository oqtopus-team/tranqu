from qiskit import QuantumCircuit  # type: ignore[import-untyped]

from tranqu.program_converter.qiskit_to_openqasm3_program_converter import (
    QiskitToOpenqasm3ProgramConverter,
)


class TestQiskitToOpenqasm3ProgramConverter:
    def setup_method(self):
        self.converter = QiskitToOpenqasm3ProgramConverter()

    def test_convert(self):
        circuit = QuantumCircuit(1)
        circuit.h(0)

        result = self.converter.convert(circuit)

        expected_code = """
OPENQASM 3.0;
include "stdgates.inc";
qubit[1] q;
h q[0];
    """
        assert result.strip() == expected_code.strip()

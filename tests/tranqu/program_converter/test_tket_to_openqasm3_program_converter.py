from pytket import Circuit

from tranqu.program_converter import TketToOpenqasm3ProgramConverter


class TestTketToOpenqasm3ProgramConverter:
    def setup_method(self):
        self.converter = TketToOpenqasm3ProgramConverter()

    def test_convert(self):
        circuit = Circuit(1)
        circuit.H(0)

        result = self.converter.convert(circuit)

        expected_code = """
OPENQASM 3.0;
include "stdgates.inc";
qubit[1] q;
h q[0];
    """
        assert result.strip() == expected_code.strip()

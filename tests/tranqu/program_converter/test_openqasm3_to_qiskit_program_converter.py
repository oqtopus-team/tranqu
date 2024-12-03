import pytest
from openqasm3.parser import QASM3ParsingError
from qiskit import QuantumCircuit  # type: ignore[import-untyped]

from tranqu.program_converter import Openqasm3ToQiskitProgramConverter


class TestOpenqasm3ToQiskitProgramConverter:
    def setup_method(self):
        self.converter = Openqasm3ToQiskitProgramConverter()

    def test_convert_valid_openqasm3(self):
        result = self.converter.convert("""
OPENQASM 3.0;
include "stdgates.inc";
qubit[1] q;
h q[0];
        """)

        assert isinstance(result, QuantumCircuit)

    def test_convert_invalid_openqasm3(self):
        with pytest.raises(QASM3ParsingError):
            self.converter.convert("INVALID OPENQASM3 CODE")

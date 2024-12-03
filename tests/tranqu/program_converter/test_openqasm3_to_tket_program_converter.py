import pytest
from openqasm3.parser import QASM3ParsingError
from pytket import Circuit

from tranqu.program_converter import Openqasm3ToTketProgramConverter


class TestOpenqasm3ToTketProgramConverter:
    def setup_method(self):
        self.converter = Openqasm3ToTketProgramConverter()

    def test_convert_valid_qasm3(self):
        result = self.converter.convert("""
OPENQASM 3.0;
include "stdgates.inc";
qubit[1] q;
h q[0];
        """)

        assert isinstance(result, Circuit)

    def test_convert_invalid_qasm3(self):
        with pytest.raises(QASM3ParsingError):
            self.converter.convert("INVALID QASM CODE")

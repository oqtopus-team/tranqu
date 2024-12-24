from tranqu import Tranqu


class TestOuquTpTranspiler:
    def test_transpile_simple_qasm3_program(self):
        tranqu = Tranqu()
        program = """OPENQASM 3.0;
include "stdgates.inc";
qubit[2] q;

h q[0];
cx q[0],q[1];
"""
        result = tranqu.transpile(
            program=program, program_lib="openqasm3", transpiler_lib="ouqu-tp"
        )

        assert isinstance(result.transpiled_program, str)
        assert "OPENQASM" in result.transpiled_program
        assert "h" in result.transpiled_program.lower()
        assert "cx" in result.transpiled_program.lower()

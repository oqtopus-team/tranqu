from pytket.architecture import Architecture  # type: ignore[import-untyped]
from pytket.circuit import OpType  # type: ignore[import-untyped]

from tranqu import Tranqu
from tranqu.program_converter import (
    Openqasm3ToTketProgramConverter,
)
from tranqu.transpiler import TketTranspiler


def test_tranqu_optimizes_hadamard_identity() -> None:
    """Verify that HH = I optimization is performed using tranqu.transpile()."""
    qasm = """
        OPENQASM 3.0;
        include "stdgates.inc";
        qubit[1] q;
        h q[0];
        h q[0];
    """
    tranqu = Tranqu()

    result = tranqu.transpile(
        program=qasm,
        program_lib="openqasm3",
        transpiler_lib="tket",
    )

    assert isinstance(result.transpiled_program, str)
    assert result.stats["before"]["n_gates"] == 2
    assert result.stats["after"]["n_gates"] == 0


def test_tket_transpiler_with_basic_optimization() -> None:
    """Verify optimization with basic synthesis level."""
    qasm = """
        OPENQASM 3.0;
        include "stdgates.inc";
        qubit[1] q;
        h q[0];
        h q[0];
    """
    transpiler = TketTranspiler("tket")
    converter = Openqasm3ToTketProgramConverter()
    circuit = converter.convert(qasm)

    result = transpiler.transpile(
        circuit,
        options={"optimization_level": TketTranspiler.OPT_LEVEL_SYNTHESIS},
    )

    assert result.stats["after"]["n_gates"] == 0


def test_tket_transpiler_respects_device_connectivity() -> None:
    """Verify that transpiler respects device connectivity constraints."""
    input_qasm = """
        OPENQASM 3.0;
        include "stdgates.inc";
        qubit[2] q;
        cx q[1], q[0];
    """
    transpiler = TketTranspiler("tket")
    converter = Openqasm3ToTketProgramConverter()
    circuit = converter.convert(input_qasm)

    device = Architecture([(0, 1)])
    result = transpiler.transpile(
        circuit,
        options={"optimization_level": 2},
        device=device,
    )

    transpiled_circuit = result.transpiled_program
    commands = transpiled_circuit.get_commands()
    assert len(commands) == 1, f"Expected 1 gate, but got {len(commands)}"
    command = commands[0]
    assert command.op.type == OpType.CX, f"Expected CX gate, but got {command.op.type}"
    qubit_indices = [q.index[0] for q in command.qubits]
    assert qubit_indices == [
        0,
        1,
    ], f"Expected CNOT from qubit 0 to 1, but got {qubit_indices}"

    qubit_mapping = result.virtual_physical_mapping["qubit_mapping"]
    assert qubit_mapping == {0: 0, 1: 1}

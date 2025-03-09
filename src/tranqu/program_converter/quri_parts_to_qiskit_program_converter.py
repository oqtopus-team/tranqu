from quri_parts.qiskit.circuit.circuit_converter import convert_to_qiskit
from quri_parts.circuit import Program  # quri-partsのプログラム
from qiskit import QuantumCircuit  # type: ignore[import-untyped]
from .program_converter import ProgramConverter  # 基底クラス

class QuripartsToQiskitProgramConverter(ProgramConverter):
    """Convert a QURI Parts program to a Qiskit quantum circuit."""

    def convert(self, program: Program) -> QuantumCircuit:
        """Convert a QURI Parts quantum program to a Qiskit quantum circuit.

        Args:
            program (Program): The QURI Parts quantum program to be converted.

        Returns:
            QuantumCircuit: The converted Qiskit quantum circuit.
        """
        return convert_to_qiskit(program)

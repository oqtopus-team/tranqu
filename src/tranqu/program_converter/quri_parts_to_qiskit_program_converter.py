from qiskit import QuantumCircuit  # type: ignore[import-untyped]
from quri_parts.circuit import Program  # type: ignore[import-untyped]
from quri_parts.qiskit.circuit.circuit_converter import (
    convert_to_qiskit,  # type: ignore[import-untyped]
)

from .program_converter import ProgramConverter


class QuripartsToQiskitProgramConverter(ProgramConverter):
    """Convert a QURI Parts program to a Qiskit quantum circuit."""

    def convert(self, program: Program) -> QuantumCircuit:  # noqa: PLR6301
        """Convert a QURI Parts quantum program to a Qiskit quantum circuit.

        Args:
            program: The QURI Parts quantum program to be converted.

        Returns:
            QuantumCircuit: The converted Qiskit quantum circuit.

        """
        return convert_to_qiskit(program)  # type: ignore[return-value]

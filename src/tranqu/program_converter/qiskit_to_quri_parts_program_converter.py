from qiskit import QuantumCircuit  # type: ignore[import-untyped]
from quri_parts.circuit import (
    QuantumCircuit as QuriPartsQuantumCircuit,  # type: ignore[import-untyped]
)
from quri_parts.qiskit.circuit.circuit_converter import (
    convert_to_quriparts,  # type: ignore[import-untyped]
)

from .program_converter import ProgramConverter


class QiskitToQuriPartsProgramConverter(ProgramConverter):
    """Convert a Qiskit quantum circuit to a QURI Parts quantum circuit."""

    def convert(self, program: QuantumCircuit) -> QuriPartsQuantumCircuit:  # noqa: PLR6301
        """Convert a Qiskit quantum circuit to a QURI Parts quantum circuit.

        Args:
            program (QuantumCircuit): The Qiskit quantum circuit to be converted.

        Returns:
            QuriPartsQuantumCircuit: The converted QURI Parts quantum circuit.

        """
        return convert_to_quriparts(program)

from qiskit import QuantumCircuit  # type: ignore[import-untyped]
from quri_parts.circuit import QuantumCircuit as QuriPartsQuantumCircuit
from quri_parts.qiskit.circuit.circuit_converter import (
    convert_to_qiskit,  # type: ignore[import-untyped]
)

from .program_converter import ProgramConverter


class QuripartsToQiskitProgramConverter(ProgramConverter):
    """Convert a QURI Parts quantum circuit to a Qiskit quantum circuit."""

    def convert(self, program: QuriPartsQuantumCircuit) -> QuantumCircuit:  # noqa: PLR6301
        """Convert a QURI Parts quantum circuit to a Qiskit quantum circuit.

        Args:
            program: The QURI Parts quantum circuit to be converted.

        Returns:
            QuantumCircuit: The converted Qiskit quantum circuit.

        """
        return convert_to_qiskit(program)

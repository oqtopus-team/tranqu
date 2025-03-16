from qiskit import QuantumCircuit  # type: ignore[import-untyped]
from quri_parts.circuit import Program  # type: ignore[import-untyped]
from quri_parts.qiskit.circuit.circuit_converter import (
    convert_to_quriparts,  # type: ignore[import-untyped]
)

from .program_converter import ProgramConverter


class QiskitToQuriPartsProgramConverter(ProgramConverter):
    """Convert a Qiskit quantum circuit to a QURI Parts program."""

    def convert(self, program: QuantumCircuit) -> Program:  # noqa: PLR6301
        """Convert a Qiskit quantum circuit to a QURI Parts quantum program.

        Args:
            program (QuantumCircuit): The Qiskit quantum circuit to be converted.

        Returns:
            Program: The converted QURI Parts quantum program.

        """
        return convert_to_quriparts(program)  # type: ignore[return-value]

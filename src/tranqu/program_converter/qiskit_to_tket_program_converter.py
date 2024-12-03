from pytket import Circuit
from pytket.extensions.qiskit import qiskit_to_tk
from qiskit import QuantumCircuit  # type: ignore[import-untyped]

from .program_converter import ProgramConverter


class QiskitToTketProgramConverter(ProgramConverter):
    """Converter to transform Qiskit circuits to tket format."""

    def convert(self, program: QuantumCircuit) -> Circuit:  # noqa: PLR6301
        """Convert a Qiskit quantum circuit to tket format.

        Args:
            program (QuantumCircuit): The Qiskit quantum circuit to be converted.

        Returns:
            Circuit: The converted tket format quantum circuit.

        """
        return qiskit_to_tk(program)

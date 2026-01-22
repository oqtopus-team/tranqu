from pytket import Circuit  # type: ignore[attr-defined]  # pytket stubs miss re-exports
from pytket.extensions.qiskit import qiskit_to_tk  # type: ignore[attr-defined]
from qiskit import QuantumCircuit  # type: ignore[import-untyped]  # qiskit is untyped

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

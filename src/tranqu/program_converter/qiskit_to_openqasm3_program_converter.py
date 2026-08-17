from qiskit import QuantumCircuit  # type: ignore[import-untyped]
from qiskit.qasm3 import dumps  # type: ignore[import-untyped]

from .program_converter import ProgramConverter


class QiskitToOpenqasm3ProgramConverter(ProgramConverter):
    """Converter for converting from Qiskit to OpenQASM3 format."""

    def convert(self, program: QuantumCircuit) -> str:  # ruff: ignore[no-self-use]
        """Convert a Qiskit quantum circuit to OpenQASM3 format.

        Args:
            program (QuantumCircuit): The Qiskit quantum circuit to be converted.

        Returns:
            str: The converted OpenQASM3 format code.

        """
        return dumps(program)

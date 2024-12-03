from qiskit import QuantumCircuit  # type: ignore[import-untyped]
from qiskit.qasm3 import loads  # type: ignore[import-untyped]

from .program_converter import ProgramConverter


class Openqasm3ToQiskitProgramConverter(ProgramConverter):
    """Converter that transforms programs in OpenQASM3 format to Qiskit's format."""

    def convert(self, program: str) -> QuantumCircuit:  # noqa: PLR6301
        """Convert the specified OpenQASM3 format program to Qiskit's format.

        Args:
            program (str): A string representing a quantum program in OpenQASM3 format.

        Returns:
            QuantumCircuit: A quantum circuit in Qiskit format.

        """
        return loads(program)

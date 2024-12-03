from pytket import Circuit
from pytket.extensions.qiskit import qiskit_to_tk
from qiskit.qasm3 import loads  # type: ignore[import-untyped]

from .program_converter import ProgramConverter


class Openqasm3ToTketProgramConverter(ProgramConverter):
    """Converter that transforms OpenQASM3 to tket format quantum circuits."""

    def convert(self, program: str) -> Circuit:  # noqa: PLR6301
        """Convert a quantum program in OpenQASM3 format to tket format.

        Args:
            program (str): A string representing a quantum program in OpenQASM3 format.

        Returns:
            Circuit: A quantum circuit in tket format.

        """
        qiskit_circuit = loads(program)
        return qiskit_to_tk(qiskit_circuit)

from pytket import Circuit
from pytket.extensions.qiskit import tk_to_qiskit
from qiskit.qasm3 import dumps  # type: ignore[import-untyped]

from .program_converter import ProgramConverter


class TketToOpenqasm3ProgramConverter(ProgramConverter):
    """Converter that transforms Tket format quantum circuits to OpenQASM3 format."""

    def convert(self, program: Circuit) -> str:  # noqa: PLR6301
        """Convert a Tket format quantum circuit to OpenQASM 3 format.

        Args:
            program (Circuit): Quantum circuit in Tket format.

        Returns:
            str: A string representing the quantum circuit in OpenQASM 3 format.

        """
        program_qiskit = tk_to_qiskit(program)
        return dumps(program_qiskit)

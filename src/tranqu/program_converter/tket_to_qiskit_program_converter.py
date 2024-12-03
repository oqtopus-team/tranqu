# mypy: disable-error-code="import-untyped"

from pytket import Circuit as TketCircuit
from pytket.extensions.qiskit import tk_to_qiskit
from qiskit import QuantumCircuit as QiskitCircuit

from .program_converter import ProgramConverter


class TketToQiskitProgramConverter(ProgramConverter):
    """Converter for transforming quantum circuits from Tket to Qiskit."""

    def convert(self, program: TketCircuit) -> QiskitCircuit:  # noqa: PLR6301
        """Convert a TketCircuit to a Qiskit QuantumCircuit.

        Args:
            program (TketCircuit): The Tket quantum circuit to be converted.

        Returns:
            QiskitCircuit: The converted Qiskit quantum circuit.

        """
        return tk_to_qiskit(program)

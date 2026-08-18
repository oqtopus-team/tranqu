from __future__ import annotations

from typing import TYPE_CHECKING

from .non_gate_operation import QISKIT_NON_GATE_OPERATION_NAMES

if TYPE_CHECKING:
    from qiskit import QuantumCircuit  # type: ignore[import-untyped]

SINGLE_QUBIT = 1
TWO_QUBIT = 2


class QiskitStatsExtractor:
    """Extract statistical information from Qiskit quantum circuits."""

    @staticmethod
    def extract_stats_from(program: QuantumCircuit) -> dict[str, int]:
        """Extract statistical information from a Qiskit quantum circuit.

        Args:
            program (QuantumCircuit): The quantum circuit to analyze.

        Returns:
            dict[str, int]: Statistical information about the circuit.

        """
        gates = [
            instruction
            for instruction in program.data
            if instruction.operation.name not in QISKIT_NON_GATE_OPERATION_NAMES
        ]

        return {
            "n_qubits": program.num_qubits,
            "n_gates": len(gates),
            "n_gates_1q": sum(1 for gate in gates if len(gate.qubits) == SINGLE_QUBIT),
            "n_gates_2q": sum(1 for gate in gates if len(gate.qubits) == TWO_QUBIT),
            "depth": program.depth(),
        }

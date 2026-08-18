from pytket import Circuit  # type: ignore[attr-defined]

from .non_gate_operation import TKET_NON_GATE_OP_TYPES

SINGLE_QUBIT = 1
TWO_QUBIT = 2


class TketStatsExtractor:
    """Extract statistical information from tket circuits."""

    @staticmethod
    def extract_stats_from(program: Circuit) -> dict[str, int]:
        """Extract stats from a tket circuit.

        Args:
            program (Circuit): The circuit to analyze.

        Returns:
            dict[str, int]: Statistical information about the circuit.

        """
        gates = [
            command
            for command in program.get_commands()
            if command.op.type not in TKET_NON_GATE_OP_TYPES
        ]

        return {
            "n_qubits": program.n_qubits,
            "n_gates": len(gates),
            "n_gates_1q": sum(1 for gate in gates if len(gate.qubits) == SINGLE_QUBIT),
            "n_gates_2q": sum(1 for gate in gates if len(gate.qubits) == TWO_QUBIT),
            "depth": program.depth(),
        }

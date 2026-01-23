from pytket import Circuit  # type: ignore[attr-defined]


class TketStatsExtractor:
    """Extract statistical information from tket circuits."""

    SINGLE_QUBIT = 1
    TWO_QUBIT = 2

    @staticmethod
    def extract_stats_from(program: Circuit) -> dict[str, int]:
        """Extract stats from a tket circuit.

        Args:
            program (Circuit): The circuit to analyze.

        Returns:
            dict[str, int]: Statistical information about the circuit.

        """
        return {
            "n_qubits": program.n_qubits,
            "n_gates": program.n_gates,
            "n_gates_1q": sum(
                1
                for cmd in program.get_commands()
                if len(cmd.qubits) == TketStatsExtractor.SINGLE_QUBIT
            ),
            "n_gates_2q": sum(
                1
                for cmd in program.get_commands()
                if len(cmd.qubits) == TketStatsExtractor.TWO_QUBIT
            ),
            "depth": program.depth(),
        }

from qiskit import QuantumCircuit  # type: ignore[import-untyped]


class QiskitStatsExtractor:
    """Extract statistical information from Qiskit quantum circuits."""

    def extract_stats_from(self, program: QuantumCircuit) -> dict[str, int]:
        """Extract statistical information from a Qiskit quantum circuit.

        Args:
            program (QuantumCircuit): The quantum circuit to analyze.

        Returns:
            dict[str, int]: Statistical information about the circuit.

        """
        stats = {}
        stats["n_qubits"] = program.num_qubits
        stats["n_gates"] = len(program.data)
        stats["n_gates_1q"] = self._count_single_qubit_gates(program)
        stats["n_gates_2q"] = self._count_two_qubit_gates(program)
        stats["depth"] = program.depth()
        return stats

    @staticmethod
    def _count_single_qubit_gates(program: QuantumCircuit) -> int:
        return sum(1 for instruction in program.data if len(instruction.qubits) == 1)

    @staticmethod
    def _count_two_qubit_gates(program: QuantumCircuit) -> int:
        return sum(1 for instruction in program.data if len(instruction.qubits) == 2)  # noqa: PLR2004

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from qiskit import QuantumCircuit
from qiskit.circuit.controlflow import CONTROL_FLOW_OP_NAMES


class QiskitStatsExtractor:
    """Extract statistical information from Qiskit quantum circuits."""

    _NON_GATE_OPERATION: ClassVar[set[str]] = {
        "measure",
        "reset",
        "barrier",
        "delay",
        "initialize",
        *CONTROL_FLOW_OP_NAMES,  # 'if_else','for_loop','while_loop','switch_case'
    }

    DEPTH_ONE = 1
    DEPTH_TWO = 2

    def extract_stats_from(self, program: QuantumCircuit) -> dict[str, int]:
        """Extract statistical information from a Qiskit quantum circuit.

        Args:
            program (QuantumCircuit): The quantum circuit to analyze.

        Returns:
            dict[str, int]: Statistical information about the circuit.

        """
        stats = {}
        stats["n_qubits"] = program.num_qubits
        stats["n_gates"] = self._count_gates(program)
        stats["n_gates_1q"] = self._count_single_qubit_gates(program)
        stats["n_gates_2q"] = self._count_two_qubit_gates(program)
        stats["depth"] = program.depth()
        """
        stats["classical_gates"] = self._count_classical_gates(program) # classic gate
        stats["rena"] = 10507
        """
        return stats

    @staticmethod
    def _count_gates(program: QuantumCircuit) -> int:
        # sum non_gate operation
        return sum(
            1
            for instruction in program.data
            if instruction.operation.name
            not in QiskitStatsExtractor._NON_GATE_OPERATION
        )

    @staticmethod
    def _count_single_qubit_gates(program: QuantumCircuit) -> int:
        data = program.data
        count = 0
        for instruction in data:
            # is 1 qubit?
            if len(instruction.qubits) != QiskitStatsExtractor.DEPTH_ONE:
                continue
            # is classical gate?
            if instruction.operation.name in QiskitStatsExtractor._NON_GATE_OPERATION:
                continue
            count += 1
        return count

    @staticmethod
    def _count_two_qubit_gates(program: QuantumCircuit) -> int:
        data = program.data
        count = 0
        for instruction in data:
            # is 2 qubit?
            if len(instruction.qubits) != QiskitStatsExtractor.DEPTH_TWO:
                continue
            # is classical gate?
            if instruction.operation.name in QiskitStatsExtractor._NON_GATE_OPERATION:
                continue
            count += 1
        return count

    @staticmethod
    def _count_classical_gates(program: QuantumCircuit) -> int:  # sum of classic gate
        return sum(
            1
            for instruction in program.data
            if instruction.operation.name in QiskitStatsExtractor._NON_GATE_OPERATION
        )

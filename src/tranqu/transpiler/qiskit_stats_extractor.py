from qiskit import QuantumCircuit  # type: ignore[import-untyped]
from qiskit.circuit.controlflow import CONTROL_FLOW_OP_NAMES


class QiskitStatsExtractor:
    """Extract statistical information from Qiskit quantum circuits."""

    _NON_UNITARY_OPERATION = {
        "measure", "reset", "barrier", "delay", "initialize",
        *CONTROL_FLOW_OP_NAMES,  #'if_else','for_loop','while_loop','switch_case', for Qiskit 2.x
        }
        
    _CLASSICAL_OPERATION = {"measure", "barrier", "delay"}

    def extract_stats_from(self, program: QuantumCircuit) -> dict[str, int]:
        """Extract statistical information from a Qiskit quantum circuit.

        Args:
            program (QuantumCircuit): The quantum circuit to analyze.

        Returns:
            dict[str, int]: Statistical information about the circuit.

        """
        
        
        
        stats = {}
        stats["n_qubits"] = program.num_qubits
        stats["n_gates"] = self._count_unitary_gates(program)
        stats["n_gates_1q"] = self._count_single_qubit_gates(program)
        stats["n_gates_2q"] = self._count_two_qubit_gates(program)
        stats["depth"] = program.depth()
        #stats["classical_gates"] = self._count_classical_gates(program) #sum of classic gate
        #stats["rena"] = 10507
        return stats
    
    @staticmethod
    def _count_unitary_gates(program: QuantumCircuit) -> int:
        non_unitary = QiskitStatsExtractor._NON_UNITARY_OPERATION
        # 非ユニタリ以外＝ユニタリだけを数える
        return sum(1 for instruction in program.data if instruction.operation.name not in non_unitary)

    @staticmethod
    def _count_single_qubit_gates(program: QuantumCircuit) -> int:
        non_unitary = QiskitStatsExtractor._NON_UNITARY_OPERATION         
        data = program.data
        count = 0
        for instruction in data:                  
            #is 1 qubit?
            if len(instruction.qubits) != 1:
                continue
            #is classical gate?
            if instruction.operation.name in non_unitary:
                continue
            count += 1
        return count

    @staticmethod
    def _count_two_qubit_gates(program: QuantumCircuit) -> int:
        non_unitary = QiskitStatsExtractor._NON_UNITARY_OPERATION         
        data = program.data
        count = 0
        for instruction in data:                  
            #is 2 qubit?
            if len(instruction.qubits) != 2:
                continue
            #is classical gate?
            if instruction.operation.name in non_unitary:
                continue
            count += 1
        return count

    @staticmethod
    def _count_classical_gates(program: QuantumCircuit) -> int: #sum of classic gate
        classical_operation = QiskitStatsExtractor._CLASSICAL_OPERATION
        return sum(1 for instruction in program.data if instruction.operation.name in classical_operation)
from qiskit import QuantumCircuit  # type: ignore[import-untyped]

from tranqu.transpile_result import TranspileResult

from .transpiler import Transpiler


class BaseQiskitTranspiler(Transpiler):
    """Provides basic functionality for transpiling Qiskit quantum circuits.

    It includes methods to extract statistics from the transpiled quantum circuit and
    create a mapping of virtual qubits to physical qubits.
    """

    def _extract_stats_from(self, program: QuantumCircuit) -> dict[str, int]:
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

    @staticmethod
    def _create_mapping_from_layout(
        transpiled_program: QuantumCircuit,
    ) -> dict[str, dict[int, int]]:
        mapping: dict[str, dict[int, int]] = {"qubit_mapping": {}, "bit_mapping": {}}

        layout = transpiled_program.layout
        if layout is not None:
            final_layout = layout.final_index_layout()
            for virtual_bit, physical_bit in enumerate(final_layout):
                mapping["qubit_mapping"][virtual_bit] = physical_bit

            if transpiled_program.num_clbits > 0:
                mapping["bit_mapping"] = {
                    i: i for i in range(transpiled_program.num_clbits)
                }
        else:
            for index in range(transpiled_program.num_qubits):
                mapping["qubit_mapping"][index] = index
            for index in range(transpiled_program.num_clbits):
                mapping["bit_mapping"][index] = index

        return mapping

    def _create_transpile_result(
        self,
        original_program: QuantumCircuit,
        transpiled_program: QuantumCircuit,
    ) -> TranspileResult:
        stats = {
            "before": self._extract_stats_from(original_program),
            "after": self._extract_stats_from(transpiled_program),
        }
        mapping = self._create_mapping_from_layout(transpiled_program)
        return TranspileResult(transpiled_program, stats, mapping)

# mypy: disable-error-code="import-untyped"

from __future__ import annotations

from qiskit import QuantumCircuit

from tranqu.transpiler.qiskit_stats_extractor import QiskitStatsExtractor


class TestQiskitStatsExtractor:
    def test_simple_circuit_counts(self) -> None:
        """Check that basic 1-qubit / 2-qubit gate counts are correct."""
        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.x(0)
        circuit.cx(0, 1)

        extractor = QiskitStatsExtractor()
        stats = extractor.extract_stats_from(circuit)

        # Number of qubits
        assert stats["n_qubits"] == 2
        # Only H, X, and CX (3 operations) are counted as gates
        assert stats["n_gates"] == 3
        # 1-qubit gates: H and X (2 operations)
        assert stats["n_gates_1q"] == 2
        # 2-qubit gates: only CX (1 operation)
        assert stats["n_gates_2q"] == 1
        # Depth should match QuantumCircuit.depth()
        assert stats["depth"] == circuit.depth()

    def test_non_gate_operations_are_ignored(self) -> None:
        """Check that non-gate operations."""
        circuit = QuantumCircuit(2, 2)
        # Gate
        circuit.h(0)
        circuit.x(0)
        circuit.cx(0, 1)
        # Various non-gate operations
        circuit.barrier()
        circuit.measure(0, 0)
        circuit.reset(1)
        circuit.delay(100, 0)
        circuit.initialize([1, 0], 0)

        extractor = QiskitStatsExtractor()
        stats = extractor.extract_stats_from(circuit)

        # Number of qubits is still correct
        assert stats["n_qubits"] == 2
        # Only H, X, and CX (3 operations) are counted as gates
        assert stats["n_gates"] == 3
        assert stats["n_gates_1q"] == 2
        assert stats["n_gates_2q"] == 1

    def test_empty_circuit(self) -> None:
        """Check that an empty circuit does not raise and all counts are zero."""
        circuit = QuantumCircuit(3)

        extractor = QiskitStatsExtractor()
        stats = extractor.extract_stats_from(circuit)

        assert stats["n_qubits"] == 3
        assert stats["n_gates"] == 0
        assert stats["n_gates_1q"] == 0
        assert stats["n_gates_2q"] == 0
        assert stats["depth"] == 0

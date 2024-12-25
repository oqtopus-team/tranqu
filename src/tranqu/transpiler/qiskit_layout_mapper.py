from qiskit import QuantumCircuit  # type: ignore[import-untyped]


class QiskitLayoutMapper:
    """Maps virtual qubits to physical qubits for Qiskit quantum circuits."""

    @staticmethod
    def create_mapping_from_layout(
        transpiled_circuit: QuantumCircuit,
    ) -> dict[str, dict[int, int]]:
        """Create a mapping between virtual and physical (qu)bits.

        Args:
            transpiled_circuit (QuantumCircuit): The transpiled quantum circuit.

        Returns:
            dict[str, dict[int, int]]: A dictionary containing the mapping between
                virtual and physical qubits and classical bits.

        """
        mapping: dict[str, dict[int, int]] = {"qubit_mapping": {}, "bit_mapping": {}}

        layout = transpiled_circuit.layout
        if layout is not None:
            final_layout = layout.final_index_layout()
            for virtual_bit, physical_bit in enumerate(final_layout):
                mapping["qubit_mapping"][virtual_bit] = physical_bit

            if transpiled_circuit.num_clbits > 0:
                mapping["bit_mapping"] = {
                    i: i for i in range(transpiled_circuit.num_clbits)
                }
        else:
            for index in range(transpiled_circuit.num_qubits):
                mapping["qubit_mapping"][index] = index
            for index in range(transpiled_circuit.num_clbits):
                mapping["bit_mapping"][index] = index

        return mapping

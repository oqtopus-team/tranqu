from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pytket import Circuit  # type: ignore[attr-defined]
    from pytket.predicates import CompilationUnit  # type: ignore[attr-defined]


class TketLayoutMapper:
    """Maps virtual qubits/bits to physical indices for tket circuits."""

    def create_mapping_from_compilation_unit(
        self, compilation_unit: CompilationUnit, circuit: Circuit
    ) -> dict[str, dict[int, int]]:
        """Create mapping from a CompilationUnit and its circuit.

        Returns:
            dict[str, dict[int, int]]: Mapping for qubits and bits.

        """
        mapping = {
            "qubit_mapping": {},
            "bit_mapping": self._identity_bit_mapping(circuit),
        }

        final_map = getattr(compilation_unit, "final_map", None)
        if final_map:
            mapping["qubit_mapping"] = {
                self._qubit_index(logical, circuit): self._qubit_index(
                    physical, circuit
                )
                for logical, physical in final_map.items()
            }
        else:
            mapping["qubit_mapping"] = self._identity_qubit_mapping(circuit)

        return mapping

    def create_identity_mapping(self, circuit: Circuit) -> dict[str, dict[int, int]]:
        """Create identity mapping for qubits and bits.

        Returns:
            dict[str, dict[int, int]]: Identity mapping for qubits and bits.

        """
        return {
            "qubit_mapping": self._identity_qubit_mapping(circuit),
            "bit_mapping": self._identity_bit_mapping(circuit),
        }

    @staticmethod
    def _identity_qubit_mapping(circuit: Circuit) -> dict[int, int]:
        return {index: index for index in range(len(circuit.qubits))}

    @staticmethod
    def _identity_bit_mapping(circuit: Circuit) -> dict[int, int]:
        return {index: index for index in range(len(circuit.bits))}

    @staticmethod
    def _qubit_index(qubit: object, circuit: Circuit) -> int:
        if hasattr(qubit, "index"):
            index = qubit.index  # type: ignore[attr-defined]
            if isinstance(index, int):
                return index
            if isinstance(index, list | tuple) and index:
                first = index[0]
                if isinstance(first, int):
                    return first
        for idx, candidate in enumerate(circuit.qubits):
            if candidate == qubit:
                return idx
        msg = f"Qubit {qubit} not found in circuit (qubits={len(circuit.qubits)})"
        raise ValueError(msg)

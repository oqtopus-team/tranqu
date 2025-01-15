from ouqu_tp.servicers.ouqu_tp import (  # type: ignore[import-untyped]
    TranspilerService as OuquTp,  # type: ignore[import-untyped]
)
from qiskit import QuantumCircuit  # type: ignore[import-untyped]
from qiskit.qasm3 import loads  # type: ignore[import-untyped]

from tranqu.transpile_result import TranspileResult

from .qiskit_stats_extractor import QiskitStatsExtractor
from .transpiler import Transpiler


class OuquTpTranspiler(Transpiler):
    """Transpile quantum circuits using ouqu-tp.

    It optimizes quantum circuits using ouqu-tp's transpilation function.
    """

    def __init__(self, program_lib: str) -> None:
        super().__init__(program_lib)
        self._ouqu_tp = OuquTp()
        self._qiskit_stats_extractor = QiskitStatsExtractor()

    def transpile(
        self,
        program: str,
        options: dict | None = None,  # noqa: ARG002
        device: str | None = None,
    ) -> TranspileResult:
        """Transpile the specified quantum circuit and return a TranspileResult.

        Args:
            program (str): The quantum circuit to transpile.
            options (dict, optional): Transpilation options.
                Defaults to an empty dictionary.
            device (Any, optional): The target device for transpilation.
                Defaults to None.

        Returns:
            TranspileResult: An object containing the transpilation result,
                including the transpiled quantum circuit, statistics,
                and the mapping of virtual qubits to physical qubits.

        """
        transpile_response = self._ouqu_tp.transpile(program, device)

        original_circuit = loads(program)
        transpiled_circuit = loads(transpile_response.qasm)

        stats = {
            "before": self._qiskit_stats_extractor.extract_stats_from(original_circuit),
            "after": self._qiskit_stats_extractor.extract_stats_from(
                transpiled_circuit
            ),
        }

        qubit_mapping = _calc_qubit_mapping(transpile_response.qubit_mapping)
        bit_mapping = _calc_bit_mapping(transpiled_circuit)
        mapping = {
            "qubit_mapping": qubit_mapping,
            "bit_mapping": bit_mapping,
        }

        return TranspileResult(transpile_response.qasm, stats, mapping)


def _calc_qubit_mapping(qubit_mapping: dict[int, int]) -> dict[int, int]:
    # qubit_mapping in ouqu-tp is physical -> virtual
    # Therefore, the keys and values are swapped
    return {v: k for k, v in qubit_mapping.items()}


def _calc_bit_mapping(transpiled_circuit: QuantumCircuit) -> dict[int, int]:
    # bit_mapping remains unchanged before and after transpilation
    num_clbits = transpiled_circuit.num_clbits
    return {i: i for i in range(num_clbits)}

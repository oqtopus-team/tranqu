from ouqu_tp.servicers.ouqu_tp import (  # type: ignore[import-untyped]
    TranspilerService as OuquTp,  # type: ignore[import-untyped]
)
from qiskit.qasm3 import loads  # type: ignore[import-untyped]

from tranqu.transpile_result import TranspileResult

from .qiskit_layout_mapper import QiskitLayoutMapper
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
        self._layout_mapper = QiskitLayoutMapper()

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

        mapping = self._layout_mapper.create_mapping_from_layout(transpiled_circuit)

        return TranspileResult(transpile_response.qasm, stats, mapping)

from qiskit import QuantumCircuit  # type: ignore[import-untyped]
from qiskit import transpile as qiskit_transpile  # type: ignore[import-untyped]
from qiskit.providers.backend import BackendV2  # type: ignore[import-untyped]

from tranqu.transpile_result import TranspileResult

from .qiskit_layout_mapper import QiskitLayoutMapper
from .qiskit_stats_extractor import QiskitStatsExtractor
from .transpiler import Transpiler


class QiskitTranspiler(Transpiler):
    """Transpile quantum circuits using Qiskit.

    It optimizes quantum circuits using Qiskit's `transpile()` function.
    """

    def __init__(self, program_lib: str) -> None:
        super().__init__(program_lib)
        self._stats_extractor = QiskitStatsExtractor()
        self._layout_mapper = QiskitLayoutMapper()

    def transpile(
        self,
        program: QuantumCircuit,
        options: dict | None = None,
        device: BackendV2 | None = None,
    ) -> TranspileResult:
        """Transpile the specified quantum circuit and return a TranspileResult.

        Args:
            program (QuantumCircuit): The quantum circuit to transpile.
            options (dict, optional): Transpilation options.
                Defaults to an empty dictionary.
            device (BackendV2, optional): The target device for transpilation.
                Defaults to None.

        Returns:
            TranspileResult: An object containing the transpilation result,
                including the transpiled quantum circuit, statistics,
                and the mapping of virtual qubits to physical qubits.

        """
        options_dict = options or {}
        if device is not None:
            options_dict["backend"] = device

        transpiled_program = qiskit_transpile(program, **options_dict)

        stats = {
            "before": self._stats_extractor.extract_stats_from(program),
            "after": self._stats_extractor.extract_stats_from(transpiled_program),
        }
        mapping = self._layout_mapper.create_mapping_from_layout(transpiled_program)

        return TranspileResult(transpiled_program, stats, mapping)

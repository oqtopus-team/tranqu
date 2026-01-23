from typing import Any

from pytket import Circuit  # type: ignore[attr-defined]
from pytket.backends import Backend  # type: ignore[attr-defined]
from pytket.passes import (  # type: ignore[attr-defined]
    DecomposeBoxes,
    FullPeepholeOptimise,
    SequencePass,
    SynthesiseTket,
)
from pytket.predicates import CompilationUnit  # type: ignore[attr-defined]

from tranqu.transpile_result import TranspileResult

from .tket_layout_mapper import TketLayoutMapper
from .tket_stats_extractor import TketStatsExtractor
from .transpiler import Transpiler


class TketTranspiler(Transpiler):
    """Transpile quantum circuits using t|ket>."""

    INVALID_OPT_LEVEL = "Invalid optimization level"

    def __init__(self, program_lib: str) -> None:
        super().__init__(program_lib)
        self._stats_extractor = TketStatsExtractor()
        self._layout_mapper = TketLayoutMapper()

    def transpile(
        self,
        program: Circuit,
        options: dict[str, Any] | None = None,
        device: Backend | None = None,
    ) -> TranspileResult:
        """Transpile the program using tket.

        Args:
            program (Circuit): Program to transpile.
            options (dict[str, Any] | None): Options for transpilation.
            device (Backend | None): Device information.

        Returns:
            TranspileResult: Result of transpilation.

        Raises:
            ValueError: If optimization_level is not 0, 1, or 2.

        """
        options_dict = options or {}
        optimization_level = options_dict.get("optimization_level", 1)

        if not isinstance(optimization_level, int) or optimization_level not in {
            0,
            1,
            2,
        }:
            raise ValueError(self.INVALID_OPT_LEVEL)

        program_copy = program.copy()

        if device is not None:
            compilation_unit = CompilationUnit(program_copy)
            compilation_pass = device.default_compilation_pass(
                optimisation_level=optimization_level
            )
            compilation_pass.apply(compilation_unit)
            transpiled_program = compilation_unit.circuit
            mapping = self._layout_mapper.create_mapping_from_compilation_unit(
                compilation_unit, transpiled_program
            )
        else:
            transpiled_program = self._apply_minimal_pass(
                program_copy, optimization_level
            )
            mapping = self._layout_mapper.create_identity_mapping(transpiled_program)

        stats = {
            "before": self._stats_extractor.extract_stats_from(program),
            "after": self._stats_extractor.extract_stats_from(transpiled_program),
        }

        return TranspileResult(transpiled_program, stats, mapping)

    @staticmethod
    def _apply_minimal_pass(circuit: Circuit, optimization_level: int) -> Circuit:
        if optimization_level == 0:
            return circuit
        if optimization_level == 1:
            SequencePass([DecomposeBoxes(), SynthesiseTket()]).apply(circuit)
            return circuit

        SequencePass([DecomposeBoxes(), FullPeepholeOptimise()]).apply(circuit)
        return circuit

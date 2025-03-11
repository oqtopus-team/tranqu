from pytket import Circuit  # type: ignore[import-untyped]
from pytket.architecture import Architecture  # type: ignore[import-untyped]
from pytket.passes import (  # type: ignore[import-untyped]
    AASRouting,
    CliffordSimp,
    CNotSynthType,
    DecomposeBoxes,
    DefaultMappingPass,
    FullPeepholeOptimise,
    RebaseTket,
    RemoveBarriers,
    SequencePass,
    SynthesiseTket,
)

from tranqu.transpile_result import TranspileResult

from .transpiler import Transpiler


class TketTranspiler(Transpiler):
    """Transpile quantum circuits using t|ket⟩.

    It optimizes quantum circuits using t|ket⟩'s optimization passes.
    """

    # Optimization levels
    OPT_LEVEL_BASIC = 0
    OPT_LEVEL_SYNTHESIS = 1
    OPT_LEVEL_CLIFFORD = 2
    OPT_LEVEL_ADVANCED = 3

    # Gate types by qubit count
    SINGLE_QUBIT = 1
    TWO_QUBIT = 2

    # Error messages
    INVALID_OPT_LEVEL = "Invalid optimization level"

    def __init__(self, program_lib: str) -> None:
        super().__init__(program_lib)

    def transpile(
        self,
        program: Circuit,
        options: dict | None = None,
        device: Architecture | None = None,  # type: ignore[reportGeneralTypeIssues]
    ) -> TranspileResult:
        """Transpile the specified quantum circuit and return a TranspileResult.

        Args:
            program (Circuit): The quantum circuit to transpile.
            options (dict, optional): Transpilation options.
                - optimization_level (int): Optimization level (0-3).
                    - 0: Basic rebase only
                    - 1: Basic synthesis
                    - 2: Full optimization with Clifford simplification
                    - 3: Advanced optimization with extended gate set
                Defaults to 1.
            device (Architecture, optional): The target device architecture.
                Defaults to None.

        Returns:
            TranspileResult: An object containing the transpilation result,
                including the transpiled quantum circuit, statistics,
                and the mapping of virtual qubits to physical qubits.

        Raises:
            ValueError: If optimization_level is not an integer between 0 and 3.

        """
        # Create a copy of the circuit for transpilation
        transpiled_program = program.copy()

        # Get optimization level from options
        opt_level = (options or {}).get("optimization_level", 1)
        if not isinstance(opt_level, int) or opt_level not in range(4):
            raise ValueError(self.INVALID_OPT_LEVEL)

        # Create optimization pass based on options and device
        optimization_pass = self._create_optimization_pass(opt_level, device)

        # Apply optimization passes
        optimization_pass.apply(transpiled_program)

        # Extract statistics
        stats = {
            "before": self._extract_stats_from(program),
            "after": self._extract_stats_from(transpiled_program),
        }

        # Create mapping
        mapping = {
            "qubit_mapping": self._create_qubit_mapping(transpiled_program),
            "bit_mapping": self._create_bit_mapping(transpiled_program),
        }

        return TranspileResult(transpiled_program, stats, mapping)

    @staticmethod
    def _extract_stats_from(circuit: Circuit) -> dict[str, int]:
        """Extract statistics from a circuit.

        Args:
            circuit (Circuit): The circuit to extract statistics from.

        Returns:
            dict[str, int]: A dictionary containing circuit statistics.

        """
        return {
            "n_qubits": circuit.n_qubits,
            "n_gates": circuit.n_gates,
            "depth": circuit.depth(),
            "n_gates_1q": sum(
                1
                for cmd in circuit.get_commands()
                if len(cmd.qubits) == TketTranspiler.SINGLE_QUBIT
            ),
            "n_gates_2q": sum(
                1
                for cmd in circuit.get_commands()
                if len(cmd.qubits) == TketTranspiler.TWO_QUBIT
            ),
        }

    @staticmethod
    def _create_qubit_mapping(circuit: Circuit) -> dict[int, int]:
        """Create a mapping of virtual to physical qubits.

        Args:
            circuit (Circuit): The circuit to create mapping from.

        Returns:
            dict[int, int]: A dictionary mapping virtual qubits to physical qubits.

        """
        # Get the qubit mapping from the circuit
        qubit_mapping = {}
        for i, q in enumerate(circuit.qubits):
            # Extract the physical qubit index from the Qubit object
            if hasattr(q, "index") and len(q.index) > 0:
                qubit_mapping[i] = q.index[0]
            else:
                qubit_mapping[i] = i
        return qubit_mapping

    @staticmethod
    def _create_bit_mapping(circuit: Circuit) -> dict[int, int]:
        """Create a mapping of virtual to physical classical bits.

        Args:
            circuit (Circuit): The circuit to create mapping from.

        Returns:
            dict[int, int]: A dictionary mapping virtual bits to physical bits.

        """
        # Get the bit mapping from the circuit
        bit_mapping = {}
        for i, b in enumerate(circuit.bits):
            # Extract the physical bit index from the Bit object
            if hasattr(b, "index") and len(b.index) > 0:
                bit_mapping[i] = b.index[0]
            else:
                bit_mapping[i] = i
        return bit_mapping

    def _create_optimization_pass(
        self, optimization_level: int, device: Architecture | None = None
    ) -> SequencePass:
        """Create optimization pass for the transpiler.

        Args:
            optimization_level (int): The optimization level (0-3).
            device (Architecture, optional): The target device architecture.

        Returns:
            SequencePass: A sequence of optimization passes.

        """
        passes = []

        # Basic passes for all optimization levels
        passes.append(DecomposeBoxes())

        # Add optimization passes based on level
        if optimization_level == self.OPT_LEVEL_BASIC:
            # Basic rebase only
            passes.append(RebaseTket())
        elif optimization_level == self.OPT_LEVEL_SYNTHESIS:
            # Basic synthesis
            passes.append(SynthesiseTket())
        elif optimization_level == self.OPT_LEVEL_CLIFFORD:
            # Full optimization with Clifford simplification
            passes.extend([FullPeepholeOptimise(), CliffordSimp()])
        else:  # optimization_level == self.OPT_LEVEL_ADVANCED
            # Advanced optimization with extended gate set
            passes.extend([
                RemoveBarriers(),
                FullPeepholeOptimise(),
                CliffordSimp(),
            ])

        # Add device-specific optimization if device is provided
        if device is not None:
            passes.append(DefaultMappingPass(device))

            # Add routing pass with more aggressive optimization
            passes.extend([
                AASRouting(device, lookahead=5, cnotsynthtype=CNotSynthType.Rec),
                RebaseTket(),  # Final rebase pass
            ])

        return SequencePass(passes)

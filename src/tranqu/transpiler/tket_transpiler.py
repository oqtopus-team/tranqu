from typing import Any

from pytket import Circuit  # type: ignore[attr-defined]
from pytket.architecture import (  # type: ignore[attr-defined]
    Architecture,
    FullyConnected,
)
from pytket.backends import Backend  # type: ignore[attr-defined]
from pytket.passes import (  # type: ignore[attr-defined]
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

        """
        if options is None:
            options = {}

        optimization_level = options.get("optimization_level", self.OPT_LEVEL_SYNTHESIS)

        # Create a copy of the program to avoid modifying the original
        program_copy = program.copy()

        # Get the architecture from the device if provided
        architecture = None
        if device is not None and device.backend_info is not None:
            architecture = device.backend_info.architecture

        # Apply optimization passes
        if optimization_level >= self.OPT_LEVEL_SYNTHESIS:
            # Create optimization pass based on options and device
            optimization_pass = self._create_optimization_pass(
                optimization_level, architecture
            )

            # Apply optimization passes
            optimization_pass.apply(program_copy)

        # Extract statistics
        stats = {
            "before": self._extract_stats_from(program),
            "after": self._extract_stats_from(program_copy),
        }

        # Create mapping
        mapping = {
            "qubit_mapping": self._create_qubit_mapping(program_copy),
            "bit_mapping": self._create_bit_mapping(program_copy),
        }

        return TranspileResult(program_copy, stats, mapping)

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
        self,
        optimization_level: int,
        architecture: Architecture | FullyConnected | None = None,
    ) -> SequencePass:
        """Create optimization pass for the transpiler.

        Args:
            optimization_level (int): The optimization level (0-3).
            architecture (Architecture, optional): The target device architecture.
                Defaults to None.

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

        # Add device-specific optimization if architecture is provided
        if architecture is not None:
            # Convert FullyConnected to Architecture if needed
            if isinstance(architecture, FullyConnected):
                n_nodes = len(architecture.nodes)
                architecture = Architecture([
                    (i, j) for i in range(n_nodes) for j in range(i + 1, n_nodes)
                ])

            passes.append(DefaultMappingPass(architecture))

            # Add routing pass with more aggressive optimization
            passes.extend([
                AASRouting(architecture, lookahead=5, cnotsynthtype=CNotSynthType.Rec),
                RebaseTket(),  # Final rebase pass
            ])

        return SequencePass(passes)

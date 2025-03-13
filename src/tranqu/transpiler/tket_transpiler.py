from typing import Any

from pytket import Circuit  # type: ignore[attr-defined]
from pytket.architecture import (  # type: ignore[attr-defined]
    Architecture,
    FullyConnected,
)
from pytket.backends import Backend  # type: ignore[attr-defined]
from pytket.circuit import OpType  # type: ignore[attr-defined]
from pytket.extensions.qiskit.backends.ibm_utils import (
    _gen_lightsabre_transformation,  # noqa: PLC2701 # type: ignore[attr-defined]
)
from pytket.passes import (  # type: ignore[attr-defined]
    AutoRebase,
    BasePass,
    CliffordSimp,
    CustomPass,
    DecomposeBoxes,
    FullPeepholeOptimise,
    GreedyPauliSimp,
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

        self.device = device

        optimization_level = options.get("optimization_level", 1)

        program_copy = program.copy()

        architecture = None
        if device is not None and device.backend_info is not None:
            architecture = device.backend_info.architecture

        if optimization_level >= 1:
            optimization_pass = self._create_optimization_pass(
                optimization_level, architecture
            )
            optimization_pass.apply(program_copy)

        stats = {
            "before": self._extract_stats_from(program),
            "after": self._extract_stats_from(program_copy),
        }

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
                1 for cmd in circuit.get_commands() if len(cmd.qubits) == 1
            ),
            "n_gates_2q": sum(
                1
                for cmd in circuit.get_commands()
                if len(cmd.qubits) == 2  # noqa: PLR2004
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
        qubit_mapping = {}
        for i, q in enumerate(circuit.qubits):
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
        bit_mapping = {}
        for i, b in enumerate(circuit.bits):
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
        timeout = 300

        if isinstance(architecture, Architecture):
            return self._arch_dependent_pass(architecture, optimization_level, timeout)

        return self._arch_independent_pass(optimization_level, timeout)

    def _arch_dependent_pass(
        self,
        architecture: Architecture,
        optimization_level: int,
        timeout: int,
    ) -> SequencePass:
        arch_specific_passes = [
            AutoRebase({OpType.CX, OpType.TK1}),
            CustomPass(
                _gen_lightsabre_transformation(architecture), label="lightsabrepass"
            ),
        ]

        if optimization_level == 0:
            return SequencePass(
                [
                    DecomposeBoxes(),
                    self._rebase_pass(),
                    *arch_specific_passes,
                    self._rebase_pass(),
                ],
            )
        if optimization_level == 1:
            return SequencePass(
                [
                    DecomposeBoxes(),
                    SynthesiseTket(),
                    *arch_specific_passes,
                    SynthesiseTket(),
                ],
            )
        if optimization_level == 2:  # noqa: PLR2004
            return SequencePass(
                [
                    DecomposeBoxes(),
                    FullPeepholeOptimise(),
                    *arch_specific_passes,
                    CliffordSimp(False),  # noqa: FBT003
                    SynthesiseTket(),
                ],
            )

        return SequencePass(
            [
                DecomposeBoxes(),
                RemoveBarriers(),
                AutoRebase({
                    OpType.Z,
                    OpType.X,
                    OpType.Y,
                    OpType.S,
                    OpType.Sdg,
                    OpType.V,
                    OpType.Vdg,
                    OpType.H,
                    OpType.CX,
                    OpType.CY,
                    OpType.CZ,
                    OpType.SWAP,
                    OpType.Rz,
                    OpType.Rx,
                    OpType.Ry,
                    OpType.T,
                    OpType.Tdg,
                    OpType.ZZMax,
                    OpType.ZZPhase,
                    OpType.XXPhase,
                    OpType.YYPhase,
                    OpType.PhasedX,
                }),
                GreedyPauliSimp(thread_timeout=timeout, only_reduce=True, trials=10),
                *arch_specific_passes,
                self._rebase_pass(),
                SynthesiseTket(),
            ],
        )

    def _arch_independent_pass(
        self, optimization_level: int, timeout: int
    ) -> SequencePass:
        if optimization_level == 0:
            return SequencePass([DecomposeBoxes(), self._rebase_pass()])
        if optimization_level == 1:
            return SequencePass([DecomposeBoxes(), SynthesiseTket()])
        if optimization_level == 2:  # noqa: PLR2004
            return SequencePass([DecomposeBoxes(), FullPeepholeOptimise()])

        return SequencePass(
            [
                DecomposeBoxes(),
                RemoveBarriers(),
                AutoRebase({
                    OpType.Z,
                    OpType.X,
                    OpType.Y,
                    OpType.S,
                    OpType.Sdg,
                    OpType.V,
                    OpType.Vdg,
                    OpType.H,
                    OpType.CX,
                    OpType.CY,
                    OpType.CZ,
                    OpType.SWAP,
                    OpType.Rz,
                    OpType.Rx,
                    OpType.Ry,
                    OpType.T,
                    OpType.Tdg,
                    OpType.ZZMax,
                    OpType.ZZPhase,
                    OpType.XXPhase,
                    OpType.YYPhase,
                    OpType.PhasedX,
                }),
                GreedyPauliSimp(thread_timeout=timeout, only_reduce=True, trials=10),
                self._rebase_pass(),
                SynthesiseTket(),
            ],
        )

    def _rebase_pass(self) -> BasePass:
        if self.device is None:
            error_message = "Device is not set"
            raise ValueError(error_message)

        if self.device.backend_info is None:
            error_message = "Device backend info is not set"
            raise ValueError(error_message)

        return AutoRebase(
            self.device.backend_info.gate_set,
        )

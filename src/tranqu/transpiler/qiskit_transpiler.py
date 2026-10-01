from qiskit import QuantumCircuit  # type: ignore[import-untyped]
from qiskit import transpile as qiskit_transpile  # type: ignore[import-untyped]
from qiskit.providers.backend import BackendV2  # type: ignore[import-untyped]

from tranqu.transpile_result import TranspileResult

from .qiskit_layout_mapper import QiskitLayoutMapper
from .qiskit_stats_extractor import QiskitStatsExtractor
from .qiskit_target_builder import build_native_target, transpile_direction_aware
from .transpiler import Transpiler

# Options that make Qiskit rebuild the Target from the backend; when one is
# given, the device is passed as ``backend`` and Qiskit handles the override.
_TARGET_OVERRIDES = frozenset({
    "coupling_map",
    "dt",
    "instruction_durations",
    "timing_constraints",
    "backend_properties",
    "inst_map",
})


class QiskitTranspiler(Transpiler):
    """Transpile quantum circuits using Qiskit.

    It optimizes quantum circuits using Qiskit's `transpile()` function.

    When a device is given together with ``basis_gates``, the device Target is
    restricted to those gates instead of being rebuilt by Qiskit, so the
    calibration (error rates and durations) is still used for the layout.
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
                Defaults to an empty dictionary. Besides the options of Qiskit's
                ``transpile()``, ``direction_aware=True`` chooses the layout
                taking into account that a CX against the registered direction
                costs extra gates. It requires a device or a ``target``.
            device (BackendV2, optional): The target device for transpilation.
                Defaults to None.

        Returns:
            TranspileResult: An object containing the transpilation result,
                including the transpiled quantum circuit, statistics,
                and the mapping of virtual qubits to physical qubits.

        Raises:
            ValueError: If ``direction_aware`` is set without a Target.

        """
        options_dict = dict(options or {})
        direction_aware = options_dict.pop("direction_aware", False)
        if device is not None:
            self._set_device(options_dict, device, require_target=direction_aware)

        if direction_aware:
            target = options_dict.pop("target", None)
            if target is None:
                msg = (
                    "direction_aware requires a device or a target, and cannot "
                    f"be combined with {', '.join(sorted(_TARGET_OVERRIDES))}."
                )
                raise ValueError(msg)
            transpiled_program = transpile_direction_aware(
                program, target, **options_dict
            )
        else:
            transpiled_program = qiskit_transpile(program, **options_dict)

        stats = {
            "before": self._stats_extractor.extract_stats_from(program),
            "after": self._stats_extractor.extract_stats_from(transpiled_program),
        }
        mapping = self._layout_mapper.create_mapping_from_layout(transpiled_program)

        return TranspileResult(transpiled_program, stats, mapping)

    @staticmethod
    def _set_device(options: dict, device: BackendV2, *, require_target: bool) -> None:
        """Pass the device to Qiskit, as a Target when the calibration can be kept.

        ``basis_gates`` along with ``backend`` would make Qiskit rebuild the
        Target without error rates, so the device Target restricted to the
        basis gates is passed as ``target`` instead.
        """
        if "target" in options:
            return
        if _TARGET_OVERRIDES.isdisjoint(options):
            basis_gates = options.get("basis_gates")
            if basis_gates is None:
                target = device.target if require_target else None
            else:
                target = build_native_target(device.target, basis_gates)
            if target is not None:
                options.pop("basis_gates", None)
                options["target"] = target
                return
        options["backend"] = device

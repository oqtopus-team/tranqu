# mypy: disable-error-code="import-untyped"

import math
import warnings

import pytest
from pytket import Circuit  # type: ignore[attr-defined]
from qiskit import QuantumCircuit  # type: ignore[import-untyped]
from qiskit.circuit import Delay
from qiskit.circuit.library import CXGate, HGate
from qiskit.providers.fake_provider import GenericBackendV2
from qiskit.transpiler import InstructionProperties, Target, TranspilerError
from qiskit_ibm_runtime.fake_provider import FakeSantiagoV2

from tranqu import Tranqu, TranspileResult


@pytest.fixture
def tranqu() -> Tranqu:
    return Tranqu()


def assert_circuits_equivalent(circuit1: QuantumCircuit, circuit2: QuantumCircuit):
    assert circuit1.data == circuit2.data, "Circuits are not equivalent"


def gate_count_of_type(result: TranspileResult, gate_name: str) -> int:
    """Return the number of gates of a specific type in the transpiled program.

    Returns:
        int: The number of gates matching the specified gate name.
    """
    return sum(
        1 for inst in result.transpiled_program.data if inst.operation.name == gate_name
    )


def has_delay(result: TranspileResult) -> bool:
    """Check if the transpiled program contains a delay.

    Returns:
        bool: True if the transpiled program contains a delay, False otherwise.
    """
    return any(
        isinstance(inst.operation, Delay) for inst in result.transpiled_program.data
    )


class TestQiskitTranspiler:
    class TestTranspileVariousFormats:
        def test_transpile_qiskit_program(self, tranqu: Tranqu):
            circuit = QuantumCircuit(1)
            circuit.h(0)
            circuit.h(0)

            result = tranqu.transpile(
                circuit,
                program_lib="qiskit",
                transpiler_lib="qiskit",
            )

            assert result.stats.after.n_gates == 0

        def test_transpile_tket_program(self, tranqu: Tranqu):
            circuit = Circuit(1)
            circuit.H(0)
            circuit.H(0)

            result = tranqu.transpile(
                circuit,
                program_lib="tket",
                transpiler_lib="qiskit",
            )

            assert result.stats.after.n_gates == 0

        def test_transpile_qasm3_program(self, tranqu: Tranqu):
            program = """
OPENQASM 3.0;
include "stdgates.inc";

qubit q;

h q;
h q;
"""

            result = tranqu.transpile(
                program,
                program_lib="openqasm3",
                transpiler_lib="qiskit",
            )

            assert result.stats.after.n_gates == 0

    class TestBasisGates:
        def test_basis_gates_option(self, tranqu: Tranqu):
            circuit = QuantumCircuit(1)
            circuit.x(0)

            result = tranqu.transpile(
                circuit,
                program_lib="qiskit",
                transpiler_lib="qiskit",
                transpiler_options={"basis_gates": ["rx"]},
            )

            expected_circuit = QuantumCircuit(1)
            expected_circuit.rx(math.pi, 0)  # X = Rx(π)
            assert_circuits_equivalent(result.transpiled_program, expected_circuit)

        def test_basis_gates_option_failure(self, tranqu: Tranqu):
            circuit = QuantumCircuit(1)
            circuit.x(0)

            with pytest.raises(TranspilerError):
                tranqu.transpile(
                    circuit,
                    program_lib="qiskit",
                    transpiler_lib="qiskit",
                    transpiler_options={"basis_gates": ["y"]},
                )

    class TestCouplingMap:
        def test_directed_coupling_map_option(self, tranqu: Tranqu):
            circuit = QuantumCircuit(2)
            circuit.cz(1, 0)

            result = tranqu.transpile(
                circuit,
                program_lib="qiskit",
                transpiler_lib="qiskit",
                transpiler_options={"coupling_map": [[0, 1]]},
            )

            expected_circuit = QuantumCircuit(2)
            expected_circuit.cz(0, 1)
            assert_circuits_equivalent(result.transpiled_program, expected_circuit)

        def test_directed_coupling_map_device(self, tranqu: Tranqu):
            circuit = QuantumCircuit(2)
            circuit.cz(1, 0)

            result = tranqu.transpile(
                circuit,
                program_lib="qiskit",
                transpiler_lib="qiskit",
                device=GenericBackendV2(
                    num_qubits=2,
                    basis_gates=["cz"],
                    coupling_map=[[0, 1]],
                ),
                device_lib="qiskit",
            )

            expected_circuit = QuantumCircuit(2)
            expected_circuit.cz(0, 1)
            assert_circuits_equivalent(result.transpiled_program, expected_circuit)

        def test_undirected_coupling_map_option(self, tranqu: Tranqu):
            circuit = QuantumCircuit(2)
            circuit.cx(0, 1)

            result = tranqu.transpile(
                circuit,
                program_lib="qiskit",
                transpiler_lib="qiskit",
                transpiler_options={"coupling_map": [[0, 1], [1, 0]]},
            )

            expected_circuit = QuantumCircuit(2)
            control_qubit = result.virtual_physical_mapping.qubit_mapping[0]
            target_qubit = result.virtual_physical_mapping.qubit_mapping[1]
            expected_circuit.cx(control_qubit, target_qubit)

            assert_circuits_equivalent(result.transpiled_program, expected_circuit)

    class TestOptimizationLevel:
        def test_optimization_level_0_option(self, tranqu: Tranqu):
            circuit = QuantumCircuit(1)
            circuit.h(0)
            circuit.h(0)

            result = tranqu.transpile(
                circuit,
                "qiskit",
                "qiskit",
                transpiler_options={"optimization_level": 0},
            )

            assert result.stats.after.n_gates == 2

        def test_optimization_level_1_option(self, tranqu: Tranqu):
            circuit = QuantumCircuit(1)
            circuit.h(0)
            circuit.h(0)

            try:
                result = tranqu.transpile(
                    circuit,
                    "qiskit",
                    "qiskit",
                    transpiler_options={"optimization_level": 1},
                )
            except ValueError as e:
                pytest.fail(f"tranqu.transpile raised an exception: {e}")

            assert result.stats.after.n_gates == 0

        def test_optimization_level_2_option(self, tranqu: Tranqu):
            circuit = QuantumCircuit(3)
            circuit.swap(0, 1)

            try:
                result = tranqu.transpile(
                    circuit,
                    "qiskit",
                    "qiskit",
                    transpiler_options={"optimization_level": 2},
                )
            except ValueError as e:
                pytest.fail(f"tranqu.transpile raised an exception: {e}")

            assert gate_count_of_type(result, "swap") == 0

        def test_optimization_level_3_option(self, tranqu: Tranqu):
            circuit = QuantumCircuit(3)
            circuit.swap(0, 2)
            circuit.swap(0, 1)
            circuit.cx(0, 1)

            try:
                result = tranqu.transpile(
                    circuit,
                    "qiskit",
                    "qiskit",
                    transpiler_options={
                        "optimization_level": 3,
                        "coupling_map": [[0, 1], [1, 2]],
                    },
                )
            except ValueError as e:
                pytest.fail(f"tranqu.transpile raised an exception: {e}")

            assert gate_count_of_type(result, "swap") == 0

        def test_invalid_optimization_level_option(self, tranqu: Tranqu):
            with pytest.raises(ValueError, match="Invalid optimization level"):
                tranqu.transpile(
                    QuantumCircuit(),
                    "qiskit",
                    "qiskit",
                    transpiler_options={"optimization_level": -1},
                )

            with pytest.raises(ValueError, match="Invalid optimization level"):
                tranqu.transpile(
                    QuantumCircuit(),
                    "qiskit",
                    "qiskit",
                    transpiler_options={"optimization_level": 4},
                )

    class TestInitialLayout:
        def test_initial_layout_option(self, tranqu: Tranqu):
            circuit = QuantumCircuit(3)
            circuit.x(0)
            circuit.y(1)
            circuit.z(2)

            result = tranqu.transpile(
                circuit,
                "qiskit",
                "qiskit",
                transpiler_options={"initial_layout": [2, 1, 0]},
            )

            expected_circuit = QuantumCircuit(3)
            expected_circuit.z(0)
            expected_circuit.y(1)
            expected_circuit.x(2)

            assert_circuits_equivalent(result.transpiled_program, expected_circuit)

        def test_invalid_initial_layout_option(self, tranqu: Tranqu):
            circuit = QuantumCircuit(3)

            with pytest.raises(
                TranspilerError,
            ):
                tranqu.transpile(
                    circuit,
                    "qiskit",
                    "qiskit",
                    transpiler_options={"initial_layout": [0]},
                )

    def test_layout_method_option(self, tranqu: Tranqu):
        circuit = QuantumCircuit(3)
        circuit.cx(0, 1)
        circuit.cx(1, 2)
        circuit.cx(0, 2)

        coupling_map = [[0, 1], [1, 2], [3, 4], [3, 6], [4, 5], [4, 6], [3, 5], [5, 6]]
        basis_gates = ["cx", "h", "t", "u"]
        seed_transpiler = 42

        transpiled_program_trivial = tranqu.transpile(
            circuit,
            "qiskit",
            "qiskit",
            transpiler_options={
                "layout_method": "trivial",
                "coupling_map": coupling_map,
                "basis_gates": basis_gates,
                "seed_transpiler": seed_transpiler,
            },
        ).transpiled_program

        transpiled_program_dense = tranqu.transpile(
            circuit,
            "qiskit",
            "qiskit",
            transpiler_options={
                "layout_method": "dense",
                "coupling_map": coupling_map,
                "basis_gates": basis_gates,
                "seed_transpiler": seed_transpiler,
            },
        ).transpiled_program

        transpiled_program_sabre = tranqu.transpile(
            circuit,
            "qiskit",
            "qiskit",
            transpiler_options={
                "layout_method": "sabre",
                "coupling_map": coupling_map,
                "basis_gates": basis_gates,
                "seed_transpiler": seed_transpiler,
            },
        ).transpiled_program

        assert transpiled_program_dense.depth() < transpiled_program_trivial.depth()
        assert transpiled_program_sabre.depth() <= transpiled_program_dense.depth()

    def test_routing_method_option(self, tranqu: Tranqu):
        circuit = QuantumCircuit(3)
        circuit.cx(0, 2)

        result = tranqu.transpile(
            circuit,
            "qiskit",
            "qiskit",
            transpiler_options={
                "coupling_map": [[0, 1], [1, 0], [1, 2], [2, 1]],
                "initial_layout": [0, 1, 2],
                "routing_method": "sabre",
                "basis_gates": ["cx", "h", "swap"],
                "seed_transpiler": 42,
            },
        )

        expected_circuit = QuantumCircuit(3)
        expected_circuit.swap(1, 2)
        expected_circuit.cx(0, 1)

        assert_circuits_equivalent(result.transpiled_program, expected_circuit)

    class TestTranslationMethod:
        def test_translation_method_option(self, tranqu: Tranqu):
            circuit = QuantumCircuit(2)
            circuit.cx(0, 1)
            circuit.x(0)
            circuit.y(0)
            circuit.z(0)
            circuit.cx(0, 1)

            basis_gates = ["u", "cx"]

            translator_result = tranqu.transpile(
                circuit,
                "qiskit",
                "qiskit",
                transpiler_options={
                    "translation_method": "translator",
                    "basis_gates": basis_gates,
                    "optimization_level": 0,
                },
            )

            synthesis_result = tranqu.transpile(
                circuit,
                "qiskit",
                "qiskit",
                transpiler_options={
                    "translation_method": "synthesis",
                    "basis_gates": basis_gates,
                    "optimization_level": 0,
                },
            )

            assert (
                translator_result.stats.after.n_gates
                > synthesis_result.stats.after.n_gates
            ), "The synthesis should have fewer gates."
            assert (
                translator_result.stats.after.depth > synthesis_result.stats.after.depth
            ), "The synthesis should have a shallower circuit."

        def test_invalid_translation_method_option(self, tranqu: Tranqu):
            with pytest.raises(
                TranspilerError,
                match="Invalid plugin name invalid_method for stage translation",
            ):
                tranqu.transpile(
                    QuantumCircuit(),
                    "qiskit",
                    "qiskit",
                    transpiler_options={"translation_method": "invalid_method"},
                )

    class TestSchedulingMethod:
        def test_scheduling_method(self, tranqu: Tranqu):
            circuit = QuantumCircuit(3)
            circuit.cx(0, 1)
            circuit.h(2)  # This gate will be scheduled

            backend = FakeSantiagoV2()

            no_scheduling_result = tranqu.transpile(
                circuit,
                "qiskit",
                "qiskit",
                transpiler_options={
                    "scheduling_method": None,
                    "optimization_level": 0,
                },
                device=backend,
                device_lib="qiskit",
            )
            asap_scheduling_result = tranqu.transpile(
                circuit,
                "qiskit",
                "qiskit",
                transpiler_options={
                    "scheduling_method": "asap",
                    "optimization_level": 0,
                },
                device=backend,
                device_lib="qiskit",
            )
            alap_scheduling_result = tranqu.transpile(
                circuit,
                "qiskit",
                "qiskit",
                transpiler_options={
                    "scheduling_method": "alap",
                    "optimization_level": 0,
                },
                device=backend,
                device_lib="qiskit",
            )

            assert not has_delay(no_scheduling_result)
            assert has_delay(asap_scheduling_result)
            assert has_delay(alap_scheduling_result)

        def test_invalid_scheduling_method(self, tranqu: Tranqu):
            with pytest.raises(
                TranspilerError,
                match="Invalid plugin name invalid_method for stage scheduling",
            ):
                tranqu.transpile(
                    QuantumCircuit(),
                    "qiskit",
                    "qiskit",
                    transpiler_options={
                        "scheduling_method": "invalid_method",
                    },
                )

    def test_instruction_durations_option(self, tranqu: Tranqu):
        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.cx(0, 1)

        h_duration = 50
        cx_duration = 500

        target = Target(dt=1e-9)
        target.add_instruction(
            HGate(), {(0,): InstructionProperties(duration=h_duration * 1e-9)}
        )
        target.add_instruction(
            CXGate(), {(0, 1): InstructionProperties(duration=cx_duration * 1e-9)}
        )

        result = tranqu.transpile(
            circuit,
            "qiskit",
            "qiskit",
            transpiler_options={
                "scheduling_method": "alap",
                "target": target,
                "optimization_level": 0,
            },
        )

        duration = result.transpiled_program.estimate_duration(target, unit="dt")
        assert duration == h_duration + cx_duration

    def test_dt_option(self, tranqu: Tranqu):
        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.cx(0, 1)

        backend = FakeSantiagoV2()
        default_dt = backend.configuration().dt

        default_dt_result = tranqu.transpile(
            circuit,
            "qiskit",
            "qiskit",
            transpiler_options={
                "dt": default_dt,
                "scheduling_method": "alap",
                "optimization_level": 0,
            },
            device=backend,
            device_lib="qiskit",
        )

        custom_dt_result = tranqu.transpile(
            circuit,
            "qiskit",
            "qiskit",
            transpiler_options={
                "dt": default_dt * 2,
                "scheduling_method": "alap",
                "optimization_level": 0,
            },
            device=backend,
            device_lib="qiskit",
        )

        default_duration = max(
            default_dt_result.transpiled_program.qubit_stop_time(i)
            for i in range(default_dt_result.transpiled_program.num_qubits)
        )
        custom_duration = max(
            custom_dt_result.transpiled_program.qubit_stop_time(i)
            for i in range(custom_dt_result.transpiled_program.num_qubits)
        )
        assert default_duration == custom_duration * 2

    class TestCalibrationKept:
        def test_calibration_kept_no_invalidate_warning_and_best_edge(
            self, tranqu: Tranqu
        ):
            device = {
                "device_id": "test_3q",
                "qubits": [
                    {
                        "id": 0,
                        "fidelity": 0.99,
                        "gate_duration": {"x": 60.0, "sx": 30.0, "rz": 0},
                    },
                    {
                        "id": 1,
                        "fidelity": 0.99,
                        "gate_duration": {"x": 60.0, "sx": 30.0, "rz": 0},
                    },
                    {
                        "id": 2,
                        "fidelity": 0.99,
                        "gate_duration": {"x": 60.0, "sx": 30.0, "rz": 0},
                    },
                ],
                "couplings": [
                    {
                        "control": 0,
                        "target": 1,
                        "fidelity": 0.80,
                        "gate_duration": {"cx": 60.0},
                    },
                    {
                        "control": 1,
                        "target": 2,
                        "fidelity": 0.99,
                        "gate_duration": {"cx": 60.0},
                    },
                ],
            }
            circuit = QuantumCircuit(2)
            circuit.cx(0, 1)
            basis_gates = ["sx", "rz", "cx", "id"]

            with warnings.catch_warnings(record=True) as recorded_warnings:
                warnings.simplefilter("always")
                result = tranqu.transpile(
                    circuit,
                    program_lib="qiskit",
                    transpiler_lib="qiskit",
                    device=device,
                    device_lib="oqtopus",
                    transpiler_options={
                        "basis_gates": basis_gates,
                        "seed_transpiler": 42,
                    },
                )

            invalidate_warnings = [
                w for w in recorded_warnings if "invalidate" in str(w.message).lower()
            ]
            assert len(invalidate_warnings) == 0

            # The chosen layout uses the best-calibrated edge (1, 2)
            mapping = result.virtual_physical_mapping.qubit_mapping
            assert (mapping[0], mapping[1]) == (1, 2)

        def test_output_gates_within_basis(self, tranqu: Tranqu):
            device = {
                "device_id": "test_3q",
                "qubits": [
                    {
                        "id": 0,
                        "fidelity": 0.99,
                        "gate_duration": {"x": 60.0, "sx": 30.0, "rz": 0},
                    },
                    {
                        "id": 1,
                        "fidelity": 0.99,
                        "gate_duration": {"x": 60.0, "sx": 30.0, "rz": 0},
                    },
                    {
                        "id": 2,
                        "fidelity": 0.99,
                        "gate_duration": {"x": 60.0, "sx": 30.0, "rz": 0},
                    },
                ],
                "couplings": [
                    {
                        "control": 0,
                        "target": 1,
                        "fidelity": 0.80,
                        "gate_duration": {"cx": 60.0},
                    },
                    {
                        "control": 1,
                        "target": 2,
                        "fidelity": 0.99,
                        "gate_duration": {"cx": 60.0},
                    },
                ],
            }
            circuit = QuantumCircuit(2)
            circuit.h(0)
            circuit.cx(0, 1)
            basis_gates = ["sx", "rz", "cx", "id"]

            result = tranqu.transpile(
                circuit,
                program_lib="qiskit",
                transpiler_lib="qiskit",
                device=device,
                device_lib="oqtopus",
                transpiler_options={
                    "basis_gates": basis_gates,
                    "seed_transpiler": 42,
                },
            )

            allowed_gates = set(basis_gates) | {"measure", "barrier", "delay", "reset"}
            assert all(
                inst.operation.name in allowed_gates
                for inst in result.transpiled_program.data
            )

        def test_basis_gates_with_coupling_map_still_works(self, tranqu: Tranqu):
            device = {
                "device_id": "test_3q",
                "qubits": [
                    {
                        "id": 0,
                        "fidelity": 0.99,
                        "gate_duration": {"x": 60.0, "sx": 30.0, "rz": 0},
                    },
                    {
                        "id": 1,
                        "fidelity": 0.99,
                        "gate_duration": {"x": 60.0, "sx": 30.0, "rz": 0},
                    },
                    {
                        "id": 2,
                        "fidelity": 0.99,
                        "gate_duration": {"x": 60.0, "sx": 30.0, "rz": 0},
                    },
                ],
                "couplings": [
                    {
                        "control": 0,
                        "target": 1,
                        "fidelity": 0.80,
                        "gate_duration": {"cx": 60.0},
                    },
                    {
                        "control": 1,
                        "target": 2,
                        "fidelity": 0.99,
                        "gate_duration": {"cx": 60.0},
                    },
                ],
            }
            circuit = QuantumCircuit(2)
            circuit.cx(0, 1)
            basis_gates = ["sx", "rz", "cx", "id"]

            result = tranqu.transpile(
                circuit,
                program_lib="qiskit",
                transpiler_lib="qiskit",
                device=device,
                device_lib="oqtopus",
                transpiler_options={
                    "basis_gates": basis_gates,
                    "coupling_map": [[0, 1], [1, 2]],
                    "seed_transpiler": 42,
                },
            )
            assert isinstance(result, TranspileResult)
            allowed_gates = set(basis_gates) | {"measure", "barrier", "delay", "reset"}
            assert all(
                inst.operation.name in allowed_gates
                for inst in result.transpiled_program.data
            )

    class TestDirectionAware:
        def test_direction_aware_bell_circuit_mapping_and_sx_count(
            self, tranqu: Tranqu
        ):
            device = {
                "device_id": "test_2q",
                "qubits": [
                    {
                        "id": 0,
                        "fidelity": 0.99,
                        "gate_duration": {"x": 60.0, "sx": 30.0, "rz": 0},
                    },
                    {
                        "id": 1,
                        "fidelity": 0.99,
                        "gate_duration": {"x": 60.0, "sx": 30.0, "rz": 0},
                    },
                ],
                "couplings": [
                    {
                        "control": 1,
                        "target": 0,
                        "fidelity": 0.95,
                        "gate_duration": {"cx": 60.0},
                    },
                ],
            }
            circuit = QuantumCircuit(2)
            circuit.h(0)
            circuit.cx(0, 1)

            result_aware = tranqu.transpile(
                circuit,
                program_lib="qiskit",
                transpiler_lib="qiskit",
                device=device,
                device_lib="oqtopus",
                transpiler_options={"direction_aware": True, "seed_transpiler": 42},
            )
            result_without_option = tranqu.transpile(
                circuit,
                program_lib="qiskit",
                transpiler_lib="qiskit",
                device=device,
                device_lib="oqtopus",
                transpiler_options={"seed_transpiler": 42},
            )

            # Maps logical 0 to physical 1
            mapping = result_aware.virtual_physical_mapping.qubit_mapping
            assert mapping[0] == 1
            assert mapping[1] == 0

            # No H sandwich -> fewer sx than without the option
            sx_aware = sum(
                1
                for inst in result_aware.transpiled_program.data
                if inst.operation.name == "sx"
            )
            sx_without = sum(
                1
                for inst in result_without_option.transpiled_program.data
                if inst.operation.name == "sx"
            )
            assert sx_aware < sx_without

            # All CX in registered direction (1 -> 0)
            cx_instructions = [
                inst
                for inst in result_aware.transpiled_program.data
                if inst.operation.name == "cx"
            ]
            assert len(cx_instructions) > 0
            for inst in cx_instructions:
                ctrl = result_aware.transpiled_program.find_bit(inst.qubits[0]).index
                tgt = result_aware.transpiled_program.find_bit(inst.qubits[1]).index
                assert (ctrl, tgt) == (1, 0)

        def test_direction_aware_without_device_raises_value_error(
            self, tranqu: Tranqu
        ):
            circuit = QuantumCircuit(2)
            circuit.h(0)
            circuit.cx(0, 1)

            with pytest.raises(
                ValueError, match="direction_aware requires a device or a target"
            ):
                tranqu.transpile(
                    circuit,
                    program_lib="qiskit",
                    transpiler_lib="qiskit",
                    transpiler_options={"direction_aware": True},
                )

        def test_direction_aware_with_coupling_map_raises_value_error(
            self, tranqu: Tranqu
        ):
            device = {
                "device_id": "test_2q",
                "qubits": [{"id": 0}, {"id": 1}],
                "couplings": [{"control": 1, "target": 0}],
            }
            circuit = QuantumCircuit(2)
            circuit.h(0)
            circuit.cx(0, 1)

            with pytest.raises(
                ValueError, match="direction_aware requires a device or a target"
            ):
                tranqu.transpile(
                    circuit,
                    program_lib="qiskit",
                    transpiler_lib="qiskit",
                    device=device,
                    device_lib="oqtopus",
                    transpiler_options={
                        "direction_aware": True,
                        "coupling_map": [[1, 0]],
                    },
                )

# mypy: disable-error-code="import-untyped"

import math

import pytest
from qiskit import QuantumCircuit
from qiskit.circuit import Parameter
from qiskit.circuit.library import CXGate, Measure, RZGate, SXGate, XGate
from qiskit.transpiler import InstructionProperties, Target

from tranqu import Tranqu
from tranqu.transpiler.qiskit_target_builder import (
    build_native_target,
    build_reverse_penalized_target,
    transpile_direction_aware,
)


@pytest.fixture
def tranqu() -> Tranqu:
    return Tranqu()


class TestQiskitTargetBuilder:
    class TestBuildNativeTarget:
        def test_keeps_instruction_properties_of_selected_gates(self):
            target = Target(num_qubits=2)
            sx_prop = InstructionProperties(duration=30e-9, error=0.001)
            rz_prop = InstructionProperties(duration=0.0, error=0.0)
            cx_prop = InstructionProperties(duration=100e-9, error=0.02)
            meas_prop = InstructionProperties(duration=1000e-9, error=0.01)

            target.add_instruction(SXGate(), {(0,): sx_prop, (1,): sx_prop})
            target.add_instruction(
                RZGate(Parameter("theta")), {(0,): rz_prop, (1,): rz_prop}
            )
            target.add_instruction(CXGate(), {(0, 1): cx_prop})
            target.add_instruction(Measure(), {(0,): meas_prop, (1,): meas_prop})

            native = build_native_target(target, basis_gates=["sx", "rz", "cx"])
            assert native is not None
            assert math.isclose(native["sx"][0,].duration, 30e-9)
            assert math.isclose(native["sx"][0,].error, 0.001)
            assert math.isclose(native["rz"][0,].duration, 0.0, abs_tol=1e-9)
            assert math.isclose(native["rz"][0,].error, 0.0, abs_tol=1e-9)
            assert math.isclose(native["cx"][0, 1].duration, 100e-9)
            assert math.isclose(native["cx"][0, 1].error, 0.02)

        def test_always_keeps_measure(self):
            target = Target(num_qubits=2)
            meas_prop = InstructionProperties(error=0.03)
            target.add_instruction(SXGate(), {(0,): None, (1,): None})
            target.add_instruction(Measure(), {(0,): meas_prop, (1,): meas_prop})

            # "measure" is not passed in basis_gates, but should be retained
            native = build_native_target(target, basis_gates=["sx"])
            assert native is not None
            assert "measure" in native.operation_names
            assert math.isclose(native["measure"][0,].error, 0.03)

        def test_drops_unselected_gates(self):
            target = Target(num_qubits=2)
            target.add_instruction(XGate(), {(0,): None, (1,): None})
            target.add_instruction(SXGate(), {(0,): None, (1,): None})
            target.add_instruction(CXGate(), {(0, 1): None})

            native = build_native_target(target, basis_gates=["sx", "cx"])
            assert native is not None
            assert "x" not in native.operation_names
            assert "sx" in native.operation_names
            assert "cx" in native.operation_names

        def test_adds_id_on_all_qubits(self):
            target = Target(num_qubits=3)
            target.add_instruction(SXGate(), {(0,): None, (1,): None, (2,): None})
            target.add_instruction(CXGate(), {(0, 1): None, (1, 2): None})

            assert "id" not in target.operation_names

            native = build_native_target(target, basis_gates=["sx", "cx", "id"])
            assert native is not None
            assert "id" in native.operation_names
            for q in range(3):
                assert (q,) in native["id"]
                assert native["id"][q,] is None

        def test_returns_none_for_unknown_2q_gate(self):
            target = Target(num_qubits=2)
            target.add_instruction(SXGate(), {(0,): None, (1,): None})
            target.add_instruction(CXGate(), {(0, 1): None})

            # ecr is a 2Q standard gate not in target
            native = build_native_target(target, basis_gates=["sx", "cx", "ecr"])
            assert native is None

            # cz is another 2Q standard gate not in target
            native_cz = build_native_target(target, basis_gates=["sx", "cx", "cz"])
            assert native_cz is None

    class TestBuildReversePenalizedTarget:
        def test_adds_reverse_cx_with_penalized_error(self):
            target = Target(num_qubits=2)
            e_cx = 0.03
            e_sx_0 = 0.01
            e_sx_1 = 0.02
            duration_cx = 120e-9

            target.add_instruction(
                SXGate(),
                {
                    (0,): InstructionProperties(error=e_sx_0),
                    (1,): InstructionProperties(error=e_sx_1),
                },
            )
            target.add_instruction(
                CXGate(),
                {(0, 1): InstructionProperties(error=e_cx, duration=duration_cx)},
            )

            planning = build_reverse_penalized_target(target)
            assert (1, 0) in planning["cx"]

            # Reverse CX error = 1 - (1 - e_cx) * (1 - e_sx_a)^2 * (1 - e_sx_b)^2
            expected_reverse_fidelity = (
                (1.0 - e_cx) * ((1.0 - e_sx_0) ** 2) * ((1.0 - e_sx_1) ** 2)
            )
            expected_reverse_error = 1.0 - expected_reverse_fidelity

            reverse_prop = planning["cx"][1, 0]
            assert math.isclose(
                reverse_prop.error, expected_reverse_error, rel_tol=1e-9
            )
            assert math.isclose(reverse_prop.duration, duration_cx)

            # Original forward CX remains intact
            forward_prop = planning["cx"][0, 1]
            assert math.isclose(forward_prop.error, e_cx)
            assert math.isclose(forward_prop.duration, duration_cx)

        def test_keeps_already_bidirectional_pairs_unchanged(self):
            target = Target(num_qubits=2)
            e_01 = 0.02
            e_10 = 0.03
            target.add_instruction(
                SXGate(),
                {
                    (0,): InstructionProperties(error=0.01),
                    (1,): InstructionProperties(error=0.01),
                },
            )
            target.add_instruction(
                CXGate(),
                {
                    (0, 1): InstructionProperties(error=e_01),
                    (1, 0): InstructionProperties(error=e_10),
                },
            )

            planning = build_reverse_penalized_target(target)
            assert math.isclose(planning["cx"][0, 1].error, e_01)
            assert math.isclose(planning["cx"][1, 0].error, e_10)

        def test_keeps_other_operations(self):
            target = Target(num_qubits=2)
            x_prop = InstructionProperties(duration=50e-9, error=0.002)
            meas_prop = InstructionProperties(error=0.05)
            rz_prop = InstructionProperties(duration=0.0, error=0.0)

            target.add_instruction(XGate(), {(0,): x_prop})
            target.add_instruction(
                RZGate(Parameter("theta")), {(0,): rz_prop, (1,): rz_prop}
            )
            target.add_instruction(Measure(), {(0,): meas_prop, (1,): meas_prop})
            target.add_instruction(
                CXGate(), {(0, 1): InstructionProperties(error=0.01)}
            )

            planning = build_reverse_penalized_target(target)
            assert math.isclose(planning["x"][0,].duration, x_prop.duration)
            assert math.isclose(planning["x"][0,].error, x_prop.error)
            assert math.isclose(planning["measure"][0,].error, meas_prop.error)
            assert math.isclose(
                planning["rz"][0,].duration, rz_prop.duration, abs_tol=1e-9
            )

    class TestTranspileDirectionAware:
        def test_output_contains_only_registered_cx_directions(self):
            # Target with 3 qubits and strictly one-way couplings: 1->0 and 1->2
            target = Target(num_qubits=3)
            target.add_instruction(
                SXGate(),
                {
                    (0,): InstructionProperties(error=0.001),
                    (1,): InstructionProperties(error=0.001),
                    (2,): InstructionProperties(error=0.001),
                },
            )
            target.add_instruction(
                RZGate(Parameter("theta")),
                {
                    (0,): InstructionProperties(error=0.0, duration=0.0),
                    (1,): InstructionProperties(error=0.0, duration=0.0),
                    (2,): InstructionProperties(error=0.0, duration=0.0),
                },
            )
            registered_cx = {(1, 0), (1, 2)}
            target.add_instruction(
                CXGate(),
                {pair: InstructionProperties(error=0.01) for pair in registered_cx},
            )
            target.add_instruction(
                Measure(),
                {(0,): None, (1,): None, (2,): None},
            )

            # Program with CX gates in reverse direction (0->1 and 2->1)
            circuit = QuantumCircuit(3)
            circuit.cx(0, 1)
            circuit.cx(2, 1)

            transpiled = transpile_direction_aware(circuit, target, seed_transpiler=42)

            cx_found = False
            for inst in transpiled.data:
                if inst.operation.name == "cx":
                    cx_found = True
                    ctrl = transpiled.find_bit(inst.qubits[0]).index
                    tgt = transpiled.find_bit(inst.qubits[1]).index
                    assert (ctrl, tgt) in registered_cx
            assert cx_found

# mypy: disable-error-code="import-untyped"

"""Targets and pass managers that keep a device's calibration in Qiskit.

Passing ``basis_gates`` together with ``backend`` to Qiskit makes it rebuild the
Target with ``Target.from_configuration``, which drops every error rate and
duration. The layout passes then choose qubits by index instead of quality.
:func:`build_native_target` restricts the device Target to the native gates
while copying their ``InstructionProperties``, so the calibration survives.

:func:`build_reverse_penalized_target` and :func:`transpile_direction_aware`
handle devices whose CX can only run in the registered direction. Layout, routing
and translation run on a planning-only Target where a reversed CX is allowed at
the cost of CX + 4 H, a direction-strict ``VF2PostLayout`` then picks the cheapest
orientation, and the final translation runs on the real one-way Target so no
reversed CX is ever emitted.
"""

from qiskit import QuantumCircuit
from qiskit.circuit.library import CXGate, get_standard_gate_name_mapping
from qiskit.transpiler import (
    ConditionalController,
    InstructionProperties,
    PassManager,
    Target,
    generate_preset_pass_manager,
)
from qiskit.transpiler.passes import ApplyLayout, VF2PostLayout
from qiskit.transpiler.passes.layout.vf2_post_layout import VF2PostLayoutStopReason

# Operations that Qiskit always accepts regardless of ``basis_gates``.
_ALWAYS_SUPPORTED = frozenset({"measure", "reset", "delay", "barrier"})


def build_native_target(target: Target, basis_gates: list[str]) -> Target | None:
    """Restrict ``target`` to ``basis_gates`` while keeping the calibration.

    Non-gate operations of ``target`` (measure, reset, delay) are always kept.
    A single-qubit standard gate that ``target`` lacks (e.g. ``id``) is added on
    every qubit without calibration.

    Args:
        target (Target): The device Target with calibration.
        basis_gates (list[str]): The native gate names.

    Returns:
        Target | None: The restricted Target, or None if a multi-qubit gate in
            ``basis_gates`` is not in ``target`` (its connectivity is unknown).

    """
    native = Target(
        num_qubits=target.num_qubits,
        dt=target.dt,
        concurrent_measurements=target.concurrent_measurements,
    )
    standard_gates = get_standard_gate_name_mapping()
    names = [name for name in target.operation_names if name in _ALWAYS_SUPPORTED]
    names += [name for name in dict.fromkeys(basis_gates) if name not in names]

    for name in names:
        if name in target.operation_names:
            native.add_instruction(
                target.operation_from_name(name), dict(target[name]), name=name
            )
        elif name in _ALWAYS_SUPPORTED:
            continue
        elif name in standard_gates and standard_gates[name].num_qubits == 1:
            native.add_instruction(
                standard_gates[name],
                {(qubit,): None for qubit in range(target.num_qubits or 0)},
            )
        else:
            return None
    return native


def build_reverse_penalized_target(target: Target) -> Target:
    """Build a planning-only Target where CX may also run in reverse.

    A reversed CX is executed as CX sandwiched by H on both qubits, and each H
    costs one ``sx`` pulse (``rz`` is virtual). Its error is therefore that of
    the registered CX combined with two ``sx`` on each qubit. This Target must
    not be used for the final translation, since the device cannot run the
    reversed CX itself.

    Args:
        target (Target): The real one-way Target.

    Returns:
        Target: The planning Target.

    """
    planning = Target(
        num_qubits=target.num_qubits,
        dt=target.dt,
        concurrent_measurements=target.concurrent_measurements,
    )
    for name in target.operation_names:
        if name != "cx":
            planning.add_instruction(
                target.operation_from_name(name), dict(target[name]), name=name
            )
    if "cx" not in target.operation_names:
        return planning

    def sx_fidelity(qubit: int) -> float:
        if "sx" not in target.operation_names:
            return 1.0
        props = target["sx"].get((qubit,))
        return 1.0 - (props.error or 0.0) if props is not None else 1.0

    cx_props = dict(target["cx"])
    for (control, tgt), props in list(cx_props.items()):
        if (tgt, control) in cx_props:
            continue
        cx_error = props.error if props is not None else None
        sx_part = sx_fidelity(control) ** 2 * sx_fidelity(tgt) ** 2
        fidelity = (1.0 - (cx_error or 0.0)) * sx_part
        cx_props[tgt, control] = InstructionProperties(
            error=1.0 - fidelity,
            duration=props.duration if props is not None else None,
        )
    planning.add_instruction(CXGate(), cx_props)
    return planning


def transpile_direction_aware(
    program: QuantumCircuit, target: Target, **options: object
) -> QuantumCircuit:
    """Transpile ``program`` choosing the layout with direction-aware costs.

    Args:
        program (QuantumCircuit): The circuit to transpile.
        target (Target): The real one-way Target.
        **options: Options for ``generate_preset_pass_manager``.

    Returns:
        QuantumCircuit: The transpiled circuit, with only registered CX directions.

    """
    planning_target = build_reverse_penalized_target(target)

    plan = generate_preset_pass_manager(target=planning_target, **options)
    if options.get("initial_layout") is None:
        # A user-given layout must not be replaced. The strict VF2PostLayout
        # needs a circuit in the Target's gates, so it runs after translation.
        plan.post_translation = _strict_post_layout(
            planning_target, options.get("seed_transpiler")
        )
    plan.optimization = plan.scheduling = None
    planned = plan.run(program)

    finish = generate_preset_pass_manager(target=target, **options)
    finish.init = finish.layout = finish.routing = None
    transpiled = finish.run(planned)
    # The finishing stages add no permutation, so the planning layout holds.
    transpiled._layout = planned.layout  # ruff: ignore[private-member-access]
    return transpiled


def _strict_post_layout(target: Target, seed: object) -> PassManager:
    def solution_found(property_set: dict[str, object]) -> bool:
        return (
            property_set["VF2PostLayout_stop_reason"]
            is VF2PostLayoutStopReason.SOLUTION_FOUND
        )

    return PassManager([
        VF2PostLayout(target=target, seed=seed, strict_direction=True),
        ConditionalController(ApplyLayout(), condition=solution_found),
    ])

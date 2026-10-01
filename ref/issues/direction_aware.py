"""Proposed transpiler fixes (ISSUES.md 3 + 4A + 4B), usable directly or as a Tranqu transpiler.

3.  Native gates are selected by building a native-only Target that keeps the calibration
    (InstructionProperties), instead of passing basis_gates (which makes Qiskit drop the errors).
4A. Virtual gates (rz) are scored with error 0 / duration 0.
4B. Layout/routing run on a planning-only Target where reversed CX is allowed but costs CX + 4 H;
    a direction-strict VF2PostLayout then picks the cheapest orientation, and the final translation
    runs on the real one-way Target, so device-gateway never receives a reversed CX.

Tranqu usage:
    tranqu = Tranqu(); register(tranqu)
    tranqu.transpile(program=qc, program_lib="qiskit", transpiler_lib=TRANSPILER_LIB,
                     transpiler_options=dict(native_gates=["rz", "sx", "cx", "measure"], optimization_level=2),
                     device=device_json, device_lib="oqtopus")
"""
from qiskit.circuit.library import CXGate
from qiskit.transpiler import ConditionalController, InstructionProperties, PassManager, Target, generate_preset_pass_manager
from qiskit.transpiler.passes import ApplyLayout, VF2PostLayout
from qiskit.transpiler.passes.layout.vf2_post_layout import VF2PostLayoutStopReason
from tranqu.device_converter.oqtopus_to_qiskit_device_converter import OqtoqusToQiskitDeviceConverter
from tranqu.transpile_result import TranspileResult
from tranqu.transpiler.qiskit_transpiler import QiskitTranspiler

TRANSPILER_LIB = "qiskit_direction_aware"


def native_target(target, names, virtual=()):
    """Keep only the native instructions, copying InstructionProperties (error/duration) as-is.

    Gates in `virtual` (e.g. rz) get error 0 / duration 0 instead of the converter's 1Q fidelity.
    """
    t = Target(num_qubits=target.num_qubits, dt=target.dt)
    for name in names:
        props = dict(target[name])
        if name in virtual:
            props = {q: InstructionProperties(error=0.0, duration=0.0) for q in props}
        t.add_instruction(target.operation_from_name(name), props)
    return t


def penalized_target(target):
    """Planning-only Target: CX also allowed in reverse, with the error of CX + 4 H (= 2 sx on each qubit)."""
    P = Target(num_qubits=target.num_qubits, dt=target.dt)
    for name in target.operation_names:
        if name != "cx":
            P.add_instruction(target.operation_from_name(name), dict(target[name]))
    sx_err = lambda q: target["sx"][(q,)].error or 0.0
    props = dict(target["cx"])
    for (a, b), p in list(props.items()):
        f = (1 - p.error) * (1 - sx_err(a)) ** 2 * (1 - sx_err(b)) ** 2
        props[(b, a)] = InstructionProperties(error=1 - f, duration=p.duration)
    P.add_instruction(CXGate(), props)
    return P


def strict_post_layout(target, seed):
    found = lambda ps: ps["VF2PostLayout_stop_reason"] is VF2PostLayoutStopReason.SOLUTION_FOUND
    return PassManager([VF2PostLayout(target=target, seed=seed, strict_direction=True), ConditionalController(ApplyLayout(), condition=found)])


def plan_then_finish(target, plan_target, qc, seed, level=2):
    """Layout/routing on `plan_target` + direction-strict VF2PostLayout, then translate on the real `target`.

    Returns (routed, out): `routed` is the circuit before translation (may contain reversed CX).
    """
    plan = generate_preset_pass_manager(optimization_level=level, target=plan_target, seed_transpiler=seed)
    plan.post_routing = strict_post_layout(plan_target, seed)
    plan.translation = plan.optimization = plan.scheduling = None
    routed = plan.run(qc)
    fin = generate_preset_pass_manager(optimization_level=level, target=target, seed_transpiler=seed)
    fin.init = fin.layout = fin.routing = None
    out = fin.run(routed)
    out._layout = routed.layout  # the finishing stage adds no permutation
    return routed, out


def solve(target, qc, native_gates=None, virtual=("rz",), optimization_level=2, seed_transpiler=None):
    """3 + 4A + 4B in one call. Returns (routed, out)."""
    nt = native_target(target, native_gates or list(target.operation_names), set(virtual))
    return plan_then_finish(nt, penalized_target(nt), qc, seed_transpiler, optimization_level)


class DirectionAwareQiskitTranspiler(QiskitTranspiler):
    """Tranqu transpiler running `solve`. Options: native_gates, virtual_gates, optimization_level, seed_transpiler."""

    OPTIONS = {"native_gates", "virtual_gates", "optimization_level", "seed_transpiler"}

    def transpile(self, program, options=None, device=None):
        opts = dict(options or {})
        unknown = set(opts) - self.OPTIONS
        if unknown:  # e.g. basis_gates would bring back issue 2
            raise ValueError(f"unsupported options: {sorted(unknown)}; use native_gates instead of basis_gates")
        _, out = solve(device.target, program, native_gates=opts.get("native_gates"), virtual=opts.get("virtual_gates", ("rz",)),
                       optimization_level=opts.get("optimization_level", 2), seed_transpiler=opts.get("seed_transpiler"))
        stats = {"before": self._stats_extractor.extract_stats_from(program), "after": self._stats_extractor.extract_stats_from(out)}
        return TranspileResult(out, stats, self._layout_mapper.create_mapping_from_layout(out))


def register(tranqu):
    tranqu.register_transpiler(TRANSPILER_LIB, DirectionAwareQiskitTranspiler(program_lib="qiskit"))
    tranqu.register_device_converter("oqtopus", TRANSPILER_LIB, OqtoqusToQiskitDeviceConverter())

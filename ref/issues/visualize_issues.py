"""Visualise two transpiler issues on a sparse ("歯抜け") topology.

1. CX direction: layouts that place logical CX against the directed coupling,
   so GateDirection-style fixes add H sandwiches (more 1Q gates / depth).
2. Calibration ignored: backend + basis_gates makes Qiskit rebuild the Target
   without error rates, so noisy qubits / couplings get selected.

Run from tp/:  .venv/bin/python issues/visualize_issues.py [--topology bad_bridge]
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "issues"
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".mpl-cache"))
os.environ.setdefault("QISKIT_NUM_PROCS", "1")
os.environ.setdefault("RAYON_NUM_THREADS", "1")
sys.path.insert(0, str(ROOT))

import argparse
import copy
import json
import math
import statistics
import warnings

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
from matplotlib.lines import Line2D
from qiskit import QuantumCircuit, transpile
from qiskit.quantum_info import Statevector
from qiskit.transpiler import generate_preset_pass_manager
from tranqu import Tranqu
from tranqu.device_converter.oqtopus_to_qiskit_device_converter import OqtoqusToQiskitDeviceConverter

from benchmark import circuits
from issues.direction_aware import TRANSPILER_LIB, native_target, penalized_target, plan_then_finish, register, solve
from issues.direction_aware import strict_post_layout as _strict_post_layout

BASIS = ["id", "sx", "x", "rz", "cx"]
# Example native set for the proposed fix (x dropped to show the subset really restricts the output).
NATIVE = ["rz", "sx", "cx", "measure"]
SEEDS = range(10)
# rz is a virtual (frame) gate: duration 0 in the JSON, so it is scored as error-free.
VIRTUAL = {"rz"}
# Thresholds used only for colouring "bad" elements in the figures.
BAD_CX = 0.93
BAD_MEAS = 0.10
# Palette (dataviz reference palette, light mode)
BLUE, ORANGE, RED, GRAY, INK, MUTED = "#2a78d6", "#eb6834", "#e34948", "#b5b4ae", "#0b0b0b", "#52514e"
plt.rcParams.update({"font.size": 9, "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED})


# ---------------------------------------------------------------- device model
class Device:
    def __init__(self, data):
        self.data = data
        self.backend = OqtoqusToQiskitDeviceConverter().convert(data)
        self.target = self.backend.target
        self.edges = {(c["control"], c["target"]) for c in data["couplings"]}
        self.cx_fid = {(c["control"], c["target"]): c["fidelity"] for c in data["couplings"]}
        self.q = {q["id"]: q for q in data["qubits"]}
        # Same definition as the Tranqu converter (mean of the two conditional errors).
        self.meas = {i: (q["meas_error"]["prob_meas1_prep0"] + q["meas_error"]["prob_meas0_prep1"]) / 2 for i, q in self.q.items()}
        self.pos = {i: (q["position"]["x"], -q["position"]["y"]) for i, q in self.q.items()}
        self.ug = nx.Graph(list(self.edges))
        bi = copy.deepcopy(data)
        bi["couplings"] += [dict(c, control=c["target"], target=c["control"]) for c in data["couplings"]]
        self.bi_backend = OqtoqusToQiskitDeviceConverter().convert(bi)

        self.dur_1q = {i: q.get("gate_duration", {}) for i, q in self.q.items()}
        # Assumption: device-gateway builds one CX from two RZX90 pulses (plus virtual/short 1Q).
        self.dur_cx = {(c["control"], c["target"]): 2 * c["gate_duration"]["rzx90"] for c in data["couplings"]}

    def _ops(self, out, skip=()):
        for inst in out.data:
            name = inst.operation.name
            if name == "barrier" or name in skip:
                continue
            qargs = tuple(out.find_bit(x).index for x in inst.qubits)
            if name == "cx" and qargs not in self.edges:  # only in the both-direction reference
                qargs = qargs[::-1]
            yield name, qargs

    def nll(self, out):
        """-sum log(1-error) over gates and measurements (rz virtual = 0), scored with the true Target."""
        return sum(-math.log1p(-self.target[n][q].error) for n, q in self._ops(out, VIRTUAL))

    def gate_nll(self, out):
        """Same as nll but without measurements: the part the CX direction can change."""
        return sum(-math.log1p(-self.target[n][q].error) for n, q in self._ops(out, VIRTUAL | {"measure"}))

    def duration(self, out):
        """Critical-path time [ns] with JSON durations (rz = 0, CX = 2 x RZX90, measure excluded)."""
        t = [0.0] * out.num_qubits
        for n, q in self._ops(out, {"measure"}):
            d = self.dur_cx[q] if n == "cx" else self.dur_1q[q[0]].get(n, 0)
            start = max(t[x] for x in q)
            for x in q:
                t[x] = start + d
        return max(t)

    def reversed_cx(self, circ):
        return sum(1 for i in circ.data if i.operation.name == "cx" and tuple(circ.find_bit(q).index for q in i.qubits) not in self.edges)

    def simple_paths(self, n):
        res = []

        def dfs(p):
            if len(p) == n:
                res.append(p)
                return
            for v in self.ug[p[-1]]:
                if v not in p:
                    dfs(p + [v])

        for s in self.ug:
            dfs([s])
        return res


def n1q(c):
    return sum(1 for i in c.data if len(i.qubits) == 1 and i.operation.name not in ("measure", "barrier"))


def phys1q(c):
    """Physical 1Q pulses (sx, x); rz is virtual."""
    ops = c.count_ops()
    return ops.get("sx", 0) + ops.get("x", 0)


def metrics(dev, c):
    return dict(phys=phys1q(c), dur=dev.duration(c), gnll=dev.gate_nll(c), nll=dev.nll(c), n1=n1q(c), depth=c.depth(),
                cx=c.count_ops().get("cx", 0))


def ghz(n):
    q = QuantumCircuit(n)
    q.h(0)
    for i in range(n - 1):
        q.cx(i, i + 1)
    q.measure_all()
    return q


def opts(dev, level, seed, mode, backend=None):
    kw = dict(optimization_level=level, backend=backend or dev.backend, seed_transpiler=seed)
    if mode == "default":  # what t.py / Tranqu users pass today
        kw["basis_gates"] = BASIS
    return kw


def run(dev, qc, level, seed, mode, **extra):
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        out = transpile(qc, **opts(dev, level, seed, mode), **extra)
    return out, [str(x.message) for x in w if "invalidate" in str(x.message)]


def layout_of(out):
    return list(out.layout.initial_index_layout(filter_ancillas=True))


# ------------------------------------------------------------------- drawing
def draw_device(ax, dev, path=None, labels="full", title=None):
    """device.py style: arrows control->target, node = id/1Q fidelity, edge = 2Q fidelity."""
    G = nx.DiGraph(list(dev.edges))
    used = set(path or [])
    path_edges = {}
    if path:
        for a, b in zip(path, path[1:]):
            path_edges[(a, b) if (a, b) in dev.edges else (b, a)] = (a, b) in dev.edges
    node_size = 1500 if labels == "full" else 520
    face = ["#fbe0df" if dev.meas[n] > BAD_MEAS else "#d9f2d0" for n in G.nodes]
    lw = [2.6 if n in used else 1.0 for n in G.nodes]
    ec = [BLUE if n in used else INK for n in G.nodes]
    nx.draw_networkx_nodes(G, dev.pos, ax=ax, node_size=node_size, node_color=face, edgecolors=ec, linewidths=lw)
    if labels == "full":
        nl = {n: f"{n}\n{dev.q[n]['fidelity']:.4f}\nro {dev.meas[n]:.3f}" for n in G.nodes}
        nx.draw_networkx_labels(G, dev.pos, labels=nl, ax=ax, font_size=7.5, font_weight="bold")
    else:
        nx.draw_networkx_labels(G, dev.pos, ax=ax, font_size=8, font_weight="bold")
    base = [e for e in G.edges if e not in path_edges]
    nx.draw_networkx_edges(G, dev.pos, edgelist=base, ax=ax, node_size=node_size, arrowstyle="-|>", arrowsize=16,
                           edge_color=[RED if dev.cx_fid[e] < BAD_CX else (GRAY if path else "dimgray") for e in base],
                           width=[2.4 if dev.cx_fid[e] < BAD_CX else 1.4 for e in base])
    for e, native in path_edges.items():
        nx.draw_networkx_edges(G, dev.pos, edgelist=[e], ax=ax, node_size=node_size, arrowstyle="-|>", arrowsize=20,
                               edge_color=BLUE if native else ORANGE, width=3.6, style="solid" if native else (0, (2, 1.2)))
    if labels == "full":
        el = {e: f"{dev.cx_fid[e]:.4f}" for e in G.edges}
        nx.draw_networkx_edge_labels(G, dev.pos, edge_labels=el, ax=ax, font_size=7, font_color="darkred", rotate=False,
                                     bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none", alpha=0.85))
    else:
        # Beside the edge (not on it): short vertical edges would otherwise hide under the nodes.
        for (a, b), native in path_edges.items():
            (x0, y0), (x1, y1) = dev.pos[a], dev.pos[b]
            mx, my = (x0 + x1) / 2, (y0 + y1) / 2
            vertical = abs(x1 - x0) < 1e-6
            txt = f"{dev.cx_fid[(a, b)]:.3f}" + ("" if native else " 逆向き")
            ax.text(mx + (0.22 if vertical else 0), my + (0 if vertical else 0.42), txt, fontsize=7.5, color="darkred",
                    ha="left" if vertical else "center", va="center" if vertical else "bottom",
                    bbox=dict(boxstyle="round,pad=0.1", fc="white", ec="none", alpha=0.85))
    if title:
        ax.set_title(title, fontsize=9, loc="left")
    ax.set_aspect("equal")
    ax.margins(0.08)
    ax.axis("off")


def jp_font():
    for f in ("Hiragino Sans", "Hiragino Maru Gothic Pro", "AppleGothic", "Noto Sans CJK JP"):
        if any(f in x.name for x in matplotlib.font_manager.fontManager.ttflist):
            plt.rcParams["font.family"] = "sans-serif"
            plt.rcParams["font.sans-serif"] = [f] + plt.rcParams["font.sans-serif"]
            return


# ---------------------------------------------------------------- experiments
MODES = {"current": "現状（backend + basis_gates）", "native": "3 のみ（native Target）", "solution": "3 + A + B"}


def compile_mode(dev, data, tq, qc, seed, mode, level=2):
    """(routed, out) for the three configurations compared in chapter 5. 'solution' is also run through Tranqu."""
    if mode == "solution":
        routed, out = solve(dev.target, qc, native_gates=NATIVE, optimization_level=level, seed_transpiler=seed)
        via = tq.transpile(program=qc, program_lib="qiskit", transpiler_lib=TRANSPILER_LIB,
                           transpiler_options=dict(native_gates=NATIVE, optimization_level=level, seed_transpiler=seed),
                           device=copy.deepcopy(data), device_lib="oqtopus").transpiled_program
        assert via.count_ops() == out.count_ops() and layout_of(via) == layout_of(out)
    else:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            if mode == "current":
                kw = dict(backend=dev.backend, basis_gates=[g for g in NATIVE if g != "measure"])
            else:
                kw = dict(target=native_target(dev.target, NATIVE))
            pm = generate_preset_pass_manager(optimization_level=level, seed_transpiler=seed, **kw)
            out = pm.run(qc)
            pm.translation = pm.optimization = pm.scheduling = None
            routed = pm.run(qc)
    assert set(out.count_ops()) - {"barrier"} <= set(NATIVE)
    assert all(n != "cx" or q in dev.edges for n, q in dev._ops(out))
    return routed, out


def solution_cases(dev, data, tq, all_cands):
    """Swap-free GHZ/Bell, seed 0, L2: current vs 3 vs 3+A+B, ranked among all placements."""
    rows = []
    for n in (2, 4, 5, 8):
        name = "bell2" if n == 2 else f"ghz{n}"
        cands = all_cands[name]
        for mode in MODES:
            routed, out = compile_mode(dev, data, tq, ghz(n), 0, mode)
            L = layout_of(out)
            v = dev.nll(out)
            rows.append(dict(circuit=name, mode=mode, layout=L, rev=sum((a, b) not in dev.edges for a, b in zip(L, L[1:])), **metrics(dev, out),
                             rank=1 + sum(c["nll"] < v - 1e-9 for c in cands), n_cand=len(cands), best=cands[0],
                             cx_used=[(a, b) if (a, b) in dev.edges else (b, a) for a, b in zip(L, L[1:])]))
    return rows


def solution_bench(dev, data, tq):
    """All circuits x 10 seeds, L2: current vs 3 vs 3+A+B."""
    cs = {"bell2": ghz(2), "ghz4": ghz(4), "ghz5": ghz(5), "ghz8": ghz(8)}
    cs.update((k, v) for k, v in circuits().items() if k != "bell2")
    rows = []
    for name, qc in cs.items():
        for seed in SEEDS:
            row = dict(circuit=name, seed=seed)
            for mode in MODES:
                routed, out = compile_mode(dev, data, tq, qc, seed, mode)
                row[mode] = dict(rev=dev.reversed_cx(routed), layout=layout_of(out), **metrics(dev, out))
            rows.append(row)
    return rows


def enumerate_ghz(dev, n):
    """All swap-free placements of GHZ-n (= simple paths with orientation)."""
    qc = ghz(n)
    cands = []
    for p in dev.simple_paths(n):
        out = transpile(qc, backend=dev.backend, initial_layout=p, optimization_level=1, seed_transpiler=0)
        cands.append(dict(path=p, rev=sum((a, b) not in dev.edges for a, b in zip(p, p[1:])), **metrics(dev, out)))
    return qc, sorted(cands, key=lambda c: c["nll"])


def case_table(dev, sizes=(2, 4, 5, 8)):
    rows = []
    for n in sizes:
        qc, cands = enumerate_ghz(dev, n)
        by_path = {tuple(c["path"]): c for c in cands}
        for mode in ("default", "target_only"):
            for level in (1, 2, 3):
                out, warn = run(dev, qc, level, 0, mode)
                L = layout_of(out)
                mirror = by_path[tuple(reversed(L))]
                v = dev.nll(out)
                rows.append(dict(circuit=f"ghz{n}" if n > 2 else "bell2", n=n, mode=mode, level=level, layout=L,
                                 rev=sum((a, b) not in dev.edges for a, b in zip(L, L[1:])), **metrics(dev, out),
                                 rank=1 + sum(c["nll"] < v - 1e-9 for c in cands), n_cand=len(cands), warned=bool(warn),
                                 mirror=dict(mirror, layout=list(reversed(L))),
                                 best=cands[0], min_rev=min(c["rev"] for c in cands),
                                 cx_used=[(a, b) if (a, b) in dev.edges else (b, a) for a, b in zip(L, L[1:])]))
        rows[-1]["_cands"] = cands
    return rows


def direction_cost(dev):
    """Same routed circuit, finished on the directed Target vs a both-direction Target."""
    cs = circuits()
    rows = []
    for name, qc in cs.items():
        for mode in ("default", "target_only"):
            for level in (1, 2):
                for seed in SEEDS:
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        pm = generate_preset_pass_manager(**opts(dev, level, seed, mode))
                        full = pm.run(qc)
                        pm.translation = pm.optimization = pm.scheduling = None
                        routed = pm.run(qc)
                        fin = {}
                        for key, be in (("dir", dev.backend), ("bi", dev.bi_backend)):
                            f = generate_preset_pass_manager(**opts(dev, level, seed, mode, backend=be))
                            f.init = f.layout = f.routing = None
                            fin[key] = f.run(routed)
                    assert fin["dir"].count_ops() == full.count_ops()
                    ops = routed.count_ops()
                    L = layout_of(full)
                    rows.append(dict(circuit=name, mode=mode, level=level, seed=seed,
                                     logical_cx=ops.get("cx", 0), rev_cx=dev.reversed_cx(routed), swaps=ops.get("swap", 0),
                                     cx=full.count_ops().get("cx", 0), n1_dir=n1q(fin["dir"]), n1_bi=n1q(fin["bi"]),
                                     depth_dir=fin["dir"].depth(), depth_bi=fin["bi"].depth(), cx_bi=fin["bi"].count_ops().get("cx", 0),
                                     phys_dir=phys1q(fin["dir"]), phys_bi=phys1q(fin["bi"]),
                                     dur_dir=dev.duration(fin["dir"]), dur_bi=dev.duration(fin["bi"]),
                                     gnll_dir=dev.gate_nll(fin["dir"]), gnll_bi=dev.gate_nll(fin["bi"]),
                                     nll=dev.nll(full), layout=L,
                                     used_qubits=sorted({full.find_bit(q).index for i in full.data if i.operation.name != "barrier" for q in i.qubits}),
                                     used_cx=sorted({tuple(full.find_bit(q).index for q in i.qubits) for i in full.data if i.operation.name == "cx"})))
    return rows


def native_solution(dev, data):
    """Proposed fix for issue 2: pass a native-only Target via `target=` instead of basis_gates."""
    nt = native_target(dev.target, NATIVE)
    tq = Tranqu()
    rows = []
    cs = {"bell2": ghz(2), "ghz4": ghz(4), "ghz5": ghz(5), "ghz8": ghz(8)}
    cs.update((k, v) for k, v in circuits().items() if k != "bell2")
    for name, qc in cs.items():
        for seed in SEEDS:
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                a = transpile(qc, target=nt, optimization_level=2, seed_transpiler=seed)
                via = tq.transpile(program=qc, program_lib="qiskit", transpiler_lib="qiskit",
                                   transpiler_options=dict(target=nt, optimization_level=2, seed_transpiler=seed),
                                   device=copy.deepcopy(data), device_lib="oqtopus").transpiled_program
            native_warn = sum("invalidate" in str(x.message) for x in w)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                b = transpile(qc, backend=dev.backend, basis_gates=[g for g in NATIVE if g != "measure"], optimization_level=2, seed_transpiler=seed)
            ops = set(a.count_ops()) - {"barrier"}
            assert ops <= set(NATIVE), ops
            assert layout_of(via) == layout_of(a) and via.count_ops() == a.count_ops()
            rows.append(dict(circuit=name, seed=seed, warnings=native_warn, ops=sorted(ops),
                             native=dict(layout=layout_of(a), nll=dev.nll(a), cx=a.count_ops().get("cx", 0)),
                             basis=dict(layout=layout_of(b), nll=dev.nll(b), cx=b.count_ops().get("cx", 0))))
    return rows


def direction_solution(dev):
    """Proposed fix B for issue 1 vs plain L2 (calibrated Target) and the hard strict_direction variant."""
    P = penalized_target(dev.target)
    cs = {"bell2": ghz(2), "ghz4": ghz(4), "ghz5": ghz(5), "ghz8": ghz(8)}
    cs.update((k, v) for k, v in circuits().items() if k != "bell2")
    rows = []
    for name, qc in cs.items():
        for seed in SEEDS:
            res = {}
            for key in ("base", "hard", "penalty"):
                if key == "penalty":
                    routed, out = plan_then_finish(dev.target, P, qc, seed)
                else:
                    pm = generate_preset_pass_manager(optimization_level=2, target=dev.target, seed_transpiler=seed)
                    if key == "hard":  # direction must match exactly; no penalty for "almost"
                        pm.post_routing = _strict_post_layout(dev.target, seed)
                    out = pm.run(qc)
                    pm.translation = pm.optimization = pm.scheduling = None
                    routed = pm.run(qc)
                assert all(dev.target.instruction_supported(n, q) and (n != "cx" or q in dev.edges) for n, q in dev._ops(out)), (name, key)
                res[key] = dict(rev=dev.reversed_cx(routed), layout=layout_of(out), **metrics(dev, out))
                if key == "penalty" and name.startswith(("bell", "ghz")) and seed < 3:
                    # GHZ state must appear on the final physical qubits.
                    c = qc.num_qubits
                    sv = Statevector(out.remove_final_measurements(inplace=False)).probabilities_dict(qargs=list(out.layout.final_index_layout()))
                    assert abs(sv.get("0" * c, 0) - .5) < 1e-9 and abs(sv.get("1" * c, 0) - .5) < 1e-9, (name, seed)
            rows.append(dict(circuit=name, seed=seed, **res))
    return rows


# ------------------------------------------------------------------- figures
def fig_map(dev, name):
    fig, ax = plt.subplots(figsize=(9, 10))
    draw_device(ax, dev)
    ax.set_title(f"{name}: 校正値マップ（ノード: id / 1Q fidelity / 測定誤差、矢印: control→target と CX fidelity）", fontsize=10, loc="left")
    ax.legend(handles=[Line2D([], [], color=RED, lw=2.4, label=f"CX fidelity < {BAD_CX}"),
                       Line2D([], [], marker="o", ls="", mfc="#fbe0df", mec=INK, ms=10, label=f"測定誤差 > {BAD_MEAS}")],
              loc="lower left", frameon=False)
    fig.tight_layout()
    fig.savefig(OUT / "fig1_fidelity_map.png", dpi=150)
    plt.close(fig)


def path_title(tag, r):
    return f"{tag}\nlayout {r['layout']}\n逆向きCX {r['rev']} / sx+x {r['phys']} / 実行時間 {r['dur']:.0f} ns / NLL {r['nll']:.3f}"


def fig_direction_cases(dev, cases):
    picks = [("bell2", "target_only", 2), ("ghz4", "target_only", 2), ("ghz8", "target_only", 2)]
    fig, axes = plt.subplots(2, 3, figsize=(15, 16))
    for col, key in enumerate(picks):
        r = next(x for x in cases if (x["circuit"], x["mode"], x["level"]) == key)
        m = dict(r["mirror"])
        draw_device(axes[0, col], dev, r["layout"], labels="small", title=path_title(f"{r['circuit']}  Qiskit の選択（{r['mode']} L{r['level']}）", r))
        draw_device(axes[1, col], dev, m["layout"], labels="small", title=path_title(f"{r['circuit']}  同じ量子ビットを逆順に配置", m))
    fig.legend(handles=[Line2D([], [], color=BLUE, lw=3.6, label="CX が登録方向どおり"),
                        Line2D([], [], color=ORANGE, lw=3.6, ls=(0, (2, 1.2)), label="CX が逆向き（H で挟む分解が入る）")],
               loc="lower center", ncol=2, frameon=False, fontsize=10)
    fig.suptitle("問題1: 同じ経路でも向きの選び方で分解が増える（SWAP なしの GHZ/Bell）", fontsize=12, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0.04, 1, 0.96))
    fig.savefig(OUT / "fig2_direction_cases.png", dpi=150)
    plt.close(fig)


def fig_direction_summary(cost):
    names = list(dict.fromkeys(r["circuit"] for r in cost))
    sel = [r for r in cost if r["mode"] == "target_only" and r["level"] == 2]
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.4))
    x = range(len(names))
    mean = lambda k, n: statistics.mean(r[k] for r in sel if r["circuit"] == n)
    ax = axes[0]
    ax.bar([i - 0.2 for i in x], [mean("phys_dir", n) for n in names], 0.38, color=ORANGE, label="実際（一方向 CX）")
    ax.bar([i + 0.2 for i in x], [mean("phys_bi", n) for n in names], 0.38, color=BLUE, label="同じ配線で向き制約なし")
    ax.set_title("物理 1Q パルス数 sx+x（rz は仮想なので除外）", loc="left", fontsize=10)
    ax.legend(frameon=False)
    ax = axes[1]
    inc = lambda k, n: 100 * (mean(k + "_dir", n) / mean(k + "_bi", n) - 1)
    ax.bar([i - 0.2 for i in x], [inc("dur", n) for n in names], 0.38, color=ORANGE, label="実行時間")
    ax.bar([i + 0.2 for i in x], [inc("gnll", n) for n in names], 0.38, color=BLUE, label="ゲート誤差 NLL")
    ax.set_title("向き補正による増加率 [%]", loc="left", fontsize=10)
    ax.legend(frameon=False)
    for ax in axes:
        ax.set_xticks(list(x), names)
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="y", color="#e6e5e0", lw=0.6)
        ax.set_axisbelow(True)
    fig.suptitle("問題1: 向き補正だけで増えた量（target_only L2、10 seed 平均。routing 後の回路を固定し、仕上げ Target だけを変えて比較）", fontsize=10.5, x=0.01, ha="left")
    fig.tight_layout()
    fig.savefig(OUT / "fig3_direction_cost.png", dpi=150)
    plt.close(fig)


def fig_calibration_cases(dev, cases):
    picks = ["bell2", "ghz4", "ghz5"]
    fig, axes = plt.subplots(2, 3, figsize=(15, 16))
    for col, c in enumerate(picks):
        for row, mode in enumerate(("default", "target_only")):
            r = next(x for x in cases if (x["circuit"], x["mode"], x["level"]) == (c, mode, 2))
            tag = f"{c}  {'basis_gates 併用（現状）' if mode == 'default' else 'basis_gates 省略（校正値あり）'} L2"
            draw_device(axes[row, col], dev, r["layout"], labels="small",
                        title=path_title(tag, r) + f"\nSWAPなし配置 {r['n_cand']} 通り中 NLL 順位 {r['rank']}")
    fig.legend(handles=[Line2D([], [], marker="o", ls="", mfc="#fbe0df", mec=INK, ms=10, label=f"測定誤差 > {BAD_MEAS}"),
                        Line2D([], [], color=RED, lw=2.4, label=f"CX fidelity < {BAD_CX}"),
                        Line2D([], [], color=BLUE, lw=3.6, label="選択された CX（登録方向）"),
                        Line2D([], [], color=ORANGE, lw=3.6, ls=(0, (2, 1.2)), label="選択された CX（逆向き）")],
               loc="lower center", ncol=4, frameon=False, fontsize=10)
    fig.suptitle("問題2: basis_gates 併用で校正値が消え、低品質の量子ビット・結合が選ばれる", fontsize=12, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0.04, 1, 0.96))
    fig.savefig(OUT / "fig4_calibration_cases.png", dpi=150)
    plt.close(fig)


def fig_calibration_rank(cases, all_cands):
    fig, ax = plt.subplots(figsize=(10, 4.2))
    names = list(all_cands)
    for i, n in enumerate(names):
        vals = [c["nll"] for c in all_cands[n]]
        ax.scatter([i] * len(vals), vals, s=14, color=GRAY, alpha=0.6, label="SWAPなし配置の全候補" if i == 0 else None, zorder=1)
        for mode, color, mk, dx in (("default", RED, "X", -0.12), ("target_only", BLUE, "o", 0.12)):
            r = next(x for x in cases if (x["circuit"], x["mode"], x["level"]) == (n, mode, 2))
            ax.scatter([i + dx], [r["nll"]], s=90, color=color, marker=mk, edgecolors="white", linewidths=1.5, zorder=3,
                       label=("basis_gates 併用（現状）" if mode == "default" else "basis_gates 省略") + " L2" if i == 0 else None)
            ax.annotate(f"{r['rank']}位", (i + dx, r["nll"]), xytext=(dx * 90, 0), textcoords="offset points", va="center",
                        ha="right" if dx < 0 else "left", fontsize=8, color=INK)
    ax.set_xticks(range(len(names)), names)
    ax.set_xlim(-0.6, len(names) - 0.4)
    ax.set_ylabel("NLL = -Σlog(1-error)（小さいほど良い）")
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", color="#e6e5e0", lw=0.6)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, loc="upper left")
    ax.set_title("問題2: 選ばれた配置は全候補の中でどの位置か（灰色の点 = 取り得る全ての SWAP なし配置）", loc="left", fontsize=10)
    fig.tight_layout()
    fig.savefig(OUT / "fig5_calibration_rank.png", dpi=150)
    plt.close(fig)


SOL_STYLE = {"current": (RED, "X"), "native": (BLUE, "o"), "solution": ("#1baf7a", "D")}


def fig_solution_cases(dev, sol_cases):
    picks = ["bell2", "ghz4", "ghz8"]
    fig, axes = plt.subplots(3, 3, figsize=(15, 23))
    for col, c in enumerate(picks):
        for row, mode in enumerate(MODES):
            r = next(x for x in sol_cases if (x["circuit"], x["mode"]) == (c, mode))
            draw_device(axes[row, col], dev, r["layout"], labels="small",
                        title=path_title(f"{c}  {MODES[mode]}  L2", r) + f"\nSWAPなし配置 {r['n_cand']} 通り中 NLL 順位 {r['rank']}")
    fig.legend(handles=[Line2D([], [], marker="o", ls="", mfc="#fbe0df", mec=INK, ms=10, label=f"測定誤差 > {BAD_MEAS}"),
                        Line2D([], [], color=RED, lw=2.4, label=f"CX fidelity < {BAD_CX}"),
                        Line2D([], [], color=BLUE, lw=3.6, label="選択された CX（登録方向）"),
                        Line2D([], [], color=ORANGE, lw=3.6, ls=(0, (2, 1.2)), label="選択された CX（逆向き）")],
               loc="lower center", ncol=4, frameon=False, fontsize=10)
    fig.suptitle("解決案の比較（問題2の図を取り直し）: 上段 現状 / 中段 3 のみ / 下段 3 + A + B", fontsize=12, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0.03, 1, 0.97))
    fig.savefig(OUT / "fig6_solution_cases.png", dpi=150)
    plt.close(fig)


def fig_solution_rank(sol_cases, all_cands):
    fig, ax = plt.subplots(figsize=(10, 4.4))
    names = list(all_cands)
    offs = dict(zip(MODES, (-0.18, 0.0, 0.18)))
    for i, n in enumerate(names):
        vals = [c["nll"] for c in all_cands[n]]
        ax.scatter([i - 0.36] * len(vals), vals, s=14, color=GRAY, alpha=0.6, label="SWAPなし配置の全候補" if i == 0 else None, zorder=1)
        for mode in MODES:
            r = next(x for x in sol_cases if (x["circuit"], x["mode"]) == (n, mode))
            color, mk = SOL_STYLE[mode]
            ax.scatter([i + offs[mode]], [r["nll"]], s=80, color=color, marker=mk, edgecolors="white", linewidths=1.5, zorder=3,
                       label=MODES[mode] if i == 0 else None)
            ax.annotate(f"{r['rank']}位", (i + offs[mode], r["nll"]), xytext=(0, 9), textcoords="offset points", ha="center", fontsize=7.5, color=INK)
    ax.set_xticks(range(len(names)), names)
    ax.set_xlim(-0.6, len(names) - 0.4)
    ax.set_ylabel("NLL = -Σlog(1-error)（小さいほど良い）")
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", color="#e6e5e0", lw=0.6)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, loc="upper left")
    ax.set_title("解決案の比較: 選ばれた配置の全候補中の順位（L2、seed 0）", loc="left", fontsize=10)
    fig.tight_layout()
    fig.savefig(OUT / "fig7_solution_rank.png", dpi=150)
    plt.close(fig)


def fig_solution_bench(sol_bench):
    names = list(dict.fromkeys(r["circuit"] for r in sol_bench))
    fig, ax = plt.subplots(figsize=(12, 4.2))
    x = range(len(names))
    base = {n: statistics.mean(r["current"]["nll"] for r in sol_bench if r["circuit"] == n) for n in names}
    for k, mode in enumerate(("native", "solution")):
        vals = [100 * (statistics.mean(r[mode]["nll"] for r in sol_bench if r["circuit"] == n) / base[n] - 1) for n in names]
        ax.bar([i + (k - 0.5) * 0.38 for i in x], vals, 0.36, color=SOL_STYLE[mode][0], label=MODES[mode])
    ax.axhline(0, color=MUTED, lw=0.8)
    ax.set_xticks(list(x), names)
    ax.set_ylabel("現状比の NLL 変化 [%]（負 = 改善）")
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", color="#e6e5e0", lw=0.6)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, loc="lower left")
    ax.set_title("解決案の比較: 全ベンチマーク回路（L2、10 seed 平均）", loc="left", fontsize=10)
    fig.tight_layout()
    fig.savefig(OUT / "fig8_solution_bench.png", dpi=150)
    plt.close(fig)


# ------------------------------------------------------------------ markdown
def summarise(dev, cases, cost, name):
    bad_q = sorted(q for q in dev.q if dev.meas[q] > BAD_MEAS)
    bad_e = sorted(e for e in dev.edges if dev.cx_fid[e] < BAD_CX)
    agg = {}
    for c in dict.fromkeys(r["circuit"] for r in cost):
        for mode in ("default", "target_only"):
            for lv in (1, 2):
                rs = [r for r in cost if (r["circuit"], r["mode"], r["level"]) == (c, mode, lv)]
                agg[(c, mode, lv)] = dict(
                    rev=statistics.mean(r["rev_cx"] for r in rs), logical=statistics.mean(r["logical_cx"] for r in rs),
                    swaps=statistics.mean(r["swaps"] for r in rs),
                    n1_dir=statistics.mean(r["n1_dir"] for r in rs), n1_bi=statistics.mean(r["n1_bi"] for r in rs),
                    d_dir=statistics.mean(r["depth_dir"] for r in rs), d_bi=statistics.mean(r["depth_bi"] for r in rs),
                    cx=statistics.mean(r["cx"] for r in rs), cx_bi=statistics.mean(r["cx_bi"] for r in rs),
                    **{k: statistics.mean(r[k] for r in rs) for k in ("phys_dir", "phys_bi", "dur_dir", "dur_bi", "gnll_dir", "gnll_bi")},
                    nll=statistics.mean(r["nll"] for r in rs),
                    bad_q=sum(any(q in bad_q for q in r["used_qubits"]) for r in rs), bad_e=sum(any(tuple(e) in bad_e for e in r["used_cx"]) for r in rs), runs=len(rs))
    return bad_q, bad_e, agg


SOURCE_NOTE = """### ソース上の根拠（Gemini による調査を grep で確認）

- `qiskit/transpiler/passes/layout/sabre_layout.py:172,188` — SabreLayout は `coupling_map.make_symmetric()` で結合を無向化。SabreSwap も無向の距離で SWAP を選ぶ。
- `qiskit/transpiler/preset_passmanagers/common.py:364-370` — level 1/2 の routing 段の VF2PostLayout は `strict_direction=False`（向きを区別せずに採点）。
- `qiskit/transpiler/preset_passmanagers/builtin_plugins.py:570-576` — `strict_direction=True` の VF2PostLayout は level 3 の最適化段だけ。
- `qiskit/transpiler/preset_passmanagers/common.py:559-572` — 向きは translation 段の `CheckGateDirection` → `GateDirection` で、逆向き CX を H で挟んで直すだけ。

"""


SOLUTION_CODE = """## 3. 解決案（問題2）: native ゲートを指定しつつ校正値を残す

native ゲートを指定して分解したい場合も、`basis_gates` は使わない。**native ゲートだけを残し、校正値（InstructionProperties）をコピーした Target を作り、`target=` で渡す。**
Qiskit は `target` が与えられると `backend`・`basis_gates` から Target を作り直さない（`generate_preset_pass_manager.py:243-246`）。そのため error が残り、警告も出ない。

```python
from qiskit.transpiler import Target

def native_target(target, names):
    \"\"\"native ゲートだけを残し、InstructionProperties（error/duration）をそのままコピーする。\"\"\"
    t = Target(num_qubits=target.num_qubits, dt=target.dt)
    for name in names:
        t.add_instruction(target.operation_from_name(name), dict(target[name]))
    return t

backend = OqtoqusToQiskitDeviceConverter().convert(device_json)
nt = native_target(backend.target, ["rz", "sx", "cx", "measure"])

# Tranqu 経由: options に target を入れる（Tranqu が追加する backend より target が優先される）
tranqu.transpile(program=qc, program_lib="qiskit", transpiler_lib="qiskit",
                 transpiler_options=dict(target=nt, optimization_level=2),
                 device=device_json, device_lib="oqtopus")
```
"""

SOLUTION1_HEAD = """
## 4. 解決案（問題1）: 逆向き CX を打てない前提で

device-gateway は逆向き CX を実行できないので、「反転を安くする」方向の対策は取れない。できるのは、(a) の分を配置で回収すること、コストを正しく見積もること、の2つである。

### A. コストのモデルを直す（最優先・簡単）

- converter は rz にも 1Q fidelity から作った error を設定している。そのため Qiskit の配置の採点では、逆向き CX のコスト（rz を含む H 4個）や 1Q の多い配置が過大に見える。rz は仮想ゲートなので error 0・duration 0 にする。
- 評価指標は「1Q 数・depth」ではなく、sx+x のパルス数、実行時間、rz を除くゲート誤差にする。

```python
nt = native_target(backend.target, ["rz", "sx", "cx", "measure"], virtual={"rz"})  # rz を誤差0・時間0に
```

### B. 計画用 Target で逆向きにソフトなペナルティを入れる（Qiskit の既存 pass だけで実現）

1. 配置・routing の段階だけ、逆方向の CX も登録した**計画用 Target**を使う。逆方向の error は「CX＋H 4個分（各量子ビットに sx×2）」にする。
2. routing の直後に、向きを厳密に区別する `VF2PostLayout(strict_direction=True)` を実行する。計画用 Target では逆向きも「高いが可能」なので、向きの揃わない配置の中から誤差最小のものが選ばれる。
3. 最後の分解（translation 以降）は**本物の一方向 Target**で行う。出力に逆向き CX は残らない。

```python
P = penalized_target(target)  # 逆向き CX = CX + 4H の error で登録（計画専用）
found = lambda ps: ps["VF2PostLayout_stop_reason"] is VF2PostLayoutStopReason.SOLUTION_FOUND
plan = generate_preset_pass_manager(optimization_level=2, target=P)
plan.post_routing = PassManager([VF2PostLayout(target=P, strict_direction=True),
                                 ConditionalController(ApplyLayout(), condition=found)])
plan.translation = plan.optimization = plan.scheduling = None
routed = plan.run(qc)
fin = generate_preset_pass_manager(optimization_level=2, target=target)  # 本物の一方向 Target
fin.init = fin.layout = fin.routing = None
out = fin.run(routed); out._layout = routed.layout
```

実装は `issues/visualize_issues.py` の `penalized_target()` / `plan_then_finish()`。
"""

SOLUTION1_TAIL = """### C. 向きを考慮した routing（独自実装、優先度低）

SWAP を含む回路で (a) を回収するには、SABRE の SWAP 選択に「次の CX が逆向きになるか」のコストを入れる必要がある。Qiskit に該当オプションは無く、独自の routing pass になる。
改善できる上限は 1.2 の「一方向 ← 両方向」の差（実行時間で数 %）までなので、CX 数・SWAP 数を減らす独自 layout/routing を検討する段階で一緒に扱う。
"""

SOLUTION_NOTES = """
- **converter が登録していないゲートを native にする場合**（例: `rzx`、`ecr`）は、このサブセット方式では足りない。converter 側でそのゲートを JSON のエラー率つきで Target に登録する必要がある。現在の converter が登録するのは `rz/sx/x/cx/measure` だけ。2Q の duration は `rzx90` キーにしか無く、ns→s の単位変換も無い点も合わせて直す。
- **問題1との関係**: device-gateway は逆向き CX を実行できないので、Target に逆方向を登録してはいけない（出力に逆向き CX が出る）。逆方向は 4章 B のように「計画専用」の Target にだけ入れる。
- 校正値を戻しても常に良くなるとは限らない（2章の ghz21）。native Target 化は問題2の前提条件であり、問題1の対策（4章）とセットで評価する。
"""


def wtl(pairs):
    """pairs of (new, old) scores, smaller is better -> (win, tie, lose)."""
    win = sum(a < b - 1e-9 for a, b in pairs)
    lose = sum(a > b + 1e-9 for a, b in pairs)
    return win, len(pairs) - win - lose, lose


def describe_wtl(res):
    """res: {circuit: (w, t, l)} -> short Japanese summary."""
    n = len(SEEDS)
    allw = [c for c, (w, t, l) in res.items() if w == n]
    most = [c for c, (w, t, l) in res.items() if n > w > n // 2 and l == 0]
    same = [c for c, (w, t, l) in res.items() if t == n]
    worse = [f"{c}（{l}/{n} seed）" for c, (w, t, l) in res.items() if l > 0]
    parts = []
    if allw: parts.append(f"{'・'.join(allw)} で全 seed 改善")
    if most: parts.append(f"{'・'.join(most)} で大半の seed が改善")
    if same: parts.append(f"{'・'.join(same)} で差なし")
    if worse: parts.append(f"**悪化: {'、'.join(worse)}**")
    return "、".join(parts) + "。"


def fmt_layout(L):
    return "[" + ",".join(map(str, L)) + "]"


def write_md(dev, name, cases, cost, all_cands, warn_text, native, dsol, sol_cases, sol_bench):
    bad_q, bad_e, agg = summarise(dev, cases, cost, name)
    C = lambda c, m, l: next(x for x in cases if (x["circuit"], x["mode"], x["level"]) == (c, m, l))
    L = []
    w = L.append
    w(f"# トランスパイラの2つの問題の見える化（{name} トポロジー）\n")
    w(f"対象: `topologies/{name}.json`（21量子ビット・有向 CX 22本の歯抜け格子。橋 11→9 の fidelity を .70 に下げた版）。"
      "Qiskit 2.4.2 / Tranqu の converter で Target を作成。transpile の呼び方は Tranqu と同じ（`backend=` を渡す）。"
      "再現: `.venv/bin/python issues/visualize_issues.py`。数値は `issues/results.json`。\n")
    w("- **default**: `t.py` と同じく `basis_gates=[id,sx,x,rz,cx]` を併用（現状）")
    w("- **target_only**: `basis_gates` を省略し、Tranqu が作った Target（校正値つき）をそのまま使う\n")
    w("## 0. 校正値マップ（ref/device.py 形式）\n")
    w("![fidelity map](fig1_fidelity_map.png)\n")
    w(f"ノードは `id / 1Q fidelity / 測定誤差`（Tranqu converter と同じ (P(1|0)+P(0|1))/2）、矢印は control→target と CX fidelity。"
      f"赤は CX fidelity < {BAD_CX}（{', '.join(f'{a}→{b} ({dev.cx_fid[(a, b)]:.3f})' for a, b in bad_e)}）、"
      f"ピンクのノードは測定誤差 > {BAD_MEAS}（{', '.join(f'q{q} ({dev.meas[q]:.3f})' for q in bad_q)}）。"
      "全結合が一方向だけ登録されており、隣り合う辺の向きが揃っていないため、鎖状の回路は向きの選び方次第で逆向き CX が生じる。\n")

    w("## 1. 問題1: CX の向き\n")
    w("前提: **device-gateway は登録方向の CX しか実行できない**。逆向きの CX は native CX の両側を H で挟んで実行するしかない。"
      "H は rz・sx・rz に分解され、rz は仮想ゲート（JSON の duration 0）なので、物理的に増えるのは sx パルスだけである。"
      "以下ではコストを **sx+x のパルス数、実行時間、ゲート誤差（rz と測定を除く NLL）** で測る。"
      "実行時間は JSON の duration（sx 16 ns、x 24 ns、rz 0）と、CX = RZX90×2 という仮定で計算した。\n")
    w("> 旧版はコストを「1Q ゲート数（rz を含む）と depth（時間の重みなし）」で測っており、ghz8 で「1Q 3→41、depth 11→29」と過大に見えていた。物理指標では下記のとおり小さい。\n")
    w("### 1.1 原因の切り分け（SWAP 不要の回路）\n")
    w("SWAP が要らない GHZ/Bell は、配置＝グラフ上の単純経路と向きの選択だけで決まる。全候補を列挙し（`initial_layout` 固定で変換）、"
      "Qiskit の選択、「同じ量子ビットを逆順に置いた配置」、全候補での逆向き CX の最小値を比べた。\n")
    w("| 回路 | 条件 | Qiskit の layout | 逆向き CX | sx+x | 実行時間 [ns] | NLL | → 逆順 layout | 逆向き CX | sx+x | 実行時間 [ns] | NLL | 全候補の最小逆向き数 |")
    w("|---|---|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|")
    for c in ("bell2", "ghz4", "ghz5", "ghz8"):
        for m, lv in (("default", 2), ("target_only", 2), ("target_only", 3)):
            r = C(c, m, lv)
            mm = r["mirror"]
            flag = " **◀**" if mm["rev"] < r["rev"] else ""
            w(f"| {c} | {m} L{lv} | {fmt_layout(r['layout'])} | {r['rev']} | {r['phys']} | {r['dur']:.0f} | {r['nll']:.3f} | {fmt_layout(mm['layout'])}{flag} | {mm['rev']} | {mm['phys']} | {mm['dur']:.0f} | {mm['nll']:.3f} | {r['min_rev']} |")
    extra = [c for c in ("bell2", "ghz4", "ghz5", "ghz8") if C(c, "target_only", 2)["rev"] > C(c, "target_only", 2)["min_rev"]]
    exact = [c for c in ("bell2", "ghz4", "ghz5", "ghz8") if c not in extra]
    w("\n**◀** = 同じ量子ビット・同じ結合のまま、並びを逆にするだけで逆向き CX が減る。"
      "L3 は参考（`strict_direction=True` の VF2PostLayout が最適化段にある唯一のレベル）で、L3 でも改善しない。"
      f"target_only L2 は {'・'.join(extra)} で最小値より多く、{'・'.join(exact) or 'なし'} は最小値に一致。\n")
    w("![direction cases](fig2_direction_cases.png)\n")
    w("追加コストは2つに分かれる。\n")
    w("- **(a) 配置で避けられる分**: Qiskit が結合を無向として配置を決めるため（下記のソース根拠）。Qiskit の選択と最小値との差。"
      "bell2（target_only L2）は校正値を見て最良の辺 10→9 を選ぶが、論理 CX を 9→10 の向きで置くので逆向きが1本生じる。**校正値を有効にすると、かえってこの問題が表面化する**。")
    w("- **(b) どう配置しても避けられない分**: このトポロジーは隣接辺の向きが交互に並ぶため、最小値（ghz8 で3本）より減らせない。"
      "一方向の結合上の SWAP も、必ず逆向き CX を1本含む。\n")
    w("### 1.2 向き補正の物理コスト（SWAP を含む全ベンチマーク回路）\n")
    w("Qiskit の routing 直後の回路を取り出し、(1) 実際の一方向 Target、(2) 同じ校正値で両方向を許した Target で、後段（translation/optimization）だけを実行して差を取った。"
      "配置と SWAP は同じなので、差は向き補正だけに起因する。(1) は通常の transpile 出力と全実行で一致を確認済み。10 seed 平均。\n")
    w("| 回路 | 条件 | 論理CX+SWAP | 逆向き CX（SWAP 除く） | sx+x 一方向 ← 両方向 | 実行時間 [ns] 一方向 ← 両方向 | ゲート誤差 NLL 一方向 ← 両方向 |")
    w("|---|---|---|---:|---:|---:|---:|")
    pct = lambda a, b: f"{a:.0f} ← {b:.0f}（+{100 * (a / b - 1):.0f}%）" if b else f"{a:.0f} ← {b:.0f}"
    for c in dict.fromkeys(r["circuit"] for r in cost):
        for m, lv in (("default", 2), ("target_only", 2)):
            a = agg[(c, m, lv)]
            w(f"| {c} | {m} L{lv} | CX {a['logical']:.0f} + SWAP {a['swaps']:.1f} | {a['rev']:.1f} | {a['phys_dir']:.1f} ← {a['phys_bi']:.1f} | "
              f"{pct(a['dur_dir'], a['dur_bi'])} | {a['gnll_dir']:.3f} ← {a['gnll_bi']:.3f}（+{100 * (a['gnll_dir'] / a['gnll_bi'] - 1):.0f}%） |")
    w("\n![direction cost](fig3_direction_cost.png)\n")
    sel = [agg[(c, "target_only", 2)] for c in dict.fromkeys(r["circuit"] for r in cost) if c != "bell2"]
    d_inc = [100 * (a["dur_dir"] / a["dur_bi"] - 1) for a in sel]
    g_inc = [100 * (a["gnll_dir"] / a["gnll_bi"] - 1) for a in sel]
    w(f"sx パルスは数倍に増えるが、sx は CX に比べて短く誤差も小さい（約 5e-4 対 約 3%）。そのため、"
      f"実行時間の増加は {min(d_inc):.0f}〜{max(d_inc):.0f}%、ゲート誤差の増加は {min(g_inc):.0f}〜{max(g_inc):.0f}% にとどまる（bell2 を除く、target_only L2）。"
      "**問題1は実在するが、CX 数・SWAP 数（routing の質）や問題2に比べると影響は小さい。**\n")

    w(SOURCE_NOTE)
    w("## 2. 問題2: エラー率が無視される\n")
    w(f"default では Qiskit が次の警告を出す: `{warn_text}`。"
      "`generate_preset_pass_manager.py:211-220` で警告を出し、`:254` で `Target.from_configuration(basis_gates=..., coupling_map=...)` により Target を作り直す。"
      "`target.py` の `from_configuration` は error を設定しないため、InstructionProperties.error は全て `None` になる（Tranqu `qiskit_transpiler.py:44-48` は options をそのまま渡す）。"
      "このため VF2Layout / VF2PostLayout の誤差による採点が働かず、量子ビット番号や探索順だけで配置が決まる。\n")
    w("### 割り出したケース（SWAP 不要の回路、L2）\n")
    w("| 回路 | 条件 | layout | 使った低品質要素 | NLL | 全候補中の順位 | 最良候補 (NLL) |")
    w("|---|---|---|---|---:|---:|---|")
    for c in ("bell2", "ghz4", "ghz5", "ghz8"):
        for m in ("default", "target_only"):
            r = C(c, m, 2)
            badparts = [f"q{q}(ro {dev.meas[q]:.3f})" for q in r["layout"] if q in bad_q] + [f"{a}→{b}({dev.cx_fid[(a, b)]:.3f})" for a, b in r["cx_used"] if (a, b) in bad_e]
            w(f"| {c} | {m} | {fmt_layout(r['layout'])} | {', '.join(badparts) or '—'} | {r['nll']:.3f} | {r['rank']}/{r['n_cand']} | {fmt_layout(r['best']['path'])} ({r['best']['nll']:.3f}) |")
    w("\n![calibration cases](fig4_calibration_cases.png)\n")
    w("![calibration rank](fig5_calibration_rank.png)\n")
    g4d, g4t = C("ghz4", "default", 2), C("ghz4", "target_only", 2)
    bad_of = lambda r: [f"q{q}（測定誤差 {dev.meas[q]:.3f}）" for q in r["layout"] if q in bad_q] + [f"{a}→{b}（fidelity {dev.cx_fid[(a, b)]:.3f}）" for a, b in r["cx_used"] if (a, b) in bad_e]
    w(f"- **ghz4（default）** は {fmt_layout(g4d['layout'])} を選び、{'、'.join(bad_of(g4d))} を使う。"
      f"NLL {g4d['nll']:.3f}、{g4d['n_cand']} 候補中 {g4d['rank']} 位。校正値を残すと {fmt_layout(g4t['layout'])}（NLL {g4t['nll']:.3f}、{g4t['rank']} 位）。")
    b0, b1 = C("bell2", "default", 1), C("bell2", "default", 2)
    w(f"- **bell2（default）** は L1 で番号順の {fmt_layout(b0['layout'])}（{'、'.join(bad_of(b0)) or '低品質要素なし'}、NLL {b0['nll']:.3f}・{b0['rank']}位）、"
      f"L2 で {fmt_layout(b1['layout'])}（{b1['rank']}位）。校正値の差ではなく探索の都合で決まっている。")
    w("- target_only は ghz4/ghz5 でほぼ最良を選ぶが、bell2・ghz4 では問題1の向きの不利を抱えたまま。2つの問題は別々に直す必要がある（4章）。\n")
    w("### SWAP を含む全ベンチマーク回路（L2、10 seed）\n")
    w("同じ seed の default と target_only の NLL（rz を誤差0として採点、測定を含む）を比較。8量子ビット以上の回路は低品質要素（測定誤差 > .1 の q0/q1/q3/q16、CX fidelity < .93 の7本）を"
      "両モードとも全 seed で通過しており、避けきれない。target_only は "
      + describe_wtl({c: wtl([(r2["nll"], r1["nll"]) for r1 in cost for r2 in cost
                              if r1["circuit"] == r2["circuit"] == c and r1["level"] == r2["level"] == 2 and r1["seed"] == r2["seed"]
                              and r1["mode"] == "default" and r2["mode"] == "target_only"]) for c in dict.fromkeys(r["circuit"] for r in cost)})
      + "悪化するのは全21量子ビットを使う ghz21 で、配置の自由度がほぼ無い（原因は未調査）。"
      "校正値を戻すことは必要だが、それだけで常に良くなるわけではない。\n")
    w("| 回路 | 平均 NLL default → target_only | target_only の 勝/同/負 |")
    w("|---|---:|---:|")
    for c in dict.fromkeys(r["circuit"] for r in cost):
        a, t = agg[(c, "default", 2)], agg[(c, "target_only", 2)]
        pair = {(r["seed"], r["mode"]): r["nll"] for r in cost if r["circuit"] == c and r["level"] == 2}
        win = sum(pair[(sd, "target_only")] < pair[(sd, "default")] - 1e-9 for sd in SEEDS)
        lose = sum(pair[(sd, "target_only")] > pair[(sd, "default")] + 1e-9 for sd in SEEDS)
        w(f"| {c} | {a['nll']:.3f} → {t['nll']:.3f} | {win}/{len(SEEDS) - win - lose}/{lose} |")
    w(SOLUTION_CODE)
    w("### bad_bridge での確認（L2、10 seed）\n")
    w(f"native = `{NATIVE}`（x を除いた例）。`target=` 直指定と Tranqu 経由（`transpiler_options=dict(target=nt, ...)` ＋ `device=`）は全実行で layout・ゲート数が一致。"
      f"警告は {sum(r['warnings'] for r in native)} 件、出力ゲートは全て native の範囲内。比較対象は同じ native を `basis_gates` で指定した現状の方法。\n")
    w("| 回路 | layout（seed 0）basis_gates | layout（seed 0）native Target | 平均 NLL basis_gates → native Target | native Target の 勝/同/負 |")
    w("|---|---|---|---:|---:|")
    for c in dict.fromkeys(r["circuit"] for r in native):
        rs = [r for r in native if r["circuit"] == c]
        win = sum(r["native"]["nll"] < r["basis"]["nll"] - 1e-9 for r in rs)
        lose = sum(r["native"]["nll"] > r["basis"]["nll"] + 1e-9 for r in rs)
        w(f"| {c} | {fmt_layout(rs[0]['basis']['layout'])} | {fmt_layout(rs[0]['native']['layout'])} | "
          f"{statistics.mean(r['basis']['nll'] for r in rs):.3f} → {statistics.mean(r['native']['nll'] for r in rs):.3f} | {win}/{len(rs) - win - lose}/{lose} |")
    w(SOLUTION_NOTES)
    w(SOLUTION1_HEAD)
    w("#### B の検証（bad_bridge、L2、10 seed）\n")
    w("比較対象は校正値つき Target での通常の L2（base）と、ペナルティなしで向きを厳密に要求する VF2PostLayout を routing 直後に入れたもの（hard）。"
      "全出力が一方向 Target の範囲（逆向き CX なし）に収まることを全実行で確認した。GHZ/Bell は seed 0〜2 で、最終配置の物理量子ビット上に GHZ 状態ができることを状態ベクトルで確認した。\n")
    w("| 回路 | 逆向き CX base / hard / B | sx+x base → B | 実行時間 [ns] base → B | NLL base → B | B の NLL 勝/同/負 | hard の NLL 勝/同/負 |")
    w("|---|---:|---:|---:|---:|---:|---:|")
    res_b = {}
    for c in dict.fromkeys(r["circuit"] for r in dsol):
        rs = [r for r in dsol if r["circuit"] == c]
        m = lambda k, f: statistics.mean(r[k][f] for r in rs)
        wb = wtl([(r["penalty"]["nll"], r["base"]["nll"]) for r in rs])
        wh = wtl([(r["hard"]["nll"], r["base"]["nll"]) for r in rs])
        res_b[c] = wb
        w(f"| {c} | {m('base', 'rev'):.1f} / {m('hard', 'rev'):.1f} / {m('penalty', 'rev'):.1f} | {m('base', 'phys'):.1f} → {m('penalty', 'phys'):.1f} | "
          f"{m('base', 'dur'):.0f} → {m('penalty', 'dur'):.0f} | {m('base', 'nll'):.3f} → {m('penalty', 'nll'):.3f} | {'/'.join(map(str, wb))} | {'/'.join(map(str, wh))} |")
    w("\nB は " + describe_wtl(res_b)
      + f"ghz21 の悪化幅は NLL {statistics.mean(r['base']['nll'] for r in dsol if r['circuit'] == 'ghz21'):.3f} → "
        f"{statistics.mean(r['penalty']['nll'] for r in dsol if r['circuit'] == 'ghz21'):.3f} とごく小さい。"
      "hard は、全 CX の向きが揃う配置が存在する bell2 でしか効かない（ghz4 以降は解なしで何もしない。L3 で改善しないのも同じ理由）。"
      "B は「向きが揃わない配置の中で一番ましなもの」を選べるので、SWAP 不要の回路で (a) の分を回収できる。"
      "SWAP を含む回路では、VF2PostLayout が routing 後の回路に別の埋め込みを見つけられず、ほぼ効かない。\n")
    w(SOLUTION1_TAIL)
    w("## 5. 解決案を入れた比較（問題2の図を取り直し）\n")
    w(f"3（native Target）、4A（rz を誤差0）、4B（計画用 Target＋向き厳密な VF2PostLayout）をまとめて `issues/direction_aware.py` に実装し、"
      f"Tranqu の transpiler（`transpiler_lib=\"{TRANSPILER_LIB}\"`）として登録して実行した。native = `{NATIVE}`、L2。比較する3構成:\n")
    w("- **現状**: `backend` + 同じ native を `basis_gates` で指定（校正値が消える）")
    w("- **3 のみ**: native Target を `target=` で渡す（校正値あり、rz に誤差あり、向きは考慮しない）")
    w("- **3 + A + B**: 上記＋rz を誤差0＋逆向きにソフトなペナルティ\n")
    w("3 + A + B は直接呼び出しと Tranqu 経由で全実行の layout・ゲート数が一致した。全構成で、出力ゲートが native の範囲内、かつ CX が全て登録方向であることを確認した。\n")
    w("```python\nfrom issues.direction_aware import TRANSPILER_LIB, register\n\ntranqu = Tranqu(); register(tranqu)\n"
      "tranqu.transpile(program=qc, program_lib=\"qiskit\", transpiler_lib=TRANSPILER_LIB,\n"
      "                 transpiler_options=dict(native_gates=[\"rz\", \"sx\", \"cx\", \"measure\"], optimization_level=2),\n"
      "                 device=device_json, device_lib=\"oqtopus\")\n```\n")
    w("`basis_gates` を渡すと例外にして、問題2が再発しないようにしてある。\n")
    w("### 5.1 SWAP 不要の回路（seed 0）\n")
    w("| 回路 | 構成 | layout | 使った低品質要素 | 逆向き CX | sx+x | 実行時間 [ns] | NLL | 全候補中の順位 |")
    w("|---|---|---|---|---:|---:|---:|---:|---:|")
    for c in ("bell2", "ghz4", "ghz5", "ghz8"):
        for mode in MODES:
            r = next(x for x in sol_cases if (x["circuit"], x["mode"]) == (c, mode))
            badparts = [f"q{q}" for q in r["layout"] if q in bad_q] + [f"{a}→{b}" for a, b in r["cx_used"] if (a, b) in bad_e]
            w(f"| {c} | {MODES[mode]} | {fmt_layout(r['layout'])} | {', '.join(badparts) or '—'} | {r['rev']} | {r['phys']} | {r['dur']:.0f} | {r['nll']:.3f} | {r['rank']}/{r['n_cand']} |")
    w("\n![solution cases](fig6_solution_cases.png)\n")
    w("![solution rank](fig7_solution_rank.png)\n")
    best = [c for c in ("bell2", "ghz4", "ghz5", "ghz8") if next(x for x in sol_cases if (x["circuit"], x["mode"]) == (c, "solution"))["rank"] == 1]
    dir_left = [c for c in ("bell2", "ghz4", "ghz5", "ghz8")
                if next(x for x in sol_cases if (x["circuit"], x["mode"]) == (c, "native"))["rev"] > next(x for x in sol_cases if (x["circuit"], x["mode"]) == (c, "solution"))["rev"]]
    w(f"3 + A + B は {'・'.join(best) or 'どの回路でも'} で全候補中1位の配置を選ぶ。"
      f"現状は低品質要素を使い、順位が低い。3 のみは順位が上がるが、{'・'.join(dir_left)} では逆向き CX が1本多い（問題1の (a)）。"
      "3 + A + B はそれも回収する。ghz8 で q3・3→4 が残るのは、それらを含む配置が全候補中で NLL 最良だからである。\n")
    w("### 5.2 全ベンチマーク回路（L2、10 seed）\n")
    w("| 回路 | NLL 現状 → 3 のみ → 3+A+B | 逆向き CX 現状 / 3 / 3+A+B | 実行時間 [ns] 現状 → 3+A+B | 3+A+B の勝/同/負（対 現状） | 3+A+B の勝/同/負（対 3 のみ） |")
    w("|---|---:|---:|---:|---:|---:|")
    res_cur, res_nat = {}, {}
    for c in dict.fromkeys(r["circuit"] for r in sol_bench):
        rs = [r for r in sol_bench if r["circuit"] == c]
        m = lambda mode, k: statistics.mean(r[mode][k] for r in rs)
        a = wtl([(r["solution"]["nll"], r["current"]["nll"]) for r in rs])
        b = wtl([(r["solution"]["nll"], r["native"]["nll"]) for r in rs])
        res_cur[c], res_nat[c] = a, b
        w(f"| {c} | {m('current', 'nll'):.3f} → {m('native', 'nll'):.3f} → {m('solution', 'nll'):.3f} | "
          f"{m('current', 'rev'):.1f} / {m('native', 'rev'):.1f} / {m('solution', 'rev'):.1f} | {m('current', 'dur'):.0f} → {m('solution', 'dur'):.0f} | "
          f"{'/'.join(map(str, a))} | {'/'.join(map(str, b))} |")
    w("\n![solution bench](fig8_solution_bench.png)\n")
    w("- 対 現状: " + describe_wtl(res_cur))
    w("- 対 3 のみ: " + describe_wtl(res_nat))
    rel = lambda c, a, b: 100 * (statistics.mean(r[a]["nll"] for r in sol_bench if r["circuit"] == c) / statistics.mean(r[b]["nll"] for r in sol_bench if r["circuit"] == c) - 1)
    swap_c = [c for c in dict.fromkeys(r["circuit"] for r in sol_bench) if c not in ("bell2", "ghz4", "ghz5", "ghz8", "ghz16")]
    w(f"- 改善の大部分は 3（校正値を戻すこと）による。A + B の上乗せが目に見えるのは SWAP 不要の小さい回路（bell2・ghz4・ghz8）で、"
      f"SWAP を含む回路では勝つ seed があっても NLL の差は {max(abs(rel(c, 'solution', 'native')) for c in swap_c):.2f}% 以内。")
    w(f"- ghz21 は現状より全 seed で悪いが、差は NLL で {rel('ghz21', 'solution', 'current'):+.2f}%。悪化は 3 の時点で出ており（2章と同じ）、"
      "全21量子ビットを使い配置の自由度がほぼ無いケース。原因は未調査。\n")
    w("\n## まとめ\n")
    w("1. **問題2（校正値）**: `basis_gates` 併用で error が消え、低品質の量子ビット・結合を選ぶ。"
      "**native ゲートだけを残し校正値を保持した Target を `target=` で渡す**（Tranqu の `transpiler_options` 経由でも可）と、native 指定と校正値を両立できる。最優先で直す。")
    w("2. **問題1（向き）**: 原因は (a) Qiskit が向きを考えずに配置を決めること、(b) トポロジーの向きの並び。device-gateway が逆向き CX を打てない以上、(b) は残る。"
      f"物理コストは実行時間で {min(d_inc):.0f}〜{max(d_inc):.0f}%、ゲート誤差で {min(g_inc):.0f}〜{max(g_inc):.0f}% 程度で、CX・SWAP 数の影響より小さい。")
    w("3. **問題1の対策の優先順位**: A（rz を誤差0にするモデル修正と指標の見直し）を問題2の修正と同時に入れる → "
      "B（計画用 Target＋向き厳密な VF2PostLayout）を SWAP 不要の小さい回路向けのオプションとして入れる → "
      "C（向きを考慮した routing）は、CX 数を減らす独自 layout/routing を作る段階で一緒に扱う。")
    w("4. **3 + A + B を入れた結果（5章）**: SWAP 不要の回路では全候補中1位の配置を選び、逆向き CX も最小になる。"
      "SWAP を含む回路の改善はほぼ 3 によるもので、A + B の上乗せはごく小さい。実装は `issues/direction_aware.py`（Tranqu transpiler として登録可能）。\n")
    w("### 限界\n")
    w("NLL は独立誤差を仮定した参考値で、実機の成功確率ではない。rz は誤差0として採点した（converter は rz にも 1Q fidelity を設定しており、Qiskit 内部の採点ではまだ使われている）。"
      "実行時間は CX = RZX90×2 の仮定による見積もりで、device-gateway の実際の CX 実装・スケジュールとは異なり得る。"
      "校正 snapshot は1つ、seed は 0〜9。\n")
    return "\n".join(L) + "\n"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--topology", default="bad_bridge")
    args = p.parse_args()
    jp_font()
    data = json.loads((ROOT / "topologies" / f"{args.topology}.json").read_text())
    dev = Device(data)
    _, warn = run(dev, ghz(2), 1, 0, "default")
    cases = case_table(dev)
    all_cands = {}
    for n in (2, 4, 5, 8):
        all_cands["bell2" if n == 2 else f"ghz{n}"] = enumerate_ghz(dev, n)[1]
    for r in cases:
        r.pop("_cands", None)
    cost = direction_cost(dev)
    native = native_solution(dev, data)
    dsol = direction_solution(dev)
    tq = Tranqu()
    register(tq)
    sol_cases = solution_cases(dev, data, tq, all_cands)
    sol_bench = solution_bench(dev, data, tq)
    fig_solution_cases(dev, sol_cases)
    fig_solution_rank(sol_cases, all_cands)
    fig_solution_bench(sol_bench)
    fig_map(dev, args.topology)
    fig_direction_cases(dev, cases)
    fig_direction_summary(cost)
    fig_calibration_cases(dev, cases)
    fig_calibration_rank(cases, all_cands)
    (OUT / "results.json").write_text(json.dumps(dict(topology=args.topology, warning=warn, cases=cases, direction_cost=cost, native_solution=native, direction_solution=dsol, solution_cases=sol_cases, solution_bench=sol_bench), indent=1, default=list) + "\n")
    (OUT / "ISSUES.md").write_text(write_md(dev, args.topology, cases, cost, all_cands, warn[0] if warn else "(none)", native, dsol, sol_cases, sol_bench))
    print("wrote", OUT)


if __name__ == "__main__":
    main()

"""Plot the before/after benchmark (fig7 style of ref/issues/ISSUES.md).

Run from the repo root on the fixed branch (the candidate placements are transpiled with it):
    uv run --with matplotlib python benchmarks/calibration_direction/plot.py \
        benchmarks/calibration_direction/results_before.json benchmarks/calibration_direction/results_after.json
"""
import os

os.environ.setdefault("QISKIT_NUM_PROCS", "1")
os.environ.setdefault("RAYON_NUM_THREADS", "1")

import argparse
import json
import sys
import warnings
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from tranqu import Tranqu

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from bench import NATIVE, make_circuits, score_circuit  # noqa: E402

SWAP_FREE = ["bell2", "ghz4", "ghz5", "ghz8"]
# config key -> (label, color, marker); same mapping as ref/issues/fig7_solution_rank.png
STYLE = {
    "before:basis": ("修正前（main: backend + basis_gates）", "#e34948", "X"),
    "after:basis": ("3 + 4A（native Target、rz 誤差 0）", "#2a78d6", "o"),
    "after:basis_da": ("3 + 4A + 4B（direction_aware=True）", "#1baf7a", "D"),
}
GRAY, INK, MUTED, GRID = "#b5b4ae", "#0b0b0b", "#52514e", "#e6e5e0"


def jp_font():
    for f in ("Hiragino Sans", "Hiragino Maru Gothic Pro", "Noto Sans CJK JP"):
        if any(f in x.name for x in matplotlib.font_manager.fontManager.ttflist):
            plt.rcParams["font.sans-serif"] = [f, *plt.rcParams["font.sans-serif"]]
            return


def style_axes(ax):
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color(MUTED)
    ax.tick_params(colors=MUTED)
    ax.grid(axis="y", color=GRID, lw=0.6)
    ax.set_axisbelow(True)


def simple_paths(dev, n):
    adj = {q["id"]: set() for q in dev["qubits"]}
    for c in dev["couplings"]:
        adj[c["control"]].add(c["target"])
        adj[c["target"]].add(c["control"])
    res = []

    def dfs(p):
        if len(p) == n:
            res.append(p)
            return
        for v in adj[p[-1]]:
            if v not in p:
                dfs([*p, v])

    for s in adj:
        dfs([s])
    return res


def candidates(dev, circuits):
    """NLL of every swap-free placement (simple path with orientation) of each GHZ/Bell circuit."""
    tq = Tranqu()
    out = {}
    for name in SWAP_FREE:
        qc = circuits[name]
        vals = []
        for p in simple_paths(dev, qc.num_qubits):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                res = tq.transpile(program=qc, program_lib="qiskit", transpiler_lib="qiskit",
                                   transpiler_options=dict(basis_gates=list(NATIVE), initial_layout=p,
                                                           optimization_level=1, seed_transpiler=0),
                                   device=dev, device_lib="oqtopus")
            vals.append(score_circuit(res.transpiled_program, "basis", dev)["nll"])
        out[name] = sorted(vals)
    return out


def fig_rank(runs, cands, path):
    fig, ax = plt.subplots(figsize=(10, 4.6))
    offs = dict(zip(STYLE, (-0.18, 0.0, 0.18)))
    for i, name in enumerate(SWAP_FREE):
        vals = cands[name]
        ax.scatter([i - 0.36] * len(vals), vals, s=14, color=GRAY, alpha=0.6, zorder=1,
                   label="SWAP なし配置の全候補" if i == 0 else None)
        for cfg, (label, color, mk) in STYLE.items():
            r = runs[cfg, name, 0]
            rank = 1 + sum(v < r["nll"] - 1e-9 for v in vals)
            ax.scatter([i + offs[cfg]], [r["nll"]], s=80, color=color, marker=mk, edgecolors="white",
                       linewidths=1.5, zorder=3, label=label if i == 0 else None)
            ax.annotate(f"{rank}位", (i + offs[cfg], r["nll"]), xytext=(0, 9), textcoords="offset points",
                        ha="center", fontsize=7.5, color=INK)
        ax.text(i, -0.13, f"{len(vals)} 候補", transform=ax.get_xaxis_transform(), ha="center", fontsize=7.5, color=MUTED)
    ax.set_xticks(range(len(SWAP_FREE)), SWAP_FREE)
    ax.set_xlim(-0.6, len(SWAP_FREE) - 0.4)
    ax.set_ylabel("NLL = −Σlog(1−error)（小さいほど良い）")
    style_axes(ax)
    ax.legend(frameon=False, loc="upper left", fontsize=8.5)
    ax.set_title("修正前後の比較: 選ばれた配置の全候補中の順位（bad_bridge、L2、seed 0）", loc="left", fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def fig_bench(runs, circuits, seeds, path):
    """Per-seed NLL change vs before (same seed), all benchmark circuits."""
    fig, ax = plt.subplots(figsize=(10, 5.2))
    offs = {"after:basis": -0.17, "after:basis_da": 0.17}
    ax.axhline(0, color=MUTED, lw=1, zorder=2)
    for i, name in enumerate(circuits):
        for cfg, dx in offs.items():
            label, color, mk = STYLE[cfg]
            d = [100 * (runs[cfg, name, s]["nll"] / runs["before:basis", name, s]["nll"] - 1) for s in seeds]
            ax.scatter([i + dx] * len(d), d, s=34, color=color, marker=mk, edgecolors="white", linewidths=1,
                       alpha=0.9, zorder=3, label=label if i == 0 else None)
            w = sum(x < -1e-7 for x in d)
            lose = sum(x > 1e-7 for x in d)
            # win/tie/lose in a fixed row above the plot, so labels never collide with the marks
            ax.text(i + dx, 1.02, f"{w}/{len(d) - w - lose}/{lose}", transform=ax.get_xaxis_transform(),
                    ha="center", va="bottom", fontsize=6.5, color=INK, rotation=90)
    ax.set_yscale("symlog", linthresh=1)
    ax.set_yticks([-50, -10, -5, -1, -0.5, 0, 0.5])
    ax.set_yticklabels(["−50%", "−10%", "−5%", "−1%", "−0.5%", "0（修正前）", "+0.5%"])
    ax.set_ylim(-80, 0.8)
    ax.set_xticks(range(len(circuits)), circuits)
    ax.set_xlim(-0.6, len(circuits) - 0.4)
    ax.set_ylabel("NLL の変化（対 修正前、同じ seed）")
    style_axes(ax)
    ax.legend(frameon=False, loc="upper left", bbox_to_anchor=(0, -0.09), ncol=2, fontsize=8.5)
    fig.suptitle(f"全ベンチマーク回路: seed ごとの NLL 変化（L2、seed 0〜{max(seeds)}）", x=0.01, ha="left", fontsize=10)
    fig.text(0.01, 0.925, "下ほど改善。±1% の外は対数目盛。上の数字は修正前に対する 勝/同/負", fontsize=8, color=MUTED)
    fig.tight_layout(rect=(0, 0, 1, 0.84))
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("before")
    p.add_argument("after")
    p.add_argument("--device", default=str(HERE / "bad_bridge.json"))
    args = p.parse_args()
    runs = {}
    for f, tag in ((args.before, "before"), (args.after, "after")):
        for r in json.loads(Path(f).read_text())["runs"]:
            runs[f"{tag}:{r['config']}", r["circuit"], r["seed"]] = r
    dev = json.loads(Path(args.device).read_text())
    circuits = make_circuits()
    seeds = sorted({s for (_, _, s) in runs})
    jp_font()
    fig_rank(runs, candidates(dev, circuits), HERE / "fig_rank.png")
    fig_bench(runs, list(circuits), seeds, HERE / "fig_bench.png")
    print("wrote", HERE / "fig_rank.png", HERE / "fig_bench.png")


if __name__ == "__main__":
    main()

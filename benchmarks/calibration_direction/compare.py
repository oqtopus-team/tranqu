"""Compare Tranqu calibration and direction-aware benchmark results."""
import argparse
import json
from pathlib import Path
import statistics
import sys


def fmt_wtl(res: tuple[int, int, int] | None) -> str:
    if res is None:
        return "-"
    w, t, l = res
    return f"{w} / {t} / {l}"


def compute_wtl(lookup: dict, cfg_a: str, cfg_b: str, circuit: str | None = None) -> tuple[int, int, int] | None:
    circuits = [circuit] if circuit else sorted({c for (_, c, _) in lookup})
    seeds = sorted({s for (_, _, s) in lookup})
    w, t, l, count = 0, 0, 0, 0
    for c in circuits:
        for s in seeds:
            ra = lookup.get((cfg_a, c, s))
            rb = lookup.get((cfg_b, c, s))
            if ra is None or rb is None:
                continue
            diff = ra["nll"] - rb["nll"]
            if diff < -1e-9:
                w += 1
            elif diff > 1e-9:
                l += 1
            else:
                t += 1
            count += 1
    return (w, t, l) if count > 0 else None


def build_means_table(title: str, configs: list[str], circuits: list[str], lookup: dict) -> list[str]:
    lines = [
        f"### {title}",
        "",
        "| 回路 (Circuit) | 設定 (Config) | NLL | Gate NLL | 逆向きCX (Rev CX) | 物理1Q (sx+x) | 実行時間 [ns] | CX数 |",
        "|:---|:---|---:|---:|---:|---:|---:|---:|",
    ]
    for c in circuits:
        for cfg in configs:
            runs = [lookup[(cfg, c, s)] for (_, cur_c, s) in lookup if cur_c == c and (cfg, c, s) in lookup]
            if not runs:
                continue
            nll = statistics.mean(r["nll"] for r in runs)
            gnll = statistics.mean(r["gate_nll"] for r in runs)
            rev = statistics.mean(r["reversed_cx"] for r in runs)
            p1q = statistics.mean(r["phys1q"] for r in runs)
            dur = statistics.mean(r["duration_ns"] for r in runs)
            cx = statistics.mean(r["cx"] for r in runs)
            lines.append(f"| {c} | {cfg} | {nll:.4f} | {gnll:.4f} | {rev:.1f} | {p1q:.1f} | {dur:.1f} | {cx:.1f} |")

    # Overall mean across circuits
    for cfg in configs:
        runs = [lookup[(cfg, c, s)] for c in circuits for (_, cur_c, s) in lookup if cur_c == c and (cfg, c, s) in lookup]
        if not runs:
            continue
        nll = statistics.mean(r["nll"] for r in runs)
        gnll = statistics.mean(r["gate_nll"] for r in runs)
        rev = statistics.mean(r["reversed_cx"] for r in runs)
        p1q = statistics.mean(r["phys1q"] for r in runs)
        dur = statistics.mean(r["duration_ns"] for r in runs)
        cx = statistics.mean(r["cx"] for r in runs)
        lines.append(f"| **全体平均 (Mean)** | **{cfg}** | {nll:.4f} | {gnll:.4f} | {rev:.1f} | {p1q:.1f} | {dur:.1f} | {cx:.1f} |")
    lines.append("")
    return lines


def build_wtl_table(family: str, pairs: list[tuple[str, str]], circuits: list[str], lookup: dict) -> list[str]:
    valid_pairs = [(a, b) for a, b in pairs if any((a, c, s) in lookup for c in circuits for s in range(50)) and any((b, c, s) in lookup for c in circuits for s in range(50))]
    if not valid_pairs:
        return []

    headers = [f"{a} vs {b}" for a, b in valid_pairs]
    lines = [
        f"### {family} NLL 勝敗数 (Win / Tie / Lose per seed; Win: < -1e-9)",
        "",
        "| 回路 (Circuit) | " + " | ".join(headers) + " |",
        "|:---| " + " | ".join([":---:"] * len(headers)) + " |",
    ]
    for c in circuits:
        row = [c]
        for a, b in valid_pairs:
            row.append(fmt_wtl(compute_wtl(lookup, a, b, c)))
        lines.append("| " + " | ".join(row) + " |")

    total_row = ["**合計 (Total)**"]
    for a, b in valid_pairs:
        total_row.append(fmt_wtl(compute_wtl(lookup, a, b)))
    lines.append("| " + " | ".join(total_row) + " |")
    lines.append("")
    return lines


def build_layouts_table(configs: list[str], circuits: list[str], lookup: dict) -> list[str]:
    lines = [
        "### 初期配置 (Seed 0 Layouts)",
        "",
        "| 回路 (Circuit) | " + " | ".join(configs) + " |",
        "|:---| " + " | ".join([":---"] * len(configs)) + " |",
    ]
    for c in circuits:
        row = [c]
        for cfg in configs:
            run = lookup.get((cfg, c, 0))
            if run and "layout" in run:
                row.append(str(run["layout"]))
            else:
                row.append("-")
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")
    return lines


def build_sanity_table(configs: list[str], lookup: dict) -> list[str]:
    lines = [
        "### 健全性チェック (Sanity Checks)",
        "",
        "| 設定 (Config) | 不正OP数 (Illegal Ops) | 逆向きCX数 (Reversed CX) | Invalidate警告数 (Warnings) | 平均実行時間 (Mean Time) |",
        "|:---|---:|---:|---:|---:|",
    ]
    for cfg in configs:
        runs = [r for (c, _, _), r in lookup.items() if c == cfg]
        if not runs:
            continue
        illegal = sum(len(r["illegal_ops"]) if isinstance(r["illegal_ops"], (list, set)) else r["illegal_ops"] for r in runs)
        rev_cx = sum(r["reversed_cx"] for r in runs)
        warns = sum(r.get("n_warnings_invalidate", 0) for r in runs)
        mean_time = statistics.mean([r["time_s"] for r in runs if "time_s" in r] or [0.0])
        lines.append(f"| {cfg} | {illegal} | {rev_cx} | {warns} | {mean_time:.4f} s |")
    lines.append("")
    return lines


def main():
    p = argparse.ArgumentParser(description="Compare before and after benchmark JSONs")
    p.add_argument("before", help="Path to before.json")
    p.add_argument("after", help="Path to after.json")
    p.add_argument("--md", default=None, help="Optional output markdown file path")
    args = p.parse_args()

    b_path, a_path = Path(args.before), Path(args.after)
    if not b_path.exists():
        sys.exit(f"File not found: {b_path}")
    if not a_path.exists():
        sys.exit(f"File not found: {a_path}")

    b_data = json.loads(b_path.read_text())
    a_data = json.loads(a_path.read_text())

    lookup = {}
    circuits = []
    for r in b_data.get("runs", []):
        lookup[(f"before:{r['config']}", r["circuit"], r["seed"])] = r
        if r["circuit"] not in circuits:
            circuits.append(r["circuit"])
    for r in a_data.get("runs", []):
        lookup[(f"after:{r['config']}", r["circuit"], r["seed"])] = r
        if r["circuit"] not in circuits:
            circuits.append(r["circuit"])

    all_cfgs = []
    for tag, cfg in [("before", "basis"), ("after", "basis"), ("after", "basis_da"),
                     ("before", "basis_legacy"), ("after", "basis_legacy"), ("after", "basis_legacy_da")]:
        key = f"{tag}:{cfg}"
        if any(c == key for (c, _, _) in lookup) and key not in all_cfgs:
            all_cfgs.append(key)

    basis_cfgs = [c for c in ["before:basis", "after:basis", "after:basis_da"] if c in all_cfgs]
    legacy_cfgs = [c for c in ["before:basis_legacy", "after:basis_legacy", "after:basis_legacy_da"] if c in all_cfgs]

    b_meta, a_meta = b_data.get("meta", {}), a_data.get("meta", {})
    md_lines = [
        "# Tranqu 校正値・向き考慮トランスパイル比較レポート",
        "",
        f"- **Before**: rev `{b_meta.get('git_rev')}`, tranqu `{b_meta.get('tranqu_version')}`, qiskit `{b_meta.get('qiskit_version')}`",
        f"- **After**: rev `{a_meta.get('git_rev')}`, tranqu `{a_meta.get('tranqu_version')}`, qiskit `{a_meta.get('qiskit_version')}`",
        "",
    ]

    if basis_cfgs:
        md_lines.extend(build_means_table("Basis 設定 (Native Basis) 平均値", basis_cfgs, circuits, lookup))
        basis_pairs = [
            ("after:basis", "before:basis"),
            ("after:basis_da", "before:basis"),
            ("after:basis_da", "after:basis"),
        ]
        md_lines.extend(build_wtl_table("Basis 設定", basis_pairs, circuits, lookup))

    if legacy_cfgs:
        md_lines.extend(build_means_table("Legacy Basis 設定 平均値", legacy_cfgs, circuits, lookup))
        legacy_pairs = [
            ("after:basis_legacy", "before:basis_legacy"),
            ("after:basis_legacy_da", "before:basis_legacy"),
            ("after:basis_legacy_da", "after:basis_legacy"),
        ]
        md_lines.extend(build_wtl_table("Legacy Basis 設定", legacy_pairs, circuits, lookup))

    if all_cfgs:
        md_lines.extend(build_layouts_table(all_cfgs, circuits, lookup))
        md_lines.extend(build_sanity_table(all_cfgs, lookup))

    md_text = "\n".join(md_lines)
    print(md_text)

    if args.md:
        out_md = Path(args.md)
        out_md.parent.mkdir(parents=True, exist_ok=True)
        out_md.write_text(md_text)


if __name__ == "__main__":
    main()

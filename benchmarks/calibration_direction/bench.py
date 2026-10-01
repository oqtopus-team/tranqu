"""Benchmark Tranqu/Qiskit calibration and direction awareness across circuit topologies."""
import os

os.environ["QISKIT_NUM_PROCS"] = "1"
os.environ["RAYON_NUM_THREADS"] = "1"

import argparse, copy, json, math, random, subprocess, sys, time, warnings
from pathlib import Path
from qiskit import QuantumCircuit
from tranqu import Tranqu

NATIVE = ["rz", "sx", "cx", "measure"]
LEGACY = ["id", "sx", "x", "rz", "cx"]


def make_circuits() -> dict[str, QuantumCircuit]:
    cs = {}
    for name, n in [("bell2", 2), ("ghz4", 4), ("ghz5", 5), ("ghz8", 8), ("ghz16", 16), ("ghz21", 21)]:
        qc = QuantumCircuit(n)
        qc.h(0)
        for i in range(n - 1):
            qc.cx(i, i + 1)
        cs[name] = qc

    for name, n in (("star8", 8), ("grid9", 9), ("dense8", 8), ("random16", 16)):
        qc, rng = QuantumCircuit(n), random.Random(20260907)
        for _ in range(3):
            for i in range(n):
                qc.ry(rng.random(), i)
            if name.startswith("star"):
                pairs = [(0, i) for i in range(1, n)]
            elif name.startswith("grid"):
                pairs = [(i, j) for i in range(n) for j in range(i + 1, n)
                         if (j == i + 1 and i // 3 == j // 3) or j == i + 3]
            elif name.startswith("dense"):
                pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]
            else:
                order = list(range(n)); rng.shuffle(order); pairs = list(zip(order[::2], order[1::2]))
            for i, j in pairs:
                qc.cx(i, j)
        cs[name] = qc

    for qc in cs.values():
        qc.measure_all()
    return cs


def make_opts(cfg: str, seed: int) -> dict:
    bg = list(LEGACY if "legacy" in cfg else NATIVE)
    opts = dict(basis_gates=bg, optimization_level=2, seed_transpiler=seed)
    if cfg.endswith("_da"):
        opts["direction_aware"] = True
    return opts


def score_circuit(out: QuantumCircuit, cfg: str, dev: dict) -> dict:
    edges = {(c["control"], c["target"]) for c in dev["couplings"]}
    cx_fid = {(c["control"], c["target"]): c["fidelity"] for c in dev["couplings"]}
    cx_dur = {(c["control"], c["target"]): 2 * c["gate_duration"]["rzx90"] for c in dev["couplings"]}
    q_map = {q["id"]: q for q in dev["qubits"]}
    meas_err = {q["id"]: (q["meas_error"]["prob_meas1_prep0"] + q["meas_error"]["prob_meas0_prep1"]) / 2.0 for q in dev["qubits"]}
    allowed = (set(LEGACY) if "legacy" in cfg else set(NATIVE)) | {"barrier", "measure"}

    illegal_ops, rev_cx, phys1q, cx_count, nll, gate_nll = [], 0, 0, 0, 0.0, 0.0
    t_busy = [0.0] * out.num_qubits

    for inst in out.data:
        op = inst.operation.name
        if op not in allowed:
            illegal_ops.append(op)
        if op == "barrier":
            continue
        qargs = tuple(out.find_bit(q).index for q in inst.qubits)
        if op == "cx":
            cx_count += 1
            if qargs not in edges:
                rev_cx += 1
            fid = cx_fid.get(qargs) or cx_fid.get((qargs[1], qargs[0]), 0.5)
            err, dur, is_gate = 1.0 - fid, cx_dur.get(qargs) or cx_dur.get((qargs[1], qargs[0]), 0.0), True
        elif op == "measure":
            err, dur, is_gate = meas_err.get(qargs[0], 0.0), 0.0, False
        elif op == "rz":
            err, dur, is_gate = 0.0, 0.0, True
        else:
            if op in ("sx", "x"):
                phys1q += 1
            err = 1.0 - q_map.get(qargs[0], {}).get("fidelity", 1.0)
            dur = float(q_map.get(qargs[0], {}).get("gate_duration", {}).get(op, 0.0))
            is_gate = True

        term = -math.log1p(-max(0.0, min(err, 0.999999)))
        nll += term
        if is_gate:
            gate_nll += term
        if op != "measure":
            start = max(t_busy[x] for x in qargs) if qargs else 0.0
            for x in qargs:
                t_busy[x] = start + dur

    return {
        "layout": list(out.layout.initial_index_layout(filter_ancillas=True)),
        "cx": cx_count,
        "reversed_cx": rev_cx,
        "illegal_ops": illegal_ops,
        "phys1q": phys1q,
        "duration_ns": max(t_busy) if t_busy else 0.0,
        "nll": nll,
        "gate_nll": gate_nll,
    }


def get_metadata(configs: list[str], seeds: int) -> dict:
    try:
        import tranqu  # record the revision of the tranqu actually imported
        repo = Path(tranqu.__file__).resolve().parent
        git_rev = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "--short", "HEAD"], text=True, stderr=subprocess.DEVNULL).strip()
        dirty = subprocess.check_output(["git", "-C", str(repo), "status", "--porcelain", "--", "."], text=True, stderr=subprocess.DEVNULL).strip()
        git_rev += "+dirty" if dirty else ""
    except Exception:
        git_rev = "unknown"
    try:
        import importlib.metadata
        tq_ver = importlib.metadata.version("tranqu")
    except Exception:
        tq_ver = "unknown"
    try:
        import qiskit
        qk_ver = getattr(qiskit, "__version__", "unknown")
    except Exception:
        qk_ver = "unknown"
    return {"tranqu_version": tq_ver, "qiskit_version": qk_ver, "git_rev": git_rev, "configs": configs, "seeds": seeds}


def main():
    p = argparse.ArgumentParser(description="Tranqu calibration/direction benchmark")
    p.add_argument("--out", default="results.json", help="Path to output JSON file")
    p.add_argument("--configs", default="basis,basis_da", help="Comma-separated configs to run")
    p.add_argument("--seeds", type=int, default=10, help="Number of seeds (0..N-1)")
    p.add_argument("--device", default="bad_bridge.json", help="Path to device JSON file")
    args = p.parse_args()

    dev_path = Path(args.device)
    if not dev_path.exists():
        dev_path = Path(__file__).parent / args.device
    if not dev_path.exists():
        sys.exit(f"Device file not found: {args.device}")

    dev_data = json.loads(dev_path.read_text())
    circuits = make_circuits()
    cfg_list = [c.strip() for c in args.configs.split(",") if c.strip()]
    tq = Tranqu()
    runs, executed_configs = [], []

    for cfg in cfg_list:
        try:
            test_opts = make_opts(cfg, 0)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                tq.transpile(
                    program=circuits["bell2"], program_lib="qiskit", transpiler_lib="qiskit",
                    transpiler_options=copy.deepcopy(test_opts), device=copy.deepcopy(dev_data), device_lib="oqtopus",
                )
        except Exception as e:
            print(f"Skipping unsupported config '{cfg}': {e}", file=sys.stderr)
            continue

        executed_configs.append(cfg)
        cfg_failed = False
        print(f"Running config: {cfg}")

        for c_name, qc in circuits.items():
            if cfg_failed:
                break
            for seed in range(args.seeds):
                opts = make_opts(cfg, seed)
                try:
                    with warnings.catch_warnings(record=True) as captured:
                        warnings.simplefilter("always")
                        t0 = time.perf_counter()
                        res = tq.transpile(
                            program=qc, program_lib="qiskit", transpiler_lib="qiskit",
                            transpiler_options=copy.deepcopy(opts), device=copy.deepcopy(dev_data), device_lib="oqtopus",
                        )
                        elapsed = time.perf_counter() - t0
                except Exception as e:
                    print(f"Error in config '{cfg}' on {c_name} seed {seed}: {e}", file=sys.stderr)
                    runs = [r for r in runs if r["config"] != cfg]
                    executed_configs.remove(cfg)
                    cfg_failed = True
                    break

                out = res.transpiled_program
                inv_warns = sum(1 for w in captured if "invalidate" in str(w.message))
                runs.append({
                    "config": cfg, "circuit": c_name, "seed": seed,
                    "n_warnings_invalidate": inv_warns, "time_s": elapsed,
                    **score_circuit(out, cfg, dev_data),
                })

    meta = get_metadata(executed_configs, args.seeds)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({"meta": meta, "runs": runs}, indent=2))
    print(f"Saved {len(runs)} runs ({len(executed_configs)} configs) to {out_path}")


if __name__ == "__main__":
    main()

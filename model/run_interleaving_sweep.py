#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import math
import shutil
import subprocess
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, stdev


REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class RunRow:
    interleave_depth: int
    fixed_interval: int
    seed: int
    strategy: str
    total_cycles: int
    scrub_cycles: int
    reads: int
    writes: int
    corrected: int
    uncorrectable_detections: int
    unique_uncorrectable_words: int
    final_sdc_words: int
    final_dangerous_words: int
    new_due_count: int
    repeated_due_detections: int
    interval_switches: int
    memory_busy_cycles: int
    busy_per_mille: int


def run_cmd(cmd: list[str], log_path: Path | None = None) -> None:
    if log_path is None:
        subprocess.run(cmd, cwd=REPO_ROOT, check=True)
        return

    log_path.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    log_path.write_text(proc.stdout, encoding="utf-8")
    print(proc.stdout, end="")
    if proc.returncode != 0:
        raise subprocess.CalledProcessError(proc.returncode, cmd)


def compile_tb(addr_width: int, output: Path) -> None:
    run_cmd([
        "iverilog",
        "-g2012",
        f"-Ptb_strategy_comparison.ADDR_WIDTH={addr_width}",
        "-o",
        str(output),
        "rtl/secded_32_39_encoder.v",
        "rtl/secded_32_39_decoder.v",
        "rtl/protected_memory_model.v",
        "rtl/interval_selector.v",
        "rtl/measured_control_estimator.v",
        "rtl/adaptive_scrub_controller.v",
        "tb/tb_strategy_comparison.v",
    ])


def write_strategy_header(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "strategy,total_cycles,scrub_cycles,reads,writes,corrected,"
        "uncorrectable_detections,unique_uncorrectable_words,final_sdc_words,"
        "final_dangerous_words,new_due_count,repeated_due_detections,"
        "interval_switches,"
        "safe_entries,safe_cycles,scrub_active_cycles,memory_busy_cycles,"
        "scrub_per_mille,busy_per_mille,safe_per_mille\n",
        encoding="utf-8",
    )


def generate_fault_events(args: argparse.Namespace, depth: int, seed: int, run_dir: Path) -> None:
    run_cmd([
        "make",
        "gen_fault_events",
        f"ADDR_WIDTH={args.addr_width}",
        "FAULT_SCENARIO=upsets",
        f"FAULT_TOTAL_CYCLES={args.total_cycles}",
        f"FAULT_WINDOW_SIZE={args.window_size}",
        f"FAULT_EVENT_COUNT={args.single_event_count}",
        "FAULT_PAIRED_EVENT_COUNT=0",
        f"FAULT_CLUSTER_EVENT_COUNT={args.cluster_event_count}",
        f"FAULT_CLUSTER_BIT_COUNT={args.cluster_bit_count}",
        f"FAULT_CLUSTER_INTERLEAVE_DEPTH={depth}",
        f"FAULT_SEED={seed}",
        f"FAULT_META_OUTPUT={run_dir / 'fault_events_meta.csv'}",
        f"FAULT_SHIFT_SUMMARY_OUTPUT={run_dir / 'event_shift_summary.md'}",
        "CONTROL_SOURCE=quantization",
        "CONTROL_QUANTIZATION=linear_max",
    ], log_path=run_dir / "gen_fault_events.log")


def run_strategy(args: argparse.Namespace, compiled_out: Path, interval: int, run_dir: Path) -> RunRow:
    result_table = REPO_ROOT / "results/tables/strategy_comparison.csv"
    write_strategy_header(result_table)

    run_cmd([
        "vvp",
        str(compiled_out),
        "+STRATEGY=0",
        f"+TOTAL_RUN_CYCLES={args.total_cycles}",
        f"+FIXED_INTERVAL={interval}",
        f"+SAFE_INTERVAL={args.safe_interval}",
        f"+LEVEL0_INTERVAL={args.level0}",
        f"+LEVEL1_INTERVAL={args.level1}",
        f"+LEVEL2_INTERVAL={args.level2}",
        f"+LEVEL3_INTERVAL={args.level3}",
        f"+LEVEL4_INTERVAL={args.level4}",
        f"+LEVEL5_INTERVAL={args.level5}",
        f"+LEVEL6_INTERVAL={args.level6}",
        f"+LEVEL7_INTERVAL={args.level7}",
        "+TRACE_EXECUTION=0",
        "+DUMP_VCD=0",
    ], log_path=run_dir / "run.log")

    rows = list(csv.DictReader(result_table.open()))
    if len(rows) != 1:
        raise RuntimeError(f"expected one strategy result row, got {len(rows)}")

    row = rows[0]
    if None in row:
        raise RuntimeError(
            "strategy_comparison.csv contains extra positional fields; "
            "the generated header is stale relative to tb_strategy_comparison.v"
        )
    required_columns = {
        "unique_uncorrectable_words",
        "final_sdc_words",
        "final_dangerous_words",
        "new_due_count",
        "repeated_due_detections",
    }
    missing_columns = required_columns - set(row)
    if missing_columns:
        raise RuntimeError(
            f"strategy_comparison.csv is missing columns: {sorted(missing_columns)}"
        )
    shutil.copy2(result_table, run_dir / "strategy_comparison.csv")

    return RunRow(
        interleave_depth=int(run_dir.parts[-3].replace("D", "")),
        fixed_interval=interval,
        seed=int(run_dir.parts[-1].replace("seed_", "")),
        strategy=row["strategy"],
        total_cycles=int(row["total_cycles"]),
        scrub_cycles=int(row["scrub_cycles"]),
        reads=int(row["reads"]),
        writes=int(row["writes"]),
        corrected=int(row["corrected"]),
        uncorrectable_detections=int(row["uncorrectable_detections"]),
        unique_uncorrectable_words=int(row["unique_uncorrectable_words"]),
        final_sdc_words=int(row["final_sdc_words"]),
        final_dangerous_words=int(row["final_dangerous_words"]),
        new_due_count=int(row["new_due_count"]),
        repeated_due_detections=int(row["repeated_due_detections"]),
        interval_switches=int(row["interval_switches"]),
        memory_busy_cycles=int(row["memory_busy_cycles"]),
        busy_per_mille=int(row["busy_per_mille"]),
    )


def mean_std(values: list[int | float]) -> tuple[float, float]:
    if not values:
        return 0.0, 0.0
    if len(values) == 1:
        return float(values[0]), 0.0
    return float(mean(values)), float(stdev(values))


def ci95(values: list[float]) -> tuple[float, float, float, float]:
    if not values:
        return 0.0, 0.0, 0.0, 0.0
    m = mean(values)
    if len(values) == 1:
        return float(m), 0.0, float(m), float(m)
    s = stdev(values)
    half = 1.96 * s / math.sqrt(len(values))
    return float(m), float(s), float(m - half), float(m + half)


def write_runs_csv(path: Path, rows: list[RunRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "interleave_depth",
        "fixed_interval",
        "seed",
        "strategy",
        "total_cycles",
        "scrub_cycles",
        "reads",
        "writes",
        "corrected",
        "uncorrectable_detections",
        "unique_uncorrectable_words",
        "final_sdc_words",
        "final_dangerous_words",
        "new_due_count",
        "repeated_due_detections",
        "interval_switches",
        "memory_busy_cycles",
        "busy_per_mille",
        "busy_percent",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({
                "interleave_depth": r.interleave_depth,
                "fixed_interval": r.fixed_interval,
                "seed": r.seed,
                "strategy": r.strategy,
                "total_cycles": r.total_cycles,
                "scrub_cycles": r.scrub_cycles,
                "reads": r.reads,
                "writes": r.writes,
                "corrected": r.corrected,
                "uncorrectable_detections": r.uncorrectable_detections,
                "unique_uncorrectable_words": r.unique_uncorrectable_words,
                "final_sdc_words": r.final_sdc_words,
                "final_dangerous_words": r.final_dangerous_words,
                "new_due_count": r.new_due_count,
                "repeated_due_detections": r.repeated_due_detections,
                "interval_switches": r.interval_switches,
                "memory_busy_cycles": r.memory_busy_cycles,
                "busy_per_mille": r.busy_per_mille,
                "busy_percent": r.busy_per_mille / 10.0,
            })


def write_summary_csv(path: Path, rows: list[RunRow]) -> None:
    groups: dict[tuple[int, int], list[RunRow]] = defaultdict(list)
    for r in rows:
        groups[(r.interleave_depth, r.fixed_interval)].append(r)

    fields = [
        "interleave_depth",
        "fixed_interval",
        "runs",
        "busy_percent_mean",
        "busy_percent_std",
        "scrub_cycles_mean",
        "scrub_cycles_std",
        "corrected_mean",
        "corrected_std",
        "uncorrectable_detections_mean",
        "uncorrectable_detections_std",
        "unique_uncorrectable_words_mean",
        "unique_uncorrectable_words_std",
        "final_sdc_words_mean",
        "final_sdc_words_std",
        "final_dangerous_words_mean",
        "final_dangerous_words_std",
        "new_due_count_mean",
        "new_due_count_std",
        "repeated_due_detections_mean",
        "repeated_due_detections_std",
    ]

    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for depth, interval in sorted(groups):
            rs = groups[(depth, interval)]
            busy_m, busy_s = mean_std([r.busy_per_mille / 10.0 for r in rs])
            scrub_m, scrub_s = mean_std([r.scrub_cycles for r in rs])
            corr_m, corr_s = mean_std([r.corrected for r in rs])
            ded_m, ded_s = mean_std([r.uncorrectable_detections for r in rs])
            unique_m, unique_s = mean_std([r.unique_uncorrectable_words for r in rs])
            sdc_m, sdc_s = mean_std([r.final_sdc_words for r in rs])
            dangerous_m, dangerous_s = mean_std([r.final_dangerous_words for r in rs])
            new_due_m, new_due_s = mean_std([r.new_due_count for r in rs])
            repeated_m, repeated_s = mean_std([r.repeated_due_detections for r in rs])
            w.writerow({
                "interleave_depth": depth,
                "fixed_interval": interval,
                "runs": len(rs),
                "busy_percent_mean": f"{busy_m:.6f}",
                "busy_percent_std": f"{busy_s:.6f}",
                "scrub_cycles_mean": f"{scrub_m:.6f}",
                "scrub_cycles_std": f"{scrub_s:.6f}",
                "corrected_mean": f"{corr_m:.6f}",
                "corrected_std": f"{corr_s:.6f}",
                "uncorrectable_detections_mean": f"{ded_m:.6f}",
                "uncorrectable_detections_std": f"{ded_s:.6f}",
                "unique_uncorrectable_words_mean": f"{unique_m:.6f}",
                "unique_uncorrectable_words_std": f"{unique_s:.6f}",
                "final_sdc_words_mean": f"{sdc_m:.6f}",
                "final_sdc_words_std": f"{sdc_s:.6f}",
                "final_dangerous_words_mean": f"{dangerous_m:.6f}",
                "final_dangerous_words_std": f"{dangerous_s:.6f}",
                "new_due_count_mean": f"{new_due_m:.6f}",
                "new_due_count_std": f"{new_due_s:.6f}",
                "repeated_due_detections_mean": f"{repeated_m:.6f}",
                "repeated_due_detections_std": f"{repeated_s:.6f}",
            })


def write_deltas_csv(path: Path, rows: list[RunRow], intervals: list[int]) -> None:
    by_key = {(r.interleave_depth, r.fixed_interval, r.seed): r for r in rows}
    seeds = sorted({r.seed for r in rows})
    fields = [
        "comparison",
        "lhs_depth",
        "lhs_interval",
        "rhs_depth",
        "rhs_interval",
        "metric",
        "n",
        "delta_mean",
        "delta_std",
        "ci95_low",
        "ci95_high",
    ]

    comparisons: list[tuple[str, int, int, int, int]] = []
    for interval in intervals:
        comparisons.append((f"D3 - D1 at interval {interval}", 3, interval, 1, interval))
        comparisons.append((f"D3 - D2 at interval {interval}", 3, interval, 2, interval))

    fastest = min(intervals)
    slowest = max(intervals)
    for depth in [1, 2, 3]:
        comparisons.append((f"D{depth} slowest - fastest", depth, slowest, depth, fastest))

    metrics = [
        "corrected",
        "uncorrectable_detections",
        "unique_uncorrectable_words",
        "final_sdc_words",
        "final_dangerous_words",
        "new_due_count",
        "repeated_due_detections",
    ]

    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()

        for name, lhs_depth, lhs_interval, rhs_depth, rhs_interval in comparisons:
            for metric in metrics:
                deltas: list[float] = []
                for seed in seeds:
                    lhs_key = (lhs_depth, lhs_interval, seed)
                    rhs_key = (rhs_depth, rhs_interval, seed)
                    if lhs_key not in by_key or rhs_key not in by_key:
                        continue
                    lhs = by_key[lhs_key]
                    rhs = by_key[rhs_key]
                    deltas.append(float(getattr(lhs, metric) - getattr(rhs, metric)))

                if not deltas:
                    continue

                m, s, lo, hi = ci95(deltas)
                w.writerow({
                    "comparison": name,
                    "lhs_depth": lhs_depth,
                    "lhs_interval": lhs_interval,
                    "rhs_depth": rhs_depth,
                    "rhs_interval": rhs_interval,
                    "metric": metric,
                    "n": len(deltas),
                    "delta_mean": f"{m:.6f}",
                    "delta_std": f"{s:.6f}",
                    "ci95_low": f"{lo:.6f}",
                    "ci95_high": f"{hi:.6f}",
                })


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--output-dir", default="results/paper/interleaving/interval_sweep")
    p.add_argument("--addr-width", type=int, default=8)
    p.add_argument("--total-cycles", type=int, default=50000)
    p.add_argument("--window-size", type=int, default=43824)
    p.add_argument("--single-event-count", type=int, default=0)
    p.add_argument("--cluster-event-count", type=int, default=20)
    p.add_argument("--cluster-bit-count", type=int, default=3)
    p.add_argument("--seed-start", type=int, default=1)
    p.add_argument("--seed-count", type=int, default=10)
    p.add_argument("--intervals", default="1089,1244,1555,2021,2400")
    p.add_argument("--safe-interval", type=int, default=1089)
    p.add_argument("--level0", type=int, default=2400)
    p.add_argument("--level1", type=int, default=2200)
    p.add_argument("--level2", type=int, default=2000)
    p.add_argument("--level3", type=int, default=1800)
    p.add_argument("--level4", type=int, default=1600)
    p.add_argument("--level5", type=int, default=1400)
    p.add_argument("--level6", type=int, default=1200)
    p.add_argument("--level7", type=int, default=1089)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = REPO_ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    intervals = [int(x.strip()) for x in args.intervals.split(",") if x.strip()]
    depths = [1, 2, 3]
    seeds = list(range(args.seed_start, args.seed_start + args.seed_count))

    compiled_out = REPO_ROOT / "results/logs/interleaving_sweep.out"
    compile_tb(args.addr_width, compiled_out)

    rows: list[RunRow] = []

    for depth in depths:
        for interval in intervals:
            for seed in seeds:
                run_dir = output_dir / f"D{depth}" / f"interval_{interval}" / f"seed_{seed:03d}"
                run_dir.mkdir(parents=True, exist_ok=True)

                generate_fault_events(args, depth, seed, run_dir)
                row = run_strategy(args, compiled_out, interval, run_dir)
                rows.append(row)

    write_runs_csv(output_dir / "interleaving_interval_sweep_runs.csv", rows)
    write_summary_csv(output_dir / "interleaving_interval_sweep_summary.csv", rows)
    write_deltas_csv(output_dir / "interleaving_interval_sweep_deltas.csv", rows, intervals)

    print(f"Wrote {output_dir / 'interleaving_interval_sweep_runs.csv'}")
    print(f"Wrote {output_dir / 'interleaving_interval_sweep_summary.csv'}")
    print(f"Wrote {output_dir / 'interleaving_interval_sweep_deltas.csv'}")


if __name__ == "__main__":
    main()

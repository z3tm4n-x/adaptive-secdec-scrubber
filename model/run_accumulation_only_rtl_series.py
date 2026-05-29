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
    new_due_count: int
    repeated_due_detections: int
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
        "uncorrectable_detections,unique_uncorrectable_words,new_due_count,"
        "repeated_due_detections,interval_switches,safe_entries,safe_cycles,"
        "scrub_active_cycles,memory_busy_cycles,scrub_per_mille,busy_per_mille,"
        "safe_per_mille\n",
        encoding="utf-8",
    )


def generate_fault_events(args: argparse.Namespace, seed: int, run_dir: Path) -> None:
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
        f"FAULT_CLUSTER_INTERLEAVE_DEPTH={args.interleave_depth}",
        f"FAULT_SEED={seed}",
        f"FAULT_META_OUTPUT={run_dir / 'fault_events_meta.csv'}",
        f"FAULT_SHIFT_SUMMARY_OUTPUT={run_dir / 'event_shift_summary.md'}",
        "CONTROL_SOURCE=quantization",
        "CONTROL_QUANTIZATION=linear_max",
    ], log_path=run_dir / "gen_fault_events.log")


def run_strategy(args: argparse.Namespace, compiled_out: Path, interval: int, seed: int, run_dir: Path) -> RunRow:
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
    shutil.copy2(result_table, run_dir / "strategy_comparison.csv")

    return RunRow(
        interleave_depth=args.interleave_depth,
        fixed_interval=interval,
        seed=seed,
        strategy=row["strategy"],
        total_cycles=int(row["total_cycles"]),
        scrub_cycles=int(row["scrub_cycles"]),
        reads=int(row["reads"]),
        writes=int(row["writes"]),
        corrected=int(row["corrected"]),
        uncorrectable_detections=int(row["uncorrectable_detections"]),
        unique_uncorrectable_words=int(row["unique_uncorrectable_words"]),
        new_due_count=int(row["new_due_count"]),
        repeated_due_detections=int(row["repeated_due_detections"]),
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
        "new_due_count",
        "repeated_due_detections",
        "memory_busy_cycles",
        "busy_per_mille",
        "busy_percent",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
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
                "new_due_count": r.new_due_count,
                "repeated_due_detections": r.repeated_due_detections,
                "memory_busy_cycles": r.memory_busy_cycles,
                "busy_per_mille": r.busy_per_mille,
                "busy_percent": r.busy_per_mille / 10.0,
            })


def write_summary_csv(path: Path, rows: list[RunRow]) -> None:
    groups: dict[int, list[RunRow]] = defaultdict(list)
    for r in rows:
        groups[r.fixed_interval].append(r)

    fields = [
        "interleave_depth",
        "fixed_interval",
        "runs",
        "busy_percent_mean",
        "busy_percent_std",
        "corrected_mean",
        "corrected_std",
        "uncorrectable_detections_mean",
        "uncorrectable_detections_std",
        "new_due_count_mean",
        "new_due_count_std",
        "repeated_due_detections_mean",
        "repeated_due_detections_std",
        "unique_uncorrectable_words_mean",
        "unique_uncorrectable_words_std",
    ]

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()

        for interval in sorted(groups):
            rs = groups[interval]
            busy_m, busy_s = mean_std([r.busy_per_mille / 10.0 for r in rs])
            corrected_m, corrected_s = mean_std([r.corrected for r in rs])
            ded_m, ded_s = mean_std([r.uncorrectable_detections for r in rs])
            new_m, new_s = mean_std([r.new_due_count for r in rs])
            repeated_m, repeated_s = mean_std([r.repeated_due_detections for r in rs])
            unique_m, unique_s = mean_std([r.unique_uncorrectable_words for r in rs])

            w.writerow({
                "interleave_depth": rs[0].interleave_depth,
                "fixed_interval": interval,
                "runs": len(rs),
                "busy_percent_mean": f"{busy_m:.6f}",
                "busy_percent_std": f"{busy_s:.6f}",
                "corrected_mean": f"{corrected_m:.6f}",
                "corrected_std": f"{corrected_s:.6f}",
                "uncorrectable_detections_mean": f"{ded_m:.6f}",
                "uncorrectable_detections_std": f"{ded_s:.6f}",
                "new_due_count_mean": f"{new_m:.6f}",
                "new_due_count_std": f"{new_s:.6f}",
                "repeated_due_detections_mean": f"{repeated_m:.6f}",
                "repeated_due_detections_std": f"{repeated_s:.6f}",
                "unique_uncorrectable_words_mean": f"{unique_m:.6f}",
                "unique_uncorrectable_words_std": f"{unique_s:.6f}",
            })


def write_delta_csv(path: Path, rows: list[RunRow], intervals: list[int]) -> None:
    if len(intervals) != 2:
        raise ValueError("delta writer expects exactly two intervals")

    fast = min(intervals)
    slow = max(intervals)

    by_key = {(r.fixed_interval, r.seed): r for r in rows}

    fields = [
        "comparison",
        "metric",
        "n",
        "delta_mean",
        "delta_std",
        "ci95_low",
        "ci95_high",
    ]

    metrics = [
        "corrected",
        "uncorrectable_detections",
        "new_due_count",
        "repeated_due_detections",
        "unique_uncorrectable_words",
        "busy_per_mille",
    ]

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()

        for metric in metrics:
            deltas: list[float] = []
            for seed in sorted({r.seed for r in rows}):
                lhs = by_key[(slow, seed)]
                rhs = by_key[(fast, seed)]
                deltas.append(float(getattr(lhs, metric) - getattr(rhs, metric)))

            m, s, lo, hi = ci95(deltas)
            w.writerow({
                "comparison": f"interval_{slow}_minus_{fast}",
                "metric": metric,
                "n": len(deltas),
                "delta_mean": f"{m:.6f}",
                "delta_std": f"{s:.6f}",
                "ci95_low": f"{lo:.6f}",
                "ci95_high": f"{hi:.6f}",
            })


def write_markdown(path: Path, rows: list[RunRow], intervals: list[int]) -> None:
    by_interval: dict[int, list[RunRow]] = defaultdict(list)
    for r in rows:
        by_interval[r.fixed_interval].append(r)

    lines: list[str] = []
    lines.append("# RTL accumulation-only interleaving series")
    lines.append("")
    lines.append("## Purpose")
    lines.append("")
    lines.append(
        "This RTL series exercises the accumulation-only regime after sufficient "
        "interleaving. For `cluster_bit_count=3` and `D=3`, each physical cluster is "
        "split as 1+1+1 across SECDED codewords, so the instant same-event DED component "
        "is removed in the logical round-robin model."
    )
    lines.append("")
    lines.append(
        "The run uses the latched runtime DUE metrics added to the strategy testbench: "
        "`new_due_count` counts first DUE appearances, while `repeated_due_detections` "
        "counts repeated diagnostic detections of already-latched DUE words."
    )
    lines.append("")
    lines.append("## Summary by interval")
    lines.append("")
    lines.append("| fixed interval | runs | busy, % | corrected | DED detections | new DUE | repeated DED | final unique DUE |")
    lines.append("|---:|---:|---:|---:|---:|---:|---:|---:|")

    for interval in sorted(by_interval):
        rs = by_interval[interval]
        busy_m, busy_s = mean_std([r.busy_per_mille / 10.0 for r in rs])
        corrected_m, corrected_s = mean_std([r.corrected for r in rs])
        ded_m, ded_s = mean_std([r.uncorrectable_detections for r in rs])
        new_m, new_s = mean_std([r.new_due_count for r in rs])
        repeated_m, repeated_s = mean_std([r.repeated_due_detections for r in rs])
        unique_m, unique_s = mean_std([r.unique_uncorrectable_words for r in rs])

        lines.append(
            f"| {interval} | {len(rs)} | {busy_m:.3f} ± {busy_s:.3f} | "
            f"{corrected_m:.1f} ± {corrected_s:.1f} | "
            f"{ded_m:.1f} ± {ded_s:.1f} | "
            f"{new_m:.3f} ± {new_s:.3f} | "
            f"{repeated_m:.1f} ± {repeated_s:.1f} | "
            f"{unique_m:.3f} ± {unique_s:.3f} |"
        )

    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    lines.append(
        "The series is expected to have zero or very low `new_due_count` because D=3 "
        "removes the instant DED part of 3-bit clusters. Any remaining DUE appears only "
        "from accumulation or repeated injection into already affected words, and is "
        "therefore the component that scrub interval can influence."
    )
    lines.append("")
    lines.append(
        "This is an RTL feasibility check of the theory's `g_D = 0` branch, not a "
        "device-level radiation validation."
    )
    lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--output-dir", default="results/paper/accumulation_only_rtl")
    p.add_argument("--addr-width", type=int, default=8)
    p.add_argument("--total-cycles", type=int, default=50000)
    p.add_argument("--window-size", type=int, default=43824)
    p.add_argument("--single-event-count", type=int, default=0)
    p.add_argument("--cluster-event-count", type=int, default=20)
    p.add_argument("--cluster-bit-count", type=int, default=3)
    p.add_argument("--interleave-depth", type=int, default=3)
    p.add_argument("--seed-start", type=int, default=1)
    p.add_argument("--seed-count", type=int, default=10)
    p.add_argument("--intervals", default="1089,2400")
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

    if args.interleave_depth < args.cluster_bit_count:
        raise ValueError("accumulation-only series requires D >= cluster_bit_count")

    intervals = [int(x.strip()) for x in args.intervals.split(",") if x.strip()]
    if len(intervals) != 2:
        raise ValueError("Use exactly two intervals for the accumulation-only RTL delta")

    output_dir = REPO_ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    compiled_out = REPO_ROOT / "results/logs/accumulation_only_rtl.out"
    compile_tb(args.addr_width, compiled_out)

    rows: list[RunRow] = []
    seeds = list(range(args.seed_start, args.seed_start + args.seed_count))

    for interval in intervals:
        for seed in seeds:
            run_dir = output_dir / f"interval_{interval}" / f"seed_{seed:03d}"
            run_dir.mkdir(parents=True, exist_ok=True)

            generate_fault_events(args, seed, run_dir)
            row = run_strategy(args, compiled_out, interval, seed, run_dir)
            rows.append(row)

    write_runs_csv(output_dir / "accumulation_only_rtl_runs.csv", rows)
    write_summary_csv(output_dir / "accumulation_only_rtl_summary.csv", rows)
    write_delta_csv(output_dir / "accumulation_only_rtl_deltas.csv", rows, intervals)
    write_markdown(output_dir / "accumulation_only_rtl_summary.md", rows, intervals)

    print(f"rows: {len(rows)}")
    print(f"runs: {output_dir / 'accumulation_only_rtl_runs.csv'}")
    print(f"summary: {output_dir / 'accumulation_only_rtl_summary.csv'}")
    print(f"deltas: {output_dir / 'accumulation_only_rtl_deltas.csv'}")
    print(f"markdown: {output_dir / 'accumulation_only_rtl_summary.md'}")

    for interval in intervals:
        rs = [r for r in rows if r.fixed_interval == interval]
        new_mean, new_std = mean_std([r.new_due_count for r in rs])
        unique_mean, unique_std = mean_std([r.unique_uncorrectable_words for r in rs])
        print(
            f"interval {interval}: new_due_mean={new_mean:.6f} "
            f"new_due_std={new_std:.6f} unique_mean={unique_mean:.6f} "
            f"unique_std={unique_std:.6f}"
        )


if __name__ == "__main__":
    main()

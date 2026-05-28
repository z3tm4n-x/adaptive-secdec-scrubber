#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, stdev
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class StrategyRun:
    seed: int
    strategy_id: int
    strategy_name: str
    total_cycles: int
    scrub_cycles: int
    reads: int
    writes: int
    corrected: int
    uncorrectable_detections: int
    unique_uncorrectable_words: int
    interval_switches: int
    safe_entries: int
    safe_cycles: int
    scrub_active_cycles: int
    memory_busy_cycles: int
    scrub_per_mille: int
    busy_per_mille: int
    safe_per_mille: int


def run_cmd(cmd: list[str], *, cwd: Path, log_path: Path | None = None) -> None:
    if log_path is None:
        subprocess.run(cmd, cwd=cwd, check=True)
        return

    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as f:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
        f.write(proc.stdout)
        print(proc.stdout, end="")
        if proc.returncode != 0:
            raise subprocess.CalledProcessError(proc.returncode, cmd)


def compile_tb(addr_width: int, output: Path) -> None:
    cmd = [
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
    ]
    run_cmd(cmd, cwd=REPO_ROOT)


def generate_fault_events(args: argparse.Namespace, seed: int, out_dir: Path) -> None:
    cmd = [
        "make",
        "gen_fault_events",
        f"ADDR_WIDTH={args.addr_width}",
        "FAULT_SCENARIO=upsets",
        f"FAULT_TOTAL_CYCLES={args.total_cycles}",
        f"FAULT_WINDOW_SIZE={args.window_size}",
        f"FAULT_EVENT_COUNT={args.event_count}",
        f"FAULT_PAIRED_EVENT_COUNT={args.paired_event_count}",
        f"FAULT_PAIR_GAP_MIN={args.pair_gap_min}",
        f"FAULT_PAIR_GAP_MAX={args.pair_gap_max}",
        f"FAULT_CLUSTER_EVENT_COUNT={args.cluster_event_count}",
        f"FAULT_SEED={seed}",
        f"FAULT_META_OUTPUT={out_dir / 'fault_events_meta.csv'}",
        f"FAULT_SHIFT_SUMMARY_OUTPUT={out_dir / 'event_shift_summary.md'}",
        "CONTROL_SOURCE=quantization",
        "CONTROL_QUANTIZATION=linear_max",
    ]
    run_cmd(cmd, cwd=REPO_ROOT, log_path=out_dir / "gen_fault_events.log")


def write_strategy_header(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "strategy,total_cycles,scrub_cycles,reads,writes,corrected,"
        "uncorrectable_detections,unique_uncorrectable_words,interval_switches,"
        "safe_entries,safe_cycles,scrub_active_cycles,memory_busy_cycles,"
        "scrub_per_mille,busy_per_mille,safe_per_mille\n",
        encoding="utf-8",
    )


def write_trace_header(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "strategy,cycle,scrub_cycle_count,selected_interval,effective_wait_interval,"
        "last_pass_duration,current_level,threshold_state,safe_mode_active,control_age,"
        "corrected_error_count,uncorrectable_error_count,memory_read_count,memory_write_count,"
        "measured_ctrl_level,measured_ctrl_valid,measured_ctrl_update,measured_window_count,"
        "measured_corrected_delta,measured_uncorrectable_delta,measured_raw_score\n",
        encoding="utf-8",
    )


def run_strategy(
    args: argparse.Namespace,
    compiled_out: Path,
    seed: int,
    strategy_id: int,
    run_dir: Path,
) -> StrategyRun:
    result_table = REPO_ROOT / "results/tables/strategy_comparison.csv"
    write_strategy_header(result_table)

    trace_path = run_dir / "execution_trace.csv"
    write_trace_header(trace_path)

    cmd = [
        "vvp",
        str(compiled_out),
        f"+STRATEGY={strategy_id}",
        f"+TOTAL_RUN_CYCLES={args.total_cycles}",
        f"+FIXED_INTERVAL={args.fixed_interval}",
        f"+SAFE_INTERVAL={args.safe_interval}",
        f"+LEVEL0_INTERVAL={args.level0}",
        f"+LEVEL1_INTERVAL={args.level1}",
        f"+LEVEL2_INTERVAL={args.level2}",
        f"+LEVEL3_INTERVAL={args.level3}",
        f"+LEVEL4_INTERVAL={args.level4}",
        f"+LEVEL5_INTERVAL={args.level5}",
        f"+LEVEL6_INTERVAL={args.level6}",
        f"+LEVEL7_INTERVAL={args.level7}",
        " +THRESHOLD_LOW_TO_MEDIUM=3".strip(),
        " +THRESHOLD_MEDIUM_TO_LOW=1".strip(),
        " +THRESHOLD_MEDIUM_TO_HIGH=6".strip(),
        " +THRESHOLD_HIGH_TO_MEDIUM=4".strip(),
        f"+THRESHOLD_LOW_INTERVAL={args.level0}",
        f"+THRESHOLD_MEDIUM_INTERVAL={args.level3}",
        f"+THRESHOLD_HIGH_INTERVAL={args.level7}",
        "+TRACE_EXECUTION=1",
        f"+TRACE_OUTPUT={trace_path}",
        "+DUMP_VCD=0",
    ]

    run_cmd(cmd, cwd=REPO_ROOT, log_path=run_dir / "run.log")

    with result_table.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    if len(rows) != 1:
        raise RuntimeError(f"expected one strategy row, got {len(rows)} for seed={seed}, strategy={strategy_id}")

    row = rows[0]
    strategy_name = row["strategy"]

    shutil.copy2(result_table, run_dir / "strategy_comparison.csv")

    return StrategyRun(
        seed=seed,
        strategy_id=strategy_id,
        strategy_name=strategy_name,
        total_cycles=int(row["total_cycles"]),
        scrub_cycles=int(row["scrub_cycles"]),
        reads=int(row["reads"]),
        writes=int(row["writes"]),
        corrected=int(row["corrected"]),
        uncorrectable_detections=int(row["uncorrectable_detections"]),
        unique_uncorrectable_words=int(row["unique_uncorrectable_words"]),
        interval_switches=int(row["interval_switches"]),
        safe_entries=int(row["safe_entries"]),
        safe_cycles=int(row["safe_cycles"]),
        scrub_active_cycles=int(row["scrub_active_cycles"]),
        memory_busy_cycles=int(row["memory_busy_cycles"]),
        scrub_per_mille=int(row["scrub_per_mille"]),
        busy_per_mille=int(row["busy_per_mille"]),
        safe_per_mille=int(row["safe_per_mille"]),
    )


def write_series_csv(path: Path, rows: list[StrategyRun]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "seed",
        "strategy_id",
        "strategy",
        "total_cycles",
        "scrub_cycles",
        "reads",
        "writes",
        "corrected",
        "uncorrectable_detections",
        "unique_uncorrectable_words",
        "interval_switches",
        "safe_entries",
        "safe_cycles",
        "scrub_active_cycles",
        "memory_busy_cycles",
        "scrub_per_mille",
        "busy_per_mille",
        "safe_per_mille",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({
                "seed": r.seed,
                "strategy_id": r.strategy_id,
                "strategy": r.strategy_name,
                "total_cycles": r.total_cycles,
                "scrub_cycles": r.scrub_cycles,
                "reads": r.reads,
                "writes": r.writes,
                "corrected": r.corrected,
                "uncorrectable_detections": r.uncorrectable_detections,
                "unique_uncorrectable_words": r.unique_uncorrectable_words,
                "interval_switches": r.interval_switches,
                "safe_entries": r.safe_entries,
                "safe_cycles": r.safe_cycles,
                "scrub_active_cycles": r.scrub_active_cycles,
                "memory_busy_cycles": r.memory_busy_cycles,
                "scrub_per_mille": r.scrub_per_mille,
                "busy_per_mille": r.busy_per_mille,
                "safe_per_mille": r.safe_per_mille,
            })


def mean_sd(values: Iterable[int]) -> tuple[float, float]:
    vals = list(values)
    if len(vals) <= 1:
        return float(vals[0]) if vals else 0.0, 0.0
    return mean(vals), stdev(vals)


def write_summary(path: Path, rows: list[StrategyRun], args: argparse.Namespace) -> None:
    by_strategy: dict[str, list[StrategyRun]] = {}
    for r in rows:
        by_strategy.setdefault(r.strategy_name, []).append(r)

    lines: list[str] = []
    lines.append("# Closed-loop measured-control multi-seed summary")
    lines.append("")
    lines.append("This experiment compares the closed-loop measured strategy against")
    lines.append("fixed, table, and threshold strategies on the same generated fault")
    lines.append("streams for each seed.")
    lines.append("")
    lines.append("## Configuration")
    lines.append("")
    lines.append(f"- Address width: {args.addr_width}")
    lines.append(f"- Memory depth: {1 << args.addr_width} SECDED codewords")
    lines.append(f"- Total cycles per run: {args.total_cycles}")
    lines.append(f"- Seeds: {args.seed_start}..{args.seed_start + args.seed_count - 1}")
    lines.append(f"- Single events: {args.event_count}")
    lines.append(f"- Paired events: {args.paired_event_count}")
    lines.append(f"- Cluster events: {args.cluster_event_count}")
    lines.append(f"- Level intervals: {args.level0}, {args.level1}, {args.level2}, {args.level3}, {args.level4}, {args.level5}, {args.level6}, {args.level7}")
    lines.append("")
    lines.append("## Aggregate metrics")
    lines.append("")
    lines.append("| strategy | busy % mean | busy % sd | unique DUE mean | unique DUE sd | DED detections mean | DED detections sd | interval switches mean |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|")

    for strategy in sorted(by_strategy):
        rs = by_strategy[strategy]
        busy_m, busy_s = mean_sd([r.busy_per_mille for r in rs])
        unique_m, unique_s = mean_sd([r.unique_uncorrectable_words for r in rs])
        ded_m, ded_s = mean_sd([r.uncorrectable_detections for r in rs])
        sw_m, _ = mean_sd([r.interval_switches for r in rs])
        lines.append(
            f"| {strategy} | {busy_m/10:.2f} | {busy_s/10:.2f} | "
            f"{unique_m:.2f} | {unique_s:.2f} | {ded_m:.2f} | {ded_s:.2f} | {sw_m:.2f} |"
        )

    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    lines.append("The measured strategy is a closed-loop RTL mode: its control level is")
    lines.append("formed inside the controller from corrected and DED counter deltas.")
    lines.append("This summary is an integration/statistical smoke result; it is not yet")
    lines.append("the final risk-busy comparison used for dissertation conclusions.")
    lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--output-dir", default="results/paper/measured_control/closed_loop")
    p.add_argument("--addr-width", type=int, default=8)
    p.add_argument("--seed-start", type=int, default=1)
    p.add_argument("--seed-count", type=int, default=10)
    p.add_argument("--total-cycles", type=int, default=500000)
    p.add_argument("--window-size", type=int, default=43824)
    p.add_argument("--event-count", type=int, default=400)
    p.add_argument("--paired-event-count", type=int, default=100)
    p.add_argument("--pair-gap-min", type=int, default=60)
    p.add_argument("--pair-gap-max", type=int, default=300)
    p.add_argument("--cluster-event-count", type=int, default=0)

    p.add_argument("--fixed-interval", type=int, default=1800)
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

    compiled_out = REPO_ROOT / "results/logs/strategy_comparison_closed_loop_measured.out"
    compile_tb(args.addr_width, compiled_out)

    all_rows: list[StrategyRun] = []
    strategy_ids = [0, 1, 2, 3]

    for seed in range(args.seed_start, args.seed_start + args.seed_count):
        seed_dir = output_dir / f"seed_{seed:03d}"
        seed_dir.mkdir(parents=True, exist_ok=True)

        generate_fault_events(args, seed, seed_dir)

        for strategy_id in strategy_ids:
            run_dir = seed_dir / f"strategy_{strategy_id}"
            run_dir.mkdir(parents=True, exist_ok=True)
            row = run_strategy(args, compiled_out, seed, strategy_id, run_dir)
            all_rows.append(row)

    series_csv = output_dir / "closed_loop_measured_series.csv"
    summary_md = output_dir / "closed_loop_measured_summary.md"

    write_series_csv(series_csv, all_rows)
    write_summary(summary_md, all_rows, args)

    print(f"Wrote {series_csv}")
    print(f"Wrote {summary_md}")


if __name__ == "__main__":
    main()

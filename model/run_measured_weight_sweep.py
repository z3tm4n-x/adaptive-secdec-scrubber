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
class MeasuredConfig:
    name: str
    corrected_weight: int
    uncorrectable_weight: int
    window_cycles: int
    description: str


@dataclass(frozen=True)
class RunRow:
    config: str
    config_description: str
    corrected_weight: int
    uncorrectable_weight: int
    window_cycles: int
    seed: int
    strategy_id: int
    strategy: str
    total_cycles: int
    corrected: int
    uncorrectable_detections: int
    unique_uncorrectable_words: int
    new_due_count: int
    repeated_due_detections: int
    interval_switches: int
    scrub_active_cycles: int
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


def configs() -> list[MeasuredConfig]:
    return [
        MeasuredConfig(
            name="default_2c_1d",
            corrected_weight=2,
            uncorrectable_weight=1,
            window_cycles=25000,
            description="Default dissertation calibration: raw_score = 2*Cdelta + 1*Ddelta.",
        ),
        MeasuredConfig(
            name="corrected_only_2c_0d",
            corrected_weight=2,
            uncorrectable_weight=0,
            window_cycles=25000,
            description="Ablation that removes DED detections from the estimator input.",
        ),
        MeasuredConfig(
            name="ded_heavy_1c_2d",
            corrected_weight=1,
            uncorrectable_weight=2,
            window_cycles=25000,
            description="Diagnostic DED-heavy estimator input.",
        ),
    ]


def compile_tb(args: argparse.Namespace, cfg: MeasuredConfig, output: Path) -> None:
    run_cmd([
        "iverilog",
        "-g2012",
        f"-Ptb_strategy_comparison.ADDR_WIDTH={args.addr_width}",
        f"-Ptb_strategy_comparison.MEASURED_WINDOW_CYCLES={cfg.window_cycles}",
        f"-Ptb_strategy_comparison.MEASURED_CORRECTED_WEIGHT={cfg.corrected_weight}",
        f"-Ptb_strategy_comparison.MEASURED_UNCORRECTABLE_WEIGHT={cfg.uncorrectable_weight}",
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
        f"FAULT_EVENT_COUNT={args.event_count}",
        f"FAULT_PAIRED_EVENT_COUNT={args.paired_event_count}",
        f"FAULT_PAIR_GAP_MIN={args.pair_gap_min}",
        f"FAULT_PAIR_GAP_MAX={args.pair_gap_max}",
        f"FAULT_CLUSTER_EVENT_COUNT={args.cluster_event_count}",
        f"FAULT_SEED={seed}",
        f"FAULT_META_OUTPUT={run_dir / 'fault_events_meta.csv'}",
        f"FAULT_SHIFT_SUMMARY_OUTPUT={run_dir / 'event_shift_summary.md'}",
        "CONTROL_SOURCE=quantization",
        "CONTROL_QUANTIZATION=linear_max",
    ], log_path=run_dir / "gen_fault_events.log")


def run_strategy(
    args: argparse.Namespace,
    cfg: MeasuredConfig,
    compiled_out: Path,
    seed: int,
    strategy_id: int,
    run_dir: Path,
) -> RunRow:
    result_table = REPO_ROOT / "results/tables/strategy_comparison.csv"
    write_strategy_header(result_table)

    run_cmd([
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
        "+THRESHOLD_LOW_TO_MEDIUM=3",
        "+THRESHOLD_MEDIUM_TO_LOW=1",
        "+THRESHOLD_MEDIUM_TO_HIGH=6",
        "+THRESHOLD_HIGH_TO_MEDIUM=4",
        f"+THRESHOLD_LOW_INTERVAL={args.level0}",
        f"+THRESHOLD_MEDIUM_INTERVAL={args.level3}",
        f"+THRESHOLD_HIGH_INTERVAL={args.level7}",
        "+TRACE_EXECUTION=0",
        "+DUMP_VCD=0",
    ], log_path=run_dir / "run.log")

    with result_table.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    if len(rows) != 1:
        raise RuntimeError(f"expected one row, got {len(rows)}")

    row = rows[0]
    shutil.copy2(result_table, run_dir / "strategy_comparison.csv")

    return RunRow(
        config=cfg.name,
        config_description=cfg.description,
        corrected_weight=cfg.corrected_weight,
        uncorrectable_weight=cfg.uncorrectable_weight,
        window_cycles=cfg.window_cycles,
        seed=seed,
        strategy_id=strategy_id,
        strategy=row["strategy"],
        total_cycles=int(row["total_cycles"]),
        corrected=int(row["corrected"]),
        uncorrectable_detections=int(row["uncorrectable_detections"]),
        unique_uncorrectable_words=int(row["unique_uncorrectable_words"]),
        new_due_count=int(row["new_due_count"]),
        repeated_due_detections=int(row["repeated_due_detections"]),
        interval_switches=int(row["interval_switches"]),
        scrub_active_cycles=int(row["scrub_active_cycles"]),
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
        "config",
        "config_description",
        "corrected_weight",
        "uncorrectable_weight",
        "window_cycles",
        "seed",
        "strategy_id",
        "strategy",
        "total_cycles",
        "corrected",
        "uncorrectable_detections",
        "unique_uncorrectable_words",
        "new_due_count",
        "repeated_due_detections",
        "interval_switches",
        "scrub_active_cycles",
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
                "config": r.config,
                "config_description": r.config_description,
                "corrected_weight": r.corrected_weight,
                "uncorrectable_weight": r.uncorrectable_weight,
                "window_cycles": r.window_cycles,
                "seed": r.seed,
                "strategy_id": r.strategy_id,
                "strategy": r.strategy,
                "total_cycles": r.total_cycles,
                "corrected": r.corrected,
                "uncorrectable_detections": r.uncorrectable_detections,
                "unique_uncorrectable_words": r.unique_uncorrectable_words,
                "new_due_count": r.new_due_count,
                "repeated_due_detections": r.repeated_due_detections,
                "interval_switches": r.interval_switches,
                "scrub_active_cycles": r.scrub_active_cycles,
                "memory_busy_cycles": r.memory_busy_cycles,
                "busy_per_mille": r.busy_per_mille,
                "busy_percent": r.busy_per_mille / 10.0,
            })


def write_summary_csv(path: Path, rows: list[RunRow]) -> None:
    groups: dict[tuple[str, str], list[RunRow]] = defaultdict(list)
    for r in rows:
        groups[(r.config, r.strategy)].append(r)

    fields = [
        "config",
        "strategy",
        "runs",
        "corrected_weight",
        "uncorrectable_weight",
        "window_cycles",
        "busy_percent_mean",
        "busy_percent_std",
        "new_due_count_mean",
        "new_due_count_std",
        "repeated_due_detections_mean",
        "repeated_due_detections_std",
        "unique_uncorrectable_words_mean",
        "unique_uncorrectable_words_std",
        "uncorrectable_detections_mean",
        "uncorrectable_detections_std",
        "corrected_mean",
        "corrected_std",
        "interval_switches_mean",
    ]

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()

        for key in sorted(groups):
            rs = groups[key]
            first = rs[0]
            busy_m, busy_s = mean_std([r.busy_per_mille / 10.0 for r in rs])
            new_m, new_s = mean_std([r.new_due_count for r in rs])
            repeated_m, repeated_s = mean_std([r.repeated_due_detections for r in rs])
            unique_m, unique_s = mean_std([r.unique_uncorrectable_words for r in rs])
            ded_m, ded_s = mean_std([r.uncorrectable_detections for r in rs])
            corrected_m, corrected_s = mean_std([r.corrected for r in rs])
            switch_m, _ = mean_std([r.interval_switches for r in rs])

            w.writerow({
                "config": first.config,
                "strategy": first.strategy,
                "runs": len(rs),
                "corrected_weight": first.corrected_weight,
                "uncorrectable_weight": first.uncorrectable_weight,
                "window_cycles": first.window_cycles,
                "busy_percent_mean": f"{busy_m:.6f}",
                "busy_percent_std": f"{busy_s:.6f}",
                "new_due_count_mean": f"{new_m:.6f}",
                "new_due_count_std": f"{new_s:.6f}",
                "repeated_due_detections_mean": f"{repeated_m:.6f}",
                "repeated_due_detections_std": f"{repeated_s:.6f}",
                "unique_uncorrectable_words_mean": f"{unique_m:.6f}",
                "unique_uncorrectable_words_std": f"{unique_s:.6f}",
                "uncorrectable_detections_mean": f"{ded_m:.6f}",
                "uncorrectable_detections_std": f"{ded_s:.6f}",
                "corrected_mean": f"{corrected_m:.6f}",
                "corrected_std": f"{corrected_s:.6f}",
                "interval_switches_mean": f"{switch_m:.6f}",
            })


def write_deltas_csv(path: Path, rows: list[RunRow]) -> None:
    fields = [
        "config",
        "metric",
        "n",
        "delta_measured_minus_fixed_mean",
        "delta_std",
        "ci95_low",
        "ci95_high",
    ]

    metrics = [
        "busy_per_mille",
        "new_due_count",
        "repeated_due_detections",
        "unique_uncorrectable_words",
        "uncorrectable_detections",
        "corrected",
    ]

    by_key = {(r.config, r.seed, r.strategy): r for r in rows}
    configs_seen = sorted({r.config for r in rows})
    seeds_seen = sorted({r.seed for r in rows})

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()

        for config in configs_seen:
            for metric in metrics:
                deltas: list[float] = []
                for seed in seeds_seen:
                    measured = by_key[(config, seed, "measured")]
                    fixed = by_key[(config, seed, "fixed")]
                    deltas.append(float(getattr(measured, metric) - getattr(fixed, metric)))

                m, s, lo, hi = ci95(deltas)
                w.writerow({
                    "config": config,
                    "metric": metric,
                    "n": len(deltas),
                    "delta_measured_minus_fixed_mean": f"{m:.6f}",
                    "delta_std": f"{s:.6f}",
                    "ci95_low": f"{lo:.6f}",
                    "ci95_high": f"{hi:.6f}",
                })


def write_markdown(path: Path, rows: list[RunRow]) -> None:
    groups: dict[tuple[str, str], list[RunRow]] = defaultdict(list)
    for r in rows:
        groups[(r.config, r.strategy)].append(r)

    lines: list[str] = []
    lines.append("# Measured-control weight sweep")
    lines.append("")
    lines.append("Measured-control status: demonstration, not a net resource win.")
    lines.append("")
    lines.append("## Purpose")
    lines.append("")
    lines.append(
        "This report keeps measured-control in the proper scope: it is a closed-loop RTL "
        "feasibility and telemetry experiment. The sweep changes estimator input weights "
        "and evaluates the result with latched DUE metrics, but it does not claim that "
        "counter-threshold measured control is a new or generally superior scrub policy."
    )
    lines.append("")
    lines.append("## Aggregate metrics")
    lines.append("")
    lines.append("| config | strategy | runs | weights C/D | busy, % | new DUE | repeated DED | final unique DUE | DED detections | corrected | switches |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")

    for key in sorted(groups):
        rs = groups[key]
        first = rs[0]
        busy_m, busy_s = mean_std([r.busy_per_mille / 10.0 for r in rs])
        new_m, new_s = mean_std([r.new_due_count for r in rs])
        repeated_m, repeated_s = mean_std([r.repeated_due_detections for r in rs])
        unique_m, unique_s = mean_std([r.unique_uncorrectable_words for r in rs])
        ded_m, ded_s = mean_std([r.uncorrectable_detections for r in rs])
        corrected_m, corrected_s = mean_std([r.corrected for r in rs])
        switch_m, _ = mean_std([r.interval_switches for r in rs])

        lines.append(
            f"| `{first.config}` | `{first.strategy}` | {len(rs)} | "
            f"{first.corrected_weight}/{first.uncorrectable_weight} | "
            f"{busy_m:.3f} ± {busy_s:.3f} | "
            f"{new_m:.3f} ± {new_s:.3f} | "
            f"{repeated_m:.1f} ± {repeated_s:.1f} | "
            f"{unique_m:.3f} ± {unique_s:.3f} | "
            f"{ded_m:.1f} ± {ded_s:.1f} | "
            f"{corrected_m:.1f} ± {corrected_s:.1f} | "
            f"{switch_m:.1f} |"
        )

    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    lines.append(
        "The estimator still observes controller counters, including diagnostic DED "
        "detections. Therefore this sweep is not the primary risk result. The primary "
        "risk semantics are the latched metrics: `new_due_count` and final "
        "`unique_uncorrectable_words`. `new_due_count` is a runtime first-arrival "
        "metric, while final `unique_uncorrectable_words` is a post-run memory audit; "
        "the two can differ if later injections alter the final state."
    )
    lines.append("")
    lines.append(
        "A configuration should not be called a net win merely because it reacts more "
        "aggressively. The summary must be read together with busy percentage and the "
        "measured-minus-fixed deltas."
    )
    lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--output-dir", default="results/paper/measured_control/weight_sweep")
    p.add_argument("--addr-width", type=int, default=8)
    p.add_argument("--seed-start", type=int, default=1)
    p.add_argument("--seed-count", type=int, default=5)
    p.add_argument("--total-cycles", type=int, default=100000)
    p.add_argument("--window-size", type=int, default=43824)
    p.add_argument("--event-count", type=int, default=80)
    p.add_argument("--paired-event-count", type=int, default=20)
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

    all_rows: list[RunRow] = []
    seeds = list(range(args.seed_start, args.seed_start + args.seed_count))

    for cfg in configs():
        compiled_out = REPO_ROOT / f"results/logs/measured_weight_sweep_{cfg.name}.out"
        compile_tb(args, cfg, compiled_out)

        for seed in seeds:
            seed_dir = output_dir / cfg.name / f"seed_{seed:03d}"
            seed_dir.mkdir(parents=True, exist_ok=True)
            generate_fault_events(args, seed, seed_dir)

            for strategy_id in [0, 3]:
                run_dir = seed_dir / f"strategy_{strategy_id}"
                run_dir.mkdir(parents=True, exist_ok=True)
                row = run_strategy(args, cfg, compiled_out, seed, strategy_id, run_dir)
                all_rows.append(row)

    write_runs_csv(output_dir / "measured_weight_sweep_runs.csv", all_rows)
    write_summary_csv(output_dir / "measured_weight_sweep_summary.csv", all_rows)
    write_deltas_csv(output_dir / "measured_weight_sweep_deltas.csv", all_rows)
    write_markdown(output_dir / "measured_weight_sweep_summary.md", all_rows)

    print(f"rows: {len(all_rows)}")
    print(f"runs: {output_dir / 'measured_weight_sweep_runs.csv'}")
    print(f"summary: {output_dir / 'measured_weight_sweep_summary.csv'}")
    print(f"deltas: {output_dir / 'measured_weight_sweep_deltas.csv'}")
    print(f"markdown: {output_dir / 'measured_weight_sweep_summary.md'}")

    for cfg in configs():
        measured = [r for r in all_rows if r.config == cfg.name and r.strategy == "measured"]
        busy_m, busy_s = mean_std([r.busy_per_mille / 10.0 for r in measured])
        new_m, new_s = mean_std([r.new_due_count for r in measured])
        print(f"{cfg.name}: measured_busy_mean={busy_m:.6f} measured_busy_std={busy_s:.6f} new_due_mean={new_m:.6f} new_due_std={new_s:.6f}")


if __name__ == "__main__":
    main()

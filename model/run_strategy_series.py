#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import subprocess
from pathlib import Path


BASE_COLUMNS = [
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


SERIES_COLUMNS = [
    "scenario",
    "seed",
    "requested_total_cycles",
    "window_size",
    "event_count",
    "paired_event_count",
    "pair_gap_min",
    "pair_gap_max",
    "cluster_event_count",
    "cluster_bit_count",
    "control_quantization",
    "control_source",
    "control_policy_schedule",
    "control_policy_level_map_output",
    "control_delay_points",
    "safe_interval",
    "level_intervals",
    "threshold_levels",
    "threshold_intervals",
    *BASE_COLUMNS,
]


def read_single_run(input_path: Path) -> list[dict[str, str]]:
    if not input_path.exists():
        raise FileNotFoundError(f"Result file not found: {input_path}")

    with input_path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        rows = list(reader)

    if not rows:
        raise ValueError(f"No rows found in {input_path}")

    missing = [column for column in BASE_COLUMNS if column not in rows[0]]

    if missing:
        raise ValueError("Missing columns in single-run CSV: " + ", ".join(missing))

    return rows


def append_series_rows(
    output_path: Path,
    rows: list[dict[str, str]],
    scenario: str,
    seed: int,
    total_cycles: int,
    window_size: int,
    event_count: int,
    paired_event_count: int,
    pair_gap_min: int,
    pair_gap_max: int,
    cluster_event_count: int,
    cluster_bit_count: int,
    control_quantization: str,
    control_source: str,
    control_policy_schedule: str,
    control_policy_level_map_output: str,
    control_delay_points: int,
    safe_interval: int,
    level_intervals_text: str,
    threshold_levels_text: str,
    threshold_intervals_text: str,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    file_exists = output_path.exists()

    with output_path.open("a", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=SERIES_COLUMNS)

        if not file_exists:
            writer.writeheader()

        for row in rows:
            output_row: dict[str, str | int] = {
                "scenario": scenario,
                "seed": seed,
                "requested_total_cycles": total_cycles,
                "window_size": window_size,
                "event_count": event_count,
                "paired_event_count": paired_event_count,
                "pair_gap_min": pair_gap_min,
                "pair_gap_max": pair_gap_max,
                "cluster_event_count": cluster_event_count,
                "cluster_bit_count": cluster_bit_count,
                "control_quantization": control_quantization,
                "control_source": control_source,
                "control_policy_schedule": control_policy_schedule,
                "control_policy_level_map_output": control_policy_level_map_output,
                "control_delay_points": control_delay_points,
                "safe_interval": safe_interval,
                "level_intervals": level_intervals_text,
                "threshold_levels": threshold_levels_text,
                "threshold_intervals": threshold_intervals_text,
            }

            for column in BASE_COLUMNS:
                output_row[column] = row[column]

            writer.writerow(output_row)


def run_one_seed(
    seed: int,
    scenario: str,
    total_cycles: int,
    window_size: int,
    event_count: int,
    paired_event_count: int,
    pair_gap_min: int,
    pair_gap_max: int,
    cluster_event_count: int,
    cluster_bit_count: int,
    control_quantization: str,
    control_source: str,
    control_policy_schedule: str,
    control_policy_level_map_output: str,
    control_delay_points: int,
    safe_interval: int,
    level_intervals: list[int],
    threshold_levels: list[int],
    threshold_intervals: list[int],
    make_command: str,
) -> None:
    command = [
        make_command,
        "test_strategy_comparison",
        f"FAULT_SCENARIO={scenario}",
        f"FAULT_TOTAL_CYCLES={total_cycles}",
        f"FAULT_WINDOW_SIZE={window_size}",
        f"FAULT_EVENT_COUNT={event_count}",
        f"FAULT_PAIRED_EVENT_COUNT={paired_event_count}",
        f"FAULT_PAIR_GAP_MIN={pair_gap_min}",
        f"FAULT_PAIR_GAP_MAX={pair_gap_max}",
        f"FAULT_CLUSTER_EVENT_COUNT={cluster_event_count}",
        f"FAULT_CLUSTER_BIT_COUNT={cluster_bit_count}",
        f"FAULT_SEED={seed}",
        f"CONTROL_QUANTIZATION={control_quantization}",
        f"CONTROL_SOURCE={control_source}",
        f"CONTROL_POLICY_SCHEDULE={control_policy_schedule}",
        f"CONTROL_POLICY_LEVEL_MAP_OUTPUT={control_policy_level_map_output}",
        f"CONTROL_DELAY_POINTS={control_delay_points}",
        f"SAFE_INTERVAL={safe_interval}",
        f"LEVEL0_INTERVAL={level_intervals[0]}",
        f"LEVEL1_INTERVAL={level_intervals[1]}",
        f"LEVEL2_INTERVAL={level_intervals[2]}",
        f"LEVEL3_INTERVAL={level_intervals[3]}",
        f"LEVEL4_INTERVAL={level_intervals[4]}",
        f"LEVEL5_INTERVAL={level_intervals[5]}",
        f"LEVEL6_INTERVAL={level_intervals[6]}",
        f"LEVEL7_INTERVAL={level_intervals[7]}",
        f"THRESHOLD_LOW_TO_MEDIUM={threshold_levels[0]}",
        f"THRESHOLD_MEDIUM_TO_LOW={threshold_levels[1]}",
        f"THRESHOLD_MEDIUM_TO_HIGH={threshold_levels[2]}",
        f"THRESHOLD_HIGH_TO_MEDIUM={threshold_levels[3]}",
        f"THRESHOLD_LOW_INTERVAL={threshold_intervals[0]}",
        f"THRESHOLD_MEDIUM_INTERVAL={threshold_intervals[1]}",
        f"THRESHOLD_HIGH_INTERVAL={threshold_intervals[2]}",
    ]

    print("")
    print("=" * 80)
    print(f"Running seed {seed}")
    print(" ".join(command))
    print("=" * 80)

    subprocess.run(command, check=True)

def parse_int_list(text: str, expected_count: int, name: str) -> list[int]:
    values: list[int] = []

    for raw_part in text.replace(";", ",").split(","):
        part = raw_part.strip()

        if not part:
            continue

        value = int(part)

        if value <= 0:
            raise ValueError(f"{name} values must be positive: {value}")

        values.append(value)

    if len(values) != expected_count:
        raise ValueError(
            f"{name} must contain exactly {expected_count} values, got {len(values)}"
        )

    return values


def parse_level_thresholds(text: str) -> list[int]:
    values: list[int] = []

    for raw_part in text.replace(";", ",").split(","):
        part = raw_part.strip()

        if not part:
            continue

        value = int(part)

        if value < 0 or value > 7:
            raise ValueError(f"threshold level must be in 0..7: {value}")

        values.append(value)

    if len(values) != 4:
        raise ValueError(
            f"threshold-levels must contain exactly 4 values, got {len(values)}"
        )

    return values


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run strategy comparison for a series of random seeds."
    )

    parser.add_argument(
        "--scenario",
        default="upsets",
        choices=["baseline", "upsets"],
        help="Fault generation scenario.",
    )

    parser.add_argument(
        "--seed-start",
        type=int,
        default=1,
        help="First seed value.",
    )

    parser.add_argument(
        "--seed-count",
        type=int,
        default=10,
        help="Number of seed values to run.",
    )

    parser.add_argument(
        "--total-cycles",
        type=int,
        default=10000,
        help="Simulation length in model cycles.",
    )

    parser.add_argument(
        "--window-size",
        type=int,
        default=10000,
        help="Number of upsets time-series points used for generation.",
    )

    parser.add_argument(
        "--event-count",
        type=int,
        default=80,
        help="Number of single fault events.",
    )

    parser.add_argument(
        "--paired-event-count",
        type=int,
        default=20,
        help="Number of paired fault events.",
    )

    parser.add_argument(
        "--pair-gap-min",
        type=int,
        default=60,
        help="Minimum distance between two events in a pair.",
    )

    parser.add_argument(
        "--pair-gap-max",
        type=int,
        default=300,
        help="Maximum distance between two events in a pair.",
    )

    parser.add_argument(
        "--cluster-event-count",
        type=int,
        default=10,
        help="Number of instantaneous cluster events.",
    )

    parser.add_argument(
        "--cluster-bit-count",
        type=int,
        default=2,
        help="Number of flipped bits in each instantaneous cluster.",
    )

    parser.add_argument(
        "--control-quantization",
        default="linear_max",
        choices=["linear_max", "percentile_tail"],
        help="Control-level quantization mode passed to fault generator.",
    )

    parser.add_argument(
        "--control-source",
        default="quantization",
        choices=["quantization", "risk_policy"],
        help="Control source passed to fault generator.",
    )

    parser.add_argument(
        "--control-policy-schedule",
        default="results/paper/tables/risk_policy_schedule.csv",
        help="Risk policy schedule path passed to fault generator.",
    )

    parser.add_argument(
        "--control-policy-level-map-output",
        default="results/tables/control_policy_level_map.csv",
        help="Risk policy level-map output path passed to fault generator.",
    )

    parser.add_argument(
        "--control-delay-points",
        type=int,
        default=0,
        help=(
            "Delay of the control estimate in source time-series points. "
            "For the paper data, one point corresponds to one hour."
        ),
    )

    parser.add_argument(
        "--safe-interval",
        type=int,
        default=5,
        help="Safe interval passed to RTL testbench.",
    )

    parser.add_argument(
        "--level-intervals",
        default="100,80,60,40,25,15,10,5",
        help="Comma-separated LEVEL0..LEVEL7 model intervals.",
    )

    parser.add_argument(
        "--threshold-levels",
        default="3,1,6,4",
        help=(
            "Comma-separated threshold levels: "
            "low_to_medium,medium_to_low,medium_to_high,high_to_medium."
        ),
    )

    parser.add_argument(
        "--threshold-intervals",
        default="100,25,8",
        help="Comma-separated threshold low,medium,high model intervals.",
    )

    parser.add_argument(
        "--single-run-input",
        type=Path,
        default=Path("results/tables/strategy_comparison.csv"),
        help="CSV produced by one run of test_strategy_comparison.",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/tables/strategy_comparison_series.csv"),
        help="Output CSV for all runs.",
    )

    parser.add_argument(
        "--make-command",
        default="make",
        help="Make command to use.",
    )

    args = parser.parse_args()

    if args.seed_count <= 0:
        raise ValueError("seed-count must be positive")

    if args.total_cycles <= 0:
        raise ValueError("total-cycles must be positive")

    if args.window_size <= 0:
        raise ValueError("window-size must be positive")

    level_intervals = parse_int_list(
        args.level_intervals,
        expected_count=8,
        name="level-intervals",
    )

    threshold_levels = parse_level_thresholds(args.threshold_levels)

    threshold_intervals = parse_int_list(
        args.threshold_intervals,
        expected_count=3,
        name="threshold-intervals",
    )

    if args.safe_interval <= 0:
        raise ValueError("safe-interval must be positive")

    if args.output.exists():
        args.output.unlink()

    for offset in range(args.seed_count):
        seed = args.seed_start + offset

        run_one_seed(
            seed=seed,
            scenario=args.scenario,
            total_cycles=args.total_cycles,
            window_size=args.window_size,
            event_count=args.event_count,
            paired_event_count=args.paired_event_count,
            pair_gap_min=args.pair_gap_min,
            pair_gap_max=args.pair_gap_max,
            cluster_event_count=args.cluster_event_count,
            cluster_bit_count=args.cluster_bit_count,
            control_quantization=args.control_quantization,
            control_source=args.control_source,
            control_policy_schedule=args.control_policy_schedule,
            control_policy_level_map_output=args.control_policy_level_map_output,
            control_delay_points=args.control_delay_points,
            safe_interval=args.safe_interval,
            level_intervals=level_intervals,
            threshold_levels=threshold_levels,
            threshold_intervals=threshold_intervals,
            make_command=args.make_command,
        )

        rows = read_single_run(args.single_run_input)

        append_series_rows(
            output_path=args.output,
            rows=rows,
            scenario=args.scenario,
            seed=seed,
            total_cycles=args.total_cycles,
            window_size=args.window_size,
            event_count=args.event_count,
            paired_event_count=args.paired_event_count,
            pair_gap_min=args.pair_gap_min,
            pair_gap_max=args.pair_gap_max,
            cluster_event_count=args.cluster_event_count,
            cluster_bit_count=args.cluster_bit_count,
            control_quantization=args.control_quantization,
            control_source=args.control_source,
            control_policy_schedule=args.control_policy_schedule,
            control_policy_level_map_output=args.control_policy_level_map_output,
            control_delay_points=args.control_delay_points,
            safe_interval=args.safe_interval,
            level_intervals_text=args.level_intervals,
            threshold_levels_text=args.threshold_levels,
            threshold_intervals_text=args.threshold_intervals,
        )

    print("")
    print(f"Series complete: {args.output}")


if __name__ == "__main__":
    main()
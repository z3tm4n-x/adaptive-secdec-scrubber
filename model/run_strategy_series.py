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
    ]

    print("")
    print("=" * 80)
    print(f"Running seed {seed}")
    print(" ".join(command))
    print("=" * 80)

    subprocess.run(command, check=True)


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
        )

    print("")
    print(f"Series complete: {args.output}")


if __name__ == "__main__":
    main()
#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import math
import subprocess
from collections import defaultdict
from pathlib import Path
from statistics import mean, stdev


LEVEL_INTERVALS = [1866, 1788, 1710, 1633, 1555, 1400, 1244, 1089]
THRESHOLD_INTERVALS = [2021, 1555, 1244]


def run(command: list[str]) -> None:
    print("+", " ".join(command))
    subprocess.run(command, check=True)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def tcrit95(n: int) -> float:
    table = {
        1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571,
        6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228,
        11: 2.201, 12: 2.179, 13: 2.160, 14: 2.145, 15: 2.131,
        16: 2.120, 17: 2.110, 18: 2.101, 19: 2.093, 20: 2.086,
    }
    return table.get(n - 1, 1.960)


def mean_ci(values: list[float]) -> tuple[float, float, float, float]:
    n = len(values)
    m = mean(values)

    if n <= 1:
        return m, 0.0, m, m

    sd = stdev(values)
    se = sd / math.sqrt(n)
    t = tcrit95(n)
    return m, sd, m - t * se, m + t * se


def append_rows(
    *,
    output: Path,
    rows: list[dict[str, str]],
    seed: int,
    interleave_depth: int,
    fixed_interval: int,
    total_cycles: int,
    event_count: int,
    paired_event_count: int,
    cluster_event_count: int,
    cluster_bit_count: int,
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "seed",
        "interleave_depth",
        "fixed_interval",
        "requested_total_cycles",
        "event_count",
        "paired_event_count",
        "cluster_event_count",
        "cluster_bit_count",
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

    write_header = not output.exists()

    with output.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)

        if write_header:
            writer.writeheader()

        for row in rows:
            out = {
                "seed": seed,
                "interleave_depth": interleave_depth,
                "fixed_interval": fixed_interval,
                "requested_total_cycles": total_cycles,
                "event_count": event_count,
                "paired_event_count": paired_event_count,
                "cluster_event_count": cluster_event_count,
                "cluster_bit_count": cluster_bit_count,
            }
            out.update(row)
            writer.writerow(out)


def build_summary(csv_path: Path, md_output: Path, csv_output: Path) -> None:
    rows = read_csv(csv_path)

    fixed_rows = [
        row for row in rows
        if row["strategy"] == "fixed"
    ]

    grouped: dict[tuple[int, int], list[dict[str, str]]] = defaultdict(list)

    for row in fixed_rows:
        key = (int(row["interleave_depth"]), int(row["fixed_interval"]))
        grouped[key].append(row)

    summary_rows: list[dict[str, object]] = []

    for key in sorted(grouped):
        depth, interval = key
        items = grouped[key]

        metrics = {
            "busy_percent": [float(row["busy_per_mille"]) / 10.0 for row in items],
            "scrub_cycles": [float(row["scrub_cycles"]) for row in items],
            "corrected": [float(row["corrected"]) for row in items],
            "uncorrectable_detections": [float(row["uncorrectable_detections"]) for row in items],
            "unique_uncorrectable_words": [float(row["unique_uncorrectable_words"]) for row in items],
        }

        out = {
            "interleave_depth": depth,
            "fixed_interval": interval,
            "runs": len(items),
        }

        for metric, values in metrics.items():
            m, sd, lo, hi = mean_ci(values)
            out[f"{metric}_mean"] = m
            out[f"{metric}_std"] = sd
            out[f"{metric}_ci95_low"] = lo
            out[f"{metric}_ci95_high"] = hi

        summary_rows.append(out)

    csv_output.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "interleave_depth",
        "fixed_interval",
        "runs",
        "busy_percent_mean",
        "busy_percent_std",
        "busy_percent_ci95_low",
        "busy_percent_ci95_high",
        "scrub_cycles_mean",
        "scrub_cycles_std",
        "scrub_cycles_ci95_low",
        "scrub_cycles_ci95_high",
        "corrected_mean",
        "corrected_std",
        "corrected_ci95_low",
        "corrected_ci95_high",
        "uncorrectable_detections_mean",
        "uncorrectable_detections_std",
        "uncorrectable_detections_ci95_low",
        "uncorrectable_detections_ci95_high",
        "unique_uncorrectable_words_mean",
        "unique_uncorrectable_words_std",
        "unique_uncorrectable_words_ci95_low",
        "unique_uncorrectable_words_ci95_high",
    ]

    with csv_output.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for row in summary_rows:
            writer.writerow({name: row[name] for name in fieldnames})

    lines: list[str] = []

    lines.append("# Interleaving interval sweep")
    lines.append("")
    lines.append("## Назначение")
    lines.append("")
    lines.append(
        "Проверяется граница применимости циклического восстановления при "
        "мгновенных многобитовых кластерах. Для `cluster_bit_count=3` "
        "сравниваются режимы перемежения D=1, D=2 и D=3 при разных постоянных "
        "интервалах скраббинга."
    )
    lines.append("")
    lines.append(
        "D=1 оставляет все биты кластера в одном кодовом слове. "
        "D=2 раскладывает 3-битовый кластер как 2+1 по двум словам. "
        "D=3 раскладывает его как 1+1+1 по трём словам."
    )
    lines.append("")
    lines.append("## Fixed-strategy sweep")
    lines.append("")
    lines.append(
        "| D | fixed interval | runs | busy, % | scrub cycles | corrected | "
        "DED detections | unique uncorrectable words |"
    )
    lines.append("|---:|---:|---:|---:|---:|---:|---:|---:|")

    for row in summary_rows:
        lines.append(
            f"| {row['interleave_depth']} | "
            f"{row['fixed_interval']} | "
            f"{row['runs']} | "
            f"{row['busy_percent_mean']:.3f} ± {row['busy_percent_std']:.3f} | "
            f"{row['scrub_cycles_mean']:.1f} ± {row['scrub_cycles_std']:.1f} | "
            f"{row['corrected_mean']:.1f} ± {row['corrected_std']:.1f} | "
            f"{row['uncorrectable_detections_mean']:.1f} ± {row['uncorrectable_detections_std']:.1f} | "
            f"{row['unique_uncorrectable_words_mean']:.3f} ± {row['unique_uncorrectable_words_std']:.3f} |"
        )

    lines.append("")
    lines.append("## Интерпретация")
    lines.append("")
    lines.append(
        "Если при D=1 уменьшение интервала не устраняет `unique_uncorrectable_words`, "
        "это означает наличие мгновенной составляющей риска, не управляемой "
        "частотой скраббинга."
    )
    lines.append("")
    lines.append(
        "Если при D=3 риск-метрики становятся ниже и начинают сильнее зависеть "
        "от интервала, это означает возврат к накопительной модели: после "
        "достаточного перемежения метод циклического восстановления снова "
        "становится применимым."
    )

    md_output.parent.mkdir(parents=True, exist_ok=True)
    md_output.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(md_output.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument("--seed-start", type=int, default=1)
    parser.add_argument("--seed-count", type=int, default=10)
    parser.add_argument("--depths", default="1,2,3")
    parser.add_argument("--fixed-intervals", default="1089,1244,1555,2021,2400")
    parser.add_argument("--total-cycles", type=int, default=500000)
    parser.add_argument("--window-size", type=int, default=43824)
    parser.add_argument("--event-count", type=int, default=400)
    parser.add_argument("--paired-event-count", type=int, default=40)
    parser.add_argument("--pair-gap-min", type=int, default=600)
    parser.add_argument("--pair-gap-max", type=int, default=3000)
    parser.add_argument("--cluster-event-count", type=int, default=30)
    parser.add_argument("--cluster-bit-count", type=int, default=3)
    parser.add_argument("--addr-width", type=int, default=8)
    parser.add_argument("--base-dir", type=Path, default=Path("results/paper/interleaving/interval_sweep"))

    args = parser.parse_args()

    depths = [int(item) for item in args.depths.split(",")]
    intervals = [int(item) for item in args.fixed_intervals.split(",")]

    raw_csv = args.base_dir / "interleaving_interval_sweep.csv"
    summary_csv = args.base_dir / "interleaving_interval_sweep_summary.csv"
    summary_md = args.base_dir / "interleaving_interval_sweep_summary.md"

    args.base_dir.mkdir(parents=True, exist_ok=True)

    if raw_csv.exists():
        raw_csv.unlink()

    for depth in depths:
        for interval in intervals:
            for seed in range(args.seed_start, args.seed_start + args.seed_count):
                run_dir = args.base_dir / f"D{depth}" / f"interval_{interval}" / f"seed_{seed:04d}"
                run_dir.mkdir(parents=True, exist_ok=True)

                command = [
                    "make",
                    "test_strategy_comparison",
                    f"ADDR_WIDTH={args.addr_width}",
                    "DUMP_VCD=0",
                    "FAULT_SCENARIO=upsets",
                    f"FAULT_TOTAL_CYCLES={args.total_cycles}",
                    f"FAULT_WINDOW_SIZE={args.window_size}",
                    f"FAULT_EVENT_COUNT={args.event_count}",
                    f"FAULT_PAIRED_EVENT_COUNT={args.paired_event_count}",
                    f"FAULT_PAIR_GAP_MIN={args.pair_gap_min}",
                    f"FAULT_PAIR_GAP_MAX={args.pair_gap_max}",
                    f"FAULT_CLUSTER_EVENT_COUNT={args.cluster_event_count}",
                    f"FAULT_CLUSTER_BIT_COUNT={args.cluster_bit_count}",
                    f"FAULT_CLUSTER_INTERLEAVE_DEPTH={depth}",
                    f"FAULT_SEED={seed}",
                    "CONTROL_SOURCE=risk_policy",
                    "CONTROL_POLICY_SCHEDULE=results/paper/tables/risk_policy_schedule.csv",
                    f"FAULT_META_OUTPUT={run_dir / 'fault_events_meta.csv'}",
                    f"FAULT_SHIFT_SUMMARY_OUTPUT={run_dir / 'event_shift_summary.md'}",
                    f"CONTROL_POLICY_LEVEL_MAP_OUTPUT={run_dir / 'risk_policy_level_map.csv'}",
                    f"FIXED_INTERVAL={interval}",
                    f"SAFE_INTERVAL={interval}",
                    f"LEVEL0_INTERVAL={LEVEL_INTERVALS[0]}",
                    f"LEVEL1_INTERVAL={LEVEL_INTERVALS[1]}",
                    f"LEVEL2_INTERVAL={LEVEL_INTERVALS[2]}",
                    f"LEVEL3_INTERVAL={LEVEL_INTERVALS[3]}",
                    f"LEVEL4_INTERVAL={LEVEL_INTERVALS[4]}",
                    f"LEVEL5_INTERVAL={LEVEL_INTERVALS[5]}",
                    f"LEVEL6_INTERVAL={LEVEL_INTERVALS[6]}",
                    f"LEVEL7_INTERVAL={LEVEL_INTERVALS[7]}",
                    f"THRESHOLD_LOW_INTERVAL={THRESHOLD_INTERVALS[0]}",
                    f"THRESHOLD_MEDIUM_INTERVAL={THRESHOLD_INTERVALS[1]}",
                    f"THRESHOLD_HIGH_INTERVAL={THRESHOLD_INTERVALS[2]}",
                ]

                run(command)

                rows = read_csv(Path("results/tables/strategy_comparison.csv"))
                append_rows(
                    output=raw_csv,
                    rows=rows,
                    seed=seed,
                    interleave_depth=depth,
                    fixed_interval=interval,
                    total_cycles=args.total_cycles,
                    event_count=args.event_count,
                    paired_event_count=args.paired_event_count,
                    cluster_event_count=args.cluster_event_count,
                    cluster_bit_count=args.cluster_bit_count,
                )

    build_summary(raw_csv, summary_md, summary_csv)


if __name__ == "__main__":
    main()

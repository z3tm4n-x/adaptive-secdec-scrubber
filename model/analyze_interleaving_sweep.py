#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import math
from collections import defaultdict
from pathlib import Path
from statistics import mean, stdev


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(path)

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


def metric_value(row: dict[str, str], metric: str) -> float:
    if metric == "busy_percent":
        return float(row["busy_per_mille"]) / 10.0

    return float(row[metric])


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--input",
        type=Path,
        default=Path("results/paper/interleaving/interval_sweep/interleaving_interval_sweep.csv"),
    )
    parser.add_argument(
        "--csv-output",
        type=Path,
        default=Path("results/paper/interleaving/interval_sweep/interleaving_interval_sweep_deltas.csv"),
    )
    parser.add_argument(
        "--md-output",
        type=Path,
        default=Path("results/paper/interleaving/interval_sweep/interleaving_interval_sweep_deltas.md"),
    )

    args = parser.parse_args()

    rows = [
        row for row in read_csv(args.input)
        if row["strategy"] == "fixed"
    ]

    by_key: dict[tuple[int, int, int], dict[str, str]] = {}

    for row in rows:
        key = (
            int(row["seed"]),
            int(row["interleave_depth"]),
            int(row["fixed_interval"]),
        )
        by_key[key] = row

    seeds = sorted({int(row["seed"]) for row in rows})
    depths = sorted({int(row["interleave_depth"]) for row in rows})
    intervals = sorted({int(row["fixed_interval"]) for row in rows})

    metrics = [
        ("unique_uncorrectable_words", "unique uncorrectable words"),
        ("uncorrectable_detections", "DED detections"),
        ("corrected", "corrected"),
        ("busy_percent", "busy, %"),
    ]

    out_rows: list[dict[str, object]] = []

    def add_comparison(
        *,
        comparison: str,
        lhs_depth: int,
        lhs_interval: int,
        rhs_depth: int,
        rhs_interval: int,
    ) -> None:
        for metric, label in metrics:
            values = []

            for seed in seeds:
                lhs = by_key[(seed, lhs_depth, lhs_interval)]
                rhs = by_key[(seed, rhs_depth, rhs_interval)]

                values.append(metric_value(lhs, metric) - metric_value(rhs, metric))

            m, sd, lo, hi = mean_ci(values)

            out_rows.append(
                {
                    "comparison": comparison,
                    "lhs_depth": lhs_depth,
                    "lhs_interval": lhs_interval,
                    "rhs_depth": rhs_depth,
                    "rhs_interval": rhs_interval,
                    "metric": metric,
                    "label": label,
                    "n": len(values),
                    "delta_mean": m,
                    "delta_std": sd,
                    "ci95_low": lo,
                    "ci95_high": hi,
                }
            )

    # D3 vs D1 and D2 at the same interval.
    for interval in intervals:
        add_comparison(
            comparison=f"D3 - D1 at interval {interval}",
            lhs_depth=3,
            lhs_interval=interval,
            rhs_depth=1,
            rhs_interval=interval,
        )
        add_comparison(
            comparison=f"D3 - D2 at interval {interval}",
            lhs_depth=3,
            lhs_interval=interval,
            rhs_depth=2,
            rhs_interval=interval,
        )

    # Interval sensitivity inside each D: slowest - fastest.
    fastest = min(intervals)
    slowest = max(intervals)

    for depth in depths:
        add_comparison(
            comparison=f"D{depth} slowest - fastest",
            lhs_depth=depth,
            lhs_interval=slowest,
            rhs_depth=depth,
            rhs_interval=fastest,
        )

    args.csv_output.parent.mkdir(parents=True, exist_ok=True)

    with args.csv_output.open("w", encoding="utf-8", newline="") as f:
        fieldnames = [
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
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for row in out_rows:
            writer.writerow({name: row[name] for name in fieldnames})

    def get(comparison: str, metric: str) -> dict[str, object]:
        for row in out_rows:
            if row["comparison"] == comparison and row["metric"] == metric:
                return row
        raise KeyError((comparison, metric))

    lines: list[str] = []

    lines.append("# Paired analysis для interleaving interval sweep")
    lines.append("")
    lines.append("## Назначение")
    lines.append("")
    lines.append(
        "Дельты считаются попарно по одному и тому же seed. Это отделяет влияние "
        "перемежения и интервала скраббинга от случайности потока событий."
    )
    lines.append("")

    lines.append("## D3 относительно D1 при одинаковом interval")
    lines.append("")
    lines.append("| interval | Δ unique | Δ DED detections | Δ corrected |")
    lines.append("|---:|---:|---:|---:|")

    for interval in intervals:
        comparison = f"D3 - D1 at interval {interval}"
        unique = get(comparison, "unique_uncorrectable_words")
        ded = get(comparison, "uncorrectable_detections")
        corrected = get(comparison, "corrected")

        lines.append(
            f"| {interval} | "
            f"{unique['delta_mean']:.3f} [{unique['ci95_low']:.3f}; {unique['ci95_high']:.3f}] | "
            f"{ded['delta_mean']:.1f} [{ded['ci95_low']:.1f}; {ded['ci95_high']:.1f}] | "
            f"{corrected['delta_mean']:.1f} [{corrected['ci95_low']:.1f}; {corrected['ci95_high']:.1f}] |"
        )

    lines.append("")
    lines.append("## D3 относительно D2 при одинаковом interval")
    lines.append("")
    lines.append("| interval | Δ unique | Δ DED detections | Δ corrected |")
    lines.append("|---:|---:|---:|---:|")

    for interval in intervals:
        comparison = f"D3 - D2 at interval {interval}"
        unique = get(comparison, "unique_uncorrectable_words")
        ded = get(comparison, "uncorrectable_detections")
        corrected = get(comparison, "corrected")

        lines.append(
            f"| {interval} | "
            f"{unique['delta_mean']:.3f} [{unique['ci95_low']:.3f}; {unique['ci95_high']:.3f}] | "
            f"{ded['delta_mean']:.1f} [{ded['ci95_low']:.1f}; {ded['ci95_high']:.1f}] | "
            f"{corrected['delta_mean']:.1f} [{corrected['ci95_low']:.1f}; {corrected['ci95_high']:.1f}] |"
        )

    lines.append("")
    lines.append("## Чувствительность к interval внутри каждого D")
    lines.append("")
    lines.append(
        "Положительная Δ unique в строке `slowest - fastest` означает, что при "
        "увеличении интервала число уникальных неустранимых слов растёт."
    )
    lines.append("")
    lines.append("| D | Δ unique, slowest-fastest | Δ DED detections | Δ corrected |")
    lines.append("|---:|---:|---:|---:|")

    for depth in depths:
        comparison = f"D{depth} slowest - fastest"
        unique = get(comparison, "unique_uncorrectable_words")
        ded = get(comparison, "uncorrectable_detections")
        corrected = get(comparison, "corrected")

        lines.append(
            f"| {depth} | "
            f"{unique['delta_mean']:.3f} [{unique['ci95_low']:.3f}; {unique['ci95_high']:.3f}] | "
            f"{ded['delta_mean']:.1f} [{ded['ci95_low']:.1f}; {ded['ci95_high']:.1f}] | "
            f"{corrected['delta_mean']:.1f} [{corrected['ci95_low']:.1f}; {corrected['ci95_high']:.1f}] |"
        )

    lines.append("")
    lines.append("## Интерпретация")
    lines.append("")
    lines.append(
        "D=3 должен давать отрицательную Δ unique относительно D=1/D=2: это "
        "означает, что достаточное перемежение устраняет мгновенную DED-составляющую "
        "трёхбитового кластера."
    )
    lines.append("")
    lines.append(
        "Одновременно положительная чувствительность `slowest - fastest` показывает, "
        "что после перемежения остаточный риск снова зависит от интервала "
        "циклического восстановления."
    )

    args.md_output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(args.md_output.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()

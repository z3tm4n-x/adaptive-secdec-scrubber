#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import math
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, stdev


METRICS = [
    "scrub_cycles",
    "reads",
    "writes",
    "corrected",
    "uncorrectable_detections",
    "unique_uncorrectable_words",
    "memory_busy_cycles",
    "busy_percent",
]

METRIC_LABELS = {
    "scrub_cycles": "scrub cycles",
    "reads": "reads",
    "writes": "writes",
    "corrected": "corrected",
    "uncorrectable_detections": "uncorrectable detections",
    "unique_uncorrectable_words": "unique uncorrectable words",
    "memory_busy_cycles": "memory busy cycles",
    "busy_percent": "busy, %",
}


@dataclass(frozen=True)
class RunRow:
    scenario: str
    seed: int
    strategy: str
    scrub_cycles: float
    reads: float
    writes: float
    corrected: float
    uncorrectable_detections: float
    unique_uncorrectable_words: float
    memory_busy_cycles: float
    busy_percent: float


@dataclass(frozen=True)
class DeltaSummary:
    scenario: str
    comparison: str
    metric: str
    n: int
    fixed_mean: float
    adaptive_mean: float
    delta_mean: float
    delta_std: float
    delta_se: float
    ci95_low: float
    ci95_high: float
    relative_percent: float


def read_float(row: dict[str, str], key: str) -> float:
    value = row.get(key, "")
    if value == "":
        raise ValueError(f"Missing value for column {key}")
    return float(value)


def read_rows(path: Path, scenario_name: str) -> list[RunRow]:
    if not path.exists():
        raise FileNotFoundError(path)

    rows: list[RunRow] = []

    with path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)

        required = {
            "seed",
            "strategy",
            "scrub_cycles",
            "reads",
            "writes",
            "corrected",
            "uncorrectable_detections",
            "unique_uncorrectable_words",
            "memory_busy_cycles",
            "busy_per_mille",
        }

        if reader.fieldnames is None:
            raise ValueError(f"Missing CSV header in {path}")

        missing = required - set(reader.fieldnames)
        if missing:
            raise ValueError(
                f"Missing required columns in {path}: {', '.join(sorted(missing))}"
            )

        for row in reader:
            rows.append(
                RunRow(
                    scenario=scenario_name,
                    seed=int(row["seed"]),
                    strategy=row["strategy"].strip(),
                    scrub_cycles=read_float(row, "scrub_cycles"),
                    reads=read_float(row, "reads"),
                    writes=read_float(row, "writes"),
                    corrected=read_float(row, "corrected"),
                    uncorrectable_detections=read_float(row, "uncorrectable_detections"),
                    unique_uncorrectable_words=read_float(row, "unique_uncorrectable_words"),
                    memory_busy_cycles=read_float(row, "memory_busy_cycles"),
                    busy_percent=read_float(row, "busy_per_mille") / 10.0,
                )
            )

    return rows


def t_critical_95(n: int) -> float:
    if n <= 1:
        return float("nan")

    df = n - 1

    table = {
        1: 12.706,
        2: 4.303,
        3: 3.182,
        4: 2.776,
        5: 2.571,
        6: 2.447,
        7: 2.365,
        8: 2.306,
        9: 2.262,
        10: 2.228,
        11: 2.201,
        12: 2.179,
        13: 2.160,
        14: 2.145,
        15: 2.131,
        16: 2.120,
        17: 2.110,
        18: 2.101,
        19: 2.093,
        20: 2.086,
        21: 2.080,
        22: 2.074,
        23: 2.069,
        24: 2.064,
        25: 2.060,
        26: 2.056,
        27: 2.052,
        28: 2.048,
        29: 2.045,
        30: 2.042,
    }

    if df in table:
        return table[df]
    if df <= 40:
        return 2.021
    if df <= 60:
        return 2.000
    return 1.960


def index_rows(rows: list[RunRow]) -> dict[tuple[int, str], RunRow]:
    result: dict[tuple[int, str], RunRow] = {}

    for row in rows:
        key = (row.seed, row.strategy)
        if key in result:
            raise ValueError(f"Duplicate row: seed={row.seed}, strategy={row.strategy}")
        result[key] = row

    return result


def metric_value(row: RunRow, metric: str) -> float:
    return float(getattr(row, metric))


def summarize(
    scenario: str,
    comparison: str,
    metric: str,
    fixed_values: list[float],
    adaptive_values: list[float],
) -> DeltaSummary:
    if len(fixed_values) != len(adaptive_values):
        raise ValueError("Fixed/adaptive value lists have different length")
    if not fixed_values:
        raise ValueError("No paired values")

    deltas = [
        adaptive - fixed
        for fixed, adaptive in zip(fixed_values, adaptive_values)
    ]

    n = len(deltas)
    delta_mean = mean(deltas)

    if n > 1:
        delta_std = stdev(deltas)
        delta_se = delta_std / math.sqrt(n)
        tcrit = t_critical_95(n)
        ci95_low = delta_mean - tcrit * delta_se
        ci95_high = delta_mean + tcrit * delta_se
    else:
        delta_std = 0.0
        delta_se = 0.0
        ci95_low = delta_mean
        ci95_high = delta_mean

    fixed_mean = mean(fixed_values)
    adaptive_mean = mean(adaptive_values)

    if abs(fixed_mean) > 1e-12:
        relative_percent = 100.0 * delta_mean / fixed_mean
    else:
        relative_percent = float("nan")

    return DeltaSummary(
        scenario=scenario,
        comparison=comparison,
        metric=metric,
        n=n,
        fixed_mean=fixed_mean,
        adaptive_mean=adaptive_mean,
        delta_mean=delta_mean,
        delta_std=delta_std,
        delta_se=delta_se,
        ci95_low=ci95_low,
        ci95_high=ci95_high,
        relative_percent=relative_percent,
    )


def analyze_scenario(rows: list[RunRow]) -> list[DeltaSummary]:
    if not rows:
        raise ValueError("Empty scenario rows")

    scenario = rows[0].scenario
    indexed = index_rows(rows)
    seeds = sorted({row.seed for row in rows})

    summaries: list[DeltaSummary] = []

    for adaptive_strategy in ["table", "threshold"]:
        comparison = f"{adaptive_strategy}-fixed"

        fixed_rows: list[RunRow] = []
        adaptive_rows: list[RunRow] = []

        for seed in seeds:
            fixed_key = (seed, "fixed")
            adaptive_key = (seed, adaptive_strategy)

            if fixed_key not in indexed:
                raise ValueError(f"Missing fixed row for scenario={scenario}, seed={seed}")
            if adaptive_key not in indexed:
                raise ValueError(
                    f"Missing {adaptive_strategy} row for scenario={scenario}, seed={seed}"
                )

            fixed_rows.append(indexed[fixed_key])
            adaptive_rows.append(indexed[adaptive_key])

        for metric in METRICS:
            fixed_values = [metric_value(row, metric) for row in fixed_rows]
            adaptive_values = [metric_value(row, metric) for row in adaptive_rows]

            summaries.append(
                summarize(
                    scenario=scenario,
                    comparison=comparison,
                    metric=metric,
                    fixed_values=fixed_values,
                    adaptive_values=adaptive_values,
                )
            )

    return summaries


def write_csv(path: Path, summaries: list[DeltaSummary]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "scenario",
        "comparison",
        "metric",
        "n",
        "fixed_mean",
        "adaptive_mean",
        "delta_mean",
        "delta_std",
        "delta_se",
        "ci95_low",
        "ci95_high",
        "relative_percent",
    ]

    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()

        for item in summaries:
            writer.writerow(
                {
                    "scenario": item.scenario,
                    "comparison": item.comparison,
                    "metric": item.metric,
                    "n": item.n,
                    "fixed_mean": f"{item.fixed_mean:.6f}",
                    "adaptive_mean": f"{item.adaptive_mean:.6f}",
                    "delta_mean": f"{item.delta_mean:.6f}",
                    "delta_std": f"{item.delta_std:.6f}",
                    "delta_se": f"{item.delta_se:.6f}",
                    "ci95_low": f"{item.ci95_low:.6f}",
                    "ci95_high": f"{item.ci95_high:.6f}",
                    "relative_percent": f"{item.relative_percent:.6f}",
                }
            )


def write_markdown(path: Path, summaries: list[DeltaSummary]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []

    lines.append("# Paired delta analysis для финальных серий")
    lines.append("")
    lines.append("## Назначение")
    lines.append("")
    lines.append(
        "Для каждого seed сравниваются adaptive-стратегии с fixed-стратегией "
        "на одном и том же потоке инжектированных событий. Дельта считается как "
        "`adaptive - fixed`."
    )
    lines.append("")
    lines.append(
        "Отрицательная дельта по `busy_percent` означает снижение занятости памяти. "
        "Положительная дельта по `unique_uncorrectable_words` означает увеличение "
        "числа уникальных слов, перешедших в неустранимое состояние."
    )
    lines.append("")

    scenario_order = ["no_clusters", "with_clusters"]
    comparison_order = ["table-fixed", "threshold-fixed"]

    for scenario in scenario_order:
        scenario_rows = [
            item for item in summaries
            if item.scenario == scenario
        ]

        if not scenario_rows:
            continue

        lines.append(f"## Сценарий `{scenario}`")
        lines.append("")

        for comparison in comparison_order:
            comparison_rows = [
                item for item in scenario_rows
                if item.comparison == comparison
            ]

            if not comparison_rows:
                continue

            lines.append(f"### `{comparison}`")
            lines.append("")
            lines.append("| metric | fixed mean | adaptive mean | Δ mean | Δ 95% CI | relative Δ |")
            lines.append("|---|---:|---:|---:|---:|---:|")

            for item in comparison_rows:
                label = METRIC_LABELS.get(item.metric, item.metric)
                lines.append(
                    f"| {label} "
                    f"| {item.fixed_mean:.3f} "
                    f"| {item.adaptive_mean:.3f} "
                    f"| {item.delta_mean:.3f} "
                    f"| [{item.ci95_low:.3f}; {item.ci95_high:.3f}] "
                    f"| {item.relative_percent:.2f} % |"
                )

            lines.append("")

    lines.append("## Интерпретация для статьи")
    lines.append("")
    lines.append(
        "Основной вывод следует делать по `busy_percent` и "
        "`unique_uncorrectable_words`. `uncorrectable_detections` является "
        "вспомогательной телеметрической метрикой, поскольку зависит от частоты "
        "повторного обхода уже повреждённых слов."
    )
    lines.append("")
    lines.append(
        "Если доверительный интервал по `unique_uncorrectable_words` включает "
        "ноль или близкие к нулю значения, корректная формулировка — "
        "«сопоставимое число уникальных неустранимых слов». Если интервал "
        "строго положителен, следует писать «снижение занятости достигается "
        "ценой умеренного увеличения числа уникальных неустранимых слов»."
    )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Paired fixed-vs-adaptive delta analysis for paper strategy series."
    )

    parser.add_argument("--no-clusters", type=Path, required=True)
    parser.add_argument("--with-clusters", type=Path, required=True)
    parser.add_argument("--csv-output", type=Path, required=True)
    parser.add_argument("--md-output", type=Path, required=True)

    args = parser.parse_args()

    no_clusters_rows = read_rows(args.no_clusters, "no_clusters")
    with_clusters_rows = read_rows(args.with_clusters, "with_clusters")

    summaries: list[DeltaSummary] = []
    summaries.extend(analyze_scenario(no_clusters_rows))
    summaries.extend(analyze_scenario(with_clusters_rows))

    write_csv(args.csv_output, summaries)
    write_markdown(args.md_output, summaries)

    print(f"Paired delta CSV: {args.csv_output}")
    print(f"Paired delta report: {args.md_output}")


if __name__ == "__main__":
    main()

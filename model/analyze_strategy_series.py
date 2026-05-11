#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import math
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, stdev


REQUIRED_COLUMNS = [
    "scenario",
    "seed",
    "requested_total_cycles",
    "window_size",
    "event_count",
    "paired_event_count",
    "pair_gap_min",
    "pair_gap_max",
    "strategy",
    "corrected",
    "uncorrectable_detections",
    "unique_uncorrectable_words",
    "interval_switches",
    "reads",
    "writes",
    "memory_busy_cycles",
    "busy_per_mille",
]


ANALYZED_METRICS = [
    "corrected",
    "uncorrectable_detections",
    "unique_uncorrectable_words",
    "reads",
    "writes",
    "interval_switches",
    "memory_busy_cycles",
    "busy_percent",
]


STRATEGY_ORDER = ["fixed", "table", "threshold"]


@dataclass
class MetricStats:
    average: float
    minimum: float
    maximum: float
    stddev: float


def read_rows(input_path: Path) -> list[dict[str, str]]:
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    with input_path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        rows = list(reader)

    if not rows:
        raise ValueError(f"No rows found in {input_path}")

    missing = [column for column in REQUIRED_COLUMNS if column not in rows[0]]

    if missing:
        raise ValueError("Missing required columns: " + ", ".join(missing))

    return rows


def to_float(row: dict[str, str], key: str) -> float:
    return float(row[key].strip())


def metric_value(row: dict[str, str], metric: str) -> float:
    if metric == "busy_percent":
        return to_float(row, "busy_per_mille") / 10.0

    return to_float(row, metric)


def compute_stats(values: list[float]) -> MetricStats:
    if not values:
        raise ValueError("Cannot compute statistics for empty value list")

    if len(values) == 1:
        stddev = 0.0
    else:
        stddev = stdev(values)

    return MetricStats(
        average=mean(values),
        minimum=min(values),
        maximum=max(values),
        stddev=stddev,
    )


def group_rows_by_strategy(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)

    for row in rows:
        grouped[row["strategy"].strip()].append(row)

    return dict(grouped)


def ordered_strategy_names(grouped: dict[str, list[dict[str, str]]]) -> list[str]:
    names: list[str] = []

    for name in STRATEGY_ORDER:
        if name in grouped:
            names.append(name)

    for name in sorted(grouped):
        if name not in names:
            names.append(name)

    return names


def compute_summary(
    rows: list[dict[str, str]],
) -> dict[str, dict[str, MetricStats]]:
    grouped = group_rows_by_strategy(rows)

    summary: dict[str, dict[str, MetricStats]] = {}

    for strategy, strategy_rows in grouped.items():
        summary[strategy] = {}

        for metric in ANALYZED_METRICS:
            values = [metric_value(row, metric) for row in strategy_rows]
            summary[strategy][metric] = compute_stats(values)

    return summary


def unique_values(rows: list[dict[str, str]], key: str) -> list[str]:
    values = sorted({row[key].strip() for row in rows})
    return values


def format_float(value: float) -> str:
    if math.isclose(value, round(value), abs_tol=1e-9):
        return f"{value:.0f}"

    return f"{value:.3f}"


def write_summary_csv(
    rows: list[dict[str, str]],
    summary: dict[str, dict[str, MetricStats]],
    output_path: Path,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    grouped = group_rows_by_strategy(rows)
    strategy_names = ordered_strategy_names(grouped)

    fieldnames = [
        "strategy",
        "run_count",
    ]

    for metric in ANALYZED_METRICS:
        fieldnames.extend(
            [
                f"{metric}_mean",
                f"{metric}_min",
                f"{metric}_max",
                f"{metric}_stddev",
            ]
        )

    with output_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()

        for strategy in strategy_names:
            output_row: dict[str, str | int] = {
                "strategy": strategy,
                "run_count": len(grouped[strategy]),
            }

            for metric in ANALYZED_METRICS:
                stats = summary[strategy][metric]

                output_row[f"{metric}_mean"] = f"{stats.average:.6f}"
                output_row[f"{metric}_min"] = f"{stats.minimum:.6f}"
                output_row[f"{metric}_max"] = f"{stats.maximum:.6f}"
                output_row[f"{metric}_stddev"] = f"{stats.stddev:.6f}"

            writer.writerow(output_row)


def relative_change(value: float, reference: float) -> float:
    if math.isclose(reference, 0.0, abs_tol=1e-12):
        return 0.0

    return 100.0 * (value - reference) / reference


def write_summary_markdown(
    rows: list[dict[str, str]],
    summary: dict[str, dict[str, MetricStats]],
    output_path: Path,
    input_path: Path,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    grouped = group_rows_by_strategy(rows)
    strategy_names = ordered_strategy_names(grouped)

    scenario_values = unique_values(rows, "scenario")
    total_cycle_values = unique_values(rows, "requested_total_cycles")
    window_size_values = unique_values(rows, "window_size")
    event_count_values = unique_values(rows, "event_count")
    paired_event_count_values = unique_values(rows, "paired_event_count")
    pair_gap_min_values = unique_values(rows, "pair_gap_min")
    pair_gap_max_values = unique_values(rows, "pair_gap_max")

    lines: list[str] = []

    lines.append("# Сводка серии сравнительных прогонов")
    lines.append("")
    lines.append(f"Источник данных: `{input_path}`")
    lines.append("")
    lines.append("## Параметры серии")
    lines.append("")
    lines.append(f"- Сценарий: {', '.join(scenario_values)}")
    lines.append(f"- Длительность моделирования: {', '.join(total_cycle_values)} тактов")
    lines.append(f"- Размер окна временного ряда: {', '.join(window_size_values)}")
    lines.append(f"- Число одиночных событий: {', '.join(event_count_values)}")
    lines.append(f"- Число парных событий: {', '.join(paired_event_count_values)}")
    lines.append(f"- Минимальный разрыв в паре: {', '.join(pair_gap_min_values)}")
    lines.append(f"- Максимальный разрыв в паре: {', '.join(pair_gap_max_values)}")
    lines.append(f"- Число зёрен генератора: {len(unique_values(rows, 'seed'))}")
    lines.append("")

    lines.append("## Основные метрики по стратегиям")
    lines.append("")
    lines.append(
        "| Стратегия | Прогонов | "
        "Исправлено, среднее ± σ | "
        "Уникальные неустранимые слова, среднее ± σ | "
        "Обнаружения неустранимых, среднее ± σ | "
        "Занятость памяти, среднее ± σ, % | "
        "Чтения, среднее | Записи, среднее | Переключения интервала, среднее |"
    )
    lines.append(
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|"
    )

    for strategy in strategy_names:
        corrected = summary[strategy]["corrected"]
        unique_uncorrectable = summary[strategy]["unique_uncorrectable_words"]
        uncorrectable_detections = summary[strategy]["uncorrectable_detections"]
        busy_percent = summary[strategy]["busy_percent"]
        reads = summary[strategy]["reads"]
        writes = summary[strategy]["writes"]
        interval_switches = summary[strategy]["interval_switches"]

        lines.append(
            f"| `{strategy}` "
            f"| {len(grouped[strategy])} "
            f"| {corrected.average:.3f} ± {corrected.stddev:.3f} "
            f"| {unique_uncorrectable.average:.3f} ± {unique_uncorrectable.stddev:.3f} "
            f"| {uncorrectable_detections.average:.3f} ± {uncorrectable_detections.stddev:.3f} "
            f"| {busy_percent.average:.3f} ± {busy_percent.stddev:.3f} "
            f"| {reads.average:.3f} "
            f"| {writes.average:.3f} "
            f"| {interval_switches.average:.3f} |"
        )

    lines.append("")

    if "fixed" in summary:
        fixed_unique = summary["fixed"]["unique_uncorrectable_words"].average
        fixed_busy = summary["fixed"]["busy_percent"].average
        fixed_corrected = summary["fixed"]["corrected"].average

        lines.append("## Сравнение с постоянным интервалом")
        lines.append("")
        lines.append(
            "| Стратегия | Изменение исправленных ошибок | "
            "Изменение уникальных неустранимых слов | "
            "Изменение занятости памяти |"
        )
        lines.append("|---|---:|---:|---:|")

        for strategy in strategy_names:
            if strategy == "fixed":
                continue

            corrected = summary[strategy]["corrected"].average
            unique_uncorrectable = summary[strategy]["unique_uncorrectable_words"].average
            busy_percent = summary[strategy]["busy_percent"].average

            corrected_delta = corrected - fixed_corrected
            unique_delta = unique_uncorrectable - fixed_unique
            busy_delta = busy_percent - fixed_busy
            busy_relative = relative_change(busy_percent, fixed_busy)

            lines.append(
                f"| `{strategy}` "
                f"| {corrected_delta:+.3f} "
                f"| {unique_delta:+.3f} "
                f"| {busy_delta:+.3f} п.п. ({busy_relative:+.2f} %) |"
            )

        lines.append("")
        lines.append("## Предварительная интерпретация")
        lines.append("")

        best_unique_value = min(
            summary[strategy]["unique_uncorrectable_words"].average
            for strategy in strategy_names
        )

        best_unique_strategies = [
            strategy for strategy in strategy_names
            if math.isclose(
                summary[strategy]["unique_uncorrectable_words"].average,
                best_unique_value,
                abs_tol=1e-9,
            )
        ]

        best_by_busy = min(
            best_unique_strategies,
            key=lambda strategy: summary[strategy]["busy_percent"].average,
        )

        lines.append(
            f"Минимальное среднее число уникальных неустранимых слов равно "
            f"{best_unique_value:.3f}. Среди стратегий с этим значением "
            f"наименьшую среднюю занятость памяти имеет `{best_by_busy}` "
            f"({summary[best_by_busy]['busy_percent'].average:.3f} %)."
        )
        lines.append("")

        lines.append(
            "Эта сводка является статистическим обобщением серии прогонов "
            "по нескольким зёрнам генератора. Поэтому она существенно надёжнее "
            "одиночного демонстрационного запуска."
        )

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze multi-seed strategy comparison series."
    )

    parser.add_argument(
        "--input",
        type=Path,
        default=Path("results/tables/strategy_comparison_series.csv"),
        help="Input CSV with all series runs.",
    )

    parser.add_argument(
        "--csv-output",
        type=Path,
        default=Path("results/tables/strategy_series_summary.csv"),
        help="Output CSV summary.",
    )

    parser.add_argument(
        "--md-output",
        type=Path,
        default=Path("results/tables/strategy_series_summary.md"),
        help="Output Markdown summary.",
    )

    args = parser.parse_args()

    rows = read_rows(args.input)
    summary = compute_summary(rows)

    write_summary_csv(rows, summary, args.csv_output)
    write_summary_markdown(rows, summary, args.md_output, args.input)

    print(f"Analyzed series rows: {len(rows)}")
    print(f"CSV summary: {args.csv_output}")
    print(f"Markdown summary: {args.md_output}")


if __name__ == "__main__":
    main()
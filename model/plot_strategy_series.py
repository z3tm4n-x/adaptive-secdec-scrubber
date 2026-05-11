#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib.pyplot as plt


REQUIRED_COLUMNS = [
    "strategy",
    "run_count",
    "corrected_mean",
    "corrected_stddev",
    "unique_uncorrectable_words_mean",
    "unique_uncorrectable_words_stddev",
    "busy_percent_mean",
    "busy_percent_stddev",
]


STRATEGY_ORDER = ["fixed", "table", "threshold"]

STRATEGY_LABELS = {
    "fixed": "Постоянный\nинтервал",
    "table": "Табличная\nстратегия",
    "threshold": "Трёхрежимная\nстратегия",
}


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


def ordered_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    by_name = {row["strategy"].strip(): row for row in rows}
    result: list[dict[str, str]] = []

    for strategy in STRATEGY_ORDER:
        if strategy in by_name:
            result.append(by_name[strategy])

    for strategy in sorted(by_name):
        if strategy not in STRATEGY_ORDER:
            result.append(by_name[strategy])

    return result


def to_float(row: dict[str, str], key: str) -> float:
    return float(row[key].strip())


def labels_for(rows: list[dict[str, str]]) -> list[str]:
    labels: list[str] = []

    for row in rows:
        strategy = row["strategy"].strip()
        labels.append(STRATEGY_LABELS.get(strategy, strategy))

    return labels


def add_value_labels(values: list[float], suffix: str = "") -> None:
    for index, value in enumerate(values):
        plt.text(
            index,
            value,
            f"{value:.2f}{suffix}",
            ha="center",
            va="bottom",
        )


def plot_bar_with_error(
    rows: list[dict[str, str]],
    mean_column: str,
    stddev_column: str,
    ylabel: str,
    title: str,
    output_path: Path,
    suffix: str = "",
) -> None:
    labels = labels_for(rows)
    means = [to_float(row, mean_column) for row in rows]
    stddevs = [to_float(row, stddev_column) for row in rows]

    plt.figure(figsize=(7.2, 4.8))
    plt.bar(labels, means, yerr=stddevs, capsize=6)

    add_value_labels(means, suffix)

    ymax = max((mean + std for mean, std in zip(means, stddevs)), default=1.0)
    if ymax <= 0:
        ymax = 1.0

    plt.ylabel(ylabel)
    plt.title(title)
    plt.ylim(0, ymax * 1.25)
    plt.tight_layout()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=300)
    plt.close()


def plot_tradeoff(rows: list[dict[str, str]], output_path: Path) -> None:
    busy = [to_float(row, "busy_percent_mean") for row in rows]
    unique = [to_float(row, "unique_uncorrectable_words_mean") for row in rows]
    labels = [row["strategy"].strip() for row in rows]

    plt.figure(figsize=(7.2, 4.8))
    plt.scatter(busy, unique)

    for x_value, y_value, label in zip(busy, unique, labels):
        plt.text(
            x_value,
            y_value,
            f" {label}",
            ha="left",
            va="center",
        )

    plt.xlabel("Средняя занятость интерфейса памяти, %")
    plt.ylabel("Среднее число уникальных неустранимых слов")
    plt.title("Компромисс между занятостью памяти и числом неустранимых слов")
    plt.grid(True)
    plt.tight_layout()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=300)
    plt.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Plot multi-seed strategy comparison summary."
    )

    parser.add_argument(
        "--input",
        type=Path,
        default=Path("results/tables/strategy_series_summary.csv"),
        help="Input CSV summary.",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results/figures"),
        help="Output directory for figures.",
    )

    args = parser.parse_args()

    rows = ordered_rows(read_rows(args.input))
    args.output_dir.mkdir(parents=True, exist_ok=True)

    plot_bar_with_error(
        rows=rows,
        mean_column="busy_percent_mean",
        stddev_column="busy_percent_stddev",
        ylabel="Занятость интерфейса памяти, %",
        title="Средняя занятость интерфейса памяти по серии прогонов",
        output_path=args.output_dir / "strategy_series_busy_percent.png",
        suffix=" %",
    )

    plot_bar_with_error(
        rows=rows,
        mean_column="unique_uncorrectable_words_mean",
        stddev_column="unique_uncorrectable_words_stddev",
        ylabel="Число слов",
        title="Среднее число уникальных слов с неустранимыми ошибками",
        output_path=args.output_dir / "strategy_series_unique_uncorrectable.png",
    )

    plot_bar_with_error(
        rows=rows,
        mean_column="corrected_mean",
        stddev_column="corrected_stddev",
        ylabel="Число исправленных ошибок",
        title="Среднее число исправленных ошибок по серии прогонов",
        output_path=args.output_dir / "strategy_series_corrected_errors.png",
    )

    plot_tradeoff(
        rows=rows,
        output_path=args.output_dir / "strategy_series_tradeoff.png",
    )

    print(f"Series figures written to: {args.output_dir}")


if __name__ == "__main__":
    main()
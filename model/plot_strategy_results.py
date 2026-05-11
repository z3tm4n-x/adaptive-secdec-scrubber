#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib.pyplot as plt


REQUIRED_COLUMNS = [
    "strategy",
    "corrected",
    "unique_uncorrectable_words",
    "busy_per_mille",
]


STRATEGY_LABELS = {
    "fixed": "Постоянный\nинтервал",
    "table": "Табличная\nстратегия",
    "threshold": "Трёхрежимная\nстратегия",
}


def read_results(input_path: Path) -> list[dict[str, str]]:
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    with input_path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        rows = list(reader)

    if not rows:
        raise ValueError(f"No rows found in {input_path}")

    missing_columns = [
        column for column in REQUIRED_COLUMNS
        if column not in rows[0]
    ]

    if missing_columns:
        raise ValueError(
            "Missing required columns: " + ", ".join(missing_columns)
        )

    return rows


def strategy_labels(rows: list[dict[str, str]]) -> list[str]:
    labels: list[str] = []

    for row in rows:
        strategy = row["strategy"].strip()
        labels.append(STRATEGY_LABELS.get(strategy, strategy))

    return labels


def to_int(row: dict[str, str], key: str) -> int:
    return int(row[key].strip())


def busy_percent(row: dict[str, str]) -> float:
    return to_int(row, "busy_per_mille") / 10.0


def add_value_labels_int(values: list[int]) -> None:
    for index, value in enumerate(values):
        plt.text(
            index,
            value,
            str(value),
            ha="center",
            va="bottom",
        )


def add_value_labels_float(values: list[float], suffix: str = "") -> None:
    for index, value in enumerate(values):
        plt.text(
            index,
            value,
            f"{value:.1f}{suffix}",
            ha="center",
            va="bottom",
        )


def plot_busy_percent(rows: list[dict[str, str]], output_path: Path) -> None:
    labels = strategy_labels(rows)
    values = [busy_percent(row) for row in rows]

    plt.figure(figsize=(7.0, 4.5))
    plt.bar(labels, values)

    add_value_labels_float(values, " %")

    plt.ylabel("Занятость интерфейса памяти, %")
    plt.title("Занятость интерфейса памяти при разных стратегиях")
    plt.ylim(0, max(values) * 1.25 if values else 1)
    plt.tight_layout()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=300)
    plt.close()


def plot_unique_uncorrectable(rows: list[dict[str, str]], output_path: Path) -> None:
    labels = strategy_labels(rows)
    values = [to_int(row, "unique_uncorrectable_words") for row in rows]

    plt.figure(figsize=(7.0, 4.5))
    plt.bar(labels, values)

    add_value_labels_int(values)

    plt.ylabel("Число слов")
    plt.title("Уникальные слова с неустранимыми ошибками")
    plt.ylim(0, max(values) * 1.35 if max(values) > 0 else 1)
    plt.tight_layout()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=300)
    plt.close()


def plot_corrected_errors(rows: list[dict[str, str]], output_path: Path) -> None:
    labels = strategy_labels(rows)
    values = [to_int(row, "corrected") for row in rows]

    plt.figure(figsize=(7.0, 4.5))
    plt.bar(labels, values)

    add_value_labels_int(values)

    plt.ylabel("Число исправленных ошибок")
    plt.title("Исправленные одиночные ошибки")
    plt.ylim(0, max(values) * 1.25 if values else 1)
    plt.tight_layout()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=300)
    plt.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Plot strategy comparison results."
    )

    parser.add_argument(
        "--input",
        type=Path,
        default=Path("results/tables/strategy_comparison.csv"),
        help="Input CSV file.",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results/figures"),
        help="Output directory for figures.",
    )

    args = parser.parse_args()

    rows = read_results(args.input)

    args.output_dir.mkdir(parents=True, exist_ok=True)

    busy_path = args.output_dir / "strategy_busy_percent.png"
    unique_path = args.output_dir / "strategy_unique_uncorrectable.png"
    corrected_path = args.output_dir / "strategy_corrected_errors.png"

    plot_busy_percent(rows, busy_path)
    plot_unique_uncorrectable(rows, unique_path)
    plot_corrected_errors(rows, corrected_path)

    print(f"Figures written to: {args.output_dir}")
    print(f"  {busy_path}")
    print(f"  {unique_path}")
    print(f"  {corrected_path}")


if __name__ == "__main__":
    main()
#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from statistics import mean, pstdev

import matplotlib.pyplot as plt

from generate_fault_events import (
    read_upsets_xlsx,
    select_window,
    quantize_upset_value,
)


def compute_levels(values: list[float]) -> list[int]:
    max_value = max(values) if values else 0.0
    return [quantize_upset_value(value, max_value) for value in values]


def level_counts(levels: list[int]) -> list[int]:
    counts = [0 for _ in range(8)]

    for level in levels:
        if level < 0 or level > 7:
            raise ValueError(f"Control level out of range: {level}")

        counts[level] += 1

    return counts


def quantization_boundaries(max_value: float) -> list[float]:
    """
    Границы между уровнями для правила:
        level = round(7 * value / max_value)

    Для непрерывных значений граница между level=k и level=k+1
    примерно соответствует (k + 0.5) / 7 от максимума окна.
    """
    if max_value <= 0.0:
        return []

    return [((level + 0.5) / 7.0) * max_value for level in range(7)]


def write_thresholds_csv(output_path: Path, max_value: float) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    boundaries = quantization_boundaries(max_value)

    with output_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["boundary", "lower_level", "upper_level", "upsets_value"])

        for lower_level, value in enumerate(boundaries):
            writer.writerow(
                [
                    f"level_{lower_level}_to_{lower_level + 1}",
                    lower_level,
                    lower_level + 1,
                    f"{value:.12g}",
                ]
            )


def write_plot_summary(
    output_path: Path,
    input_path: Path,
    start_index: int,
    window_size: int,
    total_cycles: int,
    values: list[float],
    counts: list[int],
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    window_mean = mean(values)
    window_std = pstdev(values)
    window_cv2 = (window_std / window_mean) ** 2 if window_mean > 0.0 else 0.0
    eta_theory = 1.0 + window_cv2
    max_value = max(values)

    lines: list[str] = []

    lines.append("# Диагностика квантования ν(t) → ctrl_level")
    lines.append("")
    lines.append(f"Источник: `{input_path}`")
    lines.append("")
    lines.append("## Параметры")
    lines.append("")
    lines.append(f"- Начальный индекс: {start_index}")
    lines.append(f"- Размер окна: {window_size}")
    lines.append(f"- Модельных тактов: {total_cycles}")
    lines.append(f"- Максимум окна: {max_value:.9g}")
    lines.append(f"- Среднее окна: {window_mean:.9g}")
    lines.append(f"- CV² окна: {window_cv2:.9g}")
    lines.append(f"- η_theory = 1 + CV²: {eta_theory:.9g}")
    lines.append("")
    lines.append("## Распределение уровней")
    lines.append("")
    lines.append("| Уровень | Число точек | Доля |")
    lines.append("|---:|---:|---:|")

    total = len(values)

    for level, count in enumerate(counts):
        fraction = count / total if total else 0.0
        lines.append(f"| {level} | {count} | {fraction:.6f} |")

    lines.append("")
    lines.append("## Пояснение")
    lines.append("")
    lines.append(
        "Границы уровней построены для текущей линейной нормировки по максимуму окна. "
        "Если распределение ν(t) имеет тяжёлый хвост, высокий максимум сдвигает "
        "пороги вверх, и большая часть фоновых значений попадает в уровень 0."
    )

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def plot_level_distribution(
    counts: list[int],
    output_path: Path,
) -> None:
    total = sum(counts)

    if total <= 0:
        raise ValueError("Cannot plot empty level distribution")

    levels = list(range(8))
    fractions = [count / total for count in counts]

    plt.figure(figsize=(7.2, 4.8))
    plt.bar(levels, fractions)

    ymax = max(fractions) if fractions else 1.0
    if ymax <= 0.0:
        ymax = 1.0

    for level, fraction in zip(levels, fractions):
        plt.text(
            level,
            fraction,
            f"{fraction:.3f}",
            ha="center",
            va="bottom",
        )

    plt.xlabel("Управляющий уровень")
    plt.ylabel("Доля точек окна")
    plt.title("Распределение управляющих уровней после квантования ν(t)")
    plt.xticks(levels)
    plt.ylim(0.0, ymax * 1.25)
    plt.tight_layout()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=300)
    plt.close()


def plot_upsets_histogram(
    values: list[float],
    output_path: Path,
    bins: int,
    log_y: bool,
) -> None:
    if not values:
        raise ValueError("Cannot plot empty upsets window")

    max_value = max(values)
    boundaries = quantization_boundaries(max_value)

    plt.figure(figsize=(8.4, 5.2))
    plt.hist(values, bins=bins)

    y_min, y_max = plt.ylim()

    for index, boundary in enumerate(boundaries):
        plt.axvline(boundary, linestyle="--", linewidth=1)
        plt.text(
            boundary,
            y_max,
            f"L{index}/L{index + 1}",
            rotation=90,
            va="top",
            ha="right",
        )

    if log_y:
        plt.yscale("log")

    plt.xlabel("ν(t)")
    plt.ylabel("Число точек окна")
    plt.title("Распределение ν(t) и границы линейного квантования")
    plt.tight_layout()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=300)
    plt.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Plot diagnostics for upsets-to-control-level quantization."
    )

    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/upsets.xlsx"),
        help="Input Excel file with upsets time series.",
    )

    parser.add_argument(
        "--start-index",
        type=int,
        default=0,
        help="Start index in the time series.",
    )

    parser.add_argument(
        "--window-size",
        type=int,
        required=True,
        help="Number of points in the selected window.",
    )

    parser.add_argument(
        "--total-cycles",
        type=int,
        required=True,
        help="Number of model cycles used for this window.",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results/paper/figures"),
        help="Output directory for figures.",
    )

    parser.add_argument(
        "--bins",
        type=int,
        default=120,
        help="Number of bins for the upsets histogram.",
    )

    parser.add_argument(
        "--linear-y",
        action="store_true",
        help="Use linear Y scale for the histogram. Default is logarithmic Y.",
    )

    args = parser.parse_args()

    all_values = read_upsets_xlsx(args.input)
    window = select_window(all_values, args.start_index, args.window_size)

    levels = compute_levels(window)
    counts = level_counts(levels)

    args.output_dir.mkdir(parents=True, exist_ok=True)

    level_distribution_png = args.output_dir / "control_level_distribution.png"
    histogram_png = args.output_dir / "upsets_window_histogram.png"
    thresholds_csv = args.output_dir.parent / "tables" / "control_level_thresholds.csv"
    summary_md = args.output_dir.parent / "tables" / "control_quantization_summary.md"

    plot_level_distribution(
        counts=counts,
        output_path=level_distribution_png,
    )

    plot_upsets_histogram(
        values=window,
        output_path=histogram_png,
        bins=args.bins,
        log_y=not args.linear_y,
    )

    write_thresholds_csv(
        output_path=thresholds_csv,
        max_value=max(window),
    )

    write_plot_summary(
        output_path=summary_md,
        input_path=args.input,
        start_index=args.start_index,
        window_size=args.window_size,
        total_cycles=args.total_cycles,
        values=window,
        counts=counts,
    )

    print(f"Control level distribution figure: {level_distribution_png}")
    print(f"Upsets histogram figure: {histogram_png}")
    print(f"Thresholds CSV: {thresholds_csv}")
    print(f"Quantization summary: {summary_md}")


if __name__ == "__main__":
    main()
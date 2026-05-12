#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path
from statistics import mean, pstdev

import matplotlib.pyplot as plt

from generate_fault_events import (
    read_upsets_xlsx,
    select_window,
)

from control_quantization import (
    add_quantization_arguments,
    build_quantization_config,
    count_level_changes,
    level_counts,
    parse_percentile_boundaries,
    quantize_value,
    write_thresholds_csv,
)


def compute_levels(values: list[float], mode: str, percentiles: tuple[float, ...]):
    config = build_quantization_config(
        values=values,
        mode=mode,
        percentile_boundaries=percentiles,
    )

    levels = [quantize_value(value, config) for value in values]

    return levels, config


def write_plot_summary(
    output_path: Path,
    input_path: Path,
    start_index: int,
    window_size: int,
    total_cycles: int,
    values: list[float],
    counts: list[int],
    control_level_changes: int,
    control_quantization: str,
    thresholds: tuple[float, ...],
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
    lines.append(f"- Режим квантования: `{control_quantization}`")
    lines.append(f"- Максимум окна: {max_value:.9g}")
    lines.append(f"- Среднее окна: {window_mean:.9g}")
    lines.append(f"- CV² окна: {window_cv2:.9g}")
    lines.append(f"- η_theory = 1 + CV²: {eta_theory:.9g}")
    lines.append(f"- Число изменений уровня: {control_level_changes}")
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
    lines.append("## Пороги уровней")
    lines.append("")
    lines.append("| Граница | Значение ν(t) |")
    lines.append("|---|---:|")

    for index, threshold in enumerate(thresholds):
        lines.append(f"| level {index} → {index + 1} | {threshold:.9g} |")

    lines.append("")
    lines.append("## Пояснение")
    lines.append("")
    lines.append(
        "Режим `linear_max` использует прежние пороги, пропорциональные максимуму окна. "
        "Режим `percentile_tail` задаёт пороги по перцентилям окна и лучше "
        "использует управляющие уровни при тяжёлом хвосте распределения ν(t)."
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
    thresholds: tuple[float, ...],
) -> None:
    if not values:
        raise ValueError("Cannot plot empty upsets window")

    plt.figure(figsize=(8.4, 5.2))
    plt.hist(values, bins=bins)

    y_min, y_max = plt.ylim()

    for index, threshold in enumerate(thresholds):
        plt.axvline(threshold, linestyle="--", linewidth=1)
        plt.text(
            threshold,
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
    plt.title("Распределение ν(t) и границы квантования")
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

    add_quantization_arguments(parser)

    args = parser.parse_args()

    all_values = read_upsets_xlsx(args.input)
    window = select_window(all_values, args.start_index, args.window_size)

    levels, config = compute_levels(
        values=window,
        mode=args.control_quantization,
        percentiles=parse_percentile_boundaries(args.control_percentiles),
    )

    counts = level_counts(levels)
    changes = count_level_changes(levels)

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
        thresholds=config.boundaries,
    )

    write_thresholds_csv(
        output_path=thresholds_csv,
        config=config,
    )

    write_plot_summary(
        output_path=summary_md,
        input_path=args.input,
        start_index=args.start_index,
        window_size=args.window_size,
        total_cycles=args.total_cycles,
        values=window,
        counts=counts,
        control_level_changes=changes,
        control_quantization=args.control_quantization,
        thresholds=config.boundaries,
    )

    print(f"Control level distribution figure: {level_distribution_png}")
    print(f"Upsets histogram figure: {histogram_png}")
    print(f"Thresholds CSV: {thresholds_csv}")
    print(f"Quantization summary: {summary_md}")


if __name__ == "__main__":
    main()
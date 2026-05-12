#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path
from statistics import mean, pstdev

from generate_fault_events import (
    read_upsets_xlsx,
    select_window,
    quantize_upset_value,
)


def write_summary_csv(
    output_path: Path,
    rows: list[tuple[str, str]],
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["metric", "value"])
        writer.writerows(rows)


def write_level_distribution_csv(
    output_path: Path,
    level_counts: list[int],
    total_samples: int,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["level", "sample_count", "fraction"])

        for level, count in enumerate(level_counts):
            fraction = count / total_samples if total_samples else 0.0
            writer.writerow([level, count, f"{fraction:.9f}"])


def write_markdown(
    output_path: Path,
    input_path: Path,
    start_index: int,
    window_size: int,
    total_cycles: int,
    values: list[float],
    level_counts: list[int],
    control_level_changes: int,
    event_count: int,
    paired_event_count: int,
    cluster_event_count: int,
    codeword_count: int,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    window_mean = mean(values)
    window_std = pstdev(values)
    window_cv2 = (window_std / window_mean) ** 2 if window_mean > 0.0 else 0.0
    eta_theory = 1.0 + window_cv2
    window_sum = sum(values)
    window_min = min(values)
    window_max = max(values)

    injected_fault_rows_no_clusters = event_count + 2 * paired_event_count
    injected_fault_rows_with_clusters = (
        event_count + 2 * paired_event_count + cluster_event_count
    )

    hours_per_cycle = window_size / total_cycles if total_cycles > 0 else 0.0
    cycles_per_hour = total_cycles / window_size if window_size > 0 else 0.0

    lines: list[str] = []

    lines.append("# Статистика публикационного окна ν(t)")
    lines.append("")
    lines.append(f"Источник: `{input_path}`")
    lines.append("")
    lines.append("## Параметры окна")
    lines.append("")
    lines.append(f"- Начальный индекс: {start_index}")
    lines.append(f"- Размер окна: {window_size}")
    lines.append(f"- Модельных тактов: {total_cycles}")
    lines.append(f"- Часов ряда на один модельный такт: {hours_per_cycle:.6f}")
    lines.append(f"- Модельных тактов на один час ряда: {cycles_per_hour:.6f}")
    lines.append("")
    lines.append("## Статистика ν(t)")
    lines.append("")
    lines.append(f"- Минимум: {window_min:.9g}")
    lines.append(f"- Максимум: {window_max:.9g}")
    lines.append(f"- Среднее: {window_mean:.9g}")
    lines.append(f"- Стандартное отклонение: {window_std:.9g}")
    lines.append(f"- CV²: {window_cv2:.9g}")
    lines.append(f"- η_theory = 1 + CV²: {eta_theory:.9g}")
    lines.append(f"- Сумма значений окна: {window_sum:.9g}")
    lines.append("")
    lines.append("## Параметры инжекции")
    lines.append("")
    lines.append(f"- Одиночных событий: {event_count}")
    lines.append(f"- Накопительных пар: {paired_event_count}")
    lines.append(f"- Мгновенных кластерных событий: {cluster_event_count}")
    lines.append(f"- Строк инжекции без кластеров: {injected_fault_rows_no_clusters}")
    lines.append(f"- Строк инжекции с кластерами: {injected_fault_rows_with_clusters}")
    lines.append(f"- Число кодовых слов в имитационной памяти: {codeword_count}")
    lines.append(
        f"- Плотность строк инжекции без кластеров на кодовое слово: "
        f"{injected_fault_rows_no_clusters / codeword_count:.6f}"
    )
    lines.append(
        f"- Плотность строк инжекции с кластерами на кодовое слово: "
        f"{injected_fault_rows_with_clusters / codeword_count:.6f}"
    )
    lines.append("")
    lines.append("## Распределение управляющих уровней")
    lines.append("")
    lines.append("| Уровень | Число точек | Доля |")
    lines.append("|---:|---:|---:|")

    total_samples = len(values)

    for level, count in enumerate(level_counts):
        fraction = count / total_samples if total_samples else 0.0
        lines.append(f"| {level} | {count} | {fraction:.6f} |")

    lines.append("")
    lines.append(f"Число изменений управляющего уровня: {control_level_changes}")
    lines.append("")
    lines.append("## Методическое пояснение")
    lines.append("")
    lines.append(
        "Модельная шкала времени является нормированной событийной шкалой "
        "RTL-симуляции. Временной ряд ν(t), заданный с часовым шагом, "
        "масштабируется на заданное число модельных тактов. Поэтому один "
        "модельный такт не следует интерпретировать как физический такт "
        "аппаратного контроллера."
    )
    lines.append("")
    lines.append(
        "Квантование управляющего уровня выполняется линейной нормировкой "
        "по максимуму выбранного окна. При сильно асимметричном распределении "
        "ν(t) это может приводить к высокой доле уровня 0 и слабому "
        "использованию старших уровней управления."
    )

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze selected upsets time-series window."
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
        "--event-count",
        type=int,
        required=True,
        help="Number of single fault events.",
    )

    parser.add_argument(
        "--paired-event-count",
        type=int,
        required=True,
        help="Number of paired events.",
    )

    parser.add_argument(
        "--cluster-event-count",
        type=int,
        required=True,
        help="Number of instantaneous cluster events.",
    )

    parser.add_argument(
        "--codeword-count",
        type=int,
        default=16,
        help="Number of codewords in the simulated memory.",
    )

    parser.add_argument(
        "--summary-csv",
        type=Path,
        default=Path("results/paper/tables/upsets_window_summary.csv"),
        help="Output summary CSV.",
    )

    parser.add_argument(
        "--level-csv",
        type=Path,
        default=Path("results/paper/tables/control_level_distribution.csv"),
        help="Output level distribution CSV.",
    )

    parser.add_argument(
        "--md-output",
        type=Path,
        default=Path("results/paper/tables/upsets_window_summary.md"),
        help="Output Markdown summary.",
    )

    args = parser.parse_args()

    all_values = read_upsets_xlsx(args.input)
    window = select_window(all_values, args.start_index, args.window_size)

    window_mean = mean(window)
    window_std = pstdev(window)
    window_cv2 = (window_std / window_mean) ** 2 if window_mean > 0.0 else 0.0
    eta_theory = 1.0 + window_cv2

    max_value = max(window) if window else 0.0

    levels = [quantize_upset_value(value, max_value) for value in window]

    level_counts = [0 for _ in range(8)]

    for level in levels:
        level_counts[level] += 1

    control_level_changes = 0
    previous_level: int | None = None

    for level in levels:
        if previous_level is None or level != previous_level:
            control_level_changes += 1
            previous_level = level

    hours_per_cycle = args.window_size / args.total_cycles
    cycles_per_hour = args.total_cycles / args.window_size

    rows = [
        ("input", str(args.input)),
        ("usable_series_length", str(len(all_values))),
        ("start_index", str(args.start_index)),
        ("window_size", str(args.window_size)),
        ("total_cycles", str(args.total_cycles)),
        ("hours_per_cycle", f"{hours_per_cycle:.9f}"),
        ("cycles_per_hour", f"{cycles_per_hour:.9f}"),
        ("window_min", f"{min(window):.12g}"),
        ("window_max", f"{max(window):.12g}"),
        ("window_mean", f"{window_mean:.12g}"),
        ("window_std", f"{window_std:.12g}"),
        ("window_cv2", f"{window_cv2:.12g}"),
        ("eta_theory_1_plus_cv2", f"{eta_theory:.12g}"),
        ("window_sum", f"{sum(window):.12g}"),
        ("control_level_changes", str(control_level_changes)),
        ("event_count", str(args.event_count)),
        ("paired_event_count", str(args.paired_event_count)),
        ("cluster_event_count", str(args.cluster_event_count)),
        ("codeword_count", str(args.codeword_count)),
        (
            "injected_rows_no_clusters",
            str(args.event_count + 2 * args.paired_event_count),
        ),
        (
            "injected_rows_with_clusters",
            str(args.event_count + 2 * args.paired_event_count + args.cluster_event_count),
        ),
    ]

    write_summary_csv(args.summary_csv, rows)
    write_level_distribution_csv(args.level_csv, level_counts, len(window))
    write_markdown(
        output_path=args.md_output,
        input_path=args.input,
        start_index=args.start_index,
        window_size=args.window_size,
        total_cycles=args.total_cycles,
        values=window,
        level_counts=level_counts,
        control_level_changes=control_level_changes,
        event_count=args.event_count,
        paired_event_count=args.paired_event_count,
        cluster_event_count=args.cluster_event_count,
        codeword_count=args.codeword_count,
    )

    print(f"Usable series length: {len(all_values)}")
    print(f"Window size: {args.window_size}")
    print(f"Window mean: {window_mean:.9g}")
    print(f"Window CV^2: {window_cv2:.9g}")
    print(f"Eta theory 1+CV^2: {eta_theory:.9g}")
    print(f"Control level changes: {control_level_changes}")
    print(f"Summary CSV: {args.summary_csv}")
    print(f"Level CSV: {args.level_csv}")
    print(f"Markdown summary: {args.md_output}")


if __name__ == "__main__":
    main()
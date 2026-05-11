#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
from pathlib import Path


REQUIRED_COLUMNS = [
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


def to_int(row: dict[str, str], key: str) -> int:
    return int(row[key].strip())


def to_float_percent_from_per_mille(row: dict[str, str], key: str) -> float:
    return to_int(row, key) / 10.0


def find_strategy(rows: list[dict[str, str]], name: str) -> dict[str, str]:
    for row in rows:
        if row["strategy"].strip() == name:
            return row

    raise ValueError(f"Strategy not found: {name}")


def percent_change(value: float, reference: float) -> float:
    if reference == 0.0:
        return 0.0

    return 100.0 * (value - reference) / reference


def signed_int_delta(value: int, reference: int) -> str:
    delta = value - reference

    if delta > 0:
        return f"+{delta}"

    return str(delta)


def signed_percent(value: float) -> str:
    if value > 0.0:
        return f"+{value:.1f} %"

    return f"{value:.1f} %"


def format_summary_table(rows: list[dict[str, str]]) -> list[str]:
    fixed = find_strategy(rows, "fixed")

    fixed_busy = to_float_percent_from_per_mille(fixed, "busy_per_mille")
    fixed_unique_uncorrectable = to_int(fixed, "unique_uncorrectable_words")
    fixed_corrected = to_int(fixed, "corrected")
    fixed_reads = to_int(fixed, "reads")

    lines: list[str] = []

    lines.append(
        "| Стратегия | Циклы скраббинга | Чтения | Записи | "
        "Исправлено | Обнаружения неустранимых | "
        "Уникальные неустранимые слова | Переключения интервала | "
        "Занятость памяти | Изменение занятости к fixed | "
        "Изменение уникальных неустранимых | Изменение исправленных |"
    )

    lines.append(
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    )

    for row in rows:
        strategy = row["strategy"].strip()

        scrub_cycles = to_int(row, "scrub_cycles")
        reads = to_int(row, "reads")
        writes = to_int(row, "writes")
        corrected = to_int(row, "corrected")
        uncorrectable_detections = to_int(row, "uncorrectable_detections")
        unique_uncorrectable = to_int(row, "unique_uncorrectable_words")
        interval_switches = to_int(row, "interval_switches")
        busy_percent = to_float_percent_from_per_mille(row, "busy_per_mille")

        busy_change = percent_change(busy_percent, fixed_busy)
        unique_delta = signed_int_delta(
            unique_uncorrectable,
            fixed_unique_uncorrectable,
        )
        corrected_delta = signed_int_delta(corrected, fixed_corrected)

        lines.append(
            f"| {strategy} "
            f"| {scrub_cycles} "
            f"| {reads} "
            f"| {writes} "
            f"| {corrected} "
            f"| {uncorrectable_detections} "
            f"| {unique_uncorrectable} "
            f"| {interval_switches} "
            f"| {busy_percent:.1f} % "
            f"| {signed_percent(busy_change)} "
            f"| {unique_delta} "
            f"| {corrected_delta} |"
        )

    lines.append("")

    lines.append(
        f"Базовая стратегия `fixed` принята за точку сравнения: "
        f"занятость памяти {fixed_busy:.1f} %, "
        f"число чтений {fixed_reads}, "
        f"число исправленных ошибок {fixed_corrected}, "
        f"число уникальных неустранимых слов {fixed_unique_uncorrectable}."
    )

    return lines


def make_conclusions(rows: list[dict[str, str]]) -> list[str]:
    fixed = find_strategy(rows, "fixed")

    fixed_busy = to_float_percent_from_per_mille(fixed, "busy_per_mille")
    fixed_unique = to_int(fixed, "unique_uncorrectable_words")
    fixed_corrected = to_int(fixed, "corrected")

    lines: list[str] = []
    lines.append("## Автоматически сформированный вывод")
    lines.append("")

    for row in rows:
        strategy = row["strategy"].strip()

        if strategy == "fixed":
            continue

        busy = to_float_percent_from_per_mille(row, "busy_per_mille")
        unique = to_int(row, "unique_uncorrectable_words")
        corrected = to_int(row, "corrected")

        busy_delta = busy - fixed_busy
        unique_delta = unique - fixed_unique
        corrected_delta = corrected - fixed_corrected

        lines.append(f"### Стратегия `{strategy}`")
        lines.append("")

        if unique_delta < 0:
            lines.append(
                f"- Число уникальных неустранимых слов уменьшилось "
                f"с {fixed_unique} до {unique}."
            )
        elif unique_delta == 0:
            lines.append(
                f"- Число уникальных неустранимых слов не изменилось "
                f"и равно {unique}."
            )
        else:
            lines.append(
                f"- Число уникальных неустранимых слов увеличилось "
                f"с {fixed_unique} до {unique}."
            )

        if corrected_delta > 0:
            lines.append(
                f"- Число исправленных ошибок увеличилось "
                f"с {fixed_corrected} до {corrected}."
            )
        elif corrected_delta == 0:
            lines.append(
                f"- Число исправленных ошибок не изменилось "
                f"и равно {corrected}."
            )
        else:
            lines.append(
                f"- Число исправленных ошибок уменьшилось "
                f"с {fixed_corrected} до {corrected}."
            )

        if busy_delta > 0.0:
            lines.append(
                f"- Занятость памяти выросла с {fixed_busy:.1f} % "
                f"до {busy:.1f} %, то есть на {busy_delta:.1f} процентного пункта."
            )
        elif busy_delta == 0.0:
            lines.append(
                f"- Занятость памяти не изменилась и равна {busy:.1f} %."
            )
        else:
            lines.append(
                f"- Занятость памяти уменьшилась с {fixed_busy:.1f} % "
                f"до {busy:.1f} %."
            )

        lines.append("")

    best_unique = min(to_int(row, "unique_uncorrectable_words") for row in rows)
    best_rows = [
        row for row in rows
        if to_int(row, "unique_uncorrectable_words") == best_unique
    ]

    best_rows_sorted = sorted(
        best_rows,
        key=lambda row: to_int(row, "busy_per_mille"),
    )

    best = best_rows_sorted[0]

    lines.append("## Предварительная интерпретация")
    lines.append("")
    lines.append(
        f"Минимальное число уникальных неустранимых слов равно {best_unique}. "
        f"Среди стратегий с этим значением наименьшую занятость памяти имеет "
        f"`{best['strategy'].strip()}` "
        f"({to_float_percent_from_per_mille(best, 'busy_per_mille'):.1f} %)."
    )

    return lines


def write_markdown_summary(
    rows: list[dict[str, str]],
    output_path: Path,
    input_path: Path,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []

    lines.append("# Сводка сравнения стратегий скраббинга")
    lines.append("")
    lines.append(f"Источник данных: `{input_path}`")
    lines.append("")

    lines.extend(format_summary_table(rows))
    lines.append("")
    lines.extend(make_conclusions(rows))
    lines.append("")

    with output_path.open("w", encoding="utf-8", newline="\n") as file:
        file.write("\n".join(lines))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze strategy comparison results."
    )

    parser.add_argument(
        "--input",
        type=Path,
        default=Path("results/tables/strategy_comparison.csv"),
        help="Input CSV file.",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/tables/strategy_summary.md"),
        help="Output Markdown summary.",
    )

    args = parser.parse_args()

    rows = read_results(args.input)
    write_markdown_summary(rows, args.output, args.input)

    print(f"Analyzed {len(rows)} strategy rows")
    print(f"Summary written to: {args.output}")


if __name__ == "__main__":
    main()
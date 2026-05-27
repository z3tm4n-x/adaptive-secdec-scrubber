#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path
from statistics import mean


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(path)

    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def measured_score(
    *,
    corrected_per_100k: float,
    uncorrectable_per_100k: float,
    uncorrectable_weight: float,
) -> float:
    return corrected_per_100k + uncorrectable_weight * uncorrectable_per_100k


def score_to_level(
    *,
    score: float,
    rate_max: float,
    max_level: int,
) -> int:
    if rate_max <= 0.0:
        raise ValueError("rate-max must be positive")

    raw = round(score / rate_max * max_level)
    return max(0, min(max_level, int(raw)))


def build_schedule_rows(
    *,
    rows: list[dict[str, str]],
    source_strategy: str,
    total_cycles: int,
    extra_delay_windows: int,
    uncorrectable_weight: float,
    rate_max: float,
    max_level: int,
) -> tuple[list[tuple[int, int]], list[dict[str, object]]]:
    source_rows = [
        row for row in rows
        if row["strategy"] == source_strategy
    ]

    if not source_rows:
        raise ValueError(f"No rows for strategy: {source_strategy}")

    source_rows.sort(key=lambda row: int(row["window_start"]))

    schedule: list[tuple[int, int]] = [(0, 0)]
    detailed: list[dict[str, object]] = []

    for row in source_rows:
        window_start = int(row["window_start"])
        window_end = int(row["window_end"])
        window_cycles = int(row["window_cycles"])

        corrected_rate = float(row["corrected_per_100k_cycles"])
        uncorrectable_rate = float(row["uncorrectable_detections_per_100k_cycles"])

        score = measured_score(
            corrected_per_100k=corrected_rate,
            uncorrectable_per_100k=uncorrectable_rate,
            uncorrectable_weight=uncorrectable_weight,
        )

        level = score_to_level(
            score=score,
            rate_max=rate_max,
            max_level=max_level,
        )

        schedule_cycle = window_end + extra_delay_windows * window_cycles

        if schedule_cycle < total_cycles:
            schedule.append((schedule_cycle, level))

        detailed.append(
            {
                "source_strategy": source_strategy,
                "window_start": window_start,
                "window_end": window_end,
                "window_cycles": window_cycles,
                "schedule_cycle": schedule_cycle,
                "corrected_delta": int(row["corrected_delta"]),
                "uncorrectable_detection_delta": int(row["uncorrectable_detection_delta"]),
                "corrected_per_100k_cycles": corrected_rate,
                "uncorrectable_detections_per_100k_cycles": uncorrectable_rate,
                "measured_score": score,
                "measured_level": level,
                "true_total_events": int(row["true_total_events"]),
                "true_single_events": int(row["true_single_events"]),
                "true_paired_events": int(row["true_paired_events"]),
                "true_cluster_events": int(row["true_cluster_events"]),
            }
        )

    # Убираем подряд идущие дубли уровня: тестбенчу это не нужно.
    compact: list[tuple[int, int]] = []

    for cycle, level in schedule:
        if compact and compact[-1][1] == level:
            continue
        compact.append((cycle, level))

    return compact, detailed


def write_control_levels(path: Path, schedule: list[tuple[int, int]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8", newline="\n") as f:
        for cycle, level in schedule:
            f.write(f"{cycle},{level}\n")


def write_detailed_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "source_strategy",
        "window_start",
        "window_end",
        "window_cycles",
        "schedule_cycle",
        "corrected_delta",
        "uncorrectable_detection_delta",
        "corrected_per_100k_cycles",
        "uncorrectable_detections_per_100k_cycles",
        "measured_score",
        "measured_level",
        "true_total_events",
        "true_single_events",
        "true_paired_events",
        "true_cluster_events",
    ]

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for row in rows:
            writer.writerow({name: row[name] for name in fieldnames})


def write_markdown(
    path: Path,
    *,
    schedule: list[tuple[int, int]],
    detailed: list[dict[str, object]],
    windows_path: Path,
    source_strategy: str,
    total_cycles: int,
    extra_delay_windows: int,
    uncorrectable_weight: float,
    rate_max: float,
    max_level: int,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    levels = [int(row["measured_level"]) for row in detailed]
    scores = [float(row["measured_score"]) for row in detailed]
    corrected_rates = [float(row["corrected_per_100k_cycles"]) for row in detailed]
    uncorrectable_rates = [
        float(row["uncorrectable_detections_per_100k_cycles"])
        for row in detailed
    ]

    level_counts = Counter(levels)

    lines: list[str] = []

    lines.append("# Measured level schedule")
    lines.append("")
    lines.append("## Назначение")
    lines.append("")
    lines.append(
        "Строится управляющее расписание `ctrl_level(t)` только из наблюдаемых "
        "счётчиков исполнения: приращений `corrected_error_count` и "
        "`uncorrectable_error_count` по окнам. Истинный ряд ν(t) и истинные "
        "метаданные событий не используются для выбора уровня."
    )
    lines.append("")
    lines.append("## Исходные параметры")
    lines.append("")
    lines.append(f"- Входной файл окон: `{windows_path}`")
    lines.append(f"- Источник наблюдаемых счётчиков: `{source_strategy}`")
    lines.append(f"- Длительность моделирования: {total_cycles} тактов")
    lines.append(f"- Дополнительная задержка: {extra_delay_windows} окон")
    lines.append(f"- Вес неустранимых обнаружений: {uncorrectable_weight}")
    lines.append(f"- Нормировка score→level, rate_max: {rate_max}")
    lines.append(f"- Максимальный уровень: {max_level}")
    lines.append("")

    lines.append("## Формула")
    lines.append("")
    lines.append(
        "`score = corrected_per_100k_cycles + "
        "uncorrectable_weight · uncorrectable_detections_per_100k_cycles`"
    )
    lines.append("")
    lines.append("`level = round(score / rate_max · max_level)`, с насыщением в диапазоне 0…max_level.")
    lines.append("")

    lines.append("## Сводка")
    lines.append("")
    lines.append("| Показатель | Значение |")
    lines.append("|---|---:|")
    lines.append(f"| Число окон | {len(detailed)} |")
    lines.append(f"| Число записей в compact schedule | {len(schedule)} |")
    lines.append(f"| mean corrected / 100k | {mean(corrected_rates):.3f} |")
    lines.append(f"| max corrected / 100k | {max(corrected_rates):.3f} |")
    lines.append(f"| mean uncorrectable detections / 100k | {mean(uncorrectable_rates):.3f} |")
    lines.append(f"| max uncorrectable detections / 100k | {max(uncorrectable_rates):.3f} |")
    lines.append(f"| mean score | {mean(scores):.3f} |")
    lines.append(f"| max score | {max(scores):.3f} |")
    lines.append("")

    lines.append("## Распределение уровней по окнам")
    lines.append("")
    lines.append("| level | windows | fraction, % |")
    lines.append("|---:|---:|---:|")

    for level in range(max_level + 1):
        count = level_counts.get(level, 0)
        fraction = count / len(detailed) * 100.0 if detailed else 0.0
        lines.append(f"| {level} | {count} | {fraction:.3f} |")

    lines.append("")
    lines.append("## Compact schedule")
    lines.append("")
    lines.append("| cycle | level |")
    lines.append("|---:|---:|")

    for cycle, level in schedule:
        lines.append(f"| {cycle} | {level} |")

    lines.append("")
    lines.append("## Окна")
    lines.append("")
    lines.append(
        "| window | corrected | uncorrectable detections | corrected / 100k | "
        "uncorr / 100k | score | level | true total, diagnostic |"
    )
    lines.append("|---:|---:|---:|---:|---:|---:|---:|---:|")

    for row in detailed:
        lines.append(
            f"| {row['window_start']}–{row['window_end']} | "
            f"{row['corrected_delta']} | "
            f"{row['uncorrectable_detection_delta']} | "
            f"{float(row['corrected_per_100k_cycles']):.3f} | "
            f"{float(row['uncorrectable_detections_per_100k_cycles']):.3f} | "
            f"{float(row['measured_score']):.3f} | "
            f"{row['measured_level']} | "
            f"{row['true_total_events']} |"
        )

    lines.append("")
    lines.append("## Интерпретация")
    lines.append("")
    lines.append(
        "Полученное расписание является каузальным относительно окон измерения: "
        "уровень, рассчитанный по окну, применяется начиная с конца этого окна "
        "и не использует будущие наблюдения. Нормировка `rate_max` является "
        "параметром калибровки измерительного канала."
    )
    lines.append("")
    lines.append(
        "Этот результат ещё не является полностью замкнутым контуром. Это "
        "измеренное расписание, построенное offline по наблюдаемой трассе. "
        "Следующий шаг — replay RTL с этим расписанием и сравнение с идеальной "
        "risk-policy."
    )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument("--windows", type=Path, required=True)
    parser.add_argument("--source-strategy", choices=["fixed", "table", "threshold"], required=True)
    parser.add_argument("--total-cycles", type=int, required=True)
    parser.add_argument("--extra-delay-windows", type=int, default=0)
    parser.add_argument("--uncorrectable-weight", type=float, default=0.25)
    parser.add_argument("--rate-max", type=float, default=200.0)
    parser.add_argument("--max-level", type=int, default=7)
    parser.add_argument("--control-output", type=Path, required=True)
    parser.add_argument("--detail-output", type=Path, required=True)
    parser.add_argument("--md-output", type=Path, required=True)

    args = parser.parse_args()

    rows = read_csv(args.windows)

    schedule, detailed = build_schedule_rows(
        rows=rows,
        source_strategy=args.source_strategy,
        total_cycles=args.total_cycles,
        extra_delay_windows=args.extra_delay_windows,
        uncorrectable_weight=args.uncorrectable_weight,
        rate_max=args.rate_max,
        max_level=args.max_level,
    )

    write_control_levels(args.control_output, schedule)
    write_detailed_csv(args.detail_output, detailed)
    write_markdown(
        args.md_output,
        schedule=schedule,
        detailed=detailed,
        windows_path=args.windows,
        source_strategy=args.source_strategy,
        total_cycles=args.total_cycles,
        extra_delay_windows=args.extra_delay_windows,
        uncorrectable_weight=args.uncorrectable_weight,
        rate_max=args.rate_max,
        max_level=args.max_level,
    )

    print(args.md_output.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()

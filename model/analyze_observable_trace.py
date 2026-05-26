#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import math
from collections import defaultdict
from pathlib import Path
from statistics import mean, stdev


REQUIRED_TRACE_COLUMNS = [
    "strategy",
    "cycle",
    "scrub_cycle_count",
    "corrected_error_count",
    "uncorrectable_error_count",
    "memory_read_count",
    "memory_write_count",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(path)

    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def require_columns(rows: list[dict[str, str]], required: list[str], path: Path) -> None:
    if not rows:
        raise ValueError(f"CSV is empty: {path}")

    missing = [name for name in required if name not in rows[0]]

    if missing:
        raise ValueError(f"Missing columns in {path}: {missing}")


def read_meta_events(path: Path) -> list[dict[str, str]]:
    rows = read_csv(path)

    required = [
        "event_type",
        "actual_cycle",
        "cycle_shift",
    ]

    require_columns(rows, required, path)
    return rows


def rows_by_strategy(trace_rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)

    for row in trace_rows:
        grouped[row["strategy"]].append(row)

    for strategy, items in grouped.items():
        items.sort(key=lambda row: int(row["cycle"]))

    return grouped


def snapshot_at_or_before(
    rows: list[dict[str, str]],
    cycle: int,
) -> dict[str, int]:
    selected: dict[str, str] | None = None

    for row in rows:
        if int(row["cycle"]) <= cycle:
            selected = row
        else:
            break

    if selected is None:
        return {
            "cycle": 0,
            "scrub_cycle_count": 0,
            "corrected_error_count": 0,
            "uncorrectable_error_count": 0,
            "memory_read_count": 0,
            "memory_write_count": 0,
        }

    return {
        "cycle": int(selected["cycle"]),
        "scrub_cycle_count": int(selected["scrub_cycle_count"]),
        "corrected_error_count": int(selected["corrected_error_count"]),
        "uncorrectable_error_count": int(selected["uncorrectable_error_count"]),
        "memory_read_count": int(selected["memory_read_count"]),
        "memory_write_count": int(selected["memory_write_count"]),
    }


def true_counts_for_window(
    meta_rows: list[dict[str, str]],
    start_cycle: int,
    end_cycle: int,
) -> dict[str, int]:
    counts = {
        "true_total_events": 0,
        "true_single_events": 0,
        "true_paired_events": 0,
        "true_cluster_events": 0,
        "true_shifted_events": 0,
    }

    for row in meta_rows:
        cycle = int(row["actual_cycle"])

        if not (start_cycle <= cycle < end_cycle):
            continue

        counts["true_total_events"] += 1

        event_type = row["event_type"]

        if event_type == "single":
            counts["true_single_events"] += 1
        elif event_type == "paired":
            counts["true_paired_events"] += 1
        elif event_type == "cluster":
            counts["true_cluster_events"] += 1

        if int(row["cycle_shift"]) != 0:
            counts["true_shifted_events"] += 1

    return counts


def pearson(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) != len(ys) or len(xs) < 2:
        return None

    mx = mean(xs)
    my = mean(ys)

    dx = [x - mx for x in xs]
    dy = [y - my for y in ys]

    sx = math.sqrt(sum(x * x for x in dx))
    sy = math.sqrt(sum(y * y for y in dy))

    if sx == 0.0 or sy == 0.0:
        return None

    return sum(x * y for x, y in zip(dx, dy)) / (sx * sy)


def analyze(
    *,
    trace_path: Path,
    meta_path: Path,
    total_cycles: int,
    window_cycles: int,
) -> list[dict[str, object]]:
    trace_rows = read_csv(trace_path)
    require_columns(trace_rows, REQUIRED_TRACE_COLUMNS, trace_path)

    meta_rows = read_meta_events(meta_path)
    grouped = rows_by_strategy(trace_rows)

    out: list[dict[str, object]] = []

    for strategy, rows in sorted(grouped.items()):
        for start in range(0, total_cycles, window_cycles):
            end = min(start + window_cycles, total_cycles)

            before = snapshot_at_or_before(rows, start - 1)
            after = snapshot_at_or_before(rows, end - 1)

            corrected_delta = (
                after["corrected_error_count"] - before["corrected_error_count"]
            )
            uncorrectable_delta = (
                after["uncorrectable_error_count"]
                - before["uncorrectable_error_count"]
            )
            read_delta = after["memory_read_count"] - before["memory_read_count"]
            write_delta = after["memory_write_count"] - before["memory_write_count"]
            scrub_delta = after["scrub_cycle_count"] - before["scrub_cycle_count"]

            true_counts = true_counts_for_window(meta_rows, start, end)
            scale = 100000.0 / max(1, end - start)

            out.append(
                {
                    "strategy": strategy,
                    "window_start": start,
                    "window_end": end,
                    "window_cycles": end - start,
                    "scrub_delta": scrub_delta,
                    "corrected_delta": corrected_delta,
                    "uncorrectable_detection_delta": uncorrectable_delta,
                    "read_delta": read_delta,
                    "write_delta": write_delta,
                    "corrected_per_100k_cycles": corrected_delta * scale,
                    "uncorrectable_detections_per_100k_cycles": uncorrectable_delta * scale,
                    "read_per_100k_cycles": read_delta * scale,
                    "write_per_100k_cycles": write_delta * scale,
                    **true_counts,
                }
            )

    return out


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "strategy",
        "window_start",
        "window_end",
        "window_cycles",
        "scrub_delta",
        "corrected_delta",
        "uncorrectable_detection_delta",
        "read_delta",
        "write_delta",
        "corrected_per_100k_cycles",
        "uncorrectable_detections_per_100k_cycles",
        "read_per_100k_cycles",
        "write_per_100k_cycles",
        "true_total_events",
        "true_single_events",
        "true_paired_events",
        "true_cluster_events",
        "true_shifted_events",
    ]

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for row in rows:
            writer.writerow({name: row[name] for name in fieldnames})


def strategy_summary(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)

    for row in rows:
        grouped[str(row["strategy"])].append(row)

    out: list[dict[str, object]] = []

    for strategy, items in sorted(grouped.items()):
        corrected_rates = [float(row["corrected_per_100k_cycles"]) for row in items]
        uncorrectable_rates = [
            float(row["uncorrectable_detections_per_100k_cycles"])
            for row in items
        ]
        corrected_deltas = [float(row["corrected_delta"]) for row in items]
        true_totals = [float(row["true_total_events"]) for row in items]
        true_single = [float(row["true_single_events"]) for row in items]
        true_paired = [float(row["true_paired_events"]) for row in items]

        out.append(
            {
                "strategy": strategy,
                "windows": len(items),
                "corrected_total": sum(corrected_deltas),
                "true_total": sum(true_totals),
                "true_single": sum(true_single),
                "true_paired": sum(true_paired),
                "corrected_rate_mean": mean(corrected_rates),
                "corrected_rate_std": stdev(corrected_rates) if len(corrected_rates) > 1 else 0.0,
                "corrected_rate_max": max(corrected_rates),
                "uncorrectable_rate_mean": mean(uncorrectable_rates),
                "uncorrectable_rate_max": max(uncorrectable_rates),
                "corr_corrected_vs_true_total": pearson(corrected_rates, true_totals),
                "corr_corrected_vs_true_single": pearson(corrected_rates, true_single),
            }
        )

    return out


def top_windows(
    rows: list[dict[str, object]],
    *,
    strategy: str,
    metric: str,
    count: int,
) -> list[dict[str, object]]:
    selected = [row for row in rows if row["strategy"] == strategy]

    return sorted(
        selected,
        key=lambda row: float(row[metric]),
        reverse=True,
    )[:count]


def write_markdown(
    path: Path,
    *,
    rows: list[dict[str, object]],
    trace_path: Path,
    meta_path: Path,
    total_cycles: int,
    window_cycles: int,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    summary = strategy_summary(rows)

    lines: list[str] = []

    lines.append("# Анализ наблюдаемого сигнала по счётчикам")
    lines.append("")
    lines.append("## Назначение")
    lines.append("")
    lines.append(
        "Оценивается, какой управляющий сигнал можно получить только из "
        "наблюдаемых счётчиков тестбенча: `corrected_error_count` и "
        "`uncorrectable_error_count`. Истинные события из `fault_events_meta.csv` "
        "используются только для диагностического сравнения и не входят в "
        "измерительную оценку."
    )
    lines.append("")
    lines.append("## Исходные файлы")
    lines.append("")
    lines.append(f"- Trace: `{trace_path}`")
    lines.append(f"- Metadata: `{meta_path}`")
    lines.append(f"- Длительность моделирования: {total_cycles} тактов")
    lines.append(f"- Окно оценки: {window_cycles} тактов")
    lines.append("")

    lines.append("## Сводка по стратегиям")
    lines.append("")
    lines.append(
        "| strategy | windows | corrected total | true total events | "
        "mean corrected / 100k cycles | max corrected / 100k cycles | "
        "mean uncorrectable detections / 100k cycles | "
        "corr(corrected, true total) | corr(corrected, true single) |"
    )
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")

    for item in summary:
        corr_total = item["corr_corrected_vs_true_total"]
        corr_single = item["corr_corrected_vs_true_single"]

        lines.append(
            f"| `{item['strategy']}` | "
            f"{item['windows']} | "
            f"{item['corrected_total']:.0f} | "
            f"{item['true_total']:.0f} | "
            f"{item['corrected_rate_mean']:.3f} ± {item['corrected_rate_std']:.3f} | "
            f"{item['corrected_rate_max']:.3f} | "
            f"{item['uncorrectable_rate_mean']:.3f} | "
            f"{corr_total:.3f}" if corr_total is not None else "|  |"
        )

        # Исправляем последнюю строку без сложной конкатенации.
        lines.pop()
        lines.append(
            f"| `{item['strategy']}` | "
            f"{item['windows']} | "
            f"{item['corrected_total']:.0f} | "
            f"{item['true_total']:.0f} | "
            f"{item['corrected_rate_mean']:.3f} ± {item['corrected_rate_std']:.3f} | "
            f"{item['corrected_rate_max']:.3f} | "
            f"{item['uncorrectable_rate_mean']:.3f} | "
            f"{(corr_total if corr_total is not None else float('nan')):.3f} | "
            f"{(corr_single if corr_single is not None else float('nan')):.3f} |"
        )

    lines.append("")
    lines.append("## Окна с максимальным наблюдаемым corrected-rate")
    lines.append("")

    for strategy in ["fixed", "table", "threshold"]:
        selected = top_windows(
            rows,
            strategy=strategy,
            metric="corrected_per_100k_cycles",
            count=5,
        )

        lines.append(f"### `{strategy}`")
        lines.append("")
        lines.append(
            "| window | corrected | corrected / 100k | uncorrectable detections | "
            "true total | true single | true paired |"
        )
        lines.append("|---:|---:|---:|---:|---:|---:|---:|")

        for row in selected:
            lines.append(
                f"| {row['window_start']}–{row['window_end']} | "
                f"{row['corrected_delta']} | "
                f"{row['corrected_per_100k_cycles']:.3f} | "
                f"{row['uncorrectable_detection_delta']} | "
                f"{row['true_total_events']} | "
                f"{row['true_single_events']} | "
                f"{row['true_paired_events']} |"
            )

        lines.append("")

    lines.append("## Интерпретация")
    lines.append("")
    lines.append(
        "Полученный сигнал является эндогенным: он зависит не только от внешнего "
        "потока событий, но и от выбранной частоты циклического восстановления. "
        "При более редком проходе часть ошибок может перейти в неустранимое "
        "состояние и перестать попадать в счётчик исправленных ошибок."
    )
    lines.append("")
    lines.append(
        "Поэтому `corrected_error_count` является не прямым измерением истинной "
        "частоты одиночных сбоев, а нижней оценкой наблюдаемой исправляемой "
        "части потока. `uncorrectable_error_count` должен рассматриваться как "
        "дополнительный индикатор насыщения или недооценки опасного участка."
    )
    lines.append("")
    lines.append(
        "Этот отчёт является подготовительным шагом к замкнутому контуру: "
        "следующий этап — построение управляющего уровня по окнам "
        "`corrected_error_count` без доступа к истинному ряду ν(t)."
    )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument("--trace", type=Path, required=True)
    parser.add_argument("--meta", type=Path, required=True)
    parser.add_argument("--total-cycles", type=int, required=True)
    parser.add_argument("--window-cycles", type=int, default=25000)
    parser.add_argument("--csv-output", type=Path, required=True)
    parser.add_argument("--md-output", type=Path, required=True)

    args = parser.parse_args()

    rows = analyze(
        trace_path=args.trace,
        meta_path=args.meta,
        total_cycles=args.total_cycles,
        window_cycles=args.window_cycles,
    )

    write_csv(args.csv_output, rows)
    write_markdown(
        args.md_output,
        rows=rows,
        trace_path=args.trace,
        meta_path=args.meta,
        total_cycles=args.total_cycles,
        window_cycles=args.window_cycles,
    )

    print(args.md_output.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()

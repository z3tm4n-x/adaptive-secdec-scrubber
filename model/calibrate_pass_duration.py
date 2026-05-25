#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import math
import statistics
import subprocess
from collections import Counter
from pathlib import Path


BASE_LEVEL_INTERVALS = [120, 115, 110, 105, 100, 90, 80, 70]
BASE_THRESHOLD_INTERVALS = [130, 100, 80]
BASE_FIXED_INTERVAL = 80


def parse_int_list(text: str, expected_count: int, name: str) -> list[int]:
    values: list[int] = []

    for raw_part in text.replace(";", ",").split(","):
        part = raw_part.strip()

        if not part:
            continue

        value = int(part)

        if value <= 0:
            raise ValueError(f"{name} values must be positive: {value}")

        values.append(value)

    if len(values) != expected_count:
        raise ValueError(
            f"{name} must contain exactly {expected_count} values, got {len(values)}"
        )

    return values


def run_trace(
    *,
    addr_width: int,
    total_cycles: int,
    fixed_interval: int,
    level_intervals: list[int],
    threshold_intervals: list[int],
    output_dir: Path,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)

    trace_path = output_dir / f"trace_addr_width_{addr_width}.csv"

    if trace_path.exists():
        trace_path.unlink()

    command = [
        "make",
        "test_strategy_comparison",
        f"ADDR_WIDTH={addr_width}",
        "DUMP_VCD=0",
        "TRACE_EXECUTION=1",
        f"TRACE_OUTPUT={trace_path}",
        "FAULT_SCENARIO=upsets",
        f"FAULT_TOTAL_CYCLES={total_cycles}",
        f"FAULT_WINDOW_SIZE={total_cycles}",
        "FAULT_EVENT_COUNT=0",
        "FAULT_PAIRED_EVENT_COUNT=0",
        "FAULT_CLUSTER_EVENT_COUNT=0",
        "FAULT_CLUSTER_BIT_COUNT=2",
        "FAULT_SEED=1",
        f"FIXED_INTERVAL={fixed_interval}",
        f"SAFE_INTERVAL={fixed_interval}",
        f"LEVEL0_INTERVAL={level_intervals[0]}",
        f"LEVEL1_INTERVAL={level_intervals[1]}",
        f"LEVEL2_INTERVAL={level_intervals[2]}",
        f"LEVEL3_INTERVAL={level_intervals[3]}",
        f"LEVEL4_INTERVAL={level_intervals[4]}",
        f"LEVEL5_INTERVAL={level_intervals[5]}",
        f"LEVEL6_INTERVAL={level_intervals[6]}",
        f"LEVEL7_INTERVAL={level_intervals[7]}",
        f"THRESHOLD_LOW_INTERVAL={threshold_intervals[0]}",
        f"THRESHOLD_MEDIUM_INTERVAL={threshold_intervals[1]}",
        f"THRESHOLD_HIGH_INTERVAL={threshold_intervals[2]}",
    ]

    print("")
    print("=" * 80)
    print(" ".join(command))
    print("=" * 80)

    subprocess.run(command, check=True)

    if not trace_path.exists():
        raise FileNotFoundError(f"Trace was not generated: {trace_path}")

    return trace_path


def read_trace(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        raise ValueError(f"Trace is empty: {path}")

    return rows


def measure_pass_duration(rows: list[dict[str, str]], strategy: str = "fixed") -> dict[str, object]:
    selected_rows = [
        row for row in rows
        if row["strategy"] == strategy
    ]

    if not selected_rows:
        raise ValueError(f"No trace rows for strategy={strategy}")

    positive_durations = [
        int(row["last_pass_duration"])
        for row in selected_rows
        if int(row["last_pass_duration"]) > 0
    ]

    if not positive_durations:
        raise ValueError(f"No positive last_pass_duration values for strategy={strategy}")

    counts = Counter(positive_durations)
    mode_value, mode_count = counts.most_common(1)[0]

    return {
        "strategy": strategy,
        "trace_rows": len(selected_rows),
        "positive_duration_rows": len(positive_durations),
        "pass_duration_min": min(positive_durations),
        "pass_duration_max": max(positive_durations),
        "pass_duration_mean": statistics.mean(positive_durations),
        "pass_duration_median": statistics.median(positive_durations),
        "pass_duration_mode": mode_value,
        "pass_duration_mode_count": mode_count,
        "scrub_cycles_observed": max(int(row["scrub_cycle_count"]) for row in selected_rows),
    }


def scale_intervals(
    *,
    base_pass_duration: int,
    new_pass_duration: int,
    intervals: list[int],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []

    for interval in intervals:
        ratio = interval / base_pass_duration
        scaled = math.ceil(ratio * new_pass_duration)
        effective_wait = max(1, scaled - new_pass_duration)

        rows.append(
            {
                "base_interval": interval,
                "ratio_to_base_pass": ratio,
                "scaled_interval": scaled,
                "effective_wait": effective_wait,
                "scaled_ratio_to_new_pass": scaled / new_pass_duration,
            }
        )

    return rows


def write_csv(
    path: Path,
    *,
    measurement_rows: list[dict[str, object]],
    scaled_level_rows: list[dict[str, object]],
    scaled_threshold_rows: list[dict[str, object]],
    scaled_fixed_row: dict[str, object],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["section", "name", "metric", "value"])

        for row in measurement_rows:
            name = f"addr_width_{row['addr_width']}"
            for key, value in row.items():
                writer.writerow(["pass_duration", name, key, value])

        for index, row in enumerate(scaled_level_rows):
            name = f"level{index}"
            for key, value in row.items():
                writer.writerow(["scaled_level_interval", name, key, value])

        for index, row in enumerate(scaled_threshold_rows):
            name = ["low", "medium", "high"][index]
            for key, value in row.items():
                writer.writerow(["scaled_threshold_interval", name, key, value])

        for key, value in scaled_fixed_row.items():
            writer.writerow(["scaled_fixed_interval", "fixed", key, value])


def write_md(
    path: Path,
    *,
    base_addr_width: int,
    new_addr_width: int,
    base_depth: int,
    new_depth: int,
    measurement_rows: list[dict[str, object]],
    scaled_level_rows: list[dict[str, object]],
    scaled_threshold_rows: list[dict[str, object]],
    scaled_fixed_row: dict[str, object],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    base = next(row for row in measurement_rows if row["addr_width"] == base_addr_width)
    new = next(row for row in measurement_rows if row["addr_width"] == new_addr_width)

    lines: list[str] = []
    lines.append("# Калибровка длительности полного прохода")
    lines.append("")
    lines.append("## Назначение")
    lines.append("")
    lines.append(
        "Измеряется фактическая длительность полного прохода контроллера "
        "в модельных тактах для базовой памяти DEPTH=16 и контрольной "
        "памяти DEPTH=256. По измеренному отношению интервала к длительности "
        "прохода строится масштабированная шкала периодов для контрольной "
        "серии вне насыщения."
    )
    lines.append("")
    lines.append("## Измерение полного прохода")
    lines.append("")
    lines.append(
        "| ADDR_WIDTH | DEPTH | Строк трассы | Положительных last_pass_duration | "
        "min | mean | median | mode | max | scrub cycles |"
    )
    lines.append("|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")

    for row in measurement_rows:
        lines.append(
            f"| {row['addr_width']} | {row['depth']} | "
            f"{row['trace_rows']} | {row['positive_duration_rows']} | "
            f"{row['pass_duration_min']} | {row['pass_duration_mean']:.6f} | "
            f"{row['pass_duration_median']} | {row['pass_duration_mode']} | "
            f"{row['pass_duration_max']} | {row['scrub_cycles_observed']} |"
        )

    lines.append("")
    lines.append("## Масштабирование")
    lines.append("")
    lines.append(f"- Базовая глубина: {base_depth}")
    lines.append(f"- Контрольная глубина: {new_depth}")
    lines.append(f"- Базовая длительность прохода, тактов: {base['pass_duration_mode']}")
    lines.append(f"- Контрольная длительность прохода, тактов: {new['pass_duration_mode']}")
    lines.append(
        "- Правило масштабирования: "
        "`I_new = ceil((I_base / Tpass_base) * Tpass_new)`"
    )
    lines.append("")
    lines.append("## Табличная шкала")
    lines.append("")
    lines.append(
        "| Уровень | Ibase | Ibase/Tpass_base | Inew | "
        "Inew/Tpass_new | effective_wait=Inew−Tpass_new |"
    )
    lines.append("|---:|---:|---:|---:|---:|---:|")

    for index, row in enumerate(scaled_level_rows):
        lines.append(
            f"| {index} | {row['base_interval']} | "
            f"{row['ratio_to_base_pass']:.6f} | {row['scaled_interval']} | "
            f"{row['scaled_ratio_to_new_pass']:.6f} | {row['effective_wait']} |"
        )

    lines.append("")
    lines.append("## Пороговая шкала")
    lines.append("")
    lines.append(
        "| Режим | Ibase | Ibase/Tpass_base | Inew | "
        "Inew/Tpass_new | effective_wait=Inew−Tpass_new |"
    )
    lines.append("|---|---:|---:|---:|---:|---:|")

    for name, row in zip(["low", "medium", "high"], scaled_threshold_rows):
        lines.append(
            f"| `{name}` | {row['base_interval']} | "
            f"{row['ratio_to_base_pass']:.6f} | {row['scaled_interval']} | "
            f"{row['scaled_ratio_to_new_pass']:.6f} | {row['effective_wait']} |"
        )

    lines.append("")
    lines.append("## Постоянный интервал")
    lines.append("")
    lines.append(
        "| Ibase | Ibase/Tpass_base | Inew | Inew/Tpass_new | effective_wait |"
    )
    lines.append("|---:|---:|---:|---:|---:|")
    lines.append(
        f"| {scaled_fixed_row['base_interval']} | "
        f"{scaled_fixed_row['ratio_to_base_pass']:.6f} | "
        f"{scaled_fixed_row['scaled_interval']} | "
        f"{scaled_fixed_row['scaled_ratio_to_new_pass']:.6f} | "
        f"{scaled_fixed_row['effective_wait']} |"
    )

    lines.append("")
    lines.append("## Интерпретация")
    lines.append("")
    lines.append(
        "Эта калибровка относится к методической контрольной серии с увеличенной "
        "модельной памятью. Она не является физической аппаратной проекцией "
        "целевого изделия; физическая исполнимость секундных интервалов "
        "оценивается отдельно по длительности полного прохода реальной "
        "защищаемой области."
    )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument("--base-addr-width", type=int, default=4)
    parser.add_argument("--new-addr-width", type=int, default=8)
    parser.add_argument("--base-total-cycles", type=int, default=5000)
    parser.add_argument("--new-total-cycles", type=int, default=12000)
    parser.add_argument(
        "--base-level-intervals",
        default="120,115,110,105,100,90,80,70",
    )
    parser.add_argument(
        "--base-threshold-intervals",
        default="130,100,80",
    )
    parser.add_argument("--base-fixed-interval", type=int, default=80)
    parser.add_argument(
        "--work-dir",
        type=Path,
        default=Path("results/paper/unsaturated_control"),
    )
    parser.add_argument(
        "--csv-output",
        type=Path,
        default=Path("results/paper/unsaturated_control/pass_duration_calibration.csv"),
    )
    parser.add_argument(
        "--md-output",
        type=Path,
        default=Path("results/paper/unsaturated_control/pass_duration_calibration.md"),
    )

    args = parser.parse_args()

    base_level_intervals = parse_int_list(
        args.base_level_intervals,
        expected_count=8,
        name="base-level-intervals",
    )
    base_threshold_intervals = parse_int_list(
        args.base_threshold_intervals,
        expected_count=3,
        name="base-threshold-intervals",
    )

    base_trace = run_trace(
        addr_width=args.base_addr_width,
        total_cycles=args.base_total_cycles,
        fixed_interval=args.base_fixed_interval,
        level_intervals=base_level_intervals,
        threshold_intervals=base_threshold_intervals,
        output_dir=args.work_dir,
    )

    # Для новой глубины сначала используем грубую шкалу, заведомо больше прохода.
    # Точная контрольная шкала будет построена по измеренному Tpass_new.
    rough_level_intervals = [1920, 1840, 1760, 1680, 1600, 1440, 1280, 1120]
    rough_threshold_intervals = [2080, 1600, 1280]

    new_trace = run_trace(
        addr_width=args.new_addr_width,
        total_cycles=args.new_total_cycles,
        fixed_interval=1280,
        level_intervals=rough_level_intervals,
        threshold_intervals=rough_threshold_intervals,
        output_dir=args.work_dir,
    )

    base_rows = read_trace(base_trace)
    new_rows = read_trace(new_trace)

    base_measure = measure_pass_duration(base_rows, strategy="fixed")
    new_measure = measure_pass_duration(new_rows, strategy="fixed")

    base_measure["addr_width"] = args.base_addr_width
    base_measure["depth"] = 1 << args.base_addr_width
    base_measure["trace_path"] = str(base_trace)

    new_measure["addr_width"] = args.new_addr_width
    new_measure["depth"] = 1 << args.new_addr_width
    new_measure["trace_path"] = str(new_trace)

    measurement_rows = [base_measure, new_measure]

    base_pass_duration = int(base_measure["pass_duration_mode"])
    new_pass_duration = int(new_measure["pass_duration_mode"])

    scaled_level_rows = scale_intervals(
        base_pass_duration=base_pass_duration,
        new_pass_duration=new_pass_duration,
        intervals=base_level_intervals,
    )
    scaled_threshold_rows = scale_intervals(
        base_pass_duration=base_pass_duration,
        new_pass_duration=new_pass_duration,
        intervals=base_threshold_intervals,
    )
    scaled_fixed_row = scale_intervals(
        base_pass_duration=base_pass_duration,
        new_pass_duration=new_pass_duration,
        intervals=[args.base_fixed_interval],
    )[0]

    write_csv(
        args.csv_output,
        measurement_rows=measurement_rows,
        scaled_level_rows=scaled_level_rows,
        scaled_threshold_rows=scaled_threshold_rows,
        scaled_fixed_row=scaled_fixed_row,
    )
    write_md(
        args.md_output,
        base_addr_width=args.base_addr_width,
        new_addr_width=args.new_addr_width,
        base_depth=1 << args.base_addr_width,
        new_depth=1 << args.new_addr_width,
        measurement_rows=measurement_rows,
        scaled_level_rows=scaled_level_rows,
        scaled_threshold_rows=scaled_threshold_rows,
        scaled_fixed_row=scaled_fixed_row,
    )

    print(f"CSV: {args.csv_output}")
    print(f"MD:  {args.md_output}")
    print(args.md_output.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()

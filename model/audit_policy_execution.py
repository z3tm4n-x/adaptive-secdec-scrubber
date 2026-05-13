#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from statistics import mean


@dataclass(frozen=True)
class TraceRow:
    strategy: str
    cycle: int
    scrub_cycle_count: int
    selected_interval: int
    current_level: int
    threshold_state: int
    safe_mode_active: int
    control_age: int


@dataclass(frozen=True)
class MetricRow:
    strategy: str
    scrub_cycles: int
    reads: int
    writes: int
    interval_switches: int
    safe_entries: int
    safe_cycles: int


@dataclass(frozen=True)
class ControlEvent:
    cycle: int
    level: int


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


def read_trace(path: Path) -> list[TraceRow]:
    if not path.exists():
        raise FileNotFoundError(path)

    rows: list[TraceRow] = []

    with path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)

        required = {
            "strategy",
            "cycle",
            "scrub_cycle_count",
            "selected_interval",
            "current_level",
            "threshold_state",
            "safe_mode_active",
            "control_age",
        }

        if reader.fieldnames is None:
            raise ValueError(f"Missing CSV header in {path}")

        missing = required - set(reader.fieldnames)

        if missing:
            raise ValueError(
                f"Missing trace columns in {path}: {', '.join(sorted(missing))}"
            )

        for row in reader:
            rows.append(
                TraceRow(
                    strategy=row["strategy"].strip(),
                    cycle=int(row["cycle"]),
                    scrub_cycle_count=int(row["scrub_cycle_count"]),
                    selected_interval=int(row["selected_interval"]),
                    current_level=int(row["current_level"]),
                    threshold_state=int(row["threshold_state"]),
                    safe_mode_active=int(row["safe_mode_active"]),
                    control_age=int(row["control_age"]),
                )
            )

    if not rows:
        raise ValueError(f"No trace rows found in {path}")

    return rows


def read_metrics(path: Path) -> dict[str, MetricRow]:
    if not path.exists():
        raise FileNotFoundError(path)

    result: dict[str, MetricRow] = {}

    with path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)

        required = {
            "strategy",
            "scrub_cycles",
            "reads",
            "writes",
            "interval_switches",
            "safe_entries",
            "safe_cycles",
        }

        if reader.fieldnames is None:
            raise ValueError(f"Missing CSV header in {path}")

        missing = required - set(reader.fieldnames)

        if missing:
            raise ValueError(
                f"Missing metric columns in {path}: {', '.join(sorted(missing))}"
            )

        for row in reader:
            strategy = row["strategy"].strip()

            result[strategy] = MetricRow(
                strategy=strategy,
                scrub_cycles=int(row["scrub_cycles"]),
                reads=int(row["reads"]),
                writes=int(row["writes"]),
                interval_switches=int(row["interval_switches"]),
                safe_entries=int(row["safe_entries"]),
                safe_cycles=int(row["safe_cycles"]),
            )

    return result


def read_control_events(path: Path) -> list[ControlEvent]:
    if not path.exists():
        raise FileNotFoundError(path)

    events: list[ControlEvent] = []

    with path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.reader(file)

        for row in reader:
            if not row:
                continue

            if len(row) != 2:
                raise ValueError(f"Invalid control event row: {row}")

            cycle = int(row[0])
            level = int(row[1])

            if level < 0 or level > 7:
                raise ValueError(f"Control level out of range: {level}")

            events.append(ControlEvent(cycle=cycle, level=level))

    if not events:
        raise ValueError(f"No control events found in {path}")

    events.sort(key=lambda item: item.cycle)

    return events


def control_level_at(events: list[ControlEvent], cycle: int) -> int:
    current = events[0].level

    for event in events:
        if event.cycle > cycle:
            break

        current = event.level

    return current


def group_trace_by_strategy(rows: list[TraceRow]) -> dict[str, list[TraceRow]]:
    grouped: dict[str, list[TraceRow]] = {}

    for row in rows:
        grouped.setdefault(row.strategy, []).append(row)

    for strategy_rows in grouped.values():
        strategy_rows.sort(key=lambda item: item.scrub_cycle_count)

    return grouped


def audit_strategy(
    strategy: str,
    rows: list[TraceRow],
    metrics: MetricRow,
    control_events: list[ControlEvent],
    fixed_interval: int,
    level_intervals: list[int],
    threshold_intervals: list[int],
) -> dict[str, str]:
    if not rows:
        raise ValueError(f"No trace rows for strategy {strategy}")

    final_trace_scrub_cycles = max(row.scrub_cycle_count for row in rows)
    trace_rows = len(rows)

    selected_values = [row.selected_interval for row in rows]

    selected_min = min(selected_values)
    selected_max = max(selected_values)
    selected_mean = mean(selected_values)

    safe_rows = sum(1 for row in rows if row.safe_mode_active != 0)

    interval_mismatches = 0
    control_level_mismatches = 0

    example_interval_mismatch = ""
    example_control_mismatch = ""

    allowed_threshold_intervals = set(threshold_intervals)

    for row in rows:
        expected_interval: int | None = None

        if strategy == "fixed":
            expected_interval = fixed_interval
        elif strategy == "table":
            expected_interval = level_intervals[row.current_level]

            expected_control_level = control_level_at(
                events=control_events,
                cycle=row.cycle,
            )

            if row.current_level != expected_control_level:
                control_level_mismatches += 1

                if not example_control_mismatch:
                    example_control_mismatch = (
                        f"cycle={row.cycle}, current_level={row.current_level}, "
                        f"expected_control_level={expected_control_level}"
                    )
        elif strategy == "threshold":
            if row.selected_interval not in allowed_threshold_intervals:
                interval_mismatches += 1

                if not example_interval_mismatch:
                    example_interval_mismatch = (
                        f"cycle={row.cycle}, selected_interval={row.selected_interval}, "
                        f"allowed={sorted(allowed_threshold_intervals)}"
                    )

            continue
        else:
            continue

        if row.safe_mode_active == 0 and row.selected_interval != expected_interval:
            interval_mismatches += 1

            if not example_interval_mismatch:
                example_interval_mismatch = (
                    f"cycle={row.cycle}, selected_interval={row.selected_interval}, "
                    f"expected_interval={expected_interval}, level={row.current_level}"
                )

    read_expected_from_scrubs = metrics.scrub_cycles * 16
    read_delta = metrics.reads - read_expected_from_scrubs

    return {
        "strategy": strategy,
        "trace_rows": str(trace_rows),
        "rtl_scrub_cycles": str(metrics.scrub_cycles),
        "trace_final_scrub_cycles": str(final_trace_scrub_cycles),
        "scrub_cycle_delta": str(metrics.scrub_cycles - final_trace_scrub_cycles),
        "reads": str(metrics.reads),
        "expected_reads_depth16": str(read_expected_from_scrubs),
        "read_delta": str(read_delta),
        "writes": str(metrics.writes),
        "interval_switches": str(metrics.interval_switches),
        "safe_entries": str(metrics.safe_entries),
        "safe_cycles": str(metrics.safe_cycles),
        "trace_safe_rows": str(safe_rows),
        "selected_interval_min": f"{selected_min}",
        "selected_interval_mean": f"{selected_mean:.6f}",
        "selected_interval_max": f"{selected_max}",
        "interval_mismatches": str(interval_mismatches),
        "control_level_mismatches": str(control_level_mismatches),
        "example_interval_mismatch": example_interval_mismatch,
        "example_control_mismatch": example_control_mismatch,
    }


def write_summary_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "strategy",
        "trace_rows",
        "rtl_scrub_cycles",
        "trace_final_scrub_cycles",
        "scrub_cycle_delta",
        "reads",
        "expected_reads_depth16",
        "read_delta",
        "writes",
        "interval_switches",
        "safe_entries",
        "safe_cycles",
        "trace_safe_rows",
        "selected_interval_min",
        "selected_interval_mean",
        "selected_interval_max",
        "interval_mismatches",
        "control_level_mismatches",
        "example_interval_mismatch",
        "example_control_mismatch",
    ]

    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []

    lines.append("# Аудит исполнения risk-policy в RTL")
    lines.append("")
    lines.append("## Назначение")
    lines.append("")
    lines.append(
        "Проверяется, что RTL-стенд исполняет интервалы, соответствующие "
        "выбранной политике: fixed использует постоянный интервал, table "
        "использует interval[current_level], а threshold ограничен тремя "
        "заданными интервалами."
    )
    lines.append("")
    lines.append("## Сводка")
    lines.append("")
    lines.append(
        "| strategy | trace rows | RTL scrub cycles | trace final scrub cycles | "
        "Δ scrub | reads | expected reads | Δ reads | safe entries | "
        "selected interval range | interval mismatches | control level mismatches |"
    )
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")

    for row in rows:
        lines.append(
            f"| `{row['strategy']}` "
            f"| {row['trace_rows']} "
            f"| {row['rtl_scrub_cycles']} "
            f"| {row['trace_final_scrub_cycles']} "
            f"| {row['scrub_cycle_delta']} "
            f"| {row['reads']} "
            f"| {row['expected_reads_depth16']} "
            f"| {row['read_delta']} "
            f"| {row['safe_entries']} "
            f"| {row['selected_interval_min']}–{row['selected_interval_max']} "
            f"| {row['interval_mismatches']} "
            f"| {row['control_level_mismatches']} |"
        )

    lines.append("")
    lines.append("## Критерии прохождения")
    lines.append("")
    lines.append("- `scrub_cycle_delta = 0` для всех стратегий.")
    lines.append(
        "- `0 <= read_delta < 16`: допускаются чтения незавершённого прохода "
        "в конце окна моделирования, так как ADDR_WIDTH=4 и полный проход читает 16 слов."
    )
    lines.append("- `safe_entries = 0` и `trace_safe_rows = 0`.")
    lines.append("- `interval_mismatches = 0`.")
    lines.append("- Для `table`: `control_level_mismatches = 0`.")
    lines.append("")

    failed = False

    for row in rows:
        if row["scrub_cycle_delta"] != "0":
            failed = True

        read_delta = int(row["read_delta"])
        if read_delta < 0 or read_delta >= 16:
            failed = True
        if row["safe_entries"] != "0":
            failed = True
        if row["trace_safe_rows"] != "0":
            failed = True
        if row["interval_mismatches"] != "0":
            failed = True
        if row["strategy"] == "table" and row["control_level_mismatches"] != "0":
            failed = True

    lines.append("## Итог")
    lines.append("")

    if failed:
        lines.append("**FAIL:** обнаружены расхождения исполнения политики.")
    else:
        lines.append("**PASS:** исполнение интервальной политики в RTL соответствует ожидаемой конфигурации.")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit RTL execution of risk-policy interval mapping."
    )

    parser.add_argument("--trace", type=Path, required=True)
    parser.add_argument("--metrics", type=Path, required=True)
    parser.add_argument("--control-levels", type=Path, required=True)
    parser.add_argument("--fixed-interval", type=int, required=True)
    parser.add_argument("--level-intervals", required=True)
    parser.add_argument("--threshold-intervals", required=True)
    parser.add_argument("--summary-csv", type=Path, required=True)
    parser.add_argument("--md-output", type=Path, required=True)

    args = parser.parse_args()

    level_intervals = parse_int_list(
        args.level_intervals,
        expected_count=8,
        name="level-intervals",
    )

    threshold_intervals = parse_int_list(
        args.threshold_intervals,
        expected_count=3,
        name="threshold-intervals",
    )

    if args.fixed_interval <= 0:
        raise ValueError("fixed-interval must be positive")

    trace_rows = read_trace(args.trace)
    metrics = read_metrics(args.metrics)
    control_events = read_control_events(args.control_levels)

    grouped = group_trace_by_strategy(trace_rows)

    summary_rows: list[dict[str, str]] = []

    for strategy in ("fixed", "table", "threshold"):
        if strategy not in grouped:
            raise ValueError(f"Missing trace rows for strategy {strategy}")

        if strategy not in metrics:
            raise ValueError(f"Missing metrics row for strategy {strategy}")

        summary_rows.append(
            audit_strategy(
                strategy=strategy,
                rows=grouped[strategy],
                metrics=metrics[strategy],
                control_events=control_events,
                fixed_interval=args.fixed_interval,
                level_intervals=level_intervals,
                threshold_intervals=threshold_intervals,
            )
        )

    write_summary_csv(args.summary_csv, summary_rows)
    write_markdown(args.md_output, summary_rows)

    failed = False

    for row in summary_rows:
        if row["scrub_cycle_delta"] != "0":
            failed = True

        read_delta = int(row["read_delta"])
        if read_delta < 0 or read_delta >= 16:
            failed = True
        if row["safe_entries"] != "0":
            failed = True
        if row["trace_safe_rows"] != "0":
            failed = True
        if row["interval_mismatches"] != "0":
            failed = True
        if row["strategy"] == "table" and row["control_level_mismatches"] != "0":
            failed = True

    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
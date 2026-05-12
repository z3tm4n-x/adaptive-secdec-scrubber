#!/usr/bin/env python3

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PolicyScheduleRow:
    hour_index: int
    nu: float
    tau_seconds: float
    lambda_value: float
    q_cycle: float
    cycles_per_hour: float


@dataclass(frozen=True)
class PolicyControlEvent:
    cycle: int
    level: int


@dataclass(frozen=True)
class PolicyLevelMapRow:
    level: int
    interval_seconds: float
    hours: int
    fraction: float


@dataclass(frozen=True)
class PolicyControlResult:
    events: list[PolicyControlEvent]
    level_map: list[PolicyLevelMapRow]


def read_policy_schedule(path: Path) -> list[PolicyScheduleRow]:
    if not path.exists():
        raise FileNotFoundError(f"Risk policy schedule not found: {path}")

    rows: list[PolicyScheduleRow] = []

    with path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)

        required = {
            "hour_index",
            "nu",
            "tau_seconds",
            "lambda",
            "q_cycle",
            "cycles_per_hour",
        }

        if reader.fieldnames is None:
            raise ValueError(f"Empty CSV header in {path}")

        missing = required - set(reader.fieldnames)

        if missing:
            raise ValueError(
                "Missing columns in risk policy schedule: "
                + ", ".join(sorted(missing))
            )

        for row in reader:
            tau_seconds = float(row["tau_seconds"])

            if tau_seconds <= 0.0:
                raise ValueError(f"Non-positive tau_seconds: {tau_seconds}")

            rows.append(
                PolicyScheduleRow(
                    hour_index=int(row["hour_index"]),
                    nu=float(row["nu"]),
                    tau_seconds=tau_seconds,
                    lambda_value=float(row["lambda"]),
                    q_cycle=float(row["q_cycle"]),
                    cycles_per_hour=float(row["cycles_per_hour"]),
                )
            )

    if not rows:
        raise ValueError(f"No rows found in risk policy schedule: {path}")

    return rows


def select_schedule_window(
    rows: list[PolicyScheduleRow],
    start_index: int,
    window_size: int,
) -> list[PolicyScheduleRow]:
    if start_index < 0:
        raise ValueError("start_index must be non-negative")

    if window_size <= 0:
        raise ValueError("window_size must be positive")

    end_index = start_index + window_size

    if end_index > len(rows):
        raise ValueError(
            f"Requested policy schedule window [{start_index}, {end_index}) "
            f"exceeds schedule length {len(rows)}"
        )

    return rows[start_index:end_index]


def interval_key(interval_seconds: float) -> float:
    return round(interval_seconds, 9)


def build_interval_to_level(
    rows: list[PolicyScheduleRow],
    max_levels: int = 8,
) -> dict[float, int]:
    """
    Строит отображение interval_seconds → ctrl_level.

    Смысл уровней:
        level 0 = самый длинный интервал = самый спокойный режим;
        level растёт при уменьшении интервала = более агрессивный скраббинг.

    Для текущей политики статьи 3 ожидается:
        120 s → level 0
         60 s → level 1
         30 s → level 2
         10 s → level 3
          5 s → level 4
          2 s → level 5
          1 s → level 6
    """
    unique_intervals = sorted(
        {interval_key(row.tau_seconds) for row in rows},
        reverse=True,
    )

    if len(unique_intervals) > max_levels:
        raise ValueError(
            f"Risk policy uses {len(unique_intervals)} intervals, "
            f"but only {max_levels} control levels are available. "
            "Reduce the interval set or add interval compression explicitly."
        )

    return {
        interval: level
        for level, interval in enumerate(unique_intervals)
    }


def build_level_map(
    rows: list[PolicyScheduleRow],
    interval_to_level: dict[float, int],
) -> list[PolicyLevelMapRow]:
    total_hours = len(rows)

    if total_hours <= 0:
        raise ValueError("Cannot build level map for empty policy window")

    usage: dict[int, tuple[float, int]] = {}

    for row in rows:
        key = interval_key(row.tau_seconds)
        level = interval_to_level[key]

        interval_seconds, hours = usage.get(level, (key, 0))
        usage[level] = (interval_seconds, hours + 1)

    result: list[PolicyLevelMapRow] = []

    for level in sorted(usage):
        interval_seconds, hours = usage[level]

        result.append(
            PolicyLevelMapRow(
                level=level,
                interval_seconds=interval_seconds,
                hours=hours,
                fraction=hours / total_hours,
            )
        )

    return result


def build_policy_control_events(
    rows: list[PolicyScheduleRow],
    total_cycles: int,
    max_levels: int = 8,
) -> PolicyControlResult:
    if total_cycles <= 0:
        raise ValueError("total_cycles must be positive")

    if not rows:
        raise ValueError("Cannot build control events from empty schedule")

    interval_to_level = build_interval_to_level(
        rows=rows,
        max_levels=max_levels,
    )

    events: list[PolicyControlEvent] = []
    previous_level: int | None = None
    window_size = len(rows)

    for index, row in enumerate(rows):
        key = interval_key(row.tau_seconds)
        level = interval_to_level[key]

        cycle = (index * total_cycles) // window_size

        if cycle >= total_cycles:
            cycle = total_cycles - 1

        if previous_level is None or level != previous_level:
            events.append(
                PolicyControlEvent(
                    cycle=cycle,
                    level=level,
                )
            )
            previous_level = level

    if not events or events[0].cycle != 0:
        events.insert(
            0,
            PolicyControlEvent(cycle=0, level=0),
        )

    return PolicyControlResult(
        events=events,
        level_map=build_level_map(
            rows=rows,
            interval_to_level=interval_to_level,
        ),
    )


def write_policy_level_map_csv(
    output_path: Path,
    level_map: list[PolicyLevelMapRow],
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(
            [
                "level",
                "interval_seconds",
                "hours",
                "fraction",
            ]
        )

        for row in level_map:
            writer.writerow(
                [
                    row.level,
                    f"{row.interval_seconds:.12g}",
                    row.hours,
                    f"{row.fraction:.9f}",
                ]
            )


def write_control_events_csv(
    output_path: Path,
    events: list[PolicyControlEvent],
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)

        for event in events:
            writer.writerow([event.cycle, event.level])
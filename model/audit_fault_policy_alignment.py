#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from statistics import mean


@dataclass(frozen=True)
class FaultEvent:
    cycle: int
    address: int
    mask: int


@dataclass(frozen=True)
class ControlEvent:
    cycle: int
    level: int


@dataclass(frozen=True)
class CandidatePair:
    address: int
    first_cycle: int
    second_cycle: int
    gap: int
    first_level: int
    second_level: int
    max_level: int
    first_interval: int
    second_interval: int


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


def read_fault_events(path: Path) -> list[FaultEvent]:
    if not path.exists():
        raise FileNotFoundError(path)

    events: list[FaultEvent] = []

    with path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.reader(file)

        for row in reader:
            if not row:
                continue

            if len(row) != 3:
                raise ValueError(f"Invalid fault row: {row}")

            events.append(
                FaultEvent(
                    cycle=int(row[0]),
                    address=int(row[1]),
                    mask=int(row[2], 16),
                )
            )

    if not events:
        raise ValueError(f"No fault events found in {path}")

    events.sort(key=lambda item: item.cycle)

    return events


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
                raise ValueError(f"Invalid control row: {row}")

            cycle = int(row[0])
            level = int(row[1])

            if level < 0 or level > 7:
                raise ValueError(f"Control level out of range: {level}")

            events.append(ControlEvent(cycle=cycle, level=level))

    if not events:
        raise ValueError(f"No control events found in {path}")

    events.sort(key=lambda item: item.cycle)

    if events[0].cycle != 0:
        events.insert(0, ControlEvent(cycle=0, level=0))

    return events


def level_at(events: list[ControlEvent], cycle: int) -> int:
    current = events[0].level

    for event in events:
        if event.cycle > cycle:
            break

        current = event.level

    return current


def control_level_durations(
    events: list[ControlEvent],
    total_cycles: int,
) -> dict[int, int]:
    durations = {level: 0 for level in range(8)}

    for index, event in enumerate(events):
        start = event.cycle
        end = total_cycles

        if index + 1 < len(events):
            end = events[index + 1].cycle

        if start < 0:
            start = 0

        if end > total_cycles:
            end = total_cycles

        if end > start:
            durations[event.level] += end - start

    return durations


def count_by_level(
    levels: list[int],
) -> dict[int, int]:
    counts = {level: 0 for level in range(8)}

    for level in levels:
        counts[level] += 1

    return counts


def detect_candidate_pairs(
    events: list[FaultEvent],
    control_events: list[ControlEvent],
    level_intervals: list[int],
    pair_gap_min: int,
    pair_gap_max: int,
) -> list[CandidatePair]:
    """
    Находит кандидаты накопительных пар как последовательные инжекции
    в один и тот же адрес с gap внутри [pair_gap_min, pair_gap_max].

    Это не точная разметка генератора, потому что fault_events.csv пока
    не хранит pair_id. Но это полезная проверка того, где в policy-level
    пространстве оказываются опасные повторные инжекции в один адрес.
    """
    by_addr: dict[int, list[FaultEvent]] = {}

    for event in events:
        by_addr.setdefault(event.address, []).append(event)

    pairs: list[CandidatePair] = []

    for address, addr_events in by_addr.items():
        addr_events.sort(key=lambda item: item.cycle)

        for first, second in zip(addr_events, addr_events[1:]):
            gap = second.cycle - first.cycle

            if pair_gap_min <= gap <= pair_gap_max:
                first_level = level_at(control_events, first.cycle)
                second_level = level_at(control_events, second.cycle)

                pairs.append(
                    CandidatePair(
                        address=address,
                        first_cycle=first.cycle,
                        second_cycle=second.cycle,
                        gap=gap,
                        first_level=first_level,
                        second_level=second_level,
                        max_level=max(first_level, second_level),
                        first_interval=level_intervals[first_level],
                        second_interval=level_intervals[second_level],
                    )
                )

    return pairs


def fraction(count: int, total: int) -> float:
    return count / total if total else 0.0


def write_level_alignment_csv(
    path: Path,
    total_cycles: int,
    durations: dict[int, int],
    fault_counts: dict[int, int],
    pair_first_counts: dict[int, int],
    pair_second_counts: dict[int, int],
    pair_max_counts: dict[int, int],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    total_faults = sum(fault_counts.values())
    total_pair_first = sum(pair_first_counts.values())
    total_pair_second = sum(pair_second_counts.values())
    total_pair_max = sum(pair_max_counts.values())

    fieldnames = [
        "level",
        "time_cycles",
        "time_fraction",
        "fault_count",
        "fault_fraction",
        "fault_lift_vs_time",
        "candidate_pair_first_count",
        "candidate_pair_first_fraction",
        "candidate_pair_second_count",
        "candidate_pair_second_fraction",
        "candidate_pair_max_count",
        "candidate_pair_max_fraction",
    ]

    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()

        for level in range(8):
            time_fraction = fraction(durations[level], total_cycles)
            fault_fraction = fraction(fault_counts[level], total_faults)
            lift = fault_fraction / time_fraction if time_fraction > 0.0 else 0.0

            writer.writerow(
                {
                    "level": level,
                    "time_cycles": durations[level],
                    "time_fraction": f"{time_fraction:.9f}",
                    "fault_count": fault_counts[level],
                    "fault_fraction": f"{fault_fraction:.9f}",
                    "fault_lift_vs_time": f"{lift:.6f}",
                    "candidate_pair_first_count": pair_first_counts[level],
                    "candidate_pair_first_fraction": f"{fraction(pair_first_counts[level], total_pair_first):.9f}",
                    "candidate_pair_second_count": pair_second_counts[level],
                    "candidate_pair_second_fraction": f"{fraction(pair_second_counts[level], total_pair_second):.9f}",
                    "candidate_pair_max_count": pair_max_counts[level],
                    "candidate_pair_max_fraction": f"{fraction(pair_max_counts[level], total_pair_max):.9f}",
                }
            )


def write_candidate_pairs_csv(path: Path, pairs: list[CandidatePair]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "address",
        "first_cycle",
        "second_cycle",
        "gap",
        "first_level",
        "second_level",
        "max_level",
        "first_interval",
        "second_interval",
    ]

    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()

        for pair in pairs:
            writer.writerow(
                {
                    "address": pair.address,
                    "first_cycle": pair.first_cycle,
                    "second_cycle": pair.second_cycle,
                    "gap": pair.gap,
                    "first_level": pair.first_level,
                    "second_level": pair.second_level,
                    "max_level": pair.max_level,
                    "first_interval": pair.first_interval,
                    "second_interval": pair.second_interval,
                }
            )


def weighted_mean_level(level_counts: dict[int, int]) -> float:
    total = sum(level_counts.values())

    if total == 0:
        return 0.0

    return sum(level * count for level, count in level_counts.items()) / total


def write_markdown(
    path: Path,
    total_cycles: int,
    fault_events: list[FaultEvent],
    durations: dict[int, int],
    fault_counts: dict[int, int],
    pairs: list[CandidatePair],
    pair_first_counts: dict[int, int],
    pair_second_counts: dict[int, int],
    pair_max_counts: dict[int, int],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    total_faults = len(fault_events)
    cluster_like = sum(1 for event in fault_events if event.mask.bit_count() > 1)

    mean_time_level = (
        sum(level * duration for level, duration in durations.items()) / total_cycles
        if total_cycles > 0
        else 0.0
    )
    mean_fault_level = weighted_mean_level(fault_counts)
    mean_pair_first_level = weighted_mean_level(pair_first_counts)
    mean_pair_second_level = weighted_mean_level(pair_second_counts)
    mean_pair_max_level = weighted_mean_level(pair_max_counts)

    pair_gaps = [pair.gap for pair in pairs]
    mean_pair_gap = mean(pair_gaps) if pair_gaps else 0.0

    high_time_fraction = sum(durations[level] for level in range(2, 8)) / total_cycles
    high_fault_fraction = sum(fault_counts[level] for level in range(2, 8)) / total_faults

    pair_total = len(pairs)
    high_pair_first_fraction = (
        sum(pair_first_counts[level] for level in range(2, 8)) / pair_total
        if pair_total
        else 0.0
    )
    high_pair_second_fraction = (
        sum(pair_second_counts[level] for level in range(2, 8)) / pair_total
        if pair_total
        else 0.0
    )

    lines: list[str] = []

    lines.append("# Аудит согласования fault stream и risk-policy")
    lines.append("")
    lines.append("## Назначение")
    lines.append("")
    lines.append(
        "Проверяется, насколько сгенерированные сбойные события и кандидаты "
        "накопительных пар статистически попадают в уровни управляющей "
        "risk-policy. Если события не концентрируются в повышенных уровнях, "
        "адаптивная стратегия не обязана давать выигрыш относительно fixed."
    )
    lines.append("")
    lines.append("## Общая сводка")
    lines.append("")
    lines.append(f"- Всего модельных тактов: {total_cycles}")
    lines.append(f"- Всего fault injections: {total_faults}")
    lines.append(f"- Cluster-like events по маске > 1 bit: {cluster_like}")
    lines.append(f"- Кандидатов накопительных пар: {pair_total}")
    lines.append(f"- Средний gap кандидатных пар: {mean_pair_gap:.3f} cycles")
    lines.append("")
    lines.append("## Средние уровни")
    lines.append("")
    lines.append(f"- Средний уровень по времени: {mean_time_level:.3f}")
    lines.append(f"- Средний уровень по всем fault events: {mean_fault_level:.3f}")
    lines.append(f"- Средний уровень первых событий candidate pairs: {mean_pair_first_level:.3f}")
    lines.append(f"- Средний уровень вторых событий candidate pairs: {mean_pair_second_level:.3f}")
    lines.append(f"- Средний max-level candidate pairs: {mean_pair_max_level:.3f}")
    lines.append("")
    lines.append("## Верхние уровни policy")
    lines.append("")
    lines.append(f"- Доля времени на level >= 2: {100.0 * high_time_fraction:.3f} %")
    lines.append(f"- Доля всех fault events на level >= 2: {100.0 * high_fault_fraction:.3f} %")
    lines.append(f"- Доля первых событий candidate pairs на level >= 2: {100.0 * high_pair_first_fraction:.3f} %")
    lines.append(f"- Доля вторых событий candidate pairs на level >= 2: {100.0 * high_pair_second_fraction:.3f} %")
    lines.append("")
    lines.append("## Распределение по уровням")
    lines.append("")
    lines.append(
        "| level | time % | fault count | fault % | lift fault/time | "
        "pair first | pair second | pair max |"
    )
    lines.append("|---:|---:|---:|---:|---:|---:|---:|---:|")

    total_pair_first = sum(pair_first_counts.values())
    total_pair_second = sum(pair_second_counts.values())
    total_pair_max = sum(pair_max_counts.values())

    for level in range(8):
        time_fraction = fraction(durations[level], total_cycles)
        fault_fraction = fraction(fault_counts[level], total_faults)
        lift = fault_fraction / time_fraction if time_fraction > 0 else 0.0

        lines.append(
            f"| {level} "
            f"| {100.0 * time_fraction:.3f} "
            f"| {fault_counts[level]} "
            f"| {100.0 * fault_fraction:.3f} "
            f"| {lift:.3f} "
            f"| {pair_first_counts[level]} ({100.0 * fraction(pair_first_counts[level], total_pair_first):.2f} %) "
            f"| {pair_second_counts[level]} ({100.0 * fraction(pair_second_counts[level], total_pair_second):.2f} %) "
            f"| {pair_max_counts[level]} ({100.0 * fraction(pair_max_counts[level], total_pair_max):.2f} %) |"
        )

    lines.append("")
    lines.append("## Интерпретация")
    lines.append("")
    lines.append(
        "Так как текущий `fault_events.csv` не хранит исходный `pair_id`, "
        "кандидаты накопительных пар определяются как последовательные инжекции "
        "в один и тот же адрес с gap внутри заданного диапазона. Это не точная "
        "разметка генератора, но достаточная статистическая проверка того, "
        "попадают ли потенциально опасные повторные инжекции в повышенные уровни policy."
    )
    lines.append("")

    if mean_fault_level > mean_time_level:
        lines.append(
            "**PASS (statistical):** fault events в среднем смещены в более высокие "
            "уровни risk-policy, чем случайно выбранный момент времени."
        )
    else:
        lines.append(
            "**WARNING:** fault events не смещены в повышенные уровни risk-policy. "
            "В такой постановке adaptive strategy может не получать ожидаемый выигрыш."
        )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit statistical alignment between fault events and risk-policy levels."
    )

    parser.add_argument("--fault-events", type=Path, required=True)
    parser.add_argument("--control-levels", type=Path, required=True)
    parser.add_argument("--total-cycles", type=int, required=True)
    parser.add_argument("--pair-gap-min", type=int, required=True)
    parser.add_argument("--pair-gap-max", type=int, required=True)
    parser.add_argument("--level-intervals", required=True)
    parser.add_argument("--summary-csv", type=Path, required=True)
    parser.add_argument("--pairs-csv", type=Path, required=True)
    parser.add_argument("--md-output", type=Path, required=True)

    args = parser.parse_args()

    if args.total_cycles <= 0:
        raise ValueError("total-cycles must be positive")

    if args.pair_gap_min <= 0:
        raise ValueError("pair-gap-min must be positive")

    if args.pair_gap_max < args.pair_gap_min:
        raise ValueError("pair-gap-max must be >= pair-gap-min")

    level_intervals = parse_int_list(
        args.level_intervals,
        expected_count=8,
        name="level-intervals",
    )

    fault_events = read_fault_events(args.fault_events)
    control_events = read_control_events(args.control_levels)

    durations = control_level_durations(
        events=control_events,
        total_cycles=args.total_cycles,
    )

    fault_levels = [
        level_at(control_events, event.cycle)
        for event in fault_events
    ]

    fault_counts = count_by_level(fault_levels)

    pairs = detect_candidate_pairs(
        events=fault_events,
        control_events=control_events,
        level_intervals=level_intervals,
        pair_gap_min=args.pair_gap_min,
        pair_gap_max=args.pair_gap_max,
    )

    pair_first_counts = count_by_level([pair.first_level for pair in pairs])
    pair_second_counts = count_by_level([pair.second_level for pair in pairs])
    pair_max_counts = count_by_level([pair.max_level for pair in pairs])

    write_level_alignment_csv(
        path=args.summary_csv,
        total_cycles=args.total_cycles,
        durations=durations,
        fault_counts=fault_counts,
        pair_first_counts=pair_first_counts,
        pair_second_counts=pair_second_counts,
        pair_max_counts=pair_max_counts,
    )

    write_candidate_pairs_csv(
        path=args.pairs_csv,
        pairs=pairs,
    )

    write_markdown(
        path=args.md_output,
        total_cycles=args.total_cycles,
        fault_events=fault_events,
        durations=durations,
        fault_counts=fault_counts,
        pairs=pairs,
        pair_first_counts=pair_first_counts,
        pair_second_counts=pair_second_counts,
        pair_max_counts=pair_max_counts,
    )

    print(f"Fault-policy alignment summary: {args.md_output}")
    print(f"Level alignment CSV: {args.summary_csv}")
    print(f"Candidate pairs CSV: {args.pairs_csv}")


if __name__ == "__main__":
    main()
#!/usr/bin/env python3

from __future__ import annotations

import argparse
import math
import random
from pathlib import Path

from upsets_series import load_full_upsets_series


CODEWORD_WIDTH = 39
ADDR_WIDTH = 4
DEPTH = 1 << ADDR_WIDTH

DEFAULT_TOTAL_CYCLES = 1300


FaultEvent = tuple[int, int, int]

def bit_to_mask(bit_index: int) -> int:
    if bit_index < 0 or bit_index >= CODEWORD_WIDTH:
        raise ValueError(
            f"bit_index={bit_index} is outside codeword width {CODEWORD_WIDTH}"
        )

    return 1 << bit_index

def random_distinct_bit_mask(
    rng: random.Random,
    bit_count: int,
) -> int:
    """
    Формирует маску из bit_count различных битов кодового слова.

    bit_count = 1 соответствует одиночной ошибке.
    bit_count = 2 соответствует мгновенному двухбитовому кластеру.
    """
    if bit_count <= 0:
        raise ValueError("bit_count must be positive")

    if bit_count > CODEWORD_WIDTH:
        raise ValueError(
            f"bit_count={bit_count} exceeds codeword width {CODEWORD_WIDTH}"
        )

    selected_bits = rng.sample(range(CODEWORD_WIDTH), bit_count)

    mask = 0
    for bit_index in selected_bits:
        mask |= bit_to_mask(bit_index)

    return mask

ControlLevelEvent = tuple[int, int]

def baseline_events() -> list[FaultEvent]:
    """
    Базовый детерминированный сценарий сбойных событий.

    Формат события:
        модельный такт, адрес слова, битовая маска кодового слова.

    Для одиночной ошибки маска содержит ровно один установленный бит.
    """
    return [
        (120, 3, bit_to_mask(5)),
        (260, 7, bit_to_mask(10)),
        (430, 0, bit_to_mask(2)),
        (450, 0, bit_to_mask(4)),
        (740, 5, bit_to_mask(9)),
        (760, 5, bit_to_mask(14)),
        (980, 9, bit_to_mask(1)),
        (1120, 2, bit_to_mask(20)),
    ]

def baseline_control_levels() -> list[ControlLevelEvent]:
    """
    Базовый детерминированный сценарий управляющего уровня.

    Формат события:
        модельный такт, дискретный уровень сбойной обстановки.

    Этот сценарий соответствует прежнему ручному расписанию
    в tb_strategy_comparison.v.
    """
    return [
        (0, 0),
        (200, 2),
        (400, 6),
        (700, 7),
        (900, 4),
        (1100, 1),
    ]

def read_upsets_xlsx(input_path: Path) -> list[float]:
    """
    Backward-compatible wrapper.

    Возвращает полный ряд ν(t), восстановленный из протонной составляющей
    data/upsets.xlsx с учётом ТЗЧ по формуле статьи 3.

    Важно:
        до шага 3.30 эта функция возвращала только протонную составляющую νp(t).
        Теперь все upsets-based эксперименты используют полный ряд ν(t).
    """
    return load_full_upsets_series(input_path)


def select_window(
    values: list[float],
    start_index: int,
    window_size: int,
) -> list[float]:
    if start_index < 0:
        raise ValueError("start_index must be non-negative")

    if window_size <= 0:
        raise ValueError("window_size must be positive")

    end_index = start_index + window_size

    if end_index > len(values):
        raise ValueError(
            f"Requested window [{start_index}, {end_index}) exceeds "
            f"available series length {len(values)}"
        )

    return values[start_index:end_index]

def quantize_upset_value(value: float, max_value: float) -> int:
    """
    Преобразует значение временного ряда upsets(t)
    в дискретный управляющий уровень 0...7.

    Это простая нормированная аппроксимация:
        0 соответствует нулевой или минимальной сбойной обстановке;
        7 соответствует максимуму выбранного окна.
    """
    if max_value <= 0.0:
        return 0

    normalized = value / max_value

    if normalized < 0.0:
        normalized = 0.0

    if normalized > 1.0:
        normalized = 1.0

    level = int(round(7.0 * normalized))

    if level < 0:
        return 0

    if level > 7:
        return 7

    return level


def control_levels_from_upsets(
    input_path: Path,
    start_index: int,
    window_size: int,
    total_cycles: int,
) -> list[ControlLevelEvent]:
    """
    Формирует поток управляющих уровней из того же окна upsets(t),
    которое используется для генерации сбойных событий.

    На выходе создаются только моменты изменения уровня, а не строка
    на каждый такт моделирования.
    """
    if total_cycles <= 0:
        raise ValueError("total_cycles must be positive")

    values = read_upsets_xlsx(input_path)
    window = select_window(values, start_index, window_size)

    max_value = max(window) if window else 0.0

    events: list[ControlLevelEvent] = []
    previous_level: int | None = None

    for index, value in enumerate(window):
        cycle = (index * total_cycles) // len(window)

        if cycle >= total_cycles:
            cycle = total_cycles - 1

        level = quantize_upset_value(value, max_value)

        if previous_level is None or level != previous_level:
            events.append((cycle, level))
            previous_level = level

    if not events or events[0][0] != 0:
        events.insert(0, (0, 0))

    return events

def weighted_cycle_from_series(
    rng: random.Random,
    weights: list[float],
    total_cycles: int,
) -> int:
    """
    Выбирает такт моделирования с вероятностью,
    пропорциональной значению временного ряда.
    """
    total_weight = sum(weights)

    if total_weight <= 0.0:
        hour_index = rng.randrange(len(weights))
    else:
        threshold = rng.random() * total_weight
        cumulative = 0.0
        hour_index = 0

        for index, weight in enumerate(weights):
            cumulative += weight
            if cumulative >= threshold:
                hour_index = index
                break

    cycle_start = (hour_index * total_cycles) // len(weights)
    cycle_end = ((hour_index + 1) * total_cycles) // len(weights)

    if cycle_end <= cycle_start:
        cycle_end = cycle_start + 1

    cycle = rng.randrange(cycle_start, cycle_end)

    if cycle >= total_cycles:
        cycle = total_cycles - 1

    return cycle


def find_free_cycle_near(
    preferred_cycle: int,
    used_cycles: set[int],
    total_cycles: int,
) -> int:
    """
    Находит ближайший свободный такт к preferred_cycle.
    Это нужно, потому что текущий Verilog-стенд поддерживает
    не более одного события на один такт.
    """
    if preferred_cycle < 0:
        preferred_cycle = 0

    if preferred_cycle >= total_cycles:
        preferred_cycle = total_cycles - 1

    if preferred_cycle not in used_cycles:
        return preferred_cycle

    for distance in range(1, total_cycles):
        right = preferred_cycle + distance
        left = preferred_cycle - distance

        if right < total_cycles and right not in used_cycles:
            return right

        if left >= 0 and left not in used_cycles:
            return left

    raise ValueError("No free simulation cycle is available")


def add_single_events(
    events: list[FaultEvent],
    used_cycles: set[int],
    rng: random.Random,
    weights: list[float],
    total_cycles: int,
    event_count: int,
) -> None:
    for _ in range(event_count):
        preferred_cycle = weighted_cycle_from_series(rng, weights, total_cycles)
        cycle = find_free_cycle_near(preferred_cycle, used_cycles, total_cycles)

        used_cycles.add(cycle)

        address = rng.randrange(DEPTH)
        bit_index = rng.randrange(CODEWORD_WIDTH)
        fault_mask = bit_to_mask(bit_index)

        events.append((cycle, address, fault_mask))


def add_paired_events(
    events: list[FaultEvent],
    used_cycles: set[int],
    rng: random.Random,
    weights: list[float],
    total_cycles: int,
    paired_event_count: int,
    pair_gap_min: int,
    pair_gap_max: int,
) -> None:
    """
    Добавляет парные события в одно слово памяти.

    Каждая пара имеет вид:
        t,      address A, bit b1
        t+gap,  address A, bit b2

    Если скраббинг успевает пройти слово A между этими событиями,
    первая ошибка исправляется. Если не успевает, в слове накапливаются
    две ошибки и SECDED фиксирует неустранимое состояние.
    """
    if paired_event_count < 0:
        raise ValueError("paired_event_count must be non-negative")

    if pair_gap_min <= 0:
        raise ValueError("pair_gap_min must be positive")

    if pair_gap_max < pair_gap_min:
        raise ValueError("pair_gap_max must be >= pair_gap_min")

    for pair_index in range(paired_event_count):
        placed = False

        for _attempt in range(1000):
            gap = rng.randint(pair_gap_min, pair_gap_max)

            if gap >= total_cycles:
                raise ValueError("pair gap must be smaller than total_cycles")

            preferred_first = weighted_cycle_from_series(rng, weights, total_cycles)

            if preferred_first + gap >= total_cycles:
                preferred_first = total_cycles - 1 - gap

            first_cycle = preferred_first
            second_cycle = first_cycle + gap

            if first_cycle < 0:
                first_cycle = 0
                second_cycle = first_cycle + gap

            if (
                first_cycle != second_cycle
                and first_cycle not in used_cycles
                and second_cycle not in used_cycles
                and 0 <= first_cycle < total_cycles
                and 0 <= second_cycle < total_cycles
            ):
                address = rng.randrange(DEPTH)

                first_bit = rng.randrange(CODEWORD_WIDTH)
                second_bit = rng.randrange(CODEWORD_WIDTH)

                while second_bit == first_bit:
                    second_bit = rng.randrange(CODEWORD_WIDTH)

                used_cycles.add(first_cycle)
                used_cycles.add(second_cycle)

                events.append((first_cycle, address, bit_to_mask(first_bit)))
                events.append((second_cycle, address, bit_to_mask(second_bit)))

                placed = True
                break

        if not placed:
            raise ValueError(
                f"Could not place paired event {pair_index}. "
                "Try reducing paired_event_count or gap range."
            )


def add_instant_cluster_events(
    events: list[FaultEvent],
    used_cycles: set[int],
    rng: random.Random,
    weights: list[float],
    total_cycles: int,
    cluster_event_count: int,
    cluster_bit_count: int,
) -> None:
    """
    Добавляет мгновенные кластерные события.

    Каждое событие имеет вид:
        t, address A, mask

    В отличие от накопительной пары, здесь несколько битов
    одного кодового слова повреждаются в один и тот же модельный такт.
    """
    if cluster_event_count < 0:
        raise ValueError("cluster_event_count must be non-negative")

    if cluster_bit_count <= 1:
        raise ValueError("cluster_bit_count must be greater than 1")

    if cluster_bit_count > CODEWORD_WIDTH:
        raise ValueError(
            f"cluster_bit_count={cluster_bit_count} exceeds "
            f"codeword width {CODEWORD_WIDTH}"
        )

    for _ in range(cluster_event_count):
        preferred_cycle = weighted_cycle_from_series(rng, weights, total_cycles)
        cycle = find_free_cycle_near(preferred_cycle, used_cycles, total_cycles)

        used_cycles.add(cycle)

        address = rng.randrange(DEPTH)
        fault_mask = random_distinct_bit_mask(rng, cluster_bit_count)

        events.append((cycle, address, fault_mask))

def upsets_weighted_events(
    input_path: Path,
    start_index: int,
    window_size: int,
    total_cycles: int,
    event_count: int,
    paired_event_count: int,
    pair_gap_min: int,
    pair_gap_max: int,
    cluster_event_count: int,
    cluster_bit_count: int,
    seed: int,
) -> list[FaultEvent]:
    """
    Генерирует поток сбойных событий из временного ряда upsets(t).

    Модель:
        - event_count одиночных событий;
        - paired_event_count накопительных пар;
        - cluster_event_count мгновенных кластерных событий;
        - моменты событий выбираются с вероятностью,
          пропорциональной upsets(t);
        - адреса выбираются равномерно;
        - в накопительной паре оба события относятся к одному адресу;
        - в мгновенном кластере несколько битов одного слова
          повреждаются в один модельный такт.
    """
    if total_cycles <= 0:
        raise ValueError("total_cycles must be positive")

    if event_count < 0:
        raise ValueError("event_count must be non-negative")

    total_injections = event_count + 2 * paired_event_count + cluster_event_count

    if total_injections > total_cycles:
        raise ValueError(
            f"Too many injections: {total_injections} for "
            f"total_cycles={total_cycles}"
        )

    values = read_upsets_xlsx(input_path)
    window = select_window(values, start_index, window_size)

    rng = random.Random(seed)

    used_cycles: set[int] = set()
    events: list[FaultEvent] = []

    add_single_events(
        events=events,
        used_cycles=used_cycles,
        rng=rng,
        weights=window,
        total_cycles=total_cycles,
        event_count=event_count,
    )

    add_paired_events(
        events=events,
        used_cycles=used_cycles,
        rng=rng,
        weights=window,
        total_cycles=total_cycles,
        paired_event_count=paired_event_count,
        pair_gap_min=pair_gap_min,
        pair_gap_max=pair_gap_max,
    )

    add_instant_cluster_events(
        events=events,
        used_cycles=used_cycles,
        rng=rng,
        weights=window,
        total_cycles=total_cycles,
        cluster_event_count=cluster_event_count,
        cluster_bit_count=cluster_bit_count,
    )

    events.sort(key=lambda item: item[0])
    return events


def validate_events(events: list[FaultEvent], total_cycles: int | None = None) -> None:
    previous_time = -1
    used_times: set[int] = set()

    for index, (time_cycle, address, fault_mask) in enumerate(events):
        if time_cycle < 0:
            raise ValueError(f"Event {index}: negative time_cycle={time_cycle}")

        if total_cycles is not None and time_cycle >= total_cycles:
            raise ValueError(
                f"Event {index}: time_cycle={time_cycle} is outside "
                f"total_cycles={total_cycles}"
            )

        if time_cycle < previous_time:
            raise ValueError(
                f"Event {index}: events must be sorted by time "
                f"({time_cycle} after {previous_time})"
            )

        if time_cycle in used_times:
            raise ValueError(
                f"Event {index}: more than one event in cycle {time_cycle} "
                "is not supported by the current Verilog testbench"
            )

        if address < 0 or address >= DEPTH:
            raise ValueError(
                f"Event {index}: address={address} is outside memory depth {DEPTH}"
            )

        if fault_mask <= 0:
            raise ValueError(f"Event {index}: fault_mask must be non-zero")

        if fault_mask >= (1 << CODEWORD_WIDTH):
            raise ValueError(
                f"Event {index}: fault_mask=0x{fault_mask:x} exceeds "
                f"codeword width {CODEWORD_WIDTH}"
            )

        used_times.add(time_cycle)
        previous_time = time_cycle


def validate_control_levels(
    events: list[ControlLevelEvent],
    total_cycles: int | None = None,
) -> None:
    previous_time = -1

    for index, (time_cycle, level) in enumerate(events):
        if time_cycle < 0:
            raise ValueError(f"Control event {index}: negative time_cycle={time_cycle}")

        if total_cycles is not None and time_cycle >= total_cycles:
            raise ValueError(
                f"Control event {index}: time_cycle={time_cycle} is outside "
                f"total_cycles={total_cycles}"
            )

        if time_cycle < previous_time:
            raise ValueError(
                f"Control event {index}: events must be sorted by time "
                f"({time_cycle} after {previous_time})"
            )

        if level < 0 or level > 7:
            raise ValueError(
                f"Control event {index}: level={level} is outside range 0...7"
            )

        previous_time = time_cycle

def write_events(events: list[FaultEvent], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8", newline="\n") as file:
        for time_cycle, address, fault_mask in events:
            file.write(f"{time_cycle},{address},{fault_mask:010x}\n")


def write_control_levels(
    events: list[ControlLevelEvent],
    output_path: Path,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8", newline="\n") as file:
        for time_cycle, level in events:
            file.write(f"{time_cycle},{level}\n")

def print_summary(
    events: list[FaultEvent],
    scenario: str,
    paired_event_count: int,
) -> None:
    address_counts: dict[int, int] = {}

    for _time_cycle, address, _bit_index in events:
        address_counts[address] = address_counts.get(address, 0) + 1

    repeated_addresses = sum(1 for count in address_counts.values() if count >= 2)

    print(f"Generated {len(events)} fault injections")
    print(f"Scenario: {scenario}")
    print(f"Paired events: {paired_event_count}")
    print(f"Addresses with repeated injections: {repeated_addresses}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate fault event table for strategy comparison."
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=Path("tb/fault_events.csv"),
        help="Output CSV file without header. Default: tb/fault_events.csv",
    )

    parser.add_argument(
        "--control-output",
        type=Path,
        default=Path("tb/control_levels.csv"),
        help="Output control-level CSV file without header. Default: tb/control_levels.csv",
    )


    parser.add_argument(
        "--scenario",
        choices=["baseline", "upsets"],
        default="baseline",
        help="Fault event scenario.",
    )

    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/upsets.xlsx"),
        help="Input Excel file for --scenario upsets.",
    )

    parser.add_argument(
        "--start-index",
        type=int,
        default=0,
        help="Start index in the upsets time series.",
    )

    parser.add_argument(
        "--window-size",
        type=int,
        default=1300,
        help="Number of time-series points used for upsets-based generation.",
    )

    parser.add_argument(
        "--total-cycles",
        type=int,
        default=DEFAULT_TOTAL_CYCLES,
        help="Total simulation cycles.",
    )

    parser.add_argument(
        "--event-count",
        type=int,
        default=8,
        help="Number of single generated fault events for --scenario upsets.",
    )

    parser.add_argument(
        "--paired-event-count",
        type=int,
        default=0,
        help=(
            "Number of paired events for --scenario upsets. "
            "Each pair creates two injections in the same memory word."
        ),
    )

    parser.add_argument(
        "--cluster-event-count",
        type=int,
        default=0,
        help=(
            "Number of instantaneous cluster events for --scenario upsets. "
            "Each cluster creates one mask-based injection."
        ),
    )

    parser.add_argument(
        "--cluster-bit-count",
        type=int,
        default=2,
        help="Number of flipped bits in each instantaneous cluster.",
    )

    parser.add_argument(
        "--pair-gap-min",
        type=int,
        default=10,
        help="Minimum cycle distance between two injections in a pair.",
    )

    parser.add_argument(
        "--pair-gap-max",
        type=int,
        default=80,
        help="Maximum cycle distance between two injections in a pair.",
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=12345,
        help="Random seed for reproducible event generation.",
    )

    args = parser.parse_args()

    if args.scenario == "baseline":
        events = baseline_events()
        control_events = baseline_control_levels()

        validate_events(events, total_cycles=args.total_cycles)
        validate_control_levels(control_events, total_cycles=args.total_cycles)

    elif args.scenario == "upsets":
        events = upsets_weighted_events(
            input_path=args.input,
            start_index=args.start_index,
            window_size=args.window_size,
            total_cycles=args.total_cycles,
            event_count=args.event_count,
            paired_event_count=args.paired_event_count,
            pair_gap_min=args.pair_gap_min,
            pair_gap_max=args.pair_gap_max,
            cluster_event_count=args.cluster_event_count,
            cluster_bit_count=args.cluster_bit_count,
            seed=args.seed,
        )

        control_events = control_levels_from_upsets(
            input_path=args.input,
            start_index=args.start_index,
            window_size=args.window_size,
            total_cycles=args.total_cycles,
        )

        validate_events(events, total_cycles=args.total_cycles)
        validate_control_levels(control_events, total_cycles=args.total_cycles)

    else:
        raise ValueError(f"Unsupported scenario: {args.scenario}")

    write_events(events, args.output)
    write_control_levels(control_events, args.control_output)

    print(f"Generated fault events: {args.output}")
    print(f"Generated control levels: {args.control_output}")
    print(f"Control level changes: {len(control_events)}")
    print_summary(
        events=events,
        scenario=args.scenario,
        paired_event_count=args.paired_event_count if args.scenario == "upsets" else 0,
    )

    if args.scenario == "upsets":
        print(f"Input: {args.input}")
        print(f"Start index: {args.start_index}")
        print(f"Window size: {args.window_size}")
        print(f"Total cycles: {args.total_cycles}")
        print(f"Single events: {args.event_count}")
        print(f"Paired events: {args.paired_event_count}")
        print(f"Cluster events: {args.cluster_event_count}")
        print(f"Cluster bit count: {args.cluster_bit_count}")
        print(f"Seed: {args.seed}")


if __name__ == "__main__":
    main()
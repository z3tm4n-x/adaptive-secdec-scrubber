#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path


CODEWORD_WIDTH = 39
ADDR_WIDTH = 4
DEPTH = 1 << ADDR_WIDTH


def baseline_events() -> list[tuple[int, int, int]]:
    """
    Базовый детерминированный сценарий сбойных событий.

    Формат события:
        модельный такт, адрес слова, номер бита в кодовом слове.

    В сценарии есть:
        - одиночные ошибки;
        - пары ошибок в одном слове;
        - события на фоне, росте, максимуме и спаде сбойной обстановки.
    """
    return [
        (120, 3, 5),
        (260, 7, 10),
        (430, 0, 2),
        (450, 0, 4),
        (740, 5, 9),
        (760, 5, 14),
        (980, 9, 1),
        (1120, 2, 20),
    ]


def validate_events(events: list[tuple[int, int, int]]) -> None:
    previous_time = -1

    for index, (time_cycle, address, bit_index) in enumerate(events):
        if time_cycle < 0:
            raise ValueError(f"Event {index}: negative time_cycle={time_cycle}")

        if time_cycle < previous_time:
            raise ValueError(
                f"Event {index}: events must be sorted by time "
                f"({time_cycle} after {previous_time})"
            )

        if address < 0 or address >= DEPTH:
            raise ValueError(
                f"Event {index}: address={address} is outside memory depth {DEPTH}"
            )

        if bit_index < 0 or bit_index >= CODEWORD_WIDTH:
            raise ValueError(
                f"Event {index}: bit_index={bit_index} is outside "
                f"codeword width {CODEWORD_WIDTH}"
            )

        previous_time = time_cycle


def write_events(events: list[tuple[int, int, int]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8", newline="\n") as file:
        for time_cycle, address, bit_index in events:
            file.write(f"{time_cycle},{address},{bit_index}\n")


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
        "--scenario",
        choices=["baseline"],
        default="baseline",
        help="Fault event scenario.",
    )

    args = parser.parse_args()

    if args.scenario == "baseline":
        events = baseline_events()
    else:
        raise ValueError(f"Unsupported scenario: {args.scenario}")

    validate_events(events)
    write_events(events, args.output)

    print(f"Generated {len(events)} fault events: {args.output}")


if __name__ == "__main__":
    main()
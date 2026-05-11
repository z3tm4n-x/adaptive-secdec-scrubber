#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import re
from dataclasses import dataclass
from pathlib import Path


METRIC_PATTERNS = {
    "wires": re.compile(r"Number of wires:\s+(\d+)"),
    "wire_bits": re.compile(r"Number of wire bits:\s+(\d+)"),
    "public_wires": re.compile(r"Number of public wires:\s+(\d+)"),
    "public_wire_bits": re.compile(r"Number of public wire bits:\s+(\d+)"),
    "memories": re.compile(r"Number of memories:\s+(\d+)"),
    "cells": re.compile(r"Number of cells:\s+(\d+)"),
}


@dataclass(frozen=True)
class SynthesisCase:
    name: str
    addr_width: int
    log_path: Path


@dataclass
class SynthesisMetrics:
    name: str
    addr_width: int
    memory_words: int
    information_bits_mbit: float
    codeword_bits_mbit: float
    wires: int
    wire_bits: int
    public_wires: int
    public_wire_bits: int
    memories: int
    cells: int


def default_cases() -> list[SynthesisCase]:
    return [
        SynthesisCase(
            name="adaptive_aw4",
            addr_width=4,
            log_path=Path("results/logs/adaptive_scrub_controller_synth.log"),
        ),
        SynthesisCase(
            name="adaptive_aw21",
            addr_width=21,
            log_path=Path("results/logs/adaptive_scrub_controller_aw21_synth.log"),
        ),
    ]


def extract_last_stat_block(log_path: Path) -> dict[str, int]:
    """
    Извлекает последний полный блок статистики Yosys.

    В журнале Yosys статистика может печататься несколько раз:
    по отдельным модулям и затем по всей иерархии. Для сводной
    таблицы нужен последний полный блок с метриками.
    """
    if not log_path.exists():
        raise FileNotFoundError(f"Synthesis log not found: {log_path}")

    text = log_path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    blocks: list[dict[str, int]] = []
    current: dict[str, int] = {}

    for line in lines:
        for metric_name, pattern in METRIC_PATTERNS.items():
            match = pattern.search(line)

            if match is None:
                continue

            current[metric_name] = int(match.group(1))

            if set(current.keys()) == set(METRIC_PATTERNS.keys()):
                blocks.append(current)
                current = {}

            break

    if not blocks:
        raise ValueError(f"No complete Yosys statistics block found in {log_path}")

    return blocks[-1]


def metrics_from_case(case: SynthesisCase) -> SynthesisMetrics:
    raw = extract_last_stat_block(case.log_path)

    memory_words = 1 << case.addr_width
    information_bits_mbit = memory_words * 32 / 1_000_000
    codeword_bits_mbit = memory_words * 39 / 1_000_000

    return SynthesisMetrics(
        name=case.name,
        addr_width=case.addr_width,
        memory_words=memory_words,
        information_bits_mbit=information_bits_mbit,
        codeword_bits_mbit=codeword_bits_mbit,
        wires=raw["wires"],
        wire_bits=raw["wire_bits"],
        public_wires=raw["public_wires"],
        public_wire_bits=raw["public_wire_bits"],
        memories=raw["memories"],
        cells=raw["cells"],
    )


def percent_change(value: int, reference: int) -> float:
    if reference == 0:
        return 0.0

    return 100.0 * (value - reference) / reference


def write_csv(metrics: list[SynthesisMetrics], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    baseline = metrics[0]

    with output_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)

        writer.writerow(
            [
                "configuration",
                "addr_width",
                "memory_words",
                "information_bits_mbit",
                "codeword_bits_mbit",
                "wires",
                "wire_bits",
                "public_wires",
                "public_wire_bits",
                "memories",
                "cells",
                "cells_delta_vs_baseline",
                "cells_change_percent_vs_baseline",
                "wire_bits_delta_vs_baseline",
                "wire_bits_change_percent_vs_baseline",
            ]
        )

        for item in metrics:
            writer.writerow(
                [
                    item.name,
                    item.addr_width,
                    item.memory_words,
                    f"{item.information_bits_mbit:.6f}",
                    f"{item.codeword_bits_mbit:.6f}",
                    item.wires,
                    item.wire_bits,
                    item.public_wires,
                    item.public_wire_bits,
                    item.memories,
                    item.cells,
                    item.cells - baseline.cells,
                    f"{percent_change(item.cells, baseline.cells):.3f}",
                    item.wire_bits - baseline.wire_bits,
                    f"{percent_change(item.wire_bits, baseline.wire_bits):.3f}",
                ]
            )


def write_markdown(metrics: list[SynthesisMetrics], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    baseline = metrics[0]

    lines: list[str] = []

    lines.append("# Сводка технологически независимого синтеза")
    lines.append("")
    lines.append(
        "В таблице приведена статистика Yosys для адаптивного контроллера "
        "скраббинга памяти. Синтезируется только управляющая логика; "
        "массив памяти не входит в синтезируемую область."
    )
    lines.append("")

    lines.append(
        "| Конфигурация | ADDR_WIDTH | Слов памяти | "
        "Информационный объём, Мбит | Кодированный объём, Мбит | "
        "Wires | Wire bits | Public wire bits | Memories | Cells | "
        "Рост cells к базовой | Рост wire bits к базовой |"
    )
    lines.append(
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    )

    for item in metrics:
        cells_delta = item.cells - baseline.cells
        cells_change = percent_change(item.cells, baseline.cells)
        wire_bits_delta = item.wire_bits - baseline.wire_bits
        wire_bits_change = percent_change(item.wire_bits, baseline.wire_bits)

        lines.append(
            f"| `{item.name}` "
            f"| {item.addr_width} "
            f"| {item.memory_words} "
            f"| {item.information_bits_mbit:.3f} "
            f"| {item.codeword_bits_mbit:.3f} "
            f"| {item.wires} "
            f"| {item.wire_bits} "
            f"| {item.public_wire_bits} "
            f"| {item.memories} "
            f"| {item.cells} "
            f"| {cells_delta:+d} ({cells_change:+.2f} %) "
            f"| {wire_bits_delta:+d} ({wire_bits_change:+.2f} %) |"
        )

    lines.append("")
    lines.append("## Интерпретация")
    lines.append("")

    if len(metrics) >= 2:
        base = metrics[0]
        large = metrics[1]

        word_growth = large.memory_words / base.memory_words
        cells_change = percent_change(large.cells, base.cells)

        lines.append(
            f"При переходе от `ADDR_WIDTH={base.addr_width}` "
            f"к `ADDR_WIDTH={large.addr_width}` адресное пространство "
            f"увеличивается в {word_growth:.0f} раз "
            f"({base.memory_words} → {large.memory_words} слов)."
        )
        lines.append("")
        lines.append(
            f"При этом число логических ячеек возрастает "
            f"с {base.cells} до {large.cells}, то есть на {cells_change:.2f} %. "
            "Это показывает, что стоимость контроллера слабо зависит "
            "от глубины защищаемой памяти, поскольку память рассматривается "
            "как внешний массив, а рост определяется в основном шириной "
            "адресного счётчика, адресных портов и логикой сравнения конца прохода."
        )
        lines.append("")
        lines.append(
            f"В обеих конфигурациях `Number of memories = {large.memories}`, "
            "что подтверждает отсутствие синтезируемого массива памяти "
            "в рассматриваемой области."
        )

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract Yosys synthesis statistics and create summary tables."
    )

    parser.add_argument(
        "--csv-output",
        type=Path,
        default=Path("results/tables/synthesis_summary.csv"),
        help="Output CSV summary.",
    )

    parser.add_argument(
        "--md-output",
        type=Path,
        default=Path("results/tables/synthesis_summary.md"),
        help="Output Markdown summary.",
    )

    args = parser.parse_args()

    cases = default_cases()
    metrics = [metrics_from_case(case) for case in cases]

    write_csv(metrics, args.csv_output)
    write_markdown(metrics, args.md_output)

    print(f"Analyzed {len(metrics)} synthesis logs")
    print(f"CSV summary: {args.csv_output}")
    print(f"Markdown summary: {args.md_output}")


if __name__ == "__main__":
    main()
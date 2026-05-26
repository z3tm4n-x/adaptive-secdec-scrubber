#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import subprocess
import sys
from bisect import bisect_right
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, stdev


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(path)

    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def read_control_levels(path: Path) -> list[tuple[int, int]]:
    if not path.exists():
        raise FileNotFoundError(path)

    events: list[tuple[int, int]] = []

    with path.open(encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()

            if not line:
                continue

            time_text, level_text = line.split(",")
            events.append((int(time_text), int(level_text)))

    events.sort()

    if not events:
        raise ValueError(f"No control-level events in {path}")

    return events


def level_at(control_events: list[tuple[int, int]], cycle: int) -> int:
    times = [item[0] for item in control_events]
    index = bisect_right(times, cycle) - 1

    if index < 0:
        return 0

    return control_events[index][1]


def run_generator(
    *,
    seed: int,
    output_dir: Path,
    args: argparse.Namespace,
) -> tuple[Path, Path, Path]:
    seed_dir = output_dir / f"seed_{seed:04d}"
    seed_dir.mkdir(parents=True, exist_ok=True)

    fault_output = seed_dir / "fault_events.csv"
    control_output = seed_dir / "control_levels.csv"
    meta_output = seed_dir / "fault_events_meta.csv"
    shift_summary_output = seed_dir / "event_shift_summary.md"
    level_map_output = seed_dir / "risk_policy_level_map.csv"

    command = [
        sys.executable,
        "model/generate_fault_events.py",
        "--scenario",
        args.scenario,
        "--input",
        str(args.input),
        "--output",
        str(fault_output),
        "--control-output",
        str(control_output),
        "--meta-output",
        str(meta_output),
        "--shift-summary-output",
        str(shift_summary_output),
        "--start-index",
        str(args.start_index),
        "--window-size",
        str(args.window_size),
        "--total-cycles",
        str(args.total_cycles),
        "--addr-width",
        str(args.addr_width),
        "--event-count",
        str(args.event_count),
        "--paired-event-count",
        str(args.paired_event_count),
        "--pair-gap-min",
        str(args.pair_gap_min),
        "--pair-gap-max",
        str(args.pair_gap_max),
        "--cluster-event-count",
        str(args.cluster_event_count),
        "--cluster-bit-count",
        str(args.cluster_bit_count),
        "--seed",
        str(seed),
        "--control-quantization",
        args.control_quantization,
        "--control-source",
        args.control_source,
        "--control-policy-schedule",
        str(args.control_policy_schedule),
        "--control-policy-level-map-output",
        str(level_map_output),
        "--control-delay-points",
        str(args.control_delay_points),
    ]

    subprocess.run(command, check=True)

    return meta_output, control_output, shift_summary_output


def analyze_seed(
    *,
    seed: int,
    meta_path: Path,
    control_path: Path,
    aggressive_level_min: int,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    meta_rows = read_csv(meta_path)
    control_events = read_control_levels(control_path)

    paired_rows = [row for row in meta_rows if row["event_type"] == "paired"]

    by_pair: dict[str, list[dict[str, str]]] = defaultdict(list)

    for row in paired_rows:
        by_pair[row["pair_id"]].append(row)

    pair_records: list[dict[str, object]] = []

    malformed_pairs = 0
    address_mismatch = 0
    shifted_pair_events = 0

    for pair_id, items in sorted(by_pair.items(), key=lambda item: int(item[0])):
        roles = {row["pair_role"]: row for row in items}

        if len(items) != 2 or set(roles) != {"first", "second"}:
            malformed_pairs += 1
            continue

        first = roles["first"]
        second = roles["second"]

        first_cycle = int(first["actual_cycle"])
        second_cycle = int(second["actual_cycle"])
        first_preferred = int(first["preferred_cycle"])
        second_preferred = int(second["preferred_cycle"])
        first_shift = int(first["cycle_shift"])
        second_shift = int(second["cycle_shift"])

        first_level = level_at(control_events, first_cycle)
        second_level = level_at(control_events, second_cycle)

        first_address = int(first["address"])
        second_address = int(second["address"])
        same_address = first_address == second_address

        if not same_address:
            address_mismatch += 1

        if first_shift != 0:
            shifted_pair_events += 1

        if second_shift != 0:
            shifted_pair_events += 1

        gap_actual = second_cycle - first_cycle
        gap_preferred = second_preferred - first_preferred
        max_level = max(first_level, second_level)

        pair_records.append(
            {
                "seed": seed,
                "pair_id": int(pair_id),
                "first_cycle": first_cycle,
                "second_cycle": second_cycle,
                "gap_actual": gap_actual,
                "gap_preferred": gap_preferred,
                "first_shift": first_shift,
                "second_shift": second_shift,
                "first_address": first_address,
                "second_address": second_address,
                "same_address": int(same_address),
                "first_level": first_level,
                "second_level": second_level,
                "max_level": max_level,
                "first_aggressive": int(first_level >= aggressive_level_min),
                "second_aggressive": int(second_level >= aggressive_level_min),
                "any_aggressive": int(max_level >= aggressive_level_min),
            }
        )

    all_shifted = sum(1 for row in meta_rows if int(row["cycle_shift"]) != 0)

    summary = {
        "seed": seed,
        "total_meta_events": len(meta_rows),
        "paired_event_rows": len(paired_rows),
        "pair_count": len(pair_records),
        "malformed_pairs": malformed_pairs,
        "address_mismatch": address_mismatch,
        "shifted_pair_events": shifted_pair_events,
        "all_shifted_events": all_shifted,
    }

    return pair_records, summary


def write_pair_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "seed",
        "pair_id",
        "first_cycle",
        "second_cycle",
        "gap_actual",
        "gap_preferred",
        "first_shift",
        "second_shift",
        "first_address",
        "second_address",
        "same_address",
        "first_level",
        "second_level",
        "max_level",
        "first_aggressive",
        "second_aggressive",
        "any_aggressive",
    ]

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for row in rows:
            writer.writerow({name: row[name] for name in fieldnames})


def summarize_records(
    *,
    pair_records: list[dict[str, object]],
    seed_summaries: list[dict[str, object]],
    aggressive_level_min: int,
) -> list[str]:
    total_pairs = len(pair_records)

    gaps = [int(row["gap_actual"]) for row in pair_records]
    max_levels = [int(row["max_level"]) for row in pair_records]
    first_levels = [int(row["first_level"]) for row in pair_records]
    second_levels = [int(row["second_level"]) for row in pair_records]

    level_pairs = Counter(
        (int(row["first_level"]), int(row["second_level"]))
        for row in pair_records
    )
    max_level_counts = Counter(max_levels)

    aggressive_pairs = sum(1 for row in pair_records if int(row["any_aggressive"]) != 0)
    second_aggressive_pairs = sum(
        1 for row in pair_records
        if int(row["second_aggressive"]) != 0
    )

    malformed = sum(int(row["malformed_pairs"]) for row in seed_summaries)
    address_mismatch = sum(int(row["address_mismatch"]) for row in seed_summaries)
    shifted_pair_events = sum(int(row["shifted_pair_events"]) for row in seed_summaries)
    all_shifted_events = sum(int(row["all_shifted_events"]) for row in seed_summaries)
    total_meta_events = sum(int(row["total_meta_events"]) for row in seed_summaries)

    lines: list[str] = []

    lines.append("# True pair alignment по `pair_id`")
    lines.append("")
    lines.append("## Назначение")
    lines.append("")
    lines.append(
        "Проверяется согласование накопительных пар с управляющим уровнем "
        "по истинным метаданным генератора. Пары группируются по `pair_id`, "
        "а не восстанавливаются эвристически по адресу и временному разрыву."
    )
    lines.append("")
    lines.append("## Общая сводка")
    lines.append("")
    lines.append(f"- Число seed: {len(seed_summaries)}")
    lines.append(f"- Всего метаданных событий: {total_meta_events}")
    lines.append(f"- Корректно разобранных накопительных пар: {total_pairs}")
    lines.append(f"- Некорректных pair_id-групп: {malformed}")
    lines.append(f"- Пар с разными адресами first/second: {address_mismatch}")
    lines.append(f"- Сдвинутых событий внутри накопительных пар: {shifted_pair_events}")
    lines.append(f"- Сдвинутых событий всех типов: {all_shifted_events}")
    lines.append(f"- Порог агрессивного уровня: level >= {aggressive_level_min}")
    lines.append("")

    lines.append("## Разрыв внутри накопительных пар")
    lines.append("")
    lines.append("| Показатель | Значение |")
    lines.append("|---|---:|")

    if gaps:
        lines.append(f"| min gap, тактов | {min(gaps)} |")
        lines.append(f"| mean gap, тактов | {mean(gaps):.3f} |")
        lines.append(f"| max gap, тактов | {max(gaps)} |")
        lines.append(f"| σ gap, тактов | {stdev(gaps) if len(gaps) > 1 else 0.0:.3f} |")
    else:
        lines.append("| min gap, тактов |  |")
        lines.append("| mean gap, тактов |  |")
        lines.append("| max gap, тактов |  |")
        lines.append("| σ gap, тактов |  |")

    lines.append("")

    lines.append("## Распределение максимального уровня пары")
    lines.append("")
    lines.append("| max(first_level, second_level) | Пар | Доля, % |")
    lines.append("|---:|---:|---:|")

    for level in range(8):
        count = max_level_counts.get(level, 0)
        fraction = count / total_pairs * 100.0 if total_pairs else 0.0
        lines.append(f"| {level} | {count} | {fraction:.3f} |")

    lines.append("")
    lines.append("## Распределение уровней first/second")
    lines.append("")
    lines.append("| first level | second level | Пар | Доля, % |")
    lines.append("|---:|---:|---:|---:|")

    for (first_level, second_level), count in sorted(level_pairs.items()):
        fraction = count / total_pairs * 100.0 if total_pairs else 0.0
        lines.append(
            f"| {first_level} | {second_level} | {count} | {fraction:.3f} |"
        )

    lines.append("")
    lines.append("## Агрессивные уровни")
    lines.append("")
    lines.append("| Метрика | Значение |")
    lines.append("|---|---:|")
    lines.append(
        f"| Пар, где хотя бы одно событие имеет level >= {aggressive_level_min} | "
        f"{aggressive_pairs} |"
    )
    lines.append(
        f"| Доля таких пар, % | "
        f"{(aggressive_pairs / total_pairs * 100.0) if total_pairs else 0.0:.3f} |"
    )
    lines.append(
        f"| Пар, где второе событие имеет level >= {aggressive_level_min} | "
        f"{second_aggressive_pairs} |"
    )
    lines.append(
        f"| Доля таких пар, % | "
        f"{(second_aggressive_pairs / total_pairs * 100.0) if total_pairs else 0.0:.3f} |"
    )
    lines.append("")

    lines.append("## Проверки корректности")
    lines.append("")
    lines.append("| Проверка | Результат |")
    lines.append("|---|---|")
    lines.append(f"| У каждой пары есть first и second | {'PASS' if malformed == 0 else 'FAIL'} |")
    lines.append(f"| first и second имеют один адрес | {'PASS' if address_mismatch == 0 else 'FAIL'} |")
    lines.append(f"| События накопительных пар не сдвигались | {'PASS' if shifted_pair_events == 0 else 'WARN'} |")
    lines.append("")

    lines.append("## Интерпретация")
    lines.append("")
    lines.append(
        "Этот отчёт закрывает методическое замечание о восстановлении накопительных "
        "пар по эвристике. Накопительные пары анализируются по истинным полям "
        "`pair_id` и `pair_role`, записанным генератором событий."
    )
    lines.append("")
    lines.append(
        "Распределение уровней показывает, на каких участках управляющего ряда "
        "расположены пары. Это не является метрикой надёжности само по себе, "
        "но проверяет, что сценарий пар действительно согласован с управляющей "
        "политикой и может использоваться для анализа накопительного механизма."
    )

    return lines


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument("--scenario-label", required=True)
    parser.add_argument("--scenario", default="upsets")
    parser.add_argument("--input", type=Path, default=Path("data/upsets.xlsx"))
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--seed-start", type=int, default=1)
    parser.add_argument("--seed-count", type=int, default=10)
    parser.add_argument("--start-index", type=int, default=0)
    parser.add_argument("--total-cycles", type=int, default=500000)
    parser.add_argument("--window-size", type=int, default=43824)
    parser.add_argument("--addr-width", type=int, default=8)
    parser.add_argument("--event-count", type=int, default=400)
    parser.add_argument("--paired-event-count", type=int, default=40)
    parser.add_argument("--pair-gap-min", type=int, default=600)
    parser.add_argument("--pair-gap-max", type=int, default=3000)
    parser.add_argument("--cluster-event-count", type=int, default=0)
    parser.add_argument("--cluster-bit-count", type=int, default=2)
    parser.add_argument("--control-quantization", default="linear_max")
    parser.add_argument("--control-source", default="risk_policy")
    parser.add_argument(
        "--control-policy-schedule",
        type=Path,
        default=Path("results/paper/tables/risk_policy_schedule.csv"),
    )
    parser.add_argument("--control-delay-points", type=int, default=0)
    parser.add_argument("--aggressive-level-min", type=int, default=6)
    parser.add_argument("--pair-csv-output", type=Path, required=True)
    parser.add_argument("--md-output", type=Path, required=True)

    args = parser.parse_args()

    all_pair_records: list[dict[str, object]] = []
    seed_summaries: list[dict[str, object]] = []

    for seed in range(args.seed_start, args.seed_start + args.seed_count):
        meta_path, control_path, _shift_summary_path = run_generator(
            seed=seed,
            output_dir=args.output_dir / args.scenario_label,
            args=args,
        )

        pair_records, seed_summary = analyze_seed(
            seed=seed,
            meta_path=meta_path,
            control_path=control_path,
            aggressive_level_min=args.aggressive_level_min,
        )

        all_pair_records.extend(pair_records)
        seed_summaries.append(seed_summary)

    write_pair_csv(args.pair_csv_output, all_pair_records)

    lines = summarize_records(
        pair_records=all_pair_records,
        seed_summaries=seed_summaries,
        aggressive_level_min=args.aggressive_level_min,
    )

    args.md_output.parent.mkdir(parents=True, exist_ok=True)
    args.md_output.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(args.md_output.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()

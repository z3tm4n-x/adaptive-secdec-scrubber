#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import shutil
import subprocess
import sys
from pathlib import Path


STRATEGY_IDS = {
    "fixed": 0,
    "table": 1,
    "threshold": 2,
}


def run(command: list[str]) -> None:
    print("+", " ".join(command))
    subprocess.run(command, check=True)


def write_results_header(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "strategy,total_cycles,scrub_cycles,reads,writes,corrected,"
        "uncorrectable_detections,unique_uncorrectable_words,interval_switches,"
        "safe_entries,safe_cycles,scrub_active_cycles,memory_busy_cycles,"
        "scrub_per_mille,busy_per_mille,safe_per_mille\n",
        encoding="utf-8",
    )


def read_strategy_results(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def append_replay_rows(
    *,
    output: Path,
    replay_name: str,
    replay_strategy: str,
    measured_control: Path,
    rows: list[dict[str, str]],
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "replay_name",
        "replay_strategy",
        "measured_control",
        "strategy",
        "total_cycles",
        "scrub_cycles",
        "reads",
        "writes",
        "corrected",
        "uncorrectable_detections",
        "unique_uncorrectable_words",
        "interval_switches",
        "safe_entries",
        "safe_cycles",
        "scrub_active_cycles",
        "memory_busy_cycles",
        "scrub_per_mille",
        "busy_per_mille",
        "safe_per_mille",
    ]

    write_header = not output.exists()

    with output.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)

        if write_header:
            writer.writeheader()

        for row in rows:
            out = {
                "replay_name": replay_name,
                "replay_strategy": replay_strategy,
                "measured_control": str(measured_control),
            }
            out.update(row)
            writer.writerow(out)


def build_markdown(csv_path: Path, md_path: Path) -> None:
    rows = []
    with csv_path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    lines: list[str] = []

    lines.append("# RTL replay measured schedule")
    lines.append("")
    lines.append("## Назначение")
    lines.append("")
    lines.append(
        "Проверяется исполнение управляющего расписания, построенного не по "
        "истинному ряду ν(t), а по наблюдаемым счётчикам исполнения. "
        "События отказов остаются теми же, что в исходном seed; меняется только "
        "`control_levels.csv`."
    )
    lines.append("")
    lines.append("## Результаты")
    lines.append("")
    lines.append(
        "| replay | replay strategy | RTL strategy | scrub cycles | corrected | "
        "uncorrectable detections | unique uncorrectable words | busy, % | interval switches |"
    )
    lines.append("|---|---|---|---:|---:|---:|---:|---:|---:|")

    for row in rows:
        busy = float(row["busy_per_mille"]) / 10.0
        lines.append(
            f"| `{row['replay_name']}` | "
            f"`{row['replay_strategy']}` | "
            f"`{row['strategy']}` | "
            f"{row['scrub_cycles']} | "
            f"{row['corrected']} | "
            f"{row['uncorrectable_detections']} | "
            f"{row['unique_uncorrectable_words']} | "
            f"{busy:.3f} | "
            f"{row['interval_switches']} |"
        )

    lines.append("")
    lines.append("## Интерпретация")
    lines.append("")
    lines.append(
        "Это offline-replay, а не полностью замкнутый аппаратный контур: "
        "расписание построено по ранее снятой трассе и затем подано в RTL как "
        "внешний `ctrl_level`. Тем не менее оцениватель расписания не использует "
        "истинный ряд ν(t); он использует только наблюдаемые счётчики."
    )
    lines.append("")
    lines.append(
        "Сравнение `weighted` и `corrected_only` показывает роль обнаруженных "
        "неустранимых состояний как дополнительного индикатора недооценки "
        "опасного участка."
    )

    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument("--replay-name", required=True)
    parser.add_argument("--measured-control", type=Path, required=True)
    parser.add_argument("--replay-strategy", choices=sorted(STRATEGY_IDS), default="table")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--md-output", type=Path, required=True)

    parser.add_argument("--addr-width", type=int, default=8)
    parser.add_argument("--total-cycles", type=int, default=500000)
    parser.add_argument("--fault-scenario", default="upsets")
    parser.add_argument("--fault-window-size", type=int, default=43824)
    parser.add_argument("--fault-event-count", type=int, default=400)
    parser.add_argument("--fault-paired-event-count", type=int, default=40)
    parser.add_argument("--fault-pair-gap-min", type=int, default=600)
    parser.add_argument("--fault-pair-gap-max", type=int, default=3000)
    parser.add_argument("--fault-cluster-event-count", type=int, default=0)
    parser.add_argument("--fault-cluster-bit-count", type=int, default=2)
    parser.add_argument("--fault-seed", type=int, default=1)

    parser.add_argument("--fixed-interval", type=int, default=1244)
    parser.add_argument("--safe-interval", type=int, default=1244)
    parser.add_argument(
        "--level-intervals",
        default="1866,1788,1710,1633,1555,1400,1244,1089",
    )
    parser.add_argument(
        "--threshold-intervals",
        default="2021,1555,1244",
    )

    args = parser.parse_args()

    if not args.measured_control.exists():
        raise FileNotFoundError(args.measured_control)

    # 1. Generate same fault events. The generated control_levels.csv will be overwritten.
    run(
        [
            "make",
            "gen_fault_events",
            f"ADDR_WIDTH={args.addr_width}",
            f"FAULT_SCENARIO={args.fault_scenario}",
            f"FAULT_TOTAL_CYCLES={args.total_cycles}",
            f"FAULT_WINDOW_SIZE={args.fault_window_size}",
            f"FAULT_EVENT_COUNT={args.fault_event_count}",
            f"FAULT_PAIRED_EVENT_COUNT={args.fault_paired_event_count}",
            f"FAULT_PAIR_GAP_MIN={args.fault_pair_gap_min}",
            f"FAULT_PAIR_GAP_MAX={args.fault_pair_gap_max}",
            f"FAULT_CLUSTER_EVENT_COUNT={args.fault_cluster_event_count}",
            f"FAULT_CLUSTER_BIT_COUNT={args.fault_cluster_bit_count}",
            f"FAULT_SEED={args.fault_seed}",
            "CONTROL_SOURCE=risk_policy",
            "CONTROL_POLICY_SCHEDULE=results/paper/tables/risk_policy_schedule.csv",
            "FAULT_META_OUTPUT=results/tables/fault_events_meta.csv",
            "FAULT_SHIFT_SUMMARY_OUTPUT=results/tables/event_shift_summary.md",
        ]
    )

    # 2. Replace control levels with measured schedule.
    shutil.copyfile(args.measured_control, "tb/control_levels.csv")

    # 3. Compile.
    run(
        [
            "iverilog",
            "-g2012",
            f"-Ptb_strategy_comparison.ADDR_WIDTH={args.addr_width}",
            "-o",
            "results/logs/strategy_comparison.out",
            "rtl/secded_32_39_encoder.v",
            "rtl/secded_32_39_decoder.v",
            "rtl/protected_memory_model.v",
            "rtl/interval_selector.v",
            "rtl/adaptive_scrub_controller.v",
            "tb/tb_strategy_comparison.v",
        ]
    )

    # 4. Prepare result header.
    write_results_header(Path("results/tables/strategy_comparison.csv"))

    level_values = [int(item) for item in args.level_intervals.split(",")]
    if len(level_values) != 8:
        raise ValueError("level-intervals must contain 8 integers")

    threshold_values = [int(item) for item in args.threshold_intervals.split(",")]
    if len(threshold_values) != 3:
        raise ValueError("threshold-intervals must contain 3 integers")

    strategy_id = STRATEGY_IDS[args.replay_strategy]

    plusargs = [
        "vvp",
        "results/logs/strategy_comparison.out",
        f"+STRATEGY={strategy_id}",
        f"+TOTAL_RUN_CYCLES={args.total_cycles}",
        f"+FIXED_INTERVAL={args.fixed_interval}",
        f"+SAFE_INTERVAL={args.safe_interval}",
        f"+LEVEL0_INTERVAL={level_values[0]}",
        f"+LEVEL1_INTERVAL={level_values[1]}",
        f"+LEVEL2_INTERVAL={level_values[2]}",
        f"+LEVEL3_INTERVAL={level_values[3]}",
        f"+LEVEL4_INTERVAL={level_values[4]}",
        f"+LEVEL5_INTERVAL={level_values[5]}",
        f"+LEVEL6_INTERVAL={level_values[6]}",
        f"+LEVEL7_INTERVAL={level_values[7]}",
        "+THRESHOLD_LOW_TO_MEDIUM=3",
        "+THRESHOLD_MEDIUM_TO_LOW=1",
        "+THRESHOLD_MEDIUM_TO_HIGH=6",
        "+THRESHOLD_HIGH_TO_MEDIUM=4",
        f"+THRESHOLD_LOW_INTERVAL={threshold_values[0]}",
        f"+THRESHOLD_MEDIUM_INTERVAL={threshold_values[1]}",
        f"+THRESHOLD_HIGH_INTERVAL={threshold_values[2]}",
        "+DUMP_VCD=0",
    ]

    run(plusargs)

    rows = read_strategy_results(Path("results/tables/strategy_comparison.csv"))
    append_replay_rows(
        output=args.output,
        replay_name=args.replay_name,
        replay_strategy=args.replay_strategy,
        measured_control=args.measured_control,
        rows=rows,
    )
    build_markdown(args.output, args.md_output)

    print(args.md_output.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()

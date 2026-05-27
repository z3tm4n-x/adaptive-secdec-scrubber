#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import math
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean, stdev


def run(command: list[str]) -> None:
    print("+", " ".join(command))
    subprocess.run(command, check=True)


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(path)

    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def tcrit95(n: int) -> float:
    table = {
        1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571,
        6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228,
        11: 2.201, 12: 2.179, 13: 2.160, 14: 2.145, 15: 2.131,
        16: 2.120, 17: 2.110, 18: 2.101, 19: 2.093, 20: 2.086,
    }
    return table.get(n - 1, 1.960)


def mean_ci(values: list[float]) -> tuple[float, float, float, float]:
    n = len(values)
    m = mean(values)

    if n <= 1:
        return m, 0.0, m, m

    sd = stdev(values)
    se = sd / math.sqrt(n)
    t = tcrit95(n)
    return m, sd, m - t * se, m + t * se


def build_summary(
    *,
    replay_csv: Path,
    reference_csv: Path,
    seed_start: int,
    seed_count: int,
    md_output: Path,
    csv_output: Path,
) -> None:
    replay_rows = read_csv(replay_csv)
    reference_rows = read_csv(reference_csv)

    seed_set = set(range(seed_start, seed_start + seed_count))

    reference_selected = [
        row for row in reference_rows
        if int(row["seed"]) in seed_set and row["strategy"] in {"fixed", "table", "threshold"}
    ]

    summary_rows: list[dict[str, object]] = []

    def add_group(kind: str, name: str, rows: list[dict[str, str]]) -> None:
        scrub = [float(row["scrub_cycles"]) for row in rows]
        corrected = [float(row["corrected"]) for row in rows]
        detections = [float(row["uncorrectable_detections"]) for row in rows]
        unique = [float(row["unique_uncorrectable_words"]) for row in rows]
        busy = [float(row["busy_per_mille"]) / 10.0 for row in rows]

        for metric_name, values in [
            ("scrub_cycles", scrub),
            ("corrected", corrected),
            ("uncorrectable_detections", detections),
            ("unique_uncorrectable_words", unique),
            ("busy_percent", busy),
        ]:
            m, sd, lo, hi = mean_ci(values)
            summary_rows.append({
                "kind": kind,
                "name": name,
                "metric": metric_name,
                "n": len(values),
                "mean": m,
                "std": sd,
                "ci95_low": lo,
                "ci95_high": hi,
            })

    grouped_ref: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in reference_selected:
        grouped_ref[row["strategy"]].append(row)

    for strategy in ["fixed", "table", "threshold"]:
        add_group("reference", f"risk_policy_{strategy}", grouped_ref[strategy])

    grouped_replay: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in replay_rows:
        grouped_replay[row["replay_name"]].append(row)

    for replay_name in sorted(grouped_replay):
        add_group("measured_replay", replay_name, grouped_replay[replay_name])

    csv_output.parent.mkdir(parents=True, exist_ok=True)
    with csv_output.open("w", encoding="utf-8", newline="") as f:
        fieldnames = ["kind", "name", "metric", "n", "mean", "std", "ci95_low", "ci95_high"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in summary_rows:
            writer.writerow(row)

    def get(kind: str, name: str, metric: str) -> dict[str, object]:
        for row in summary_rows:
            if row["kind"] == kind and row["name"] == name and row["metric"] == metric:
                return row
        raise KeyError((kind, name, metric))

    lines: list[str] = []
    lines.append("# Multi-seed measured replay")
    lines.append("")
    lines.append("## Назначение")
    lines.append("")
    lines.append(
        "Проверяется offline-replay управляющих расписаний, построенных по "
        "наблюдаемым счётчикам исполнения, на серии seed. Истинный ряд ν(t) "
        "не используется при построении measured schedule."
    )
    lines.append("")
    lines.append(f"- Seed range: {seed_start}…{seed_start + seed_count - 1}")
    lines.append(f"- Replay CSV: `{replay_csv}`")
    lines.append(f"- Reference CSV: `{reference_csv}`")
    lines.append("")
    lines.append("## Сводка")
    lines.append("")
    lines.append("| kind | name | busy, % | scrub cycles | corrected | uncorrectable detections | unique uncorrectable words |")
    lines.append("|---|---|---:|---:|---:|---:|---:|")

    ordered = [
        ("reference", "risk_policy_fixed"),
        ("reference", "risk_policy_table"),
        ("reference", "risk_policy_threshold"),
        ("measured_replay", "measured_table_weighted"),
        ("measured_replay", "measured_table_corrected_only"),
    ]

    for kind, name in ordered:
        busy = get(kind, name, "busy_percent")
        scrub = get(kind, name, "scrub_cycles")
        corrected = get(kind, name, "corrected")
        detections = get(kind, name, "uncorrectable_detections")
        unique = get(kind, name, "unique_uncorrectable_words")

        lines.append(
            f"| `{kind}` | `{name}` | "
            f"{busy['mean']:.3f} ± {busy['std']:.3f} | "
            f"{scrub['mean']:.1f} ± {scrub['std']:.1f} | "
            f"{corrected['mean']:.1f} ± {corrected['std']:.1f} | "
            f"{detections['mean']:.1f} ± {detections['std']:.1f} | "
            f"{unique['mean']:.3f} ± {unique['std']:.3f} |"
        )

    lines.append("")
    lines.append("## Ключевые paired-delta measured replay")
    lines.append("")
    lines.append("| Сравнение | Δ busy, п.п. | Δ uncorrectable detections | Δ unique |")
    lines.append("|---|---:|---:|---:|")

    replay_by_seed: dict[tuple[int, str], dict[str, str]] = {}
    for row in replay_rows:
        replay_by_seed[(int(row["fault_seed"]), row["replay_name"])] = row

    deltas = {
        "weighted - corrected_only": [],
    }

    for seed in seed_set:
        weighted = replay_by_seed[(seed, "measured_table_weighted")]
        corrected_only = replay_by_seed[(seed, "measured_table_corrected_only")]

        deltas["weighted - corrected_only"].append({
            "busy": float(weighted["busy_per_mille"]) / 10.0 - float(corrected_only["busy_per_mille"]) / 10.0,
            "detections": float(weighted["uncorrectable_detections"]) - float(corrected_only["uncorrectable_detections"]),
            "unique": float(weighted["unique_uncorrectable_words"]) - float(corrected_only["unique_uncorrectable_words"]),
        })

    for label, items in deltas.items():
        busy_values = [item["busy"] for item in items]
        detection_values = [item["detections"] for item in items]
        unique_values = [item["unique"] for item in items]

        busy_m, _, busy_lo, busy_hi = mean_ci(busy_values)
        det_m, _, det_lo, det_hi = mean_ci(detection_values)
        uniq_m, _, uniq_lo, uniq_hi = mean_ci(unique_values)

        lines.append(
            f"| `{label}` | "
            f"{busy_m:.3f} [{busy_lo:.3f}; {busy_hi:.3f}] | "
            f"{det_m:.1f} [{det_lo:.1f}; {det_hi:.1f}] | "
            f"{uniq_m:.3f} [{uniq_lo:.3f}; {uniq_hi:.3f}] |"
        )

    lines.append("")
    lines.append("## Интерпретация")
    lines.append("")
    lines.append(
        "`measured_table_corrected_only` использует только исправленные ошибки "
        "и поэтому может недооценивать опасные участки. `measured_table_weighted` "
        "добавляет обнаруженные неустранимые состояния как штрафной индикатор."
    )
    lines.append("")
    lines.append(
        "Если `weighted - corrected_only` имеет положительную Δ busy и "
        "отрицательную Δ unique / Δ uncorrectable detections, то добавление "
        "`uncorrectable_error_count` повышает интенсивность восстановления, "
        "но снижает риск-метрики."
    )

    md_output.parent.mkdir(parents=True, exist_ok=True)
    md_output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument("--seed-start", type=int, default=1)
    parser.add_argument("--seed-count", type=int, default=10)
    parser.add_argument("--base-dir", type=Path, default=Path("results/paper/measured_control/no_clusters_multiseed"))
    parser.add_argument("--observable-base-dir", type=Path, default=Path("results/paper/observable_signal/no_clusters_multiseed"))
    parser.add_argument("--reference-csv", type=Path, default=Path("results/paper/unsaturated_control/no_clusters/strategy_comparison_series.csv"))

    parser.add_argument("--total-cycles", type=int, default=500000)
    parser.add_argument("--window-cycles", type=int, default=25000)
    parser.add_argument("--addr-width", type=int, default=8)

    args = parser.parse_args()

    replay_csv = args.base_dir / "replay/measured_replay_series.csv"
    replay_md = args.base_dir / "replay/measured_replay_series_live.md"
    summary_csv = args.base_dir / "measured_replay_series_summary.csv"
    summary_md = args.base_dir / "measured_replay_series_summary.md"

    if replay_csv.exists():
        replay_csv.unlink()
    if replay_md.exists():
        replay_md.unlink()

    for seed in range(args.seed_start, args.seed_start + args.seed_count):
        seed_name = f"seed_{seed:04d}"
        observable_dir = args.observable_base_dir / seed_name
        measured_dir = args.base_dir / seed_name
        replay_dir = args.base_dir / "replay"

        observable_dir.mkdir(parents=True, exist_ok=True)
        measured_dir.mkdir(parents=True, exist_ok=True)
        replay_dir.mkdir(parents=True, exist_ok=True)

        trace = observable_dir / "strategy_execution_trace.csv"
        meta = observable_dir / "fault_events_meta.csv"
        windows = observable_dir / "observable_signal_windows.csv"
        observable_md = observable_dir / "observable_signal_summary.md"

        run([
            "make",
            "test_strategy_comparison",
            f"ADDR_WIDTH={args.addr_width}",
            "DUMP_VCD=0",
            "TRACE_EXECUTION=1",
            f"TRACE_OUTPUT={trace}",
            "FAULT_SCENARIO=upsets",
            f"FAULT_TOTAL_CYCLES={args.total_cycles}",
            "FAULT_WINDOW_SIZE=43824",
            "FAULT_EVENT_COUNT=400",
            "FAULT_PAIRED_EVENT_COUNT=40",
            "FAULT_PAIR_GAP_MIN=600",
            "FAULT_PAIR_GAP_MAX=3000",
            "FAULT_CLUSTER_EVENT_COUNT=0",
            "FAULT_CLUSTER_BIT_COUNT=2",
            f"FAULT_SEED={seed}",
            f"FAULT_META_OUTPUT={meta}",
            f"FAULT_SHIFT_SUMMARY_OUTPUT={observable_dir / 'event_shift_summary.md'}",
            "CONTROL_SOURCE=risk_policy",
            "CONTROL_POLICY_SCHEDULE=results/paper/tables/risk_policy_schedule.csv",
            f"CONTROL_POLICY_LEVEL_MAP_OUTPUT={observable_dir / 'risk_policy_level_map.csv'}",
            "CONTROL_DELAY_POINTS=0",
            "FIXED_INTERVAL=1244",
            "SAFE_INTERVAL=1244",
            "LEVEL0_INTERVAL=1866",
            "LEVEL1_INTERVAL=1788",
            "LEVEL2_INTERVAL=1710",
            "LEVEL3_INTERVAL=1633",
            "LEVEL4_INTERVAL=1555",
            "LEVEL5_INTERVAL=1400",
            "LEVEL6_INTERVAL=1244",
            "LEVEL7_INTERVAL=1089",
            "THRESHOLD_LOW_INTERVAL=2021",
            "THRESHOLD_MEDIUM_INTERVAL=1555",
            "THRESHOLD_HIGH_INTERVAL=1244",
        ])

        run([
            sys.executable,
            "model/analyze_observable_trace.py",
            "--trace", str(trace),
            "--meta", str(meta),
            "--total-cycles", str(args.total_cycles),
            "--window-cycles", str(args.window_cycles),
            "--csv-output", str(windows),
            "--md-output", str(observable_md),
        ])

        weighted_control = measured_dir / "control_levels_measured_table.csv"
        corrected_control = measured_dir / "control_levels_measured_table_corrected_only.csv"

        run([
            sys.executable,
            "model/build_measured_level_schedule.py",
            "--windows", str(windows),
            "--source-strategy", "table",
            "--total-cycles", str(args.total_cycles),
            "--extra-delay-windows", "0",
            "--uncorrectable-weight", "0.25",
            "--rate-max", "200",
            "--max-level", "7",
            "--control-output", str(weighted_control),
            "--detail-output", str(measured_dir / "measured_level_windows_table.csv"),
            "--md-output", str(measured_dir / "measured_level_schedule_table.md"),
        ])

        run([
            sys.executable,
            "model/build_measured_level_schedule.py",
            "--windows", str(windows),
            "--source-strategy", "table",
            "--total-cycles", str(args.total_cycles),
            "--extra-delay-windows", "0",
            "--uncorrectable-weight", "0.0",
            "--rate-max", "200",
            "--max-level", "7",
            "--control-output", str(corrected_control),
            "--detail-output", str(measured_dir / "measured_level_windows_table_corrected_only.csv"),
            "--md-output", str(measured_dir / "measured_level_schedule_table_corrected_only.md"),
        ])

        run([
            sys.executable,
            "model/run_measured_schedule_replay.py",
            "--replay-name", "measured_table_weighted",
            "--measured-control", str(weighted_control),
            "--replay-strategy", "table",
            "--output", str(replay_csv),
            "--md-output", str(replay_md),
            "--fault-seed", str(seed),
        ])

        run([
            sys.executable,
            "model/run_measured_schedule_replay.py",
            "--replay-name", "measured_table_corrected_only",
            "--measured-control", str(corrected_control),
            "--replay-strategy", "table",
            "--output", str(replay_csv),
            "--md-output", str(replay_md),
            "--fault-seed", str(seed),
        ])

    build_summary(
        replay_csv=replay_csv,
        reference_csv=args.reference_csv,
        seed_start=args.seed_start,
        seed_count=args.seed_count,
        md_output=summary_md,
        csv_output=summary_csv,
    )

    print(summary_md.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()

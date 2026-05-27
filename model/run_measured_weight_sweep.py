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


def weight_label(weight: float) -> str:
    return f"w{weight:.2f}".replace(".", "p")


def summarize(replay_csv: Path, summary_csv: Path, summary_md: Path) -> None:
    rows = read_csv(replay_csv)

    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[row["replay_name"]].append(row)

    metrics = [
        ("busy_percent", "busy, %"),
        ("scrub_cycles", "scrub cycles"),
        ("corrected", "corrected"),
        ("uncorrectable_detections", "uncorrectable detections"),
        ("unique_uncorrectable_words", "unique uncorrectable words"),
    ]

    summary_rows = []

    for replay_name in sorted(grouped):
        items = grouped[replay_name]
        for metric, label in metrics:
            if metric == "busy_percent":
                values = [float(row["busy_per_mille"]) / 10.0 for row in items]
            else:
                values = [float(row[metric]) for row in items]

            m, sd, lo, hi = mean_ci(values)

            summary_rows.append({
                "replay_name": replay_name,
                "metric": metric,
                "label": label,
                "n": len(values),
                "mean": m,
                "std": sd,
                "ci95_low": lo,
                "ci95_high": hi,
            })

    summary_csv.parent.mkdir(parents=True, exist_ok=True)
    with summary_csv.open("w", encoding="utf-8", newline="") as f:
        fieldnames = ["replay_name", "metric", "n", "mean", "std", "ci95_low", "ci95_high"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in summary_rows:
            writer.writerow({k: row[k] for k in fieldnames})

    def get(replay_name: str, metric: str) -> dict[str, object]:
        for row in summary_rows:
            if row["replay_name"] == replay_name and row["metric"] == metric:
                return row
        raise KeyError((replay_name, metric))

    lines = []
    lines.append("# Measured control weight sweep")
    lines.append("")
    lines.append("## Назначение")
    lines.append("")
    lines.append(
        "Проверяется чувствительность measured-control replay к весу "
        "`uncorrectable_error_count` в измерительном score. Все replay строятся "
        "по наблюдаемым окнам `corrected_error_count` / `uncorrectable_error_count`; "
        "истинный ряд ν(t) не используется при выборе уровня."
    )
    lines.append("")
    lines.append("## Сводка")
    lines.append("")
    lines.append("| replay | busy, % | scrub cycles | corrected | uncorrectable detections | unique uncorrectable words |")
    lines.append("|---|---:|---:|---:|---:|---:|")

    for replay_name in sorted(grouped):
        busy = get(replay_name, "busy_percent")
        scrub = get(replay_name, "scrub_cycles")
        corrected = get(replay_name, "corrected")
        detections = get(replay_name, "uncorrectable_detections")
        unique = get(replay_name, "unique_uncorrectable_words")

        lines.append(
            f"| `{replay_name}` | "
            f"{busy['mean']:.3f} ± {busy['std']:.3f} | "
            f"{scrub['mean']:.1f} ± {scrub['std']:.1f} | "
            f"{corrected['mean']:.1f} ± {corrected['std']:.1f} | "
            f"{detections['mean']:.1f} ± {detections['std']:.1f} | "
            f"{unique['mean']:.3f} ± {unique['std']:.3f} |"
        )

    lines.append("")
    lines.append("## Интерпретация")
    lines.append("")
    lines.append(
        "Если рост веса `uncorrectable_error_count` приводит только к росту "
        "занятости без устойчивого снижения `unique_uncorrectable_words` или "
        "`uncorrectable_detections`, выбранная формула score требует иной "
        "калибровки или другой нелинейной реакции на обнаруженные DED-состояния."
    )

    summary_md.parent.mkdir(parents=True, exist_ok=True)
    summary_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(summary_md.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument("--seed-start", type=int, default=1)
    parser.add_argument("--seed-count", type=int, default=10)
    parser.add_argument("--weights", default="0,0.1,0.25,0.5,0.75,1.0")
    parser.add_argument("--rate-max", type=float, default=200.0)
    parser.add_argument("--total-cycles", type=int, default=500000)
    parser.add_argument("--observable-base-dir", type=Path, default=Path("results/paper/observable_signal/no_clusters_multiseed"))
    parser.add_argument("--base-dir", type=Path, default=Path("results/paper/measured_control/no_clusters_weight_sweep"))

    args = parser.parse_args()

    weights = [float(item) for item in args.weights.split(",")]

    replay_dir = args.base_dir / "replay"
    replay_dir.mkdir(parents=True, exist_ok=True)

    replay_csv = replay_dir / "measured_weight_sweep_replay.csv"
    replay_md_live = replay_dir / "measured_weight_sweep_live.md"

    if replay_csv.exists():
        replay_csv.unlink()
    if replay_md_live.exists():
        replay_md_live.unlink()

    for seed in range(args.seed_start, args.seed_start + args.seed_count):
        seed_name = f"seed_{seed:04d}"
        windows = args.observable_base_dir / seed_name / "observable_signal_windows.csv"

        if not windows.exists():
            raise FileNotFoundError(windows)

        for weight in weights:
            label = weight_label(weight)
            measured_dir = args.base_dir / seed_name / label
            measured_dir.mkdir(parents=True, exist_ok=True)

            control = measured_dir / f"control_levels_measured_table_{label}.csv"

            run([
                sys.executable,
                "model/build_measured_level_schedule.py",
                "--windows", str(windows),
                "--source-strategy", "table",
                "--total-cycles", str(args.total_cycles),
                "--extra-delay-windows", "0",
                "--uncorrectable-weight", str(weight),
                "--rate-max", str(args.rate_max),
                "--max-level", "7",
                "--control-output", str(control),
                "--detail-output", str(measured_dir / f"measured_level_windows_table_{label}.csv"),
                "--md-output", str(measured_dir / f"measured_level_schedule_table_{label}.md"),
            ])

            run([
                sys.executable,
                "model/run_measured_schedule_replay.py",
                "--replay-name", f"measured_table_{label}",
                "--measured-control", str(control),
                "--replay-strategy", "table",
                "--output", str(replay_csv),
                "--md-output", str(replay_md_live),
                "--fault-seed", str(seed),
            ])

    summarize(
        replay_csv=replay_csv,
        summary_csv=args.base_dir / "measured_weight_sweep_summary.csv",
        summary_md=args.base_dir / "measured_weight_sweep_summary.md",
    )


if __name__ == "__main__":
    main()

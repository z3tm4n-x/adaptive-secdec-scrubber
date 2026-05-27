#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import math
from collections import defaultdict
from pathlib import Path
from statistics import mean, stdev


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


def replay_metric(row: dict[str, str], metric: str) -> float:
    if metric == "busy_percent":
        return float(row["busy_per_mille"]) / 10.0
    return float(row[metric])


def reference_metric(row: dict[str, str], metric: str) -> float:
    if metric == "busy_percent":
        return float(row["busy_per_mille"]) / 10.0
    return float(row[metric])


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--replay",
        type=Path,
        default=Path("results/paper/measured_control/no_clusters_weight_sweep/replay/measured_weight_sweep_replay.csv"),
    )
    parser.add_argument(
        "--reference",
        type=Path,
        default=Path("results/paper/unsaturated_control/no_clusters/strategy_comparison_series.csv"),
    )
    parser.add_argument(
        "--csv-output",
        type=Path,
        default=Path("results/paper/measured_control/no_clusters_weight_sweep/measured_weight_sweep_deltas.csv"),
    )
    parser.add_argument(
        "--md-output",
        type=Path,
        default=Path("results/paper/measured_control/no_clusters_weight_sweep/measured_weight_sweep_deltas.md"),
    )

    args = parser.parse_args()

    replay_rows = read_csv(args.replay)
    reference_rows = read_csv(args.reference)

    metrics = [
        ("busy_percent", "busy, %"),
        ("scrub_cycles", "scrub cycles"),
        ("corrected", "corrected"),
        ("uncorrectable_detections", "uncorrectable detections"),
        ("unique_uncorrectable_words", "unique uncorrectable words"),
    ]

    by_replay_seed: dict[tuple[str, int], dict[str, str]] = {}
    replay_names = sorted({row["replay_name"] for row in replay_rows})
    seeds = sorted({int(row["fault_seed"]) for row in replay_rows})

    for row in replay_rows:
        by_replay_seed[(row["replay_name"], int(row["fault_seed"]))] = row

    by_reference_seed: dict[tuple[str, int], dict[str, str]] = {}

    for row in reference_rows:
        seed = int(row["seed"])
        if seed not in seeds:
            continue
        by_reference_seed[(row["strategy"], seed)] = row

    out_rows: list[dict[str, object]] = []

    def add_delta(comparison: str, lhs_name: str, rhs_name: str, lhs_kind: str, rhs_kind: str) -> None:
        for metric, label in metrics:
            deltas = []
            lhs_values = []
            rhs_values = []

            for seed in seeds:
                if lhs_kind == "replay":
                    lhs_row = by_replay_seed[(lhs_name, seed)]
                    lhs_value = replay_metric(lhs_row, metric)
                else:
                    lhs_row = by_reference_seed[(lhs_name, seed)]
                    lhs_value = reference_metric(lhs_row, metric)

                if rhs_kind == "replay":
                    rhs_row = by_replay_seed[(rhs_name, seed)]
                    rhs_value = replay_metric(rhs_row, metric)
                else:
                    rhs_row = by_reference_seed[(rhs_name, seed)]
                    rhs_value = reference_metric(rhs_row, metric)

                lhs_values.append(lhs_value)
                rhs_values.append(rhs_value)
                deltas.append(lhs_value - rhs_value)

            dm, sd, lo, hi = mean_ci(deltas)
            lm, _, _, _ = mean_ci(lhs_values)
            rm, _, _, _ = mean_ci(rhs_values)

            out_rows.append({
                "comparison": comparison,
                "lhs": lhs_name,
                "rhs": rhs_name,
                "metric": metric,
                "label": label,
                "n": len(deltas),
                "lhs_mean": lm,
                "rhs_mean": rm,
                "delta_mean": dm,
                "delta_std": sd,
                "ci95_low": lo,
                "ci95_high": hi,
            })

    baseline = "measured_table_w0p00"

    for replay_name in replay_names:
        if replay_name != baseline:
            add_delta(
                comparison=f"{replay_name} - {baseline}",
                lhs_name=replay_name,
                rhs_name=baseline,
                lhs_kind="replay",
                rhs_kind="replay",
            )

    for replay_name in replay_names:
        add_delta(
            comparison=f"{replay_name} - risk_policy_fixed",
            lhs_name=replay_name,
            rhs_name="fixed",
            lhs_kind="replay",
            rhs_kind="reference",
        )

    args.csv_output.parent.mkdir(parents=True, exist_ok=True)

    with args.csv_output.open("w", encoding="utf-8", newline="") as f:
        fieldnames = [
            "comparison",
            "lhs",
            "rhs",
            "metric",
            "n",
            "lhs_mean",
            "rhs_mean",
            "delta_mean",
            "delta_std",
            "ci95_low",
            "ci95_high",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in out_rows:
            writer.writerow({name: row[name] for name in fieldnames})

    def rows_for(comparison: str) -> list[dict[str, object]]:
        return [row for row in out_rows if row["comparison"] == comparison]

    def metric_row(comparison: str, metric: str) -> dict[str, object]:
        for row in out_rows:
            if row["comparison"] == comparison and row["metric"] == metric:
                return row
        raise KeyError((comparison, metric))

    lines: list[str] = []

    lines.append("# Paired analysis для measured weight sweep")
    lines.append("")
    lines.append("## Назначение")
    lines.append("")
    lines.append(
        "Для каждого seed сравниваются replay-режимы с разным весом "
        "`uncorrectable_error_count`. Дельты считаются попарно по одному и тому же "
        "потоку событий."
    )
    lines.append("")

    lines.append("## Дельты относительно corrected-only (`w0.00`)")
    lines.append("")
    lines.append("| replay | Δ busy, п.п. | Δ detections | Δ unique |")
    lines.append("|---|---:|---:|---:|")

    for replay_name in replay_names:
        if replay_name == baseline:
            continue

        comparison = f"{replay_name} - {baseline}"
        busy = metric_row(comparison, "busy_percent")
        detections = metric_row(comparison, "uncorrectable_detections")
        unique = metric_row(comparison, "unique_uncorrectable_words")

        lines.append(
            f"| `{replay_name}` | "
            f"{busy['delta_mean']:.3f} [{busy['ci95_low']:.3f}; {busy['ci95_high']:.3f}] | "
            f"{detections['delta_mean']:.1f} [{detections['ci95_low']:.1f}; {detections['ci95_high']:.1f}] | "
            f"{unique['delta_mean']:.3f} [{unique['ci95_low']:.3f}; {unique['ci95_high']:.3f}] |"
        )

    lines.append("")
    lines.append("## Дельты относительно `risk_policy_fixed`")
    lines.append("")
    lines.append("| replay | Δ busy, п.п. | Δ detections | Δ unique |")
    lines.append("|---|---:|---:|---:|")

    for replay_name in replay_names:
        comparison = f"{replay_name} - risk_policy_fixed"
        busy = metric_row(comparison, "busy_percent")
        detections = metric_row(comparison, "uncorrectable_detections")
        unique = metric_row(comparison, "unique_uncorrectable_words")

        lines.append(
            f"| `{replay_name}` | "
            f"{busy['delta_mean']:.3f} [{busy['ci95_low']:.3f}; {busy['ci95_high']:.3f}] | "
            f"{detections['delta_mean']:.1f} [{detections['ci95_low']:.1f}; {detections['ci95_high']:.1f}] | "
            f"{unique['delta_mean']:.3f} [{unique['ci95_low']:.3f}; {unique['ci95_high']:.3f}] |"
        )

    lines.append("")
    lines.append("## Интерпретация")
    lines.append("")
    lines.append(
        "Оптимальный вес выбирается не по одному seed, а по компромиссу между "
        "занятостью и риск-метриками. Особый интерес представляет область, где "
        "занятость остаётся не выше `risk_policy_fixed`, а `unique_uncorrectable_words` "
        "не хуже или ниже reference fixed."
    )
    lines.append("")
    lines.append(
        "Если доверительный интервал по Δ unique включает ноль, корректная "
        "формулировка — не доказанное улучшение, а сопоставимый уровень риска "
        "при другой занятости."
    )

    args.md_output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(args.md_output.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()

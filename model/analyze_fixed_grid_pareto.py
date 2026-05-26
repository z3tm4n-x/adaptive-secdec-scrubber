#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path
from statistics import mean, stdev


def busy_percent(row: dict[str, str]) -> float:
    return float(row["busy_per_mille"]) / 10.0


def summarize(rows: list[dict[str, str]], group_key: str) -> list[dict[str, object]]:
    groups: dict[str, list[dict[str, str]]] = defaultdict(list)

    for row in rows:
        groups[row[group_key]].append(row)

    def sort_key(item: tuple[str, list[dict[str, str]]]):
        key = item[0]
        try:
            return (0, int(key))
        except ValueError:
            return (1, key)

    out: list[dict[str, object]] = []

    for key, items in sorted(groups.items(), key=sort_key):
        unique = [float(row["unique_uncorrectable_words"]) for row in items]
        busy = [busy_percent(row) for row in items]
        scrub = [float(row["scrub_cycles"]) for row in items]

        out.append(
            {
                group_key: key,
                "runs": len(items),
                "unique_mean": mean(unique),
                "unique_std": stdev(unique) if len(unique) > 1 else 0.0,
                "busy_mean": mean(busy),
                "busy_std": stdev(busy) if len(busy) > 1 else 0.0,
                "scrub_mean": mean(scrub),
            }
        )

    return out


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(path)

    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(
    path: Path,
    adaptive_summary: list[dict[str, object]],
    fixed_summary: list[dict[str, object]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "kind",
        "name",
        "runs",
        "unique_mean",
        "unique_std",
        "busy_mean",
        "busy_std",
        "scrub_mean",
    ]

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for row in adaptive_summary:
            writer.writerow(
                {
                    "kind": "adaptive",
                    "name": row["strategy"],
                    "runs": row["runs"],
                    "unique_mean": f"{row['unique_mean']:.6f}",
                    "unique_std": f"{row['unique_std']:.6f}",
                    "busy_mean": f"{row['busy_mean']:.6f}",
                    "busy_std": f"{row['busy_std']:.6f}",
                    "scrub_mean": f"{row['scrub_mean']:.6f}",
                }
            )

        for row in fixed_summary:
            writer.writerow(
                {
                    "kind": "fixed",
                    "name": row["fixed_interval"],
                    "runs": row["runs"],
                    "unique_mean": f"{row['unique_mean']:.6f}",
                    "unique_std": f"{row['unique_std']:.6f}",
                    "busy_mean": f"{row['busy_mean']:.6f}",
                    "busy_std": f"{row['busy_std']:.6f}",
                    "scrub_mean": f"{row['scrub_mean']:.6f}",
                }
            )


def write_markdown(
    path: Path,
    adaptive_summary: list[dict[str, object]],
    fixed_summary: list[dict[str, object]],
    scenario_label: str,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []

    lines.append(f"# Fixed-grid Pareto check для `{scenario_label}`")
    lines.append("")
    lines.append("## Назначение")
    lines.append("")
    lines.append(
        "Проверяется, существует ли постоянный интервал, который одновременно "
        "имеет не большую занятость памяти и не большее среднее число уникальных "
        "неустранимых слов, чем adaptive-стратегия."
    )
    lines.append("")
    lines.append("## Adaptive-точки")
    lines.append("")
    lines.append("| strategy | runs | unique mean ± σ | busy mean ± σ, % | scrub cycles mean |")
    lines.append("|---|---:|---:|---:|---:|")

    for row in adaptive_summary:
        lines.append(
            f"| `{row['strategy']}` | {row['runs']} | "
            f"{row['unique_mean']:.3f} ± {row['unique_std']:.3f} | "
            f"{row['busy_mean']:.3f} ± {row['busy_std']:.3f} | "
            f"{row['scrub_mean']:.1f} |"
        )

    lines.append("")
    lines.append("## Fixed-сетка")
    lines.append("")
    lines.append("| fixed interval | runs | unique mean ± σ | busy mean ± σ, % | scrub cycles mean |")
    lines.append("|---:|---:|---:|---:|---:|")

    for row in fixed_summary:
        lines.append(
            f"| {row['fixed_interval']} | {row['runs']} | "
            f"{row['unique_mean']:.3f} ± {row['unique_std']:.3f} | "
            f"{row['busy_mean']:.3f} ± {row['busy_std']:.3f} | "
            f"{row['scrub_mean']:.1f} |"
        )

    lines.append("")
    lines.append("## Проверка доминирования")
    lines.append("")
    lines.append("| adaptive | adaptive unique | adaptive busy, % | dominating fixed intervals |")
    lines.append("|---|---:|---:|---|")

    for adaptive in adaptive_summary:
        dominating: list[str] = []

        for fixed in fixed_summary:
            if (
                fixed["unique_mean"] <= adaptive["unique_mean"]
                and fixed["busy_mean"] <= adaptive["busy_mean"]
            ):
                dominating.append(str(fixed["fixed_interval"]))

        lines.append(
            f"| `{adaptive['strategy']}` | {adaptive['unique_mean']:.3f} | "
            f"{adaptive['busy_mean']:.3f} | "
            f"{', '.join(dominating) if dominating else 'none'} |"
        )

    lines.append("")
    lines.append("## Интерпретация")
    lines.append("")
    lines.append(
        "Если список `dominating fixed intervals` пуст, adaptive-точка не "
        "доминируется рассмотренной сеткой постоянных интервалов. Если список "
        "непустой, выбранная adaptive-точка не является Парето-эффективной "
        "относительно этой fixed-сетки."
    )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument("--adaptive-series", type=Path, required=True)
    parser.add_argument("--fixed-grid-series", type=Path, required=True)
    parser.add_argument("--scenario-label", required=True)
    parser.add_argument("--csv-output", type=Path, required=True)
    parser.add_argument("--md-output", type=Path, required=True)

    args = parser.parse_args()

    adaptive_rows = read_csv(args.adaptive_series)
    fixed_grid_rows = read_csv(args.fixed_grid_series)

    adaptive_summary = summarize(
        [
            row for row in adaptive_rows
            if row["strategy"] in {"table", "threshold"}
        ],
        "strategy",
    )

    fixed_summary = summarize(fixed_grid_rows, "fixed_interval")

    write_csv(args.csv_output, adaptive_summary, fixed_summary)
    write_markdown(
        args.md_output,
        adaptive_summary,
        fixed_summary,
        scenario_label=args.scenario_label,
    )

    print(f"CSV: {args.csv_output}")
    print(f"MD:  {args.md_output}")
    print(args.md_output.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()

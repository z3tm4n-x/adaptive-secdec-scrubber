#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib.pyplot as plt


def read_eta_summary(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(path)

    with path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)

        required = {
            "strategy",
            "fixed_interval",
            "busy_percent_mean",
            "unique_uncorrectable_mean",
            "uncorrectable_detections_mean",
        }

        if reader.fieldnames is None:
            raise ValueError(f"Missing CSV header in {path}")

        missing = required - set(reader.fieldnames)
        if missing:
            raise ValueError(
                f"Missing columns in {path}: {', '.join(sorted(missing))}"
            )

        return list(reader)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Plot Pareto tradeoff for achievable eta run."
    )

    parser.add_argument(
        "--input",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--output-png",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--output-svg",
        type=Path,
        required=True,
    )

    args = parser.parse_args()

    rows = read_eta_summary(args.input)

    fixed_rows = [
        row for row in rows
        if row["strategy"] == "fixed"
    ]

    adaptive_rows = [
        row for row in rows
        if row["strategy"] != "fixed"
    ]

    fig, ax = plt.subplots(figsize=(6.8, 4.6))

    fixed_busy = [float(row["busy_percent_mean"]) for row in fixed_rows]
    fixed_unique = [float(row["unique_uncorrectable_mean"]) for row in fixed_rows]
    fixed_labels = [row["fixed_interval"] for row in fixed_rows]

    ax.plot(fixed_busy, fixed_unique, marker="o", linestyle="-", label="fixed sweep")

    for x, y, label in zip(fixed_busy, fixed_unique, fixed_labels):
        ax.text(x, y, label, fontsize=8, ha="left", va="bottom")

    for row in adaptive_rows:
        strategy = row["strategy"]
        busy = float(row["busy_percent_mean"])
        unique = float(row["unique_uncorrectable_mean"])

        ax.scatter([busy], [unique], marker="s", s=70, label=strategy)
        ax.text(busy, unique, f" {strategy}", fontsize=9, ha="left", va="center")

    ax.set_xlabel("Memory busy, %")
    ax.set_ylabel("Unique uncorrectable words")
    ax.set_title("Pareto tradeoff: busy time vs unique uncorrectable words")
    ax.grid(True, linewidth=0.4, alpha=0.6)
    ax.legend()

    fig.tight_layout()

    args.output_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output_png, dpi=300)
    fig.savefig(args.output_svg)
    plt.close(fig)

    print(f"Wrote {args.output_png}")
    print(f"Wrote {args.output_svg}")


if __name__ == "__main__":
    main()

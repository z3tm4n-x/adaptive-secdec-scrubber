#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib.pyplot as plt


def read_scenario_summary(path: Path) -> dict[str, dict[str, float]]:
    if not path.exists():
        raise FileNotFoundError(path)

    rows: dict[str, dict[str, float]] = {}

    with path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)

        required = {
            "strategy",
            "corrected_mean",
            "unique_uncorrectable_words_mean",
            "uncorrectable_detections_mean",
            "busy_percent_mean",
        }

        if reader.fieldnames is None:
            raise ValueError(f"Missing CSV header in {path}")

        missing = required - set(reader.fieldnames)
        if missing:
            raise ValueError(
                f"Missing columns in {path}: {', '.join(sorted(missing))}"
            )

        for row in reader:
            strategy = row["strategy"].strip()
            rows[strategy] = {
                "corrected": float(row["corrected_mean"]),
                "unique": float(row["unique_uncorrectable_words_mean"]),
                "detections": float(row["uncorrectable_detections_mean"]),
                "busy": float(row["busy_percent_mean"]),
            }

    return rows


def plot_busy_comparison(
    no_clusters: dict[str, dict[str, float]],
    with_clusters: dict[str, dict[str, float]],
    output_png: Path,
    output_svg: Path,
) -> None:
    strategies = ["fixed", "table", "threshold"]
    x = range(len(strategies))
    width = 0.36

    no_values = [no_clusters[strategy]["busy"] for strategy in strategies]
    with_values = [with_clusters[strategy]["busy"] for strategy in strategies]

    fig, ax = plt.subplots(figsize=(7.0, 4.2))

    left_positions = [i - width / 2 for i in x]
    right_positions = [i + width / 2 for i in x]

    ax.bar(left_positions, no_values, width, label="no clusters")
    ax.bar(right_positions, with_values, width, label="with clusters")

    ax.set_ylabel("Memory busy, %")
    ax.set_xlabel("Strategy")
    ax.set_title("Memory-interface busy time by strategy")
    ax.set_xticks(list(x))
    ax.set_xticklabels(strategies)
    ax.legend()

    for positions, values in [(left_positions, no_values), (right_positions, with_values)]:
        for xpos, value in zip(positions, values):
            ax.text(xpos, value, f"{value:.1f}", ha="center", va="bottom", fontsize=9)

    fig.tight_layout()
    output_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_png, dpi=300)
    fig.savefig(output_svg)
    plt.close(fig)


def plot_cluster_unique_delta(
    no_clusters: dict[str, dict[str, float]],
    with_clusters: dict[str, dict[str, float]],
    output_png: Path,
    output_svg: Path,
) -> None:
    strategies = ["fixed", "table", "threshold"]
    deltas = [
        with_clusters[strategy]["unique"] - no_clusters[strategy]["unique"]
        for strategy in strategies
    ]

    fig, ax = plt.subplots(figsize=(6.4, 4.0))

    ax.bar(strategies, deltas)

    ax.set_ylabel("Δ unique uncorrectable words")
    ax.set_xlabel("Strategy")
    ax.set_title("Instant-cluster contribution to unique uncorrectable words")

    for xpos, value in enumerate(deltas):
        ax.text(xpos, value, f"{value:+.3f}", ha="center", va="bottom", fontsize=9)

    fig.tight_layout()
    output_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_png, dpi=300)
    fig.savefig(output_svg)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate summary figures for paper 5."
    )

    parser.add_argument(
        "--no-clusters-summary",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--with-clusters-summary",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
    )

    args = parser.parse_args()

    no_clusters = read_scenario_summary(args.no_clusters_summary)
    with_clusters = read_scenario_summary(args.with_clusters_summary)

    plot_busy_comparison(
        no_clusters=no_clusters,
        with_clusters=with_clusters,
        output_png=args.output_dir / "paper_busy_comparison.png",
        output_svg=args.output_dir / "paper_busy_comparison.svg",
    )

    plot_cluster_unique_delta(
        no_clusters=no_clusters,
        with_clusters=with_clusters,
        output_png=args.output_dir / "paper_cluster_unique_delta.png",
        output_svg=args.output_dir / "paper_cluster_unique_delta.svg",
    )

    print(f"Wrote figures to {args.output_dir}")


if __name__ == "__main__":
    main()

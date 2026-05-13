#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


EPS = 1e-9


@dataclass(frozen=True)
class EtaPoint:
    strategy: str
    fixed_interval: int | None
    run_count: int
    scrub_cycles: float
    busy_percent: float
    unique_uncorrectable: float
    uncorrectable_detections: float


@dataclass(frozen=True)
class AdaptiveParetoSummary:
    strategy: str
    busy_percent: float
    unique_uncorrectable: float
    uncorrectable_detections: float
    fixed_points_dominated_by_adaptive: int
    fixed_points_dominating_adaptive: int
    fixed_points_tradeoff: int
    cheapest_fixed_unique_interval: int | None
    cheapest_fixed_unique_busy: float | None
    cheapest_fixed_unique_eta_busy: float | None
    cheapest_fixed_detections_interval: int | None
    cheapest_fixed_detections_busy: float | None
    cheapest_fixed_detections_eta_busy: float | None
    cheapest_fixed_both_interval: int | None
    cheapest_fixed_both_busy: float | None
    cheapest_fixed_both_eta_busy: float | None
    pareto_front_member: bool


def parse_optional_int(text: str) -> int | None:
    text = text.strip()

    if not text:
        return None

    return int(text)


def read_summary(path: Path) -> list[EtaPoint]:
    if not path.exists():
        raise FileNotFoundError(path)

    rows: list[EtaPoint] = []

    with path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)

        required = {
            "strategy",
            "fixed_interval",
            "run_count",
            "scrub_cycles_mean",
            "busy_percent_mean",
            "unique_uncorrectable_mean",
            "uncorrectable_detections_mean",
        }

        if reader.fieldnames is None:
            raise ValueError(f"Missing CSV header in {path}")

        missing = required - set(reader.fieldnames)

        if missing:
            raise ValueError(
                f"Missing required columns in {path}: {', '.join(sorted(missing))}"
            )

        for row in reader:
            rows.append(
                EtaPoint(
                    strategy=row["strategy"].strip(),
                    fixed_interval=parse_optional_int(row["fixed_interval"]),
                    run_count=int(row["run_count"]),
                    scrub_cycles=float(row["scrub_cycles_mean"]),
                    busy_percent=float(row["busy_percent_mean"]),
                    unique_uncorrectable=float(row["unique_uncorrectable_mean"]),
                    uncorrectable_detections=float(row["uncorrectable_detections_mean"]),
                )
            )

    return rows


def no_worse(a: float, b: float) -> bool:
    return a <= b + EPS


def strictly_better(a: float, b: float) -> bool:
    return a < b - EPS


def dominates(left: EtaPoint, right: EtaPoint) -> bool:
    """
    Multi-objective dominance for:
      cost: busy_percent, lower is better
      risk 1: unique_uncorrectable, lower is better
      risk 2: uncorrectable_detections, lower is better
    """
    no_worse_all = (
        no_worse(left.busy_percent, right.busy_percent)
        and no_worse(left.unique_uncorrectable, right.unique_uncorrectable)
        and no_worse(left.uncorrectable_detections, right.uncorrectable_detections)
    )

    strictly_better_any = (
        strictly_better(left.busy_percent, right.busy_percent)
        or strictly_better(left.unique_uncorrectable, right.unique_uncorrectable)
        or strictly_better(left.uncorrectable_detections, right.uncorrectable_detections)
    )

    return no_worse_all and strictly_better_any


def fixed_rows(points: Iterable[EtaPoint]) -> list[EtaPoint]:
    return [
        point
        for point in points
        if point.strategy == "fixed" and point.fixed_interval is not None
    ]


def adaptive_rows(points: Iterable[EtaPoint]) -> list[EtaPoint]:
    return [
        point
        for point in points
        if point.strategy != "fixed"
    ]


def cheapest_fixed(
    fixed: list[EtaPoint],
    predicate,
) -> EtaPoint | None:
    candidates = [point for point in fixed if predicate(point)]

    if not candidates:
        return None

    return min(candidates, key=lambda point: point.busy_percent)


def point_is_pareto_member(point: EtaPoint, all_points: list[EtaPoint]) -> bool:
    return not any(
        dominates(other, point)
        for other in all_points
        if other is not point
    )


def eta_busy_or_none(fixed_point: EtaPoint | None, adaptive: EtaPoint) -> float | None:
    if fixed_point is None:
        return None

    if adaptive.busy_percent <= 0.0:
        return None

    return fixed_point.busy_percent / adaptive.busy_percent


def summarize_adaptive(
    adaptive: EtaPoint,
    fixed: list[EtaPoint],
    all_points: list[EtaPoint],
) -> AdaptiveParetoSummary:
    dominated_by_adaptive = [
        point
        for point in fixed
        if dominates(adaptive, point)
    ]

    dominating_adaptive = [
        point
        for point in fixed
        if dominates(point, adaptive)
    ]

    tradeoff = [
        point
        for point in fixed
        if point not in dominated_by_adaptive and point not in dominating_adaptive
    ]

    cheapest_unique = cheapest_fixed(
        fixed,
        lambda point: point.unique_uncorrectable <= adaptive.unique_uncorrectable + EPS,
    )

    cheapest_detections = cheapest_fixed(
        fixed,
        lambda point: point.uncorrectable_detections <= adaptive.uncorrectable_detections + EPS,
    )

    cheapest_both = cheapest_fixed(
        fixed,
        lambda point: (
            point.unique_uncorrectable <= adaptive.unique_uncorrectable + EPS
            and point.uncorrectable_detections <= adaptive.uncorrectable_detections + EPS
        ),
    )

    return AdaptiveParetoSummary(
        strategy=adaptive.strategy,
        busy_percent=adaptive.busy_percent,
        unique_uncorrectable=adaptive.unique_uncorrectable,
        uncorrectable_detections=adaptive.uncorrectable_detections,
        fixed_points_dominated_by_adaptive=len(dominated_by_adaptive),
        fixed_points_dominating_adaptive=len(dominating_adaptive),
        fixed_points_tradeoff=len(tradeoff),
        cheapest_fixed_unique_interval=(
            cheapest_unique.fixed_interval if cheapest_unique is not None else None
        ),
        cheapest_fixed_unique_busy=(
            cheapest_unique.busy_percent if cheapest_unique is not None else None
        ),
        cheapest_fixed_unique_eta_busy=eta_busy_or_none(cheapest_unique, adaptive),
        cheapest_fixed_detections_interval=(
            cheapest_detections.fixed_interval if cheapest_detections is not None else None
        ),
        cheapest_fixed_detections_busy=(
            cheapest_detections.busy_percent if cheapest_detections is not None else None
        ),
        cheapest_fixed_detections_eta_busy=eta_busy_or_none(cheapest_detections, adaptive),
        cheapest_fixed_both_interval=(
            cheapest_both.fixed_interval if cheapest_both is not None else None
        ),
        cheapest_fixed_both_busy=(
            cheapest_both.busy_percent if cheapest_both is not None else None
        ),
        cheapest_fixed_both_eta_busy=eta_busy_or_none(cheapest_both, adaptive),
        pareto_front_member=point_is_pareto_member(adaptive, all_points),
    )


def fmt_optional_int(value: int | None) -> str:
    return "" if value is None else str(value)


def fmt_optional_float(value: float | None) -> str:
    return "" if value is None else f"{value:.6f}"


def write_summary_csv(path: Path, rows: list[AdaptiveParetoSummary]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "strategy",
        "busy_percent",
        "unique_uncorrectable",
        "uncorrectable_detections",
        "fixed_points_dominated_by_adaptive",
        "fixed_points_dominating_adaptive",
        "fixed_points_tradeoff",
        "cheapest_fixed_unique_interval",
        "cheapest_fixed_unique_busy",
        "cheapest_fixed_unique_eta_busy",
        "cheapest_fixed_detections_interval",
        "cheapest_fixed_detections_busy",
        "cheapest_fixed_detections_eta_busy",
        "cheapest_fixed_both_interval",
        "cheapest_fixed_both_busy",
        "cheapest_fixed_both_eta_busy",
        "pareto_front_member",
    ]

    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()

        for row in rows:
            writer.writerow(
                {
                    "strategy": row.strategy,
                    "busy_percent": f"{row.busy_percent:.6f}",
                    "unique_uncorrectable": f"{row.unique_uncorrectable:.6f}",
                    "uncorrectable_detections": f"{row.uncorrectable_detections:.6f}",
                    "fixed_points_dominated_by_adaptive": row.fixed_points_dominated_by_adaptive,
                    "fixed_points_dominating_adaptive": row.fixed_points_dominating_adaptive,
                    "fixed_points_tradeoff": row.fixed_points_tradeoff,
                    "cheapest_fixed_unique_interval": fmt_optional_int(row.cheapest_fixed_unique_interval),
                    "cheapest_fixed_unique_busy": fmt_optional_float(row.cheapest_fixed_unique_busy),
                    "cheapest_fixed_unique_eta_busy": fmt_optional_float(row.cheapest_fixed_unique_eta_busy),
                    "cheapest_fixed_detections_interval": fmt_optional_int(row.cheapest_fixed_detections_interval),
                    "cheapest_fixed_detections_busy": fmt_optional_float(row.cheapest_fixed_detections_busy),
                    "cheapest_fixed_detections_eta_busy": fmt_optional_float(row.cheapest_fixed_detections_eta_busy),
                    "cheapest_fixed_both_interval": fmt_optional_int(row.cheapest_fixed_both_interval),
                    "cheapest_fixed_both_busy": fmt_optional_float(row.cheapest_fixed_both_busy),
                    "cheapest_fixed_both_eta_busy": fmt_optional_float(row.cheapest_fixed_both_eta_busy),
                    "pareto_front_member": int(row.pareto_front_member),
                }
            )


def write_point_classification_csv(
    path: Path,
    fixed: list[EtaPoint],
    adaptive: list[EtaPoint],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "adaptive_strategy",
        "fixed_interval",
        "fixed_busy_percent",
        "fixed_unique_uncorrectable",
        "fixed_uncorrectable_detections",
        "relation_to_adaptive",
    ]

    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()

        for adaptive_point in adaptive:
            for fixed_point in fixed:
                if dominates(adaptive_point, fixed_point):
                    relation = "fixed_dominated_by_adaptive"
                elif dominates(fixed_point, adaptive_point):
                    relation = "fixed_dominates_adaptive"
                else:
                    relation = "tradeoff"

                writer.writerow(
                    {
                        "adaptive_strategy": adaptive_point.strategy,
                        "fixed_interval": fixed_point.fixed_interval,
                        "fixed_busy_percent": f"{fixed_point.busy_percent:.6f}",
                        "fixed_unique_uncorrectable": f"{fixed_point.unique_uncorrectable:.6f}",
                        "fixed_uncorrectable_detections": f"{fixed_point.uncorrectable_detections:.6f}",
                        "relation_to_adaptive": relation,
                    }
                )


def write_markdown(
    path: Path,
    summary_rows: list[AdaptiveParetoSummary],
    fixed: list[EtaPoint],
    adaptive: list[EtaPoint],
    all_points: list[EtaPoint],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    pareto_points = [
        point
        for point in all_points
        if point_is_pareto_member(point, all_points)
    ]

    pareto_points.sort(
        key=lambda point: (
            point.strategy != "fixed",
            point.fixed_interval or 10**9,
            point.strategy,
        )
    )

    lines: list[str] = []

    lines.append("# Pareto-анализ η для achievable RTL mapping")
    lines.append("")
    lines.append("## Назначение")
    lines.append("")
    lines.append(
        "Проверяется multi-objective сравнение adaptive-стратегий с fixed sweep. "
        "Минимизируются одновременно стоимость (`busy_percent`) и две риск-метрики: "
        "`unique_uncorrectable` и `uncorrectable_detections`."
    )
    lines.append("")
    lines.append(
        "Fixed-режим считается доминирующим adaptive только если он одновременно "
        "имеет не большую занятость памяти, не больше уникальных неустранимых слов "
        "и не больше обнаружений неустранимых состояний, причём хотя бы по одной "
        "метрике строго лучше."
    )
    lines.append("")
    lines.append("## Adaptive summary")
    lines.append("")
    lines.append(
        "| strategy | busy, % | unique | detections | dominated fixed | "
        "fixed dominating adaptive | tradeoff fixed | Pareto member |"
    )
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|")

    for row in summary_rows:
        lines.append(
            f"| `{row.strategy}` "
            f"| {row.busy_percent:.3f} "
            f"| {row.unique_uncorrectable:.3f} "
            f"| {row.uncorrectable_detections:.3f} "
            f"| {row.fixed_points_dominated_by_adaptive} "
            f"| {row.fixed_points_dominating_adaptive} "
            f"| {row.fixed_points_tradeoff} "
            f"| {int(row.pareto_front_member)} |"
        )

    lines.append("")
    lines.append("## Constrained fixed comparison")
    lines.append("")
    lines.append(
        "| strategy | cheapest fixed with unique <= adaptive | η busy | "
        "cheapest fixed with detections <= adaptive | η busy | "
        "cheapest fixed with both risks <= adaptive | η busy |"
    )
    lines.append("|---|---:|---:|---:|---:|---:|---:|")

    for row in summary_rows:
        lines.append(
            f"| `{row.strategy}` "
            f"| {fmt_optional_int(row.cheapest_fixed_unique_interval)} "
            f"| {fmt_optional_float(row.cheapest_fixed_unique_eta_busy)} "
            f"| {fmt_optional_int(row.cheapest_fixed_detections_interval)} "
            f"| {fmt_optional_float(row.cheapest_fixed_detections_eta_busy)} "
            f"| {fmt_optional_int(row.cheapest_fixed_both_interval)} "
            f"| {fmt_optional_float(row.cheapest_fixed_both_eta_busy)} |"
        )

    lines.append("")
    lines.append("## Pareto front")
    lines.append("")
    lines.append("| strategy | fixed interval | busy, % | unique | detections |")
    lines.append("|---|---:|---:|---:|---:|")

    for point in pareto_points:
        lines.append(
            f"| `{point.strategy}` "
            f"| {fmt_optional_int(point.fixed_interval)} "
            f"| {point.busy_percent:.3f} "
            f"| {point.unique_uncorrectable:.3f} "
            f"| {point.uncorrectable_detections:.3f} |"
        )

    lines.append("")
    lines.append("## Интерпретация")
    lines.append("")
    lines.append(
        "Если `fixed dominating adaptive = 0`, то в рассмотренном fixed sweep нет "
        "постоянного интервала, который одновременно дешевле adaptive и не хуже "
        "по обеим риск-метрикам."
    )
    lines.append("")
    lines.append(
        "Если `cheapest fixed with both risks <= adaptive` отсутствует, это означает, "
        "что fixed sweep не содержит точки, которая одновременно сохраняет обе "
        "риск-метрики adaptive. В этом случае single-metric matching по detections "
        "или unique следует интерпретировать осторожно: он может игнорировать "
        "ухудшение второй риск-метрики."
    )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Pareto/constrained comparison for ETA summary."
    )

    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="eta_summary.csv produced by run_eta_verification.py",
    )

    parser.add_argument(
        "--summary-csv",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--classification-csv",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--md-output",
        type=Path,
        required=True,
    )

    args = parser.parse_args()

    points = read_summary(args.input)
    fixed = fixed_rows(points)
    adaptive = adaptive_rows(points)

    if not fixed:
        raise ValueError("No fixed points found")

    if not adaptive:
        raise ValueError("No adaptive points found")

    summary_rows = [
        summarize_adaptive(
            adaptive=adaptive_point,
            fixed=fixed,
            all_points=points,
        )
        for adaptive_point in adaptive
    ]

    write_summary_csv(args.summary_csv, summary_rows)
    write_point_classification_csv(args.classification_csv, fixed, adaptive)
    write_markdown(args.md_output, summary_rows, fixed, adaptive, points)

    print(f"Pareto summary CSV: {args.summary_csv}")
    print(f"Pareto classification CSV: {args.classification_csv}")
    print(f"Pareto report: {args.md_output}")


if __name__ == "__main__":
    main()
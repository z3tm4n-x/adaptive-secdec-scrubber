#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import math
import subprocess
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, pstdev


from generate_fault_events import read_upsets_xlsx, select_window


STRATEGY_ORDER = ["fixed", "table", "threshold"]

INPUT_RESULT_COLUMNS = [
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


@dataclass
class RawRow:
    seed: int
    fixed_interval: int | None
    strategy: str
    total_cycles: int
    scrub_cycles: int
    reads: int
    writes: int
    corrected: int
    uncorrectable_detections: int
    unique_uncorrectable_words: int
    interval_switches: int
    memory_busy_cycles: int
    busy_per_mille: int


@dataclass
class SummaryRow:
    strategy: str
    fixed_interval: int | None
    run_count: int
    scrub_cycles_mean: float
    scrub_cycles_std: float
    busy_percent_mean: float
    busy_percent_std: float
    unique_uncorrectable_mean: float
    unique_uncorrectable_std: float
    corrected_mean: float
    corrected_std: float
    uncorrectable_detections_mean: float
    uncorrectable_detections_std: float

MATCHING_METRICS = (
    "unique_uncorrectable_words",
    "uncorrectable_detections",
)


@dataclass
class PracticalEtaRow:
    adaptive_strategy: str
    matching_metric: str
    window_cv2: float
    eta_theory: float

    adaptive_scrub_cycles: float
    adaptive_busy_percent: float
    adaptive_unique_uncorrectable: float
    adaptive_uncorrectable_detections: float

    matched_fixed_interval: int
    matched_fixed_scrub_cycles: float
    matched_fixed_busy_percent: float
    matched_fixed_unique_uncorrectable: float
    matched_fixed_uncorrectable_detections: float

    eta_practical_scrub_cycles: float
    eta_practical_busy_percent: float
    metric_difference: float

def parse_intervals(text: str) -> list[int]:
    result: list[int] = []

    for part in text.replace(";", ",").split(","):
        part = part.strip()

        if not part:
            continue

        value = int(part)

        if value <= 0:
            raise ValueError(f"Fixed interval must be positive: {value}")

        result.append(value)

    if not result:
        raise ValueError("No fixed intervals provided")

    return result

def parse_int_list(text: str, expected_count: int, name: str) -> list[int]:
    values: list[int] = []

    for raw_part in text.replace(";", ",").split(","):
        part = raw_part.strip()

        if not part:
            continue

        value = int(part)

        if value <= 0:
            raise ValueError(f"{name} values must be positive: {value}")

        values.append(value)

    if len(values) != expected_count:
        raise ValueError(
            f"{name} must contain exactly {expected_count} values, got {len(values)}"
        )

    return values


def parse_level_thresholds(text: str) -> list[int]:
    values: list[int] = []

    for raw_part in text.replace(";", ",").split(","):
        part = raw_part.strip()

        if not part:
            continue

        value = int(part)

        if value < 0 or value > 7:
            raise ValueError(f"threshold level must be in 0..7: {value}")

        values.append(value)

    if len(values) != 4:
        raise ValueError(
            f"threshold-levels must contain exactly 4 values, got {len(values)}"
        )

    return values


def read_strategy_result(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Strategy result CSV not found: {path}")

    with path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        rows = list(reader)

    if not rows:
        raise ValueError(f"No rows found in {path}")

    missing = [column for column in INPUT_RESULT_COLUMNS if column not in rows[0]]

    if missing:
        raise ValueError("Missing columns in strategy result: " + ", ".join(missing))

    return rows


def int_field(row: dict[str, str], key: str) -> int:
    return int(row[key].strip())


def convert_result_row(
    row: dict[str, str],
    seed: int,
    fixed_interval: int | None,
) -> RawRow:
    return RawRow(
        seed=seed,
        fixed_interval=fixed_interval,
        strategy=row["strategy"].strip(),
        total_cycles=int_field(row, "total_cycles"),
        scrub_cycles=int_field(row, "scrub_cycles"),
        reads=int_field(row, "reads"),
        writes=int_field(row, "writes"),
        corrected=int_field(row, "corrected"),
        uncorrectable_detections=int_field(row, "uncorrectable_detections"),
        unique_uncorrectable_words=int_field(row, "unique_uncorrectable_words"),
        interval_switches=int_field(row, "interval_switches"),
        memory_busy_cycles=int_field(row, "memory_busy_cycles"),
        busy_per_mille=int_field(row, "busy_per_mille"),
    )


def run_one_configuration(
    make_command: str,
    seed: int,
    fixed_interval: int,
    total_cycles: int,
    window_size: int,
    event_count: int,
    paired_event_count: int,
    pair_gap_min: int,
    pair_gap_max: int,
    cluster_event_count: int,
    cluster_bit_count: int,
    control_quantization: str,
    control_source: str,
    control_policy_schedule: str,
    control_policy_level_map_output: str,
    safe_interval: int,
    level_intervals: list[int],
    threshold_levels: list[int],
    threshold_intervals: list[int],
) -> list[dict[str, str]]:
    command = [
        make_command,
        "test_strategy_comparison",
        "FAULT_SCENARIO=upsets",
        f"FAULT_TOTAL_CYCLES={total_cycles}",
        f"FAULT_WINDOW_SIZE={window_size}",
        f"FAULT_EVENT_COUNT={event_count}",
        f"FAULT_PAIRED_EVENT_COUNT={paired_event_count}",
        f"FAULT_PAIR_GAP_MIN={pair_gap_min}",
        f"FAULT_PAIR_GAP_MAX={pair_gap_max}",
        f"FAULT_CLUSTER_EVENT_COUNT={cluster_event_count}",
        f"FAULT_CLUSTER_BIT_COUNT={cluster_bit_count}",
        f"FAULT_SEED={seed}",
        f"FIXED_INTERVAL={fixed_interval}",
        f"CONTROL_QUANTIZATION={control_quantization}",
        f"CONTROL_SOURCE={control_source}",
        f"CONTROL_POLICY_SCHEDULE={control_policy_schedule}",
        f"CONTROL_POLICY_LEVEL_MAP_OUTPUT={control_policy_level_map_output}",
        f"SAFE_INTERVAL={safe_interval}",
        f"LEVEL0_INTERVAL={level_intervals[0]}",
        f"LEVEL1_INTERVAL={level_intervals[1]}",
        f"LEVEL2_INTERVAL={level_intervals[2]}",
        f"LEVEL3_INTERVAL={level_intervals[3]}",
        f"LEVEL4_INTERVAL={level_intervals[4]}",
        f"LEVEL5_INTERVAL={level_intervals[5]}",
        f"LEVEL6_INTERVAL={level_intervals[6]}",
        f"LEVEL7_INTERVAL={level_intervals[7]}",
        f"THRESHOLD_LOW_TO_MEDIUM={threshold_levels[0]}",
        f"THRESHOLD_MEDIUM_TO_LOW={threshold_levels[1]}",
        f"THRESHOLD_MEDIUM_TO_HIGH={threshold_levels[2]}",
        f"THRESHOLD_HIGH_TO_MEDIUM={threshold_levels[3]}",
        f"THRESHOLD_LOW_INTERVAL={threshold_intervals[0]}",
        f"THRESHOLD_MEDIUM_INTERVAL={threshold_intervals[1]}",
        f"THRESHOLD_HIGH_INTERVAL={threshold_intervals[2]}",
    ]

    print("=" * 80)
    print(f"ETA run: seed={seed}, fixed_interval={fixed_interval}")
    print(" ".join(command))
    print("=" * 80)

    subprocess.run(command, check=True)

    return read_strategy_result(Path("results/tables/strategy_comparison.csv"))


def collect_raw_rows(args: argparse.Namespace, intervals: list[int]) -> list[RawRow]:
    raw_rows: list[RawRow] = []

    for seed in range(args.seed_start, args.seed_start + args.seed_count):
        adaptive_rows_captured = False

        for fixed_interval in intervals:
            rows = run_one_configuration(
                make_command=args.make_command,
                seed=seed,
                fixed_interval=fixed_interval,
                total_cycles=args.total_cycles,
                window_size=args.window_size,
                event_count=args.event_count,
                paired_event_count=args.paired_event_count,
                pair_gap_min=args.pair_gap_min,
                pair_gap_max=args.pair_gap_max,
                cluster_event_count=args.cluster_event_count,
                cluster_bit_count=args.cluster_bit_count,
                control_quantization=args.control_quantization,
                control_source=args.control_source,
                control_policy_schedule=args.control_policy_schedule,
                control_policy_level_map_output=args.control_policy_level_map_output,
                safe_interval=args.safe_interval,
                level_intervals=args.level_intervals_parsed,
                threshold_levels=args.threshold_levels_parsed,
                threshold_intervals=args.threshold_intervals_parsed,
            )

            for row in rows:
                strategy = row["strategy"].strip()

                if strategy == "fixed":
                    raw_rows.append(
                        convert_result_row(
                            row=row,
                            seed=seed,
                            fixed_interval=fixed_interval,
                        )
                    )
                elif not adaptive_rows_captured and strategy in {"table", "threshold"}:
                    raw_rows.append(
                        convert_result_row(
                            row=row,
                            seed=seed,
                            fixed_interval=None,
                        )
                    )

            adaptive_rows_captured = True

    return raw_rows


def std_or_zero(values: list[float]) -> float:
    if len(values) <= 1:
        return 0.0

    return pstdev(values)


def summarize(raw_rows: list[RawRow]) -> list[SummaryRow]:
    groups: dict[tuple[str, int | None], list[RawRow]] = {}

    for row in raw_rows:
        groups.setdefault((row.strategy, row.fixed_interval), []).append(row)

    summaries: list[SummaryRow] = []

    for (strategy, fixed_interval), rows in groups.items():
        scrub_cycles = [float(row.scrub_cycles) for row in rows]
        busy_percent = [float(row.busy_per_mille) / 10.0 for row in rows]
        unique = [float(row.unique_uncorrectable_words) for row in rows]
        corrected = [float(row.corrected) for row in rows]
        uncorrectable = [float(row.uncorrectable_detections) for row in rows]

        summaries.append(
            SummaryRow(
                strategy=strategy,
                fixed_interval=fixed_interval,
                run_count=len(rows),
                scrub_cycles_mean=mean(scrub_cycles),
                scrub_cycles_std=std_or_zero(scrub_cycles),
                busy_percent_mean=mean(busy_percent),
                busy_percent_std=std_or_zero(busy_percent),
                unique_uncorrectable_mean=mean(unique),
                unique_uncorrectable_std=std_or_zero(unique),
                corrected_mean=mean(corrected),
                corrected_std=std_or_zero(corrected),
                uncorrectable_detections_mean=mean(uncorrectable),
                uncorrectable_detections_std=std_or_zero(uncorrectable),
            )
        )

    order = {name: index for index, name in enumerate(STRATEGY_ORDER)}

    return sorted(
        summaries,
        key=lambda row: (
            order.get(row.strategy, len(order)),
            -1 if row.fixed_interval is None else row.fixed_interval,
        ),
    )


def compute_window_stats(input_path: Path, start_index: int, window_size: int) -> tuple[float, float, float]:
    values = select_window(read_upsets_xlsx(input_path), start_index, window_size)
    window_mean = mean(values)
    window_std = pstdev(values)
    cv2 = (window_std / window_mean) ** 2 if window_mean > 0.0 else 0.0
    eta_theory = 1.0 + cv2

    return window_mean, cv2, eta_theory


def write_raw_csv(raw_rows: list[RawRow], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "seed",
        "fixed_interval",
        "strategy",
        "total_cycles",
        "scrub_cycles",
        "reads",
        "writes",
        "corrected",
        "uncorrectable_detections",
        "unique_uncorrectable_words",
        "interval_switches",
        "memory_busy_cycles",
        "busy_percent",
    ]

    with output_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()

        for row in raw_rows:
            writer.writerow(
                {
                    "seed": row.seed,
                    "fixed_interval": "" if row.fixed_interval is None else row.fixed_interval,
                    "strategy": row.strategy,
                    "total_cycles": row.total_cycles,
                    "scrub_cycles": row.scrub_cycles,
                    "reads": row.reads,
                    "writes": row.writes,
                    "corrected": row.corrected,
                    "uncorrectable_detections": row.uncorrectable_detections,
                    "unique_uncorrectable_words": row.unique_uncorrectable_words,
                    "interval_switches": row.interval_switches,
                    "memory_busy_cycles": row.memory_busy_cycles,
                    "busy_percent": f"{row.busy_per_mille / 10.0:.6f}",
                }
            )


def write_summary_csv(summaries: list[SummaryRow], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "strategy",
        "fixed_interval",
        "run_count",
        "scrub_cycles_mean",
        "scrub_cycles_std",
        "busy_percent_mean",
        "busy_percent_std",
        "unique_uncorrectable_mean",
        "unique_uncorrectable_std",
        "corrected_mean",
        "corrected_std",
        "uncorrectable_detections_mean",
        "uncorrectable_detections_std",
    ]

    with output_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()

        for row in summaries:
            writer.writerow(
                {
                    "strategy": row.strategy,
                    "fixed_interval": "" if row.fixed_interval is None else row.fixed_interval,
                    "run_count": row.run_count,
                    "scrub_cycles_mean": f"{row.scrub_cycles_mean:.6f}",
                    "scrub_cycles_std": f"{row.scrub_cycles_std:.6f}",
                    "busy_percent_mean": f"{row.busy_percent_mean:.6f}",
                    "busy_percent_std": f"{row.busy_percent_std:.6f}",
                    "unique_uncorrectable_mean": f"{row.unique_uncorrectable_mean:.6f}",
                    "unique_uncorrectable_std": f"{row.unique_uncorrectable_std:.6f}",
                    "corrected_mean": f"{row.corrected_mean:.6f}",
                    "corrected_std": f"{row.corrected_std:.6f}",
                    "uncorrectable_detections_mean": f"{row.uncorrectable_detections_mean:.6f}",
                    "uncorrectable_detections_std": f"{row.uncorrectable_detections_std:.6f}",
                }
            )


def fixed_summaries(summaries: list[SummaryRow]) -> list[SummaryRow]:
    return [
        row for row in summaries
        if row.strategy == "fixed" and row.fixed_interval is not None
    ]


def adaptive_summaries(summaries: list[SummaryRow]) -> list[SummaryRow]:
    return [
        row for row in summaries
        if row.strategy in {"table", "threshold"} and row.fixed_interval is None
    ]


def summary_metric_value(row: SummaryRow, metric: str) -> float:
    if metric == "unique_uncorrectable_words":
        return row.unique_uncorrectable_mean

    if metric == "uncorrectable_detections":
        return row.uncorrectable_detections_mean

    raise ValueError(f"Unsupported matching metric: {metric}")


def nearest_fixed_by_metric(
    fixed_rows: list[SummaryRow],
    target_value: float,
    metric: str,
) -> SummaryRow:
    if not fixed_rows:
        raise ValueError("No fixed sweep rows available")

    return min(
        fixed_rows,
        key=lambda row: abs(summary_metric_value(row, metric) - target_value),
    )


def compute_practical_eta_rows(
    summaries: list[SummaryRow],
    window_cv2: float,
    eta_theory: float,
) -> list[PracticalEtaRow]:
    fixed_rows = fixed_summaries(summaries)
    adaptive_rows = adaptive_summaries(summaries)

    rows: list[PracticalEtaRow] = []

    for adaptive in adaptive_rows:
        for metric in MATCHING_METRICS:
            adaptive_metric_value = summary_metric_value(adaptive, metric)

            matched = nearest_fixed_by_metric(
                fixed_rows=fixed_rows,
                target_value=adaptive_metric_value,
                metric=metric,
            )

            eta_scrub = (
                matched.scrub_cycles_mean / adaptive.scrub_cycles_mean
                if adaptive.scrub_cycles_mean > 0.0
                else 0.0
            )

            eta_busy = (
                matched.busy_percent_mean / adaptive.busy_percent_mean
                if adaptive.busy_percent_mean > 0.0
                else 0.0
            )

            metric_difference = (
                summary_metric_value(matched, metric)
                - adaptive_metric_value
            )

            if matched.fixed_interval is None:
                raise ValueError("Matched fixed row has no fixed_interval")

            rows.append(
                PracticalEtaRow(
                    adaptive_strategy=adaptive.strategy,
                    matching_metric=metric,
                    window_cv2=window_cv2,
                    eta_theory=eta_theory,
                    adaptive_scrub_cycles=adaptive.scrub_cycles_mean,
                    adaptive_busy_percent=adaptive.busy_percent_mean,
                    adaptive_unique_uncorrectable=adaptive.unique_uncorrectable_mean,
                    adaptive_uncorrectable_detections=adaptive.uncorrectable_detections_mean,
                    matched_fixed_interval=matched.fixed_interval,
                    matched_fixed_scrub_cycles=matched.scrub_cycles_mean,
                    matched_fixed_busy_percent=matched.busy_percent_mean,
                    matched_fixed_unique_uncorrectable=matched.unique_uncorrectable_mean,
                    matched_fixed_uncorrectable_detections=matched.uncorrectable_detections_mean,
                    eta_practical_scrub_cycles=eta_scrub,
                    eta_practical_busy_percent=eta_busy,
                    metric_difference=metric_difference,
                )
            )

    return rows


def write_eta_summary_csv(
    summaries: list[SummaryRow],
    output_path: Path,
    window_cv2: float,
    eta_theory: float,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    practical_rows = compute_practical_eta_rows(
        summaries=summaries,
        window_cv2=window_cv2,
        eta_theory=eta_theory,
    )

    fieldnames = [
        "adaptive_strategy",
        "matching_metric",
        "window_cv2",
        "eta_theory_1_plus_cv2",
        "adaptive_scrub_cycles",
        "adaptive_busy_percent",
        "adaptive_unique_uncorrectable",
        "adaptive_uncorrectable_detections",
        "matched_fixed_interval",
        "matched_fixed_scrub_cycles",
        "matched_fixed_busy_percent",
        "matched_fixed_unique_uncorrectable",
        "matched_fixed_uncorrectable_detections",
        "eta_practical_scrub_cycles",
        "eta_practical_busy_percent",
        "metric_difference",
    ]

    with output_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()

        for row in practical_rows:
            writer.writerow(
                {
                    "adaptive_strategy": row.adaptive_strategy,
                    "matching_metric": row.matching_metric,
                    "window_cv2": f"{row.window_cv2:.9f}",
                    "eta_theory_1_plus_cv2": f"{row.eta_theory:.9f}",
                    "adaptive_scrub_cycles": f"{row.adaptive_scrub_cycles:.6f}",
                    "adaptive_busy_percent": f"{row.adaptive_busy_percent:.6f}",
                    "adaptive_unique_uncorrectable": f"{row.adaptive_unique_uncorrectable:.6f}",
                    "adaptive_uncorrectable_detections": f"{row.adaptive_uncorrectable_detections:.6f}",
                    "matched_fixed_interval": row.matched_fixed_interval,
                    "matched_fixed_scrub_cycles": f"{row.matched_fixed_scrub_cycles:.6f}",
                    "matched_fixed_busy_percent": f"{row.matched_fixed_busy_percent:.6f}",
                    "matched_fixed_unique_uncorrectable": f"{row.matched_fixed_unique_uncorrectable:.6f}",
                    "matched_fixed_uncorrectable_detections": f"{row.matched_fixed_uncorrectable_detections:.6f}",
                    "eta_practical_scrub_cycles": f"{row.eta_practical_scrub_cycles:.6f}",
                    "eta_practical_busy_percent": f"{row.eta_practical_busy_percent:.6f}",
                    "metric_difference": f"{row.metric_difference:.6f}",
                }
            )


def write_markdown(
    summaries: list[SummaryRow],
    output_path: Path,
    window_mean: float,
    window_cv2: float,
    eta_theory: float,
    args: argparse.Namespace,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fixed_rows = fixed_summaries(summaries)
    adaptive_rows = adaptive_summaries(summaries)

    lines: list[str] = []

    lines.append("# Верификация η на RTL-стенде")
    lines.append("")
    lines.append("## Параметры эксперимента")
    lines.append("")
    lines.append(f"- Окно ν(t): {args.window_size} точек")
    lines.append(f"- Модельных тактов: {args.total_cycles}")
    lines.append(f"- Seed count: {args.seed_count}")
    lines.append(f"- Одиночных событий: {args.event_count}")
    lines.append(f"- Накопительных пар: {args.paired_event_count}")
    lines.append(f"- Мгновенных кластеров: {args.cluster_event_count}")
    lines.append(f"- Квантование управляющего уровня: `{args.control_quantization}`")
    lines.append(f"- Источник управляющего потока: `{args.control_source}`")
    lines.append(f"- Risk-policy level map output: `{args.control_policy_level_map_output}`")
    lines.append(
        "- Level intervals: "
        + ", ".join(str(value) for value in args.level_intervals_parsed)
    )
    lines.append(
        "- Threshold levels: "
        + ", ".join(str(value) for value in args.threshold_levels_parsed)
    )
    lines.append(
        "- Threshold intervals: "
        + ", ".join(str(value) for value in args.threshold_intervals_parsed)
    )
    lines.append(f"- Sweep fixed_interval: {', '.join(str(v) for v in parse_intervals(args.fixed_intervals))}")
    lines.append("")
    lines.append("## Статистика окна ν(t)")
    lines.append("")
    lines.append(f"- Среднее ν(t): {window_mean:.9g}")
    lines.append(f"- CV² окна: {window_cv2:.9g}")
    lines.append(f"- Теоретическое η = 1 + CV²: {eta_theory:.9g}")
    lines.append("")
    lines.append("## Fixed sweep")
    lines.append("")
    lines.append(
        "| fixed_interval | Прогонов | scrub_cycles, mean ± σ | "
        "busy, mean ± σ, % | unique_uncorrectable, mean ± σ | "
        "uncorrectable_detections, mean ± σ |"
    )
    lines.append("|---:|---:|---:|---:|---:|---:|")

    for row in sorted(fixed_rows, key=lambda item: item.fixed_interval or 0):
        lines.append(
            f"| {row.fixed_interval} "
            f"| {row.run_count} "
            f"| {row.scrub_cycles_mean:.3f} ± {row.scrub_cycles_std:.3f} "
            f"| {row.busy_percent_mean:.3f} ± {row.busy_percent_std:.3f} "
            f"| {row.unique_uncorrectable_mean:.3f} ± {row.unique_uncorrectable_std:.3f} "
            f"| {row.uncorrectable_detections_mean:.3f} ± {row.uncorrectable_detections_std:.3f} |"
        )

    lines.append("")
    lines.append("## Адаптивные точки")
    lines.append("")
    lines.append(
        "| strategy | Прогонов | scrub_cycles, mean ± σ | "
        "busy, mean ± σ, % | unique_uncorrectable, mean ± σ | "
        "uncorrectable_detections, mean ± σ |"
    )
    lines.append("|---|---:|---:|---:|---:|---:|")

    for row in adaptive_rows:
        lines.append(
            f"| `{row.strategy}` "
            f"| {row.run_count} "
            f"| {row.scrub_cycles_mean:.3f} ± {row.scrub_cycles_std:.3f} "
            f"| {row.busy_percent_mean:.3f} ± {row.busy_percent_std:.3f} "
            f"| {row.unique_uncorrectable_mean:.3f} ± {row.unique_uncorrectable_std:.3f} "
            f"| {row.uncorrectable_detections_mean:.3f} ± {row.uncorrectable_detections_std:.3f} |"
        )

    lines.append("")
    lines.append("## Практическая оценка η")
    lines.append("")
    lines.append(
        "| adaptive strategy | matching metric | matched fixed_interval | "
        "η_practical по scrub_cycles | η_practical по busy | "
        "metric difference | η_theory |"
    )
    lines.append("|---|---|---:|---:|---:|---:|---:|")

    practical_rows = compute_practical_eta_rows(
        summaries=summaries,
        window_cv2=window_cv2,
        eta_theory=eta_theory,
    )

    for row in practical_rows:
        lines.append(
            f"| `{row.adaptive_strategy}` "
            f"| `{row.matching_metric}` "
            f"| {row.matched_fixed_interval} "
            f"| {row.eta_practical_scrub_cycles:.3f} "
            f"| {row.eta_practical_busy_percent:.3f} "
            f"| {row.metric_difference:+.3f} "
            f"| {row.eta_theory:.3f} |"
        )

    lines.append("")
    lines.append("## Интерпретация")
    lines.append("")
    lines.append(
        "η_theory = 1 + CV² относится к идеализированному классу "
        "пропорциональных стратегий при сравнении с постоянным интервалом "
        "на одинаковом уровне риска. Данный эксперимент строит практическую "
        "оценку η на RTL-стенде: fixed_interval варьируется, а затем для "
        "каждой адаптивной стратегии выбирается ближайшая fixed-точка по "
        "двум метрикам риска: числу уникальных неустранимых слов и числу "
        "обнаружений неустранимых состояний."
    )
    lines.append("")
    lines.append(
        "Ожидаемое отличие η_practical от η_theory связано с дискретностью "
        "интервалов, квантованием ν(t) в 3-битный управляющий уровень, "
        "малой stress-test памятью и конечным числом инжектированных событий."
    )

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def plot_eta_curve(summaries: list[SummaryRow], output_path: Path) -> None:
    import matplotlib.pyplot as plt

    fixed_rows = sorted(
        fixed_summaries(summaries),
        key=lambda row: row.scrub_cycles_mean,
    )

    adaptive_rows = adaptive_summaries(summaries)

    if not fixed_rows:
        raise ValueError("No fixed rows to plot")

    x_fixed = [row.scrub_cycles_mean for row in fixed_rows]
    y_fixed = [row.unique_uncorrectable_mean for row in fixed_rows]
    yerr_fixed = [row.unique_uncorrectable_std for row in fixed_rows]

    plt.figure(figsize=(7.6, 5.2))
    plt.errorbar(
        x_fixed,
        y_fixed,
        yerr=yerr_fixed,
        marker="o",
        capsize=5,
        label="fixed sweep",
    )

    for row in adaptive_rows:
        plt.scatter(
            [row.scrub_cycles_mean],
            [row.unique_uncorrectable_mean],
            marker="x",
            s=80,
            label=row.strategy,
        )
        plt.text(
            row.scrub_cycles_mean,
            row.unique_uncorrectable_mean,
            f" {row.strategy}",
            ha="left",
            va="center",
        )

    for row in fixed_rows:
        plt.text(
            row.scrub_cycles_mean,
            row.unique_uncorrectable_mean,
            f" {row.fixed_interval}",
            ha="left",
            va="bottom",
        )

    plt.xlabel("Среднее число циклов скраббинга")
    plt.ylabel("Среднее число уникальных неустранимых слов")
    plt.title("Оценка η: fixed sweep и адаптивные стратегии")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=300)
    plt.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run eta verification via fixed-interval sweep."
    )

    parser.add_argument("--input", type=Path, default=Path("data/upsets.xlsx"))
    parser.add_argument("--start-index", type=int, default=0)
    parser.add_argument("--window-size", type=int, required=True)
    parser.add_argument("--total-cycles", type=int, required=True)

    parser.add_argument("--seed-start", type=int, default=1)
    parser.add_argument("--seed-count", type=int, default=10)

    parser.add_argument("--event-count", type=int, required=True)
    parser.add_argument("--paired-event-count", type=int, required=True)
    parser.add_argument("--pair-gap-min", type=int, required=True)
    parser.add_argument("--pair-gap-max", type=int, required=True)

    parser.add_argument("--cluster-event-count", type=int, default=0)
    parser.add_argument("--cluster-bit-count", type=int, default=2)

    parser.add_argument(
        "--control-quantization",
        default="linear_max",
        choices=["linear_max", "percentile_tail"],
        help="Control-level quantization mode passed to fault generator.",
    )

    parser.add_argument(
        "--control-source",
        default="quantization",
        choices=["quantization", "risk_policy"],
        help="Control source passed to fault generator.",
    )

    parser.add_argument(
        "--control-policy-schedule",
        default="results/paper/tables/risk_policy_schedule.csv",
        help="Risk policy schedule path passed to fault generator.",
    )

    parser.add_argument(
        "--control-policy-level-map-output",
        default="results/tables/control_policy_level_map.csv",
        help="Risk policy level-map output path passed to fault generator.",
    )

    parser.add_argument(
        "--safe-interval",
        type=int,
        default=5,
        help="Safe interval passed to RTL testbench.",
    )

    parser.add_argument(
        "--level-intervals",
        default="100,80,60,40,25,15,10,5",
        help="Comma-separated LEVEL0..LEVEL7 model intervals.",
    )

    parser.add_argument(
        "--threshold-levels",
        default="3,1,6,4",
        help=(
            "Comma-separated threshold levels: "
            "low_to_medium,medium_to_low,medium_to_high,high_to_medium."
        ),
    )

    parser.add_argument(
        "--threshold-intervals",
        default="100,25,8",
        help="Comma-separated threshold low,medium,high model intervals.",
    )

    parser.add_argument(
        "--fixed-intervals",
        type=str,
        default="20,30,40,60,80,100,150,200",
        help="Comma-separated list of fixed intervals.",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results/paper/eta"),
    )

    parser.add_argument(
        "--make-command",
        type=str,
        default="make",
    )

    args = parser.parse_args()

    intervals = parse_intervals(args.fixed_intervals)

    args.level_intervals_parsed = parse_int_list(
        args.level_intervals,
        expected_count=8,
        name="level-intervals",
    )

    args.threshold_levels_parsed = parse_level_thresholds(args.threshold_levels)

    args.threshold_intervals_parsed = parse_int_list(
        args.threshold_intervals,
        expected_count=3,
        name="threshold-intervals",
    )

    if args.safe_interval <= 0:
        raise ValueError("safe-interval must be positive")

    window_mean, window_cv2, eta_theory = compute_window_stats(
        input_path=args.input,
        start_index=args.start_index,
        window_size=args.window_size,
    )

    raw_rows = collect_raw_rows(args, intervals)
    summaries = summarize(raw_rows)

    tables_dir = args.output_dir / "tables"
    figures_dir = args.output_dir / "figures"

    tables_dir = args.output_dir / "tables"
    figures_dir = args.output_dir / "figures"

    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    raw_csv = tables_dir / "eta_raw.csv"
    summary_csv = tables_dir / "eta_summary.csv"
    practical_csv = tables_dir / "eta_practical_summary.csv"
    markdown_path = tables_dir / "eta_verification.md"
    figure_path = figures_dir / "eta_curve.png"

    write_raw_csv(
        raw_rows=raw_rows,
        output_path=raw_csv,
    )

    write_summary_csv(
        summaries=summaries,
        output_path=summary_csv,
    )

    write_eta_summary_csv(
        summaries=summaries,
        output_path=practical_csv,
        window_cv2=window_cv2,
        eta_theory=eta_theory,
    )

    write_markdown(
        summaries=summaries,
        output_path=markdown_path,
        window_mean=window_mean,
        window_cv2=window_cv2,
        eta_theory=eta_theory,
        args=args,
    )

    plot_eta_curve(
        summaries=summaries,
        output_path=figure_path,
    )

    print(f"Raw CSV: {raw_csv}")
    print(f"Summary CSV: {summary_csv}")
    print(f"Practical eta CSV: {practical_csv}")
    print(f"Markdown report: {markdown_path}")
    print(f"Figure: {figure_path}")

if __name__ == "__main__":
    main()
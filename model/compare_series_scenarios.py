#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import math
from dataclasses import dataclass
from pathlib import Path


REQUIRED_COLUMNS = [
    "strategy",
    "run_count",
    "corrected_mean",
    "corrected_stddev",
    "uncorrectable_detections_mean",
    "uncorrectable_detections_stddev",
    "unique_uncorrectable_words_mean",
    "unique_uncorrectable_words_stddev",
    "busy_percent_mean",
    "busy_percent_stddev",
    "interval_switches_mean",
    "interval_switches_stddev",
]

STRATEGY_ORDER = ["fixed", "table", "threshold"]


@dataclass(frozen=True)
class ScenarioInput:
    name: str
    path: Path


@dataclass
class ScenarioRow:
    scenario: str
    strategy: str
    run_count: int
    corrected_mean: float
    corrected_stddev: float
    uncorrectable_detections_mean: float
    uncorrectable_detections_stddev: float
    unique_uncorrectable_words_mean: float
    unique_uncorrectable_words_stddev: float
    busy_percent_mean: float
    busy_percent_stddev: float
    interval_switches_mean: float
    interval_switches_stddev: float


def read_summary(path: Path, scenario_name: str) -> list[ScenarioRow]:
    if not path.exists():
        raise FileNotFoundError(f"Input summary not found: {path}")

    with path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        rows = list(reader)

    if not rows:
        raise ValueError(f"No rows found in {path}")

    missing = [column for column in REQUIRED_COLUMNS if column not in rows[0]]
    if missing:
        raise ValueError(
            f"Missing required columns in {path}: " + ", ".join(missing)
        )

    result: list[ScenarioRow] = []

    for row in rows:
        result.append(
            ScenarioRow(
                scenario=scenario_name,
                strategy=row["strategy"].strip(),
                run_count=int(float(row["run_count"])),
                corrected_mean=float(row["corrected_mean"]),
                corrected_stddev=float(row["corrected_stddev"]),
                uncorrectable_detections_mean=float(row["uncorrectable_detections_mean"]),
                uncorrectable_detections_stddev=float(row["uncorrectable_detections_stddev"]),
                unique_uncorrectable_words_mean=float(row["unique_uncorrectable_words_mean"]),
                unique_uncorrectable_words_stddev=float(row["unique_uncorrectable_words_stddev"]),
                busy_percent_mean=float(row["busy_percent_mean"]),
                busy_percent_stddev=float(row["busy_percent_stddev"]),
                interval_switches_mean=float(row["interval_switches_mean"]),
                interval_switches_stddev=float(row["interval_switches_stddev"]),
            )
        )

    return sort_rows(result)


def sort_rows(rows: list[ScenarioRow]) -> list[ScenarioRow]:
    order = {name: index for index, name in enumerate(STRATEGY_ORDER)}

    return sorted(
        rows,
        key=lambda row: order.get(row.strategy, len(order)),
    )


def write_csv(rows: list[ScenarioRow], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "scenario",
        "strategy",
        "run_count",
        "corrected_mean",
        "corrected_stddev",
        "uncorrectable_detections_mean",
        "uncorrectable_detections_stddev",
        "unique_uncorrectable_words_mean",
        "unique_uncorrectable_words_stddev",
        "busy_percent_mean",
        "busy_percent_stddev",
        "interval_switches_mean",
        "interval_switches_stddev",
    ]

    with output_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()

        for row in rows:
            writer.writerow(
                {
                    "scenario": row.scenario,
                    "strategy": row.strategy,
                    "run_count": row.run_count,
                    "corrected_mean": f"{row.corrected_mean:.6f}",
                    "corrected_stddev": f"{row.corrected_stddev:.6f}",
                    "uncorrectable_detections_mean": f"{row.uncorrectable_detections_mean:.6f}",
                    "uncorrectable_detections_stddev": f"{row.uncorrectable_detections_stddev:.6f}",
                    "unique_uncorrectable_words_mean": f"{row.unique_uncorrectable_words_mean:.6f}",
                    "unique_uncorrectable_words_stddev": f"{row.unique_uncorrectable_words_stddev:.6f}",
                    "busy_percent_mean": f"{row.busy_percent_mean:.6f}",
                    "busy_percent_stddev": f"{row.busy_percent_stddev:.6f}",
                    "interval_switches_mean": f"{row.interval_switches_mean:.6f}",
                    "interval_switches_stddev": f"{row.interval_switches_stddev:.6f}",
                }
            )


def scenario_map(rows: list[ScenarioRow]) -> dict[str, dict[str, ScenarioRow]]:
    result: dict[str, dict[str, ScenarioRow]] = {}

    for row in rows:
        result.setdefault(row.scenario, {})[row.strategy] = row

    return result


def percent_change(value: float, reference: float) -> float:
    if math.isclose(reference, 0.0, abs_tol=1e-12):
        return 0.0

    return 100.0 * (value - reference) / reference


def format_delta(value: float) -> str:
    return f"{value:+.3f}"


def write_markdown(
    rows: list[ScenarioRow],
    output_path: Path,
    no_clusters_input: Path,
    with_clusters_input: Path,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    by_scenario = scenario_map(rows)

    lines: list[str] = []

    lines.append("# Сравнение серийных сценариев")
    lines.append("")
    lines.append("Источник данных:")
    lines.append("")
    lines.append(f"- Без мгновенных кластеров: `{no_clusters_input}`")
    lines.append(f"- С мгновенными кластерами: `{with_clusters_input}`")
    lines.append("")

    lines.append("## Итоговая таблица")
    lines.append("")
    lines.append(
        "| Сценарий | Стратегия | Прогонов | "
        "Исправлено, среднее ± σ | "
        "Уникальные неустранимые слова, среднее ± σ | "
        "Обнаружения неустранимых, среднее ± σ | "
        "Занятость памяти, среднее ± σ, % | "
        "Переключения интервала, среднее ± σ |"
    )
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|")

    for row in rows:
        lines.append(
            f"| `{row.scenario}` "
            f"| `{row.strategy}` "
            f"| {row.run_count} "
            f"| {row.corrected_mean:.3f} ± {row.corrected_stddev:.3f} "
            f"| {row.unique_uncorrectable_words_mean:.3f} ± {row.unique_uncorrectable_words_stddev:.3f} "
            f"| {row.uncorrectable_detections_mean:.3f} ± {row.uncorrectable_detections_stddev:.3f} "
            f"| {row.busy_percent_mean:.3f} ± {row.busy_percent_stddev:.3f} "
            f"| {row.interval_switches_mean:.3f} ± {row.interval_switches_stddev:.3f} |"
        )

    lines.append("")

    lines.append("## Изменение относительно постоянного интервала внутри каждого сценария")
    lines.append("")
    lines.append(
        "| Сценарий | Стратегия | Δ исправленных | "
        "Δ уникальных неустранимых слов | Δ занятости памяти |"
    )
    lines.append("|---|---|---:|---:|---:|")

    for scenario_name, strategies in by_scenario.items():
        if "fixed" not in strategies:
            continue

        fixed = strategies["fixed"]

        for strategy in STRATEGY_ORDER:
            if strategy == "fixed" or strategy not in strategies:
                continue

            row = strategies[strategy]

            corrected_delta = row.corrected_mean - fixed.corrected_mean
            unique_delta = (
                row.unique_uncorrectable_words_mean
                - fixed.unique_uncorrectable_words_mean
            )
            busy_delta = row.busy_percent_mean - fixed.busy_percent_mean
            busy_relative = percent_change(row.busy_percent_mean, fixed.busy_percent_mean)

            lines.append(
                f"| `{scenario_name}` "
                f"| `{strategy}` "
                f"| {format_delta(corrected_delta)} "
                f"| {format_delta(unique_delta)} "
                f"| {format_delta(busy_delta)} п.п. ({busy_relative:+.2f} %) |"
            )

    lines.append("")

    lines.append("## Ключевой численный вывод")
    lines.append("")

    for scenario_name in ["no_clusters", "with_clusters"]:
        if scenario_name not in by_scenario:
            continue

        strategies = by_scenario[scenario_name]

        if "fixed" not in strategies:
            continue

        fixed = strategies["fixed"]

        lines.append(f"### Сценарий `{scenario_name}`")
        lines.append("")

        adaptive_strategies = [
            strategy for strategy in ["table", "threshold"]
            if strategy in strategies
        ]

        for strategy in adaptive_strategies:
            row = strategies[strategy]

            corrected_delta = row.corrected_mean - fixed.corrected_mean
            unique_delta = (
                row.unique_uncorrectable_words_mean
                - fixed.unique_uncorrectable_words_mean
            )
            busy_delta = row.busy_percent_mean - fixed.busy_percent_mean
            busy_relative = percent_change(row.busy_percent_mean, fixed.busy_percent_mean)

            lines.append(
                f"- `{strategy}`: занятость памяти изменилась "
                f"с {fixed.busy_percent_mean:.3f} % до {row.busy_percent_mean:.3f} % "
                f"({busy_delta:+.3f} п.п., {busy_relative:+.2f} % относительно `fixed`); "
                f"среднее число уникальных неустранимых слов изменилось "
                f"с {fixed.unique_uncorrectable_words_mean:.3f} "
                f"до {row.unique_uncorrectable_words_mean:.3f} "
                f"({unique_delta:+.3f}); "
                f"среднее число исправленных ошибок изменилось "
                f"с {fixed.corrected_mean:.3f} "
                f"до {row.corrected_mean:.3f} "
                f"({corrected_delta:+.3f})."
            )

        if adaptive_strategies:
            all_busy_lower = all(
                strategies[strategy].busy_percent_mean < fixed.busy_percent_mean
                for strategy in adaptive_strategies
            )

            max_abs_unique_delta = max(
                abs(
                    strategies[strategy].unique_uncorrectable_words_mean
                    - fixed.unique_uncorrectable_words_mean
                )
                for strategy in adaptive_strategies
            )

            if all_busy_lower and max_abs_unique_delta <= 1.0:
                lines.append("")
                lines.append(
                    "Итог: адаптивные стратегии в данном сценарии обеспечивают "
                    "сопоставимое среднее число уникальных неустранимых слов "
                    "при меньшей средней занятости интерфейса памяти."
                )

        lines.append("")

    if "no_clusters" in by_scenario and "with_clusters" in by_scenario:
        lines.append("## Вклад мгновенных кластеров")
        lines.append("")
        lines.append(
            "| Стратегия | Δ исправленных при добавлении кластеров | "
            "Δ уникальных неустранимых слов | Δ обнаружений неустранимых | "
            "Δ занятости памяти |"
        )
        lines.append("|---|---:|---:|---:|---:|")

        no_clusters = by_scenario["no_clusters"]
        with_clusters = by_scenario["with_clusters"]

        for strategy in STRATEGY_ORDER:
            if strategy not in no_clusters or strategy not in with_clusters:
                continue

            base = no_clusters[strategy]
            clustered = with_clusters[strategy]

            corrected_delta = clustered.corrected_mean - base.corrected_mean
            unique_delta = (
                clustered.unique_uncorrectable_words_mean
                - base.unique_uncorrectable_words_mean
            )
            detections_delta = (
                clustered.uncorrectable_detections_mean
                - base.uncorrectable_detections_mean
            )
            busy_delta = clustered.busy_percent_mean - base.busy_percent_mean

            lines.append(
                f"| `{strategy}` "
                f"| {format_delta(corrected_delta)} "
                f"| {format_delta(unique_delta)} "
                f"| {format_delta(detections_delta)} "
                f"| {format_delta(busy_delta)} п.п. |"
            )

        lines.append("")

    lines.append("## Интерпретация")
    lines.append("")
    lines.append(
        "Сценарий `no_clusters` изолирует эффект адаптивного скраббинга "
        "при одиночных ошибках и накопительных парах. В этом сценарии "
        "разница между стратегиями отражает способность контроллера "
        "уменьшать вероятность накопления второй ошибки в том же слове."
    )
    lines.append("")
    lines.append(
        "Сценарий `with_clusters` дополнительно включает мгновенные "
        "двухбитовые кластерные события. Такие события возникают за один "
        "модельный такт и для SECDED являются обнаруживаемыми, но "
        "неисправимыми. Поэтому они формируют дополнительный вклад в "
        "число неустранимых состояний, который не может быть полностью "
        "устранён уменьшением интервала скраббинга."
    )
    lines.append("")
    lines.append(
        "Для текста статьи эти два сценария следует интерпретировать отдельно: "
        "`no_clusters` — как оценку выигрыша адаптивной стратегии скраббинга, "
        "`with_clusters` — как оценку поведения той же архитектуры при "
        "наличии кластерной компоненты потока ошибок."
    )

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare no-cluster and cluster strategy series summaries."
    )

    parser.add_argument(
        "--no-clusters-input",
        type=Path,
        default=Path("results/tables/strategy_series_summary_no_clusters.csv"),
        help="Input summary CSV for the no-cluster scenario.",
    )

    parser.add_argument(
        "--with-clusters-input",
        type=Path,
        default=Path("results/tables/strategy_series_summary_with_clusters.csv"),
        help="Input summary CSV for the cluster scenario.",
    )

    parser.add_argument(
        "--csv-output",
        type=Path,
        default=Path("results/tables/strategy_scenario_comparison.csv"),
        help="Output combined CSV.",
    )

    parser.add_argument(
        "--md-output",
        type=Path,
        default=Path("results/tables/strategy_scenario_comparison.md"),
        help="Output combined Markdown report.",
    )

    args = parser.parse_args()

    rows: list[ScenarioRow] = []
    rows.extend(read_summary(args.no_clusters_input, "no_clusters"))
    rows.extend(read_summary(args.with_clusters_input, "with_clusters"))

    write_csv(rows, args.csv_output)
    write_markdown(
        rows=rows,
        output_path=args.md_output,
        no_clusters_input=args.no_clusters_input,
        with_clusters_input=args.with_clusters_input,
    )

    print(f"Scenario comparison rows: {len(rows)}")
    print(f"CSV comparison: {args.csv_output}")
    print(f"Markdown comparison: {args.md_output}")


if __name__ == "__main__":
    main()
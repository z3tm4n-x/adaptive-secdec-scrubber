#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
from pathlib import Path


def read_practical(path: Path, mapping_name: str) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(path)

    rows: list[dict[str, str]] = []

    with path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
            item = {"mapping": mapping_name}
            item.update(row)
            rows.append(item)

    return rows


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "mapping",
        "adaptive_strategy",
        "matching_metric",
        "matched_fixed_interval",
        "adaptive_scrub_cycles",
        "adaptive_busy_percent",
        "adaptive_unique_uncorrectable",
        "adaptive_uncorrectable_detections",
        "matched_fixed_scrub_cycles",
        "matched_fixed_busy_percent",
        "matched_fixed_unique_uncorrectable",
        "matched_fixed_uncorrectable_detections",
        "eta_practical_scrub_cycles",
        "eta_practical_busy_percent",
        "metric_difference",
        "eta_theory_1_plus_cv2",
    ]

    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()

        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def write_md(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []

    lines.append("# Чувствительность η к нормировке RTL-интервалов")
    lines.append("")
    lines.append("## Назначение")
    lines.append("")
    lines.append(
        "Сравниваются три отображения расчётных интервалов risk-policy "
        "в model-cycle intervals RTL-стенда: slow, base и fast. "
        "Цель — проверить, является ли неоднозначная practical η следствием "
        "конкретно выбранной нормировки."
    )
    lines.append("")
    lines.append("## Сводка practical η")
    lines.append("")
    lines.append(
        "| mapping | strategy | matching metric | matched fixed | "
        "η scrub | η busy | adaptive busy, % | adaptive unique | adaptive detections |"
    )
    lines.append("|---|---|---|---:|---:|---:|---:|---:|---:|")

    for row in rows:
        lines.append(
            f"| `{row.get('mapping', '')}` "
            f"| `{row.get('adaptive_strategy', '')}` "
            f"| `{row.get('matching_metric', '')}` "
            f"| {row.get('matched_fixed_interval', '')} "
            f"| {float(row.get('eta_practical_scrub_cycles', '0')):.3f} "
            f"| {float(row.get('eta_practical_busy_percent', '0')):.3f} "
            f"| {float(row.get('adaptive_busy_percent', '0')):.3f} "
            f"| {float(row.get('adaptive_unique_uncorrectable', '0')):.3f} "
            f"| {float(row.get('adaptive_uncorrectable_detections', '0')):.3f} |"
        )

    lines.append("")
    lines.append("## Интерпретация")
    lines.append("")
    lines.append(
        "Если ranking стратегий и practical η сильно меняются между slow/base/fast, "
        "то итоговый эффект адаптации чувствителен к нормировке model-cycle intervals. "
        "Если вывод устойчив, выбранная нормировка не является основной причиной "
        "слабой или неоднозначной η."
    )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare eta practical summaries for interval mapping sensitivity."
    )

    parser.add_argument(
        "--base-dir",
        type=Path,
        default=Path("results/paper/eta_sensitivity"),
    )

    parser.add_argument(
        "--mappings",
        default="slow,base,fast",
    )

    parser.add_argument(
        "--csv-output",
        type=Path,
        default=Path("results/paper/eta_sensitivity/eta_sensitivity_summary.csv"),
    )

    parser.add_argument(
        "--md-output",
        type=Path,
        default=Path("results/paper/eta_sensitivity/eta_sensitivity_summary.md"),
    )

    args = parser.parse_args()

    rows: list[dict[str, str]] = []

    for mapping_name in [part.strip() for part in args.mappings.split(",") if part.strip()]:
        practical_path = (
            args.base_dir
            / mapping_name
            / "tables"
            / "eta_practical_summary.csv"
        )

        rows.extend(read_practical(practical_path, mapping_name))

    write_csv(args.csv_output, rows)
    write_md(args.md_output, rows)

    print(f"Sensitivity CSV: {args.csv_output}")
    print(f"Sensitivity MD: {args.md_output}")


if __name__ == "__main__":
    main()
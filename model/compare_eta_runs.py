#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
from pathlib import Path


def parse_named_run(text: str) -> tuple[str, Path]:
    if "=" not in text:
        raise ValueError(f"Run must have NAME=PATH format: {text}")

    name, path = text.split("=", 1)

    name = name.strip()
    path = path.strip()

    if not name:
        raise ValueError(f"Empty run name in: {text}")

    if not path:
        raise ValueError(f"Empty run path in: {text}")

    return name, Path(path)


def read_practical(run_name: str, run_dir: Path) -> list[dict[str, str]]:
    path = run_dir / "tables" / "eta_practical_summary.csv"

    if not path.exists():
        raise FileNotFoundError(path)

    rows: list[dict[str, str]] = []

    with path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
            item = {"run": run_name}
            item.update(row)
            rows.append(item)

    return rows


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "run",
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


def write_markdown(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []

    lines.append("# Сравнение η для direct и achievable RTL mapping")
    lines.append("")
    lines.append("## Назначение")
    lines.append("")
    lines.append(
        "Сравниваются две семантически разные RTL-постановки: direct mapping "
        "использует исходное отображение уровней risk-policy в короткие интервалы, "
        "а achievable mapping ограничивает интервалы архитектурно достижимой "
        "областью последовательного скраббера."
    )
    lines.append("")
    lines.append("## Сводка practical η")
    lines.append("")
    lines.append(
        "| run | strategy | matching metric | matched fixed | "
        "η scrub | η busy | adaptive busy, % | adaptive unique | adaptive detections |"
    )
    lines.append("|---|---|---|---:|---:|---:|---:|---:|---:|")

    for row in rows:
        lines.append(
            f"| `{row.get('run', '')}` "
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
        "Если achievable mapping даёт более устойчивую practical η, это означает, "
        "что прежняя direct-постановка была ограничена насыщением скраббера: "
        "часть целевых интервалов была меньше длительности полного прохода памяти."
    )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare practical eta summaries for multiple ETA runs."
    )

    parser.add_argument(
        "--run",
        action="append",
        required=True,
        help="Named run in NAME=PATH format.",
    )

    parser.add_argument(
        "--csv-output",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--md-output",
        type=Path,
        required=True,
    )

    args = parser.parse_args()

    rows: list[dict[str, str]] = []

    for run_text in args.run:
        name, path = parse_named_run(run_text)
        rows.extend(read_practical(name, path))

    write_csv(args.csv_output, rows)
    write_markdown(args.md_output, rows)

    print(f"Comparison CSV: {args.csv_output}")
    print(f"Comparison MD: {args.md_output}")


if __name__ == "__main__":
    main()
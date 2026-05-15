#!/usr/bin/env python3

import argparse
import csv
from pathlib import Path


def parse_run_arg(text):
    if "=" not in text:
        raise ValueError("Run must be LABEL=PATH")
    label, path = text.split("=", 1)
    return label.strip(), Path(path.strip())


def read_rows(path):
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def find_metric(rows, scenario, comparison, metric):
    for row in rows:
        if (
            row["scenario"] == scenario
            and row["comparison"] == comparison
            and row["metric"] == metric
        ):
            return row
    raise KeyError((scenario, comparison, metric))


def ci_text(row):
    return f"{float(row['delta_mean']):+.3f} [{float(row['ci95_low']):+.3f}; {float(row['ci95_high']):+.3f}]"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--run", action="append", required=True)
    p.add_argument("--csv-output", required=True)
    p.add_argument("--md-output", required=True)
    args = p.parse_args()

    scenarios = ["no_clusters", "with_clusters"]
    comparisons = ["table-fixed", "threshold-fixed"]

    all_out = []

    for raw in args.run:
        label, path = parse_run_arg(raw)
        rows = read_rows(path)

        for scenario in scenarios:
            for comparison in comparisons:
                unique = find_metric(rows, scenario, comparison, "unique_uncorrectable_words")
                busy = find_metric(rows, scenario, comparison, "busy_percent")
                detections = find_metric(rows, scenario, comparison, "uncorrectable_detections")
                scrub = find_metric(rows, scenario, comparison, "scrub_cycles")

                strategy = comparison.replace("-fixed", "")

                all_out.append({
                    "variant": label,
                    "scenario": scenario,
                    "strategy": strategy,
                    "fixed_unique": float(unique["fixed_mean"]),
                    "adaptive_unique": float(unique["adaptive_mean"]),
                    "delta_unique": float(unique["delta_mean"]),
                    "unique_ci_low": float(unique["ci95_low"]),
                    "unique_ci_high": float(unique["ci95_high"]),
                    "fixed_busy": float(busy["fixed_mean"]),
                    "adaptive_busy": float(busy["adaptive_mean"]),
                    "delta_busy": float(busy["delta_mean"]),
                    "busy_ci_low": float(busy["ci95_low"]),
                    "busy_ci_high": float(busy["ci95_high"]),
                    "busy_reduction_percent": -float(busy["relative_percent"]),
                    "delta_detections": float(detections["delta_mean"]),
                    "detections_ci_low": float(detections["ci95_low"]),
                    "detections_ci_high": float(detections["ci95_high"]),
                    "delta_scrub_cycles": float(scrub["delta_mean"]),
                    "scrub_reduction_percent": -float(scrub["relative_percent"]),
                })

    csv_path = Path(args.csv_output)
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = list(all_out[0].keys())
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(all_out)

    md = []
    md.append("# Итоговая сводка RTL-проверки стратегий\n")
    md.append("## Назначение\n")
    md.append(
        "Таблица сопоставляет три варианта входной оценки частоты одиночных сбоев: "
        "синхронную, задержанную на один отсчёт и модифицированную задержанную. "
        "Сравнение выполняется с постоянным режимом fixed=80 в одной и той же "
        "нормированной проверочной модели.\n"
    )

    md.append("## Сводка\n")
    md.append(
        "| Вариант оценки | Сценарий | Стратегия | Unique fixed | Unique adaptive | "
        "Δ unique, 95 % ДИ | Busy fixed, % | Busy adaptive, % | Δ busy, п.п., 95 % ДИ | "
        "Снижение busy, % | Δ обнаружений, 95 % ДИ | Снижение проходов, % |"
    )
    md.append("|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")

    for row in all_out:
        md.append(
            f"| {row['variant']} | {row['scenario']} | `{row['strategy']}` | "
            f"{row['fixed_unique']:.3f} | {row['adaptive_unique']:.3f} | "
            f"{row['delta_unique']:+.3f} [{row['unique_ci_low']:+.3f}; {row['unique_ci_high']:+.3f}] | "
            f"{row['fixed_busy']:.3f} | {row['adaptive_busy']:.3f} | "
            f"{row['delta_busy']:+.3f} [{row['busy_ci_low']:+.3f}; {row['busy_ci_high']:+.3f}] | "
            f"{row['busy_reduction_percent']:.2f} | "
            f"{row['delta_detections']:+.3f} [{row['detections_ci_low']:+.3f}; {row['detections_ci_high']:+.3f}] | "
            f"{row['scrub_reduction_percent']:.2f} |"
        )

    md.append("\n## Интерпретация\n")
    md.append(
        "Основная риск-метрика — число различных кодовых слов с неустранимой ошибкой. "
        "Если доверительный интервал для Δ unique включает ноль, результат следует "
        "формулировать как сопоставимый с fixed. Занятость интерфейса во всех "
        "адаптивных вариантах уменьшается, если доверительный интервал для Δ busy "
        "полностью отрицателен."
    )
    md.append(
        "\nДля окончательной версии статьи основной практический акцент следует делать "
        "на модифицированной задержанной оценке, поскольку она прямо продолжает расчётную "
        "логику статьи 3 и сохраняет сопоставимость основной риск-метрики в RTL-проверке."
    )

    md_path = Path(args.md_output)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text("\n".join(md) + "\n", encoding="utf-8")

    print(f"CSV: {csv_path}")
    print(f"MD:  {md_path}")
    print(md_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
import argparse
import csv
import math
from collections import defaultdict
from pathlib import Path


METRICS = [
    "scrub_cycles",
    "reads",
    "writes",
    "corrected",
    "uncorrectable_detections",
    "unique_uncorrectable_words",
    "memory_busy_cycles",
    "busy_percent",
]


def mean(values):
    values = list(values)
    return sum(values) / len(values) if values else float("nan")


def sample_std(values):
    values = list(values)
    if len(values) < 2:
        return 0.0
    m = mean(values)
    return math.sqrt(sum((x - m) ** 2 for x in values) / (len(values) - 1))


def t_critical_95(n):
    # Достаточно для наших серий. Для n=30 t0.975,29 ≈ 2.045.
    table = {
        2: 12.706,
        3: 4.303,
        4: 3.182,
        5: 2.776,
        6: 2.571,
        7: 2.447,
        8: 2.365,
        9: 2.306,
        10: 2.262,
        15: 2.145,
        20: 2.093,
        25: 2.064,
        30: 2.045,
        40: 2.023,
        60: 2.000,
        120: 1.980,
    }
    if n <= 1:
        return 0.0
    keys = sorted(table)
    for k in keys:
        if n <= k:
            return table[k]
    return 1.96


def ci95_for_paired_delta(deltas):
    deltas = list(deltas)
    n = len(deltas)
    m = mean(deltas)
    if n < 2:
        return m, m, m
    se = sample_std(deltas) / math.sqrt(n)
    half = t_critical_95(n) * se
    return m, m - half, m + half


def parse_run_spec(spec):
    if "=" not in spec:
        raise SystemExit(f"--run must be label=path, got: {spec}")
    label, path = spec.split("=", 1)
    return label.strip(), Path(path.strip())


def read_rows(path):
    rows = []
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # busy_percent может отсутствовать в raw CSV; тогда считаем из busy_per_mille
            # или из memory_busy_cycles / total_cycles.
            if "busy_percent" not in row or row.get("busy_percent", "") == "":
                if "busy_per_mille" in row and row["busy_per_mille"] != "":
                    row["busy_percent"] = float(row["busy_per_mille"]) / 10.0
                else:
                    row["busy_percent"] = (
                        float(row["memory_busy_cycles"]) / float(row["total_cycles"]) * 100.0
                    )
            else:
                row["busy_percent"] = float(row["busy_percent"])

            for key in [
                "seed",
                "total_cycles",
                "scrub_cycles",
                "reads",
                "writes",
                "corrected",
                "uncorrectable_detections",
                "unique_uncorrectable_words",
                "memory_busy_cycles",
            ]:
                if key in row and row[key] != "":
                    row[key] = float(row[key])
            rows.append(row)
    return rows


def summarize_run(label, path):
    rows = read_rows(path)

    by_strategy = defaultdict(list)
    for row in rows:
        by_strategy[row["strategy"]].append(row)

    if "fixed" not in by_strategy:
        raise SystemExit(f"{path}: no fixed strategy rows")

    fixed_by_seed = {int(r["seed"]): r for r in by_strategy["fixed"]}

    result_rows = []

    for strategy in ["table", "threshold"]:
        if strategy not in by_strategy:
            continue

        adaptive_rows = by_strategy[strategy]
        adaptive_by_seed = {int(r["seed"]): r for r in adaptive_rows}
        common_seeds = sorted(set(fixed_by_seed) & set(adaptive_by_seed))

        fixed_unique = mean(fixed_by_seed[s]["unique_uncorrectable_words"] for s in common_seeds)
        adaptive_unique = mean(adaptive_by_seed[s]["unique_uncorrectable_words"] for s in common_seeds)

        fixed_busy = mean(fixed_by_seed[s]["busy_percent"] for s in common_seeds)
        adaptive_busy = mean(adaptive_by_seed[s]["busy_percent"] for s in common_seeds)

        fixed_scrubs = mean(fixed_by_seed[s]["scrub_cycles"] for s in common_seeds)
        adaptive_scrubs = mean(adaptive_by_seed[s]["scrub_cycles"] for s in common_seeds)

        unique_deltas = [
            adaptive_by_seed[s]["unique_uncorrectable_words"]
            - fixed_by_seed[s]["unique_uncorrectable_words"]
            for s in common_seeds
        ]
        busy_deltas = [
            adaptive_by_seed[s]["busy_percent"] - fixed_by_seed[s]["busy_percent"]
            for s in common_seeds
        ]

        unique_m, unique_lo, unique_hi = ci95_for_paired_delta(unique_deltas)
        busy_m, busy_lo, busy_hi = ci95_for_paired_delta(busy_deltas)

        busy_reduction_pct = -busy_m / fixed_busy * 100.0 if fixed_busy else float("nan")
        scrub_reduction_pct = (fixed_scrubs - adaptive_scrubs) / fixed_scrubs * 100.0 if fixed_scrubs else float("nan")

        result_rows.append({
            "run": label,
            "strategy": strategy,
            "n": len(common_seeds),
            "fixed_unique_mean": fixed_unique,
            "adaptive_unique_mean": adaptive_unique,
            "unique_delta_mean": unique_m,
            "unique_delta_ci_low": unique_lo,
            "unique_delta_ci_high": unique_hi,
            "fixed_busy_percent": fixed_busy,
            "adaptive_busy_percent": adaptive_busy,
            "busy_delta_pp": busy_m,
            "busy_delta_ci_low": busy_lo,
            "busy_delta_ci_high": busy_hi,
            "busy_reduction_percent": busy_reduction_pct,
            "fixed_scrub_cycles": fixed_scrubs,
            "adaptive_scrub_cycles": adaptive_scrubs,
            "scrub_reduction_percent": scrub_reduction_pct,
            "mean_unique_no_worse": adaptive_unique <= fixed_unique,
            "unique_statistically_compatible": unique_lo <= 0.0,
            "busy_lower": busy_hi < 0.0,
        })

    return result_rows


def fmt(x, digits=3):
    if isinstance(x, bool):
        return "1" if x else "0"
    if isinstance(x, float):
        return f"{x:.{digits}f}"
    return str(x)


def write_csv(rows, path):
    if not rows:
        raise SystemExit("No rows to write")
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_md(rows, path):
    rows_sorted = sorted(
        rows,
        key=lambda r: (
            r["strategy"],
            not (r["unique_statistically_compatible"] and r["busy_lower"]),
            -r["busy_reduction_percent"],
        ),
    )

    lines = []
    lines.append("# Sweep риск-ограниченных RTL-отображений\n")
    lines.append("## Назначение\n")
    lines.append(
        "Проверяется, можно ли подобрать дискретную шкалу периодов полного прохода, "
        "которая снижает занятость интерфейса ЗУ относительно fixed=80 и при этом "
        "сохраняет число различных кодовых слов с неустранимой ошибкой на сопоставимом уровне.\n"
    )
    lines.append("Критерии чтения таблицы:\n")
    lines.append("- `unique statistically compatible = 1`: 95 % доверительный интервал для paired-дельты unique включает ноль или значения лучше fixed.")
    lines.append("- `busy lower = 1`: 95 % доверительный интервал для paired-дельты занятости полностью ниже нуля.")
    lines.append("- Сильная кандидатная шкала должна иметь оба признака равными 1.\n")

    lines.append("## Сводка\n")
    lines.append(
        "| run | strategy | n | fixed unique | adaptive unique | Δ unique, 95% CI | "
        "fixed busy, % | adaptive busy, % | Δ busy, п.п., 95% CI | busy reduction, % | "
        "scrub reduction, % | unique statistically compatible | busy lower |"
    )
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")

    for r in rows_sorted:
        unique_ci = f"{fmt(r['unique_delta_mean'])} [{fmt(r['unique_delta_ci_low'])}; {fmt(r['unique_delta_ci_high'])}]"
        busy_ci = f"{fmt(r['busy_delta_pp'])} [{fmt(r['busy_delta_ci_low'])}; {fmt(r['busy_delta_ci_high'])}]"
        lines.append(
            f"| `{r['run']}` | `{r['strategy']}` | {int(r['n'])} | "
            f"{fmt(r['fixed_unique_mean'])} | {fmt(r['adaptive_unique_mean'])} | {unique_ci} | "
            f"{fmt(r['fixed_busy_percent'])} | {fmt(r['adaptive_busy_percent'])} | {busy_ci} | "
            f"{fmt(r['busy_reduction_percent'], 2)} | {fmt(r['scrub_reduction_percent'], 2)} | "
            f"{fmt(r['unique_statistically_compatible'])} | {fmt(r['busy_lower'])} |"
        )

    good = [
        r for r in rows
        if r["unique_statistically_compatible"] and r["busy_lower"]
    ]

    lines.append("\n## Интерпретация\n")
    if good:
        lines.append(
            "Найдены отображения, у которых занятость интерфейса ЗУ статистически ниже fixed=80, "
            "а увеличение числа различных кодовых слов с неустранимой ошибкой статистически не отделено от нуля. "
            "Такие отображения можно рассматривать как кандидаты на риск-ограниченную RTL-реализацию."
        )
    else:
        lines.append(
            "В заданном наборе отображений не найдено шкалы, которая одновременно статистически снижает занятость "
            "и сохраняет число различных кодовых слов с неустранимой ошибкой на уровне fixed=80. "
            "Нужно либо расширить набор шкал в сторону более частого восстановления, либо трактовать результат как Парето-компромисс."
        )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="append", required=True, help="label=csv_path")
    parser.add_argument("--csv-output", required=True)
    parser.add_argument("--md-output", required=True)
    args = parser.parse_args()

    all_rows = []
    for spec in args.run:
        label, path = parse_run_spec(spec)
        all_rows.extend(summarize_run(label, path))

    csv_path = Path(args.csv_output)
    md_path = Path(args.md_output)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)

    write_csv(all_rows, csv_path)
    write_md(all_rows, md_path)

    print(f"CSV: {csv_path}")
    print(f"MD:  {md_path}")


if __name__ == "__main__":
    main()

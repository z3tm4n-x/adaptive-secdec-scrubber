#!/usr/bin/env python3

import argparse
import csv
import math
from pathlib import Path


COSRAD_ROWS = [
    {
        "strategy": "cosrad_peak_fixed_3.3s",
        "role": "Постоянный интервал по пиковому потоку COSRAD; безопасный, но консервативный режим из статьи 3",
        "interval_seconds": 3.3,
        "p_mission": 0.0037,
    },
    {
        "strategy": "cosrad_average_fixed_7050s",
        "role": "Постоянный интервал по усреднённому потоку COSRAD; экономный, но не обеспечивающий требуемый риск режим из статьи 3",
        "interval_seconds": 7050.0,
        "p_mission": 0.9985,
    },
]


MAIN_STRATEGIES = [
    "adaptive_current_discrete",
    "adaptive_delayed_1h_discrete",
    "adaptive_modified_delayed_1h_discrete",
]


CONTROL_STRATEGIES = [
    "fixed_continuous_at_target",
]


def read_projection(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def fnum(value, digits=6):
    if value is None or value == "":
        return ""
    return f"{float(value):.{digits}f}"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--projection", required=True)
    p.add_argument("--window-hours", type=float, default=43824)
    p.add_argument("--csv-output", required=True)
    p.add_argument("--md-output", required=True)
    args = p.parse_args()

    projection = read_projection(Path(args.projection))
    by_name = {row["strategy"]: row for row in projection}

    if "adaptive_modified_delayed_1h_discrete" not in by_name:
        raise SystemExit("adaptive_modified_delayed_1h_discrete not found in projection")

    total_seconds = args.window_hours * 3600.0
    pass_seconds = float(by_name["adaptive_modified_delayed_1h_discrete"]["pass_seconds"])

    out = []

    for row in COSRAD_ROWS:
        interval = row["interval_seconds"]
        cycles = total_seconds / interval
        busy = pass_seconds / interval * 100.0

        out.append({
            "strategy": row["strategy"],
            "role": row["role"],
            "interval_description": f"{interval:g} с",
            "cycles": cycles,
            "p_mission": row["p_mission"],
            "pmax_per_cycle": "",
            "mean_busy_percent": busy,
            "max_busy_percent": busy,
            "saturated": int(interval <= pass_seconds),
        })

    for name in MAIN_STRATEGIES:
        row = by_name[name]
        out.append({
            "strategy": name,
            "role": "Расчётная адаптивная стратегия статьи 3, переведённая в аппаратную оценку полного прохода",
            "interval_description": f"{float(row['tau_min_seconds']):.3f}–{float(row['tau_max_seconds']):.3f} с; средний {float(row['mean_tau_seconds']):.3f} с",
            "cycles": float(row["cycles"]),
            "p_mission": float(row["P_mission"]),
            "pmax_per_cycle": float(row["Pmax_per_cycle"]),
            "mean_busy_percent": float(row["mean_busy_percent"]),
            "max_busy_percent": float(row["max_busy_percent"]),
            "saturated": int(float(row["saturated"])),
        })

    for name in CONTROL_STRATEGIES:
        if name not in by_name:
            continue
        row = by_name[name]
        out.append({
            "strategy": name,
            "role": "Дополнительный равнорисковый постоянный ориентир, рассчитанный по тому же ряду; не является COSRAD-режимом статьи 3",
            "interval_description": f"{float(row['mean_tau_seconds']):.3f} с",
            "cycles": float(row["cycles"]),
            "p_mission": float(row["P_mission"]),
            "pmax_per_cycle": float(row["Pmax_per_cycle"]),
            "mean_busy_percent": float(row["mean_busy_percent"]),
            "max_busy_percent": float(row["max_busy_percent"]),
            "saturated": int(float(row["saturated"])),
        })

    csv_path = Path(args.csv_output)
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "strategy",
        "role",
        "interval_description",
        "cycles",
        "p_mission",
        "pmax_per_cycle",
        "mean_busy_percent",
        "max_busy_percent",
        "saturated",
    ]

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for row in out:
            w.writerow(row)

    md = []
    md.append("# Итоговая аппаратная сводка стратегий циклического восстановления\n")
    md.append("## Назначение\n")
    md.append(
        "Таблица сопоставляет постоянные проектные интервалы COSRAD из статьи 3 "
        "с расчётными адаптивными стратегиями, переведёнными в аппаратную оценку "
        "контроллера полного прохода.\n"
    )
    md.append("## Исходная аппаратная оценка\n")
    md.append(f"- Длительность расчётного периода, ч: {args.window_hours:.0f}")
    md.append(f"- Длительность одного полного прохода, с: {pass_seconds:.9f}\n")

    md.append("## Сводка\n")
    md.append(
        "| Стратегия | Роль | Интервал | Проходов за расчётный период | Pм | "
        "Pmax за цикл | Средняя занятость интерфейса, % | Максимальная локальная занятость, % | Насыщение |"
    )
    md.append("|---|---|---:|---:|---:|---:|---:|---:|---:|")

    for row in out:
        pmax = "" if row["pmax_per_cycle"] == "" else f"{float(row['pmax_per_cycle']):.6g}"
        md.append(
            f"| `{row['strategy']}` | {row['role']} | {row['interval_description']} | "
            f"{float(row['cycles']):.0f} | {float(row['p_mission']):.6g} | {pmax} | "
            f"{float(row['mean_busy_percent']):.6f} | {float(row['max_busy_percent']):.6f} | "
            f"{row['saturated']} |"
        )

    md.append("\n## Интерпретация\n")
    md.append(
        "Пиковый COSRAD-интервал является безопасным, но приводит к существенно большей "
        "занятости интерфейса ЗУ. Интервал, выбранный по среднему потоку COSRAD, почти "
        "не нагружает интерфейс, но не обеспечивает требуемый риск. "
        "Модифицированная задержанная адаптивная стратегия сохраняет расчётный риск "
        "порядка 1 %, не входит в насыщение и даёт малую среднюю занятость интерфейса."
    )
    md.append(
        "\nСтрока `fixed_continuous_at_target` приведена только как дополнительный "
        "равнорисковый ориентир, рассчитанный по тому же пятилетнему ряду. "
        "Её нельзя смешивать с COSRAD-интервалами статьи 3."
    )

    md_path = Path(args.md_output)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text("\n".join(md) + "\n", encoding="utf-8")

    print(f"CSV: {csv_path}")
    print(f"MD:  {md_path}")
    print(md_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()

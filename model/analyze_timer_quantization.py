#!/usr/bin/env python3
import argparse
import csv
import math
from pathlib import Path


def bits_needed(max_count):
    if max_count <= 1:
        return 1
    return math.ceil(math.log2(max_count + 1))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--max-interval-seconds", type=float, default=3600.0)
    p.add_argument("--min-interval-seconds", type=float, default=1.0)
    p.add_argument("--clock-hz", type=float, default=100e6)
    p.add_argument("--timer-ticks-seconds", default="1e-8,1e-6,1e-4,1e-3,1e-2,1e-1,1")
    p.add_argument("--csv-output", required=True)
    p.add_argument("--md-output", required=True)
    args = p.parse_args()

    ticks = [float(x.strip()) for x in args.timer_ticks_seconds.split(",") if x.strip()]

    rows = []
    for tick in ticks:
        max_count = math.ceil(args.max_interval_seconds / tick)
        min_count = math.ceil(args.min_interval_seconds / tick)
        rows.append({
            "timer_tick_seconds": tick,
            "timer_tick_label": f"{tick:g}",
            "min_interval_count": min_count,
            "max_interval_count": max_count,
            "counter_bits": bits_needed(max_count),
            "max_rounding_error_seconds": tick,
            "relative_error_at_1s_percent": tick / args.min_interval_seconds * 100.0,
            "relative_error_at_max_percent": tick / args.max_interval_seconds * 100.0,
        })

    csv_path = Path(args.csv_output)
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    md = []
    md.append("# Таймерное представление физических интервалов\n")
    md.append("## Назначение\n")
    md.append(
        "Физические интервалы циклического восстановления могут быть заданы не в тактах "
        "системной частоты, а в тиках медленного таймера. Это уменьшает разрядность "
        "счётчика периода без потери инженерного смысла интервала.\n"
    )
    md.append("## Исходные параметры\n")
    md.append(f"- Минимальный интервал, с: {args.min_interval_seconds:g}")
    md.append(f"- Максимальный интервал, с: {args.max_interval_seconds:g}")
    md.append(f"- Системная частота, Гц: {args.clock_hz:.0f}\n")

    md.append("## Сводка\n")
    md.append(
        "| Тик таймера, с | Счёт для 1 с | Счёт для максимального интервала | "
        "Разрядность счётчика | Ошибка округления, с | Ошибка на 1 с, % | Ошибка на max, % |"
    )
    md.append("|---:|---:|---:|---:|---:|---:|---:|")

    for r in rows:
        md.append(
            f"| {r['timer_tick_seconds']:.9g} | {r['min_interval_count']} | "
            f"{r['max_interval_count']} | {r['counter_bits']} | "
            f"{r['max_rounding_error_seconds']:.9g} | "
            f"{r['relative_error_at_1s_percent']:.6f} | "
            f"{r['relative_error_at_max_percent']:.9f} |"
        )

    md.append("\n## Интерпретация\n")
    md.append(
        "Использование медленного таймера позволяет задавать интервалы порядка секунд "
        "и часов без широкого счётчика тактов системной частоты. Например, тик 1 мс "
        "задаёт интервал 3600 с счётчиком на 3 600 000 состояний, то есть требует "
        "22 разряда, тогда как прямой счёт тактов 100 МГц потребовал бы около 39 разрядов."
    )

    md_path = Path(args.md_output)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text("\n".join(md) + "\n", encoding="utf-8")

    print(f"CSV: {csv_path}")
    print(f"MD:  {md_path}")
    print(md_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()

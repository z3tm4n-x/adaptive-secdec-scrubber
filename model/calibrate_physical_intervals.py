#!/usr/bin/env python3
import argparse
import csv
from pathlib import Path


def read_policy(path):
    rows = []
    with Path(path).open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def find_interval_field(rows):
    if not rows:
        raise SystemExit("empty policy CSV")

    candidates = [
        "selected_interval_seconds",
        "interval_seconds",
        "discrete_interval_seconds",
        "adaptive_current_discrete_interval",
        "interval",
    ]

    fields = rows[0].keys()
    for c in candidates:
        if c in fields:
            return c

    numeric_like = []
    for field in fields:
        name = field.lower()
        if "interval" in name or "tau" in name:
            numeric_like.append(field)

    if len(numeric_like) == 1:
        return numeric_like[0]

    raise SystemExit(
        "Cannot find interval field. Available columns: "
        + ", ".join(rows[0].keys())
    )


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--policy", required=True)
    p.add_argument("--codeword-count", type=int, default=1935832)
    p.add_argument("--clock-hz", type=float, default=100e6)
    p.add_argument("--cycles-per-word", type=float, default=4.0)
    p.add_argument("--pass-overhead-cycles", type=float, default=4.0)
    p.add_argument("--csv-output", required=True)
    p.add_argument("--md-output", required=True)
    args = p.parse_args()

    rows = read_policy(args.policy)
    interval_field = find_interval_field(rows)

    pass_cycles = args.codeword_count * args.cycles_per_word + args.pass_overhead_cycles
    pass_seconds = pass_cycles / args.clock_hz

    intervals = []
    for row in rows:
        try:
            tau = float(row[interval_field])
        except Exception:
            continue
        if tau > 0:
            intervals.append(tau)

    if not intervals:
        raise SystemExit(f"No positive intervals found in field {interval_field}")

    min_tau = min(intervals)
    max_tau = max(intervals)
    mean_tau = sum(intervals) / len(intervals)

    saturated = [tau for tau in intervals if tau <= pass_seconds]
    busy_values = [min(1.0, pass_seconds / tau) * 100.0 for tau in intervals]

    mean_busy = sum(busy_values) / len(busy_values)
    max_busy = max(busy_values)
    min_busy = min(busy_values)

    out_rows = []
    for tau, busy in zip(intervals, busy_values):
        out_rows.append({
            "interval_seconds": tau,
            "pass_seconds": pass_seconds,
            "pass_cycles": pass_cycles,
            "busy_percent": busy,
            "saturated": int(tau <= pass_seconds),
        })

    csv_path = Path(args.csv_output)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "interval_seconds",
                "pass_seconds",
                "pass_cycles",
                "busy_percent",
                "saturated",
            ],
        )
        writer.writeheader()
        writer.writerows(out_rows)

    md = []
    md.append("# Физическая калибровка интервалов циклического восстановления\n")
    md.append("## Назначение\n")
    md.append(
        "Проверяется, может ли контроллер полного прохода исполнить физические интервалы "
        "циклического восстановления, полученные в расчётной постановке.\n"
    )
    md.append("## Исходные параметры\n")
    md.append(f"- Число кодовых слов: {args.codeword_count}")
    md.append(f"- Тактовая частота контроллера, Гц: {args.clock_hz:.0f}")
    md.append(f"- Тактов на одно кодовое слово: {args.cycles_per_word:.3f}")
    md.append(f"- Служебные такты полного прохода: {args.pass_overhead_cycles:.3f}")
    md.append(f"- Полный проход, тактов: {pass_cycles:.3f}")
    md.append(f"- Полный проход, секунд: {pass_seconds:.9f}\n")

    md.append("## Сводка\n")
    md.append(f"- Использованное поле интервала: `{interval_field}`")
    md.append(f"- Число интервалов в расписании: {len(intervals)}")
    md.append(f"- Минимальный интервал, с: {min_tau:.6f}")
    md.append(f"- Средний интервал, с: {mean_tau:.6f}")
    md.append(f"- Максимальный интервал, с: {max_tau:.6f}")
    md.append(f"- Минимальная оценка занятости, %: {min_busy:.6f}")
    md.append(f"- Средняя оценка занятости, %: {mean_busy:.6f}")
    md.append(f"- Максимальная оценка занятости, %: {max_busy:.6f}")
    md.append(f"- Интервалов в насыщении: {len(saturated)}\n")

    md.append("## Интерпретация\n")
    if saturated:
        md.append(
            "Для части расписания длительность полного прохода не меньше заданного физического "
            "интервала. В этих точках контроллер переходит в насыщение: следующий проход должен "
            "начинаться практически сразу после предыдущего."
        )
    else:
        md.append(
            "Минимальный физический интервал больше длительности полного прохода. "
            "Для заданных параметров контроллер может исполнить расчётные интервалы без насыщения."
        )

    md_path = Path(args.md_output)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text("\n".join(md) + "\n", encoding="utf-8")

    print(f"CSV: {csv_path}")
    print(f"MD:  {md_path}")
    print(md_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()

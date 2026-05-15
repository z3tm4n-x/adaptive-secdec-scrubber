#!/usr/bin/env python3
import argparse
import csv
import math
import re
from pathlib import Path


def parse_float(text):
    text = text.strip().replace(",", ".")
    if text == "" or text == " ":
        return None
    return float(text)


def parse_int(text):
    text = text.strip().replace(" ", "")
    if text == "":
        return None
    return int(float(text))


def parse_range_seconds(text):
    text = text.strip()
    if "–" in text:
        a, b = text.split("–", 1)
    elif "-" in text:
        a, b = text.split("-", 1)
    else:
        v = parse_float(text)
        return v, v
    return parse_float(a), parse_float(b)


def read_strategy_table(summary_path):
    lines = Path(summary_path).read_text(encoding="utf-8").splitlines()
    rows = []
    in_table = False

    for line in lines:
        if line.startswith("| Стратегия |"):
            in_table = True
            continue
        if not in_table:
            continue
        if line.startswith("|---"):
            continue
        if not line.startswith("|"):
            if rows:
                break
            continue

        parts = [p.strip() for p in line.strip().strip("|").split("|")]
        if len(parts) < 9:
            continue

        strategy = parts[0].strip("`")
        c_value = parse_float(parts[1]) if parts[1] else None
        e_value = parse_float(parts[2])
        p_mission = parse_float(parts[3])
        cycles = parse_int(parts[4])
        pmax = parse_float(parts[5])
        mean_tau = parse_float(parts[6])
        tau_min, tau_max = parse_range_seconds(parts[7])
        rel_to_practical = parts[8]

        rows.append({
            "strategy": strategy,
            "c": c_value,
            "E": e_value,
            "P_mission": p_mission,
            "cycles": cycles,
            "Pmax_per_cycle": pmax,
            "mean_tau_seconds": mean_tau,
            "tau_min_seconds": tau_min,
            "tau_max_seconds": tau_max,
            "relative_to_practical_lower_bound": rel_to_practical,
        })

    if not rows:
        raise SystemExit(f"Cannot parse strategy table from {summary_path}")

    return rows


def md_escape(text):
    return str(text).replace("|", "\\|")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--risk-summary", required=True)
    parser.add_argument("--window-hours", type=float, default=43824.0)
    parser.add_argument("--codeword-count", type=int, default=1935832)
    parser.add_argument("--clock-hz", type=float, default=100e6)
    parser.add_argument("--cycles-per-word", type=float, default=4.0)
    parser.add_argument("--pass-overhead-cycles", type=float, default=4.0)
    parser.add_argument("--csv-output", required=True)
    parser.add_argument("--md-output", required=True)
    args = parser.parse_args()

    rows = read_strategy_table(args.risk_summary)

    total_seconds = args.window_hours * 3600.0
    pass_cycles = args.codeword_count * args.cycles_per_word + args.pass_overhead_cycles
    pass_seconds = pass_cycles / args.clock_hz

    fixed = next((r for r in rows if r["strategy"] == "fixed_continuous_at_target"), None)
    fixed_busy = None

    out = []
    for r in rows:
        mean_busy = r["cycles"] * pass_seconds / total_seconds * 100.0
        max_busy = min(100.0, pass_seconds / r["tau_min_seconds"] * 100.0)
        min_busy = min(100.0, pass_seconds / r["tau_max_seconds"] * 100.0)
        saturated = int(r["tau_min_seconds"] <= pass_seconds)

        rr = dict(r)
        rr.update({
            "window_hours": args.window_hours,
            "pass_cycles": pass_cycles,
            "pass_seconds": pass_seconds,
            "mean_busy_percent": mean_busy,
            "min_busy_percent": min_busy,
            "max_busy_percent": max_busy,
            "saturated": saturated,
        })
        out.append(rr)

        if r["strategy"] == "fixed_continuous_at_target":
            fixed_busy = mean_busy

    if fixed_busy is not None:
        for r in out:
            r["busy_relative_to_fixed"] = r["mean_busy_percent"] / fixed_busy
            r["busy_reduction_vs_fixed_percent"] = (1.0 - r["mean_busy_percent"] / fixed_busy) * 100.0
    else:
        for r in out:
            r["busy_relative_to_fixed"] = float("nan")
            r["busy_reduction_vs_fixed_percent"] = float("nan")

    csv_path = Path(args.csv_output)
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "strategy",
        "cycles",
        "E",
        "P_mission",
        "Pmax_per_cycle",
        "mean_tau_seconds",
        "tau_min_seconds",
        "tau_max_seconds",
        "pass_seconds",
        "mean_busy_percent",
        "max_busy_percent",
        "busy_relative_to_fixed",
        "busy_reduction_vs_fixed_percent",
        "saturated",
    ]

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in out:
            w.writerow({k: r.get(k) for k in fieldnames})

    md = []
    md.append("# Аппаратная проекция расчётных стратегий статьи 3\n")
    md.append("## Назначение\n")
    md.append(
        "Расчётные стратегии статьи 3 заданы в физическом времени. "
        "Здесь число полных проходов за расчётный период переводится в оценку "
        "занятости интерфейса ЗУ для контроллера полного прохода.\n"
    )

    md.append("## Исходные параметры\n")
    md.append(f"- Расчётный период, ч: {args.window_hours:.0f}")
    md.append(f"- Расчётный период, с: {total_seconds:.0f}")
    md.append(f"- Число кодовых слов: {args.codeword_count}")
    md.append(f"- Тактовая частота контроллера, Гц: {args.clock_hz:.0f}")
    md.append(f"- Тактов на кодовое слово: {args.cycles_per_word:.3f}")
    md.append(f"- Служебные такты прохода: {args.pass_overhead_cycles:.3f}")
    md.append(f"- Полный проход, тактов: {pass_cycles:.3f}")
    md.append(f"- Полный проход, с: {pass_seconds:.9f}\n")

    md.append("## Сводка\n")
    md.append(
        "| Стратегия | Проходов за период | Pм | Pmax за цикл | Средний τ, с | "
        "Диапазон τ, с | Средняя занятость, % | Максимальная локальная занятость, % | "
        "Занятость относительно fixed | Снижение занятости к fixed | Насыщение |"
    )
    md.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")

    for r in out:
        tau_range = f"{r['tau_min_seconds']:.3f}–{r['tau_max_seconds']:.3f}"
        md.append(
            f"| `{md_escape(r['strategy'])}` | {r['cycles']} | "
            f"{r['P_mission']:.6g} | {r['Pmax_per_cycle']:.6g} | "
            f"{r['mean_tau_seconds']:.3f} | {tau_range} | "
            f"{r['mean_busy_percent']:.6f} | {r['max_busy_percent']:.6f} | "
            f"{r['busy_relative_to_fixed']:.6f} | "
            f"{r['busy_reduction_vs_fixed_percent']:.2f} % | {r['saturated']} |"
        )

    md.append("\n## Интерпретация\n")
    if any(r["saturated"] for r in out):
        md.append(
            "Для части стратегий минимальный интервал не превышает длительность полного прохода. "
            "В этих точках контроллер полного прохода оказывается в насыщении."
        )
    else:
        md.append(
            "Для всех расчётных стратегий минимальный интервал больше длительности полного прохода. "
            "Следовательно, при заданных параметрах контроллер может исполнить интервалы статьи 3 "
            "без насыщения."
        )

    md.append(
        "\nСредняя занятость интерфейса вычислена как произведение числа полных проходов "
        "за расчётный период на длительность одного прохода, делённое на длительность "
        "расчётного периода. Эта оценка относится к физической аппаратной проекции, "
        "а не к нормированной RTL-модели малого объёма."
    )

    md_path = Path(args.md_output)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text("\n".join(md) + "\n", encoding="utf-8")

    print(f"CSV: {csv_path}")
    print(f"MD:  {md_path}")
    print(md_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()

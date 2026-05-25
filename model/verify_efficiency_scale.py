#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from upsets_series import load_full_upsets_series

from risk_core import (
    DEFAULT_ALPHA,
    DEFAULT_INTERVALS_SECONDS,
    DEFAULT_TARGET_PMISSION,
    attach_efficiency_metrics,
    compute_series_stats,
    current_estimate,
    delayed_estimate,
    fixed_allowed_at_target,
    fixed_continuous_at_target,
    modified_delayed_estimate,
    parse_intervals_seconds,
    select_window,
    strategy_for_estimate,
    target_risk_from_probability,
)


def format_float(value: float | None, digits: int = 9) -> str:
    if value is None:
        return ""

    return f"{value:.{digits}g}"


def strategy_row(result) -> dict[str, str]:
    risk = result.risk

    return {
        "strategy": result.name,
        "c": format_float(result.c_value, 12),
        "E": format_float(risk.risk_e, 12),
        "P_mission": format_float(risk.p_mission, 12),
        "cycles": format_float(risk.cycles, 12),
        "Pmax_per_cycle": format_float(risk.p_max_cycle, 12),
        "mean_tau_seconds": format_float(risk.mean_tau_seconds, 12),
        "tau_min_seconds": format_float(risk.min_tau_seconds, 12),
        "tau_max_seconds": format_float(risk.max_tau_seconds, 12),
        "eta_gain_vs_fixed": format_float(result.eta_gain_vs_fixed, 12),
        "rho_loss_vs_ideal": format_float(result.rho_loss_vs_ideal, 12),
    }


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "strategy",
        "c",
        "E",
        "P_mission",
        "cycles",
        "Pmax_per_cycle",
        "mean_tau_seconds",
        "tau_min_seconds",
        "tau_max_seconds",
        "eta_gain_vs_fixed",
        "rho_loss_vs_ideal",
    ]

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_md(
    path: Path,
    *,
    input_path: Path,
    start_index: int,
    window_size: int,
    target_pmission: float,
    target_e: float,
    intervals_seconds: tuple[float, ...],
    stats,
    rows: list[dict[str, str]],
    eta_numeric: float,
    eta_theory: float,
    eta_relative_error_percent: float,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []

    lines.append("# Проверка шкалы эффективности адаптивного скраббинга\n")

    lines.append("## Назначение\n")
    lines.append(
        "Скрипт проверяет расчётную шкалу эффективности в постановке равного риска: "
        "коэффициенты стратегий подбираются так, чтобы мера риска E не превышала "
        "целевое значение. RTL-модель здесь не используется.\n"
    )

    lines.append("## Исходные данные\n")
    lines.append(f"- Входной файл: `{input_path}`")
    lines.append(f"- Начальный индекс окна: {start_index}")
    lines.append(f"- Размер окна: {window_size}")
    lines.append(f"- Целевая вероятность Pм*: {target_pmission:.12g}")
    lines.append(f"- Целевая мера риска E*: {target_e:.12g}")
    lines.append(
        "- Допустимые интервалы, с: "
        + ", ".join(f"{value:g}" for value in intervals_seconds)
    )
    lines.append("")

    lines.append("## Статистика ряда\n")
    lines.append(f"- Число отсчётов: {stats.count}")
    lines.append(f"- Минимум ν(t): {stats.minimum:.12g}")
    lines.append(f"- Среднее ν(t): {stats.mean_value:.12g}")
    lines.append(f"- Максимум ν(t): {stats.maximum:.12g}")
    lines.append(f"- CV²: {stats.cv2:.12g}")
    lines.append(f"- 1 + CV²: {stats.eta_max_theory:.12g}")
    lines.append("")

    lines.append("## Сравнение аналитической и численной эффективности\n")
    lines.append(f"- ηmax аналитически = 1 + CV² = {eta_theory:.12g}")
    lines.append(f"- ηideal численно = Nfixed / Nideal = {eta_numeric:.12g}")
    lines.append(f"- Относительное расхождение, %: {eta_relative_error_percent:.6g}")
    lines.append("")

    lines.append("## Сводка стратегий\n")
    lines.append(
        "| Стратегия | c | E | Pм | Циклов | Pmax за цикл | "
        "Средний τ, с | Диапазон τ, с | η=Nfixed/N | ρ=N/Nideal |"
    )
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")

    for row in rows:
        tau_range = f"{row['tau_min_seconds']}–{row['tau_max_seconds']}"
        lines.append(
            f"| `{row['strategy']}` | {row['c']} | {row['E']} | "
            f"{row['P_mission']} | {row['cycles']} | "
            f"{row['Pmax_per_cycle']} | {row['mean_tau_seconds']} | "
            f"{tau_range} | {row['eta_gain_vs_fixed']} | "
            f"{row['rho_loss_vs_ideal']} |"
        )

    lines.append("\n## Интерпретация\n")
    lines.append(
        "Для идеальной текущей оценки ν̂(t)=ν(t) численное отношение "
        "Nfixed/Nideal должно совпадать с аналитическим значением 1+CV². "
        "Для задержанной и модифицированной задержанной оценок величина ρ "
        "показывает цену неидеальности управляющего сигнала относительно "
        "идеальной адаптации."
    )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/upsets.xlsx"),
        help="Input Excel file with upset time series source data.",
    )
    parser.add_argument(
        "--start-index",
        type=int,
        default=0,
        help="Start index of the selected time-series window.",
    )
    parser.add_argument(
        "--window-size",
        type=int,
        default=43824,
        help="Number of hourly points in the selected window.",
    )
    parser.add_argument(
        "--target-pmission",
        type=float,
        default=DEFAULT_TARGET_PMISSION,
        help="Target mission probability of uncorrectable error.",
    )
    parser.add_argument(
        "--intervals-seconds",
        default=",".join(f"{value:g}" for value in DEFAULT_INTERVALS_SECONDS),
        help="Comma-separated allowed scrub intervals in seconds.",
    )
    parser.add_argument(
        "--alpha",
        type=float,
        default=DEFAULT_ALPHA,
        help="Quadratic risk coefficient alpha.",
    )
    parser.add_argument(
        "--growth-threshold",
        type=float,
        default=1.35,
        help="Q threshold for modified delayed estimate.",
    )
    parser.add_argument(
        "--growth-beta",
        type=float,
        default=0.7,
        help="Beta exponent for modified delayed estimate.",
    )
    parser.add_argument(
        "--growth-rmax",
        type=float,
        default=2.5,
        help="Maximum multiplier for modified delayed estimate.",
    )
    parser.add_argument(
        "--csv-output",
        type=Path,
        default=Path("results/paper/tables/efficiency_scale_verification.csv"),
        help="Output CSV path.",
    )
    parser.add_argument(
        "--md-output",
        type=Path,
        default=Path("results/paper/tables/efficiency_scale_verification.md"),
        help="Output Markdown path.",
    )

    args = parser.parse_args()

    values = load_full_upsets_series(args.input)
    nu_values = select_window(
        values=values,
        start_index=args.start_index,
        window_size=args.window_size,
    )

    intervals_seconds = parse_intervals_seconds(args.intervals_seconds)
    target_e = target_risk_from_probability(args.target_pmission)
    stats = compute_series_stats(nu_values)

    _fixed_tau_hour, fixed_risk = fixed_continuous_at_target(
        nu_values=nu_values,
        target_e=target_e,
        alpha=args.alpha,
    )

    current = current_estimate(nu_values)
    delayed = delayed_estimate(nu_values, delay_points=1)
    modified = modified_delayed_estimate(
        nu_values=nu_values,
        q_threshold=args.growth_threshold,
        beta=args.growth_beta,
        r_max=args.growth_rmax,
    )

    ideal_c, ideal_risk = strategy_for_estimate(
        nu_values=nu_values,
        estimate_values=current,
        target_e=target_e,
        allowed_seconds=None,
        alpha=args.alpha,
    )

    strategies = []

    strategies.append(
        attach_efficiency_metrics(
            name="fixed_continuous_at_target",
            c_value=None,
            risk=fixed_risk,
            fixed_reference=fixed_risk,
            ideal_reference=ideal_risk,
        )
    )

    fixed_allowed_seconds, fixed_allowed_risk = fixed_allowed_at_target(
        nu_values=nu_values,
        target_e=target_e,
        allowed_seconds=intervals_seconds,
        alpha=args.alpha,
    )
    strategies.append(
        attach_efficiency_metrics(
            name=f"fixed_allowed_{fixed_allowed_seconds:g}s",
            c_value=None,
            risk=fixed_allowed_risk,
            fixed_reference=fixed_risk,
            ideal_reference=ideal_risk,
        )
    )

    strategies.append(
        attach_efficiency_metrics(
            name="adaptive_current_continuous",
            c_value=ideal_c,
            risk=ideal_risk,
            fixed_reference=fixed_risk,
            ideal_reference=ideal_risk,
        )
    )

    for name, estimate in [
        ("adaptive_current_discrete", current),
        ("adaptive_delayed_1h_discrete", delayed),
        ("adaptive_modified_delayed_1h_discrete", modified),
    ]:
        c_value, risk = strategy_for_estimate(
            nu_values=nu_values,
            estimate_values=estimate,
            target_e=target_e,
            allowed_seconds=intervals_seconds,
            alpha=args.alpha,
        )
        strategies.append(
            attach_efficiency_metrics(
                name=name,
                c_value=c_value,
                risk=risk,
                fixed_reference=fixed_risk,
                ideal_reference=ideal_risk,
            )
        )

    rows = [strategy_row(result) for result in strategies]

    eta_numeric = fixed_risk.cycles / ideal_risk.cycles
    eta_theory = stats.eta_max_theory
    eta_relative_error_percent = (
        abs(eta_numeric - eta_theory) / eta_theory * 100.0
        if eta_theory > 0.0
        else 0.0
    )

    if eta_relative_error_percent > 1e-6:
        raise RuntimeError(
            "Numerical ideal eta does not match 1+CV^2: "
            f"eta_numeric={eta_numeric}, eta_theory={eta_theory}, "
            f"relative_error_percent={eta_relative_error_percent}"
        )

    write_csv(args.csv_output, rows)

    write_md(
        args.md_output,
        input_path=args.input,
        start_index=args.start_index,
        window_size=args.window_size,
        target_pmission=args.target_pmission,
        target_e=target_e,
        intervals_seconds=intervals_seconds,
        stats=stats,
        rows=rows,
        eta_numeric=eta_numeric,
        eta_theory=eta_theory,
        eta_relative_error_percent=eta_relative_error_percent,
    )

    print(f"CSV: {args.csv_output}")
    print(f"MD:  {args.md_output}")
    print(args.md_output.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()

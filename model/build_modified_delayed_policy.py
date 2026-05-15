#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path
from statistics import mean

from upsets_series import load_full_upsets_series
from scrub_risk_policy import (
    DEFAULT_ALPHA,
    DEFAULT_INTERVALS_SECONDS,
    DEFAULT_TARGET_PMISSION,
    DT_HOURS,
    EPS_NU,
    StrategyResult,
    RiskStats,
    assign_deviations,
    clamp_value,
    fixed_continuous_at_target,
    fixed_allowed_at_target,
    mission_probability_from_risk,
    nearest_log_interval_seconds,
    parse_intervals_seconds,
    q_cycle_quadratic,
    risk_stats_for_tau_hours,
    select_window,
    target_risk_from_probability,
    continuous_adaptive_current_analytic,
    adaptive_policy_result,
    write_strategy_summary_csv,
    write_csv,
)


def modified_delayed_estimate(
    nu_values: list[float],
    q_threshold: float,
    beta: float,
    r_max: float,
) -> list[float]:
    """
    Формирует задержанную оценку с поправкой на быстрый рост ряда.

    Базовая задержанная оценка:
        nu_hat(t) = nu(t-1)

    Если на предыдущем шаге наблюдался рост:
        r(t) = nu(t-1) / nu(t-2),

    то при r(t) > q_threshold вводится множитель:
        M(t) = min(r_max, r(t)^beta).

    Для первых двух отсчётов используется доступное предыдущее значение.
    """
    if not nu_values:
        return []

    if len(nu_values) == 1:
        return [nu_values[0]]

    result: list[float] = []

    for i in range(len(nu_values)):
        if i == 0:
            base = nu_values[0]
            multiplier = 1.0
        elif i == 1:
            base = nu_values[0]
            multiplier = 1.0
        else:
            prev = max(nu_values[i - 1], EPS_NU)
            prevprev = max(nu_values[i - 2], EPS_NU)
            base = prev
            ratio = prev / prevprev

            if ratio > q_threshold:
                multiplier = min(r_max, ratio ** beta)
            else:
                multiplier = 1.0

        result.append(base * multiplier)

    return result


def tau_from_c_over_estimate(
    estimate_values: list[float],
    c_value: float,
    allowed_seconds: tuple[float, ...] | None,
) -> list[float]:
    tau_hours: list[float] = []

    for estimate in estimate_values:
        safe_estimate = max(estimate, EPS_NU)
        tau_hour_continuous = c_value / safe_estimate

        if allowed_seconds is None:
            tau_hours.append(tau_hour_continuous)
            continue

        tau_seconds = tau_hour_continuous * 3600.0
        tau_seconds = clamp_value(
            tau_seconds,
            minimum=allowed_seconds[0],
            maximum=allowed_seconds[-1],
        )
        tau_seconds = nearest_log_interval_seconds(
            tau_seconds=tau_seconds,
            allowed_seconds=allowed_seconds,
        )

        tau_hours.append(tau_seconds / 3600.0)

    return tau_hours


def risk_for_c_estimate(
    nu_values: list[float],
    estimate_values: list[float],
    c_value: float,
    allowed_seconds: tuple[float, ...] | None,
    alpha: float,
) -> RiskStats:
    tau_hours = tau_from_c_over_estimate(
        estimate_values=estimate_values,
        c_value=c_value,
        allowed_seconds=allowed_seconds,
    )

    return risk_stats_for_tau_hours(
        nu_values=nu_values,
        tau_hours=tau_hours,
        alpha=alpha,
    )


def find_largest_c_under_risk_estimate(
    nu_values: list[float],
    estimate_values: list[float],
    target_e: float,
    allowed_seconds: tuple[float, ...] | None,
    alpha: float,
) -> tuple[float, RiskStats]:
    low = 0.0
    high = 1.0

    while True:
        high_risk = risk_for_c_estimate(
            nu_values=nu_values,
            estimate_values=estimate_values,
            c_value=high,
            allowed_seconds=allowed_seconds,
            alpha=alpha,
        )

        if high_risk.risk_e > target_e:
            break

        high *= 2.0

        if high > 1e12:
            raise ValueError("Could not bracket c value")

    best_c = low
    best_risk = risk_for_c_estimate(
        nu_values=nu_values,
        estimate_values=estimate_values,
        c_value=best_c,
        allowed_seconds=allowed_seconds,
        alpha=alpha,
    )

    for _ in range(90):
        mid = 0.5 * (low + high)

        mid_risk = risk_for_c_estimate(
            nu_values=nu_values,
            estimate_values=estimate_values,
            c_value=mid,
            allowed_seconds=allowed_seconds,
            alpha=alpha,
        )

        if mid_risk.risk_e <= target_e:
            low = mid
            best_c = mid
            best_risk = mid_risk
        else:
            high = mid

    return best_c, best_risk


def modified_delayed_policy_result(
    nu_values: list[float],
    target_e: float,
    allowed_seconds: tuple[float, ...],
    alpha: float,
    q_threshold: float,
    beta: float,
    r_max: float,
) -> tuple[StrategyResult, list[float], list[float]]:
    estimate = modified_delayed_estimate(
        nu_values=nu_values,
        q_threshold=q_threshold,
        beta=beta,
        r_max=r_max,
    )

    c_value, risk = find_largest_c_under_risk_estimate(
        nu_values=nu_values,
        estimate_values=estimate,
        target_e=target_e,
        allowed_seconds=allowed_seconds,
        alpha=alpha,
    )

    tau_hours = tau_from_c_over_estimate(
        estimate_values=estimate,
        c_value=c_value,
        allowed_seconds=allowed_seconds,
    )

    return (
        StrategyResult(
            name="adaptive_modified_delayed_1h_discrete",
            c_value=c_value,
            risk=risk,
            deviation_from_practical_lower_percent=None,
        ),
        estimate,
        tau_hours,
    )


def schedule_rows_for_tau(
    nu_values: list[float],
    estimate_values: list[float],
    tau_hours: list[float],
    alpha: float,
) -> list[dict[str, str]]:
    rows = []

    for index, (nu_value, estimate_value, tau_hour) in enumerate(
        zip(nu_values, estimate_values, tau_hours)
    ):
        tau_seconds = tau_hour * 3600.0
        lambda_value = nu_value * tau_hour
        q_value = q_cycle_quadratic(lambda_value, alpha)
        cycles_per_hour = 1.0 / tau_hour

        rows.append(
            {
                "hour_index": str(index),
                "nu": f"{nu_value:.12g}",
                "nu_hat": f"{estimate_value:.12g}",
                "tau_seconds": f"{tau_seconds:.12g}",
                "lambda": f"{lambda_value:.12g}",
                "q_cycle": f"{q_value:.12g}",
                "cycles_per_hour": f"{cycles_per_hour:.12g}",
            }
        )

    return rows


def interval_usage_rows(
    schedule_rows: list[dict[str, str]],
    allowed_seconds: tuple[float, ...],
) -> list[dict[str, str]]:
    grouped: dict[float, list[dict[str, str]]] = {
        interval: []
        for interval in allowed_seconds
    }

    for row in schedule_rows:
        tau_seconds = float(row["tau_seconds"])
        grouped.setdefault(tau_seconds, []).append(row)

    rows = []
    total_hours = len(schedule_rows)

    for interval in allowed_seconds:
        group = grouped.get(interval, [])

        if group:
            nu_values = [float(row["nu"]) for row in group]
            cycles = sum(float(row["cycles_per_hour"]) for row in group)
            risk_e = sum(
                float(row["q_cycle"]) * float(row["cycles_per_hour"])
                for row in group
            )
            fraction = len(group) / total_hours if total_hours else 0.0

            rows.append(
                {
                    "interval_seconds": f"{interval:g}",
                    "hours": str(len(group)),
                    "fraction": f"{fraction:.9f}",
                    "cycles": f"{cycles:.6f}",
                    "risk_e": f"{risk_e:.12g}",
                    "nu_min": f"{min(nu_values):.12g}",
                    "nu_max": f"{max(nu_values):.12g}",
                }
            )
        else:
            rows.append(
                {
                    "interval_seconds": f"{interval:g}",
                    "hours": "0",
                    "fraction": "0.000000000",
                    "cycles": "0.000000",
                    "risk_e": "0",
                    "nu_min": "",
                    "nu_max": "",
                }
            )

    return rows


def write_markdown(
    output_path: Path,
    target_pmission: float,
    target_e: float,
    intervals_seconds: tuple[float, ...],
    q_threshold: float,
    beta: float,
    r_max: float,
    results: list[StrategyResult],
    practical_lower_name: str,
) -> None:
    lines = []
    lines.append("# Модифицированная задержанная расчётная политика")
    lines.append("")
    lines.append("## Назначение")
    lines.append("")
    lines.append(
        "Строится задержанная управляющая оценка с поправкой на быстрый рост "
        "частоты одиночных сбоев. Полученное расписание интервалов используется "
        "как входная расчётная политика для последующего RTL-моделирования."
    )
    lines.append("")
    lines.append("## Параметры")
    lines.append("")
    lines.append(f"- Целевая вероятность Pм*: {target_pmission:.9g}")
    lines.append(f"- Целевая мера риска E*: {target_e:.12g}")
    lines.append(
        "- Допустимые интервалы, с: "
        + ", ".join(f"{value:g}" for value in intervals_seconds)
    )
    lines.append(f"- Порог роста Q: {q_threshold:g}")
    lines.append(f"- Степенной показатель beta: {beta:g}")
    lines.append(f"- Ограничение множителя Rmax: {r_max:g}")
    lines.append("")
    lines.append("## Сравнение стратегий")
    lines.append("")
    lines.append(
        "| Стратегия | c | E | Pм | N циклов | Pmax за цикл | "
        "Средний τ, с | Диапазон τ, с | Отклонение от практической нижней границы |"
    )
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")

    for result in results:
        deviation = (
            ""
            if result.deviation_from_practical_lower_percent is None
            else f"{result.deviation_from_practical_lower_percent:+.3f} %"
        )
        c_text = "" if result.c_value is None else f"{result.c_value:.6g}"
        lines.append(
            f"| `{result.name}` "
            f"| {c_text} "
            f"| {result.risk.risk_e:.6g} "
            f"| {result.risk.p_mission:.6g} "
            f"| {result.risk.cycles:.0f} "
            f"| {result.risk.p_max_cycle:.6g} "
            f"| {result.risk.mean_tau_seconds:.3f} "
            f"| {result.risk.min_tau_seconds:.3f}–{result.risk.max_tau_seconds:.3f} "
            f"| {deviation} |"
        )

    lines.append("")
    lines.append("## Интерпретация")
    lines.append("")
    lines.append(
        f"Практической нижней границей оставлена стратегия `{practical_lower_name}`. "
        "Модифицированная задержанная стратегия сопоставляется с ней по числу циклов, "
        "при этом все стратегии нормированы по одной и той же целевой мере риска."
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("data/upsets.xlsx"))
    parser.add_argument("--start-index", type=int, default=0)
    parser.add_argument("--window-size", type=int, required=True)
    parser.add_argument("--target-pmission", type=float, default=DEFAULT_TARGET_PMISSION)
    parser.add_argument(
        "--intervals-seconds",
        default=",".join(f"{value:g}" for value in DEFAULT_INTERVALS_SECONDS),
    )
    parser.add_argument("--alpha", type=float, default=DEFAULT_ALPHA)
    parser.add_argument("--q-threshold", type=float, default=1.35)
    parser.add_argument("--beta", type=float, default=0.7)
    parser.add_argument("--r-max", type=float, default=2.5)
    parser.add_argument("--output-dir", type=Path, default=Path("results/paper/tables"))

    args = parser.parse_args()

    full_series = load_full_upsets_series(args.input)
    window = select_window(
        values=full_series,
        start_index=args.start_index,
        window_size=args.window_size,
    )

    intervals_seconds = parse_intervals_seconds(args.intervals_seconds)
    target_e = target_risk_from_probability(args.target_pmission)

    adaptive_continuous = continuous_adaptive_current_analytic(
        nu_values=window,
        target_e=target_e,
        alpha=args.alpha,
    )

    adaptive_current_discrete = adaptive_policy_result(
        nu_values=window,
        target_e=target_e,
        nu_hat_mode="current",
        allowed_seconds=intervals_seconds,
        alpha=args.alpha,
        name="adaptive_current_discrete",
    )

    adaptive_delayed_discrete = adaptive_policy_result(
        nu_values=window,
        target_e=target_e,
        nu_hat_mode="delayed_1h",
        allowed_seconds=intervals_seconds,
        alpha=args.alpha,
        name="adaptive_delayed_1h_discrete",
    )

    fixed_continuous = fixed_continuous_at_target(
        nu_values=window,
        target_e=target_e,
        alpha=args.alpha,
    )

    fixed_allowed = fixed_allowed_at_target(
        nu_values=window,
        target_e=target_e,
        allowed_seconds=intervals_seconds,
        alpha=args.alpha,
    )

    (
        adaptive_modified_delayed,
        modified_estimate,
        modified_tau_hours,
    ) = modified_delayed_policy_result(
        nu_values=window,
        target_e=target_e,
        allowed_seconds=intervals_seconds,
        alpha=args.alpha,
        q_threshold=args.q_threshold,
        beta=args.beta,
        r_max=args.r_max,
    )

    practical_lower_name = "adaptive_current_discrete"

    results = [
        adaptive_continuous,
        adaptive_current_discrete,
        adaptive_delayed_discrete,
        adaptive_modified_delayed,
        fixed_continuous,
        fixed_allowed,
    ]

    results = assign_deviations(
        results=results,
        practical_lower_name=practical_lower_name,
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)

    write_strategy_summary_csv(
        output_path=args.output_dir / "risk_policy_modified_delay_summary.csv",
        results=results,
    )

    schedule_rows = schedule_rows_for_tau(
        nu_values=window,
        estimate_values=modified_estimate,
        tau_hours=modified_tau_hours,
        alpha=args.alpha,
    )

    write_csv(
        output_path=args.output_dir / "risk_policy_schedule_modified_delay.csv",
        rows=schedule_rows,
        fieldnames=[
            "hour_index",
            "nu",
            "nu_hat",
            "tau_seconds",
            "lambda",
            "q_cycle",
            "cycles_per_hour",
        ],
    )

    usage_rows = interval_usage_rows(
        schedule_rows=schedule_rows,
        allowed_seconds=intervals_seconds,
    )

    write_csv(
        output_path=args.output_dir / "risk_policy_modified_delay_interval_usage.csv",
        rows=usage_rows,
        fieldnames=[
            "interval_seconds",
            "hours",
            "fraction",
            "cycles",
            "risk_e",
            "nu_min",
            "nu_max",
        ],
    )

    write_markdown(
        output_path=args.output_dir / "risk_policy_modified_delay_summary.md",
        target_pmission=args.target_pmission,
        target_e=target_e,
        intervals_seconds=intervals_seconds,
        q_threshold=args.q_threshold,
        beta=args.beta,
        r_max=args.r_max,
        results=results,
        practical_lower_name=practical_lower_name,
    )

    print(f"Summary: {args.output_dir / 'risk_policy_modified_delay_summary.md'}")
    print(f"Schedule: {args.output_dir / 'risk_policy_schedule_modified_delay.csv'}")
    print(f"Interval usage: {args.output_dir / 'risk_policy_modified_delay_interval_usage.csv'}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import math
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, pstdev

from upsets_series import load_full_upsets_series


WORD_BITS = 39
CODEWORD_COUNT = 1_935_832
TOTAL_BITS = WORD_BITS * CODEWORD_COUNT

# alpha = (Nсл - 1) / (2 * (Nкр - 1))
# Для рассматриваемой памяти получается около 2.52e-7.
DEFAULT_ALPHA = (WORD_BITS - 1) / (2.0 * (TOTAL_BITS - 1))

DEFAULT_TARGET_PMISSION = 0.01

DEFAULT_INTERVALS_SECONDS = (
    1.0,
    2.0,
    5.0,
    10.0,
    30.0,
    60.0,
    120.0,
    300.0,
    600.0,
    1200.0,
    1800.0,
    3600.0,
)

DT_HOURS = 1.0
EPS_NU = 1e-30


@dataclass(frozen=True)
class SeriesStats:
    count: int
    minimum: float
    maximum: float
    mean_value: float
    std_value: float
    cv2: float
    eta_constant_theory: float
    total_sum: float
    sum_squares: float


@dataclass(frozen=True)
class RiskStats:
    risk_e: float
    p_mission: float
    cycles: float
    p_max_cycle: float
    mean_tau_seconds: float
    min_tau_seconds: float
    max_tau_seconds: float


@dataclass(frozen=True)
class StrategyResult:
    name: str
    c_value: float | None
    risk: RiskStats
    deviation_from_practical_lower_percent: float | None


def select_window(
    values: list[float],
    start_index: int,
    window_size: int,
) -> list[float]:
    if start_index < 0:
        raise ValueError("start_index must be non-negative")

    if window_size <= 0:
        raise ValueError("window_size must be positive")

    end_index = start_index + window_size

    if end_index > len(values):
        raise ValueError(
            f"Requested window [{start_index}, {end_index}) exceeds "
            f"available series length {len(values)}"
        )

    return values[start_index:end_index]


def compute_series_stats(values: list[float]) -> SeriesStats:
    if not values:
        raise ValueError("Cannot compute stats of empty series")

    mean_value = mean(values)
    std_value = pstdev(values)
    cv2 = (std_value / mean_value) ** 2 if mean_value > 0.0 else 0.0

    return SeriesStats(
        count=len(values),
        minimum=min(values),
        maximum=max(values),
        mean_value=mean_value,
        std_value=std_value,
        cv2=cv2,
        eta_constant_theory=1.0 + cv2,
        total_sum=sum(values),
        sum_squares=sum(value * value for value in values),
    )


def parse_intervals_seconds(text: str) -> tuple[float, ...]:
    values: list[float] = []

    for raw_part in text.replace(";", ",").split(","):
        part = raw_part.strip()

        if not part:
            continue

        value = float(part)

        if value <= 0.0:
            raise ValueError(f"Interval must be positive: {value}")

        values.append(value)

    if not values:
        raise ValueError("No intervals provided")

    values = sorted(set(values))

    return tuple(values)


def target_risk_from_probability(p_mission: float) -> float:
    if p_mission <= 0.0 or p_mission >= 1.0:
        raise ValueError("Target mission probability must be inside (0, 1)")

    return -math.log(1.0 - p_mission)


def mission_probability_from_risk(risk_e: float) -> float:
    if risk_e < 0.0:
        raise ValueError("Risk E must be non-negative")

    return 1.0 - math.exp(-risk_e)


def q_cycle_quadratic(lambda_value: float, alpha: float) -> float:
    """
    Редкособытийное приближение статьи 3:
        q(lambda) ≈ alpha * lambda^2.

    Для выбора политики при Pм* = 1 % оптимальные интервалы попадают
    в область малых локальных вероятностей, где это приближение
    и даёт аналитическую шкалу eta = 1 + CV^2.
    """
    if lambda_value <= 0.0:
        return 0.0

    return alpha * lambda_value * lambda_value


def risk_stats_for_tau_hours(
    nu_values: list[float],
    tau_hours: list[float],
    alpha: float,
) -> RiskStats:
    if len(nu_values) != len(tau_hours):
        raise ValueError("nu_values and tau_hours must have the same length")

    risk_e = 0.0
    cycles = 0.0
    p_max_cycle = 0.0
    tau_seconds = []

    for nu_value, tau_hour in zip(nu_values, tau_hours):
        if tau_hour <= 0.0:
            raise ValueError("tau must be positive")

        lambda_value = nu_value * tau_hour
        q_value = q_cycle_quadratic(lambda_value, alpha)

        risk_e += q_value * DT_HOURS / tau_hour
        cycles += DT_HOURS / tau_hour
        p_max_cycle = max(p_max_cycle, q_value)
        tau_seconds.append(tau_hour * 3600.0)

    return RiskStats(
        risk_e=risk_e,
        p_mission=mission_probability_from_risk(risk_e),
        cycles=cycles,
        p_max_cycle=p_max_cycle,
        mean_tau_seconds=mean(tau_seconds),
        min_tau_seconds=min(tau_seconds),
        max_tau_seconds=max(tau_seconds),
    )


def nearest_log_interval_seconds(
    tau_seconds: float,
    allowed_seconds: tuple[float, ...],
) -> float:
    if tau_seconds <= 0.0:
        raise ValueError("tau_seconds must be positive")

    best_interval = allowed_seconds[0]
    best_distance = abs(math.log(tau_seconds / best_interval))

    for interval in allowed_seconds[1:]:
        distance = abs(math.log(tau_seconds / interval))

        if distance < best_distance:
            best_distance = distance
            best_interval = interval

    return best_interval


def clamp_value(value: float, minimum: float, maximum: float) -> float:
    if value < minimum:
        return minimum

    if value > maximum:
        return maximum

    return value


def nu_hat_series(
    nu_values: list[float],
    mode: str,
) -> list[float]:
    if mode == "current":
        return list(nu_values)

    if mode == "delayed_1h":
        if not nu_values:
            return []

        return [nu_values[0], *nu_values[:-1]]

    raise ValueError(f"Unsupported nu-hat mode: {mode}")


def tau_from_c_over_nu_hat(
    nu_values: list[float],
    c_value: float,
    nu_hat_mode: str,
    allowed_seconds: tuple[float, ...] | None,
) -> list[float]:
    estimate = nu_hat_series(nu_values, nu_hat_mode)

    if len(estimate) != len(nu_values):
        raise ValueError("nu_hat length mismatch")

    tau_hours: list[float] = []

    for estimate_value in estimate:
        safe_estimate = max(estimate_value, EPS_NU)
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


def risk_for_c_value(
    nu_values: list[float],
    c_value: float,
    nu_hat_mode: str,
    allowed_seconds: tuple[float, ...] | None,
    alpha: float,
) -> RiskStats:
    tau_hours = tau_from_c_over_nu_hat(
        nu_values=nu_values,
        c_value=c_value,
        nu_hat_mode=nu_hat_mode,
        allowed_seconds=allowed_seconds,
    )

    return risk_stats_for_tau_hours(
        nu_values=nu_values,
        tau_hours=tau_hours,
        alpha=alpha,
    )


def find_largest_c_under_risk(
    nu_values: list[float],
    target_e: float,
    nu_hat_mode: str,
    allowed_seconds: tuple[float, ...] | None,
    alpha: float,
) -> tuple[float, RiskStats]:
    if target_e <= 0.0:
        raise ValueError("target_e must be positive")

    low = 0.0
    high = 1.0

    while True:
        high_risk = risk_for_c_value(
            nu_values=nu_values,
            c_value=high,
            nu_hat_mode=nu_hat_mode,
            allowed_seconds=allowed_seconds,
            alpha=alpha,
        )

        if high_risk.risk_e > target_e:
            break

        high *= 2.0

        if high > 1e12:
            raise ValueError("Could not bracket c value")

    best_c = low
    best_risk = risk_for_c_value(
        nu_values=nu_values,
        c_value=best_c,
        nu_hat_mode=nu_hat_mode,
        allowed_seconds=allowed_seconds,
        alpha=alpha,
    )

    for _ in range(90):
        mid = 0.5 * (low + high)

        mid_risk = risk_for_c_value(
            nu_values=nu_values,
            c_value=mid,
            nu_hat_mode=nu_hat_mode,
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


def continuous_adaptive_current_analytic(
    nu_values: list[float],
    target_e: float,
    alpha: float,
) -> StrategyResult:
    total_nu = sum(nu_values) * DT_HOURS

    c_value = target_e / (alpha * total_nu)

    tau_hours = [
        c_value / max(nu_value, EPS_NU)
        for nu_value in nu_values
    ]

    risk = risk_stats_for_tau_hours(
        nu_values=nu_values,
        tau_hours=tau_hours,
        alpha=alpha,
    )

    return StrategyResult(
        name="adaptive_current_continuous",
        c_value=c_value,
        risk=risk,
        deviation_from_practical_lower_percent=None,
    )


def fixed_continuous_at_target(
    nu_values: list[float],
    target_e: float,
    alpha: float,
) -> StrategyResult:
    sum_nu_squared = sum(nu_value * nu_value for nu_value in nu_values) * DT_HOURS

    tau_hour = target_e / (alpha * sum_nu_squared)
    tau_hours = [tau_hour for _ in nu_values]

    risk = risk_stats_for_tau_hours(
        nu_values=nu_values,
        tau_hours=tau_hours,
        alpha=alpha,
    )

    return StrategyResult(
        name="fixed_continuous_at_target",
        c_value=None,
        risk=risk,
        deviation_from_practical_lower_percent=None,
    )


def fixed_allowed_at_target(
    nu_values: list[float],
    target_e: float,
    allowed_seconds: tuple[float, ...],
    alpha: float,
) -> StrategyResult:
    candidates: list[tuple[float, RiskStats]] = []

    for interval_seconds in allowed_seconds:
        tau_hours = [
            interval_seconds / 3600.0
            for _ in nu_values
        ]

        risk = risk_stats_for_tau_hours(
            nu_values=nu_values,
            tau_hours=tau_hours,
            alpha=alpha,
        )

        if risk.risk_e <= target_e:
            candidates.append((interval_seconds, risk))

    if candidates:
        interval_seconds, risk = max(candidates, key=lambda item: item[0])
    else:
        interval_seconds = allowed_seconds[0]
        tau_hours = [
            interval_seconds / 3600.0
            for _ in nu_values
        ]
        risk = risk_stats_for_tau_hours(
            nu_values=nu_values,
            tau_hours=tau_hours,
            alpha=alpha,
        )

    return StrategyResult(
        name=f"fixed_allowed_{interval_seconds:g}s",
        c_value=None,
        risk=risk,
        deviation_from_practical_lower_percent=None,
    )


def adaptive_policy_result(
    nu_values: list[float],
    target_e: float,
    nu_hat_mode: str,
    allowed_seconds: tuple[float, ...],
    alpha: float,
    name: str,
) -> StrategyResult:
    c_value, risk = find_largest_c_under_risk(
        nu_values=nu_values,
        target_e=target_e,
        nu_hat_mode=nu_hat_mode,
        allowed_seconds=allowed_seconds,
        alpha=alpha,
    )

    return StrategyResult(
        name=name,
        c_value=c_value,
        risk=risk,
        deviation_from_practical_lower_percent=None,
    )


def assign_deviations(
    results: list[StrategyResult],
    practical_lower_name: str,
) -> list[StrategyResult]:
    reference = None

    for result in results:
        if result.name == practical_lower_name:
            reference = result
            break

    if reference is None:
        return results

    updated: list[StrategyResult] = []

    for result in results:
        deviation = (
            (result.risk.cycles / reference.risk.cycles - 1.0) * 100.0
            if reference.risk.cycles > 0.0
            else None
        )

        updated.append(
            StrategyResult(
                name=result.name,
                c_value=result.c_value,
                risk=result.risk,
                deviation_from_practical_lower_percent=deviation,
            )
        )

    return updated


def policy_schedule_rows(
    nu_values: list[float],
    c_value: float,
    allowed_seconds: tuple[float, ...],
    alpha: float,
) -> list[dict[str, str]]:
    tau_hours = tau_from_c_over_nu_hat(
        nu_values=nu_values,
        c_value=c_value,
        nu_hat_mode="current",
        allowed_seconds=allowed_seconds,
    )

    rows: list[dict[str, str]] = []

    for index, (nu_value, tau_hour) in enumerate(zip(nu_values, tau_hours)):
        tau_seconds = tau_hour * 3600.0
        lambda_value = nu_value * tau_hour
        q_value = q_cycle_quadratic(lambda_value, alpha)
        cycles_per_hour = 1.0 / tau_hour

        rows.append(
            {
                "hour_index": str(index),
                "nu": f"{nu_value:.12g}",
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

    rows: list[dict[str, str]] = []
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


def interval_boundary_rows(
    c_value: float,
    allowed_seconds: tuple[float, ...],
) -> list[dict[str, str]]:
    """
    Границы по nu для логарифмического округления tau = c / nu
    к соседним интервалам из множества T.

    Если tau_boundary = sqrt(T_short * T_long), то
        nu_boundary = 3600*c / tau_boundary_seconds.
    """
    rows: list[dict[str, str]] = []

    for short_interval, long_interval in zip(allowed_seconds, allowed_seconds[1:]):
        tau_boundary = math.sqrt(short_interval * long_interval)
        nu_boundary = 3600.0 * c_value / tau_boundary

        rows.append(
            {
                "shorter_interval_seconds": f"{short_interval:g}",
                "longer_interval_seconds": f"{long_interval:g}",
                "tau_boundary_seconds": f"{tau_boundary:.12g}",
                "nu_boundary": f"{nu_boundary:.12g}",
            }
        )

    return rows


def write_csv(
    output_path: Path,
    rows: list[dict[str, str]],
    fieldnames: list[str],
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_strategy_summary_csv(
    output_path: Path,
    results: list[StrategyResult],
) -> None:
    rows: list[dict[str, str]] = []

    for result in results:
        rows.append(
            {
                "strategy": result.name,
                "c_value": "" if result.c_value is None else f"{result.c_value:.12g}",
                "risk_e": f"{result.risk.risk_e:.12g}",
                "p_mission": f"{result.risk.p_mission:.12g}",
                "cycles": f"{result.risk.cycles:.6f}",
                "p_max_cycle": f"{result.risk.p_max_cycle:.12g}",
                "mean_tau_seconds": f"{result.risk.mean_tau_seconds:.12g}",
                "min_tau_seconds": f"{result.risk.min_tau_seconds:.12g}",
                "max_tau_seconds": f"{result.risk.max_tau_seconds:.12g}",
                "deviation_from_practical_lower_percent": (
                    ""
                    if result.deviation_from_practical_lower_percent is None
                    else f"{result.deviation_from_practical_lower_percent:.6f}"
                ),
            }
        )

    write_csv(
        output_path=output_path,
        rows=rows,
        fieldnames=[
            "strategy",
            "c_value",
            "risk_e",
            "p_mission",
            "cycles",
            "p_max_cycle",
            "mean_tau_seconds",
            "min_tau_seconds",
            "max_tau_seconds",
            "deviation_from_practical_lower_percent",
        ],
    )


def write_markdown(
    output_path: Path,
    input_path: Path,
    start_index: int,
    window_size: int,
    target_pmission: float,
    target_e: float,
    alpha: float,
    intervals_seconds: tuple[float, ...],
    stats: SeriesStats,
    results: list[StrategyResult],
    practical_lower_name: str,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []

    lines.append("# Расчётно-рисковая политика скраббинга")
    lines.append("")
    lines.append("## Назначение")
    lines.append("")
    lines.append(
        "Этот отчёт строит расчётную политику скраббинга по вероятностной "
        "постановке статьи 3. На этом шаге политика только рассчитывается; "
        "подключение к RTL выполняется следующим шагом."
    )
    lines.append("")
    lines.append("## Входные параметры")
    lines.append("")
    lines.append(f"- Источник ряда: `{input_path}`")
    lines.append(f"- Начальный индекс: {start_index}")
    lines.append(f"- Размер окна: {window_size}")
    lines.append(f"- Целевая вероятность Pм*: {target_pmission:.9g}")
    lines.append(f"- Целевая мера риска E*: {target_e:.12g}")
    lines.append(f"- alpha: {alpha:.12g}")
    lines.append(
        "- Допустимые интервалы, с: "
        + ", ".join(f"{value:g}" for value in intervals_seconds)
    )
    lines.append("")
    lines.append("## Статистика ν(t)")
    lines.append("")
    lines.append(f"- Число точек: {stats.count}")
    lines.append(f"- Минимум: {stats.minimum:.9g}")
    lines.append(f"- Максимум: {stats.maximum:.9g}")
    lines.append(f"- Среднее: {stats.mean_value:.9g}")
    lines.append(f"- Стандартное отклонение: {stats.std_value:.9g}")
    lines.append(f"- CV²: {stats.cv2:.9g}")
    lines.append(f"- η_theory = 1 + CV²: {stats.eta_constant_theory:.9g}")
    lines.append("")
    lines.append("## Сравнение расчётных стратегий")
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
    lines.append("## Контрольная интерпретация")
    lines.append("")
    lines.append(
        f"Практической нижней границей для дальнейшего сопоставления принята "
        f"стратегия `{practical_lower_name}`: она использует тот же класс "
        "τ = c / ν̂(t), но с ограничениями Tmin/Tmax и дискретным множеством "
        "допустимых интервалов."
    )
    lines.append("")
    lines.append(
        "Дальнейшее подключение к RTL должно исполнять именно рассчитанную "
        "дискретную интервальную политику, а не статистическую нарезку ряда "
        "по перцентилям."
    )
    lines.append("")
    lines.append("## Ограничение текущего шага")
    lines.append("")
    lines.append(
        "В текущей версии используется редкособытийное квадратичное ядро "
        "q(λ) ≈ αλ². Оно является тем приближением, из которого следует "
        "шкала η = 1 + CV². Для финальной сверки при необходимости можно "
        "добавить точное пуассоновское q(λ), но сначала нужно убедиться, "
        "что базовые контрольные числа совпадают со статьёй 3."
    )

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build risk-based scrubbing policy from full ν(t) series."
    )

    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/upsets.xlsx"),
        help="Input Excel file with proton component used to build full ν(t).",
    )

    parser.add_argument(
        "--start-index",
        type=int,
        default=0,
        help="Start index in the full ν(t) series.",
    )

    parser.add_argument(
        "--window-size",
        type=int,
        required=True,
        help="Number of points in the selected ν(t) window.",
    )

    parser.add_argument(
        "--target-pmission",
        type=float,
        default=DEFAULT_TARGET_PMISSION,
        help="Target mission probability Pм*. Default: 0.01.",
    )

    parser.add_argument(
        "--intervals-seconds",
        default=",".join(f"{value:g}" for value in DEFAULT_INTERVALS_SECONDS),
        help="Comma-separated allowed scrubbing intervals in seconds.",
    )

    parser.add_argument(
        "--alpha",
        type=float,
        default=DEFAULT_ALPHA,
        help="Quadratic risk coefficient alpha.",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results/paper/tables"),
        help="Output directory for policy tables.",
    )

    args = parser.parse_args()

    full_series = load_full_upsets_series(args.input)
    window = select_window(
        values=full_series,
        start_index=args.start_index,
        window_size=args.window_size,
    )

    stats = compute_series_stats(window)
    intervals_seconds = parse_intervals_seconds(args.intervals_seconds)
    target_e = target_risk_from_probability(args.target_pmission)

    adaptive_continuous = continuous_adaptive_current_analytic(
        nu_values=window,
        target_e=target_e,
        alpha=args.alpha,
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

    results = [
        adaptive_continuous,
        adaptive_current_discrete,
        adaptive_delayed_discrete,
        fixed_continuous,
        fixed_allowed,
    ]

    practical_lower_name = "adaptive_current_discrete"
    results = assign_deviations(
        results=results,
        practical_lower_name=practical_lower_name,
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)

    write_strategy_summary_csv(
        output_path=args.output_dir / "risk_policy_summary.csv",
        results=results,
    )

    if adaptive_current_discrete.c_value is None:
        raise ValueError("Adaptive current discrete policy has no c value")

    schedule_rows = policy_schedule_rows(
        nu_values=window,
        c_value=adaptive_current_discrete.c_value,
        allowed_seconds=intervals_seconds,
        alpha=args.alpha,
    )

    write_csv(
        output_path=args.output_dir / "risk_policy_schedule.csv",
        rows=schedule_rows,
        fieldnames=[
            "hour_index",
            "nu",
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
        output_path=args.output_dir / "risk_policy_interval_usage.csv",
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

    boundary_rows = interval_boundary_rows(
        c_value=adaptive_current_discrete.c_value,
        allowed_seconds=intervals_seconds,
    )

    write_csv(
        output_path=args.output_dir / "risk_policy_boundaries.csv",
        rows=boundary_rows,
        fieldnames=[
            "shorter_interval_seconds",
            "longer_interval_seconds",
            "tau_boundary_seconds",
            "nu_boundary",
        ],
    )

    write_markdown(
        output_path=args.output_dir / "risk_policy_summary.md",
        input_path=args.input,
        start_index=args.start_index,
        window_size=args.window_size,
        target_pmission=args.target_pmission,
        target_e=target_e,
        alpha=args.alpha,
        intervals_seconds=intervals_seconds,
        stats=stats,
        results=results,
        practical_lower_name=practical_lower_name,
    )

    print(f"Series count: {stats.count}")
    print(f"Mean ν(t): {stats.mean_value:.9g}")
    print(f"CV^2: {stats.cv2:.9g}")
    print(f"Eta theory 1+CV^2: {stats.eta_constant_theory:.9g}")
    print(f"Target E*: {target_e:.12g}")
    print(f"Summary: {args.output_dir / 'risk_policy_summary.md'}")
    print(f"Schedule: {args.output_dir / 'risk_policy_schedule.csv'}")
    print(f"Interval usage: {args.output_dir / 'risk_policy_interval_usage.csv'}")
    print(f"Boundaries: {args.output_dir / 'risk_policy_boundaries.csv'}")


if __name__ == "__main__":
    main()
#!/usr/bin/env python3

from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import mean, pstdev


WORD_BITS = 39
CODEWORD_COUNT = 1_935_832
TOTAL_BITS = WORD_BITS * CODEWORD_COUNT

# alpha = (Nсл - 1) / (2 * (Nкр - 1))
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
    eta_max_theory: float
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
    eta_gain_vs_fixed: float | None
    rho_loss_vs_ideal: float | None


def select_window(values: list[float], start_index: int, window_size: int) -> list[float]:
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
        eta_max_theory=1.0 + cv2,
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

    return tuple(sorted(set(values)))


def target_risk_from_probability(p_mission: float) -> float:
    if p_mission <= 0.0 or p_mission >= 1.0:
        raise ValueError("Target mission probability must be inside (0, 1)")

    return -math.log(1.0 - p_mission)


def mission_probability_from_risk(risk_e: float) -> float:
    if risk_e < 0.0:
        raise ValueError("Risk E must be non-negative")

    return 1.0 - math.exp(-risk_e)


def q_cycle_quadratic(lambda_value: float, alpha: float = DEFAULT_ALPHA) -> float:
    """
    Редкособытийное приближение:
        q(lambda) ≈ alpha * lambda^2.
    """
    if lambda_value <= 0.0:
        return 0.0

    return alpha * lambda_value * lambda_value


def risk_stats_for_tau_hours(
    nu_values: list[float],
    tau_hours: list[float],
    alpha: float = DEFAULT_ALPHA,
) -> RiskStats:
    if len(nu_values) != len(tau_hours):
        raise ValueError("nu_values and tau_hours must have the same length")

    risk_e = 0.0
    cycles = 0.0
    p_max_cycle = 0.0
    tau_seconds_values: list[float] = []

    for nu_value, tau_hour in zip(nu_values, tau_hours):
        if tau_hour <= 0.0:
            raise ValueError("tau must be positive")

        lambda_value = nu_value * tau_hour
        q_value = q_cycle_quadratic(lambda_value=lambda_value, alpha=alpha)

        risk_e += q_value * DT_HOURS / tau_hour
        cycles += DT_HOURS / tau_hour
        p_max_cycle = max(p_max_cycle, q_value)
        tau_seconds_values.append(tau_hour * 3600.0)

    return RiskStats(
        risk_e=risk_e,
        p_mission=mission_probability_from_risk(risk_e),
        cycles=cycles,
        p_max_cycle=p_max_cycle,
        mean_tau_seconds=mean(tau_seconds_values),
        min_tau_seconds=min(tau_seconds_values),
        max_tau_seconds=max(tau_seconds_values),
    )


def clamp_value(value: float, minimum: float, maximum: float) -> float:
    if value < minimum:
        return minimum

    if value > maximum:
        return maximum

    return value


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


def discretize_tau_seconds(
    tau_seconds: float,
    allowed_seconds: tuple[float, ...],
) -> float:
    tau_seconds = clamp_value(
        value=tau_seconds,
        minimum=allowed_seconds[0],
        maximum=allowed_seconds[-1],
    )

    return nearest_log_interval_seconds(
        tau_seconds=tau_seconds,
        allowed_seconds=allowed_seconds,
    )


def current_estimate(nu_values: list[float]) -> list[float]:
    return list(nu_values)


def delayed_estimate(nu_values: list[float], delay_points: int = 1) -> list[float]:
    if delay_points < 0:
        raise ValueError("delay_points must be non-negative")

    if not nu_values:
        return []

    if delay_points == 0:
        return list(nu_values)

    result: list[float] = []

    for index in range(len(nu_values)):
        source_index = index - delay_points

        if source_index < 0:
            result.append(nu_values[0])
        else:
            result.append(nu_values[source_index])

    return result


def modified_delayed_estimate(
    nu_values: list[float],
    q_threshold: float = 1.35,
    beta: float = 0.7,
    r_max: float = 2.5,
) -> list[float]:
    """
    Задержанная оценка с поправкой на быстрый рост:

        nu_hat(t) = nu(t-1) * M(t),

    где при r(t)=nu(t-1)/nu(t-2) > Q:
        M(t)=min(Rmax, r(t)^beta).
    """
    if not nu_values:
        return []

    if len(nu_values) == 1:
        return [nu_values[0]]

    result: list[float] = []

    for index in range(len(nu_values)):
        if index == 0:
            base = nu_values[0]
            multiplier = 1.0
        elif index == 1:
            base = nu_values[0]
            multiplier = 1.0
        else:
            prev = max(nu_values[index - 1], EPS_NU)
            prevprev = max(nu_values[index - 2], EPS_NU)
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
    allowed_seconds: tuple[float, ...] | None = None,
) -> list[float]:
    tau_hours: list[float] = []

    for estimate_value in estimate_values:
        safe_estimate = max(estimate_value, EPS_NU)
        tau_hour_continuous = c_value / safe_estimate

        if allowed_seconds is None:
            tau_hours.append(tau_hour_continuous)
            continue

        tau_seconds = tau_hour_continuous * 3600.0
        tau_seconds = discretize_tau_seconds(
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
    alpha: float = DEFAULT_ALPHA,
) -> RiskStats:
    if len(nu_values) != len(estimate_values):
        raise ValueError("nu_values and estimate_values must have the same length")

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
    alpha: float = DEFAULT_ALPHA,
) -> tuple[float, RiskStats]:
    if target_e <= 0.0:
        raise ValueError("target_e must be positive")

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

    best_c: float | None = None
    best_risk: RiskStats | None = None

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

    if best_c is None or best_risk is None:
        raise RuntimeError("Binary search did not find feasible positive c")

    return best_c, best_risk


def fixed_continuous_at_target(
    nu_values: list[float],
    target_e: float,
    alpha: float = DEFAULT_ALPHA,
) -> tuple[float, RiskStats]:
    sum_nu_squared = sum(value * value for value in nu_values) * DT_HOURS
    tau_hour = target_e / (alpha * sum_nu_squared)
    tau_hours = [tau_hour for _ in nu_values]

    risk = risk_stats_for_tau_hours(
        nu_values=nu_values,
        tau_hours=tau_hours,
        alpha=alpha,
    )

    return tau_hour, risk


def fixed_allowed_at_target(
    nu_values: list[float],
    target_e: float,
    allowed_seconds: tuple[float, ...],
    alpha: float = DEFAULT_ALPHA,
) -> tuple[float, RiskStats]:
    candidates: list[tuple[float, RiskStats]] = []

    for interval_seconds in allowed_seconds:
        tau_hours = [interval_seconds / 3600.0 for _ in nu_values]
        risk = risk_stats_for_tau_hours(
            nu_values=nu_values,
            tau_hours=tau_hours,
            alpha=alpha,
        )

        if risk.risk_e <= target_e:
            candidates.append((interval_seconds, risk))

    if candidates:
        return max(candidates, key=lambda item: item[0])

    interval_seconds = allowed_seconds[0]
    tau_hours = [interval_seconds / 3600.0 for _ in nu_values]
    risk = risk_stats_for_tau_hours(
        nu_values=nu_values,
        tau_hours=tau_hours,
        alpha=alpha,
    )
    return interval_seconds, risk


def strategy_for_estimate(
    nu_values: list[float],
    estimate_values: list[float],
    target_e: float,
    allowed_seconds: tuple[float, ...] | None,
    alpha: float = DEFAULT_ALPHA,
) -> tuple[float, RiskStats]:
    c_value, risk = find_largest_c_under_risk_estimate(
        nu_values=nu_values,
        estimate_values=estimate_values,
        target_e=target_e,
        allowed_seconds=allowed_seconds,
        alpha=alpha,
    )

    return c_value, risk


def attach_efficiency_metrics(
    name: str,
    c_value: float | None,
    risk: RiskStats,
    fixed_reference: RiskStats,
    ideal_reference: RiskStats,
) -> StrategyResult:
    eta_gain = (
        fixed_reference.cycles / risk.cycles
        if risk.cycles > 0.0
        else None
    )

    rho_loss = (
        risk.cycles / ideal_reference.cycles
        if ideal_reference.cycles > 0.0
        else None
    )

    return StrategyResult(
        name=name,
        c_value=c_value,
        risk=risk,
        eta_gain_vs_fixed=eta_gain,
        rho_loss_vs_ideal=rho_loss,
    )

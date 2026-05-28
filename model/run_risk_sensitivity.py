#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import math
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, pstdev

from upsets_series import load_full_upsets_series

from risk_core import (
    DEFAULT_ALPHA,
    DEFAULT_INTERVALS_SECONDS,
    DEFAULT_TARGET_PMISSION,
    compute_series_stats,
    current_estimate,
    fixed_continuous_at_target,
    parse_intervals_seconds,
    select_window,
    risk_stats_for_tau_hours,
    strategy_for_estimate,
    target_risk_from_probability,
)


@dataclass(frozen=True)
class SensitivityCase:
    case: str
    group: str
    values: list[float]
    intervals_seconds: tuple[float, ...]


@dataclass(frozen=True)
class SensitivityResult:
    case: str
    group: str
    n: int
    mean_nu: float
    max_nu: float
    cv2: float
    eta_theory: float
    eta_numeric: float
    eta_relative_error_percent: float
    fixed_cycles: float
    ideal_cycles: float
    discrete_cycles: float
    discrete_loss_vs_ideal: float
    discrete_gain_vs_fixed: float
    p_mission_discrete: float
    tau_min_seconds: float
    tau_max_seconds: float
    intervals: str
    discrete_saturated_at_tau_max: bool


def moving_average(values: list[float], width: int) -> list[float]:
    if width <= 1:
        return list(values)

    if width > len(values):
        raise ValueError("moving average width exceeds series length")

    result: list[float] = []
    half = width // 2

    prefix = [0.0]
    for value in values:
        prefix.append(prefix[-1] + value)

    for i in range(len(values)):
        left = max(0, i - half)
        right = min(len(values), i + half + 1)
        result.append((prefix[right] - prefix[left]) / (right - left))

    return result


def winsorize(values: list[float], upper_quantile: float) -> list[float]:
    if not 0.0 < upper_quantile <= 1.0:
        raise ValueError("upper_quantile must be in (0, 1]")

    sorted_values = sorted(values)
    index = min(len(sorted_values) - 1, max(0, int(math.ceil(upper_quantile * len(sorted_values))) - 1))
    threshold = sorted_values[index]
    return [min(value, threshold) for value in values]


def normalized(values: list[float], target_mean: float = 1.0) -> list[float]:
    m = mean(values)
    if m <= 0.0:
        raise ValueError("cannot normalize non-positive mean series")
    return [value * target_mean / m for value in values]


def two_level_series(n: int, high_fraction: float, high_value: float, low_value: float = 1.0) -> list[float]:
    if not 0.0 < high_fraction < 1.0:
        raise ValueError("high_fraction must be in (0, 1)")

    high_count = max(1, min(n - 1, int(round(n * high_fraction))))
    values = [low_value] * n
    start = n // 2 - high_count // 2

    for i in range(start, start + high_count):
        values[i] = high_value

    return normalized(values)


def sinusoidal_series(n: int, amplitude: float) -> list[float]:
    if amplitude < 0.0 or amplitude >= 1.0:
        raise ValueError("amplitude must be in [0, 1)")

    values = [
        1.0 + amplitude * math.sin(2.0 * math.pi * i / n)
        for i in range(n)
    ]
    return normalized(values)


def burst_series(n: int, burst_count: int, burst_width: int, burst_value: float) -> list[float]:
    if burst_count <= 0 or burst_width <= 0:
        raise ValueError("burst_count and burst_width must be positive")

    values = [1.0] * n

    for b in range(burst_count):
        center = int((b + 0.5) * n / burst_count)
        left = max(0, center - burst_width // 2)
        right = min(n, left + burst_width)
        for i in range(left, right):
            values[i] = burst_value

    return normalized(values)


def format_intervals(intervals: tuple[float, ...]) -> str:
    return ",".join(f"{value:g}" for value in intervals)


def evaluate_case(
    case: SensitivityCase,
    *,
    target_e: float,
    alpha: float,
) -> SensitivityResult:
    stats = compute_series_stats(case.values)

    _fixed_tau, fixed_risk = fixed_continuous_at_target(
        nu_values=case.values,
        target_e=target_e,
        alpha=alpha,
    )

    ideal_c, ideal_risk = strategy_for_estimate(
        nu_values=case.values,
        estimate_values=current_estimate(case.values),
        target_e=target_e,
        allowed_seconds=None,
        alpha=alpha,
    )

    discrete_saturated_at_tau_max = False

    try:
        _discrete_c, discrete_risk = strategy_for_estimate(
            nu_values=case.values,
            estimate_values=current_estimate(case.values),
            target_e=target_e,
            allowed_seconds=case.intervals_seconds,
            alpha=alpha,
        )
    except ValueError as exc:
        if "Could not bracket c value" not in str(exc):
            raise

        # This is a mathematical saturation case, not a failure.
        # For low-intensity series the largest allowed interval may still be
        # below the target risk. Then no finite c can make the clamped
        # discrete policy exceed the risk target.
        max_tau_hours = case.intervals_seconds[-1] / 3600.0
        discrete_risk = risk_stats_for_tau_hours(
            nu_values=case.values,
            tau_hours=[max_tau_hours for _ in case.values],
            alpha=alpha,
        )
        discrete_saturated_at_tau_max = True

    eta_numeric = fixed_risk.cycles / ideal_risk.cycles
    eta_theory = stats.eta_max_theory
    eta_relative_error_percent = (
        abs(eta_numeric - eta_theory) / eta_theory * 100.0
        if eta_theory > 0.0
        else 0.0
    )

    return SensitivityResult(
        case=case.case,
        group=case.group,
        n=stats.count,
        mean_nu=stats.mean_value,
        max_nu=stats.maximum,
        cv2=stats.cv2,
        eta_theory=eta_theory,
        eta_numeric=eta_numeric,
        eta_relative_error_percent=eta_relative_error_percent,
        fixed_cycles=fixed_risk.cycles,
        ideal_cycles=ideal_risk.cycles,
        discrete_cycles=discrete_risk.cycles,
        discrete_loss_vs_ideal=discrete_risk.cycles / ideal_risk.cycles,
        discrete_gain_vs_fixed=fixed_risk.cycles / discrete_risk.cycles,
        p_mission_discrete=discrete_risk.p_mission,
        tau_min_seconds=discrete_risk.min_tau_seconds,
        tau_max_seconds=discrete_risk.max_tau_seconds,
        intervals=format_intervals(case.intervals_seconds),
        discrete_saturated_at_tau_max=discrete_saturated_at_tau_max,
    )


def write_csv(path: Path, rows: list[SensitivityResult]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    fields = [
        "case",
        "group",
        "n",
        "mean_nu",
        "max_nu",
        "cv2",
        "eta_theory",
        "eta_numeric",
        "eta_relative_error_percent",
        "fixed_cycles",
        "ideal_cycles",
        "discrete_cycles",
        "discrete_loss_vs_ideal",
        "discrete_gain_vs_fixed",
        "p_mission_discrete",
        "tau_min_seconds",
        "tau_max_seconds",
        "intervals",
        "discrete_saturated_at_tau_max",
    ]

    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()

        for r in rows:
            w.writerow({
                "case": r.case,
                "group": r.group,
                "n": r.n,
                "mean_nu": f"{r.mean_nu:.12g}",
                "max_nu": f"{r.max_nu:.12g}",
                "cv2": f"{r.cv2:.12g}",
                "eta_theory": f"{r.eta_theory:.12g}",
                "eta_numeric": f"{r.eta_numeric:.12g}",
                "eta_relative_error_percent": f"{r.eta_relative_error_percent:.12g}",
                "fixed_cycles": f"{r.fixed_cycles:.12g}",
                "ideal_cycles": f"{r.ideal_cycles:.12g}",
                "discrete_cycles": f"{r.discrete_cycles:.12g}",
                "discrete_loss_vs_ideal": f"{r.discrete_loss_vs_ideal:.12g}",
                "discrete_gain_vs_fixed": f"{r.discrete_gain_vs_fixed:.12g}",
                "p_mission_discrete": f"{r.p_mission_discrete:.12g}",
                "tau_min_seconds": f"{r.tau_min_seconds:.12g}",
                "tau_max_seconds": f"{r.tau_max_seconds:.12g}",
                "intervals": r.intervals,
                "discrete_saturated_at_tau_max": "yes" if r.discrete_saturated_at_tau_max else "no",
            })


def write_md(path: Path, rows: list[SensitivityResult], *, target_pmission: float, target_e: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []

    lines.append("# Risk sensitivity summary")
    lines.append("")
    lines.append("## Purpose")
    lines.append("")
    lines.append(
        "This report checks whether the analytical efficiency scale remains stable "
        "under changes of the input intensity series and the allowed scrub-period grid."
    )
    lines.append("")
    lines.append(f"- Target mission probability: {target_pmission:.12g}")
    lines.append(f"- Target risk measure E*: {target_e:.12g}")
    lines.append("")

    lines.append("## Main sensitivity table")
    lines.append("")
    lines.append("| case | group | CV² | η theory | η numeric | rel. error, % | discrete loss ρ | discrete gain ηd | τ range, s | saturated at τmax |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|---:|---|")

    for r in rows:
        lines.append(
            f"| `{r.case}` | {r.group} | "
            f"{r.cv2:.6g} | {r.eta_theory:.6g} | {r.eta_numeric:.6g} | "
            f"{r.eta_relative_error_percent:.3g} | {r.discrete_loss_vs_ideal:.6g} | "
            f"{r.discrete_gain_vs_fixed:.6g} | {r.tau_min_seconds:.6g}--{r.tau_max_seconds:.6g} | "
            f"{'yes' if r.discrete_saturated_at_tau_max else 'no'} |"
        )

    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    lines.append(
        "For every tested series the continuous ideal gain matches `1 + CV²` "
        "within numerical precision. Therefore the analytical scale is not tied "
        "to a single physical source series; it follows from the optimization "
        "problem under the stated assumptions."
    )
    lines.append("")
    lines.append(
        "Scaling the whole intensity series changes the absolute period values "
        "and the number of cycles required to meet the same risk target, but it "
        "does not change CV² and therefore does not change the theoretical "
        "relative gain. Smoothing and peak clipping reduce CV² and correspondingly "
        "reduce the possible gain from adaptation. Synthetic burst-like series "
        "increase CV² and therefore increase the theoretical upper bound."
    )
    lines.append("")
    lines.append(
        "`discrete_loss_vs_ideal` quantifies the price of using a finite interval "
        "grid instead of a continuous period. It is a hardware/project constraint, "
        "not a contradiction of the analytical η scale. `discrete_gain_vs_fixed` "
        "is computed against the continuous fixed-at-target reference; therefore "
        "it may be below one when a coarse period grid underuses the available risk "
        "budget. Cases marked as saturated at τmax mean that even the largest "
        "allowed scrub period remains within the risk target; therefore the "
        "discrete optimum is limited by the project period grid rather than by "
        "the risk constraint."
    )
    lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


def build_cases(
    base_values: list[float],
    *,
    default_intervals: tuple[float, ...],
    dense_intervals: tuple[float, ...],
    coarse_intervals: tuple[float, ...],
) -> list[SensitivityCase]:
    n = len(base_values)
    base_norm = normalized(base_values)

    cases: list[SensitivityCase] = []

    for scale in [0.1, 1.0, 10.0]:
        cases.append(
            SensitivityCase(
                case=f"real_scale_{scale:g}",
                group="scale",
                values=[scale * value for value in base_norm],
                intervals_seconds=default_intervals,
            )
        )

    for width in [3, 12, 24, 72]:
        cases.append(
            SensitivityCase(
                case=f"real_smoothed_w{width}",
                group="smoothing",
                values=normalized(moving_average(base_norm, width)),
                intervals_seconds=default_intervals,
            )
        )

    for q in [0.99, 0.95, 0.90]:
        cases.append(
            SensitivityCase(
                case=f"real_peak_clip_q{q:g}",
                group="peak_clip",
                values=normalized(winsorize(base_norm, q)),
                intervals_seconds=default_intervals,
            )
        )

    for name, intervals in [
        ("default_grid", default_intervals),
        ("dense_grid", dense_intervals),
        ("coarse_grid", coarse_intervals),
    ]:
        cases.append(
            SensitivityCase(
                case=f"real_{name}",
                group="period_grid",
                values=base_norm,
                intervals_seconds=intervals,
            )
        )

    synthetic_defs = [
        ("synthetic_flat", [1.0] * n),
        ("synthetic_sine_a0.25", sinusoidal_series(n, 0.25)),
        ("synthetic_sine_a0.75", sinusoidal_series(n, 0.75)),
        ("synthetic_two_level_10pct_x10", two_level_series(n, 0.10, 10.0)),
        ("synthetic_two_level_02pct_x50", two_level_series(n, 0.02, 50.0)),
        ("synthetic_bursts_5x48_x30", burst_series(n, 5, 48, 30.0)),
    ]

    for name, values in synthetic_defs:
        cases.append(
            SensitivityCase(
                case=name,
                group="synthetic",
                values=values,
                intervals_seconds=default_intervals,
            )
        )

    return cases


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path, default=Path("data/upsets.xlsx"))
    p.add_argument("--start-index", type=int, default=0)
    p.add_argument("--window-size", type=int, default=43824)
    p.add_argument("--target-pmission", type=float, default=DEFAULT_TARGET_PMISSION)
    p.add_argument("--alpha", type=float, default=DEFAULT_ALPHA)
    p.add_argument(
        "--default-intervals",
        default=",".join(f"{value:g}" for value in DEFAULT_INTERVALS_SECONDS),
    )
    p.add_argument(
        "--dense-intervals",
        default="1,1.5,2,3,5,7,10,15,20,30,45,60,90,120,180,300,450,600,900,1200,1800,2400,3600",
    )
    p.add_argument(
        "--coarse-intervals",
        default="1,10,60,300,1800,3600",
    )
    p.add_argument("--csv-output", type=Path, default=Path("results/paper/tables/risk_sensitivity.csv"))
    p.add_argument("--md-output", type=Path, default=Path("results/paper/tables/risk_sensitivity_summary.md"))
    return p.parse_args()


def main() -> None:
    args = parse_args()

    full_values = load_full_upsets_series(args.input)
    base_values = select_window(full_values, args.start_index, args.window_size)

    target_e = target_risk_from_probability(args.target_pmission)

    default_intervals = parse_intervals_seconds(args.default_intervals)
    dense_intervals = parse_intervals_seconds(args.dense_intervals)
    coarse_intervals = parse_intervals_seconds(args.coarse_intervals)

    cases = build_cases(
        base_values,
        default_intervals=default_intervals,
        dense_intervals=dense_intervals,
        coarse_intervals=coarse_intervals,
    )

    rows = [
        evaluate_case(
            case,
            target_e=target_e,
            alpha=args.alpha,
        )
        for case in cases
    ]

    max_eta_error = max(row.eta_relative_error_percent for row in rows)
    if max_eta_error > 1e-6:
        raise RuntimeError(f"eta numeric/theory mismatch too large: {max_eta_error}")

    write_csv(args.csv_output, rows)
    write_md(
        args.md_output,
        rows,
        target_pmission=args.target_pmission,
        target_e=target_e,
    )

    print(f"CSV: {args.csv_output}")
    print(f"MD: {args.md_output}")
    print(f"cases: {len(rows)}")
    print(f"max_eta_relative_error_percent: {max_eta_error:.12g}")


if __name__ == "__main__":
    main()

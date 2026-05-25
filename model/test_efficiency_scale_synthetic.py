#!/usr/bin/env python3

from __future__ import annotations

from risk_core import (
    compute_series_stats,
    current_estimate,
    fixed_continuous_at_target,
    strategy_for_estimate,
    target_risk_from_probability,
)


def check_series(name: str, values: list[float], expected_eta: float, tolerance: float = 1e-9) -> None:
    target_e = target_risk_from_probability(0.01)
    stats = compute_series_stats(values)

    _fixed_tau, fixed_risk = fixed_continuous_at_target(
        nu_values=values,
        target_e=target_e,
    )

    ideal_c, ideal_risk = strategy_for_estimate(
        nu_values=values,
        estimate_values=current_estimate(values),
        target_e=target_e,
        allowed_seconds=None,
    )

    eta_numeric = fixed_risk.cycles / ideal_risk.cycles

    print(f"{name}:")
    print(f"  expected eta = {expected_eta:.12g}")
    print(f"  stats eta    = {stats.eta_max_theory:.12g}")
    print(f"  numeric eta  = {eta_numeric:.12g}")
    print(f"  c            = {ideal_c:.12g}")

    if abs(stats.eta_max_theory - expected_eta) > tolerance:
        raise SystemExit(
            f"{name}: stats eta mismatch: "
            f"{stats.eta_max_theory} vs {expected_eta}"
        )

    if abs(eta_numeric - expected_eta) > tolerance:
        raise SystemExit(
            f"{name}: numeric eta mismatch: "
            f"{eta_numeric} vs {expected_eta}"
        )


def main() -> None:
    constant = [5.0 for _ in range(1000)]
    check_series(
        name="constant",
        values=constant,
        expected_eta=1.0,
    )

    r = 10.0
    two_level = [1.0 for _ in range(500)] + [r for _ in range(500)]
    expected_cv2 = ((r - 1.0) / (r + 1.0)) ** 2
    expected_eta = 1.0 + expected_cv2

    check_series(
        name="two_level_r10",
        values=two_level,
        expected_eta=expected_eta,
    )

    print("Synthetic efficiency scale tests passed.")


if __name__ == "__main__":
    main()

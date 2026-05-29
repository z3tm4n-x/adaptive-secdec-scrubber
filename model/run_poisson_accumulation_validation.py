#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from upsets_series import load_full_upsets_series

import risk_core as rc


REPO_ROOT = Path(__file__).resolve().parents[1]

WORD_BITS = int(getattr(rc, "WORD_BITS"))
TOTAL_BITS = int(getattr(rc, "TOTAL_BITS"))
WORD_COUNT = TOTAL_BITS // WORD_BITS


@dataclass(frozen=True)
class Policy:
    name: str
    tau_seconds_by_bin: np.ndarray
    g_d: float
    description: str


@dataclass(frozen=True)
class ValidationRow:
    policy: str
    description: str
    trials: int
    g_d: float
    analytic_e_inst: float
    analytic_e_acc: float
    analytic_e_total: float
    empirical_mean_total: float
    empirical_mean_inst: float
    empirical_mean_acc: float
    empirical_std_total: float
    ci95_low_total: float
    ci95_high_total: float
    rel_error_total_percent: float
    within_95ci: bool


def q_exact_poisson_words(lambda_value: float, word_count: int = WORD_COUNT) -> float:
    if lambda_value <= 0.0:
        return 0.0

    mu_word = lambda_value / word_count
    log_p_word_safe = -mu_word + math.log1p(mu_word)
    log_p_all_safe = word_count * log_p_word_safe

    return -math.expm1(log_p_all_safe)


def select_window(values: list[float], start_index: int, window_size: int) -> np.ndarray:
    end = start_index + window_size

    if start_index < 0 or window_size <= 0 or end > len(values):
        raise ValueError(
            f"Invalid window: start={start_index}, size={window_size}, available={len(values)}"
        )

    return np.asarray(values[start_index:end], dtype=np.float64)


def build_quantile_policy(nu_values: np.ndarray) -> np.ndarray:
    q50, q70, q90 = np.quantile(nu_values, [0.50, 0.70, 0.90])

    tau = np.full_like(nu_values, 3600.0, dtype=np.float64)
    tau[nu_values >= q50] = 1800.0
    tau[nu_values >= q70] = 600.0
    tau[nu_values >= q90] = 300.0

    return tau


def analytical_expected_counts(nu_values: np.ndarray, policy: Policy) -> tuple[float, float, float]:
    slots_by_bin = (3600.0 / policy.tau_seconds_by_bin).astype(np.int64)

    if np.any(slots_by_bin < 1):
        raise ValueError("Every bin must contain at least one scrub slot")

    # E_inst is the expected count of instant dangerous physical events.
    e_inst = float(policy.g_d * np.sum(nu_values))

    # For accumulated risk, instant-dangerous events are removed from the safe event stream.
    safe_nu_values = (1.0 - policy.g_d) * nu_values

    e_acc = 0.0

    for nu, slots in zip(safe_nu_values, slots_by_bin):
        lam_slot = float(nu / slots)
        q = q_exact_poisson_words(lam_slot)
        e_acc += int(slots) * q

    return e_inst, e_acc, e_inst + e_acc


def count_accumulated_due_for_bin(
    *,
    rng: np.random.Generator,
    safe_event_count: int,
    slots: int,
) -> int:
    if safe_event_count < 2:
        return 0

    slot_ids = rng.integers(0, slots, size=safe_event_count, dtype=np.int64)
    word_ids = rng.integers(0, WORD_COUNT, size=safe_event_count, dtype=np.int64)

    keys = slot_ids * WORD_COUNT + word_ids

    unique_keys, counts = np.unique(keys, return_counts=True)
    duplicate_keys = unique_keys[counts >= 2]

    if duplicate_keys.size == 0:
        return 0

    due_slots = np.unique(duplicate_keys // WORD_COUNT)

    return int(due_slots.size)


def run_one_trial(
    *,
    rng: np.random.Generator,
    nu_values: np.ndarray,
    policy: Policy,
) -> tuple[int, int, int]:
    slots_by_bin = (3600.0 / policy.tau_seconds_by_bin).astype(np.int64)

    event_counts = rng.poisson(nu_values)

    instant_due = 0
    accumulated_due = 0

    for k, slots in zip(event_counts, slots_by_bin):
        k_int = int(k)

        if k_int <= 0:
            continue

        if policy.g_d > 0.0:
            dangerous = rng.binomial(k_int, policy.g_d)
        else:
            dangerous = 0

        instant_due += dangerous

        safe_k = k_int - dangerous

        accumulated_due += count_accumulated_due_for_bin(
            rng=rng,
            safe_event_count=safe_k,
            slots=int(slots),
        )

    return instant_due + accumulated_due, instant_due, accumulated_due


def validate_policy(
    *,
    rng: np.random.Generator,
    nu_values: np.ndarray,
    policy: Policy,
    trials: int,
) -> ValidationRow:
    e_inst, e_acc, e_total = analytical_expected_counts(nu_values, policy)

    total_counts: list[int] = []
    inst_counts: list[int] = []
    acc_counts: list[int] = []

    for _ in range(trials):
        total, inst, acc = run_one_trial(
            rng=rng,
            nu_values=nu_values,
            policy=policy,
        )
        total_counts.append(total)
        inst_counts.append(inst)
        acc_counts.append(acc)

    total_arr = np.asarray(total_counts, dtype=np.float64)
    inst_arr = np.asarray(inst_counts, dtype=np.float64)
    acc_arr = np.asarray(acc_counts, dtype=np.float64)

    empirical_mean = float(np.mean(total_arr))
    empirical_std = float(np.std(total_arr, ddof=1)) if trials > 1 else 0.0
    se = empirical_std / math.sqrt(trials) if trials > 1 else 0.0
    ci_low = empirical_mean - 1.96 * se
    ci_high = empirical_mean + 1.96 * se

    within = ci_low <= e_total <= ci_high

    rel_error = (
        (empirical_mean - e_total) / e_total * 100.0
        if e_total > 0.0
        else 0.0
    )

    return ValidationRow(
        policy=policy.name,
        description=policy.description,
        trials=trials,
        g_d=policy.g_d,
        analytic_e_inst=e_inst,
        analytic_e_acc=e_acc,
        analytic_e_total=e_total,
        empirical_mean_total=empirical_mean,
        empirical_mean_inst=float(np.mean(inst_arr)),
        empirical_mean_acc=float(np.mean(acc_arr)),
        empirical_std_total=empirical_std,
        ci95_low_total=ci_low,
        ci95_high_total=ci_high,
        rel_error_total_percent=rel_error,
        within_95ci=within,
    )


def build_policies(nu_values: np.ndarray) -> list[Policy]:
    tau_fixed_3600 = np.full_like(nu_values, 3600.0, dtype=np.float64)
    tau_fixed_600 = np.full_like(nu_values, 600.0, dtype=np.float64)
    tau_adaptive = build_quantile_policy(nu_values)

    # g_D is deliberately small: it represents rare instant-dangerous MCU-to-MBU
    # mappings but is high enough to be visible in Monte Carlo over the selected row.
    g_positive = 1.0e-6

    return [
        Policy(
            name="fixed_3600_g0",
            tau_seconds_by_bin=tau_fixed_3600,
            g_d=0.0,
            description="Fixed one-hour scrub interval, accumulated risk only.",
        ),
        Policy(
            name="fixed_600_g0",
            tau_seconds_by_bin=tau_fixed_600,
            g_d=0.0,
            description="Fixed ten-minute scrub interval, accumulated risk only.",
        ),
        Policy(
            name="adaptive_quantile_g0",
            tau_seconds_by_bin=tau_adaptive,
            g_d=0.0,
            description="Simple quantile adaptive interval schedule, accumulated risk only.",
        ),
        Policy(
            name="adaptive_quantile_gpos",
            tau_seconds_by_bin=tau_adaptive,
            g_d=g_positive,
            description="Same adaptive schedule with a nonzero instant-MBU floor.",
        ),
    ]


def write_csv(path: Path, rows: list[ValidationRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    fields = [
        "policy",
        "description",
        "trials",
        "g_D",
        "analytic_E_inst",
        "analytic_E_acc",
        "analytic_E_total",
        "empirical_mean_total",
        "empirical_mean_inst",
        "empirical_mean_acc",
        "empirical_std_total",
        "ci95_low_total",
        "ci95_high_total",
        "rel_error_total_percent",
        "within_95ci",
    ]

    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()

        for r in rows:
            w.writerow({
                "policy": r.policy,
                "description": r.description,
                "trials": r.trials,
                "g_D": f"{r.g_d:.12g}",
                "analytic_E_inst": f"{r.analytic_e_inst:.12g}",
                "analytic_E_acc": f"{r.analytic_e_acc:.12g}",
                "analytic_E_total": f"{r.analytic_e_total:.12g}",
                "empirical_mean_total": f"{r.empirical_mean_total:.12g}",
                "empirical_mean_inst": f"{r.empirical_mean_inst:.12g}",
                "empirical_mean_acc": f"{r.empirical_mean_acc:.12g}",
                "empirical_std_total": f"{r.empirical_std_total:.12g}",
                "ci95_low_total": f"{r.ci95_low_total:.12g}",
                "ci95_high_total": f"{r.ci95_high_total:.12g}",
                "rel_error_total_percent": f"{r.rel_error_total_percent:.12g}",
                "within_95ci": "yes" if r.within_95ci else "no",
            })


def write_md(path: Path, rows: list[ValidationRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []

    lines.append("# Poisson accumulation validation")
    lines.append("")
    lines.append("## Purpose")
    lines.append("")
    lines.append(
        "This report validates the probabilistic accumulated-risk model by direct "
        "Monte Carlo simulation of Poisson physical events distributed over SECDED "
        "codewords. This is distinct from the controlled RTL workloads: controlled "
        "workloads are used for paired strategy comparison, while this Monte Carlo "
        "check tests whether empirical DUE counts agree with analytical expectations."
    )
    lines.append("")
    lines.append("## Method")
    lines.append("")
    lines.append(
        "For every hourly bin, the number of physical events is sampled from "
        "`Poisson(nu_i)`. Events are assigned uniformly to scrub slots inside the bin "
        "and uniformly to codewords. An accumulated DUE is counted when at least two "
        "safe events hit the same codeword within the same scrub slot. If `g_D > 0`, "
        "each physical event is also independently marked as instant-dangerous with "
        "probability `g_D`; those events contribute to `E_inst` and are removed from "
        "the safe accumulated-event stream."
    )
    lines.append("")
    lines.append("## Results")
    lines.append("")
    lines.append("| policy | g_D | E_inst | E_acc | E_total analytical | empirical mean | 95% CI | rel. error, % | within CI |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---|")

    for r in rows:
        lines.append(
            f"| `{r.policy}` | {r.g_d:.3g} | {r.analytic_e_inst:.6g} | "
            f"{r.analytic_e_acc:.6g} | {r.analytic_e_total:.6g} | "
            f"{r.empirical_mean_total:.6g} | "
            f"[{r.ci95_low_total:.6g}; {r.ci95_high_total:.6g}] | "
            f"{r.rel_error_total_percent:.3g} | {'yes' if r.within_95ci else 'no'} |"
        )

    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    lines.append(
        "The accumulated-only policies check the quadratic collision model under "
        "different scrub intervals and under a simple nonstationary adaptive schedule. "
        "The `g_D > 0` case shows that total mission risk contains an instant component "
        "in addition to accumulated collisions. Agreement within the Monte Carlo "
        "confidence interval is an internal consistency check, not a device-level "
        "radiation validation."
    )
    lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path, default=Path("data/upsets.xlsx"))
    p.add_argument("--start-index", type=int, default=0)
    p.add_argument("--window-size", type=int, default=43824)
    p.add_argument("--trials", type=int, default=100)
    p.add_argument("--seed", type=int, default=12345)
    p.add_argument("--csv-output", type=Path, default=Path("results/paper/theory_consistency/poisson_accumulation_validation.csv"))
    p.add_argument("--md-output", type=Path, default=Path("results/paper/theory_consistency/poisson_accumulation_validation.md"))
    return p.parse_args()


def main() -> None:
    args = parse_args()

    if args.trials < 10:
        raise ValueError("Use at least 10 trials for a meaningful confidence interval")

    full_values = load_full_upsets_series(args.input)
    nu_values = np.asarray(full_values[args.start_index:args.start_index + args.window_size], dtype=np.float64)

    if len(nu_values) != args.window_size:
        raise ValueError("Requested window exceeds available input data")

    rng = np.random.default_rng(args.seed)

    policies = build_policies(nu_values)

    rows = [
        validate_policy(
            rng=rng,
            nu_values=nu_values,
            policy=policy,
            trials=args.trials,
        )
        for policy in policies
    ]

    write_csv(REPO_ROOT / args.csv_output, rows)
    write_md(REPO_ROOT / args.md_output, rows)

    failures = [r for r in rows if not r.within_95ci]

    print(f"CSV: {args.csv_output}")
    print(f"MD: {args.md_output}")
    print(f"policies: {len(rows)}")
    print(f"trials: {args.trials}")
    print(f"within_95ci: {len(rows) - len(failures)}/{len(rows)}")

    for r in rows:
        print(
            f"{r.policy}: analytical={r.analytic_e_total:.6g} "
            f"empirical={r.empirical_mean_total:.6g} "
            f"ci=[{r.ci95_low_total:.6g},{r.ci95_high_total:.6g}] "
            f"within={'yes' if r.within_95ci else 'no'}"
        )

    if failures:
        raise SystemExit(
            "Some policies are outside the 95% Monte Carlo interval. "
            "Increase --trials or inspect the modeling assumptions."
        )


if __name__ == "__main__":
    main()

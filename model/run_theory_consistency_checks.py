#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import math
from dataclasses import dataclass
from pathlib import Path
from statistics import mean

from upsets_series import load_full_upsets_series

import risk_core as rc


REPO_ROOT = Path(__file__).resolve().parents[1]

WORD_BITS = int(getattr(rc, "WORD_BITS"))
TOTAL_BITS = int(getattr(rc, "TOTAL_BITS"))
WORD_COUNT = TOTAL_BITS // WORD_BITS
ALPHA_BIT_LEVEL = float(getattr(rc, "DEFAULT_ALPHA"))
DT_HOURS = float(getattr(rc, "DT_HOURS", 1.0))


@dataclass(frozen=True)
class ExactRow:
    lambda_value: float
    q_exact_words: float
    q_quad_words: float
    q_quad_bit_level: float
    rel_error_words_percent: float
    rel_error_bit_level_percent: float


@dataclass(frozen=True)
class SlopeRow:
    case: str
    g_d: float
    a_d: float
    lambda_min: float
    lambda_max: float
    fitted_slope: float
    expected_slope: float
    max_abs_log_residual: float


@dataclass(frozen=True)
class FloorRow:
    case: str
    tau_seconds: float
    e_inst: float
    e_acc: float
    e_total: float
    e_acc_fraction_of_total: float


def q_exact_poisson_words(lambda_value: float, word_count: int = WORD_COUNT) -> float:
    """
    Exact no-DUE probability for a Poisson number of independent bit upsets
    distributed uniformly over codewords, using word-level Poisson splitting.

    Each word receives Pois(lambda/W) hits. A word is safe if it receives 0 or 1 hit.
    The whole memory is safe if every word is safe.
    """
    if lambda_value < 0.0:
        raise ValueError("lambda must be non-negative")
    if lambda_value == 0.0:
        return 0.0

    mu_word = lambda_value / word_count
    log_p_word_safe = -mu_word + math.log1p(mu_word)
    log_p_all_safe = word_count * log_p_word_safe

    # q = 1 - exp(log_p_all_safe), computed accurately for tiny q.
    return -math.expm1(log_p_all_safe)


def q_quad_words(lambda_value: float, word_count: int = WORD_COUNT) -> float:
    return lambda_value * lambda_value / (2.0 * word_count)


def q_quad_bit_level(lambda_value: float) -> float:
    return ALPHA_BIT_LEVEL * lambda_value * lambda_value


def q_cycle_mbu_asymptotic(lambda_value: float, *, g_d: float, a_d: float) -> float:
    exponent = -lambda_value * g_d - lambda_value * lambda_value * a_d * a_d / (2.0 * WORD_COUNT)
    return -math.expm1(exponent)


def log_log_slope(xs: list[float], ys: list[float]) -> tuple[float, float]:
    lx = [math.log(x) for x in xs]
    ly = [math.log(y) for y in ys]

    mx = mean(lx)
    my = mean(ly)

    var_x = sum((x - mx) ** 2 for x in lx)
    cov_xy = sum((x - mx) * (y - my) for x, y in zip(lx, ly))

    slope = cov_xy / var_x
    intercept = my - slope * mx

    residuals = [
        abs(y - (intercept + slope * x))
        for x, y in zip(lx, ly)
    ]

    return slope, max(residuals)


def build_exact_rows() -> list[ExactRow]:
    lambdas = [
        1e-4, 3e-4,
        1e-3, 3e-3,
        1e-2, 3e-2,
        1e-1, 3e-1,
        1.0, 3.0, 10.0,
    ]

    rows: list[ExactRow] = []

    for lam in lambdas:
        q_exact = q_exact_poisson_words(lam)
        q_w = q_quad_words(lam)
        q_b = q_quad_bit_level(lam)

        rows.append(
            ExactRow(
                lambda_value=lam,
                q_exact_words=q_exact,
                q_quad_words=q_w,
                q_quad_bit_level=q_b,
                rel_error_words_percent=(q_w - q_exact) / q_exact * 100.0 if q_exact > 0 else 0.0,
                rel_error_bit_level_percent=(q_b - q_exact) / q_exact * 100.0 if q_exact > 0 else 0.0,
            )
        )

    return rows


def build_slope_rows() -> list[SlopeRow]:
    # Small-lambda range: enough above floating underflow and still in asymptotic region.
    lambdas = [10.0 ** x for x in [-3.0, -2.75, -2.5, -2.25, -2.0, -1.75, -1.5]]

    cases = [
        ("accumulation_only_g0", 0.0, 1.0, 2.0),
        ("instant_mbu_g_positive", 5.0e-4, 1.0, 1.0),
    ]

    rows: list[SlopeRow] = []

    for name, g_d, a_d, expected in cases:
        ys = [
            q_cycle_mbu_asymptotic(lam, g_d=g_d, a_d=a_d)
            for lam in lambdas
        ]

        slope, max_residual = log_log_slope(lambdas, ys)

        rows.append(
            SlopeRow(
                case=name,
                g_d=g_d,
                a_d=a_d,
                lambda_min=min(lambdas),
                lambda_max=max(lambdas),
                fitted_slope=slope,
                expected_slope=expected,
                max_abs_log_residual=max_residual,
            )
        )

    return rows


def select_window(values: list[float], start_index: int, window_size: int) -> list[float]:
    end = start_index + window_size
    if start_index < 0 or window_size <= 0 or end > len(values):
        raise ValueError(
            f"Invalid window: start={start_index}, size={window_size}, available={len(values)}"
        )
    return values[start_index:end]


def build_floor_rows(nu_values: list[float]) -> list[FloorRow]:
    """
    Mission-risk decomposition:
        E_inst = g_D * N_events
        E_acc  = (a_D^2 / 2W) * sum Lambda(t)^2 * tau(t) * dt

    Here nu(t) is treated as the physical event rate for the synthetic consistency check
    by using mu=1, i.e. Lambda(t)=nu(t). This is the conservative convention used in v6
    when translating a bit-inversion row into an event count.
    """
    tau_seconds_values = [3600.0, 1800.0, 600.0, 300.0, 60.0, 10.0, 1.0, 0.1, 0.01]

    n_total = sum(nu * DT_HOURS for nu in nu_values)

    cases = [
        ("accumulation_only_g0", 0.0, 1.0),
        ("instant_mbu_g_positive", 1.0e-7, 1.0),
    ]

    rows: list[FloorRow] = []

    for case, g_d, a_d in cases:
        e_inst = g_d * n_total

        for tau_seconds in tau_seconds_values:
            tau_hours = tau_seconds / 3600.0

            e_acc = (
                a_d * a_d / (2.0 * WORD_COUNT)
                * sum(nu * nu * tau_hours * DT_HOURS for nu in nu_values)
            )

            e_total = e_inst + e_acc

            rows.append(
                FloorRow(
                    case=case,
                    tau_seconds=tau_seconds,
                    e_inst=e_inst,
                    e_acc=e_acc,
                    e_total=e_total,
                    e_acc_fraction_of_total=e_acc / e_total if e_total > 0.0 else 0.0,
                )
            )

    return rows


def write_csv(path: Path, exact_rows: list[ExactRow], slope_rows: list[SlopeRow], floor_rows: list[FloorRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    fields = [
        "section",
        "case",
        "lambda",
        "q_exact_words",
        "q_quad_words",
        "q_quad_bit_level",
        "rel_error_words_percent",
        "rel_error_bit_level_percent",
        "g_D",
        "a_D",
        "lambda_min",
        "lambda_max",
        "fitted_slope",
        "expected_slope",
        "max_abs_log_residual",
        "tau_seconds",
        "E_inst",
        "E_acc",
        "E_total",
        "E_acc_fraction_of_total",
    ]

    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()

        for r in exact_rows:
            w.writerow({
                "section": "exact_vs_quadratic",
                "case": "word_poisson_vs_quadratic",
                "lambda": f"{r.lambda_value:.12g}",
                "q_exact_words": f"{r.q_exact_words:.12g}",
                "q_quad_words": f"{r.q_quad_words:.12g}",
                "q_quad_bit_level": f"{r.q_quad_bit_level:.12g}",
                "rel_error_words_percent": f"{r.rel_error_words_percent:.12g}",
                "rel_error_bit_level_percent": f"{r.rel_error_bit_level_percent:.12g}",
            })

        for r in slope_rows:
            w.writerow({
                "section": "slope_check",
                "case": r.case,
                "g_D": f"{r.g_d:.12g}",
                "a_D": f"{r.a_d:.12g}",
                "lambda_min": f"{r.lambda_min:.12g}",
                "lambda_max": f"{r.lambda_max:.12g}",
                "fitted_slope": f"{r.fitted_slope:.12g}",
                "expected_slope": f"{r.expected_slope:.12g}",
                "max_abs_log_residual": f"{r.max_abs_log_residual:.12g}",
            })

        for r in floor_rows:
            w.writerow({
                "section": "mission_floor",
                "case": r.case,
                "tau_seconds": f"{r.tau_seconds:.12g}",
                "E_inst": f"{r.e_inst:.12g}",
                "E_acc": f"{r.e_acc:.12g}",
                "E_total": f"{r.e_total:.12g}",
                "E_acc_fraction_of_total": f"{r.e_acc_fraction_of_total:.12g}",
            })


def write_md(path: Path, exact_rows: list[ExactRow], slope_rows: list[SlopeRow], floor_rows: list[FloorRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    max_small_lambda_error = max(
        abs(r.rel_error_words_percent)
        for r in exact_rows
        if r.lambda_value <= 0.1
    )

    bit_to_word_ratio = ALPHA_BIT_LEVEL / (1.0 / (2.0 * WORD_COUNT))

    floor_positive = [r for r in floor_rows if r.case == "instant_mbu_g_positive"]
    floor_low_tau = min(floor_positive, key=lambda r: r.tau_seconds)

    lines: list[str] = []

    lines.append("# Theory consistency checks")
    lines.append("")
    lines.append("## Purpose")
    lines.append("")
    lines.append(
        "This report checks that the repository implements the same risk structure "
        "as the dissertation theory and the MBU model: quadratic accumulated risk "
        "when `g_D = 0`, linear local behavior when `g_D > 0`, and a mission-level "
        "instant-risk floor `E_inst = g_D * N_total` that cannot be removed by reducing "
        "the scrub interval."
    )
    lines.append("")
    lines.append("## Constants")
    lines.append("")
    lines.append(f"- `WORD_BITS`: {WORD_BITS}")
    lines.append(f"- `WORD_COUNT`: {WORD_COUNT}")
    lines.append(f"- `TOTAL_BITS`: {TOTAL_BITS}")
    lines.append(f"- `risk_core` bit-level alpha: {ALPHA_BIT_LEVEL:.12g}")
    lines.append(f"- word-level `1/(2W)`: {1.0 / (2.0 * WORD_COUNT):.12g}")
    lines.append(f"- alpha ratio, bit-level / word-level: {bit_to_word_ratio:.12g}")
    lines.append("")

    lines.append("## Exact vs quadratic accumulated-risk approximation")
    lines.append("")
    lines.append("| lambda | q exact, word Poisson | q quad, word | rel. error word, % | q quad, risk_core alpha | rel. error bit-level, % |")
    lines.append("|---:|---:|---:|---:|---:|---:|")

    for r in exact_rows:
        lines.append(
            f"| {r.lambda_value:.3g} | {r.q_exact_words:.6g} | {r.q_quad_words:.6g} | "
            f"{r.rel_error_words_percent:.6g} | {r.q_quad_bit_level:.6g} | "
            f"{r.rel_error_bit_level_percent:.6g} |"
        )

    lines.append("")
    lines.append(
        f"For lambda <= 0.1, the maximum absolute relative error of the word-level "
        f"quadratic approximation is {max_small_lambda_error:.6g} %. "
        "The `risk_core` alpha is the bit-placement coefficient used in the original "
        "scrubbing model; its difference from the word-level coefficient is the expected "
        "`WORD_BITS/(WORD_BITS-1)` bit-vs-word placement correction."
    )
    lines.append("")

    lines.append("## Local asymptotic slope check")
    lines.append("")
    lines.append("| case | g_D | a_D | fitted slope | expected slope | lambda range | max log residual |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")

    for r in slope_rows:
        lines.append(
            f"| `{r.case}` | {r.g_d:.3g} | {r.a_d:.3g} | {r.fitted_slope:.6g} | "
            f"{r.expected_slope:.6g} | {r.lambda_min:.3g}--{r.lambda_max:.3g} | "
            f"{r.max_abs_log_residual:.3g} |"
        )

    lines.append("")
    lines.append(
        "The `g_D = 0` case has the expected quadratic local behavior. "
        "When `g_D > 0`, the local cycle probability is dominated by the linear "
        "instant-MBU term."
    )
    lines.append("")

    lines.append("## Mission-level instant-risk floor")
    lines.append("")
    lines.append("| case | tau, s | E_inst | E_acc | E_total | E_acc / E_total |")
    lines.append("|---|---:|---:|---:|---:|---:|")

    for r in floor_rows:
        lines.append(
            f"| `{r.case}` | {r.tau_seconds:.6g} | {r.e_inst:.6g} | "
            f"{r.e_acc:.6g} | {r.e_total:.6g} | {r.e_acc_fraction_of_total:.6g} |"
        )

    lines.append("")
    lines.append(
        "For `g_D = 0`, the mission risk decreases with the scrub interval because only "
        "the accumulated component remains. For `g_D > 0`, reducing the interval "
        "reduces `E_acc`, but `E_total` tends to the nonzero floor `E_inst`. "
        f"At the smallest tested interval ({floor_low_tau.tau_seconds:g} s), "
        f"`E_total = {floor_low_tau.e_total:.6g}` and "
        f"`E_inst = {floor_low_tau.e_inst:.6g}`."
    )
    lines.append("")

    lines.append("## Interpretation")
    lines.append("")
    lines.append(
        "These checks do not replace device-specific radiation validation. Their role is "
        "internal consistency: the software model used for policy construction follows "
        "the same accumulated/instant risk decomposition as the analytical theory."
    )
    lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path, default=Path("data/upsets.xlsx"))
    p.add_argument("--start-index", type=int, default=0)
    p.add_argument("--window-size", type=int, default=43824)
    p.add_argument("--csv-output", type=Path, default=Path("results/paper/theory_consistency/theory_consistency.csv"))
    p.add_argument("--md-output", type=Path, default=Path("results/paper/theory_consistency/theory_consistency_summary.md"))
    return p.parse_args()


def main() -> None:
    args = parse_args()

    full_values = load_full_upsets_series(args.input)
    nu_values = select_window(full_values, args.start_index, args.window_size)

    exact_rows = build_exact_rows()
    slope_rows = build_slope_rows()
    floor_rows = build_floor_rows(nu_values)

    # Hard sanity checks: these are deliberately loose enough to avoid numerical fragility
    # but strict enough to catch a broken formula.
    slope_by_case = {r.case: r.fitted_slope for r in slope_rows}

    if abs(slope_by_case["accumulation_only_g0"] - 2.0) > 0.02:
        raise RuntimeError("Accumulation-only slope is not close to 2")

    if abs(slope_by_case["instant_mbu_g_positive"] - 1.0) > 0.02:
        raise RuntimeError("Instant-MBU slope is not close to 1")

    floor_positive = sorted(
        [r for r in floor_rows if r.case == "instant_mbu_g_positive"],
        key=lambda r: r.tau_seconds,
        reverse=True,
    )
    floor_low_tau = min(floor_positive, key=lambda r: r.tau_seconds)

    # The floor check is asymptotic: E_inst is constant, E_acc must decrease
    # approximately linearly with tau, and E_total must approach E_inst for the
    # smallest synthetic interval. It is not required that a flight-realistic
    # one-second interval is already floor-dominated.
    e_inst_values = [r.e_inst for r in floor_positive]
    if max(e_inst_values) - min(e_inst_values) > 1e-18:
        raise RuntimeError("E_inst is not constant across scrub intervals")

    for prev, cur in zip(floor_positive, floor_positive[1:]):
        if cur.e_acc > prev.e_acc:
            raise RuntimeError("E_acc does not decrease when tau decreases")

    if abs(floor_low_tau.e_total - floor_low_tau.e_inst) / floor_low_tau.e_inst > 0.05:
        raise RuntimeError("Mission floor is not approached at the smallest synthetic interval")

    write_csv(REPO_ROOT / args.csv_output, exact_rows, slope_rows, floor_rows)
    write_md(REPO_ROOT / args.md_output, exact_rows, slope_rows, floor_rows)

    print(f"CSV: {args.csv_output}")
    print(f"MD: {args.md_output}")
    print(f"exact_rows: {len(exact_rows)}")
    print(f"slope_rows: {len(slope_rows)}")
    print(f"floor_rows: {len(floor_rows)}")
    print(f"accumulation_slope: {slope_by_case['accumulation_only_g0']:.12g}")
    print(f"instant_mbu_slope: {slope_by_case['instant_mbu_g_positive']:.12g}")
    print(f"floor_low_tau_E_total: {floor_low_tau.e_total:.12g}")
    print(f"floor_low_tau_E_inst: {floor_low_tau.e_inst:.12g}")


if __name__ == "__main__":
    main()

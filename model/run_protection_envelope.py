#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import math
from dataclasses import dataclass
from pathlib import Path

from risk_core import (
    DEFAULT_TARGET_PMISSION,
    mission_probability_from_risk,
    risk_stats_for_tau_hours,
    target_risk_from_probability,
)
from upsets_series import load_full_upsets_series


REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class EnvelopeScenario:
    name: str
    description: str
    event_count: float
    pm: dict[int, float]
    nu_scale: float


@dataclass(frozen=True)
class EnvelopeRow:
    scenario: str
    description: str
    interleave_depth: int
    event_count: float
    nu_scale: float
    p2: float
    p3: float
    p4: float
    p5: float
    g_d: float
    target_e: float
    e_inst: float
    rho_d: float
    e_residual: float
    e_acc_min: float
    tau_min_seconds: float
    e_acc_min_over_residual: float
    status: str
    recommendation: str


def secded_danger_probability_for_m(m: int, interleave_depth: int) -> float:
    if m <= 1:
        return 0.0
    if interleave_depth <= 0:
        raise ValueError("interleave_depth must be positive")

    return 1.0 if math.ceil(m / interleave_depth) >= 2 else 0.0


def compute_gd(pm: dict[int, float], interleave_depth: int) -> float:
    return sum(
        float(p_m) * secded_danger_probability_for_m(m, interleave_depth)
        for m, p_m in pm.items()
    )


def default_scenarios() -> list[EnvelopeScenario]:
    return [
        EnvelopeScenario(
            name="light_3bit_tail",
            description=(
                "3-bit clusters consume part of the budget at D=1/2 but become "
                "instant-safe in the logical round-robin model at D>=3."
            ),
            event_count=1_000_000.0,
            pm={2: 0.0, 3: 5.0e-9, 4: 0.0, 5: 0.0},
            nu_scale=1.0,
        ),
        EnvelopeScenario(
            name="overbudget_3bit_tail",
            description=(
                "A heavier 3-bit tail violates the instant component at D=1/2; "
                "D>=3 removes this instant SECDED-dangerous mapping."
            ),
            event_count=1_000_000.0,
            pm={2: 0.0, 3: 2.0e-8, 4: 0.0, 5: 0.0},
            nu_scale=1.0,
        ),
        EnvelopeScenario(
            name="bandwidth_limited_accumulation",
            description=(
                "The instant component is absent, but the accumulated-risk floor "
                "under tau_min is moderately stressed to demonstrate the "
                "bandwidth/tau_min insufficiency region."
            ),
            event_count=1_000_000.0,
            pm={2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0},
            nu_scale=4.0,
        ),
        EnvelopeScenario(
            name="four_bit_tail_requires_D4",
            description=(
                "4-bit clusters remain instant-dangerous at D=3 and require D>=4 "
                "or a stronger code/placement rule in the simplified model."
            ),
            event_count=1_000_000.0,
            pm={2: 0.0, 3: 0.0, 4: 2.0e-8, 5: 0.0},
            nu_scale=1.0,
        ),
    ]


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


def accumulated_min_risk(nu_values: list[float], tau_min_seconds: float) -> float:
    tau_hours = [tau_min_seconds / 3600.0 for _ in nu_values]
    return risk_stats_for_tau_hours(nu_values, tau_hours).risk_e


def classify(
    *,
    rho_d: float,
    e_residual: float,
    e_acc_min: float,
) -> tuple[str, str]:
    if rho_d >= 1.0 or e_residual <= 0.0:
        return (
            "architecture_change_required",
            "reduce g_D by increasing interleaving, changing placement, using stronger ECC, or changing memory organization",
        )

    if e_acc_min > e_residual:
        return (
            "bandwidth_or_tau_min_insufficient",
            "instant component is acceptable, but tau_min/bandwidth cannot meet the residual accumulated-risk budget",
        )

    return (
        "scrub_period_selectable",
        "criterion passes and the residual accumulated-risk budget is reachable; proceed to scrub-period selection",
    )


def evaluate(
    *,
    scenarios: list[EnvelopeScenario],
    depths: list[int],
    nu_values: list[float],
    target_e: float,
    tau_min_seconds: float,
) -> list[EnvelopeRow]:
    rows: list[EnvelopeRow] = []

    for scenario in scenarios:
        scaled_nu = [v * scenario.nu_scale for v in nu_values]
        e_acc_min = accumulated_min_risk(scaled_nu, tau_min_seconds)

        for depth in depths:
            g_d = compute_gd(scenario.pm, depth)
            e_inst = scenario.event_count * g_d
            rho_d = e_inst / target_e if target_e > 0.0 else float("inf")
            e_residual = target_e - e_inst

            if e_residual > 0.0:
                e_acc_min_over_residual = e_acc_min / e_residual
            else:
                e_acc_min_over_residual = float("inf")

            status, recommendation = classify(
                rho_d=rho_d,
                e_residual=e_residual,
                e_acc_min=e_acc_min,
            )

            rows.append(
                EnvelopeRow(
                    scenario=scenario.name,
                    description=scenario.description,
                    interleave_depth=depth,
                    event_count=scenario.event_count,
                    nu_scale=scenario.nu_scale,
                    p2=scenario.pm.get(2, 0.0),
                    p3=scenario.pm.get(3, 0.0),
                    p4=scenario.pm.get(4, 0.0),
                    p5=scenario.pm.get(5, 0.0),
                    g_d=g_d,
                    target_e=target_e,
                    e_inst=e_inst,
                    rho_d=rho_d,
                    e_residual=e_residual,
                    e_acc_min=e_acc_min,
                    tau_min_seconds=tau_min_seconds,
                    e_acc_min_over_residual=e_acc_min_over_residual,
                    status=status,
                    recommendation=recommendation,
                )
            )

    return rows


def write_csv(path: Path, rows: list[EnvelopeRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    fields = [
        "scenario",
        "description",
        "D",
        "event_count",
        "nu_scale",
        "p2",
        "p3",
        "p4",
        "p5",
        "g_D",
        "E_star",
        "E_inst",
        "rho_D",
        "E_residual",
        "E_acc_min",
        "tau_min_seconds",
        "E_acc_min_over_residual",
        "status",
        "recommendation",
    ]

    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()

        for r in rows:
            w.writerow(
                {
                    "scenario": r.scenario,
                    "description": r.description,
                    "D": r.interleave_depth,
                    "event_count": f"{r.event_count:.12g}",
                    "nu_scale": f"{r.nu_scale:.12g}",
                    "p2": f"{r.p2:.12g}",
                    "p3": f"{r.p3:.12g}",
                    "p4": f"{r.p4:.12g}",
                    "p5": f"{r.p5:.12g}",
                    "g_D": f"{r.g_d:.12g}",
                    "E_star": f"{r.target_e:.12g}",
                    "E_inst": f"{r.e_inst:.12g}",
                    "rho_D": f"{r.rho_d:.12g}",
                    "E_residual": f"{r.e_residual:.12g}",
                    "E_acc_min": f"{r.e_acc_min:.12g}",
                    "tau_min_seconds": f"{r.tau_min_seconds:.12g}",
                    "E_acc_min_over_residual": f"{r.e_acc_min_over_residual:.12g}",
                    "status": r.status,
                    "recommendation": r.recommendation,
                }
            )


def finite_fmt(value: float, digits: int = 6) -> str:
    if math.isinf(value):
        return "inf"
    if math.isnan(value):
        return "nan"
    return f"{value:.{digits}g}"


def write_markdown(
    path: Path,
    *,
    rows: list[EnvelopeRow],
    input_path: Path,
    start_index: int,
    window_size: int,
    target_pmission: float,
    target_e: float,
    tau_min_seconds: float,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    status_order = {
        "architecture_change_required": 0,
        "bandwidth_or_tau_min_insufficient": 1,
        "scrub_period_selectable": 2,
    }

    ordered = sorted(
        rows,
        key=lambda r: (r.scenario, r.interleave_depth),
    )

    lines: list[str] = []
    lines.append("# Protection envelope for SECDED scrubbing")
    lines.append("")
    lines.append("## Purpose")
    lines.append("")
    lines.append(
        "This report turns the instant/accumulated decomposition into an engineering "
        "applicability map. It classifies each scenario into one of three regions: "
        "architecture change required, bandwidth/tau_min insufficient, or scrub-period selectable."
    )
    lines.append("")
    lines.append("The classification uses:")
    lines.append("")
    lines.append("- `E_inst = g_D * N_events`")
    lines.append("- `rho_D = E_inst / E*`")
    lines.append("- `E_residual = E* - E_inst`")
    lines.append("- `E_acc_min`: accumulated-risk floor when all bins use `tau_min`")
    lines.append("")
    lines.append("## Inputs")
    lines.append("")
    lines.append(f"- Upset-rate input: `{input_path}`")
    lines.append(f"- Start index: {start_index}")
    lines.append(f"- Window size: {window_size}")
    lines.append(f"- Target mission probability: {target_pmission:.12g}")
    lines.append(f"- Target risk measure E*: {target_e:.12g}")
    lines.append(f"- tau_min: {tau_min_seconds:.12g} s")
    lines.append("")
    lines.append("## Region definitions")
    lines.append("")
    lines.append("| region | condition | interpretation |")
    lines.append("|---|---|---|")
    lines.append("| A | `rho_D >= 1` | instant dangerous mapping alone exceeds the mission budget; period selection cannot solve the problem |")
    lines.append("| B | `rho_D < 1` and `E_acc_min > E_residual` | instant term is acceptable, but the minimum scrub interval is still insufficient |")
    lines.append("| C | `rho_D < 1` and `E_acc_min <= E_residual` | SECDED scrubbing is applicable; proceed to residual-budget period selection |")
    lines.append("")
    lines.append("## Scenario table")
    lines.append("")
    lines.append("| scenario | D | nu_scale | p2 | p3 | p4 | g_D | rho_D | E_residual | E_acc_min | E_acc_min/E_residual | status |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|")

    for r in ordered:
        lines.append(
            f"| `{r.scenario}` | {r.interleave_depth} | {r.nu_scale:.3g} | "
            f"{r.p2:.3g} | {r.p3:.3g} | {r.p4:.3g} | "
            f"{r.g_d:.3g} | {r.rho_d:.3g} | "
            f"{finite_fmt(r.e_residual, 6)} | {finite_fmt(r.e_acc_min, 6)} | "
            f"{finite_fmt(r.e_acc_min_over_residual, 6)} | `{r.status}` |"
        )

    lines.append("")
    lines.append("## Compact status map")
    lines.append("")
    lines.append("| scenario | D=1 | D=2 | D=3 | D=4 |")
    lines.append("|---|---|---|---|---|")

    scenarios = sorted({r.scenario for r in rows})
    by_key = {(r.scenario, r.interleave_depth): r for r in rows}

    for scenario in scenarios:
        status_cells = []
        for depth in [1, 2, 3, 4]:
            row = by_key[(scenario, depth)]
            status_cells.append(f"`{row.status}`")
        lines.append(f"| `{scenario}` | " + " | ".join(status_cells) + " |")

    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    lines.append(
        "`E_acc_min` depends on the accumulated-error-rate series used by the scenario. "
        "The `nu_scale` column explicitly shows when a scenario scales `ν(t)` to exercise "
        "the bandwidth/tau_min insufficiency region; therefore rows with `g_D = 0` may "
        "still have different accumulated-risk floors."
    )
    lines.append("")

    lines.append(
        "The envelope separates two failure modes that are easy to conflate. "
        "If `rho_D >= 1`, no scrub period can satisfy the target because the "
        "instant dangerous component already consumes the whole risk measure. "
        "If `rho_D < 1` but `E_acc_min > E_residual`, the issue is not the "
        "instant MCU mapping but the practical lower bound on the scrub interval."
    )
    lines.append("")
    lines.append(
        "The scenario values are illustrative design points, not measured device "
        "multiplicity distributions. Their role is to exercise the three regions "
        "of the design procedure and to support the Chapter 2 feasibility argument."
    )
    lines.append("")

    counts = {}
    for r in rows:
        counts[r.status] = counts.get(r.status, 0) + 1

    lines.append("## Status counts")
    lines.append("")
    lines.append("| status | rows |")
    lines.append("|---|---:|")
    for status in sorted(counts, key=lambda s: status_order.get(s, 99)):
        lines.append(f"| `{status}` | {counts[status]} |")

    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path, default=Path("data/upsets.xlsx"))
    p.add_argument("--start-index", type=int, default=0)
    p.add_argument("--window-size", type=int, default=43824)
    p.add_argument("--target-pmission", type=float, default=DEFAULT_TARGET_PMISSION)
    p.add_argument("--tau-min-seconds", type=float, default=1.0)
    p.add_argument("--output-dir", type=Path, default=Path("results/paper/protection_envelope"))
    return p.parse_args()


def main() -> None:
    args = parse_args()

    input_path = REPO_ROOT / args.input
    output_dir = REPO_ROOT / args.output_dir

    nu_full = load_full_upsets_series(input_path)
    nu_window = select_window(nu_full, args.start_index, args.window_size)

    target_e = target_risk_from_probability(args.target_pmission)

    rows = evaluate(
        scenarios=default_scenarios(),
        depths=[1, 2, 3, 4],
        nu_values=nu_window,
        target_e=target_e,
        tau_min_seconds=args.tau_min_seconds,
    )

    csv_path = output_dir / "protection_envelope.csv"
    md_path = output_dir / "protection_envelope_summary.md"

    write_csv(csv_path, rows)
    write_markdown(
        md_path,
        rows=rows,
        input_path=args.input,
        start_index=args.start_index,
        window_size=args.window_size,
        target_pmission=args.target_pmission,
        target_e=target_e,
        tau_min_seconds=args.tau_min_seconds,
    )

    statuses = sorted({r.status for r in rows})
    print(f"CSV: {csv_path}")
    print(f"MD: {md_path}")
    print(f"rows: {len(rows)}")
    print(f"statuses: {', '.join(statuses)}")
    print(f"target_E: {target_e:.12g}")
    print(f"P(E_acc_min baseline): {mission_probability_from_risk(accumulated_min_risk(nu_window, args.tau_min_seconds)):.12g}")


if __name__ == "__main__":
    main()

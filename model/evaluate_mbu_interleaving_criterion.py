#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import math
from dataclasses import dataclass
from pathlib import Path

from risk_core import DEFAULT_TARGET_PMISSION, target_risk_from_probability


@dataclass(frozen=True)
class Scenario:
    name: str
    description: str
    event_count: float
    pm: dict[int, float]


@dataclass(frozen=True)
class ResultRow:
    scenario: str
    description: str
    event_count: float
    interleave_depth: int
    g_d: float
    g_d_limit: float
    e_inst: float
    e_residual: float
    pass_criterion: bool
    required_action: str
    p2: float
    p3: float
    p4: float


def secded_danger_probability_for_m(m: int, interleave_depth: int) -> float:
    if m <= 1:
        return 0.0

    if interleave_depth <= 0:
        raise ValueError("interleave_depth must be positive")

    max_bits_per_word = math.ceil(m / interleave_depth)

    return 1.0 if max_bits_per_word >= 2 else 0.0


def compute_gd(pm: dict[int, float], interleave_depth: int) -> float:
    total = 0.0

    for m, probability in pm.items():
        h = secded_danger_probability_for_m(
            m=m,
            interleave_depth=interleave_depth,
        )
        total += probability * h

    return total


def default_scenarios() -> list[Scenario]:
    return [
        Scenario(
            name="subbudget_3bit_clusters",
            description="3-bit clusters are present but their instant contribution remains below the mission risk budget.",
            event_count=1_000_000.0,
            pm={2: 0.0, 3: 5.0e-9, 4: 0.0},
        ),
        Scenario(
            name="rare_3bit_clusters",
            description="Rare but over-budget 3-bit clusters; D=3 is sufficient in the idealized mapping.",
            event_count=1_000_000.0,
            pm={2: 0.0, 3: 2.0e-8, 4: 0.0},
        ),
        Scenario(
            name="strong_3bit_clusters",
            description="More frequent 3-bit clusters; D=1/2 violates the budget, D=3 removes the instant SECDED-DUE part.",
            event_count=1_000_000.0,
            pm={2: 0.0, 3: 2.0e-7, 4: 0.0},
        ),
        Scenario(
            name="mixed_2bit_3bit",
            description="Mixture of 2-bit and 3-bit clusters; D=3 removes the 3-bit part but 2-bit same-event hits still require D>=2.",
            event_count=1_000_000.0,
            pm={2: 5.0e-8, 3: 1.0e-7, 4: 0.0},
        ),
        Scenario(
            name="four_bit_clusters",
            description="4-bit clusters remain dangerous at D=3; D=4 or a stronger code/placement rule is required.",
            event_count=1_000_000.0,
            pm={2: 0.0, 3: 0.0, 4: 2.0e-7},
        ),
        Scenario(
            name="high_event_count_low_probability",
            description="Low per-event danger can still violate the mission budget when the event count is high.",
            event_count=100_000_000.0,
            pm={2: 0.0, 3: 2.0e-10, 4: 0.0},
        ),
    ]


def action_for(row_passes: bool, interleave_depth: int, g_d: float) -> str:
    if row_passes:
        if g_d == 0.0:
            return "scrubbing may optimize only accumulated risk"
        return "scrubbing may use residual accumulated-risk budget"

    if interleave_depth < 4:
        return "increase interleaving or reduce instant MBU mapping probability"

    return "use stronger ECC / architecture; period alone is insufficient"


def evaluate(
    scenarios: list[Scenario],
    interleave_depths: list[int],
    target_e: float,
) -> list[ResultRow]:
    rows: list[ResultRow] = []

    for scenario in scenarios:
        g_d_limit = target_e / scenario.event_count

        for depth in interleave_depths:
            g_d = compute_gd(scenario.pm, depth)
            e_inst = scenario.event_count * g_d
            e_residual = target_e - e_inst
            pass_criterion = e_inst <= target_e

            rows.append(
                ResultRow(
                    scenario=scenario.name,
                    description=scenario.description,
                    event_count=scenario.event_count,
                    interleave_depth=depth,
                    g_d=g_d,
                    g_d_limit=g_d_limit,
                    e_inst=e_inst,
                    e_residual=e_residual,
                    pass_criterion=pass_criterion,
                    required_action=action_for(pass_criterion, depth, g_d),
                    p2=scenario.pm.get(2, 0.0),
                    p3=scenario.pm.get(3, 0.0),
                    p4=scenario.pm.get(4, 0.0),
                )
            )

    return rows


def write_csv(path: Path, rows: list[ResultRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    fields = [
        "scenario",
        "description",
        "event_count",
        "interleave_depth",
        "p2",
        "p3",
        "p4",
        "g_D",
        "g_D_limit",
        "E_inst",
        "E_residual",
        "pass_criterion",
        "required_action",
    ]

    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()

        for r in rows:
            w.writerow({
                "scenario": r.scenario,
                "description": r.description,
                "event_count": f"{r.event_count:.12g}",
                "interleave_depth": r.interleave_depth,
                "p2": f"{r.p2:.12g}",
                "p3": f"{r.p3:.12g}",
                "p4": f"{r.p4:.12g}",
                "g_D": f"{r.g_d:.12g}",
                "g_D_limit": f"{r.g_d_limit:.12g}",
                "E_inst": f"{r.e_inst:.12g}",
                "E_residual": f"{r.e_residual:.12g}",
                "pass_criterion": "yes" if r.pass_criterion else "no",
                "required_action": r.required_action,
            })


def write_md(path: Path, rows: list[ResultRow], *, target_pmission: float, target_e: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    lines.append("# MBU interleaving criterion examples")
    lines.append("")
    lines.append("## Purpose")
    lines.append("")
    lines.append(
        "This report gives numerical examples for the go/no-go criterion of periodic "
        "scrubbing under instant multi-bit events. The examples are intentionally "
        "simple and deterministic: an m-bit physical cluster is distributed over D "
        "codewords in a round-robin way, and SECDED is considered unsafe when two "
        "or more bits of the same event land in one codeword."
    )
    lines.append("")
    lines.append("The criterion is:")
    lines.append("")
    lines.append("- E_inst = N_events * g_D")
    lines.append("- g_D <= E* / N_events")
    lines.append("")
    lines.append(
        "If the criterion is violated, reducing the scrub period cannot remove this "
        "instant component. The remedy must change interleaving, code strength, "
        "logical placement, or memory organization."
    )
    lines.append("")
    lines.append(f"- Target mission probability: {target_pmission:.12g}")
    lines.append(f"- Target risk measure E*: {target_e:.12g}")
    lines.append("")

    lines.append("## Logical danger map")
    lines.append("")
    lines.append("| m-bit event | D=1 | D=2 | D=3 | D=4 |")
    lines.append("|---:|---:|---:|---:|---:|")

    for m in [1, 2, 3, 4]:
        vals = [
            secded_danger_probability_for_m(m, d)
            for d in [1, 2, 3, 4]
        ]
        lines.append(
            f"| {m} | "
            f"{vals[0]:.0f} | {vals[1]:.0f} | {vals[2]:.0f} | {vals[3]:.0f} |"
        )

    lines.append("")
    lines.append("Value 1 means instant SECDED-DUE is possible under the simplified mapping; value 0 means the event is split into single-bit errors across codewords.")
    lines.append("")

    lines.append("## Scenario results")
    lines.append("")
    lines.append("| scenario | N events | D | p2 | p3 | p4 | g_D | g_D limit | E_inst | E_residual | pass | action |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|")

    for r in rows:
        lines.append(
            f"| `{r.scenario}` | {r.event_count:.6g} | {r.interleave_depth} | "
            f"{r.p2:.3g} | {r.p3:.3g} | {r.p4:.3g} | "
            f"{r.g_d:.3g} | {r.g_d_limit:.3g} | {r.e_inst:.3g} | "
            f"{r.e_residual:.3g} | {'yes' if r.pass_criterion else 'no'} | "
            f"{r.required_action} |"
        )

    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    lines.append(
        "For 3-bit clusters, D=3 is sufficient in this simplified SECDED placement "
        "model because the cluster becomes 1+1+1 across three codewords. D=2 is "
        "not sufficient for a 3-bit event because the split is 2+1 and one codeword "
        "still receives a double-bit error. The `subbudget_3bit_clusters` case shows "
        "that nonzero instant MBU risk is acceptable only if it leaves a positive "
        "residual budget for the accumulated component."
    )
    lines.append("")
    lines.append(
        "For 4-bit clusters, D=3 is not sufficient because the split still contains "
        "a two-bit group. This is the practical meaning of the applicability "
        "criterion: once the instant component exceeds the budget, the scrub period "
        "is no longer the controlling design parameter."
    )
    lines.append("")
    lines.append(
        "The probabilities p2, p3 and p4 in this report are illustrative inputs. In "
        "a dissertation calculation they must be replaced by technology-specific "
        "or literature-supported h_m^(D) and event-rate estimates."
    )
    lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--target-pmission", type=float, default=DEFAULT_TARGET_PMISSION)
    p.add_argument("--depths", default="1,2,3,4")
    p.add_argument("--csv-output", type=Path, default=Path("results/paper/tables/mbu_interleaving_criterion_examples.csv"))
    p.add_argument("--md-output", type=Path, default=Path("results/paper/tables/mbu_interleaving_criterion_examples.md"))
    return p.parse_args()


def main() -> None:
    args = parse_args()

    target_e = target_risk_from_probability(args.target_pmission)
    depths = [int(x.strip()) for x in args.depths.split(",") if x.strip()]

    rows = evaluate(
        scenarios=default_scenarios(),
        interleave_depths=depths,
        target_e=target_e,
    )

    write_csv(args.csv_output, rows)
    write_md(
        args.md_output,
        rows,
        target_pmission=args.target_pmission,
        target_e=target_e,
    )

    failures = sum(1 for row in rows if not row.pass_criterion)
    print(f"CSV: {args.csv_output}")
    print(f"MD: {args.md_output}")
    print(f"rows: {len(rows)}")
    print(f"criterion_failures: {failures}")


if __name__ == "__main__":
    main()

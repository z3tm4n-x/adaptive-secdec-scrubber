#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
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
    pm_source: str


@dataclass(frozen=True)
class ResultRow:
    scenario: str
    description: str
    event_count: float
    interleave_depth: int
    hmd_mode: str
    hmd_source: str
    g_d: float
    g_d_limit: float
    e_inst: float
    e_residual: float
    residual_fraction: float
    pass_criterion: bool
    required_action: str
    pm_json: str
    hmd_json: str
    p1: float
    p2: float
    p3: float
    p4: float
    p5: float


@dataclass(frozen=True)
class SuppressionRow:
    scenario: str
    event_count: float
    interleave_depth: int
    multiplicity: int
    p_m: float
    g_d_limit: float
    h_required_max: float
    h_required_max_capped: float
    interpretation: str


def secded_danger_probability_for_m(m: int, interleave_depth: int) -> float:
    if m <= 1:
        return 0.0

    if interleave_depth <= 0:
        raise ValueError("interleave_depth must be positive")

    max_bits_per_word = math.ceil(m / interleave_depth)

    return 1.0 if max_bits_per_word >= 2 else 0.0


def normalize_pm(pm: dict[int, float]) -> dict[int, float]:
    cleaned = {int(m): float(p) for m, p in pm.items() if float(p) != 0.0}

    for m, p in cleaned.items():
        if m <= 0:
            raise ValueError(f"Multiplicity must be positive: {m}")
        if p < 0.0:
            raise ValueError(f"Negative p_m for m={m}: {p}")

    total = sum(cleaned.values())

    if total <= 0.0:
        raise ValueError("p_m distribution is empty")

    # In this repository p_m may be either a full distribution or a sparse dangerous-event
    # contribution vector. Do not automatically normalize, because the default examples
    # intentionally use small per-event dangerous fractions such as p3=5e-9.
    return cleaned


def read_pm_file(path: Path, *, event_count: float, scenario_name: str, description: str) -> list[Scenario]:
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        raise ValueError(f"Empty p_m file: {path}")

    # Two supported layouts:
    # 1. simple file: m,p_m,...
    # 2. scenario file: scenario,event_count,m,p_m,...
    has_scenario_column = "scenario" in rows[0]

    scenarios: dict[str, dict[int, float]] = {}
    descriptions: dict[str, str] = {}
    event_counts: dict[str, float] = {}

    if has_scenario_column:
        for r in rows:
            name = r.get("scenario", "").strip() or scenario_name
            m = int(r["m"])
            p = float(r["p_m"] or 0.0)
            scenarios.setdefault(name, {})[m] = p
            descriptions[name] = r.get("description", "").strip() or description
            if r.get("event_count", "").strip():
                event_counts[name] = float(r["event_count"])
            else:
                event_counts[name] = event_count
    else:
        pm: dict[int, float] = {}
        for r in rows:
            m = int(r["m"])
            p = float(r["p_m"] or 0.0)
            pm[m] = p
        scenarios[scenario_name] = pm
        descriptions[scenario_name] = description
        event_counts[scenario_name] = event_count

    result: list[Scenario] = []

    for name, pm in scenarios.items():
        result.append(
            Scenario(
                name=name,
                description=descriptions[name],
                event_count=event_counts[name],
                pm=normalize_pm(pm),
                pm_source=str(path),
            )
        )

    return result


def read_hmd_file(path: Path) -> dict[tuple[int, int], float]:
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        raise ValueError(f"Empty h_m file: {path}")

    result: dict[tuple[int, int], float] = {}

    for r in rows:
        if not r.get("h_D", "").strip():
            continue

        m = int(r["m"])
        d = int(r["D"])
        h = float(r["h_D"])

        if h < 0.0 or h > 1.0:
            raise ValueError(f"h_D must be in [0,1], got h={h} for m={m}, D={d}")

        result[(m, d)] = h

    if not result:
        raise ValueError(f"No usable h_D values in {path}")

    return result


def h_d_for_m(
    *,
    m: int,
    interleave_depth: int,
    hmd_mode: str,
    hmd_table: dict[tuple[int, int], float] | None,
) -> float:
    if hmd_mode == "logical_round_robin":
        return secded_danger_probability_for_m(m, interleave_depth)

    if hmd_mode == "table":
        if hmd_table is None:
            raise ValueError("hmd_table is required for hmd_mode=table")

        key = (m, interleave_depth)

        if key not in hmd_table:
            raise KeyError(f"Missing h_D for m={m}, D={interleave_depth}")

        return hmd_table[key]

    raise ValueError(f"Unsupported hmd_mode: {hmd_mode}")


def compute_gd(
    pm: dict[int, float],
    interleave_depth: int,
    *,
    hmd_mode: str,
    hmd_table: dict[tuple[int, int], float] | None,
) -> tuple[float, dict[int, float]]:
    total = 0.0
    h_values: dict[int, float] = {}

    for m, probability in pm.items():
        h = h_d_for_m(
            m=m,
            interleave_depth=interleave_depth,
            hmd_mode=hmd_mode,
            hmd_table=hmd_table,
        )
        h_values[m] = h
        total += probability * h

    return total, h_values


def default_scenarios() -> list[Scenario]:
    return [
        Scenario(
            name="subbudget_3bit_clusters",
            description="3-bit clusters are present but their instant contribution remains below the mission risk budget.",
            event_count=1_000_000.0,
            pm={2: 0.0, 3: 5.0e-9, 4: 0.0},
            pm_source="built_in_default",
        ),
        Scenario(
            name="rare_3bit_clusters",
            description="Rare but over-budget 3-bit clusters; D=3 is sufficient in the idealized mapping.",
            event_count=1_000_000.0,
            pm={2: 0.0, 3: 2.0e-8, 4: 0.0},
            pm_source="built_in_default",
        ),
        Scenario(
            name="strong_3bit_clusters",
            description="More frequent 3-bit clusters; D=1/2 violates the budget, D=3 removes the instant SECDED-DUE part.",
            event_count=1_000_000.0,
            pm={2: 0.0, 3: 2.0e-7, 4: 0.0},
            pm_source="built_in_default",
        ),
        Scenario(
            name="mixed_2bit_3bit",
            description="Mixture of 2-bit and 3-bit clusters; D=3 removes the 3-bit part but 2-bit same-event hits still require D>=2.",
            event_count=1_000_000.0,
            pm={2: 5.0e-8, 3: 1.0e-7, 4: 0.0},
            pm_source="built_in_default",
        ),
        Scenario(
            name="four_bit_clusters",
            description="4-bit clusters remain dangerous at D=3; D=4 or a stronger code/placement rule is required.",
            event_count=1_000_000.0,
            pm={2: 0.0, 3: 0.0, 4: 2.0e-7},
            pm_source="built_in_default",
        ),
        Scenario(
            name="high_event_count_low_probability",
            description="Low per-event danger can still violate the mission budget when the event count is high.",
            event_count=100_000_000.0,
            pm={2: 0.0, 3: 2.0e-10, 4: 0.0},
            pm_source="built_in_default",
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
    *,
    hmd_mode: str,
    hmd_table: dict[tuple[int, int], float] | None,
    hmd_source: str,
) -> list[ResultRow]:
    rows: list[ResultRow] = []

    for scenario in scenarios:
        g_d_limit = target_e / scenario.event_count

        for depth in interleave_depths:
            g_d, h_values = compute_gd(
                scenario.pm,
                depth,
                hmd_mode=hmd_mode,
                hmd_table=hmd_table,
            )
            e_inst = scenario.event_count * g_d
            e_residual = target_e - e_inst
            pass_criterion = e_inst <= target_e
            residual_fraction = e_residual / target_e if target_e > 0 else float("nan")

            rows.append(
                ResultRow(
                    scenario=scenario.name,
                    description=scenario.description,
                    event_count=scenario.event_count,
                    interleave_depth=depth,
                    hmd_mode=hmd_mode,
                    hmd_source=hmd_source,
                    g_d=g_d,
                    g_d_limit=g_d_limit,
                    e_inst=e_inst,
                    e_residual=e_residual,
                    residual_fraction=residual_fraction,
                    pass_criterion=pass_criterion,
                    required_action=action_for(pass_criterion, depth, g_d),
                    pm_json=json.dumps(scenario.pm, sort_keys=True),
                    hmd_json=json.dumps(h_values, sort_keys=True),
                    p1=scenario.pm.get(1, 0.0),
                    p2=scenario.pm.get(2, 0.0),
                    p3=scenario.pm.get(3, 0.0),
                    p4=scenario.pm.get(4, 0.0),
                    p5=scenario.pm.get(5, 0.0),
                )
            )

    return rows


def build_suppression_rows(
    scenarios: list[Scenario],
    interleave_depths: list[int],
    target_e: float,
) -> list[SuppressionRow]:
    rows: list[SuppressionRow] = []

    for scenario in scenarios:
        g_d_limit = target_e / scenario.event_count

        for depth in interleave_depths:
            for m, p_m in sorted(scenario.pm.items()):
                if m <= 1 or p_m <= 0.0:
                    continue

                h_required = g_d_limit / p_m
                h_capped = min(1.0, h_required)

                if h_required >= 1.0:
                    interpretation = "no suppression required for this single class alone"
                elif h_required <= 0.0:
                    interpretation = "impossible"
                else:
                    interpretation = "logical mapping must suppress this class below the listed h_m limit"

                rows.append(
                    SuppressionRow(
                        scenario=scenario.name,
                        event_count=scenario.event_count,
                        interleave_depth=depth,
                        multiplicity=m,
                        p_m=p_m,
                        g_d_limit=g_d_limit,
                        h_required_max=h_required,
                        h_required_max_capped=h_capped,
                        interpretation=interpretation,
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
        "hmd_mode",
        "hmd_source",
        "p1",
        "p2",
        "p3",
        "p4",
        "p5",
        "pm_json",
        "hmd_json",
        "g_D",
        "g_D_limit",
        "E_inst",
        "E_residual",
        "residual_fraction",
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
                "hmd_mode": r.hmd_mode,
                "hmd_source": r.hmd_source,
                "p1": f"{r.p1:.12g}",
                "p2": f"{r.p2:.12g}",
                "p3": f"{r.p3:.12g}",
                "p4": f"{r.p4:.12g}",
                "p5": f"{r.p5:.12g}",
                "pm_json": r.pm_json,
                "hmd_json": r.hmd_json,
                "g_D": f"{r.g_d:.12g}",
                "g_D_limit": f"{r.g_d_limit:.12g}",
                "E_inst": f"{r.e_inst:.12g}",
                "E_residual": f"{r.e_residual:.12g}",
                "residual_fraction": f"{r.residual_fraction:.12g}",
                "pass_criterion": "yes" if r.pass_criterion else "no",
                "required_action": r.required_action,
            })


def write_suppression_csv(path: Path, rows: list[SuppressionRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    fields = [
        "scenario",
        "event_count",
        "interleave_depth",
        "m",
        "p_m",
        "g_D_limit",
        "h_required_max",
        "h_required_max_capped",
        "interpretation",
    ]

    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()

        for r in rows:
            w.writerow({
                "scenario": r.scenario,
                "event_count": f"{r.event_count:.12g}",
                "interleave_depth": r.interleave_depth,
                "m": r.multiplicity,
                "p_m": f"{r.p_m:.12g}",
                "g_D_limit": f"{r.g_d_limit:.12g}",
                "h_required_max": f"{r.h_required_max:.12g}",
                "h_required_max_capped": f"{r.h_required_max_capped:.12g}",
                "interpretation": r.interpretation,
            })


def write_md(
    path: Path,
    rows: list[ResultRow],
    suppression_rows: list[SuppressionRow],
    *,
    target_pmission: float,
    target_e: float,
    pm_source: str,
    hmd_source: str,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []

    lines.append("# MBU interleaving criterion examples")
    lines.append("")
    lines.append("## Purpose")
    lines.append("")
    lines.append(
        "This report gives numerical examples for the go/no-go criterion of periodic "
        "scrubbing under instant multi-bit events. The default mode is deterministic "
        "and logical: an m-bit physical cluster is distributed over D codewords in a "
        "round-robin way, and SECDED is considered unsafe when two or more bits of the "
        "same event land in one codeword. The script can also consume p_m and h_m^(D) "
        "from CSV files."
    )
    lines.append("")
    lines.append("The criterion is:")
    lines.append("")
    lines.append("- E_inst = N_events * g_D")
    lines.append("- g_D <= E* / N_events")
    lines.append("- E_residual = E* - E_inst")
    lines.append("")
    lines.append(
        "If the criterion is violated, reducing the scrub period cannot remove this "
        "instant component. The remedy must change interleaving, code strength, "
        "logical placement, or memory organization."
    )
    lines.append("")
    lines.append(f"- Target mission probability: {target_pmission:.12g}")
    lines.append(f"- Target risk measure E*: {target_e:.12g}")
    lines.append(f"- p_m source: `{pm_source}`")
    lines.append(f"- h_m^(D) source: `{hmd_source}`")
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
    lines.append(
        "Value 1 means instant SECDED-DUE is possible under the simplified mapping; "
        "value 0 means the event is split into single-bit errors across codewords."
    )
    lines.append("")

    lines.append("## Scenario results")
    lines.append("")
    lines.append("| scenario | N events | D | p2 | p3 | p4 | g_D | g_D limit | E_inst | E_residual | residual fraction | pass | action |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|")

    for r in rows:
        lines.append(
            f"| `{r.scenario}` | {r.event_count:.6g} | {r.interleave_depth} | "
            f"{r.p2:.3g} | {r.p3:.3g} | {r.p4:.3g} | "
            f"{r.g_d:.3g} | {r.g_d_limit:.3g} | {r.e_inst:.3g} | "
            f"{r.e_residual:.3g} | {r.residual_fraction:.3g} | "
            f"{'yes' if r.pass_criterion else 'no'} | {r.required_action} |"
        )

    lines.append("")
    lines.append("## Suppression requirements")
    lines.append("")
    lines.append(
        "For a single multiplicity class considered alone, the criterion implies "
        "h_m^(D) <= g_crit / p_m, where g_crit = E* / N_events. This bound itself is "
        "D-independent; rows are repeated for each D so the required bound can be "
        "compared with the actual mapping value h_m^(D). In mixed cases this is "
        "a per-class diagnostic bound; the actual criterion remains the sum "
        "g_D = sum_m p_m h_m^(D)."
    )
    lines.append("")
    lines.append("| scenario | N events | D | m | p_m | g_crit | required h_m max | capped at 1 | interpretation |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---|")

    for r in suppression_rows:
        lines.append(
            f"| `{r.scenario}` | {r.event_count:.6g} | {r.interleave_depth} | "
            f"{r.multiplicity} | {r.p_m:.3g} | {r.g_d_limit:.3g} | "
            f"{r.h_required_max:.3g} | {r.h_required_max_capped:.3g} | "
            f"{r.interpretation} |"
        )

    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    lines.append(
        "The key point is that instant multi-bit events create a period-independent "
        "risk component. If E_inst already exceeds E*, no scrub interval can satisfy "
        "the target. If E_inst is below the target, the positive residual budget "
        "E_residual can be passed to the accumulated-risk scrub-period policy."
    )
    lines.append("")
    lines.append(
        "The p_m and h_m^(D) values used here are either built-in examples or values "
        "loaded from explicit CSV files. Values marked as illustrative or "
        "logical_round_robin must not be presented as measured technology parameters."
    )
    lines.append("")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_suppression_md(
    path: Path,
    rows: list[SuppressionRow],
    *,
    target_pmission: float,
    target_e: float,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []

    lines.append("# MBU suppression requirements")
    lines.append("")
    lines.append(f"- Target mission probability: {target_pmission:.12g}")
    lines.append(f"- Target risk measure E*: {target_e:.12g}")
    lines.append("")
    lines.append(
        "For a single multiplicity class, the applicability criterion can be written "
        "as p_m * h_m^(D) <= g_crit, therefore h_m^(D) <= g_crit / p_m. "
        "The required bound is independent of D; D enters through the actual achieved "
        "mapping probability h_m^(D). Rows are repeated by D for direct comparison "
        "with mapping tables."
    )
    lines.append("")
    lines.append("| scenario | N events | D | m | p_m | g_crit | required h_m max | capped at 1 | interpretation |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---|")

    for r in rows:
        lines.append(
            f"| `{r.scenario}` | {r.event_count:.6g} | {r.interleave_depth} | "
            f"{r.multiplicity} | {r.p_m:.3g} | {r.g_d_limit:.3g} | "
            f"{r.h_required_max:.3g} | {r.h_required_max_capped:.3g} | "
            f"{r.interpretation} |"
        )

    lines.append("")
    lines.append(
        "For mixed p_m distributions this table is diagnostic only. The full pass/fail "
        "condition is computed from the sum over all multiplicities."
    )
    lines.append("")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_depths(raw: str) -> list[int]:
    result = [int(x.strip()) for x in raw.split(",") if x.strip()]

    if not result:
        raise ValueError("At least one interleave depth is required")

    if any(x <= 0 for x in result):
        raise ValueError("Interleave depths must be positive")

    return result


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--target-pmission", type=float, default=DEFAULT_TARGET_PMISSION)
    p.add_argument("--interleave-depths", type=str, default="1,2,3,4")
    p.add_argument("--pm-file", type=Path, default=None)
    p.add_argument("--hmd-file", type=Path, default=None)
    p.add_argument("--hmd-mode", choices=["logical_round_robin", "table"], default="logical_round_robin")
    p.add_argument("--event-count", type=float, default=1_000_000.0)
    p.add_argument("--scenario-name", type=str, default="csv_pm_scenario")
    p.add_argument("--scenario-description", type=str, default="Scenario loaded from CSV p_m values.")
    p.add_argument("--csv-output", type=Path, default=Path("results/paper/tables/mbu_interleaving_criterion_examples.csv"))
    p.add_argument("--md-output", type=Path, default=Path("results/paper/tables/mbu_interleaving_criterion_examples.md"))
    p.add_argument("--suppression-csv-output", type=Path, default=Path("results/paper/tables/mbu_suppression_requirements.csv"))
    p.add_argument("--suppression-md-output", type=Path, default=Path("results/paper/tables/mbu_suppression_requirements.md"))
    return p.parse_args()


def main() -> None:
    args = parse_args()

    target_e = target_risk_from_probability(args.target_pmission)
    interleave_depths = parse_depths(args.interleave_depths)

    if args.pm_file is None:
        scenarios = default_scenarios()
        pm_source = "built_in_default"
    else:
        scenarios = read_pm_file(
            args.pm_file,
            event_count=args.event_count,
            scenario_name=args.scenario_name,
            description=args.scenario_description,
        )
        pm_source = str(args.pm_file)

    if args.hmd_mode == "table":
        if args.hmd_file is None:
            raise ValueError("--hmd-file is required when --hmd-mode table")
        hmd_table = read_hmd_file(args.hmd_file)
        hmd_source = str(args.hmd_file)
    else:
        hmd_table = None
        hmd_source = "logical_round_robin"

    rows = evaluate(
        scenarios,
        interleave_depths,
        target_e,
        hmd_mode=args.hmd_mode,
        hmd_table=hmd_table,
        hmd_source=hmd_source,
    )

    suppression_rows = build_suppression_rows(
        scenarios,
        interleave_depths,
        target_e,
    )

    write_csv(args.csv_output, rows)
    write_md(
        args.md_output,
        rows,
        suppression_rows,
        target_pmission=args.target_pmission,
        target_e=target_e,
        pm_source=pm_source,
        hmd_source=hmd_source,
    )
    write_suppression_csv(args.suppression_csv_output, suppression_rows)
    write_suppression_md(
        args.suppression_md_output,
        suppression_rows,
        target_pmission=args.target_pmission,
        target_e=target_e,
    )

    pass_count = sum(1 for r in rows if r.pass_criterion)

    print(f"rows: {len(rows)}")
    print(f"pass_rows: {pass_count}")
    print(f"fail_rows: {len(rows) - pass_count}")
    print(f"criterion_csv: {args.csv_output}")
    print(f"criterion_md: {args.md_output}")
    print(f"suppression_csv: {args.suppression_csv_output}")
    print(f"suppression_md: {args.suppression_md_output}")
    print(f"pm_source: {pm_source}")
    print(f"hmd_source: {hmd_source}")


if __name__ == "__main__":
    main()

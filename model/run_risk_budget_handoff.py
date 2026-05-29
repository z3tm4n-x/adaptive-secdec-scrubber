#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import math
import subprocess
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class HandoffCase:
    case_name: str
    scenario: str
    interleave_depth: int
    description: str


def run_cmd(cmd: list[str]) -> None:
    print("+ " + " ".join(cmd))
    subprocess.run(cmd, cwd=REPO_ROOT, check=True)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def find_criterion_row(
    rows: list[dict[str, str]],
    *,
    scenario: str,
    interleave_depth: int,
) -> dict[str, str]:
    for row in rows:
        if row["scenario"] == scenario and int(row["interleave_depth"]) == interleave_depth:
            return row
    raise KeyError((scenario, interleave_depth))


def risk_to_probability(e_value: float) -> float:
    if e_value < 0.0:
        raise ValueError("risk measure E must be non-negative")
    return 1.0 - math.exp(-e_value)


def safe_name(text: str) -> str:
    out = []
    for ch in text:
        if ch.isalnum() or ch in "-_":
            out.append(ch)
        else:
            out.append("_")
    return "".join(out)


def read_policy_summary(output_dir: Path) -> list[dict[str, str]]:
    path = output_dir / "risk_policy_summary.csv"
    if not path.exists():
        raise FileNotFoundError(path)
    return read_csv(path)


def write_markdown(
    path: Path,
    *,
    criterion_csv: Path,
    input_file: Path,
    start_index: int,
    window_size: int,
    rows: list[dict[str, str]],
) -> None:
    lines: list[str] = []

    lines.append("# Risk-budget handoff from MBU criterion to scrub policy")
    lines.append("")
    lines.append("## Purpose")
    lines.append("")
    lines.append(
        "This report connects the instant-MBU applicability criterion with the accumulated-risk "
        "scrub policy. The criterion computes E_inst = N_events * g_D. If E_inst <= E*, "
        "the remaining budget E_residual = E* - E_inst is passed to the accumulated-risk "
        "policy builder."
    )
    lines.append("")
    lines.append("The handoff is intentionally thin: it reuses evaluate_mbu_interleaving_criterion.py "
                 "and scrub_risk_policy.py instead of creating a parallel policy builder.")
    lines.append("")
    lines.append("## Inputs")
    lines.append("")
    lines.append(f"- Criterion CSV: `{criterion_csv}`")
    lines.append(f"- Upset input: `{input_file}`")
    lines.append(f"- Start index: {start_index}")
    lines.append(f"- Window size: {window_size}")
    lines.append("")
    lines.append("## Case summary")
    lines.append("")
    lines.append("| case | scenario | D | E* | E_inst | E_residual | P_residual | pass | policy output |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---|---|")

    seen_cases = set()
    for row in rows:
        key = row["case_name"]
        if key in seen_cases:
            continue
        seen_cases.add(key)
        lines.append(
            f"| `{row['case_name']}` | `{row['scenario']}` | {row['interleave_depth']} | "
            f"{float(row['target_e']):.6g} | {float(row['E_inst']):.6g} | "
            f"{float(row['E_residual']):.6g} | {float(row['P_residual']):.6g} | "
            f"{row['pass_criterion']} | `{row['policy_output_dir']}` |"
        )

    lines.append("")
    lines.append("## Policy rows under residual budgets")
    lines.append("")
    lines.append("| case | policy strategy | E used by policy | utilization of E_residual | budget slack | P mission | cycles | tau range, s |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|")

    for row in rows:
        lines.append(
            f"| `{row['case_name']}` | `{row['policy_strategy']}` | "
            f"{float(row['policy_risk_e']):.6g} | "
            f"{float(row['policy_residual_utilization']):.6g} | "
            f"{float(row['policy_budget_slack']):.6g} | "
            f"{float(row['policy_p_mission']):.6g} | "
            f"{float(row['policy_cycles']):.3f} | "
            f"{float(row['policy_min_tau_seconds']):.3f}--{float(row['policy_max_tau_seconds']):.3f} |"
        )

    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    lines.append(
        "The partial-residual case demonstrates the mixed regime: instant MBU consumes part "
        "of the mission budget and leaves a smaller accumulated-risk budget for scrubbing. "
        "The g_D=0 case demonstrates the accumulation-only regime: all target risk remains "
        "available for interval optimization. A finite interval grid may underuse the residual "
        "budget; this appears as positive policy_budget_slack rather than a criterion failure."
    )
    lines.append("")
    lines.append(
        "These outputs are policy-construction artifacts. They do not by themselves prove "
        "a flight implementation; they document that the repository now executes the same "
        "budget chain used by the theory."
    )
    lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--criterion-csv", type=Path, default=Path("results/paper/tables/mbu_interleaving_criterion_examples.csv"))
    p.add_argument("--input", type=Path, default=Path("data/upsets.xlsx"))
    p.add_argument("--start-index", type=int, default=0)
    p.add_argument("--window-size", type=int, default=43824)
    p.add_argument("--intervals-seconds", default="1,2,5,10,30,60,120,300,600,1200,1800,3600")
    p.add_argument("--output-dir", type=Path, default=Path("results/paper/risk_budget_handoff"))
    return p.parse_args()


def main() -> None:
    args = parse_args()

    criterion_path = REPO_ROOT / args.criterion_csv
    criterion_rows = read_csv(criterion_path)

    cases = [
        HandoffCase(
            case_name="partial_instant_residual_D1",
            scenario="subbudget_3bit_clusters",
            interleave_depth=1,
            description="Instant 3-bit clusters consume part of the mission budget; residual budget remains positive.",
        ),
        HandoffCase(
            case_name="accumulation_only_gD0_D3",
            scenario="subbudget_3bit_clusters",
            interleave_depth=3,
            description="Sufficient interleaving removes the instant term in the logical round-robin model.",
        ),
    ]

    combined_rows: list[dict[str, str]] = []

    for case in cases:
        crit = find_criterion_row(
            criterion_rows,
            scenario=case.scenario,
            interleave_depth=case.interleave_depth,
        )

        pass_criterion = crit["pass_criterion"]
        if pass_criterion != "yes":
            raise RuntimeError(f"Selected handoff case does not pass criterion: {case}")

        target_e = float(crit["g_D_limit"]) * float(crit["event_count"])
        e_inst = float(crit["E_inst"])
        e_residual = float(crit["E_residual"])

        if e_residual <= 0.0:
            raise RuntimeError(f"No positive residual budget for {case.case_name}")

        p_residual = risk_to_probability(e_residual)

        case_dir = REPO_ROOT / args.output_dir / safe_name(case.case_name)

        run_cmd([
            "python3",
            "model/scrub_risk_policy.py",
            "--input",
            str(args.input),
            "--start-index",
            str(args.start_index),
            "--window-size",
            str(args.window_size),
            "--target-pmission",
            f"{p_residual:.17g}",
            "--intervals-seconds",
            args.intervals_seconds,
            "--output-dir",
            str(case_dir.relative_to(REPO_ROOT)),
        ])

        policy_rows = read_policy_summary(case_dir)

        for policy in policy_rows:
            policy_risk_e = float(policy["risk_e"])
            policy_budget_slack = e_residual - policy_risk_e
            policy_residual_utilization = policy_risk_e / e_residual if e_residual > 0.0 else 0.0

            combined_rows.append({
                "case_name": case.case_name,
                "description": case.description,
                "scenario": case.scenario,
                "interleave_depth": str(case.interleave_depth),
                "event_count": crit["event_count"],
                "g_D": crit["g_D"],
                "target_e": f"{target_e:.12g}",
                "E_inst": f"{e_inst:.12g}",
                "E_residual": f"{e_residual:.12g}",
                "P_residual": f"{p_residual:.12g}",
                "pass_criterion": pass_criterion,
                "policy_output_dir": str(case_dir.relative_to(REPO_ROOT)),
                "policy_strategy": policy["strategy"],
                "policy_risk_e": policy["risk_e"],
                "policy_p_mission": policy["p_mission"],
                "policy_cycles": policy["cycles"],
                "policy_min_tau_seconds": policy["min_tau_seconds"],
                "policy_max_tau_seconds": policy["max_tau_seconds"],
                "policy_budget_slack": f"{policy_budget_slack:.12g}",
                "policy_residual_utilization": f"{policy_residual_utilization:.12g}",
            })

    out_dir = REPO_ROOT / args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    fields = [
        "case_name",
        "description",
        "scenario",
        "interleave_depth",
        "event_count",
        "g_D",
        "target_e",
        "E_inst",
        "E_residual",
        "P_residual",
        "pass_criterion",
        "policy_output_dir",
        "policy_strategy",
        "policy_risk_e",
        "policy_p_mission",
        "policy_cycles",
        "policy_min_tau_seconds",
        "policy_max_tau_seconds",
        "policy_budget_slack",
        "policy_residual_utilization",
    ]

    write_csv(out_dir / "risk_budget_handoff_cases.csv", combined_rows, fields)

    write_markdown(
        out_dir / "risk_budget_handoff_summary.md",
        criterion_csv=args.criterion_csv,
        input_file=args.input,
        start_index=args.start_index,
        window_size=args.window_size,
        rows=combined_rows,
    )

    print(f"handoff rows: {len(combined_rows)}")
    print(f"summary: {args.output_dir / 'risk_budget_handoff_summary.md'}")
    print(f"csv: {args.output_dir / 'risk_budget_handoff_cases.csv'}")

    for row in combined_rows:
        if row["policy_strategy"] == "adaptive_current_discrete":
            print(
                f"{row['case_name']}: E_inst={row['E_inst']} "
                f"E_residual={row['E_residual']} P_residual={row['P_residual']} "
                f"policy_E={row['policy_risk_e']}"
            )


if __name__ == "__main__":
    main()

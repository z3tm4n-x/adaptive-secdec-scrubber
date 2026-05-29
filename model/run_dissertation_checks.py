#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import py_compile
import subprocess
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


REQUIRED_FILES = [
    "README.md",
    "REPRODUCE.md",
    "Makefile",
    "doc/dissertation_mapping.md",
    "doc/prior_art_measured_control.md",
    "model/risk_core.py",
    "model/verify_efficiency_scale.py",
    "model/run_risk_sensitivity.py",
    "model/evaluate_mbu_interleaving_criterion.py",
    "model/run_interleaving_sweep.py",
    "model/run_closed_loop_measured_series.py",
    "model/build_interleaving_summary.py",
    "rtl/adaptive_scrub_controller.v",
    "rtl/interval_selector.v",
    "rtl/measured_control_estimator.v",
    "rtl/protected_memory_model.v",
    "tb/tb_strategy_comparison.v",
    "tb/tb_measured_control_estimator.v",
    "results/paper/README.md",
    "results/paper/final_results_summary.md",
    "results/paper/repository_integrity_check.md",
    "results/paper/measured_control/measured_control_summary.md",
    "results/paper/measured_control/closed_loop_smoke/closed_loop_smoke_summary.md",
    "results/paper/measured_control/closed_loop/closed_loop_measured_summary.md",
    "results/paper/measured_control/closed_loop/closed_loop_measured_series.csv",
    "results/paper/interleaving/interleaving_summary.md",
    "results/paper/interleaving/interval_sweep/interleaving_interval_sweep_runs.csv",
    "results/paper/interleaving/interval_sweep/interleaving_interval_sweep_summary.csv",
    "results/paper/interleaving/interval_sweep/interleaving_interval_sweep_deltas.csv",
    "results/paper/tables/efficiency_scale_verification.md",
    "results/paper/tables/efficiency_scale_verification.csv",
    "results/paper/tables/risk_sensitivity_summary.md",
    "results/paper/tables/risk_sensitivity.csv",
    "results/paper/tables/mbu_interleaving_criterion_examples.md",
    "results/paper/tables/mbu_interleaving_criterion_examples.csv",
    "results/paper/measured_control/weight_sweep/measured_weight_sweep_deltas.csv",
    "results/paper/measured_control/weight_sweep/measured_weight_sweep_runs.csv",
    "results/paper/measured_control/weight_sweep/measured_weight_sweep_summary.csv",
    "results/paper/measured_control/weight_sweep/measured_weight_sweep_summary.md",
    "results/paper/accumulation_only_rtl/accumulation_only_rtl_deltas.csv",
    "results/paper/accumulation_only_rtl/accumulation_only_rtl_runs.csv",
    "results/paper/accumulation_only_rtl/accumulation_only_rtl_summary.csv",
    "results/paper/accumulation_only_rtl/accumulation_only_rtl_summary.md",
    "results/paper/risk_budget_handoff/risk_budget_handoff_cases.csv",
    "results/paper/risk_budget_handoff/risk_budget_handoff_summary.md",
    "results/paper/tables/mbu_suppression_requirements.csv",
    "results/paper/tables/mbu_suppression_requirements.md",
    "results/paper/theory_consistency/poisson_accumulation_validation.csv",
    "results/paper/theory_consistency/poisson_accumulation_validation.md",
    "results/paper/theory_consistency/theory_consistency.csv",
    "results/paper/theory_consistency/theory_consistency_summary.md",
    "model/run_measured_weight_sweep.py",
    "model/run_accumulation_only_rtl_series.py",
    "model/run_risk_budget_handoff.py",
    "model/run_poisson_accumulation_validation.py",
    "model/run_theory_consistency_checks.py",
    "data/mbu_hmd_literature_template.csv",
    "data/mbu_pm_literature_template.csv",
    "data/mbu_hmd_logical_round_robin.csv",
    "data/mbu_pm_logical_example.csv",
    "doc/mbu_parameter_sources.md",
]


CSV_MIN_ROWS = {
    "results/paper/measured_control/closed_loop/closed_loop_measured_series.csv": 40,
    "results/paper/interleaving/interval_sweep/interleaving_interval_sweep_runs.csv": 150,
    "results/paper/interleaving/interval_sweep/interleaving_interval_sweep_summary.csv": 15,
    "results/paper/interleaving/interval_sweep/interleaving_interval_sweep_deltas.csv": 39,
    "results/paper/tables/risk_sensitivity.csv": 19,
    "results/paper/tables/mbu_interleaving_criterion_examples.csv": 24,
    "results/paper/tables/efficiency_scale_verification.csv": 5,
    "results/paper/measured_control/weight_sweep/measured_weight_sweep_deltas.csv": 18,
    "results/paper/measured_control/weight_sweep/measured_weight_sweep_summary.csv": 6,
    "results/paper/measured_control/weight_sweep/measured_weight_sweep_runs.csv": 30,
    "results/paper/accumulation_only_rtl/accumulation_only_rtl_deltas.csv": 6,
    "results/paper/accumulation_only_rtl/accumulation_only_rtl_summary.csv": 2,
    "results/paper/accumulation_only_rtl/accumulation_only_rtl_runs.csv": 20,
    "results/paper/risk_budget_handoff/risk_budget_handoff_cases.csv": 10,
    "results/paper/tables/mbu_suppression_requirements.csv": 20,
    "results/paper/theory_consistency/poisson_accumulation_validation.csv": 4,
    "results/paper/theory_consistency/theory_consistency.csv": 31,
}


TEXT_MUST_CONTAIN = {
    "doc/dissertation_mapping.md": [
        "Do not state that adaptive scrub-rate itself is new",
        "mbu_interleaving_criterion_examples.md",
        "risk_sensitivity_summary.md",
        "closed_loop_measured_summary.md",
        "run_theory_consistency_checks.py",
        "run_risk_budget_handoff.py",
        "run_accumulation_only_rtl_series.py",
        "run_measured_weight_sweep.py",
        "new_due_count",
    ],
    "results/paper/measured_control/measured_control_summary.md": [
        "closed-loop RTL",
        "MODE_MEASURED",
        "offline replay",
        "unique DUE",
        "Measured-control status: demonstration, not a net resource win.",
        "runtime first-arrival",
        "post-run audit",
        "not a net resource win",
    ],
    "results/paper/final_results_summary.md": [
        "closed-loop",
        "MODE_MEASURED",
        "offline replay",
        "unique DUE",
        "Current interleaving note",
        "cluster_injection_skew = 0",
        "Measured-control status: demonstration",
        "Theory-aligned repository update",
        "run_risk_budget_handoff.py",
        "new_due_count",
        "measured-control не следует описывать как net resource win",
        "g_D = 0",
    ],
    "results/paper/interleaving/interleaving_summary.md": [
        "истинно одновременно",
        "cluster_injection_skew = 0",
        "Частичное перемежение D=2",
        "new_due_count",
        "repeated DED",
        "diagnostic counter",
    ],
    "results/paper/tables/risk_sensitivity_summary.md": [
        "1 + CV",
        "discrete_gain_vs_fixed",
        "below one",
        "saturated at",
    ],
    "results/paper/tables/mbu_interleaving_criterion_examples.md": [
        "E_inst = N_events * g_D",
        "g_D <= E* / N_events",
        "subbudget_3bit_clusters",
        "positive residual budget",
        "Suppression requirements",
        "h_m^(D) <= g_crit / p_m",
    ],
    "doc/mbu_parameter_sources.md": [
        "logical_round_robin",
        "illustrative",
        "source_required",
        "Giot",
        "Baeg",
        "mu = 1",
    ],
    "results/paper/theory_consistency/theory_consistency_summary.md": [
        "Exact vs quadratic",
        "Mission-level instant-risk floor",
        "g_D = 0",
    ],
    "results/paper/theory_consistency/poisson_accumulation_validation.md": [
        "Poisson accumulation validation",
        "within CI",
        "device-level radiation validation",
    ],
    "results/paper/risk_budget_handoff/risk_budget_handoff_summary.md": [
        "E_inst = N_events * g_D",
        "E_residual = E* - E_inst",
        "policy_budget_slack",
        "budget chain",
    ],
    "results/paper/accumulation_only_rtl/accumulation_only_rtl_summary.md": [
        "g_D = 0",
        "new_due_count",
        "not a device-level radiation validation",
    ],
    "results/paper/measured_control/weight_sweep/measured_weight_sweep_summary.md": [
        "Measured-control status: demonstration, not a net resource win.",
        "new_due_count",
        "runtime first-arrival",
        "post-run memory audit",
    ],
}



TEXT_MUST_NOT_CONTAIN = {
    "results/paper/interleaving/interleaving_summary.md": [
        "Техническое ограничение текущего Verilog-стенда",
        "физически одномоментный кластер сериализуется",
        "по соседним тактам",
        "статистически значимый рост unique",
    ],
    "results/paper/final_results_summary.md": [
        "Техническое ограничение текущего Verilog-стенда",
        "физически одномоментный кластер сериализуется",
        "по соседним тактам",
        "одна fault-инжекция за такт",
        "D3 slowest-fastest | +6.400",
        "`D3 slowest-fastest` | +6.400",
        "+6.400 [4.399; 8.401]",
        "статистически значимый рост unique",
        "Это не полностью аппаратно замкнутый контур",
        "measured-control is a net win",
        "measured-control net win",
    ],
}



PYTHON_SCRIPTS = [
    "model/risk_core.py",
    "model/verify_efficiency_scale.py",
    "model/run_risk_sensitivity.py",
    "model/evaluate_mbu_interleaving_criterion.py",
    "model/run_interleaving_sweep.py",
    "model/run_closed_loop_measured_series.py",
    "model/build_interleaving_summary.py",
    "model/build_measured_control_summary.py",
    "model/check_repository_results_integrity.py",
    "model/regression_check_risk_outputs.py",
    "model/generate_fault_events.py",
]


@dataclass
class CheckResult:
    name: str
    ok: bool
    details: str


def rel(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def check_required_files() -> list[CheckResult]:
    results: list[CheckResult] = []

    for item in REQUIRED_FILES:
        path = REPO_ROOT / item
        if not path.exists():
            results.append(CheckResult(f"required:{item}", False, "missing"))
        elif path.is_file() and path.stat().st_size == 0:
            results.append(CheckResult(f"required:{item}", False, "empty"))
        else:
            results.append(CheckResult(f"required:{item}", True, "present"))

    return results


def check_csv_files() -> list[CheckResult]:
    results: list[CheckResult] = []

    for item, min_rows in CSV_MIN_ROWS.items():
        path = REPO_ROOT / item

        if not path.exists():
            results.append(CheckResult(f"csv:{item}", False, "missing"))
            continue

        try:
            with path.open(newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
        except Exception as exc:
            results.append(CheckResult(f"csv:{item}", False, f"read error: {exc}"))
            continue

        if len(rows) < min_rows:
            results.append(CheckResult(f"csv:{item}", False, f"rows={len(rows)} < {min_rows}"))
        else:
            results.append(CheckResult(f"csv:{item}", True, f"rows={len(rows)}"))

    return results


def check_text_content() -> list[CheckResult]:
    results: list[CheckResult] = []

    for item, needles in TEXT_MUST_CONTAIN.items():
        path = REPO_ROOT / item

        if not path.exists():
            results.append(CheckResult(f"text_contains:{item}", False, "missing"))
            continue

        text = path.read_text(encoding="utf-8")

        for needle in needles:
            ok = needle in text
            results.append(
                CheckResult(
                    f"text_contains:{item}:{needle}",
                    ok,
                    "found" if ok else "not found",
                )
            )

    for item, needles in TEXT_MUST_NOT_CONTAIN.items():
        path = REPO_ROOT / item

        if not path.exists():
            results.append(CheckResult(f"text_forbidden:{item}", False, "missing"))
            continue

        text = path.read_text(encoding="utf-8")

        for needle in needles:
            ok = needle not in text
            results.append(
                CheckResult(
                    f"text_forbidden:{item}:{needle}",
                    ok,
                    "absent" if ok else "forbidden text present",
                )
            )

    return results


def check_python_compile() -> list[CheckResult]:
    results: list[CheckResult] = []

    for item in PYTHON_SCRIPTS:
        path = REPO_ROOT / item

        if not path.exists():
            results.append(CheckResult(f"py_compile:{item}", False, "missing"))
            continue

        try:
            py_compile.compile(str(path), doraise=True)
        except Exception as exc:
            results.append(CheckResult(f"py_compile:{item}", False, str(exc)))
        else:
            results.append(CheckResult(f"py_compile:{item}", True, "compiled"))

    return results


def check_no_debug_artifacts() -> list[CheckResult]:
    results: list[CheckResult] = []

    debug_patterns = [
        "results/paper/**/*.vcd",
        "results/paper/**/*.out",
    ]

    for pattern in debug_patterns:
        matches = sorted(REPO_ROOT.glob(pattern))
        ok = len(matches) == 0
        detail = "none" if ok else ", ".join(rel(p) for p in matches[:20])
        if len(matches) > 20:
            detail += f" ... and {len(matches) - 20} more"
        results.append(CheckResult(f"debug_artifacts:{pattern}", ok, detail))

    interleaving_seed_dirs = sorted((REPO_ROOT / "results/paper/interleaving/interval_sweep").glob("D*/interval_*/seed_*"))
    stale_tables: list[Path] = []

    for seed_dir in interleaving_seed_dirs:
        table = seed_dir / "strategy_comparison.csv"
        if table.exists():
            header = table.read_text(encoding="utf-8").splitlines()[0]
            if "new_due_count" not in header or "repeated_due_detections" not in header:
                stale_tables.append(table)

    ok = len(stale_tables) == 0
    if not interleaving_seed_dirs:
        detail = "no per-seed directories present; aggregated tables are authoritative"
    elif ok:
        detail = f"per-seed dirs present and latched DUE columns verified: {len(interleaving_seed_dirs)}"
    else:
        detail = ", ".join(rel(p) for p in stale_tables[:20])
        if len(stale_tables) > 20:
            detail += f" ... and {len(stale_tables) - 20} more"

    results.append(CheckResult("interleaving_seed_dirs_latched_due_columns", ok, detail))

    return results


def check_make_target() -> list[CheckResult]:
    makefile = REPO_ROOT / "Makefile"

    if not makefile.exists():
        return [CheckResult("make_target:dissertation_check", False, "Makefile missing")]

    text = makefile.read_text(encoding="utf-8")
    ok = "dissertation_check" in text
    return [
        CheckResult(
            "make_target:dissertation_check",
            ok,
            "present" if ok else "missing",
        )
    ]


def run_optional_rtl_smoke() -> list[CheckResult]:
    commands = [
        ["make", "test_measured_control_estimator"],
        ["make", "test_adaptive_scrub_controller"],
    ]

    results: list[CheckResult] = []

    for cmd in commands:
        name = "rtl_smoke:" + " ".join(cmd)
        proc = subprocess.run(
            cmd,
            cwd=REPO_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )

        if proc.returncode == 0:
            results.append(CheckResult(name, True, "passed"))
        else:
            tail = "\n".join(proc.stdout.splitlines()[-20:])
            results.append(CheckResult(name, False, tail))

    return results


def write_report(path: Path, results: list[CheckResult]) -> None:
    passed = [r for r in results if r.ok]
    failed = [r for r in results if not r.ok]

    lines: list[str] = []
    lines.append("# Dissertation repository check")
    lines.append("")
    lines.append(f"- Total checks: {len(results)}")
    lines.append(f"- Passed: {len(passed)}")
    lines.append(f"- Failed: {len(failed)}")
    lines.append("")
    lines.append("## Failed checks")
    lines.append("")

    if failed:
        lines.append("| check | details |")
        lines.append("|---|---|")
        for r in failed:
            safe_details = r.details.replace("\n", "<br>")
            lines.append(f"| `{r.name}` | {safe_details} |")
    else:
        lines.append("No failed checks.")

    lines.append("")
    lines.append("## Passed checks")
    lines.append("")
    lines.append("| check | details |")
    lines.append("|---|---|")

    for r in passed:
        safe_details = r.details.replace("\n", "<br>")
        lines.append(f"| `{r.name}` | {safe_details} |")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--with-rtl-smoke",
        action="store_true",
        help="Also run a small subset of RTL smoke tests.",
    )
    p.add_argument(
        "--report",
        type=Path,
        default=Path("results/paper/dissertation_check.md"),
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()

    results: list[CheckResult] = []
    results.extend(check_required_files())
    results.extend(check_csv_files())
    results.extend(check_text_content())
    results.extend(check_python_compile())
    results.extend(check_no_debug_artifacts())
    results.extend(check_make_target())

    if args.with_rtl_smoke:
        results.extend(run_optional_rtl_smoke())

    write_report(REPO_ROOT / args.report, results)

    failed = [r for r in results if not r.ok]

    print(f"report: {args.report}")
    print(f"checks: {len(results)}")
    print(f"passed: {len(results) - len(failed)}")
    print(f"failed: {len(failed)}")

    if failed:
        print("failed checks:")
        for r in failed:
            print(f"- {r.name}: {r.details}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()

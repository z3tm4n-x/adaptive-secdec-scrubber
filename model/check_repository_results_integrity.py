#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class Issue:
    severity: str
    path: str
    message: str


def rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def inspect_csv(path: Path) -> tuple[bool, str, int, int]:
    try:
        with path.open("r", encoding="utf-8", newline="") as f:
            rows = list(csv.reader(f))
    except Exception as exc:
        return False, f"CSV read error: {exc}", 0, 0

    if not rows:
        return False, "CSV has no rows", 0, 0

    header = rows[0]
    data_rows = rows[1:]

    if not header or all(cell.strip() == "" for cell in header):
        return False, "CSV header is empty", len(header), len(data_rows)

    if len(data_rows) == 0:
        return False, "CSV has header but no data rows", len(header), 0

    return True, "ok", len(header), len(data_rows)


def git_status(root: Path) -> str:
    proc = subprocess.run(
        ["git", "status", "--short"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )

    if proc.returncode != 0:
        return proc.stderr.strip() or "git status failed"

    return proc.stdout.strip() or "clean"


def check_required_files(root: Path, issues: list[Issue]) -> list[dict[str, str]]:
    required = [
        ("README.md", "root README"),
        ("REPRODUCE.md", "reproduce instructions"),
        ("Makefile", "top-level build/run entrypoint"),
        ("doc/prior_art_measured_control.md", "measured-control prior-art boundary"),

        ("model/risk_core.py", "canonical risk model"),
        ("model/verify_efficiency_scale.py", "efficiency verification"),
        ("model/build_measured_control_summary.py", "measured-control summary builder"),
        ("model/build_interleaving_summary.py", "interleaving summary builder"),

        ("rtl/adaptive_scrub_controller.v", "main scrub controller"),
        ("rtl/interval_selector.v", "interval selector"),
        ("rtl/protected_memory_model.v", "protected memory model"),

        ("tb/tb_strategy_comparison.v", "strategy comparison testbench"),

        ("results/paper/README.md", "paper results navigation"),
        ("results/paper/final_results_summary.md", "final results summary"),

        ("results/paper/tables/efficiency_scale_verification.md", "efficiency scale report"),
        ("results/paper/tables/efficiency_scale_verification.csv", "efficiency scale csv"),
        ("results/paper/tables/risk_regression_report.md", "risk regression report"),
        ("results/paper/tables/risk_regression_report.csv", "risk regression report csv"),

        ("results/paper/unsaturated_control/unsaturated_control_summary.md", "unsaturated control summary"),
        ("results/paper/unsaturated_control/no_clusters/strategy_series_summary.md", "no-clusters strategy summary"),
        ("results/paper/unsaturated_control/no_clusters/paired_delta_analysis.md", "no-clusters paired delta"),
        ("results/paper/unsaturated_control/fixed_grid_no_clusters/fixed_grid_pareto.md", "fixed-grid no-clusters"),
        ("results/paper/unsaturated_control/fixed_grid_with_clusters/fixed_grid_pareto.md", "fixed-grid with-clusters"),

        ("results/paper/measured_control/measured_control_summary.md", "measured-control summary"),
        ("results/paper/measured_control/no_clusters_weight_sweep/measured_weight_sweep_summary.md", "measured weight sweep summary"),
        ("results/paper/measured_control/no_clusters_weight_sweep/measured_weight_sweep_deltas.md", "measured weight sweep deltas"),
        ("results/paper/observable_signal/no_clusters_seed1/observable_signal_summary.md", "observable signal summary"),

        ("results/paper/interleaving/interleaving_summary.md", "interleaving summary"),
        ("results/paper/interleaving/interval_sweep/interleaving_interval_sweep_summary.md", "interleaving interval sweep summary"),
        ("results/paper/interleaving/interval_sweep/interleaving_interval_sweep_deltas.md", "interleaving interval sweep deltas"),

        ("results/paper/true_pair_alignment/true_pair_alignment_summary.md", "true pair alignment summary"),
    ]

    rows: list[dict[str, str]] = []

    for path_text, purpose in required:
        path = root / path_text
        exists = path.exists()
        size = path.stat().st_size if exists else 0

        if not exists:
            status = "FAIL"
            issues.append(Issue("FAIL", path_text, "required file is missing"))
        elif size == 0:
            status = "FAIL"
            issues.append(Issue("FAIL", path_text, "required file is empty"))
        else:
            status = "ok"

        rows.append(
            {
                "path": path_text,
                "purpose": purpose,
                "status": status,
                "size": str(size),
            }
        )

    return rows


def check_expected_sections(root: Path, issues: list[Issue]) -> None:
    checks = {
        "results/paper/README.md": [
            "Читать в первую очередь",
            "Основной смысл результатов",
            "Ограничения интерпретации",
            "Воспроизведение",
        ],
        "results/paper/final_results_summary.md": [
            "Расчётная шкала эффективности",
            "Контрольная серия вне насыщения",
            "Observable signal",
            "measured-control",
            "Перемежение",
            "Ограничения",
        ],
        "results/paper/measured_control/measured_control_summary.md": [
            "w=0.50",
            "corrected-only",
            "measured_table_w0p50",
        ],
        "results/paper/interleaving/interleaving_summary.md": [
            "D=1",
            "D=2",
            "D=3",
        ],
    }

    for relative, needles in checks.items():
        path = root / relative
        if not path.exists():
            continue

        text = read_text(path)

        for needle in needles:
            if needle not in text:
                issues.append(
                    Issue(
                        "WARN",
                        relative,
                        f"expected phrase not found: {needle}",
                    )
                )


def check_all_md_csv(root: Path, issues: list[Issue]) -> dict[str, int]:
    base = root / "results" / "paper"
    counts = {
        "md_files": 0,
        "csv_files": 0,
        "empty_files": 0,
        "bad_csv_files": 0,
    }

    if not base.exists():
        issues.append(Issue("FAIL", "results/paper", "directory is missing"))
        return counts

    for path in sorted(base.rglob("*")):
        if not path.is_file():
            continue

        suffix = path.suffix.lower()
        if suffix not in {".md", ".csv"}:
            continue

        relative = rel(path, root)
        size = path.stat().st_size

        if suffix == ".md":
            counts["md_files"] += 1
        elif suffix == ".csv":
            counts["csv_files"] += 1

        if size == 0:
            counts["empty_files"] += 1
            issues.append(Issue("FAIL", relative, "file is empty"))
            continue

        if suffix == ".csv":
            ok, message, header_cols, data_rows = inspect_csv(path)
            if not ok:
                counts["bad_csv_files"] += 1
                issues.append(
                    Issue(
                        "FAIL",
                        relative,
                        f"{message}; header_cols={header_cols}; data_rows={data_rows}",
                    )
                )

    return counts


def check_interleaving_matrix(root: Path, issues: list[Issue]) -> dict[str, str]:
    path = root / "results/paper/interleaving/interval_sweep/interleaving_interval_sweep.csv"

    report = {
        "raw_csv": rel(path, root),
        "raw_rows": "missing",
        "depths": "",
        "intervals": "",
        "seeds": "",
        "strategies": "",
        "matrix_complete": "no",
    }

    if not path.exists():
        issues.append(Issue("FAIL", rel(path, root), "interleaving raw sweep CSV is missing"))
        return report

    try:
        with path.open("r", encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
    except Exception as exc:
        issues.append(Issue("FAIL", rel(path, root), f"could not read interleaving raw CSV: {exc}"))
        return report

    report["raw_rows"] = str(len(rows))

    if not rows:
        issues.append(Issue("FAIL", rel(path, root), "interleaving raw CSV has no data rows"))
        return report

    required = {"seed", "interleave_depth", "fixed_interval", "strategy"}
    missing = required - set(rows[0].keys())

    if missing:
        issues.append(
            Issue(
                "FAIL",
                rel(path, root),
                f"missing required columns: {sorted(missing)}",
            )
        )
        return report

    depths = sorted({int(row["interleave_depth"]) for row in rows})
    intervals = sorted({int(row["fixed_interval"]) for row in rows})
    seeds = sorted({int(row["seed"]) for row in rows})
    strategies = sorted({row["strategy"] for row in rows})

    report["depths"] = ",".join(str(x) for x in depths)
    report["intervals"] = ",".join(str(x) for x in intervals)
    report["seeds"] = f"{len(seeds)} ({seeds[0]}..{seeds[-1]})" if seeds else "0"
    report["strategies"] = ",".join(strategies)

    expected_depths = [1, 2, 3]
    expected_intervals = [1089, 1244, 1555, 2021, 2400]
    expected_seeds = list(range(1, 11))
    expected_strategies = ["fixed", "table", "threshold"]

    expected_rows = (
        len(expected_depths)
        * len(expected_intervals)
        * len(expected_seeds)
        * len(expected_strategies)
    )

    if len(rows) != expected_rows:
        issues.append(
            Issue(
                "FAIL",
                rel(path, root),
                f"expected {expected_rows} rows, got {len(rows)}",
            )
        )

    if depths != expected_depths:
        issues.append(Issue("FAIL", rel(path, root), f"unexpected D values: {depths}"))

    if intervals != expected_intervals:
        issues.append(Issue("FAIL", rel(path, root), f"unexpected intervals: {intervals}"))

    if seeds != expected_seeds:
        issues.append(Issue("FAIL", rel(path, root), f"unexpected seeds: {seeds}"))

    if strategies != expected_strategies:
        issues.append(Issue("FAIL", rel(path, root), f"unexpected strategies: {strategies}"))

    present = {
        (
            int(row["interleave_depth"]),
            int(row["fixed_interval"]),
            int(row["seed"]),
            row["strategy"],
        )
        for row in rows
    }

    missing_cells = []

    for depth in expected_depths:
        for interval in expected_intervals:
            for seed in expected_seeds:
                for strategy in expected_strategies:
                    key = (depth, interval, seed, strategy)
                    if key not in present:
                        missing_cells.append(key)

    if missing_cells:
        sample = ", ".join(str(item) for item in missing_cells[:10])
        issues.append(
            Issue(
                "FAIL",
                rel(path, root),
                f"missing matrix cells: {len(missing_cells)}; first: {sample}",
            )
        )
    else:
        report["matrix_complete"] = "yes"

    return report


def extract_markdown_paths(text: str) -> set[str]:
    found: set[str] = set()

    # Markdown links: [text](path)
    for match in re.finditer(r"\]\(([^)]+)\)", text):
        item = match.group(1).strip()
        if item.startswith(("http://", "https://", "#", "mailto:")):
            continue
        found.add(item)

    # Backticked paths, only if they look like repository paths.
    for match in re.finditer(r"`([^`]+)`", text):
        item = match.group(1).strip()
        if "/" not in item:
            continue
        if item.startswith(("./", "../")):
            item = item[2:] if item.startswith("./") else item
        if any(ch.isspace() for ch in item):
            continue
        if item.endswith((".md", ".csv", ".py", ".v", ".xlsx", ".txt", ".json")) or "/" in item:
            found.add(item)

    cleaned: set[str] = set()

    for item in found:
        item = item.split("#", 1)[0]
        item = item.strip()
        if not item:
            continue
        if item.startswith(("http://", "https://")):
            continue
        cleaned.add(item)

    return cleaned


def check_doc_references(root: Path, issues: list[Issue]) -> None:
    docs = [
        "README.md",
        "REPRODUCE.md",
        "results/paper/README.md",
    ]

    for relative in docs:
        path = root / relative

        if not path.exists():
            continue

        text = read_text(path)
        refs = extract_markdown_paths(text)

        for ref in sorted(refs):
            # Skip command-like Makefile variables or globs.
            if "$" in ref or "*" in ref:
                continue

            target = (path.parent / ref).resolve() if not ref.startswith(("results/", "model/", "rtl/", "tb/", "doc/", "data/", "synth/")) else (root / ref).resolve()

            if not target.exists():
                issues.append(
                    Issue(
                        "WARN",
                        relative,
                        f"referenced path does not exist: {ref}",
                    )
                )


def check_forbidden_artifacts(root: Path, issues: list[Issue]) -> list[str]:
    found: list[str] = []

    for path in sorted(root.glob("results/**/*.vcd")):
        if path.is_file():
            relative = rel(path, root)
            found.append(relative)
            issues.append(
                Issue(
                    "WARN",
                    relative,
                    "VCD/debug waveform file should not remain in final repository state",
                )
            )

    transient_files = [
        "tb/fault_events.csv",
        "tb/control_levels.csv",
        "results/tables/strategy_comparison.csv",
        "results/tables/fault_events_meta.csv",
        "results/tables/event_shift_summary.md",
        "results/tables/control_policy_level_map.csv",
    ]

    for relative in transient_files:
        path = root / relative

        if path.exists():
            found.append(relative)
            issues.append(
                Issue(
                    "WARN",
                    relative,
                    "generated transient file exists; verify whether it is intentionally tracked",
                )
            )

    return sorted(set(found))


def write_report(
    *,
    root: Path,
    output: Path,
    required_rows: list[dict[str, str]],
    generic_counts: dict[str, int],
    interleaving_report: dict[str, str],
    forbidden: list[str],
    issues: list[Issue],
    git_status_text: str,
) -> None:
    failures = [item for item in issues if item.severity == "FAIL"]
    warnings = [item for item in issues if item.severity == "WARN"]
    status = "PASS" if not failures else "FAIL"

    lines: list[str] = []

    lines.append("# Repository results integrity check")
    lines.append("")
    lines.append("## Status")
    lines.append("")
    lines.append(f"- Status: `{status}`")
    lines.append(f"- Checked at UTC: `{datetime.now(timezone.utc).isoformat(timespec='seconds')}`")
    lines.append(f"- Failures: {len(failures)}")
    lines.append(f"- Warnings: {len(warnings)}")
    lines.append(f"- Repository root: `{root}`")
    lines.append("")

    lines.append("## Required files")
    lines.append("")
    lines.append("| File | Purpose | Status | Size, bytes |")
    lines.append("|---|---|---:|---:|")

    for row in required_rows:
        lines.append(
            f"| `{row['path']}` | {row['purpose']} | `{row['status']}` | {row['size']} |"
        )

    lines.append("")
    lines.append("## Generic results file checks")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---:|")

    for key, value in generic_counts.items():
        lines.append(f"| `{key}` | {value} |")

    lines.append("")
    lines.append("## Interleaving sweep matrix")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---|")

    for key, value in interleaving_report.items():
        lines.append(f"| `{key}` | `{value}` |")

    lines.append("")
    lines.append("## Forbidden or transient artifacts")
    lines.append("")

    if forbidden:
        for item in forbidden:
            lines.append(f"- `{item}`")
    else:
        lines.append("No forbidden/debug artifacts found.")

    lines.append("")
    lines.append("## Git status")
    lines.append("")
    lines.append("```")
    lines.append(git_status_text)
    lines.append("```")
    lines.append("")

    lines.append("## Failures")
    lines.append("")

    if failures:
        lines.append("| Path | Message |")
        lines.append("|---|---|")
        for item in failures:
            lines.append(f"| `{item.path}` | {item.message} |")
    else:
        lines.append("No failures.")

    lines.append("")
    lines.append("## Warnings")
    lines.append("")

    if warnings:
        lines.append("| Path | Message |")
        lines.append("|---|---|")
        for item in warnings:
            lines.append(f"| `{item.path}` | {item.message} |")
    else:
        lines.append("No warnings.")

    lines.append("")
    lines.append("## Interpretation")
    lines.append("")

    if failures:
        lines.append(
            "Найдены ошибки целостности. Не используйте этот отчёт как закрывающий аудит, "
            "пока failures не будут исправлены или явно обоснованы."
        )
    elif warnings:
        lines.append(
            "Критических ошибок нет, но есть предупреждения. Их нужно разобрать перед "
            "созданием чистовой ветки `dissertation-release`."
        )
    else:
        lines.append(
            "Критических ошибок и предупреждений не найдено. Текущие результаты проходят "
            "проверку целостности."
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/paper/repository_integrity_check.md"),
    )
    args = parser.parse_args()

    root = args.root.resolve()
    output = args.output

    issues: list[Issue] = []

    required_rows = check_required_files(root, issues)
    check_expected_sections(root, issues)
    generic_counts = check_all_md_csv(root, issues)
    interleaving_report = check_interleaving_matrix(root, issues)
    check_doc_references(root, issues)
    forbidden = check_forbidden_artifacts(root, issues)
    git_status_text = git_status(root)

    write_report(
        root=root,
        output=output,
        required_rows=required_rows,
        generic_counts=generic_counts,
        interleaving_report=interleaving_report,
        forbidden=forbidden,
        issues=issues,
        git_status_text=git_status_text,
    )

    failures = [item for item in issues if item.severity == "FAIL"]

    print(f"Wrote {output}")

    if failures:
        print(f"FAIL: {len(failures)} integrity failure(s)")
        raise SystemExit(1)

    print("PASS: no integrity failures")


if __name__ == "__main__":
    main()

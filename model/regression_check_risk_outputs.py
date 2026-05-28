#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import math
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ExpectedMetric:
    strategy: str
    metric: str
    expected: float
    rel_tol: float = 1e-8
    abs_tol: float = 1e-8


EXPECTED: list[ExpectedMetric] = [
    # fixed continuous
    ExpectedMetric("fixed_continuous_at_target", "E", 0.0100503358535, rel_tol=1e-10, abs_tol=1e-12),
    ExpectedMetric("fixed_continuous_at_target", "P_mission", 0.01, rel_tol=1e-10, abs_tol=1e-12),
    ExpectedMetric("fixed_continuous_at_target", "cycles", 17424471.3418, rel_tol=1e-8, abs_tol=1e-3),
    ExpectedMetric("fixed_continuous_at_target", "Pmax_per_cycle", 2.26938552698e-06, rel_tol=1e-8, abs_tol=1e-14),
    ExpectedMetric("fixed_continuous_at_target", "mean_tau_seconds", 9.05430052398, rel_tol=1e-8, abs_tol=1e-9),
    ExpectedMetric("fixed_continuous_at_target", "eta_gain_vs_fixed", 1.0, rel_tol=1e-12, abs_tol=1e-12),
    ExpectedMetric("fixed_continuous_at_target", "rho_loss_vs_ideal", 7.24295991773, rel_tol=1e-8, abs_tol=1e-9),

    # fixed allowed 5s
    ExpectedMetric("fixed_allowed_5s", "E", 0.00555003438801, rel_tol=1e-8, abs_tol=1e-12),
    ExpectedMetric("fixed_allowed_5s", "P_mission", 0.00553466140051, rel_tol=1e-8, abs_tol=1e-12),
    ExpectedMetric("fixed_allowed_5s", "cycles", 31553280.0, rel_tol=0.0, abs_tol=0.0),
    ExpectedMetric("fixed_allowed_5s", "Pmax_per_cycle", 6.92051603255e-07, rel_tol=1e-8, abs_tol=1e-14),
    ExpectedMetric("fixed_allowed_5s", "mean_tau_seconds", 5.0, rel_tol=0.0, abs_tol=0.0),
    ExpectedMetric("fixed_allowed_5s", "eta_gain_vs_fixed", 0.552223773306, rel_tol=1e-8, abs_tol=1e-10),
    ExpectedMetric("fixed_allowed_5s", "rho_loss_vs_ideal", 13.1159871557, rel_tol=1e-8, abs_tol=1e-9),

    # adaptive current continuous
    ExpectedMetric("adaptive_current_continuous", "c", 0.128842118041, rel_tol=1e-8, abs_tol=1e-12),
    ExpectedMetric("adaptive_current_continuous", "E", 0.0100503358535, rel_tol=1e-10, abs_tol=1e-12),
    ExpectedMetric("adaptive_current_continuous", "P_mission", 0.01, rel_tol=1e-10, abs_tol=1e-12),
    ExpectedMetric("adaptive_current_continuous", "cycles", 2405711.41352, rel_tol=1e-8, abs_tol=1e-4),
    ExpectedMetric("adaptive_current_continuous", "Pmax_per_cycle", 4.17769803851e-09, rel_tol=1e-8, abs_tol=1e-16),
    ExpectedMetric("adaptive_current_continuous", "mean_tau_seconds", 96.5657390135, rel_tol=1e-8, abs_tol=1e-8),
    ExpectedMetric("adaptive_current_continuous", "eta_gain_vs_fixed", 7.24295991773, rel_tol=1e-8, abs_tol=1e-9),
    ExpectedMetric("adaptive_current_continuous", "rho_loss_vs_ideal", 1.0, rel_tol=1e-12, abs_tol=1e-12),

    # adaptive current discrete
    ExpectedMetric("adaptive_current_discrete", "c", 0.127059554228, rel_tol=1e-8, abs_tol=1e-12),
    ExpectedMetric("adaptive_current_discrete", "E", 0.0100501809522, rel_tol=1e-8, abs_tol=1e-12),
    ExpectedMetric("adaptive_current_discrete", "P_mission", 0.00999984664774, rel_tol=1e-8, abs_tol=1e-12),
    ExpectedMetric("adaptive_current_discrete", "cycles", 2543790.0, rel_tol=0.0, abs_tol=0.0),
    ExpectedMetric("adaptive_current_discrete", "Pmax_per_cycle", 2.76820641302e-08, rel_tol=1e-8, abs_tol=1e-15),
    ExpectedMetric("adaptive_current_discrete", "mean_tau_seconds", 87.0203085068, rel_tol=1e-8, abs_tol=1e-8),
    ExpectedMetric("adaptive_current_discrete", "eta_gain_vs_fixed", 6.84980731184, rel_tol=1e-8, abs_tol=1e-9),
    ExpectedMetric("adaptive_current_discrete", "rho_loss_vs_ideal", 1.05739615554, rel_tol=1e-8, abs_tol=1e-9),

    # adaptive delayed
    ExpectedMetric("adaptive_delayed_1h_discrete", "c", 0.12090343247, rel_tol=1e-8, abs_tol=1e-12),
    ExpectedMetric("adaptive_delayed_1h_discrete", "E", 0.0100502237581, rel_tol=1e-8, abs_tol=1e-12),
    ExpectedMetric("adaptive_delayed_1h_discrete", "P_mission", 0.00999988902558, rel_tol=1e-8, abs_tol=1e-12),
    ExpectedMetric("adaptive_delayed_1h_discrete", "cycles", 2653530.0, rel_tol=0.0, abs_tol=0.0),
    ExpectedMetric("adaptive_delayed_1h_discrete", "Pmax_per_cycle", 1.58576414452e-06, rel_tol=1e-8, abs_tol=1e-14),
    ExpectedMetric("adaptive_delayed_1h_discrete", "mean_tau_seconds", 84.7550657174, rel_tol=1e-8, abs_tol=1e-8),
    ExpectedMetric("adaptive_delayed_1h_discrete", "eta_gain_vs_fixed", 6.56652509743, rel_tol=1e-8, abs_tol=1e-9),
    ExpectedMetric("adaptive_delayed_1h_discrete", "rho_loss_vs_ideal", 1.10301259955, rel_tol=1e-8, abs_tol=1e-9),

    # adaptive modified delayed
    ExpectedMetric("adaptive_modified_delayed_1h_discrete", "c", 0.125087686835, rel_tol=1e-8, abs_tol=1e-12),
    ExpectedMetric("adaptive_modified_delayed_1h_discrete", "E", 0.0100501474398, rel_tol=1e-8, abs_tol=1e-12),
    ExpectedMetric("adaptive_modified_delayed_1h_discrete", "P_mission", 0.00999981347043, rel_tol=1e-8, abs_tol=1e-12),
    ExpectedMetric("adaptive_modified_delayed_1h_discrete", "cycles", 2594580.0, rel_tol=0.0, abs_tol=0.0),
    ExpectedMetric("adaptive_modified_delayed_1h_discrete", "Pmax_per_cycle", 1.23947578455e-06, rel_tol=1e-8, abs_tol=1e-14),
    ExpectedMetric("adaptive_modified_delayed_1h_discrete", "mean_tau_seconds", 86.2632347572, rel_tol=1e-8, abs_tol=1e-8),
    ExpectedMetric("adaptive_modified_delayed_1h_discrete", "eta_gain_vs_fixed", 6.7157194389, rel_tol=1e-8, abs_tol=1e-9),
    ExpectedMetric("adaptive_modified_delayed_1h_discrete", "rho_loss_vs_ideal", 1.07850841353, rel_tol=1e-8, abs_tol=1e-9),
]


def read_rows(path: Path) -> dict[str, dict[str, float]]:
    with path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = {}

        for row in reader:
            strategy = row["strategy"]
            rows[strategy] = {}

            for key, value in row.items():
                if key == "strategy" or value == "":
                    continue

                rows[strategy][key] = float(value)

        return rows


def compare_value(expected: ExpectedMetric, actual: float) -> tuple[bool, float, float]:
    abs_error = abs(actual - expected.expected)

    if expected.expected != 0.0:
        rel_error = abs_error / abs(expected.expected)
    else:
        rel_error = 0.0 if abs_error == 0.0 else math.inf

    ok = abs_error <= expected.abs_tol or rel_error <= expected.rel_tol
    return ok, abs_error, rel_error


def write_md(path: Path, results: list[dict[str, object]], passed: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    lines.append("# Regression-check расчётных риск-результатов")
    lines.append("")
    lines.append("## Назначение")
    lines.append("")
    lines.append(
        "Проверяется, что общий модуль `risk_core.py` и расчётная проверка "
        "шкалы эффективности воспроизводят ранее зафиксированные численные "
        "результаты для стратегий статьи 3."
    )
    lines.append("")
    lines.append("## Итог")
    lines.append("")
    lines.append(f"- Статус: {'PASS' if passed else 'FAIL'}")
    lines.append(f"- Проверок: {len(results)}")
    lines.append(f"- Ошибок: {sum(1 for row in results if not row['ok'])}")
    lines.append("")
    lines.append("## Использование результатов")
    lines.append("")
    lines.append("Этот отчёт фиксирует, что каноническая расчётная цепочка на базе `risk_core.py` воспроизводит численные результаты, используемые для шкалы эффективности.")
    lines.append("")
    lines.append("Для текста диссертации следует использовать:")
    lines.append("")
    lines.append("- `results/paper/tables/efficiency_scale_verification.md` — основной отчёт по шкале эффективности;")
    lines.append("- `results/paper/tables/efficiency_scale_verification.csv` — машинно-читаемая таблица тех же расчётов;")
    lines.append("- `results/paper/tables/risk_regression_report.md` — регрессионное подтверждение воспроизводимости чисел.")
    lines.append("")
    lines.append("Старые или промежуточные риск-таблицы не следует цитировать напрямую, если они не включены в `doc/dissertation_mapping.md`.")
    lines.append("")
    lines.append("## Таблица проверок")
    lines.append("")
    lines.append(
        "| Стратегия | Метрика | Ожидалось | Получено | "
        "|abs err| | rel err | Статус |"
    )
    lines.append("|---|---|---:|---:|---:|---:|---|")

    for row in results:
        lines.append(
            f"| `{row['strategy']}` | `{row['metric']}` | "
            f"{row['expected']:.12g} | {row['actual']:.12g} | "
            f"{row['abs_error']:.3e} | {row['rel_error']:.3e} | "
            f"{'PASS' if row['ok'] else 'FAIL'} |"
        )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_csv(path: Path, results: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "strategy",
        "metric",
        "expected",
        "actual",
        "abs_error",
        "rel_error",
        "ok",
    ]

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--generated-csv",
        type=Path,
        default=Path("results/paper/tables/efficiency_scale_verification.csv"),
        help="CSV generated by verify_efficiency_scale.py.",
    )
    parser.add_argument(
        "--regenerate",
        action="store_true",
        help="Run verify_efficiency_scale.py before checking.",
    )
    parser.add_argument(
        "--csv-output",
        type=Path,
        default=Path("results/paper/tables/risk_regression_report.csv"),
    )
    parser.add_argument(
        "--md-output",
        type=Path,
        default=Path("results/paper/tables/risk_regression_report.md"),
    )

    args = parser.parse_args()

    if args.regenerate:
        command = [
            sys.executable,
            "model/verify_efficiency_scale.py",
            "--input",
            "data/upsets.xlsx",
            "--start-index",
            "0",
            "--window-size",
            "43824",
            "--target-pmission",
            "0.01",
            "--intervals-seconds",
            "1,2,5,10,30,60,120,300,600,1200,1800,3600",
            "--csv-output",
            str(args.generated_csv),
            "--md-output",
            "results/paper/tables/efficiency_scale_verification.md",
        ]
        subprocess.run(command, check=True)

    if not args.generated_csv.exists():
        raise FileNotFoundError(
            f"Generated CSV not found: {args.generated_csv}. "
            "Run verify_efficiency_scale.py first or use --regenerate."
        )

    rows = read_rows(args.generated_csv)

    results: list[dict[str, object]] = []
    passed = True

    for expected in EXPECTED:
        if expected.strategy not in rows:
            raise KeyError(f"Missing strategy in generated CSV: {expected.strategy}")

        if expected.metric not in rows[expected.strategy]:
            raise KeyError(
                f"Missing metric {expected.metric} for strategy {expected.strategy}"
            )

        actual = rows[expected.strategy][expected.metric]
        ok, abs_error, rel_error = compare_value(expected, actual)
        passed = passed and ok

        results.append(
            {
                "strategy": expected.strategy,
                "metric": expected.metric,
                "expected": expected.expected,
                "actual": actual,
                "abs_error": abs_error,
                "rel_error": rel_error,
                "ok": ok,
            }
        )

    write_csv(args.csv_output, results)
    write_md(args.md_output, results, passed)

    print(f"CSV: {args.csv_output}")
    print(f"MD:  {args.md_output}")
    print(args.md_output.read_text(encoding="utf-8"))

    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

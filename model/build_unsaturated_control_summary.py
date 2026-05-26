#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import re
from collections import defaultdict
from pathlib import Path
from statistics import mean, stdev


DEPTH = 256


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(path)

    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def busy_percent(row: dict[str, str]) -> float:
    return float(row["busy_per_mille"]) / 10.0


def summarize_strategy_series(path: Path) -> dict[str, dict[str, float]]:
    rows = read_csv(path)
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)

    for row in rows:
        grouped[row["strategy"]].append(row)

    result: dict[str, dict[str, float]] = {}

    for strategy, items in grouped.items():
        unique = [float(row["unique_uncorrectable_words"]) for row in items]
        busy = [busy_percent(row) for row in items]
        scrub = [float(row["scrub_cycles"]) for row in items]
        corrected = [float(row["corrected"]) for row in items]
        detections = [float(row["uncorrectable_detections"]) for row in items]

        result[strategy] = {
            "runs": float(len(items)),
            "unique_mean": mean(unique),
            "unique_std": stdev(unique) if len(unique) > 1 else 0.0,
            "unique_min": min(unique),
            "unique_max": max(unique),
            "busy_mean": mean(busy),
            "busy_std": stdev(busy) if len(busy) > 1 else 0.0,
            "scrub_mean": mean(scrub),
            "corrected_mean": mean(corrected),
            "detections_mean": mean(detections),
        }

    return result


def read_paired_delta(path: Path) -> dict[tuple[str, str, str], dict[str, float]]:
    rows = read_csv(path)
    result: dict[tuple[str, str, str], dict[str, float]] = {}

    for row in rows:
        key = (row["scenario"], row["comparison"], row["metric"])
        result[key] = {
            "fixed_mean": float(row["fixed_mean"]),
            "adaptive_mean": float(row["adaptive_mean"]),
            "delta_mean": float(row["delta_mean"]),
            "ci95_low": float(row["ci95_low"]),
            "ci95_high": float(row["ci95_high"]),
            "relative_percent": float(row["relative_percent"]),
        }

    return result


def read_fixed_grid_summary(path: Path) -> tuple[list[dict[str, float | str]], list[dict[str, float | str]]]:
    rows = read_csv(path)

    adaptive: list[dict[str, float | str]] = []
    fixed: list[dict[str, float | str]] = []

    for row in rows:
        item = {
            "name": row["name"],
            "runs": float(row["runs"]),
            "unique_mean": float(row["unique_mean"]),
            "unique_std": float(row["unique_std"]),
            "busy_mean": float(row["busy_mean"]),
            "busy_std": float(row["busy_std"]),
            "scrub_mean": float(row["scrub_mean"]),
        }

        if row["kind"] == "adaptive":
            adaptive.append(item)
        elif row["kind"] == "fixed":
            fixed.append(item)

    return adaptive, fixed


def pareto_rows(
    adaptive: list[dict[str, float | str]],
    fixed: list[dict[str, float | str]],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []

    for adaptive_item in adaptive:
        dominating = []

        for fixed_item in fixed:
            if (
                float(fixed_item["unique_mean"]) <= float(adaptive_item["unique_mean"])
                and float(fixed_item["busy_mean"]) <= float(adaptive_item["busy_mean"])
            ):
                dominating.append(str(fixed_item["name"]))

        nearest = min(
            fixed,
            key=lambda item: abs(float(item["busy_mean"]) - float(adaptive_item["busy_mean"])),
        )

        rows.append(
            {
                "strategy": adaptive_item["name"],
                "adaptive_unique": float(adaptive_item["unique_mean"]),
                "adaptive_busy": float(adaptive_item["busy_mean"]),
                "nearest_fixed": nearest["name"],
                "nearest_fixed_unique": float(nearest["unique_mean"]),
                "nearest_fixed_busy": float(nearest["busy_mean"]),
                "dominating": dominating,
            }
        )

    return rows


def read_calibration(path: Path) -> dict[str, str]:
    rows = read_csv(path)
    out: dict[str, str] = {}

    for row in rows:
        if row["section"] == "pass_duration":
            out[f"{row['name']}.{row['metric']}"] = row["value"]

    return out


def parse_shift_summary(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")

    def find(pattern: str, default: str = "") -> str:
        match = re.search(pattern, text)
        return match.group(1) if match else default

    return {
        "total": find(r"Всего событий: ([0-9]+)"),
        "shifted": find(r"Событий со сдвигом: ([0-9]+)"),
        "shift_percent": find(r"Доля событий со сдвигом, %: ([0-9.]+)"),
        "max_abs_shift": find(r"Максимальный \|сдвиг\|, тактов: ([0-9.]+)"),
    }


def add_strategy_table(lines: list[str], title: str, summary: dict[str, dict[str, float]]) -> None:
    lines.append(f"## {title}")
    lines.append("")
    lines.append(
        "| Стратегия | Прогонов | unique mean ± σ | unique max / DEPTH, % | "
        "busy mean, % | scrub cycles mean | corrected mean | detections mean |"
    )
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|")

    for strategy in ["fixed", "table", "threshold"]:
        item = summary[strategy]
        lines.append(
            f"| `{strategy}` | {int(item['runs'])} | "
            f"{item['unique_mean']:.3f} ± {item['unique_std']:.3f} | "
            f"{item['unique_max'] / DEPTH * 100.0:.2f} | "
            f"{item['busy_mean']:.3f} | "
            f"{item['scrub_mean']:.1f} | "
            f"{item['corrected_mean']:.1f} | "
            f"{item['detections_mean']:.1f} |"
        )

    lines.append("")


def add_delta_table(
    lines: list[str],
    title: str,
    scenario: str,
    deltas: dict[tuple[str, str, str], dict[str, float]],
) -> None:
    lines.append(f"## {title}")
    lines.append("")
    lines.append("| Сравнение | Δ busy, % | Δ busy, 95% CI | Δ unique | Δ unique, 95% CI |")
    lines.append("|---|---:|---:|---:|---:|")

    for comparison in ["table-fixed", "threshold-fixed"]:
        busy = deltas[(scenario, comparison, "busy_percent")]
        unique = deltas[(scenario, comparison, "unique_uncorrectable_words")]

        lines.append(
            f"| `{comparison}` | "
            f"{busy['delta_mean']:.3f} | "
            f"[{busy['ci95_low']:.3f}; {busy['ci95_high']:.3f}] | "
            f"{unique['delta_mean']:.3f} | "
            f"[{unique['ci95_low']:.3f}; {unique['ci95_high']:.3f}] |"
        )

    lines.append("")


def add_pareto_table(lines: list[str], title: str, rows: list[dict[str, object]]) -> None:
    lines.append(f"## {title}")
    lines.append("")
    lines.append(
        "| Adaptive | adaptive unique | adaptive busy, % | nearest fixed | "
        "nearest fixed unique | nearest fixed busy, % | dominating fixed intervals |"
    )
    lines.append("|---|---:|---:|---:|---:|---:|---|")

    for row in rows:
        dominating = row["dominating"]
        assert isinstance(dominating, list)

        lines.append(
            f"| `{row['strategy']}` | "
            f"{row['adaptive_unique']:.3f} | "
            f"{row['adaptive_busy']:.3f} | "
            f"{row['nearest_fixed']} | "
            f"{row['nearest_fixed_unique']:.3f} | "
            f"{row['nearest_fixed_busy']:.3f} | "
            f"{', '.join(dominating) if dominating else 'none'} |"
        )

    lines.append("")


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--base-dir",
        type=Path,
        default=Path("results/paper/unsaturated_control"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/paper/unsaturated_control/unsaturated_control_summary.md"),
    )

    args = parser.parse_args()
    base = args.base_dir

    calibration = read_calibration(base / "pass_duration_calibration.csv")

    no_summary = summarize_strategy_series(base / "no_clusters/strategy_comparison_series.csv")
    with_summary = summarize_strategy_series(base / "with_clusters/strategy_comparison_series.csv")
    deltas = read_paired_delta(base / "paired_delta_analysis.csv")

    no_adaptive, no_fixed = read_fixed_grid_summary(base / "fixed_grid_no_clusters/fixed_grid_summary.csv")
    with_adaptive, with_fixed = read_fixed_grid_summary(base / "fixed_grid_with_clusters/fixed_grid_summary.csv")

    no_pareto = pareto_rows(no_adaptive, no_fixed)
    with_pareto = pareto_rows(with_adaptive, with_fixed)

    no_shift = parse_shift_summary(base / "no_clusters/event_shift_summary_last_seed.md")
    with_shift = parse_shift_summary(base / "with_clusters/event_shift_summary_last_seed.md")

    lines: list[str] = []

    lines.append("# Итоговая сводка контрольной серии вне насыщения")
    lines.append("")
    lines.append("## Назначение")
    lines.append("")
    lines.append(
        "Контрольная серия проверяет, сохраняются ли выводы о снижении занятости "
        "интерфейса памяти после выхода из насыщенного режима 16-словного стенда. "
        "Для этого используется модельная память DEPTH=256 и масштабированные "
        "интервалы полного прохода."
    )
    lines.append("")
    lines.append("## Калибровка полного прохода")
    lines.append("")
    lines.append("| ADDR_WIDTH | DEPTH | Tpass, тактов |")
    lines.append("|---:|---:|---:|")
    lines.append(
        f"| 4 | 16 | {calibration['addr_width_4.pass_duration_mode']} |"
    )
    lines.append(
        f"| 8 | 256 | {calibration['addr_width_8.pass_duration_mode']} |"
    )
    lines.append("")
    lines.append(
        "Использованная шкала для DEPTH=256: "
        "`table = 1866,1788,1710,1633,1555,1400,1244,1089`, "
        "`threshold = 2021,1555,1244`, `fixed = 1244`."
    )
    lines.append("")

    add_strategy_table(lines, "Серия без мгновенных кластеров", no_summary)
    add_strategy_table(lines, "Серия с мгновенными двухбитовыми кластерами", with_summary)

    lines.append("## Вклад мгновенных кластеров")
    lines.append("")
    lines.append("| Стратегия | unique без кластеров | unique с кластерами | Прибавка |")
    lines.append("|---|---:|---:|---:|")
    for strategy in ["fixed", "table", "threshold"]:
        a = no_summary[strategy]["unique_mean"]
        b = with_summary[strategy]["unique_mean"]
        lines.append(f"| `{strategy}` | {a:.3f} | {b:.3f} | {b - a:.3f} |")
    lines.append("")

    add_delta_table(lines, "Paired-delta без мгновенных кластеров", "no_clusters", deltas)
    add_delta_table(lines, "Paired-delta с мгновенными кластерами", "with_clusters", deltas)

    add_pareto_table(lines, "Fixed-grid Pareto без мгновенных кластеров", no_pareto)
    add_pareto_table(lines, "Fixed-grid Pareto с мгновенными кластерами", with_pareto)

    lines.append("## Сдвиги событий")
    lines.append("")
    lines.append("| Сценарий | Всего событий | Со сдвигом | Доля, % | Максимальный |сдвиг|, тактов |")
    lines.append("|---|---:|---:|---:|---:|")
    lines.append(
        f"| `no_clusters` | {no_shift['total']} | {no_shift['shifted']} | "
        f"{no_shift['shift_percent']} | {no_shift['max_abs_shift']} |"
    )
    lines.append(
        f"| `with_clusters` | {with_shift['total']} | {with_shift['shifted']} | "
        f"{with_shift['shift_percent']} | {with_shift['max_abs_shift']} |"
    )
    lines.append("")

    lines.append("## Итоговая интерпретация")
    lines.append("")
    lines.append(
        "Контрольная серия показывает, что на увеличенной модельной памяти вывод "
        "становится более строгим, чем на малом 16-словном стенде. Адаптивные "
        "стратегии уменьшают занятость памяти на 31–38 %, но это сопровождается "
        "статистически значимым увеличением среднего числа уникальных "
        "неустранимых слов."
    )
    lines.append("")
    lines.append(
        "При этом сравнение с плотной сеткой постоянных интервалов показывает, "
        "что adaptive-точки не доминируются: в рассмотренной сетке нет "
        "постоянного интервала, который одновременно имел бы не большую "
        "занятость и не большее число уникальных неустранимых слов."
    )
    lines.append("")
    lines.append(
        "Мгновенные двухбитовые кластеры добавляют близкую по величине нижнюю "
        "границу риска для всех стратегий. Поэтому они должны рассматриваться "
        "отдельно от накопительных ошибок, зависящих от интервала циклического "
        "восстановления."
    )
    lines.append("")
    lines.append(
        "Эта серия является методической контрольной проверкой вне насыщения, "
        "а не физической аппаратной проекцией целевого массива. Физическая "
        "проекция секундных интервалов и занятости интерфейса оценивается "
        "отдельно."
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(args.output.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()

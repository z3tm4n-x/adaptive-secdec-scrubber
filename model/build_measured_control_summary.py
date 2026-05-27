#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import math
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, stdev


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(path)

    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def pearson(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) != len(ys) or len(xs) < 2:
        return None

    mx = mean(xs)
    my = mean(ys)

    dx = [x - mx for x in xs]
    dy = [y - my for y in ys]

    sx = math.sqrt(sum(x * x for x in dx))
    sy = math.sqrt(sum(y * y for y in dy))

    if sx == 0.0 or sy == 0.0:
        return None

    return sum(x * y for x, y in zip(dx, dy)) / (sx * sy)


def summarize_observable_windows(path: Path) -> list[dict[str, object]]:
    rows = read_csv(path)
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)

    for row in rows:
        grouped[row["strategy"]].append(row)

    out: list[dict[str, object]] = []

    for strategy in ["fixed", "table", "threshold"]:
        items = grouped[strategy]

        corrected_total = sum(float(row["corrected_delta"]) for row in items)
        true_total = sum(float(row["true_total_events"]) for row in items)

        corrected_rate = [float(row["corrected_per_100k_cycles"]) for row in items]
        uncorr_rate = [float(row["uncorrectable_detections_per_100k_cycles"]) for row in items]
        true_events = [float(row["true_total_events"]) for row in items]
        true_single = [float(row["true_single_events"]) for row in items]

        out.append(
            {
                "strategy": strategy,
                "windows": len(items),
                "corrected_total": corrected_total,
                "true_total": true_total,
                "corrected_rate_mean": mean(corrected_rate),
                "corrected_rate_max": max(corrected_rate),
                "uncorr_rate_mean": mean(uncorr_rate),
                "uncorr_rate_max": max(uncorr_rate),
                "corr_true_total": pearson(corrected_rate, true_events),
                "corr_true_single": pearson(corrected_rate, true_single),
            }
        )

    return out


def summarize_measured_schedule(path: Path, name: str) -> dict[str, object]:
    rows = read_csv(path)
    levels = [int(row["measured_level"]) for row in rows]
    scores = [float(row["measured_score"]) for row in rows]
    corrected_rates = [float(row["corrected_per_100k_cycles"]) for row in rows]
    uncorr_rates = [float(row["uncorrectable_detections_per_100k_cycles"]) for row in rows]

    level_counts = Counter(levels)

    return {
        "name": name,
        "windows": len(rows),
        "mean_score": mean(scores),
        "max_score": max(scores),
        "mean_corrected_rate": mean(corrected_rates),
        "max_corrected_rate": max(corrected_rates),
        "mean_uncorr_rate": mean(uncorr_rates),
        "max_uncorr_rate": max(uncorr_rates),
        "level_counts": level_counts,
    }


def read_multiseed_summary(path: Path) -> dict[tuple[str, str, str], dict[str, float]]:
    rows = read_csv(path)
    out: dict[tuple[str, str, str], dict[str, float]] = {}

    for row in rows:
        key = (row["kind"], row["name"], row["metric"])
        out[key] = {
            "n": float(row["n"]),
            "mean": float(row["mean"]),
            "std": float(row["std"]),
            "ci95_low": float(row["ci95_low"]),
            "ci95_high": float(row["ci95_high"]),
        }

    return out


def read_weight_summary(path: Path) -> dict[tuple[str, str], dict[str, float]]:
    rows = read_csv(path)
    out: dict[tuple[str, str], dict[str, float]] = {}

    for row in rows:
        key = (row["replay_name"], row["metric"])
        out[key] = {
            "n": float(row["n"]),
            "mean": float(row["mean"]),
            "std": float(row["std"]),
            "ci95_low": float(row["ci95_low"]),
            "ci95_high": float(row["ci95_high"]),
        }

    return out


def read_delta_summary(path: Path) -> dict[tuple[str, str], dict[str, float]]:
    rows = read_csv(path)
    out: dict[tuple[str, str], dict[str, float]] = {}

    for row in rows:
        key = (row["comparison"], row["metric"])
        out[key] = {
            "n": float(row["n"]),
            "lhs_mean": float(row["lhs_mean"]),
            "rhs_mean": float(row["rhs_mean"]),
            "delta_mean": float(row["delta_mean"]),
            "delta_std": float(row["delta_std"]),
            "ci95_low": float(row["ci95_low"]),
            "ci95_high": float(row["ci95_high"]),
        }

    return out


def busy(row: dict[str, str]) -> float:
    return float(row["busy_percent"])


def add_observable_section(lines: list[str], observable_rows: list[dict[str, object]]) -> None:
    lines.append("## 1. Наблюдаемый сигнал по счётчикам")
    lines.append("")
    lines.append(
        "Сначала из трассы RTL извлекается сигнал, доступный бортовой системе: "
        "приращения `corrected_error_count` и `uncorrectable_error_count` по окнам. "
        "Истинные события используются только для диагностической проверки корреляции."
    )
    lines.append("")
    lines.append("| strategy | windows | corrected total | true total events | mean corrected / 100k | max corrected / 100k | mean DED detections / 100k | corr(corrected, true total) |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|")

    for row in observable_rows:
        corr = row["corr_true_total"]
        corr_text = f"{corr:.3f}" if corr is not None else "nan"

        lines.append(
            f"| `{row['strategy']}` | "
            f"{row['windows']} | "
            f"{row['corrected_total']:.0f} | "
            f"{row['true_total']:.0f} | "
            f"{row['corrected_rate_mean']:.3f} | "
            f"{row['corrected_rate_max']:.3f} | "
            f"{row['uncorr_rate_mean']:.3f} | "
            f"{corr_text} |"
        )

    lines.append("")
    lines.append(
        "Вывод: `corrected_error_count` даёт наблюдаемый временной сигнал, "
        "но он эндогенен — его величина зависит от выбранной стратегии восстановления. "
        "`uncorrectable_error_count` служит дополнительным индикатором недооценки опасного окна."
    )
    lines.append("")


def add_schedule_section(lines: list[str], weighted: dict[str, object], corrected_only: dict[str, object]) -> None:
    lines.append("## 2. Построение measured level schedule")
    lines.append("")
    lines.append(
        "По наблюдаемым окнам строятся два расписания 3-битного управляющего уровня: "
        "`corrected-only` и `weighted`, где в score добавлен штраф за обнаруженные DED-состояния."
    )
    lines.append("")
    lines.append("Формула:")
    lines.append("")
    lines.append("```text")
    lines.append("score = corrected_per_100k_cycles + w · uncorrectable_detections_per_100k_cycles")
    lines.append("level = round(score / rate_max · 7)")
    lines.append("```")
    lines.append("")
    lines.append("| schedule | windows | mean score | max score | level 0 | level 1 | level 2 | level 3 | level 4 | level 5 | level 6 | level 7 |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")

    for item in [weighted, corrected_only]:
        counts: Counter[int] = item["level_counts"]  # type: ignore[assignment]

        lines.append(
            f"| `{item['name']}` | "
            f"{item['windows']} | "
            f"{item['mean_score']:.3f} | "
            f"{item['max_score']:.3f} | "
            f"{counts.get(0, 0)} | "
            f"{counts.get(1, 0)} | "
            f"{counts.get(2, 0)} | "
            f"{counts.get(3, 0)} | "
            f"{counts.get(4, 0)} | "
            f"{counts.get(5, 0)} | "
            f"{counts.get(6, 0)} | "
            f"{counts.get(7, 0)} |"
        )

    lines.append("")
    lines.append(
        "Для одиночного seed выбранный вес `w=0.50` переводит большую часть окон "
        "в уровни 6–7, тогда как `corrected-only` не достигает уровня 7."
    )
    lines.append("")


def add_single_replay_section(lines: list[str], path: Path) -> None:
    rows = read_csv(path)

    lines.append("## 3. Single-seed RTL replay")
    lines.append("")
    lines.append(
        "Далее measured schedule подаётся обратно в RTL как внешний `control_levels.csv`. "
        "События остаются теми же, меняется только управляющее расписание."
    )
    lines.append("")
    lines.append("| kind | name | scrub cycles | corrected | DED detections | unique uncorrectable words | busy, % | switches |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|")

    for row in rows:
        lines.append(
            f"| `{row['kind']}` | `{row['name']}` | "
            f"{row['scrub_cycles']} | "
            f"{row['corrected']} | "
            f"{row['uncorrectable_detections']} | "
            f"{row['unique_uncorrectable_words']} | "
            f"{float(row['busy_percent']):.3f} | "
            f"{row['interval_switches']} |"
        )

    lines.append("")
    lines.append(
        "На одном seed выбранный `w=0.50` демонстрирует ожидаемую реакцию measured-control: "
        "увеличивает частоту проходов и снижает риск-метрики относительно corrected-only. "
        "Основной вывод далее делается не по этому seed, а по multi-seed sweep."
    )
    lines.append("")


def add_multiseed_section(lines: list[str], summary: dict[tuple[str, str, str], dict[str, float]]) -> None:
    lines.append("## 4. Multi-seed measured replay")
    lines.append("")
    lines.append("Серия replay выполнена для seed 1…10.")
    lines.append("")
    lines.append("| kind | name | busy, % | scrub cycles | corrected | DED detections | unique uncorrectable words |")
    lines.append("|---|---|---:|---:|---:|---:|---:|")

    ordered = [
        ("reference", "risk_policy_fixed"),
        ("reference", "risk_policy_table"),
        ("reference", "risk_policy_threshold"),
        ("measured_replay", "measured_table_weighted"),
        ("measured_replay", "measured_table_corrected_only"),
    ]

    for kind, name in ordered:
        busy_item = summary[(kind, name, "busy_percent")]
        scrub_item = summary[(kind, name, "scrub_cycles")]
        corrected_item = summary[(kind, name, "corrected")]
        ded_item = summary[(kind, name, "uncorrectable_detections")]
        unique_item = summary[(kind, name, "unique_uncorrectable_words")]

        lines.append(
            f"| `{kind}` | `{name}` | "
            f"{busy_item['mean']:.3f} ± {busy_item['std']:.3f} | "
            f"{scrub_item['mean']:.1f} ± {scrub_item['std']:.1f} | "
            f"{corrected_item['mean']:.1f} ± {corrected_item['std']:.1f} | "
            f"{ded_item['mean']:.1f} ± {ded_item['std']:.1f} | "
            f"{unique_item['mean']:.3f} ± {unique_item['std']:.3f} |"
        )

    lines.append("")
    lines.append(
        "Для `w=0.25` рост занятости относительно corrected-only устойчив, "
        "но снижение риск-метрик статистически недостаточно выражено. Поэтому была выполнена калибровка веса."
    )
    lines.append("")


def add_weight_sweep_section(
    lines: list[str],
    weight_summary: dict[tuple[str, str], dict[str, float]],
    deltas: dict[tuple[str, str], dict[str, float]],
) -> None:
    lines.append("## 5. Weight sweep measured-control")
    lines.append("")
    lines.append("Проверены веса `w = 0.00, 0.10, 0.25, 0.50, 0.75, 1.00`.")
    lines.append("")
    lines.append("| replay | busy, % | scrub cycles | corrected | DED detections | unique uncorrectable words |")
    lines.append("|---|---:|---:|---:|---:|---:|")

    replay_names = [
        "measured_table_w0p00",
        "measured_table_w0p10",
        "measured_table_w0p25",
        "measured_table_w0p50",
        "measured_table_w0p75",
        "measured_table_w1p00",
    ]

    for name in replay_names:
        busy_item = weight_summary[(name, "busy_percent")]
        scrub_item = weight_summary[(name, "scrub_cycles")]
        corrected_item = weight_summary[(name, "corrected")]
        ded_item = weight_summary[(name, "uncorrectable_detections")]
        unique_item = weight_summary[(name, "unique_uncorrectable_words")]

        lines.append(
            f"| `{name}` | "
            f"{busy_item['mean']:.3f} ± {busy_item['std']:.3f} | "
            f"{scrub_item['mean']:.1f} ± {scrub_item['std']:.1f} | "
            f"{corrected_item['mean']:.1f} ± {corrected_item['std']:.1f} | "
            f"{ded_item['mean']:.1f} ± {ded_item['std']:.1f} | "
            f"{unique_item['mean']:.3f} ± {unique_item['std']:.3f} |"
        )

    lines.append("")
    lines.append("### Paired-delta относительно corrected-only")
    lines.append("")
    lines.append("| replay | Δ busy, п.п. | Δ DED detections | Δ unique |")
    lines.append("|---|---:|---:|---:|")

    for name in replay_names:
        if name == "measured_table_w0p00":
            continue

        comparison = f"{name} - measured_table_w0p00"
        busy_delta = deltas[(comparison, "busy_percent")]
        ded_delta = deltas[(comparison, "uncorrectable_detections")]
        unique_delta = deltas[(comparison, "unique_uncorrectable_words")]

        lines.append(
            f"| `{name}` | "
            f"{busy_delta['delta_mean']:.3f} [{busy_delta['ci95_low']:.3f}; {busy_delta['ci95_high']:.3f}] | "
            f"{ded_delta['delta_mean']:.1f} [{ded_delta['ci95_low']:.1f}; {ded_delta['ci95_high']:.1f}] | "
            f"{unique_delta['delta_mean']:.3f} [{unique_delta['ci95_low']:.3f}; {unique_delta['ci95_high']:.3f}] |"
        )

    lines.append("")
    lines.append("### Paired-delta относительно `risk_policy_fixed`")
    lines.append("")
    lines.append("| replay | Δ busy, п.п. | Δ DED detections | Δ unique |")
    lines.append("|---|---:|---:|---:|")

    for name in replay_names:
        comparison = f"{name} - risk_policy_fixed"
        busy_delta = deltas[(comparison, "busy_percent")]
        ded_delta = deltas[(comparison, "uncorrectable_detections")]
        unique_delta = deltas[(comparison, "unique_uncorrectable_words")]

        lines.append(
            f"| `{name}` | "
            f"{busy_delta['delta_mean']:.3f} [{busy_delta['ci95_low']:.3f}; {busy_delta['ci95_high']:.3f}] | "
            f"{ded_delta['delta_mean']:.1f} [{ded_delta['ci95_low']:.1f}; {ded_delta['ci95_high']:.1f}] | "
            f"{unique_delta['delta_mean']:.3f} [{unique_delta['ci95_low']:.3f}; {unique_delta['ci95_high']:.3f}] |"
        )

    lines.append("")
    lines.append(
        "Лучшей рабочей точкой из проверенной сетки является `w=0.50`: "
        "относительно corrected-only она статистически значимо увеличивает занятость, "
        "но также статистически значимо снижает `DED detections` и `unique_uncorrectable_words`."
    )
    lines.append("")
    lines.append(
        "Относительно `risk_policy_fixed` режим `w=0.50` имеет статистически сопоставимые "
        "риск-метрики и меньшую среднюю занятость, но доверительные интервалы по дельтам включают ноль. "
        "Поэтому корректная формулировка — не превосходство над fixed, а сопоставимость с fixed "
        "при меньшей средней занятости."
    )
    lines.append("")


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/paper/measured_control/measured_control_summary.md"),
    )

    args = parser.parse_args()

    observable_rows = summarize_observable_windows(
        Path("results/paper/observable_signal/no_clusters_seed1/observable_signal_windows.csv")
    )

    weighted_schedule = summarize_measured_schedule(
        Path("results/paper/measured_control/no_clusters_weight_sweep/seed_0001/w0p50/measured_level_windows_table_w0p50.csv"),
        "selected weighted w0.50",
    )

    corrected_schedule = summarize_measured_schedule(
        Path("results/paper/measured_control/no_clusters_weight_sweep/seed_0001/w0p00/measured_level_windows_table_w0p00.csv"),
        "corrected-only w0.00",
    )

    multiseed = read_multiseed_summary(
        Path("results/paper/measured_control/no_clusters_multiseed/measured_replay_series_summary.csv")
    )

    weight_summary = read_weight_summary(
        Path("results/paper/measured_control/no_clusters_weight_sweep/measured_weight_sweep_summary.csv")
    )

    deltas = read_delta_summary(
        Path("results/paper/measured_control/no_clusters_weight_sweep/measured_weight_sweep_deltas.csv")
    )

    lines: list[str] = []

    lines.append("# Итоговая сводка measured-control")
    lines.append("")
    lines.append("## Назначение")
    lines.append("")
    lines.append(
        "Этот отчёт объединяет результаты по реализуемому управляющему сигналу: "
        "извлечение наблюдаемого сигнала из RTL-трассы, построение measured schedule, "
        "offline replay в RTL, multi-seed проверку и калибровку веса `uncorrectable_error_count`."
    )
    lines.append("")
    lines.append(
        "Важно: это **offline replay**, а не полностью замкнутый аппаратный контур. "
        "Расписание строится по ранее снятой трассе и затем подаётся в RTL как внешний `ctrl_level`. "
        "Тем не менее построение расписания не использует истинный ряд ν(t), а опирается только "
        "на наблюдаемые счётчики исполнения."
    )
    lines.append("")

    add_observable_section(lines, observable_rows)
    add_schedule_section(lines, weighted_schedule, corrected_schedule)
    add_single_replay_section(
        lines,
        Path("results/paper/measured_control/no_clusters_weight_sweep/seed1_selected_replay_comparison.csv"),
    )
    add_multiseed_section(lines, multiseed)
    add_weight_sweep_section(lines, weight_summary, deltas)

    lines.append("## 6. Итоговая интерпретация")
    lines.append("")
    lines.append(
        "Блок measured-control показывает, что управляющий сигнал можно строить не только "
        "по идеальному внешнему ряду, но и по наблюдаемым счётчикам исполнения. "
        "Один только `corrected_error_count` недооценивает опасные участки, потому что "
        "при недостаточной частоте восстановления часть ошибок переходит в неустранимые состояния "
        "и перестаёт попадать в счётчик исправлений."
    )
    lines.append("")
    lines.append(
        "Добавление `uncorrectable_error_count` как штрафного индикатора является методически оправданным. "
        "При `w=0.50` оно статистически значимо снижает риск-метрики относительно corrected-only, "
        "ценой роста занятости интерфейса памяти."
    )
    lines.append("")
    lines.append(
        "Этот блок закрывает каузальную трещину между идеальной risk-policy и реализуемым входным сигналом "
        "на уровне replay-модели. Полностью аппаратное замыкание оценивателя в RTL остаётся отдельным "
        "инженерным этапом."
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(args.output.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()

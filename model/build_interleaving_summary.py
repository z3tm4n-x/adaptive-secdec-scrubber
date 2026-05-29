#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
from pathlib import Path


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(path)

    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def busy_percent_from_per_mille(row: dict[str, str]) -> float:
    return float(row["busy_per_mille"]) / 10.0


def read_smoke_results(base: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []

    for depth in [1, 2, 3]:
        path = base / "smoke" / f"strategy_comparison_D{depth}.csv"
        for row in read_csv(path):
            rows.append(
                {
                    "D": depth,
                    "strategy": row["strategy"],
                    "scrub_cycles": int(row["scrub_cycles"]),
                    "corrected": int(row["corrected"]),
                    "uncorrectable_detections": int(row["uncorrectable_detections"]),
                    "unique_uncorrectable_words": int(row["unique_uncorrectable_words"]),
                    "new_due_count": int(row.get("new_due_count", row["unique_uncorrectable_words"])),
                    "repeated_due_detections": int(row.get("repeated_due_detections", "0")),
                    "busy_percent": busy_percent_from_per_mille(row),
                }
            )

    return rows


def read_interval_summary(path: Path) -> list[dict[str, object]]:
    rows = []

    for row in read_csv(path):
        rows.append(
            {
                "D": int(row["interleave_depth"]),
                "fixed_interval": int(row["fixed_interval"]),
                "runs": int(row["runs"]),
                "busy_mean": float(row["busy_percent_mean"]),
                "busy_std": float(row["busy_percent_std"]),
                "scrub_mean": float(row["scrub_cycles_mean"]),
                "scrub_std": float(row["scrub_cycles_std"]),
                "corrected_mean": float(row["corrected_mean"]),
                "corrected_std": float(row["corrected_std"]),
                "ded_mean": float(row["uncorrectable_detections_mean"]),
                "ded_std": float(row["uncorrectable_detections_std"]),
                "unique_mean": float(row["unique_uncorrectable_words_mean"]),
                "unique_std": float(row["unique_uncorrectable_words_std"]),
                "new_due_mean": float(row.get("new_due_count_mean", row["unique_uncorrectable_words_mean"])),
                "new_due_std": float(row.get("new_due_count_std", row["unique_uncorrectable_words_std"])),
                "repeated_mean": float(row.get("repeated_due_detections_mean", "0")),
                "repeated_std": float(row.get("repeated_due_detections_std", "0")),
            }
        )

    return rows


def read_deltas(path: Path) -> list[dict[str, object]]:
    rows = []

    for row in read_csv(path):
        rows.append(
            {
                "comparison": row["comparison"],
                "lhs_depth": int(row["lhs_depth"]),
                "lhs_interval": int(row["lhs_interval"]),
                "rhs_depth": int(row["rhs_depth"]),
                "rhs_interval": int(row["rhs_interval"]),
                "metric": row["metric"],
                "n": int(row["n"]),
                "delta_mean": float(row["delta_mean"]),
                "delta_std": float(row["delta_std"]),
                "ci95_low": float(row["ci95_low"]),
                "ci95_high": float(row["ci95_high"]),
            }
        )

    return rows


def delta_lookup(
    rows: list[dict[str, object]],
    comparison: str,
    metric: str,
) -> dict[str, object]:
    for row in rows:
        if row["comparison"] == comparison and row["metric"] == metric:
            return row

    raise KeyError((comparison, metric))


def add_smoke_section(lines: list[str], smoke_rows: list[dict[str, object]]) -> None:
    lines.append("## 1. Smoke-проверка механизма D=1/2/3")
    lines.append("")
    lines.append(
        "Smoke-серия использует только 5 мгновенных кластеров по 3 бита "
        "и показывает, что генератор действительно меняет структуру отказа при изменении глубины перемежения."
    )
    lines.append("")
    lines.append("| D | strategy | scrub cycles | corrected | DED detections | new DUE | repeated DED | final unique DUE | busy, % |")
    lines.append("|---:|---|---:|---:|---:|---:|---:|---:|---:|")

    for row in smoke_rows:
        lines.append(
            f"| {row['D']} | "
            f"`{row['strategy']}` | "
            f"{row['scrub_cycles']} | "
            f"{row['corrected']} | "
            f"{row['uncorrectable_detections']} | "
            f"{row['new_due_count']} | "
            f"{row['repeated_due_detections']} | "
            f"{row['unique_uncorrectable_words']} | "
            f"{row['busy_percent']:.3f} |"
        )

    lines.append("")
    lines.append(
        "В smoke-прогоне при D=1 трёхбитовый кластер остаётся многобитовой ошибкой одного слова. "
        "При D=2 он раскладывается как 2+1 по двум словам: одна DED-группа остаётся, "
        "а дополнительная одиночная ошибка становится исправимой. "
        "При D=3 он раскладывается как 1+1+1 по трём словам, и в smoke-прогоне "
        "уникальные неустранимые слова исчезают."
    )
    lines.append("")


def add_interval_sweep_section(lines: list[str], summary_rows: list[dict[str, object]]) -> None:
    lines.append("## 2. Fixed-strategy interval sweep")
    lines.append("")
    lines.append(
        "Основная серия выполнена для 10 seed, `cluster_bit_count=3`, "
        "D=1/2/3 и пяти постоянных интервалов скраббинга."
    )
    lines.append("")
    lines.append("| D | fixed interval | runs | busy, % | corrected | DED detections | new DUE | repeated DED | final unique DUE |")
    lines.append("|---:|---:|---:|---:|---:|---:|---:|---:|---:|")

    for row in summary_rows:
        lines.append(
            f"| {row['D']} | "
            f"{row['fixed_interval']} | "
            f"{row['runs']} | "
            f"{row['busy_mean']:.3f} ± {row['busy_std']:.3f} | "
            f"{row['corrected_mean']:.1f} ± {row['corrected_std']:.1f} | "
            f"{row['ded_mean']:.1f} ± {row['ded_std']:.1f} | "
            f"{row['new_due_mean']:.3f} ± {row['new_due_std']:.3f} | "
            f"{row['repeated_mean']:.1f} ± {row['repeated_std']:.1f} | "
            f"{row['unique_mean']:.3f} ± {row['unique_std']:.3f} |"
        )

    lines.append("")
    lines.append(
        "При D=1 и D=2 сохраняется мгновенная DED-составляющая: даже на самом агрессивном "
        "из проверенных интервалов число новых runtime DUE и итоговых уникальных неустранимых слов "
        "остаётся существенно выше нуля. "
        "Частичное перемежение D=2 не обязано монотонно улучшать риск-метрику относительно D=1, "
        "поскольку раскладка 2+1 оставляет DED-группу и добавляет исправимую одиночную ошибку "
        "в другом слове. При D=3 риск-метрика резко ниже и сильнее отражает накопительный механизм."
    )
    lines.append("")


def add_deltas_section(lines: list[str], deltas: list[dict[str, object]]) -> None:
    intervals = [1089, 1244, 1555, 2021, 2400]

    lines.append("## 3. Paired-delta анализ")
    lines.append("")
    lines.append(
        "Дельты считаются попарно по одному и тому же seed, поэтому сравнение отделяет "
        "эффект перемежения от случайности потока событий."
    )
    lines.append("")

    lines.append("### D=3 относительно D=1")
    lines.append("")
    lines.append("| interval | Δ new DUE | Δ final unique DUE | Δ repeated DED | Δ DED detections | Δ corrected |")
    lines.append("|---:|---:|---:|---:|---:|---:|")

    for interval in intervals:
        comparison = f"D3 - D1 at interval {interval}"
        new_due = delta_lookup(deltas, comparison, "new_due_count")
        unique = delta_lookup(deltas, comparison, "unique_uncorrectable_words")
        repeated = delta_lookup(deltas, comparison, "repeated_due_detections")
        ded = delta_lookup(deltas, comparison, "uncorrectable_detections")
        corrected = delta_lookup(deltas, comparison, "corrected")

        lines.append(
            f"| {interval} | "
            f"{new_due['delta_mean']:.3f} [{new_due['ci95_low']:.3f}; {new_due['ci95_high']:.3f}] | "
            f"{unique['delta_mean']:.3f} [{unique['ci95_low']:.3f}; {unique['ci95_high']:.3f}] | "
            f"{repeated['delta_mean']:.1f} [{repeated['ci95_low']:.1f}; {repeated['ci95_high']:.1f}] | "
            f"{ded['delta_mean']:.1f} [{ded['ci95_low']:.1f}; {ded['ci95_high']:.1f}] | "
            f"{corrected['delta_mean']:.1f} [{corrected['ci95_low']:.1f}; {corrected['ci95_high']:.1f}] |"
        )

    lines.append("")
    lines.append("### D=3 относительно D=2")
    lines.append("")
    lines.append("| interval | Δ new DUE | Δ final unique DUE | Δ repeated DED | Δ DED detections | Δ corrected |")
    lines.append("|---:|---:|---:|---:|---:|---:|")

    for interval in intervals:
        comparison = f"D3 - D2 at interval {interval}"
        new_due = delta_lookup(deltas, comparison, "new_due_count")
        unique = delta_lookup(deltas, comparison, "unique_uncorrectable_words")
        repeated = delta_lookup(deltas, comparison, "repeated_due_detections")
        ded = delta_lookup(deltas, comparison, "uncorrectable_detections")
        corrected = delta_lookup(deltas, comparison, "corrected")

        lines.append(
            f"| {interval} | "
            f"{new_due['delta_mean']:.3f} [{new_due['ci95_low']:.3f}; {new_due['ci95_high']:.3f}] | "
            f"{unique['delta_mean']:.3f} [{unique['ci95_low']:.3f}; {unique['ci95_high']:.3f}] | "
            f"{repeated['delta_mean']:.1f} [{repeated['ci95_low']:.1f}; {repeated['ci95_high']:.1f}] | "
            f"{ded['delta_mean']:.1f} [{ded['ci95_low']:.1f}; {ded['ci95_high']:.1f}] | "
            f"{corrected['delta_mean']:.1f} [{corrected['ci95_low']:.1f}; {corrected['ci95_high']:.1f}] |"
        )

    lines.append("")
    lines.append("### Чувствительность к интервалу внутри каждого D")
    lines.append("")
    lines.append("| D | Δ new DUE slowest-fastest | Δ final unique DUE | Δ repeated DED | Δ DED detections | Δ corrected |")
    lines.append("|---:|---:|---:|---:|---:|---:|")

    for depth in [1, 2, 3]:
        comparison = f"D{depth} slowest - fastest"
        new_due = delta_lookup(deltas, comparison, "new_due_count")
        unique = delta_lookup(deltas, comparison, "unique_uncorrectable_words")
        repeated = delta_lookup(deltas, comparison, "repeated_due_detections")
        ded = delta_lookup(deltas, comparison, "uncorrectable_detections")
        corrected = delta_lookup(deltas, comparison, "corrected")

        lines.append(
            f"| {depth} | "
            f"{new_due['delta_mean']:.3f} [{new_due['ci95_low']:.3f}; {new_due['ci95_high']:.3f}] | "
            f"{unique['delta_mean']:.3f} [{unique['ci95_low']:.3f}; {unique['ci95_high']:.3f}] | "
            f"{repeated['delta_mean']:.1f} [{repeated['ci95_low']:.1f}; {repeated['ci95_high']:.1f}] | "
            f"{ded['delta_mean']:.1f} [{ded['ci95_low']:.1f}; {ded['ci95_high']:.1f}] | "
            f"{corrected['delta_mean']:.1f} [{corrected['ci95_low']:.1f}; {corrected['ci95_high']:.1f}] |"
        )

    lines.append("")
    lines.append(
        "Во всех проверенных интервалах D=3 статистически значимо снижает "
        "`new_due_count` и `unique_uncorrectable_words` относительно D=1 и D=2. "
        "Старый `uncorrectable_detections` следует читать как диагностический счётчик "
        "(diagnostic counter) повторных обнаружений: он может расти из-за повторного чтения "
        "уже latched DUE-слова. "
        "Внутри D=3 на более медленных интервалах появляются отдельные new/unique DUE, "
        "что качественно соответствует возврату к накопительной, управляемой интервалом модели риска; "
        "однако в данной серии paired-delta CI для slowest-fastest по new/unique DUE включает ноль, "
        "поэтому этот внутригрупповой рост не следует называть статистически значимым."
    )
    lines.append("")


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--base-dir",
        type=Path,
        default=Path("results/paper/interleaving"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/paper/interleaving/interleaving_summary.md"),
    )

    args = parser.parse_args()

    smoke_rows = read_smoke_results(args.base_dir)
    summary_rows = read_interval_summary(
        args.base_dir / "interval_sweep" / "interleaving_interval_sweep_summary.csv"
    )
    deltas = read_deltas(
        args.base_dir / "interval_sweep" / "interleaving_interval_sweep_deltas.csv"
    )

    lines: list[str] = []

    lines.append("# Итоговая сводка по перемежению кластерных ошибок")
    lines.append("")
    lines.append("## Назначение")
    lines.append("")
    lines.append(
        "Этот отчёт фиксирует границу применимости циклического восстановления "
        "при мгновенных многобитовых кластерах. Проверяется, как глубина перемежения "
        "D меняет характер отказа и возвращает или не возвращает задачу к накопительной модели."
    )
    lines.append("")
    lines.append("Рассматривается `cluster_bit_count=3`:")
    lines.append("")
    lines.append("- `D=1`: три бита попадают в одно кодовое слово.")
    lines.append("- `D=2`: три бита раскладываются как 2+1 по двум словам.")
    lines.append("- `D=3`: три бита раскладываются как 1+1+1 по трём словам.")
    lines.append("")
    lines.append(
        "В текущем RTL-стенде группы одного физического кластера инжектируются "
        "истинно одновременно: несколько fault-событий с одним `time_cycle` "
        "передаются в модель памяти за один такт через несколько injection slots. "
        "Для новых результатов `cluster_injection_skew = 0`."
    )
    lines.append("")

    add_smoke_section(lines, smoke_rows)
    add_interval_sweep_section(lines, summary_rows)
    add_deltas_section(lines, deltas)

    lines.append("## 4. Итоговая интерпретация")
    lines.append("")
    lines.append(
        "Недостаточное перемежение оставляет мгновенную составляющую риска, "
        "которую нельзя устранить одним только уменьшением периода скраббинга. "
        "Для трёхбитового кластера D=1 оставляет все биты в одном слове, а D=2 "
        "оставляет одну двухбитовую группу, поэтому D=2 не является достаточной глубиной."
    )
    lines.append("")
    lines.append(
        "При D=3 каждый бит кластера попадает в отдельное кодовое слово. "
        "В этом случае мгновенная DED-составляющая устраняется, число исправленных ошибок растёт, "
        "а число уникальных неустранимых слов статистически значимо снижается относительно D=1 и D=2."
    )
    lines.append("")
    lines.append(
        "После достаточного перемежения остаточный риск снова становится чувствительным "
        "к интервалу циклического восстановления. Это подтверждает методический вывод: "
        "адаптивный скраббинг применим к накопительным ошибкам, но для мгновенных многобитовых "
        "кластеров требуется предварительное пространственное разделение битов по кодовым словам."
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(args.output.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()

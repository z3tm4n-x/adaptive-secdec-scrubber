# Publication Results Snapshot

Эта директория содержит curated snapshot результатов для статьи об RTL-архитектуре адаптивного скраббинга памяти.

В отличие от `results/tables`, `results/figures` и `results/logs`, содержимое `results/paper` предназначено для хранения в git и использования при написании статьи.

## Основные таблицы статьи

| Файл | Раздел статьи |
|---|---|
| `tables/risk_policy_summary.md` | Расчёт risk-policy по полному ряду `ν(t)` |
| `tables/strategy_scenario_comparison.md` | Основные численные эксперименты: `no_clusters` / `with_clusters` |
| `tables/strategy_series_summary_no_clusters.md` | Сводка серии без мгновенных кластеров |
| `tables/strategy_series_summary_with_clusters.md` | Сводка серии с мгновенными кластерами |
| `eta_achievable/tables/eta_verification.md` | Practical η на достижимой RTL-шкале |
| `eta_achievable/tables/eta_pareto_summary.md` | Pareto-анализ adaptive vs fixed |
| `eta_design_comparison.md` | Сравнение direct и achievable mapping |
| `tables/synthesis_summary.md` | Технологически независимый синтез Yosys |

## Финальная RTL mapping для статьи

Используется архитектурно достижимая таблица интервалов:

```text
level_intervals = 240,200,150,120,100,80,70,70
threshold_intervals = 200,120,70
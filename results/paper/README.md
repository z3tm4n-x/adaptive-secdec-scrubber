# Навигация по результатам

## Назначение

Эта директория содержит итоговые отчёты, агрегированные таблицы и промежуточные артефакты экспериментов для ветки `dissertation-finalization`.

Если цель — понять, что писать в диссертации или статье, не начинайте с per-seed директорий. Начинайте с итоговых Markdown-отчётов, перечисленных ниже.

## Читать в первую очередь

| Порядок | Файл | Назначение |
|---:|---|---|
| 1 | `final_results_summary.md` | Главная сводка результатов, ограничений и корректных формулировок |
| 2 | `tables/efficiency_scale_verification.md` | Проверка аналитической шкалы эффективности `ηmax = 1 + CV²` |
| 3 | `unsaturated_control/unsaturated_control_summary.md` | Контрольная RTL-серия вне насыщения на `DEPTH=256` |
| 4 | `measured_control/measured_control_summary.md` | Observable signal, measured-control replay, weight sweep и closed-loop RTL |
| 5 | `interleaving/interleaving_summary.md` | Перемежение D=1/2/3 и границы применимости скраббинга |
| 6 | `true_pair_alignment/true_pair_alignment_summary.md` | Проверка накопительных пар по истинным `pair_id` |

## Основной смысл результатов

Краткая интерпретация результатов зафиксирована в `final_results_summary.md`.

Сжатая логика такая:

1. Идеальный расчётный выигрыш адаптивного восстановления определяется вариативностью риска и ограничен `1 + CV²`.
2. В RTL-модели adaptive-стратегии уменьшают занятость интерфейса памяти, но вне насыщения это является компромиссом с риск-метрикой.
3. Управляющий сигнал можно строить по наблюдаемым RTL-счётчикам, но нужно учитывать не только исправленные ошибки, но и DED-индикатор.
4. Мгновенные многобитовые кластеры не устраняются одной частотой скраббинга; для них требуется пространственное перемежение.
5. При достаточном перемежении кластер превращается в одиночные ошибки по разным кодовым словам, и остаточный риск снова управляется интервалом восстановления.

## Что является итоговыми артефактами

### Эффективность

| Файл | Содержание |
|---|---|
| `tables/efficiency_scale_verification.md` | Основной отчёт по `ηmax = 1 + CV²` |
| `tables/efficiency_scale_verification.csv` | Табличная версия результатов |

### Контроль вне насыщения

| Файл | Содержание |
|---|---|
| `unsaturated_control/unsaturated_control_summary.md` | Главный отчёт блока |
| `unsaturated_control/no_clusters/strategy_series_summary.md` | Серия без мгновенных кластеров |
| `unsaturated_control/no_clusters/paired_delta_analysis.md` | Paired-delta анализ без мгновенных кластеров |
| `unsaturated_control/fixed_grid_no_clusters/fixed_grid_pareto.md` | Fixed-grid Pareto без мгновенных кластеров |
| `unsaturated_control/fixed_grid_with_clusters/fixed_grid_pareto.md` | Fixed-grid Pareto с мгновенными кластерами |

### Measured-control

| Файл | Содержание |
|---|---|
| `measured_control/measured_control_summary.md` | Главный отчёт блока: offline replay calibration и closed-loop RTL |
| `measured_control/no_clusters_weight_sweep/measured_weight_sweep_summary.md` | Sweep по весу DED-индикатора |
| `measured_control/no_clusters_weight_sweep/measured_weight_sweep_deltas.md` | Paired-delta анализ sweep |
| `measured_control/closed_loop_smoke/closed_loop_smoke_summary.md` | Smoke-проверка RTL `MODE_MEASURED` |
| `measured_control/closed_loop/closed_loop_measured_summary.md` | Multi-seed серия closed-loop RTL `MODE_MEASURED` |
| `observable_signal/no_clusters_seed1/observable_signal_summary.md` | Диагностика наблюдаемого сигнала на одном seed |

### Перемежение

| Файл | Содержание |
|---|---|
| `interleaving/interleaving_summary.md` | Главный отчёт блока |
| `interleaving/interval_sweep/interleaving_interval_sweep_summary.md` | Sweep по D и fixed interval |
| `interleaving/interval_sweep/interleaving_interval_sweep_deltas.md` | Paired-delta анализ D=1/2/3 |
| `interleaving/smoke/` | Smoke-проверка механизма D=1/2/3 |

## Что является промежуточными данными

Следующие директории нужны в основном для воспроизводимости и диагностики. Их не следует читать первыми при подготовке текста диссертации.

| Директория | Назначение |
|---|---|
| `interleaving/interval_sweep/D*/interval_*/seed_*/` | Per-seed метаданные sweep по перемежению |
| `observable_signal/no_clusters_multiseed/seed_*/` | Per-seed observable windows |
| `measured_control/no_clusters_weight_sweep/seed_*/` | Per-seed measured schedules для разных весов |
| `measured_control/no_clusters_multiseed/seed_*/` | Per-seed measured replay |
| `unsaturated_control/no_clusters/` | Пилотная серия перед основной серией |

Эти директории могут содержать много однотипных файлов:

- `fault_events_meta.csv`;
- `event_shift_summary.md`;
- `risk_policy_level_map.csv`;
- промежуточные `control_levels*.csv`;
- per-seed таблицы replay.

Они важны для аудита и воспроизведения, но не являются основными файлами для написания текста.

## Что не следует интерпретировать как финальный вывод

Не делайте выводы напрямую из одиночных per-seed файлов, если рядом есть агрегированный отчёт.

Например:

- для measured-control используйте `measured_control/measured_control_summary.md`; для closed-loop RTL дополнительно доступны `closed_loop_smoke/closed_loop_smoke_summary.md` и `closed_loop/closed_loop_measured_summary.md`;
- для interleaving используйте `interleaving/interleaving_summary.md` и paired-delta отчёт;
- для unsaturated-control используйте `unsaturated_control/unsaturated_control_summary.md`.

## Ограничения интерпретации

1. Ранний `measured-control` является offline replay и используется как калибровка; дополнительно реализован closed-loop RTL-режим `MODE_MEASURED`, который формирует уровень внутри контроллера.
2. Adaptive-стратегии вне насыщения дают компромисс busy/risk, а не безусловное превосходство.
3. Проверка Pareto выполнена относительно выбранной fixed-сетки, а не относительно всех возможных политик.
4. Для D>1 кластерные инжекции сериализуются по соседним тактам из-за ограничения testbench: одна fault-инжекция за такт.
5. Физическая аппаратная проекция секундных интервалов оценивается отдельно от методических RTL-серий.

## Воспроизведение

Общие команды воспроизведения находятся в корневом файле:

`REPRODUCE.md`

Перед повторным запуском серий учитывайте, что некоторые sweep-эксперименты занимают заметное время.

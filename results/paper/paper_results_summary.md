# Итоговая сводка результатов статьи 5

## 1. Входные данные

- Источник: `data/upsets.xlsx`
- Размер окна: 43824 часовых отсчёта
- Число модельных тактов: 50000
- Среднее ν(t): 7.07276729
- CV²: 6.24295992
- η_theory = 1 + CV² = 7.24295992

## 2. Расчёт risk-policy

- Pm* = 0.01
- E* = 0.0100503358535
- adaptive_current_continuous: 2405711 cycles
- adaptive_current_discrete: 2543790 cycles
- fixed_continuous_at_target: 17424471 cycles
- fixed_continuous / adaptive_continuous ≈ 7.243
- Цена дискретизации относительно continuous adaptive: +5.74 %
- delayed_1h_discrete относительно adaptive_current_discrete: +4.314 %

## 3. Финальное RTL-отображение

- Источник управления: `risk_policy`
- Table intervals: 240, 200, 150, 120, 100, 80, 70, 70
- Threshold intervals: 200, 120, 70

Семантика интервала:

selected_interval = целевой период полного прохода

effective_wait_interval = max(1, selected_interval - last_pass_duration)

## 4. Practical η

| Стратегия | η scrub | η busy |
|---|---:|---:|
| table | 1.362 | 1.334 |
| threshold | 1.475 | 1.442 |

Pareto / constrained comparison:

| Стратегия | η busy |
|---|---:|
| table | 1.650 |
| threshold | 1.442 |

Для `table` и `threshold` fixed_points_dominating_adaptive = 0, то есть adaptive-точки не доминируются fixed-точками и входят в Pareto-front.

## 5. Финальные серии no_clusters

| Стратегия | Corrected | Unique | Detections | Busy, % |
|---|---:|---:|---:|---:|
| fixed | 507.533 | 4.200 | 852.767 | 21.187 |
| table | 419.133 | 4.967 | 750.467 | 8.667 |
| threshold | 439.633 | 4.733 | 748.900 | 9.920 |

Снижение busy относительно fixed:

- table: -59.09 %
- threshold: -53.18 %

Paired deltas относительно fixed:

| Стратегия | Δ busy, п.п. | Δ busy 95% CI | Δ unique | Δ unique 95% CI |
|---|---:|---:|---:|---:|
| table | -12.520 | [-12.538; -12.502] | +0.767 | [+0.104; +1.429] |
| threshold | -11.267 | [-11.287; -11.246] | +0.533 | [-0.053; +1.119] |

## 6. Финальные серии with_clusters

| Стратегия | Corrected | Unique | Detections | Busy, % |
|---|---:|---:|---:|---:|
| fixed | 497.800 | 4.567 | 1219.067 | 21.177 |
| table | 412.500 | 5.267 | 861.567 | 8.657 |
| threshold | 431.400 | 5.167 | 889.600 | 9.897 |

Снижение busy относительно fixed:

- table: -59.12 %
- threshold: -53.27 %

Paired deltas относительно fixed:

| Стратегия | Δ busy, п.п. | Δ busy 95% CI | Δ unique | Δ unique 95% CI |
|---|---:|---:|---:|---:|
| table | -12.520 | [-12.538; -12.502] | +0.700 | [+0.041; +1.359] |
| threshold | -11.280 | [-11.298; -11.262] | +0.600 | [-0.009; +1.209] |

## 7. Вклад мгновенных кластеров

| Стратегия | Δ corrected | Δ unique | Δ detections | Δ busy |
|---|---:|---:|---:|---:|
| fixed | -9.733 | +0.367 | +366.300 | -0.010 п.п. |
| table | -6.633 | +0.300 | +111.100 | -0.010 п.п. |
| threshold | -8.233 | +0.433 | +140.700 | -0.023 п.п. |

Интерпретация:

- `unique_uncorrectable_words` — основная физическая метрика вклада кластеров.
- `uncorrectable_detections` зависит от частоты обхода памяти и считает повторные обнаружения.

## 8. Синтез

| Конфигурация | ADDR_WIDTH | Слов | Cells | Рост |
|---|---:|---:|---:|---:|
| adaptive_aw4 | 4 | 16 | 4125 | baseline |
| adaptive_aw21 | 21 | 2097152 | 4207 | +1.99 % |

Массив памяти не входит в синтезируемую область. Number of memories = 0.

## 9. Основные ограничения

- Память 16 слов — stress-test RTL-среда, а не полная модель 72-Мбит памяти.
- Модельный такт — нормированное время симуляции, а не физический такт аппаратуры.
- Поправка M(t) из статьи 3 не реализована в RTL.
- Режимы интерливинга D=2 и D≥3 из статьи 4 не реализованы.
- Энергия напрямую не моделируется; используются proxy-метрики: busy ratio, reads/writes, scrub cycles.

## 10. Главная формулировка для статьи

В рассмотренной RTL stress-test среде adaptive table и threshold стратегии снижают среднюю занятость интерфейса памяти на 53–59 % относительно fixed-режима. Это достигается ценой умеренного увеличения числа уникальных неустранимых слов, менее чем на одно слово за прогон в среднем, при этом adaptive-точки остаются Pareto-эффективными относительно fixed sweep.

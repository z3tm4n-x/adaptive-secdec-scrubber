# Pareto-анализ η для achievable RTL mapping

## Назначение

Проверяется multi-objective сравнение adaptive-стратегий с fixed sweep. Минимизируются одновременно стоимость (`busy_percent`) и две риск-метрики: `unique_uncorrectable` и `uncorrectable_detections`.

Fixed-режим считается доминирующим adaptive только если он одновременно имеет не большую занятость памяти, не больше уникальных неустранимых слов и не больше обнаружений неустранимых состояний, причём хотя бы по одной метрике строго лучше.

## Adaptive summary

| strategy | busy, % | unique | detections | dominated fixed | fixed dominating adaptive | tradeoff fixed | Pareto member |
|---|---:|---:|---:|---:|---:|---:|---:|
| `table` | 8.667 | 4.967 | 750.467 | 2 | 0 | 7 | 1 |
| `threshold` | 9.920 | 4.733 | 748.900 | 1 | 0 | 8 | 1 |

## Constrained fixed comparison

| strategy | cheapest fixed with unique <= adaptive | η busy | cheapest fixed with detections <= adaptive | η busy | cheapest fixed with both risks <= adaptive | η busy |
|---|---:|---:|---:|---:|---:|---:|
| `table` | 120 | 1.650385 |  |  |  |  |
| `threshold` | 120 | 1.441868 |  |  |  |  |

## Pareto front

| strategy | fixed interval | busy, % | unique | detections |
|---|---:|---:|---:|---:|
| `fixed` | 60 | 24.967 | 3.667 | 788.967 |
| `fixed` | 70 | 24.137 | 3.967 | 812.467 |
| `fixed` | 100 | 17.067 | 4.033 | 808.533 |
| `fixed` | 120 | 14.303 | 4.600 | 822.533 |
| `fixed` | 240 | 7.383 | 5.567 | 787.900 |
| `fixed` | 300 | 5.977 | 6.000 | 774.533 |
| `table` |  | 8.667 | 4.967 | 750.467 |
| `threshold` |  | 9.920 | 4.733 | 748.900 |

## Интерпретация

Если `fixed dominating adaptive = 0`, то в рассмотренном fixed sweep нет постоянного интервала, который одновременно дешевле adaptive и не хуже по обеим риск-метрикам.

Если `cheapest fixed with both risks <= adaptive` отсутствует, это означает, что fixed sweep не содержит точки, которая одновременно сохраняет обе риск-метрики adaptive. В этом случае single-metric matching по detections или unique следует интерпретировать осторожно: он может игнорировать ухудшение второй риск-метрики.

# Multi-seed measured replay

## Назначение

Проверяется offline-replay управляющих расписаний, построенных по наблюдаемым счётчикам исполнения, на серии seed. Истинный ряд ν(t) не используется при построении measured schedule.

- Seed range: 1…10
- Replay CSV: `results/paper/measured_control/no_clusters_multiseed/replay/measured_replay_series.csv`
- Reference CSV: `results/paper/unsaturated_control/no_clusters/strategy_comparison_series.csv`

## Сводка

| kind | name | busy, % | scrub cycles | corrected | uncorrectable detections | unique uncorrectable words |
|---|---|---:|---:|---:|---:|---:|
| `reference` | `risk_policy_fixed` | 20.600 ± 0.000 | 401.0 ± 0.0 | 469.5 ± 4.4 | 557.4 ± 349.1 | 2.800 ± 1.814 |
| `reference` | `risk_policy_table` | 14.200 ± 0.000 | 276.0 ± 0.0 | 460.9 ± 6.9 | 767.8 ± 234.9 | 4.500 ± 2.121 |
| `reference` | `risk_policy_threshold` | 12.700 ± 0.000 | 248.0 ± 0.0 | 459.3 ± 5.3 | 828.8 ± 228.9 | 5.300 ± 2.214 |
| `measured_replay` | `measured_table_weighted` | 17.650 ± 0.467 | 343.7 ± 8.9 | 466.5 ± 6.6 | 718.0 ± 440.7 | 3.900 ± 2.331 |
| `measured_replay` | `measured_table_corrected_only` | 16.120 ± 0.155 | 313.7 ± 3.3 | 463.6 ± 7.1 | 742.3 ± 356.0 | 4.400 ± 3.098 |

## Ключевые paired-delta measured replay

| Сравнение | Δ busy, п.п. | Δ uncorrectable detections | Δ unique |
|---|---:|---:|---:|
| `weighted - corrected_only` | 1.530 [1.132; 1.928] | -24.3 [-210.1; 161.5] | -0.500 [-1.580; 0.580] |

## Интерпретация

`measured_table_corrected_only` использует только исправленные ошибки и поэтому может недооценивать опасные участки. `measured_table_weighted` добавляет обнаруженные неустранимые состояния как штрафной индикатор.

Если `weighted - corrected_only` имеет положительную Δ busy и отрицательную Δ unique / Δ uncorrectable detections, то добавление `uncorrectable_error_count` повышает интенсивность восстановления, но снижает риск-метрики.

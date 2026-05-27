# Сравнение measured replay с reference-стратегиями

## Назначение

Сравниваются reference-стратегии `fixed/table/threshold`, рассчитанные по исходной risk-policy, и replay-стратегии, где `control_levels.csv` построен только по наблюдаемым счётчикам исполнения.

Все строки относятся к одному потоку событий: `no_clusters`, `seed=1`.

| kind | name | scrub cycles | corrected | uncorrectable detections | unique uncorrectable words | busy, % | interval switches |
|---|---|---:|---:|---:|---:|---:|---:|
| `reference` | `risk_policy_fixed` | 401 | 474 | 39 | 1 | 20.600 | 0 |
| `reference` | `risk_policy_table` | 276 | 459 | 856 | 4 | 14.200 | 1295 |
| `reference` | `risk_policy_threshold` | 248 | 470 | 585 | 1 | 12.700 | 42 |
| `measured_replay` | `measured_table_weighted` | 345 | 478 | 11 | 1 | 17.700 | 16 |
| `measured_replay` | `measured_table_corrected_only` | 311 | 466 | 471 | 3 | 16.000 | 17 |

## Интерпретация

`measured_table_corrected_only` строит уровень только по исправленным ошибкам и поэтому даёт меньшую занятость, но существенно больше обнаружений неустранимых состояний.

`measured_table_weighted` добавляет штраф за `uncorrectable_error_count`; это увеличивает число проходов и занятость, но резко снижает число неустранимых обнаружений и уникальных неустранимых слов.

Этот результат показывает, что наблюдаемый контур должен учитывать не только исправленные одиночные ошибки, но и обнаруженные неустранимые состояния как индикатор недооценки опасного участка.

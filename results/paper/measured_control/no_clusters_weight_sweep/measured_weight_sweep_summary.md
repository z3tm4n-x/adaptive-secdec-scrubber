# Measured control weight sweep

## Назначение

Проверяется чувствительность measured-control replay к весу `uncorrectable_error_count` в измерительном score. Все replay строятся по наблюдаемым окнам `corrected_error_count` / `uncorrectable_error_count`; истинный ряд ν(t) не используется при выборе уровня.

## Сводка

| replay | busy, % | scrub cycles | corrected | uncorrectable detections | unique uncorrectable words |
|---|---:|---:|---:|---:|---:|
| `measured_table_w0p00` | 16.120 ± 0.155 | 313.7 ± 3.3 | 463.6 ± 7.1 | 742.3 ± 356.0 | 4.400 ± 3.098 |
| `measured_table_w0p10` | 16.680 ± 0.103 | 324.4 ± 2.0 | 466.6 ± 3.9 | 615.9 ± 296.0 | 3.900 ± 2.025 |
| `measured_table_w0p25` | 17.650 ± 0.467 | 343.7 ± 8.9 | 466.5 ± 6.6 | 718.0 ± 440.7 | 3.900 ± 2.331 |
| `measured_table_w0p50` | 19.850 ± 1.414 | 386.4 ± 27.4 | 469.3 ± 6.3 | 519.2 ± 397.7 | 2.700 ± 2.359 |
| `measured_table_w0p75` | 21.160 ± 1.428 | 412.1 ± 27.5 | 469.6 ± 6.1 | 565.2 ± 432.1 | 2.500 ± 2.068 |
| `measured_table_w1p00` | 21.880 ± 0.977 | 426.1 ± 19.2 | 469.2 ± 5.1 | 576.6 ± 400.7 | 2.600 ± 1.955 |

## Интерпретация

Если рост веса `uncorrectable_error_count` приводит только к росту занятости без устойчивого снижения `unique_uncorrectable_words` или `uncorrectable_detections`, выбранная формула score требует иной калибровки или другой нелинейной реакции на обнаруженные DED-состояния.

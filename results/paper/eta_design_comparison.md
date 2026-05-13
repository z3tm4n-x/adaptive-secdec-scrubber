# Сравнение η для direct и achievable RTL mapping

## Назначение

Сравниваются две семантически разные RTL-постановки: direct mapping использует исходное отображение уровней risk-policy в короткие интервалы, а achievable mapping ограничивает интервалы архитектурно достижимой областью последовательного скраббера.

## Сводка practical η

| run | strategy | matching metric | matched fixed | η scrub | η busy | adaptive busy, % | adaptive unique | adaptive detections |
|---|---|---|---:|---:|---:|---:|---:|---:|
| `direct` | `table` | `unique_uncorrectable_words` | 100 | 0.866 | 0.870 | 19.607 | 4.100 | 720.567 |
| `direct` | `table` | `uncorrectable_detections` | 20 | 1.287 | 1.275 | 19.607 | 4.100 | 720.567 |
| `direct` | `threshold` | `unique_uncorrectable_words` | 10 | 1.000 | 1.000 | 24.990 | 3.900 | 842.633 |
| `direct` | `threshold` | `uncorrectable_detections` | 10 | 1.000 | 1.000 | 24.990 | 3.900 | 842.633 |
| `achievable` | `table` | `unique_uncorrectable_words` | 150 | 1.362 | 1.334 | 8.667 | 4.967 | 750.467 |
| `achievable` | `table` | `uncorrectable_detections` | 300 | 0.677 | 0.690 | 8.667 | 4.967 | 750.467 |
| `achievable` | `threshold` | `unique_uncorrectable_words` | 120 | 1.475 | 1.442 | 9.920 | 4.733 | 748.900 |
| `achievable` | `threshold` | `uncorrectable_detections` | 300 | 0.587 | 0.602 | 9.920 | 4.733 | 748.900 |

## Интерпретация

Если achievable mapping даёт более устойчивую practical η, это означает, что прежняя direct-постановка была ограничена насыщением скраббера: часть целевых интервалов была меньше длительности полного прохода памяти.

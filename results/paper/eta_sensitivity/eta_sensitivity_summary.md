# Чувствительность η к нормировке RTL-интервалов

## Назначение

Сравниваются три отображения расчётных интервалов risk-policy в model-cycle intervals RTL-стенда: slow, base и fast. Цель — проверить, является ли неоднозначная practical η следствием конкретно выбранной нормировки.

## Сводка practical η

| mapping | strategy | matching metric | matched fixed | η scrub | η busy | adaptive busy, % | adaptive unique | adaptive detections |
|---|---|---|---:|---:|---:|---:|---:|---:|
| `slow` | `table` | `unique_uncorrectable_words` | 200 | 0.774 | 0.783 | 8.530 | 6.100 | 666.600 |
| `slow` | `table` | `uncorrectable_detections` | 20 | 2.410 | 2.298 | 8.530 | 6.100 | 666.600 |
| `slow` | `threshold` | `unique_uncorrectable_words` | 10 | 1.999 | 1.930 | 11.450 | 4.100 | 674.300 |
| `slow` | `threshold` | `uncorrectable_detections` | 40 | 1.429 | 1.397 | 11.450 | 4.100 | 674.300 |
| `base` | `table` | `unique_uncorrectable_words` | 25 | 1.549 | 1.513 | 12.270 | 4.800 | 733.600 |
| `base` | `table` | `uncorrectable_detections` | 150 | 0.648 | 0.661 | 12.270 | 4.800 | 733.600 |
| `base` | `threshold` | `unique_uncorrectable_words` | 20 | 1.301 | 1.284 | 15.270 | 3.200 | 746.200 |
| `base` | `threshold` | `uncorrectable_detections` | 60 | 0.885 | 0.889 | 15.270 | 3.200 | 746.200 |
| `fast` | `table` | `unique_uncorrectable_words` | 40 | 0.991 | 0.989 | 16.180 | 3.700 | 649.000 |
| `fast` | `table` | `uncorrectable_detections` | 20 | 1.224 | 1.211 | 16.180 | 3.700 | 649.000 |
| `fast` | `threshold` | `unique_uncorrectable_words` | 20 | 1.055 | 1.051 | 18.650 | 3.200 | 791.200 |
| `fast` | `threshold` | `uncorrectable_detections` | 10 | 1.194 | 1.185 | 18.650 | 3.200 | 791.200 |

## Интерпретация

Если ranking стратегий и practical η сильно меняются между slow/base/fast, то итоговый эффект адаптации чувствителен к нормировке model-cycle intervals. Если вывод устойчив, выбранная нормировка не является основной причиной слабой или неоднозначной η.

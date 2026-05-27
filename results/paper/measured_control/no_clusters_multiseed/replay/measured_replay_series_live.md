# RTL replay measured schedule

## Назначение

Проверяется исполнение управляющего расписания, построенного не по истинному ряду ν(t), а по наблюдаемым счётчикам исполнения. События отказов остаются теми же, что в исходном seed; меняется только `control_levels.csv`.

## Результаты

| replay | seed | replay strategy | RTL strategy | scrub cycles | corrected | uncorrectable detections | unique uncorrectable words | busy, % | interval switches |
|---|---:|---|---|---:|---:|---:|---:|---:|---:|
| `measured_table_weighted` | 1 | `table` | `table` | 345 | 478 | 11 | 1 | 17.700 | 16 |
| `measured_table_corrected_only` | 1 | `table` | `table` | 311 | 466 | 471 | 3 | 16.000 | 17 |
| `measured_table_weighted` | 2 | `table` | `table` | 344 | 476 | 232 | 2 | 17.700 | 16 |
| `measured_table_corrected_only` | 2 | `table` | `table` | 309 | 471 | 499 | 2 | 15.900 | 14 |
| `measured_table_weighted` | 3 | `table` | `table` | 341 | 457 | 792 | 9 | 17.500 | 15 |
| `measured_table_corrected_only` | 3 | `table` | `table` | 312 | 451 | 1197 | 12 | 16.100 | 12 |
| `measured_table_weighted` | 4 | `table` | `table` | 361 | 469 | 833 | 3 | 18.500 | 14 |
| `measured_table_corrected_only` | 4 | `table` | `table` | 314 | 466 | 683 | 5 | 16.100 | 12 |
| `measured_table_weighted` | 5 | `table` | `table` | 334 | 464 | 846 | 4 | 17.100 | 12 |
| `measured_table_corrected_only` | 5 | `table` | `table` | 317 | 463 | 624 | 4 | 16.300 | 14 |
| `measured_table_weighted` | 6 | `table` | `table` | 339 | 468 | 207 | 3 | 17.400 | 14 |
| `measured_table_corrected_only` | 6 | `table` | `table` | 316 | 472 | 152 | 1 | 16.200 | 14 |
| `measured_table_weighted` | 7 | `table` | `table` | 343 | 467 | 1199 | 2 | 17.600 | 12 |
| `measured_table_corrected_only` | 7 | `table` | `table` | 320 | 469 | 1070 | 2 | 16.400 | 13 |
| `measured_table_weighted` | 8 | `table` | `table` | 355 | 464 | 1175 | 4 | 18.300 | 14 |
| `measured_table_corrected_only` | 8 | `table` | `table` | 311 | 455 | 1207 | 5 | 16.000 | 14 |
| `measured_table_weighted` | 9 | `table` | `table` | 331 | 462 | 647 | 5 | 17.000 | 13 |
| `measured_table_corrected_only` | 9 | `table` | `table` | 315 | 466 | 524 | 4 | 16.200 | 12 |
| `measured_table_weighted` | 10 | `table` | `table` | 344 | 460 | 1238 | 6 | 17.700 | 14 |
| `measured_table_corrected_only` | 10 | `table` | `table` | 312 | 457 | 996 | 6 | 16.000 | 12 |

## Интерпретация

Это offline-replay, а не полностью замкнутый аппаратный контур: расписание построено по ранее снятой трассе и затем подано в RTL как внешний `ctrl_level`. Тем не менее оцениватель расписания не использует истинный ряд ν(t); он использует только наблюдаемые счётчики.

Сравнение `weighted` и `corrected_only` показывает роль обнаруженных неустранимых состояний как дополнительного индикатора недооценки опасного участка.

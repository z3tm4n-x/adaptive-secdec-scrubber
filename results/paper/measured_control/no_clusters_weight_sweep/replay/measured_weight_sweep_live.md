# RTL replay measured schedule

## Назначение

Проверяется исполнение управляющего расписания, построенного не по истинному ряду ν(t), а по наблюдаемым счётчикам исполнения. События отказов остаются теми же, что в исходном seed; меняется только `control_levels.csv`.

## Результаты

| replay | seed | replay strategy | RTL strategy | scrub cycles | corrected | uncorrectable detections | unique uncorrectable words | busy, % | interval switches |
|---|---:|---|---|---:|---:|---:|---:|---:|---:|
| `measured_table_w0p00` | 1 | `table` | `table` | 311 | 466 | 471 | 3 | 16.000 | 17 |
| `measured_table_w0p10` | 1 | `table` | `table` | 325 | 472 | 216 | 1 | 16.700 | 16 |
| `measured_table_w0p25` | 1 | `table` | `table` | 345 | 478 | 11 | 1 | 17.700 | 16 |
| `measured_table_w0p50` | 1 | `table` | `table` | 400 | 480 | 0 | 0 | 20.500 | 12 |
| `measured_table_w0p75` | 1 | `table` | `table` | 431 | 480 | 0 | 0 | 22.100 | 7 |
| `measured_table_w1p00` | 1 | `table` | `table` | 442 | 476 | 38 | 0 | 22.700 | 2 |
| `measured_table_w0p00` | 2 | `table` | `table` | 309 | 471 | 499 | 2 | 15.900 | 14 |
| `measured_table_w0p10` | 2 | `table` | `table` | 323 | 471 | 492 | 4 | 16.600 | 15 |
| `measured_table_w0p25` | 2 | `table` | `table` | 344 | 476 | 232 | 2 | 17.700 | 16 |
| `measured_table_w0p50` | 2 | `table` | `table` | 386 | 474 | 428 | 1 | 19.800 | 12 |
| `measured_table_w0p75` | 2 | `table` | `table` | 419 | 475 | 331 | 2 | 21.500 | 9 |
| `measured_table_w1p00` | 2 | `table` | `table` | 430 | 475 | 344 | 2 | 22.100 | 8 |
| `measured_table_w0p00` | 3 | `table` | `table` | 312 | 451 | 1197 | 12 | 16.100 | 12 |
| `measured_table_w0p10` | 3 | `table` | `table` | 322 | 459 | 707 | 9 | 16.600 | 10 |
| `measured_table_w0p25` | 3 | `table` | `table` | 341 | 457 | 792 | 9 | 17.500 | 15 |
| `measured_table_w0p50` | 3 | `table` | `table` | 396 | 459 | 777 | 8 | 20.300 | 11 |
| `measured_table_w0p75` | 3 | `table` | `table` | 436 | 460 | 1213 | 7 | 22.400 | 6 |
| `measured_table_w1p00` | 3 | `table` | `table` | 439 | 460 | 1223 | 7 | 22.500 | 4 |
| `measured_table_w0p00` | 4 | `table` | `table` | 314 | 466 | 683 | 5 | 16.100 | 12 |
| `measured_table_w0p10` | 4 | `table` | `table` | 327 | 471 | 579 | 3 | 16.800 | 14 |
| `measured_table_w0p25` | 4 | `table` | `table` | 361 | 469 | 833 | 3 | 18.500 | 14 |
| `measured_table_w0p50` | 4 | `table` | `table` | 435 | 474 | 395 | 2 | 22.400 | 6 |
| `measured_table_w0p75` | 4 | `table` | `table` | 441 | 473 | 506 | 2 | 22.700 | 2 |
| `measured_table_w1p00` | 4 | `table` | `table` | 442 | 473 | 506 | 2 | 22.700 | 2 |
| `measured_table_w0p00` | 5 | `table` | `table` | 317 | 463 | 624 | 4 | 16.300 | 14 |
| `measured_table_w0p10` | 5 | `table` | `table` | 323 | 465 | 586 | 4 | 16.600 | 13 |
| `measured_table_w0p25` | 5 | `table` | `table` | 334 | 464 | 846 | 4 | 17.100 | 12 |
| `measured_table_w0p50` | 5 | `table` | `table` | 354 | 468 | 476 | 2 | 18.200 | 12 |
| `measured_table_w0p75` | 5 | `table` | `table` | 377 | 466 | 541 | 3 | 19.300 | 13 |
| `measured_table_w1p00` | 5 | `table` | `table` | 407 | 468 | 533 | 2 | 20.900 | 13 |
| `measured_table_w0p00` | 6 | `table` | `table` | 316 | 472 | 152 | 1 | 16.200 | 14 |
| `measured_table_w0p10` | 6 | `table` | `table` | 325 | 466 | 322 | 3 | 16.700 | 14 |
| `measured_table_w0p25` | 6 | `table` | `table` | 339 | 468 | 207 | 3 | 17.400 | 14 |
| `measured_table_w0p50` | 6 | `table` | `table` | 383 | 472 | 55 | 2 | 19.700 | 16 |
| `measured_table_w0p75` | 6 | `table` | `table` | 414 | 474 | 210 | 0 | 21.300 | 14 |
| `measured_table_w1p00` | 6 | `table` | `table` | 428 | 470 | 272 | 2 | 22.000 | 7 |
| `measured_table_w0p00` | 7 | `table` | `table` | 320 | 469 | 1070 | 2 | 16.400 | 13 |
| `measured_table_w0p10` | 7 | `table` | `table` | 328 | 464 | 1304 | 3 | 16.900 | 16 |
| `measured_table_w0p25` | 7 | `table` | `table` | 343 | 467 | 1199 | 2 | 17.600 | 12 |
| `measured_table_w0p50` | 7 | `table` | `table` | 364 | 467 | 1276 | 2 | 18.700 | 12 |
| `measured_table_w0p75` | 7 | `table` | `table` | 389 | 465 | 1383 | 3 | 20.000 | 11 |
| `measured_table_w1p00` | 7 | `table` | `table` | 417 | 469 | 1285 | 2 | 21.400 | 9 |
| `measured_table_w0p00` | 8 | `table` | `table` | 311 | 455 | 1207 | 5 | 16.000 | 14 |
| `measured_table_w0p10` | 8 | `table` | `table` | 325 | 465 | 809 | 4 | 16.700 | 14 |
| `measured_table_w0p25` | 8 | `table` | `table` | 355 | 464 | 1175 | 4 | 18.300 | 14 |
| `measured_table_w0p50` | 8 | `table` | `table` | 420 | 472 | 357 | 1 | 21.600 | 12 |
| `measured_table_w0p75` | 8 | `table` | `table` | 441 | 472 | 400 | 1 | 22.600 | 4 |
| `measured_table_w1p00` | 8 | `table` | `table` | 444 | 472 | 400 | 1 | 22.800 | 2 |
| `measured_table_w0p00` | 9 | `table` | `table` | 315 | 466 | 524 | 4 | 16.200 | 12 |
| `measured_table_w0p10` | 9 | `table` | `table` | 322 | 466 | 543 | 4 | 16.600 | 11 |
| `measured_table_w0p25` | 9 | `table` | `table` | 331 | 462 | 647 | 5 | 17.000 | 13 |
| `measured_table_w0p50` | 9 | `table` | `table` | 350 | 464 | 421 | 4 | 18.000 | 14 |
| `measured_table_w0p75` | 9 | `table` | `table` | 363 | 466 | 364 | 3 | 18.600 | 15 |
| `measured_table_w1p00` | 9 | `table` | `table` | 383 | 464 | 424 | 4 | 19.700 | 16 |
| `measured_table_w0p00` | 10 | `table` | `table` | 312 | 457 | 996 | 6 | 16.000 | 12 |
| `measured_table_w0p10` | 10 | `table` | `table` | 324 | 467 | 601 | 4 | 16.600 | 15 |
| `measured_table_w0p25` | 10 | `table` | `table` | 344 | 460 | 1238 | 6 | 17.700 | 14 |
| `measured_table_w0p50` | 10 | `table` | `table` | 376 | 463 | 1007 | 5 | 19.300 | 11 |
| `measured_table_w0p75` | 10 | `table` | `table` | 410 | 465 | 704 | 4 | 21.100 | 10 |
| `measured_table_w1p00` | 10 | `table` | `table` | 429 | 465 | 741 | 4 | 22.000 | 6 |

## Интерпретация

Это offline-replay, а не полностью замкнутый аппаратный контур: расписание построено по ранее снятой трассе и затем подано в RTL как внешний `ctrl_level`. Тем не менее оцениватель расписания не использует истинный ряд ν(t); он использует только наблюдаемые счётчики.

Сравнение `weighted` и `corrected_only` показывает роль обнаруженных неустранимых состояний как дополнительного индикатора недооценки опасного участка.

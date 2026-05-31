# Финальная сводка результатов диссертационного эксперимента

## Назначение

Этот отчёт объединяет основные результаты, полученные в ветке `dissertation-finalization`. Он предназначен как техническая опора для финального текста диссертации / статьи и фиксирует, какие утверждения подтверждены численно, а какие требуют аккуратной формулировки.

## 1. Расчётная шкала эффективности адаптивного скраббинга

Проверена аналитическая шкала эффективности в постановке равного риска. Для исходного ряда интенсивности отказов из `data/upsets.xlsx` получено:

| Метрика | Значение |
|---|---:|
| CV² ряда ν(t) | 6.24295991773 |
| 1 + CV² | 7.24295991773 |
| ηmax аналитически | 7.24295991773 |
| ηideal численно | 7.24295991773 |
| Относительное расхождение | 1.84308e-11 % |

Вывод: численная оптимизация полностью согласуется с аналитическим выражением `ηmax = 1 + CV²`. Это закрывает расчётную часть модели: потенциальный выигрыш адаптивного восстановления определяется вариативностью временного ряда риска.

## 2. Контрольная серия вне насыщения

Для исключения артефактов 16-словного стенда выполнена контрольная серия на `ADDR_WIDTH=8`, `DEPTH=256`. Полный проход контроллера масштабирован с учётом измеренного `Tpass`.

| ADDR_WIDTH | DEPTH | Tpass, тактов |
|---:|---:|---:|
| 4 | 16 | 66 |
| 8 | 256 | 1026 |

### 2.1. Серия без мгновенных кластеров

| Стратегия | unique mean ± σ | busy mean, % | corrected mean |
|---|---:|---:|---:|
| `fixed` | 2.800 ± 1.814 | 20.600 | 469.5 |
| `table` | 4.500 ± 2.121 | 14.200 | 460.9 |
| `threshold` | 5.300 ± 2.214 | 12.700 | 459.3 |

По paired-delta относительно `fixed`:

| Сравнение | Δ busy, п.п. | Δ unique |
|---|---:|---:|
| `table-fixed` | -6.400 [-6.400; -6.400] | 1.700 [0.686; 2.714] |
| `threshold-fixed` | -7.900 [-7.900; -7.900] | 2.500 [1.227; 3.773] |

Вывод: вне насыщения adaptive-стратегии действительно уменьшают занятость памяти, но это сопровождается статистически значимым увеличением среднего числа уникальных неустранимых слов. Поэтому корректная формулировка — не “бесплатный выигрыш”, а компромисс между занятостью интерфейса и риск-метрикой.

### 2.2. Серия с мгновенными двухбитовыми кластерами

| Стратегия | unique mean ± σ | busy mean, % | corrected mean |
|---|---:|---:|---:|
| `fixed` | 9.300 ± 1.829 | 20.600 | 467.6 |
| `table` | 10.900 ± 1.663 | 14.200 | 459.0 |
| `threshold` | 11.700 ± 2.627 | 12.700 | 457.4 |

Мгновенные кластеры добавляют близкую по величине нижнюю границу риска для всех стратегий. Это подтверждает, что мгновенные многобитовые события необходимо анализировать отдельно от накопительных ошибок, зависящих от периода циклического восстановления.

### 2.3. Fixed-grid Pareto check

Для adaptive-точек выполнено сравнение с плотной сеткой постоянных интервалов. В рассмотренной сетке не найден постоянный интервал, который одновременно имел бы не большую занятость и не большее число уникальных неустранимых слов.

Вывод: adaptive-точки не доминируются выбранной fixed-сеткой, но представляют другой участок компромиссной кривой, а не абсолютное улучшение по всем метрикам.

## 3. Проверка накопительных пар

Добавлена метаинформация `pair_id` / `pair_role`, что позволяет анализировать накопительные пары напрямую, без эвристического восстановления по адресу и времени.

Проверено:

- malformed pair-групп нет;
- каждая накопительная пара содержит роли `first` и `second`;
- события пары относятся к одному адресу;
- события накопительных пар не сдвигаются генератором;
- анализ строится по истинным `pair_id`, а не по косвенным признакам.

Вывод: методическая ошибка, связанная с эвристическим анализом накопительных пар, закрыта.

## 4. Observable signal, measured-control replay и closed-loop RTL

Measured-control status: demonstration, not a net resource win. Closed-loop measured control is treated as an RTL feasibility and telemetry experiment; it must not be described as an overall improvement when its memory-busy cost exceeds the fixed baseline.


Построен наблюдаемый управляющий сигнал по RTL-счётчикам исполнения:

| Счётчик |
|---|
| `corrected_error_count` |
| `uncorrectable_error_count` |
| `memory_read_count` |
| `memory_write_count` |

Показано, что `corrected_error_count` даёт эндогенный временной сигнал: он отражает поток исправленных ошибок, но зависит от выбранной стратегии восстановления. Если частота восстановления недостаточна, часть ошибок переходит в DED-состояния и перестаёт попадать в счётчик исправлений.

Поэтому введён measured score:

`score = corrected_per_100k_cycles + w · uncorrectable_detections_per_100k_cycles`

### 4.1. Single-seed replay

Для `seed=1` выбранная точка `w=0.50` показала ожидаемую реакцию:

| Режим | scrub cycles | corrected | DED detections | unique | busy, % |
|---|---:|---:|---:|---:|---:|
| `measured_table_w0p00` | 311 | 466 | 471 | 3 | 16.000 |
| `measured_table_w0p50` | 400 | 480 | 0 | 0 | 20.500 |

Single-seed результат используется только как демонстрация механизма; основной вывод сделан по серии seed.

### 4.2. Weight sweep

Для `w = 0.00, 0.10, 0.25, 0.50, 0.75, 1.00` выполнен multi-seed replay.

Главная рабочая точка:

| Сравнение | Δ busy, п.п. | Δ DED detections | Δ unique |
|---|---:|---:|---:|
| `w0.50 - w0.00` | +3.730 [2.656; 4.804] | -223.1 [-435.8; -10.4] | -1.700 [-2.964; -0.436] |
| `w0.50 - risk_policy_fixed` | -0.750 [-1.761; 0.261] | -38.2 [-396.5; 320.1] | -0.100 [-1.190; 0.990] |

Вывод: добавление `uncorrectable_error_count` при `w=0.50` статистически значимо снижает риск-метрики относительно corrected-only, ценой роста занятости. Относительно `risk_policy_fixed` риск-метрики статистически сопоставимы; превосходство над fixed не доказано.

Важно: исходный measured-control используется как offline replay для калибровки:

`RTL trace → measured schedule → RTL replay`

После калибровки реализован closed-loop RTL-режим `MODE_MEASURED`, в котором управляющий уровень формируется внутри контроллера по приращениям `corrected_error_count` и `uncorrectable_error_count`.

Offline replay используется только как калибровочный этап. Closed-loop RTL-режим `MODE_MEASURED` является аппаратно замкнутым в пределах RTL-модели: уровень выбирается внутри контроллера по наблюдаемым счётчикам corrected/DED без внешнего расписания уровней и без использования истинного ряда ν(t).

## 5. Перемежение D=1/2/3 для мгновенных кластеров

Для трёхбитового мгновенного кластера проверены режимы:

| D | Раскладка |
|---:|---|
| 1 | 3 бита в одно кодовое слово |
| 2 | 2+1 по двум словам |
| 3 | 1+1+1 по трём словам |

Smoke-проверка показала:

| D | corrected | DED detections | unique |
|---:|---:|---:|---:|
| 1 | 2 | 109 | 3 |
| 2 | 5 | 140 | 5 |
| 3 | 15 | 0 | 0 |

В основной серии paired-delta показал:

| Сравнение | Результат по Δ unique |
|---|---:|
| `D3 - D1` | от -6.100 до -6.600, CI строго ниже нуля |
| `D3 - D2` | от -15.400 до -16.200, CI строго ниже нуля |
| `D3 slowest-fastest` | +0.400 [-0.123; 0.923] |

Вывод: перемежение D=3 статистически значимо снижает число уникальных неустранимых слов относительно D=1 и D=2. После достаточного перемежения остаточный риск снова становится чувствительным к интервалу скраббинга, то есть возвращается к накопительной модели риска.

Методический вывод: адаптивный скраббинг применим к накопительным ошибкам, но мгновенные многобитовые кластеры требуют предварительного пространственного разделения битов по кодовым словам.

## 6. Итоговая формулировка результата

Полученные эксперименты поддерживают следующую итоговую картину:

1. Теоретический выигрыш адаптивного восстановления определяется вариативностью риска и для идеальной оценки ограничен величиной `1 + CV²`.
2. В RTL-модели с конечной памятью адаптивные стратегии уменьшают занятость интерфейса памяти, но вне насыщения это является компромиссом с риск-метрикой, а не бесплатным улучшением.
3. Наблюдаемый measured-control возможен по счётчикам исполнения, но должен учитывать не только исправленные ошибки, но и DED-индикатор.
4. Measured-control в текущей версии является демонстрацией замкнутого RTL-механизма и телеметрии, а не самостоятельным доказанным выигрышем по риск-ресурсной метрике.
5. Closed-loop RTL-режим `MODE_MEASURED` реализует принцип внутри контроллера: уровень выбирается по счётчикам corrected/DED без внешнего расписания уровней. Новые latch-метрики показывают, что текущие веса не дают убедительного net win; поэтому блок используется как реализуемость и инженерный механизм, а не как центральная новизна.
6. Мгновенные многобитовые кластеры не устраняются увеличением частоты скраббинга; для них требуется перемежение.
7. При достаточном перемежении мгновенный кластер преобразуется в набор одиночных ошибок по разным кодовым словам, и задача снова становится управляемой периодом восстановления.

## 7. Ограничения

- measured-control replay используется как калибровочный этап; closed-loop RTL-режим `MODE_MEASURED` реализован отдельно и требует дальнейшей оптимизации порогов;
- физическая аппаратная проекция секундных интервалов оценивается отдельно от методической RTL-серии;
- статистические выводы относятся к выбранной модели событий, числу seed и сетке интервалов;
- adaptive-точки проверены относительно выбранной fixed-сетки, а не непрерывного множества всех возможных политик.

## 8. Основные файлы результатов

| Блок | Файл |
|---|---|
| Эффективность | `results/paper/tables/efficiency_scale_verification.md` |
| Контроль вне насыщения | `results/paper/unsaturated_control/unsaturated_control_summary.md` |
| Measured-control | `results/paper/measured_control/measured_control_summary.md` |
| Перемежение | `results/paper/interleaving/interleaving_summary.md` |
| True pair alignment | `results/paper/true_pair_alignment/true_pair_alignment_summary.md` |
| Theory consistency | `results/paper/theory_consistency/theory_consistency_summary.md` |
| Poisson accumulation validation | `results/paper/theory_consistency/poisson_accumulation_validation.md` |
| Risk-budget handoff | `results/paper/risk_budget_handoff/risk_budget_handoff_summary.md` |
| Accumulation-only RTL | `results/paper/accumulation_only_rtl/accumulation_only_rtl_summary.md` |
| Measured-control weight sweep | `results/paper/measured_control/weight_sweep/measured_weight_sweep_summary.md` |
| RTL synthesis resource estimates | `results/paper/synthesis/rtl_synthesis_summary.md` |

Current interleaving note: the final RTL interleaving results use true simultaneous multi-slot cluster injection. Groups belonging to one physical cluster are injected with the same `time_cycle`; for the current results `cluster_injection_skew = 0`. D=3 statistically significantly reduces `unique_uncorrectable_words` relative to D=1 and D=2 in the tested clustered-fault scenario. Inside D=3, the slowest-fastest paired delta for unique DUE has a confidence interval that includes zero, so this internal growth must not be called statistically significant.

## 9. Theory-aligned repository update

После отдельной theory-alignment итерации репозиторий теперь проверяет полную цепочку:

1. `p_m`, `h_m^(D)` и статус источников параметров задокументированы в `doc/mbu_parameter_sources.md`.
2. `evaluate_mbu_interleaving_criterion.py` читает таблицы `p_m/h_m`, считает `g_D`, `E_inst`, `E_residual` и таблицу подавления `h_m <= g_crit / p_m`.
3. `run_risk_budget_handoff.py` передаёт положительный `E_residual` в `scrub_risk_policy.py`, не создавая параллельный policy-builder.
4. `run_theory_consistency_checks.py` проверяет exact-vs-quadratic, наклон 2 при `g_D=0`, наклон 1 при `g_D>0` и пол `E_inst`.
5. `run_poisson_accumulation_validation.py` подтверждает accumulated-risk модель независимой Poisson Monte Carlo проверкой.
6. `tb_strategy_comparison.v` теперь выводит latched runtime DUE метрики: `new_due_count` и `repeated_due_detections`.

### 9.1. Accumulation-only RTL branch

В серии `results/paper/accumulation_only_rtl` проверен случай `D=3`, `cluster_bit_count=3`, где мгновенная same-event DED-составляющая устранена логическим перемежением.

| fixed interval | new DUE mean | final unique DUE mean | busy, % |
|---:|---:|---:|---:|
| 1089 | 0.000 | 0.000 | 23.100 |
| 2400 | 0.400 | 0.400 | 10.300 |

Paired delta `interval_2400_minus_1089` по `new_due_count`: 0.400 [-0.123; 0.923].

Вывод: серия подтверждает ветвь `g_D = 0` как RTL sanity check. Остаточные DUE малы; рост на более медленном интервале в этой серии не следует называть статистически значимым.

### 9.2. Measured-control latch-metric sweep

Новый closed-loop weight sweep оценивает measured-control не по повторному diagnostic DED counter, а по `new_due_count`, `repeated_due_detections`, final `unique_uncorrectable_words` и busy.

| config / strategy | busy, % | new DUE | final unique DUE | repeated DED |
|---|---:|---:|---:|---:|
| default fixed | 14.100 | 16.600 | 15.400 | 521.0 |
| default measured | 20.200 | 16.800 | 15.800 | 832.4 |
| corrected-only measured | 13.660 | 17.200 | 15.600 | 525.4 |
| DED-heavy measured | 20.200 | 16.800 | 15.800 | 832.4 |

Default measured-minus-fixed delta по busy_per_mille: 61.000 [61.000; 61.000]. Default measured-minus-fixed delta по `new_due_count`: 0.200 [-1.100; 1.500].

Corrected-only measured-minus-fixed delta по busy_per_mille: -4.400 [-8.895; 0.095]. Corrected-only measured-minus-fixed delta по `new_due_count`: 0.600 [-0.729; 1.929].

Вывод: measured-control не следует описывать как net resource win. Он подтверждает реализуемость замкнутого контроллера и наблюдаемой телеметрии, но центральный результат диссертации остаётся risk-limited chain: criterion, eta scale, residual-budget policy, RTL sanity checks.

## 10. RTL synthesis resource estimates

A final RTL synthesis resource-estimate pass was added for the synthesizable blocks used by the dissertation model. Testbenches, fault generators, result builders, and post-run audit scripts are not included in the hardware-cost estimate.

| target | Xilinx 7-series estimate: cells | FF | LUT | carry | mux |
|---|---:|---:|---:|---:|---:|
| `secded_32_39_encoder` | 106 | 0 | 33 | 0 | 2 |
| `secded_32_39_decoder` | 256 | 0 | 116 | 2 | 14 |
| `interval_selector` | 1082 | 38 | 306 | 11 | 186 |
| `measured_control_estimator` | 679 | 197 | 211 | 51 | 19 |
| `adaptive_scrub_controller` | 3220 | 730 | 883 | 183 | 214 |

For the full `adaptive_scrub_controller`, the technology-independent generic flow reports 2068 cells and 491 FF-equivalent cells. The Xilinx 7-series estimate reports 3220 cells, 730 FF, and 883 LUT.

Interpretation: this closes the dissertation Section 4.8 resource-estimate gap at RTL synthesis level. Fmax is not claimed from this Yosys-only flow; a valid maximum-frequency statement requires a concrete target device, timing constraints, and place-and-route.

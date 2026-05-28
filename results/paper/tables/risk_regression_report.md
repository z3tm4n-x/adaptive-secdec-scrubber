# Regression-check расчётных риск-результатов

## Назначение

Проверяется, что общий модуль `risk_core.py` и расчётная проверка шкалы эффективности воспроизводят ранее зафиксированные численные результаты для стратегий статьи 3.

## Итог

- Статус: PASS
- Проверок: 46
- Ошибок: 0

## Использование результатов

Этот отчёт фиксирует, что каноническая расчётная цепочка на базе `risk_core.py` воспроизводит численные результаты, используемые для шкалы эффективности.

Для текста диссертации следует использовать:

- `results/paper/tables/efficiency_scale_verification.md` — основной отчёт по шкале эффективности;
- `results/paper/tables/efficiency_scale_verification.csv` — машинно-читаемая таблица тех же расчётов;
- `results/paper/tables/risk_regression_report.md` — регрессионное подтверждение воспроизводимости чисел.

Старые или промежуточные риск-таблицы не следует цитировать напрямую, если они не включены в `doc/dissertation_mapping.md`.

## Таблица проверок

| Стратегия | Метрика | Ожидалось | Получено | |abs err| | rel err | Статус |
|---|---|---:|---:|---:|---:|---|
| `fixed_continuous_at_target` | `E` | 0.0100503358535 | 0.0100503358535 | 0.000e+00 | 0.000e+00 | PASS |
| `fixed_continuous_at_target` | `P_mission` | 0.01 | 0.01 | 0.000e+00 | 0.000e+00 | PASS |
| `fixed_continuous_at_target` | `cycles` | 17424471.3418 | 17424471.3418 | 0.000e+00 | 0.000e+00 | PASS |
| `fixed_continuous_at_target` | `Pmax_per_cycle` | 2.26938552698e-06 | 2.26938552698e-06 | 0.000e+00 | 0.000e+00 | PASS |
| `fixed_continuous_at_target` | `mean_tau_seconds` | 9.05430052398 | 9.05430052398 | 0.000e+00 | 0.000e+00 | PASS |
| `fixed_continuous_at_target` | `eta_gain_vs_fixed` | 1 | 1 | 0.000e+00 | 0.000e+00 | PASS |
| `fixed_continuous_at_target` | `rho_loss_vs_ideal` | 7.24295991773 | 7.24295991773 | 0.000e+00 | 0.000e+00 | PASS |
| `fixed_allowed_5s` | `E` | 0.00555003438801 | 0.00555003438801 | 0.000e+00 | 0.000e+00 | PASS |
| `fixed_allowed_5s` | `P_mission` | 0.00553466140051 | 0.00553466140051 | 0.000e+00 | 0.000e+00 | PASS |
| `fixed_allowed_5s` | `cycles` | 31553280 | 31553280 | 0.000e+00 | 0.000e+00 | PASS |
| `fixed_allowed_5s` | `Pmax_per_cycle` | 6.92051603255e-07 | 6.92051603255e-07 | 0.000e+00 | 0.000e+00 | PASS |
| `fixed_allowed_5s` | `mean_tau_seconds` | 5 | 5 | 0.000e+00 | 0.000e+00 | PASS |
| `fixed_allowed_5s` | `eta_gain_vs_fixed` | 0.552223773306 | 0.552223773306 | 0.000e+00 | 0.000e+00 | PASS |
| `fixed_allowed_5s` | `rho_loss_vs_ideal` | 13.1159871557 | 13.1159871557 | 0.000e+00 | 0.000e+00 | PASS |
| `adaptive_current_continuous` | `c` | 0.128842118041 | 0.128842118041 | 0.000e+00 | 0.000e+00 | PASS |
| `adaptive_current_continuous` | `E` | 0.0100503358535 | 0.0100503358535 | 0.000e+00 | 0.000e+00 | PASS |
| `adaptive_current_continuous` | `P_mission` | 0.01 | 0.01 | 0.000e+00 | 0.000e+00 | PASS |
| `adaptive_current_continuous` | `cycles` | 2405711.41352 | 2405711.41352 | 0.000e+00 | 0.000e+00 | PASS |
| `adaptive_current_continuous` | `Pmax_per_cycle` | 4.17769803851e-09 | 4.17769803851e-09 | 0.000e+00 | 0.000e+00 | PASS |
| `adaptive_current_continuous` | `mean_tau_seconds` | 96.5657390135 | 96.5657390135 | 0.000e+00 | 0.000e+00 | PASS |
| `adaptive_current_continuous` | `eta_gain_vs_fixed` | 7.24295991773 | 7.24295991773 | 0.000e+00 | 0.000e+00 | PASS |
| `adaptive_current_continuous` | `rho_loss_vs_ideal` | 1 | 1 | 0.000e+00 | 0.000e+00 | PASS |
| `adaptive_current_discrete` | `c` | 0.127059554228 | 0.127059554228 | 0.000e+00 | 0.000e+00 | PASS |
| `adaptive_current_discrete` | `E` | 0.0100501809522 | 0.0100501809522 | 0.000e+00 | 0.000e+00 | PASS |
| `adaptive_current_discrete` | `P_mission` | 0.00999984664774 | 0.00999984664774 | 0.000e+00 | 0.000e+00 | PASS |
| `adaptive_current_discrete` | `cycles` | 2543790 | 2543790 | 0.000e+00 | 0.000e+00 | PASS |
| `adaptive_current_discrete` | `Pmax_per_cycle` | 2.76820641302e-08 | 2.76820641302e-08 | 0.000e+00 | 0.000e+00 | PASS |
| `adaptive_current_discrete` | `mean_tau_seconds` | 87.0203085068 | 87.0203085068 | 0.000e+00 | 0.000e+00 | PASS |
| `adaptive_current_discrete` | `eta_gain_vs_fixed` | 6.84980731184 | 6.84980731184 | 0.000e+00 | 0.000e+00 | PASS |
| `adaptive_current_discrete` | `rho_loss_vs_ideal` | 1.05739615554 | 1.05739615554 | 0.000e+00 | 0.000e+00 | PASS |
| `adaptive_delayed_1h_discrete` | `c` | 0.12090343247 | 0.12090343247 | 0.000e+00 | 0.000e+00 | PASS |
| `adaptive_delayed_1h_discrete` | `E` | 0.0100502237581 | 0.0100502237581 | 0.000e+00 | 0.000e+00 | PASS |
| `adaptive_delayed_1h_discrete` | `P_mission` | 0.00999988902558 | 0.00999988902558 | 0.000e+00 | 0.000e+00 | PASS |
| `adaptive_delayed_1h_discrete` | `cycles` | 2653530 | 2653530 | 0.000e+00 | 0.000e+00 | PASS |
| `adaptive_delayed_1h_discrete` | `Pmax_per_cycle` | 1.58576414452e-06 | 1.58576414452e-06 | 0.000e+00 | 0.000e+00 | PASS |
| `adaptive_delayed_1h_discrete` | `mean_tau_seconds` | 84.7550657174 | 84.7550657174 | 0.000e+00 | 0.000e+00 | PASS |
| `adaptive_delayed_1h_discrete` | `eta_gain_vs_fixed` | 6.56652509743 | 6.56652509743 | 0.000e+00 | 0.000e+00 | PASS |
| `adaptive_delayed_1h_discrete` | `rho_loss_vs_ideal` | 1.10301259955 | 1.10301259955 | 0.000e+00 | 0.000e+00 | PASS |
| `adaptive_modified_delayed_1h_discrete` | `c` | 0.125087686835 | 0.125087686835 | 0.000e+00 | 0.000e+00 | PASS |
| `adaptive_modified_delayed_1h_discrete` | `E` | 0.0100501474398 | 0.0100501474398 | 0.000e+00 | 0.000e+00 | PASS |
| `adaptive_modified_delayed_1h_discrete` | `P_mission` | 0.00999981347043 | 0.00999981347043 | 0.000e+00 | 0.000e+00 | PASS |
| `adaptive_modified_delayed_1h_discrete` | `cycles` | 2594580 | 2594580 | 0.000e+00 | 0.000e+00 | PASS |
| `adaptive_modified_delayed_1h_discrete` | `Pmax_per_cycle` | 1.23947578455e-06 | 1.23947578455e-06 | 0.000e+00 | 0.000e+00 | PASS |
| `adaptive_modified_delayed_1h_discrete` | `mean_tau_seconds` | 86.2632347572 | 86.2632347572 | 0.000e+00 | 0.000e+00 | PASS |
| `adaptive_modified_delayed_1h_discrete` | `eta_gain_vs_fixed` | 6.7157194389 | 6.7157194389 | 0.000e+00 | 0.000e+00 | PASS |
| `adaptive_modified_delayed_1h_discrete` | `rho_loss_vs_ideal` | 1.07850841353 | 1.07850841353 | 0.000e+00 | 0.000e+00 | PASS |

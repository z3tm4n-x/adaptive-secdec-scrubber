# Аудит исполнения risk-policy в RTL

## Назначение

Проверяется, что RTL-стенд исполняет интервалы, соответствующие выбранной политике: fixed использует постоянный интервал, table использует interval[current_level], а threshold ограничен тремя заданными интервалами.

## Сводка

| strategy | trace rows | RTL scrub cycles | trace final scrub cycles | Δ scrub | reads | expected reads | Δ reads | safe entries | selected interval range | interval mismatches | control level mismatches |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `fixed` | 341 | 341 | 341 | 0 | 5458 | 5456 | 2 | 0 | 80–80 | 0 | 0 |
| `table` | 355 | 355 | 355 | 0 | 5680 | 5680 | 0 | 0 | 5–120 | 0 | 0 |
| `threshold` | 448 | 448 | 448 | 0 | 7179 | 7168 | 11 | 0 | 1–60 | 0 | 0 |

## Критерии прохождения

- `scrub_cycle_delta = 0` для всех стратегий.
- `0 <= read_delta < 16`: допускаются чтения незавершённого прохода в конце окна моделирования, так как ADDR_WIDTH=4 и полный проход читает 16 слов.
- `safe_entries = 0` и `trace_safe_rows = 0`.
- `interval_mismatches = 0`.
- Для `table`: `control_level_mismatches = 0`.

## Итог

**PASS:** исполнение интервальной политики в RTL соответствует ожидаемой конфигурации.

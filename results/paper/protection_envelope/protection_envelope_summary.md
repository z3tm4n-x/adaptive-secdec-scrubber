# Protection envelope for SECDED scrubbing

## Purpose

This report turns the instant/accumulated decomposition into an engineering applicability map. It classifies each scenario into one of three regions: architecture change required, bandwidth/tau_min insufficient, or scrub-period selectable.

The classification uses:

- `E_inst = g_D * N_events`
- `rho_D = E_inst / E*`
- `E_residual = E* - E_inst`
- `E_acc_min`: accumulated-risk floor when all bins use `tau_min`

## Inputs

- Upset-rate input: `data/upsets.xlsx`
- Start index: 0
- Window size: 43824
- Target mission probability: 0.01
- Target risk measure E*: 0.0100503358535
- tau_min: 1 s

## Region definitions

| region | condition | interpretation |
|---|---|---|
| A | `rho_D >= 1` | instant dangerous mapping alone exceeds the mission budget; period selection cannot solve the problem |
| B | `rho_D < 1` and `E_acc_min > E_residual` | instant term is acceptable, but the minimum scrub interval is still insufficient |
| C | `rho_D < 1` and `E_acc_min <= E_residual` | SECDED scrubbing is applicable; proceed to residual-budget period selection |

## Scenario table

| scenario | D | nu_scale | p2 | p3 | p4 | g_D | rho_D | E_residual | E_acc_min | E_acc_min/E_residual | status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `bandwidth_limited_accumulation` | 1 | 4 | 0 | 0 | 0 | 0 | 0 | 0.0100503 | 0.0177601 | 1.76712 | `bandwidth_or_tau_min_insufficient` |
| `bandwidth_limited_accumulation` | 2 | 4 | 0 | 0 | 0 | 0 | 0 | 0.0100503 | 0.0177601 | 1.76712 | `bandwidth_or_tau_min_insufficient` |
| `bandwidth_limited_accumulation` | 3 | 4 | 0 | 0 | 0 | 0 | 0 | 0.0100503 | 0.0177601 | 1.76712 | `bandwidth_or_tau_min_insufficient` |
| `bandwidth_limited_accumulation` | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0.0100503 | 0.0177601 | 1.76712 | `bandwidth_or_tau_min_insufficient` |
| `four_bit_tail_requires_D4` | 1 | 1 | 0 | 0 | 2e-08 | 2e-08 | 1.99 | -0.00994966 | 0.00111001 | inf | `architecture_change_required` |
| `four_bit_tail_requires_D4` | 2 | 1 | 0 | 0 | 2e-08 | 2e-08 | 1.99 | -0.00994966 | 0.00111001 | inf | `architecture_change_required` |
| `four_bit_tail_requires_D4` | 3 | 1 | 0 | 0 | 2e-08 | 2e-08 | 1.99 | -0.00994966 | 0.00111001 | inf | `architecture_change_required` |
| `four_bit_tail_requires_D4` | 4 | 1 | 0 | 0 | 2e-08 | 0 | 0 | 0.0100503 | 0.00111001 | 0.110445 | `scrub_period_selectable` |
| `light_3bit_tail` | 1 | 1 | 0 | 5e-09 | 0 | 5e-09 | 0.497 | 0.00505034 | 0.00111001 | 0.219789 | `scrub_period_selectable` |
| `light_3bit_tail` | 2 | 1 | 0 | 5e-09 | 0 | 5e-09 | 0.497 | 0.00505034 | 0.00111001 | 0.219789 | `scrub_period_selectable` |
| `light_3bit_tail` | 3 | 1 | 0 | 5e-09 | 0 | 0 | 0 | 0.0100503 | 0.00111001 | 0.110445 | `scrub_period_selectable` |
| `light_3bit_tail` | 4 | 1 | 0 | 5e-09 | 0 | 0 | 0 | 0.0100503 | 0.00111001 | 0.110445 | `scrub_period_selectable` |
| `overbudget_3bit_tail` | 1 | 1 | 0 | 2e-08 | 0 | 2e-08 | 1.99 | -0.00994966 | 0.00111001 | inf | `architecture_change_required` |
| `overbudget_3bit_tail` | 2 | 1 | 0 | 2e-08 | 0 | 2e-08 | 1.99 | -0.00994966 | 0.00111001 | inf | `architecture_change_required` |
| `overbudget_3bit_tail` | 3 | 1 | 0 | 2e-08 | 0 | 0 | 0 | 0.0100503 | 0.00111001 | 0.110445 | `scrub_period_selectable` |
| `overbudget_3bit_tail` | 4 | 1 | 0 | 2e-08 | 0 | 0 | 0 | 0.0100503 | 0.00111001 | 0.110445 | `scrub_period_selectable` |

## Compact status map

| scenario | D=1 | D=2 | D=3 | D=4 |
|---|---|---|---|---|
| `bandwidth_limited_accumulation` | `bandwidth_or_tau_min_insufficient` | `bandwidth_or_tau_min_insufficient` | `bandwidth_or_tau_min_insufficient` | `bandwidth_or_tau_min_insufficient` |
| `four_bit_tail_requires_D4` | `architecture_change_required` | `architecture_change_required` | `architecture_change_required` | `scrub_period_selectable` |
| `light_3bit_tail` | `scrub_period_selectable` | `scrub_period_selectable` | `scrub_period_selectable` | `scrub_period_selectable` |
| `overbudget_3bit_tail` | `architecture_change_required` | `architecture_change_required` | `scrub_period_selectable` | `scrub_period_selectable` |

## Interpretation

`E_acc_min` depends on the accumulated-error-rate series used by the scenario. The `nu_scale` column explicitly shows when a scenario scales `ν(t)` to exercise the bandwidth/tau_min insufficiency region; therefore rows with `g_D = 0` may still have different accumulated-risk floors.

The envelope separates two failure modes that are easy to conflate. If `rho_D >= 1`, no scrub period can satisfy the target because the instant dangerous component already consumes the whole risk measure. If `rho_D < 1` but `E_acc_min > E_residual`, the issue is not the instant MCU mapping but the practical lower bound on the scrub interval.

The scenario values are illustrative design points, not measured device multiplicity distributions. Their role is to exercise the three regions of the design procedure and to support the Chapter 2 feasibility argument.

## Status counts

| status | rows |
|---|---:|
| `architecture_change_required` | 5 |
| `bandwidth_or_tau_min_insufficient` | 4 |
| `scrub_period_selectable` | 7 |

# Risk-budget handoff from MBU criterion to scrub policy

## Purpose

This report connects the instant-MBU applicability criterion with the accumulated-risk scrub policy. The criterion computes E_inst = N_events * g_D. If E_inst <= E*, the remaining budget E_residual = E* - E_inst is passed to the accumulated-risk policy builder.

The handoff is intentionally thin: it reuses evaluate_mbu_interleaving_criterion.py and scrub_risk_policy.py instead of creating a parallel policy builder.

## Inputs

- Criterion CSV: `results/paper/tables/mbu_interleaving_criterion_examples.csv`
- Upset input: `data/upsets.xlsx`
- Start index: 0
- Window size: 43824

## Case summary

| case | scenario | D | E* | E_inst | E_residual | P_residual | pass | policy output |
|---|---|---:|---:|---:|---:|---:|---|---|
| `partial_instant_residual_D1` | `subbudget_3bit_clusters` | 1 | 0.0100503 | 0.005 | 0.00505034 | 0.0050376 | yes | `results/paper/risk_budget_handoff/partial_instant_residual_D1` |
| `accumulation_only_gD0_D3` | `subbudget_3bit_clusters` | 3 | 0.0100503 | 0 | 0.0100503 | 0.01 | yes | `results/paper/risk_budget_handoff/accumulation_only_gD0_D3` |

## Policy rows under residual budgets

| case | policy strategy | E used by policy | utilization of E_residual | budget slack | P mission | cycles | tau range, s |
|---|---|---:|---:|---:|---:|---:|---:|
| `partial_instant_residual_D1` | `adaptive_current_continuous` | 0.00505034 | 1 | 0 | 0.0050376 | 4787445.503 | 0.195--94.002 |
| `partial_instant_residual_D1` | `adaptive_current_discrete` | 0.00505018 | 0.999969 | 1.54853e-07 | 0.00503745 | 5624700.000 | 1.000--60.000 |
| `partial_instant_residual_D1` | `adaptive_delayed_1h_discrete` | 0.00505027 | 0.999986 | 6.82185e-08 | 0.00503754 | 5829960.000 | 1.000--60.000 |
| `partial_instant_residual_D1` | `fixed_continuous_at_target` | 0.00505034 | 1 | 0 | 0.0050376 | 34675275.889 | 4.550--4.550 |
| `partial_instant_residual_D1` | `fixed_allowed_2s` | 0.00222001 | 0.439577 | 0.00283032 | 0.00221755 | 78883200.000 | 2.000--2.000 |
| `accumulation_only_gD0_D3` | `adaptive_current_continuous` | 0.0100503 | 1 | 0 | 0.01 | 2405711.414 | 0.388--187.067 |
| `accumulation_only_gD0_D3` | `adaptive_current_discrete` | 0.0100502 | 0.999985 | 1.54901e-07 | 0.00999985 | 2543790.000 | 1.000--120.000 |
| `accumulation_only_gD0_D3` | `adaptive_delayed_1h_discrete` | 0.0100502 | 0.999989 | 1.12095e-07 | 0.00999989 | 2653530.000 | 1.000--120.000 |
| `accumulation_only_gD0_D3` | `fixed_continuous_at_target` | 0.0100503 | 1 | 0 | 0.01 | 17424471.342 | 9.054--9.054 |
| `accumulation_only_gD0_D3` | `fixed_allowed_5s` | 0.00555003 | 0.552224 | 0.0045003 | 0.00553466 | 31553280.000 | 5.000--5.000 |

## Interpretation

The partial-residual case demonstrates the mixed regime: instant MBU consumes part of the mission budget and leaves a smaller accumulated-risk budget for scrubbing. The g_D=0 case demonstrates the accumulation-only regime: all target risk remains available for interval optimization. A finite interval grid may underuse the residual budget; this appears as positive policy_budget_slack rather than a criterion failure.

These outputs are policy-construction artifacts. They do not by themselves prove a flight implementation; they document that the repository now executes the same budget chain used by the theory.

# MBU interleaving criterion examples

## Purpose

This report gives numerical examples for the go/no-go criterion of periodic scrubbing under instant multi-bit events. The default mode is deterministic and logical: an m-bit physical cluster is distributed over D codewords in a round-robin way, and SECDED is considered unsafe when two or more bits of the same event land in one codeword. The script can also consume p_m and h_m^(D) from CSV files.

The criterion is:

- E_inst = N_events * g_D
- g_D <= E* / N_events
- E_residual = E* - E_inst

If the criterion is violated, reducing the scrub period cannot remove this instant component. The remedy must change interleaving, code strength, logical placement, or memory organization.

- Target mission probability: 0.01
- Target risk measure E*: 0.0100503358535
- p_m source: `built_in_default`
- h_m^(D) source: `logical_round_robin`

## Logical danger map

| m-bit event | D=1 | D=2 | D=3 | D=4 |
|---:|---:|---:|---:|---:|
| 1 | 0 | 0 | 0 | 0 |
| 2 | 1 | 0 | 0 | 0 |
| 3 | 1 | 1 | 0 | 0 |
| 4 | 1 | 1 | 1 | 0 |

Value 1 means instant SECDED-DUE is possible under the simplified mapping; value 0 means the event is split into single-bit errors across codewords.

## Scenario results

| scenario | N events | D | p2 | p3 | p4 | g_D | g_D limit | E_inst | E_residual | residual fraction | pass | action |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| `subbudget_3bit_clusters` | 1e+06 | 1 | 0 | 5e-09 | 0 | 5e-09 | 1.01e-08 | 0.005 | 0.00505 | 0.503 | yes | scrubbing may use residual accumulated-risk budget |
| `subbudget_3bit_clusters` | 1e+06 | 2 | 0 | 5e-09 | 0 | 5e-09 | 1.01e-08 | 0.005 | 0.00505 | 0.503 | yes | scrubbing may use residual accumulated-risk budget |
| `subbudget_3bit_clusters` | 1e+06 | 3 | 0 | 5e-09 | 0 | 0 | 1.01e-08 | 0 | 0.0101 | 1 | yes | scrubbing may optimize only accumulated risk |
| `subbudget_3bit_clusters` | 1e+06 | 4 | 0 | 5e-09 | 0 | 0 | 1.01e-08 | 0 | 0.0101 | 1 | yes | scrubbing may optimize only accumulated risk |
| `rare_3bit_clusters` | 1e+06 | 1 | 0 | 2e-08 | 0 | 2e-08 | 1.01e-08 | 0.02 | -0.00995 | -0.99 | no | increase interleaving or reduce instant MBU mapping probability |
| `rare_3bit_clusters` | 1e+06 | 2 | 0 | 2e-08 | 0 | 2e-08 | 1.01e-08 | 0.02 | -0.00995 | -0.99 | no | increase interleaving or reduce instant MBU mapping probability |
| `rare_3bit_clusters` | 1e+06 | 3 | 0 | 2e-08 | 0 | 0 | 1.01e-08 | 0 | 0.0101 | 1 | yes | scrubbing may optimize only accumulated risk |
| `rare_3bit_clusters` | 1e+06 | 4 | 0 | 2e-08 | 0 | 0 | 1.01e-08 | 0 | 0.0101 | 1 | yes | scrubbing may optimize only accumulated risk |
| `strong_3bit_clusters` | 1e+06 | 1 | 0 | 2e-07 | 0 | 2e-07 | 1.01e-08 | 0.2 | -0.19 | -18.9 | no | increase interleaving or reduce instant MBU mapping probability |
| `strong_3bit_clusters` | 1e+06 | 2 | 0 | 2e-07 | 0 | 2e-07 | 1.01e-08 | 0.2 | -0.19 | -18.9 | no | increase interleaving or reduce instant MBU mapping probability |
| `strong_3bit_clusters` | 1e+06 | 3 | 0 | 2e-07 | 0 | 0 | 1.01e-08 | 0 | 0.0101 | 1 | yes | scrubbing may optimize only accumulated risk |
| `strong_3bit_clusters` | 1e+06 | 4 | 0 | 2e-07 | 0 | 0 | 1.01e-08 | 0 | 0.0101 | 1 | yes | scrubbing may optimize only accumulated risk |
| `mixed_2bit_3bit` | 1e+06 | 1 | 5e-08 | 1e-07 | 0 | 1.5e-07 | 1.01e-08 | 0.15 | -0.14 | -13.9 | no | increase interleaving or reduce instant MBU mapping probability |
| `mixed_2bit_3bit` | 1e+06 | 2 | 5e-08 | 1e-07 | 0 | 1e-07 | 1.01e-08 | 0.1 | -0.0899 | -8.95 | no | increase interleaving or reduce instant MBU mapping probability |
| `mixed_2bit_3bit` | 1e+06 | 3 | 5e-08 | 1e-07 | 0 | 0 | 1.01e-08 | 0 | 0.0101 | 1 | yes | scrubbing may optimize only accumulated risk |
| `mixed_2bit_3bit` | 1e+06 | 4 | 5e-08 | 1e-07 | 0 | 0 | 1.01e-08 | 0 | 0.0101 | 1 | yes | scrubbing may optimize only accumulated risk |
| `four_bit_clusters` | 1e+06 | 1 | 0 | 0 | 2e-07 | 2e-07 | 1.01e-08 | 0.2 | -0.19 | -18.9 | no | increase interleaving or reduce instant MBU mapping probability |
| `four_bit_clusters` | 1e+06 | 2 | 0 | 0 | 2e-07 | 2e-07 | 1.01e-08 | 0.2 | -0.19 | -18.9 | no | increase interleaving or reduce instant MBU mapping probability |
| `four_bit_clusters` | 1e+06 | 3 | 0 | 0 | 2e-07 | 2e-07 | 1.01e-08 | 0.2 | -0.19 | -18.9 | no | increase interleaving or reduce instant MBU mapping probability |
| `four_bit_clusters` | 1e+06 | 4 | 0 | 0 | 2e-07 | 0 | 1.01e-08 | 0 | 0.0101 | 1 | yes | scrubbing may optimize only accumulated risk |
| `high_event_count_low_probability` | 1e+08 | 1 | 0 | 2e-10 | 0 | 2e-10 | 1.01e-10 | 0.02 | -0.00995 | -0.99 | no | increase interleaving or reduce instant MBU mapping probability |
| `high_event_count_low_probability` | 1e+08 | 2 | 0 | 2e-10 | 0 | 2e-10 | 1.01e-10 | 0.02 | -0.00995 | -0.99 | no | increase interleaving or reduce instant MBU mapping probability |
| `high_event_count_low_probability` | 1e+08 | 3 | 0 | 2e-10 | 0 | 0 | 1.01e-10 | 0 | 0.0101 | 1 | yes | scrubbing may optimize only accumulated risk |
| `high_event_count_low_probability` | 1e+08 | 4 | 0 | 2e-10 | 0 | 0 | 1.01e-10 | 0 | 0.0101 | 1 | yes | scrubbing may optimize only accumulated risk |

## Suppression requirements

For a single multiplicity class considered alone, the criterion implies h_m^(D) <= g_crit / p_m, where g_crit = E* / N_events. This bound itself is D-independent; rows are repeated for each D so the required bound can be compared with the actual mapping value h_m^(D). In mixed cases this is a per-class diagnostic bound; the actual criterion remains the sum g_D = sum_m p_m h_m^(D).

| scenario | N events | D | m | p_m | g_crit | required h_m max | capped at 1 | interpretation |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `subbudget_3bit_clusters` | 1e+06 | 1 | 3 | 5e-09 | 1.01e-08 | 2.01 | 1 | no suppression required for this single class alone |
| `subbudget_3bit_clusters` | 1e+06 | 2 | 3 | 5e-09 | 1.01e-08 | 2.01 | 1 | no suppression required for this single class alone |
| `subbudget_3bit_clusters` | 1e+06 | 3 | 3 | 5e-09 | 1.01e-08 | 2.01 | 1 | no suppression required for this single class alone |
| `subbudget_3bit_clusters` | 1e+06 | 4 | 3 | 5e-09 | 1.01e-08 | 2.01 | 1 | no suppression required for this single class alone |
| `rare_3bit_clusters` | 1e+06 | 1 | 3 | 2e-08 | 1.01e-08 | 0.503 | 0.503 | logical mapping must suppress this class below the listed h_m limit |
| `rare_3bit_clusters` | 1e+06 | 2 | 3 | 2e-08 | 1.01e-08 | 0.503 | 0.503 | logical mapping must suppress this class below the listed h_m limit |
| `rare_3bit_clusters` | 1e+06 | 3 | 3 | 2e-08 | 1.01e-08 | 0.503 | 0.503 | logical mapping must suppress this class below the listed h_m limit |
| `rare_3bit_clusters` | 1e+06 | 4 | 3 | 2e-08 | 1.01e-08 | 0.503 | 0.503 | logical mapping must suppress this class below the listed h_m limit |
| `strong_3bit_clusters` | 1e+06 | 1 | 3 | 2e-07 | 1.01e-08 | 0.0503 | 0.0503 | logical mapping must suppress this class below the listed h_m limit |
| `strong_3bit_clusters` | 1e+06 | 2 | 3 | 2e-07 | 1.01e-08 | 0.0503 | 0.0503 | logical mapping must suppress this class below the listed h_m limit |
| `strong_3bit_clusters` | 1e+06 | 3 | 3 | 2e-07 | 1.01e-08 | 0.0503 | 0.0503 | logical mapping must suppress this class below the listed h_m limit |
| `strong_3bit_clusters` | 1e+06 | 4 | 3 | 2e-07 | 1.01e-08 | 0.0503 | 0.0503 | logical mapping must suppress this class below the listed h_m limit |
| `mixed_2bit_3bit` | 1e+06 | 1 | 2 | 5e-08 | 1.01e-08 | 0.201 | 0.201 | logical mapping must suppress this class below the listed h_m limit |
| `mixed_2bit_3bit` | 1e+06 | 1 | 3 | 1e-07 | 1.01e-08 | 0.101 | 0.101 | logical mapping must suppress this class below the listed h_m limit |
| `mixed_2bit_3bit` | 1e+06 | 2 | 2 | 5e-08 | 1.01e-08 | 0.201 | 0.201 | logical mapping must suppress this class below the listed h_m limit |
| `mixed_2bit_3bit` | 1e+06 | 2 | 3 | 1e-07 | 1.01e-08 | 0.101 | 0.101 | logical mapping must suppress this class below the listed h_m limit |
| `mixed_2bit_3bit` | 1e+06 | 3 | 2 | 5e-08 | 1.01e-08 | 0.201 | 0.201 | logical mapping must suppress this class below the listed h_m limit |
| `mixed_2bit_3bit` | 1e+06 | 3 | 3 | 1e-07 | 1.01e-08 | 0.101 | 0.101 | logical mapping must suppress this class below the listed h_m limit |
| `mixed_2bit_3bit` | 1e+06 | 4 | 2 | 5e-08 | 1.01e-08 | 0.201 | 0.201 | logical mapping must suppress this class below the listed h_m limit |
| `mixed_2bit_3bit` | 1e+06 | 4 | 3 | 1e-07 | 1.01e-08 | 0.101 | 0.101 | logical mapping must suppress this class below the listed h_m limit |
| `four_bit_clusters` | 1e+06 | 1 | 4 | 2e-07 | 1.01e-08 | 0.0503 | 0.0503 | logical mapping must suppress this class below the listed h_m limit |
| `four_bit_clusters` | 1e+06 | 2 | 4 | 2e-07 | 1.01e-08 | 0.0503 | 0.0503 | logical mapping must suppress this class below the listed h_m limit |
| `four_bit_clusters` | 1e+06 | 3 | 4 | 2e-07 | 1.01e-08 | 0.0503 | 0.0503 | logical mapping must suppress this class below the listed h_m limit |
| `four_bit_clusters` | 1e+06 | 4 | 4 | 2e-07 | 1.01e-08 | 0.0503 | 0.0503 | logical mapping must suppress this class below the listed h_m limit |
| `high_event_count_low_probability` | 1e+08 | 1 | 3 | 2e-10 | 1.01e-10 | 0.503 | 0.503 | logical mapping must suppress this class below the listed h_m limit |
| `high_event_count_low_probability` | 1e+08 | 2 | 3 | 2e-10 | 1.01e-10 | 0.503 | 0.503 | logical mapping must suppress this class below the listed h_m limit |
| `high_event_count_low_probability` | 1e+08 | 3 | 3 | 2e-10 | 1.01e-10 | 0.503 | 0.503 | logical mapping must suppress this class below the listed h_m limit |
| `high_event_count_low_probability` | 1e+08 | 4 | 3 | 2e-10 | 1.01e-10 | 0.503 | 0.503 | logical mapping must suppress this class below the listed h_m limit |

## Interpretation

The key point is that instant multi-bit events create a period-independent risk component. If E_inst already exceeds E*, no scrub interval can satisfy the target. If E_inst is below the target, the positive residual budget E_residual can be passed to the accumulated-risk scrub-period policy.

The p_m and h_m^(D) values used here are either built-in examples or values loaded from explicit CSV files. Values marked as illustrative or logical_round_robin must not be presented as measured technology parameters.


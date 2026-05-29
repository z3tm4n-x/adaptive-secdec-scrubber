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
- p_m source: `data/mbu_pm_logical_example.csv`
- h_m^(D) source: `data/mbu_hmd_logical_round_robin.csv`

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
| `csv_logical_example` | 1e+06 | 1 | 0.005 | 0.0005 | 0 | 0.0055 | 1.01e-08 | 5.5e+03 | -5.5e+03 | -5.47e+05 | no | increase interleaving or reduce instant MBU mapping probability |
| `csv_logical_example` | 1e+06 | 2 | 0.005 | 0.0005 | 0 | 0.0005 | 1.01e-08 | 500 | -500 | -4.97e+04 | no | increase interleaving or reduce instant MBU mapping probability |
| `csv_logical_example` | 1e+06 | 3 | 0.005 | 0.0005 | 0 | 0 | 1.01e-08 | 0 | 0.0101 | 1 | yes | scrubbing may optimize only accumulated risk |
| `csv_logical_example` | 1e+06 | 4 | 0.005 | 0.0005 | 0 | 0 | 1.01e-08 | 0 | 0.0101 | 1 | yes | scrubbing may optimize only accumulated risk |

## Suppression requirements

For a single multiplicity class considered alone, the criterion implies h_m^(D) <= g_crit / p_m, where g_crit = E* / N_events. This bound itself is D-independent; rows are repeated for each D so the required bound can be compared with the actual mapping value h_m^(D). In mixed cases this is a per-class diagnostic bound; the actual criterion remains the sum g_D = sum_m p_m h_m^(D).

| scenario | N events | D | m | p_m | g_crit | required h_m max | capped at 1 | interpretation |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `csv_logical_example` | 1e+06 | 1 | 2 | 0.005 | 1.01e-08 | 2.01e-06 | 2.01e-06 | logical mapping must suppress this class below the listed h_m limit |
| `csv_logical_example` | 1e+06 | 1 | 3 | 0.0005 | 1.01e-08 | 2.01e-05 | 2.01e-05 | logical mapping must suppress this class below the listed h_m limit |
| `csv_logical_example` | 1e+06 | 2 | 2 | 0.005 | 1.01e-08 | 2.01e-06 | 2.01e-06 | logical mapping must suppress this class below the listed h_m limit |
| `csv_logical_example` | 1e+06 | 2 | 3 | 0.0005 | 1.01e-08 | 2.01e-05 | 2.01e-05 | logical mapping must suppress this class below the listed h_m limit |
| `csv_logical_example` | 1e+06 | 3 | 2 | 0.005 | 1.01e-08 | 2.01e-06 | 2.01e-06 | logical mapping must suppress this class below the listed h_m limit |
| `csv_logical_example` | 1e+06 | 3 | 3 | 0.0005 | 1.01e-08 | 2.01e-05 | 2.01e-05 | logical mapping must suppress this class below the listed h_m limit |
| `csv_logical_example` | 1e+06 | 4 | 2 | 0.005 | 1.01e-08 | 2.01e-06 | 2.01e-06 | logical mapping must suppress this class below the listed h_m limit |
| `csv_logical_example` | 1e+06 | 4 | 3 | 0.0005 | 1.01e-08 | 2.01e-05 | 2.01e-05 | logical mapping must suppress this class below the listed h_m limit |

## Interpretation

The key point is that instant multi-bit events create a period-independent risk component. If E_inst already exceeds E*, no scrub interval can satisfy the target. If E_inst is below the target, the positive residual budget E_residual can be passed to the accumulated-risk scrub-period policy.

The p_m and h_m^(D) values used here are either built-in examples or values loaded from explicit CSV files. Values marked as illustrative or logical_round_robin must not be presented as measured technology parameters.


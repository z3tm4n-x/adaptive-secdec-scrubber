# MBU interleaving criterion examples

## Purpose

This report gives numerical examples for the go/no-go criterion of periodic scrubbing under instant multi-bit events. The examples are intentionally simple and deterministic: an m-bit physical cluster is distributed over D codewords in a round-robin way, and SECDED is considered unsafe when two or more bits of the same event land in one codeword.

The criterion is:

- E_inst = N_events * g_D
- g_D <= E* / N_events

If the criterion is violated, reducing the scrub period cannot remove this instant component. The remedy must change interleaving, code strength, logical placement, or memory organization.

- Target mission probability: 0.01
- Target risk measure E*: 0.0100503358535

## Logical danger map

| m-bit event | D=1 | D=2 | D=3 | D=4 |
|---:|---:|---:|---:|---:|
| 1 | 0 | 0 | 0 | 0 |
| 2 | 1 | 0 | 0 | 0 |
| 3 | 1 | 1 | 0 | 0 |
| 4 | 1 | 1 | 1 | 0 |

Value 1 means instant SECDED-DUE is possible under the simplified mapping; value 0 means the event is split into single-bit errors across codewords.

## Scenario results

| scenario | N events | D | p2 | p3 | p4 | g_D | g_D limit | E_inst | E_residual | pass | action |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| `subbudget_3bit_clusters` | 1e+06 | 1 | 0 | 5e-09 | 0 | 5e-09 | 1.01e-08 | 0.005 | 0.00505 | yes | scrubbing may use residual accumulated-risk budget |
| `subbudget_3bit_clusters` | 1e+06 | 2 | 0 | 5e-09 | 0 | 5e-09 | 1.01e-08 | 0.005 | 0.00505 | yes | scrubbing may use residual accumulated-risk budget |
| `subbudget_3bit_clusters` | 1e+06 | 3 | 0 | 5e-09 | 0 | 0 | 1.01e-08 | 0 | 0.0101 | yes | scrubbing may optimize only accumulated risk |
| `subbudget_3bit_clusters` | 1e+06 | 4 | 0 | 5e-09 | 0 | 0 | 1.01e-08 | 0 | 0.0101 | yes | scrubbing may optimize only accumulated risk |
| `rare_3bit_clusters` | 1e+06 | 1 | 0 | 2e-08 | 0 | 2e-08 | 1.01e-08 | 0.02 | -0.00995 | no | increase interleaving or reduce instant MBU mapping probability |
| `rare_3bit_clusters` | 1e+06 | 2 | 0 | 2e-08 | 0 | 2e-08 | 1.01e-08 | 0.02 | -0.00995 | no | increase interleaving or reduce instant MBU mapping probability |
| `rare_3bit_clusters` | 1e+06 | 3 | 0 | 2e-08 | 0 | 0 | 1.01e-08 | 0 | 0.0101 | yes | scrubbing may optimize only accumulated risk |
| `rare_3bit_clusters` | 1e+06 | 4 | 0 | 2e-08 | 0 | 0 | 1.01e-08 | 0 | 0.0101 | yes | scrubbing may optimize only accumulated risk |
| `strong_3bit_clusters` | 1e+06 | 1 | 0 | 2e-07 | 0 | 2e-07 | 1.01e-08 | 0.2 | -0.19 | no | increase interleaving or reduce instant MBU mapping probability |
| `strong_3bit_clusters` | 1e+06 | 2 | 0 | 2e-07 | 0 | 2e-07 | 1.01e-08 | 0.2 | -0.19 | no | increase interleaving or reduce instant MBU mapping probability |
| `strong_3bit_clusters` | 1e+06 | 3 | 0 | 2e-07 | 0 | 0 | 1.01e-08 | 0 | 0.0101 | yes | scrubbing may optimize only accumulated risk |
| `strong_3bit_clusters` | 1e+06 | 4 | 0 | 2e-07 | 0 | 0 | 1.01e-08 | 0 | 0.0101 | yes | scrubbing may optimize only accumulated risk |
| `mixed_2bit_3bit` | 1e+06 | 1 | 5e-08 | 1e-07 | 0 | 1.5e-07 | 1.01e-08 | 0.15 | -0.14 | no | increase interleaving or reduce instant MBU mapping probability |
| `mixed_2bit_3bit` | 1e+06 | 2 | 5e-08 | 1e-07 | 0 | 1e-07 | 1.01e-08 | 0.1 | -0.0899 | no | increase interleaving or reduce instant MBU mapping probability |
| `mixed_2bit_3bit` | 1e+06 | 3 | 5e-08 | 1e-07 | 0 | 0 | 1.01e-08 | 0 | 0.0101 | yes | scrubbing may optimize only accumulated risk |
| `mixed_2bit_3bit` | 1e+06 | 4 | 5e-08 | 1e-07 | 0 | 0 | 1.01e-08 | 0 | 0.0101 | yes | scrubbing may optimize only accumulated risk |
| `four_bit_clusters` | 1e+06 | 1 | 0 | 0 | 2e-07 | 2e-07 | 1.01e-08 | 0.2 | -0.19 | no | increase interleaving or reduce instant MBU mapping probability |
| `four_bit_clusters` | 1e+06 | 2 | 0 | 0 | 2e-07 | 2e-07 | 1.01e-08 | 0.2 | -0.19 | no | increase interleaving or reduce instant MBU mapping probability |
| `four_bit_clusters` | 1e+06 | 3 | 0 | 0 | 2e-07 | 2e-07 | 1.01e-08 | 0.2 | -0.19 | no | increase interleaving or reduce instant MBU mapping probability |
| `four_bit_clusters` | 1e+06 | 4 | 0 | 0 | 2e-07 | 0 | 1.01e-08 | 0 | 0.0101 | yes | scrubbing may optimize only accumulated risk |
| `high_event_count_low_probability` | 1e+08 | 1 | 0 | 2e-10 | 0 | 2e-10 | 1.01e-10 | 0.02 | -0.00995 | no | increase interleaving or reduce instant MBU mapping probability |
| `high_event_count_low_probability` | 1e+08 | 2 | 0 | 2e-10 | 0 | 2e-10 | 1.01e-10 | 0.02 | -0.00995 | no | increase interleaving or reduce instant MBU mapping probability |
| `high_event_count_low_probability` | 1e+08 | 3 | 0 | 2e-10 | 0 | 0 | 1.01e-10 | 0 | 0.0101 | yes | scrubbing may optimize only accumulated risk |
| `high_event_count_low_probability` | 1e+08 | 4 | 0 | 2e-10 | 0 | 0 | 1.01e-10 | 0 | 0.0101 | yes | scrubbing may optimize only accumulated risk |

## Interpretation

For 3-bit clusters, D=3 is sufficient in this simplified SECDED placement model because the cluster becomes 1+1+1 across three codewords. D=2 is not sufficient for a 3-bit event because the split is 2+1 and one codeword still receives a double-bit error. The `subbudget_3bit_clusters` case shows that nonzero instant MBU risk is acceptable only if it leaves a positive residual budget for the accumulated component.

For 4-bit clusters, D=3 is not sufficient because the split still contains a two-bit group. This is the practical meaning of the applicability criterion: once the instant component exceeds the budget, the scrub period is no longer the controlling design parameter.

The probabilities p2, p3 and p4 in this report are illustrative inputs. In a dissertation calculation they must be replaced by technology-specific or literature-supported h_m^(D) and event-rate estimates.

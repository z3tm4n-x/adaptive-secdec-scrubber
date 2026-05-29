# MBU suppression requirements

- Target mission probability: 0.01
- Target risk measure E*: 0.0100503358535

For a single multiplicity class, the applicability criterion can be written as p_m * h_m^(D) <= g_crit, therefore h_m^(D) <= g_crit / p_m. The required bound is independent of D; D enters through the actual achieved mapping probability h_m^(D). Rows are repeated by D for direct comparison with mapping tables.

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

For mixed p_m distributions this table is diagnostic only. The full pass/fail condition is computed from the sum over all multiplicities.


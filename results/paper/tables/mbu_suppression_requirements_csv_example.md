# MBU suppression requirements

- Target mission probability: 0.01
- Target risk measure E*: 0.0100503358535

For a single multiplicity class, the applicability criterion can be written as p_m * h_m^(D) <= g_crit, therefore h_m^(D) <= g_crit / p_m. The required bound is independent of D; D enters through the actual achieved mapping probability h_m^(D). Rows are repeated by D for direct comparison with mapping tables.

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

For mixed p_m distributions this table is diagnostic only. The full pass/fail condition is computed from the sum over all multiplicities.


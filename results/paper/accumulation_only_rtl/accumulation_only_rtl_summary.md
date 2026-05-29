# RTL accumulation-only interleaving series

## Purpose

This RTL series exercises the accumulation-only regime after sufficient interleaving. For `cluster_bit_count=3` and `D=3`, each physical cluster is split as 1+1+1 across SECDED codewords, so the instant same-event DED component is removed in the logical round-robin model.

The run uses the latched runtime DUE metrics added to the strategy testbench: `new_due_count` counts first DUE appearances, while `repeated_due_detections` counts repeated diagnostic detections of already-latched DUE words.

## Summary by interval

| fixed interval | runs | busy, % | corrected | DED detections | new DUE | repeated DED | final unique DUE |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1089 | 10 | 23.100 ± 0.000 | 59.7 ± 0.9 | 0.0 ± 0.0 | 0.000 ± 0.000 | 0.0 ± 0.0 | 0.000 ± 0.000 |
| 2400 | 10 | 10.300 ± 0.000 | 56.2 ± 3.0 | 4.0 ± 9.7 | 0.400 ± 0.843 | 3.6 ± 8.9 | 0.400 ± 0.843 |

## Interpretation

The series is expected to have zero or very low `new_due_count` because D=3 removes the instant DED part of 3-bit clusters. Any remaining DUE appears only from accumulation or repeated injection into already affected words, and is therefore the component that scrub interval can influence.

This is an RTL feasibility check of the theory's `g_D = 0` branch, not a device-level radiation validation.

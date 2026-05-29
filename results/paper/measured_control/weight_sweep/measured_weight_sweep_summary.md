# Measured-control weight sweep

Measured-control status: demonstration, not a net resource win.

## Purpose

This report keeps measured-control in the proper scope: it is a closed-loop RTL feasibility and telemetry experiment. The sweep changes estimator input weights and evaluates the result with latched DUE metrics, but it does not claim that counter-threshold measured control is a new or generally superior scrub policy.

## Aggregate metrics

| config | strategy | runs | weights C/D | busy, % | new DUE | repeated DED | final unique DUE | DED detections | corrected | switches |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `corrected_only_2c_0d` | `fixed` | 5 | 2/0 | 14.100 ± 0.000 | 16.600 ± 1.140 | 521.0 ± 71.3 | 15.400 ± 1.517 | 537.6 ± 72.0 | 82.8 ± 2.6 | 0.0 |
| `corrected_only_2c_0d` | `measured` | 5 | 2/0 | 13.660 ± 0.513 | 17.200 ± 1.304 | 525.4 ± 123.2 | 15.600 ± 1.517 | 542.6 ± 124.1 | 82.4 ± 4.4 | 3.0 |
| `ded_heavy_1c_2d` | `fixed` | 5 | 1/2 | 14.100 ± 0.000 | 16.600 ± 1.140 | 521.0 ± 71.3 | 15.400 ± 1.517 | 537.6 ± 72.0 | 82.8 ± 2.6 | 0.0 |
| `ded_heavy_1c_2d` | `measured` | 5 | 1/2 | 20.200 ± 0.000 | 16.800 ± 0.837 | 832.4 ± 165.3 | 15.800 ± 1.095 | 849.2 ± 165.8 | 81.8 ± 4.4 | 1.0 |
| `default_2c_1d` | `fixed` | 5 | 2/1 | 14.100 ± 0.000 | 16.600 ± 1.140 | 521.0 ± 71.3 | 15.400 ± 1.517 | 537.6 ± 72.0 | 82.8 ± 2.6 | 0.0 |
| `default_2c_1d` | `measured` | 5 | 2/1 | 20.200 ± 0.000 | 16.800 ± 0.837 | 832.4 ± 165.3 | 15.800 ± 1.095 | 849.2 ± 165.8 | 81.8 ± 4.4 | 1.0 |

## Interpretation

The estimator still observes controller counters, including diagnostic DED detections. Therefore this sweep is not the primary risk result. The primary risk semantics are the latched metrics: `new_due_count` and final `unique_uncorrectable_words`. `new_due_count` is a runtime first-arrival metric, while final `unique_uncorrectable_words` is a post-run memory audit; the two can differ if later injections alter the final state.

A configuration should not be called a net win merely because it reacts more aggressively. The summary must be read together with busy percentage and the measured-minus-fixed deltas.

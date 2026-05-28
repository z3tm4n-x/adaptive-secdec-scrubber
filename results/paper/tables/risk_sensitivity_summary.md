# Risk sensitivity summary

## Purpose

This report checks whether the analytical efficiency scale remains stable under changes of the input intensity series and the allowed scrub-period grid.

- Target mission probability: 0.01
- Target risk measure E*: 0.0100503358535

## Main sensitivity table

| case | group | CV² | η theory | η numeric | rel. error, % | discrete loss ρ | discrete gain ηd | τ range, s | saturated at τmax |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| `real_scale_0.1` | scale | 6.24296 | 7.24296 | 7.24296 | 6.86e-11 | 91.127 | 0.079482 | 3600--3600 | yes |
| `real_scale_1` | scale | 6.24296 | 7.24296 | 7.24296 | 9.14e-12 | 1.14321 | 6.33566 | 30--3600 | no |
| `real_scale_10` | scale | 6.24296 | 7.24296 | 7.24296 | 9.45e-11 | 1.17599 | 6.15902 | 1--60 | no |
| `real_smoothed_w3` | smoothing | 5.99133 | 6.99133 | 6.99133 | 2.76e-11 | 1.14264 | 6.11856 | 30--3600 | no |
| `real_smoothed_w12` | smoothing | 4.83972 | 5.83972 | 5.83972 | 4.92e-11 | 1.14293 | 5.10941 | 30--3600 | no |
| `real_smoothed_w24` | smoothing | 4.02012 | 5.02012 | 5.02012 | 7.89e-11 | 1.14194 | 4.39614 | 60--3600 | no |
| `real_smoothed_w72` | smoothing | 2.08947 | 3.08947 | 3.08947 | 5.26e-11 | 1.13616 | 2.71923 | 120--3600 | no |
| `real_peak_clip_q0.99` | peak_clip | 0.322803 | 1.3228 | 1.3228 | 1.8e-11 | 1.11222 | 1.18933 | 1200--3600 | no |
| `real_peak_clip_q0.95` | peak_clip | 0.283537 | 1.28354 | 1.28354 | 5.65e-11 | 1.107 | 1.15947 | 1800--3600 | no |
| `real_peak_clip_q0.9` | peak_clip | 0.255469 | 1.25547 | 1.25547 | 7.77e-11 | 1.10424 | 1.13696 | 1800--3600 | no |
| `real_default_grid` | period_grid | 6.24296 | 7.24296 | 7.24296 | 9.14e-12 | 1.14321 | 6.33566 | 30--3600 | no |
| `real_dense_grid` | period_grid | 6.24296 | 7.24296 | 7.24296 | 9.14e-12 | 1.12654 | 6.42939 | 20--3600 | no |
| `real_coarse_grid` | period_grid | 6.24296 | 7.24296 | 7.24296 | 9.14e-12 | 1.16941 | 6.19371 | 10--3600 | no |
| `synthetic_flat` | synthetic | 0 | 1 | 1 | 3.6e-12 | 1.82254 | 0.548685 | 1800--1800 | no |
| `synthetic_sine_a0.25` | synthetic | 0.03125 | 1.03125 | 1.03125 | 4.38e-11 | 1.05348 | 0.978899 | 1800--3600 | no |
| `synthetic_sine_a0.75` | synthetic | 0.28125 | 1.28125 | 1.28125 | 4.37e-11 | 1.15387 | 1.11039 | 1800--3600 | no |
| `synthetic_two_level_10pct_x10` | synthetic | 2.0194 | 3.0194 | 3.0194 | 1.39e-10 | 1.36686 | 2.209 | 600--3600 | no |
| `synthetic_two_level_02pct_x50` | synthetic | 12.0038 | 13.0038 | 13.0038 | 4.98e-11 | 1.43952 | 9.03347 | 120--3600 | no |
| `synthetic_bursts_5x48_x30` | synthetic | 3.41099 | 4.41099 | 4.41099 | 8.72e-12 | 1.056 | 4.17709 | 120--3600 | no |

## Interpretation

For every tested series the continuous ideal gain matches `1 + CV²` within numerical precision. Therefore the analytical scale is not tied to a single physical source series; it follows from the optimization problem under the stated assumptions.

Scaling the whole intensity series changes the absolute period values and the number of cycles required to meet the same risk target, but it does not change CV² and therefore does not change the theoretical relative gain. Smoothing and peak clipping reduce CV² and correspondingly reduce the possible gain from adaptation. Synthetic burst-like series increase CV² and therefore increase the theoretical upper bound.

`discrete_loss_vs_ideal` quantifies the price of using a finite interval grid instead of a continuous period. It is a hardware/project constraint, not a contradiction of the analytical η scale. `discrete_gain_vs_fixed` is computed against the continuous fixed-at-target reference; therefore it may be below one when a coarse period grid underuses the available risk budget. Cases marked as saturated at τmax mean that even the largest allowed scrub period remains within the risk target; therefore the discrete optimum is limited by the project period grid rather than by the risk constraint.

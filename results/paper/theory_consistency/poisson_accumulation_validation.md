# Poisson accumulation validation

## Purpose

This report validates the probabilistic accumulated-risk model by direct Monte Carlo simulation of Poisson physical events distributed over SECDED codewords. This is distinct from the controlled RTL workloads: controlled workloads are used for paired strategy comparison, while this Monte Carlo check tests whether empirical DUE counts agree with analytical expectations.

## Method

For every hourly bin, the number of physical events is sampled from `Poisson(nu_i)`. Events are assigned uniformly to scrub slots inside the bin and uniformly to codewords. An accumulated DUE is counted when at least two safe events hit the same codeword within the same scrub slot. If `g_D > 0`, each physical event is also independently marked as instant-dangerous with probability `g_D`; those events contribute to `E_inst` and are removed from the safe accumulated-event stream.

## Results

| policy | g_D | E_inst | E_acc | E_total analytical | empirical mean | 95% CI | rel. error, % | within CI |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `fixed_3600_g0` | 0 | 0 | 3.87794 | 3.87794 | 3.92667 | [3.71783; 4.13551] | 1.26 | yes |
| `fixed_600_g0` | 0 | 0 | 0.682396 | 0.682396 | 0.69 | [0.600708; 0.779292] | 1.11 | yes |
| `adaptive_quantile_g0` | 0 | 0 | 0.463726 | 0.463726 | 0.49 | [0.407488; 0.572512] | 5.67 | yes |
| `adaptive_quantile_gpos` | 1e-06 | 0.309957 | 0.463725 | 0.773682 | 0.716667 | [0.616791; 0.816542] | -7.37 | yes |

## Interpretation

The accumulated-only policies check the quadratic collision model under different scrub intervals and under a simple nonstationary adaptive schedule. The `g_D > 0` case shows that total mission risk contains an instant component in addition to accumulated collisions. Agreement within the Monte Carlo confidence interval is an internal consistency check, not a device-level radiation validation.

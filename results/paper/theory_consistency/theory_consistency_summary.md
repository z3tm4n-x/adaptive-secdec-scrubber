# Theory consistency checks

## Purpose

This report checks that the repository implements the same risk structure as the dissertation theory and the MBU model: quadratic accumulated risk when `g_D = 0`, linear local behavior when `g_D > 0`, and a mission-level instant-risk floor `E_inst = g_D * N_total` that cannot be removed by reducing the scrub interval.

## Constants

- `WORD_BITS`: 39
- `WORD_COUNT`: 1935832
- `TOTAL_BITS`: 75497448
- `risk_core` bit-level alpha: 2.51664139054e-07
- word-level `1/(2W)`: 2.58286876134e-07
- alpha ratio, bit-level / word-level: 0.974358987265

## Exact vs quadratic accumulated-risk approximation

| lambda | q exact, word Poisson | q quad, word | rel. error word, % | q quad, risk_core alpha | rel. error bit-level, % |
|---:|---:|---:|---:|---:|---:|
| 0.0001 | 2.58287e-15 | 2.58287e-15 | -9.02295e-06 | 2.51664e-15 | -2.56411 |
| 0.0003 | 2.32458e-14 | 2.32458e-14 | -9.02295e-06 | 2.26498e-14 | -2.56411 |
| 0.001 | 2.58287e-13 | 2.58287e-13 | -9.02294e-06 | 2.51664e-13 | -2.56411 |
| 0.003 | 2.32458e-12 | 2.32458e-12 | 8.19835e-06 | 2.26498e-12 | -2.56409 |
| 0.01 | 2.58287e-11 | 2.58287e-11 | 3.37759e-06 | 2.51664e-11 | -2.5641 |
| 0.03 | 2.32458e-10 | 2.32458e-10 | 2.01023e-06 | 2.26498e-10 | -2.5641 |
| 0.1 | 2.58287e-09 | 2.58287e-09 | 3.50545e-06 | 2.51664e-09 | -2.5641 |
| 0.3 | 2.32458e-08 | 2.32458e-08 | 1.15373e-05 | 2.26498e-08 | -2.56409 |
| 1 | 2.58287e-07 | 2.58287e-07 | 4.73781e-05 | 2.51664e-07 | -2.56406 |
| 3 | 2.32458e-06 | 2.32458e-06 | 0.000219538 | 2.26498e-06 | -2.56389 |
| 10 | 2.58283e-05 | 2.58287e-05 | 0.00163582 | 2.51664e-05 | -2.56251 |

For lambda <= 0.1, the maximum absolute relative error of the word-level quadratic approximation is 9.02295e-06 %. The `risk_core` alpha is the bit-placement coefficient used in the original scrubbing model; its difference from the word-level coefficient is the expected `WORD_BITS/(WORD_BITS-1)` bit-vs-word placement correction.

## Local asymptotic slope check

| case | g_D | a_D | fitted slope | expected slope | lambda range | max log residual |
|---|---:|---:|---:|---:|---:|---:|
| `accumulation_only_g0` | 0 | 1 | 2 | 2 | 0.001--0.0316 | 5.08e-11 |
| `instant_mbu_g_positive` | 0.0005 | 1 | 1 | 1 | 0.001--0.0316 | 1.99e-06 |

The `g_D = 0` case has the expected quadratic local behavior. When `g_D > 0`, the local cycle probability is dominated by the linear instant-MBU term.

## Mission-level instant-risk floor

| case | tau, s | E_inst | E_acc | E_total | E_acc / E_total |
|---|---:|---:|---:|---:|---:|
| `accumulation_only_g0` | 3600 | 0 | 4.10118 | 4.10118 | 1 |
| `accumulation_only_g0` | 1800 | 0 | 2.05059 | 2.05059 | 1 |
| `accumulation_only_g0` | 600 | 0 | 0.683531 | 0.683531 | 1 |
| `accumulation_only_g0` | 300 | 0 | 0.341765 | 0.341765 | 1 |
| `accumulation_only_g0` | 60 | 0 | 0.0683531 | 0.0683531 | 1 |
| `accumulation_only_g0` | 10 | 0 | 0.0113922 | 0.0113922 | 1 |
| `accumulation_only_g0` | 1 | 0 | 0.00113922 | 0.00113922 | 1 |
| `accumulation_only_g0` | 0.1 | 0 | 0.000113922 | 0.000113922 | 1 |
| `accumulation_only_g0` | 0.01 | 0 | 1.13922e-05 | 1.13922e-05 | 1 |
| `instant_mbu_g_positive` | 3600 | 0.0309957 | 4.10118 | 4.13218 | 0.992499 |
| `instant_mbu_g_positive` | 1800 | 0.0309957 | 2.05059 | 2.08159 | 0.98511 |
| `instant_mbu_g_positive` | 600 | 0.0309957 | 0.683531 | 0.714526 | 0.956621 |
| `instant_mbu_g_positive` | 300 | 0.0309957 | 0.341765 | 0.372761 | 0.916848 |
| `instant_mbu_g_positive` | 60 | 0.0309957 | 0.0683531 | 0.0993487 | 0.688011 |
| `instant_mbu_g_positive` | 10 | 0.0309957 | 0.0113922 | 0.0423879 | 0.26876 |
| `instant_mbu_g_positive` | 1 | 0.0309957 | 0.00113922 | 0.0321349 | 0.0354511 |
| `instant_mbu_g_positive` | 0.1 | 0.0309957 | 0.000113922 | 0.0311096 | 0.00366195 |
| `instant_mbu_g_positive` | 0.01 | 0.0309957 | 1.13922e-05 | 0.0310071 | 0.000367406 |

For `g_D = 0`, the mission risk decreases with the scrub interval because only the accumulated component remains. For `g_D > 0`, reducing the interval reduces `E_acc`, but `E_total` tends to the nonzero floor `E_inst`. At the smallest tested interval (0.01 s), `E_total = 0.0310071` and `E_inst = 0.0309957`.

## Interpretation

These checks do not replace device-specific radiation validation. Their role is internal consistency: the software model used for policy construction follows the same accumulated/instant risk decomposition as the analytical theory.

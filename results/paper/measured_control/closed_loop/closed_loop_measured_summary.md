# Closed-loop measured-control multi-seed summary

This experiment compares the closed-loop measured strategy against
fixed, table, and threshold strategies on the same generated fault
streams for each seed.

## Configuration

- Address width: 8
- Memory depth: 256 SECDED codewords
- Total cycles per run: 500000
- Seeds: 1..10
- Single events: 400
- Paired events: 100
- Cluster events: 0
- Level intervals: 2400, 2200, 2000, 1800, 1600, 1400, 1200, 1089

## Aggregate metrics

| strategy | busy % mean | busy % sd | unique DUE mean | unique DUE sd | DED detections mean | DED detections sd | interval switches mean |
|---|---:|---:|---:|---:|---:|---:|---:|
| fixed | 14.20 | 0.00 | 49.70 | 5.21 | 9587.50 | 1226.93 | 0.00 |
| measured | 22.82 | 0.12 | 47.40 | 3.34 | 15031.10 | 1682.55 | 1.40 |
| table | 10.70 | 0.00 | 50.90 | 5.97 | 7453.70 | 794.02 | 43.00 |
| threshold | 10.70 | 0.00 | 51.10 | 6.12 | 7447.30 | 776.73 | 6.00 |

## Interpretation

The measured strategy is a closed-loop RTL mode: its control level is
formed inside the controller from corrected and DED counter deltas.
This summary is an integration/statistical smoke result; it is not yet
the final risk-busy comparison used for dissertation conclusions.

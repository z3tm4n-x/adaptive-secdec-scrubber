# Closed-loop measured-control smoke test

This smoke test checks that the MODE_MEASURED path is closed inside RTL:
the controller forms the control level from its own corrected/uncorrectable
counters and does not require an external control-level schedule for mode
selection.

## Configuration

- Strategy: measured, STRATEGY=3
- Address width: ADDR_WIDTH=8
- Memory depth: 256 SECDED codewords
- Total cycles: 500000
- Fault seed: 1
- Single fault events: 400
- Paired fault events: 100
- Cluster events: 0
- Level intervals: 2400, 2200, 2000, 1800, 1600, 1400, 1200, 1089
- Safe interval: 1089

The interval table is intentionally chosen above the measured full-pass
duration of the 256-word scrubber, so the run does not collapse into continuous
scrubbing.

## Result

The run passed:

- STRATEGY RESULT: measured
- Strategy comparison run passed for strategy measured.

The measured-control loop produced internal updates:

- measured_ctrl_update rows: 20
- observed measured/current levels: 0, 6, 7
- observed selected intervals: 2400, 1200, 1089
- interval switches: 2
- rows with effective_wait_interval <= 1: 0

The minimum effective wait was 47 cycles, while the observed full-pass duration
was about 1026--1042 cycles. Therefore this smoke test exercises the
closed-loop measured mode in an achievable, non-continuous-scrubbing regime.

## Metrics

CSV header:
strategy,total_cycles,scrub_cycles,reads,writes,corrected,uncorrectable_detections,unique_uncorrectable_words,interval_switches,safe_entries,safe_cycles,scrub_active_cycles,memory_busy_cycles,scrub_per_mille,busy_per_mille,safe_per_mille

CSV row:
measured,500000,444,113764,416,416,15417,49,2,0,0,455914,114180,911,228,0

## Interpretation

This is a smoke/integration test, not a final statistical comparison. It shows
that the RTL controller can select scrub intervals from measured corrected and
DED counters without an external control schedule. Multi-seed statistical
comparison is performed separately.

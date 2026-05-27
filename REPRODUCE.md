# Reproduce dissertation-finalization results

## Scope

This document describes how to reproduce the main results generated in the `dissertation-finalization` branch.

The repository contains both source scripts and generated result summaries. The most important final summaries are:

| Block | Result file |
|---|---|
| Final summary | `results/paper/final_results_summary.md` |
| Efficiency scale | `results/paper/tables/efficiency_scale_verification.md` |
| Unsaturated control | `results/paper/unsaturated_control/unsaturated_control_summary.md` |
| Measured control | `results/paper/measured_control/measured_control_summary.md` |
| Interleaving | `results/paper/interleaving/interleaving_summary.md` |
| True pair alignment | `results/paper/true_pair_alignment/true_pair_alignment_summary.md` |

## Expected tools

The experiments were run in a Python virtual environment with the project dependencies installed. RTL simulations use Icarus Verilog through the project `Makefile`.

Recommended local checks:

    python3 --version
    iverilog -V | head -1
    vvp -V | head -1
    make --version | Verilog through the project `Makefile`.

Recommended local checks:

    python3 --version
    iverilog -V | head -1
    vvp -V | head -1
 head -1

## Basic validation

Run syntax checks for the Python scripts used by the final experiments:

    python3 -m py_compile \
        model/generate_fault_events.py \
        model/run_strategy_series.py \
        model/run_interleaving_interval_sweep.py \
        model/analyze_interleaving_sweep.py \
        model/build_interleaving_summary.py \
        model/build_measured_control_summary.py \
        model/build_unsaturated_control_summary.py \
        model/risk_core.py \
        model/verify_efficiency_scale.py \
        model/test_efficiency_scale_synthetic.py \
        model/regression_check_risk_outputs.py

Run analytical / numerical checks:

    python3 model/test_efficiency_scale_synthetic.py
    python3 model/regression_check_risk_outputs.py

## Efficiency scale

Rebuild the equal-risk efficiency verification:

    python3 model/verify_efficiency_scale.py
    cat results/paper/tables/efficiency_scale_verification.md

Expected key result:

    eta_max = 1 + CV^2 = 7.24295991773

## Fault event metadata and shift reporting

Generate a small upsets scenario with event metadata:

    make gen_fault_events \
        ADDR_WIDTH=8 \
        FAULT_SCENARIO=upsets \
        FAULT_TOTAL_CYCLES=5000 \
        FAULT_WINDOW_SIZE=5000 \
        FAULT_EVENT_COUNT=20 \
        FAULT_PAIRED_EVENT_COUNT=5 \
        FAULT_PAIR_GAP_MIN=60 \
        FAULT_PAIR_GAP_MAX=300 \
        FAULT_CLUSTER_EVENT_COUNT=3 \
        FAULT_CLUSTER_BIT_COUNT=2 \
        FAULT_SEED=1 \
        FAULT_META_OUTPUT=results/tables/fault_events_meta_reproduce_smoke.csv \
        FAULT_SHIFT_SUMMARY_OUTPUT=results/tables/event_shift_summary_reproduce_smoke.md

Inspect:

    cat results/tables/event_shift_summary_reproduce_smoke.md

## Unsaturated-control series

The final generated summary is:

    cat results/paper/unsaturated_control/unsaturated_control_summary.md

The full unsaturated-control campaign uses the generated scripts and stored results under:

    results/paper/unsaturated_control/

Important generated reports:

    results/paper/unsaturated_control/no_clusters/strategy_series_summary.md
    results/paper/unsaturated_control/no_clusters/paired_delta_analysis.md
    results/paper/unsaturated_control/fixed_grid_no_clusters/fixed_grid_pareto.md
    results/paper/unsaturated_control/fixed_grid_with_clusters/fixed_grid_pareto.md
    results/paper/unsaturated_control/unsaturated_control_summary.md

## Observable signal and measured control

Final measured-control summary:

    cat results/paper/measured_control/measured_control_summary.md

Important steps:

1. Analyze observable RTL trace windows:

    python3 model/analyze_observable_trace.py \
        --trace results/paper/observable_signal/no_clusters_seed1/strategy_execution_trace.csv \
        --meta results/paper/observable_signal/no_clusters_seed1/fault_events_meta.csv \
        --total-cycles 500000 \
        --window-cycles 25000 \
        --csv-output results/paper/observable_signal/no_clusters_seed1/observable_signal_windows.csv \
        --md-output results/paper/observable_signal/no_clusters_seed1/observable_signal_summary.md

2. Rebuild measured level schedules from observable counters:

    python3 model/build_measured_level_schedule.py \
        --windows results/paper/observable_signal/no_clusters_seed1/observable_signal_windows.csv \
        --source-strategy table \
        --total-cycles 500000 \
        --extra-delay-windows 0 \
        --uncorrectable-weight 0.50 \
        --rate-max 200 \
        --max-level 7 \
        --control-output results/paper/measured_control/no_clusters_seed1/control_levels_measured_table_w0p50.csv \
        --detail-output results/paper/measured_control/no_clusters_seed1/measured_level_windows_table_w0p50.csv \
        --md-output results/paper/measured_control/no_clusters_seed1/measured_level_schedule_table_w0p50.md

3. Rebuild the measured-control summary:

    python3 model/build_measured_control_summary.py
    cat results/paper/measured_control/measured_control_summary.md

The measured-control block is an offline replay:

    RTL trace -> measured schedule -> RTL replay

It is not a fully closed RTL feedback loop.

## Interleaving D=1/2/3

Run the interleaving interval sweep:

    python3 model/run_interleaving_interval_sweep.py \
        --seed-start 1 \
        --seed-count 10 \
        --depths 1,2,3 \
        --fixed-intervals 1089,1244,1555,2021,2400 \
        --total-cycles 500000 \
        --window-size 43824 \
        --event-count 400 \
        --paired-event-count 40 \
        --pair-gap-min 600 \
        --pair-gap-max 3000 \
        --cluster-event-count 30 \
        --cluster-bit-count 3 \
        --addr-width 8 \
        --base-dir results/paper/interleaving/interval_sweep

Analyze paired deltas:

    python3 model/analyze_interleaving_sweep.py \
        --input results/paper/interleaving/interval_sweep/interleaving_interval_sweep.csv \
        --csv-output results/paper/interleaving/interval_sweep/interleaving_interval_sweep_deltas.csv \
        --md-output results/paper/interleaving/interval_sweep/interleaving_interval_sweep_deltas.md

Rebuild the interleaving summary:

    python3 model/build_interleaving_summary.py
    cat results/paper/interleaving/interleaving_summary.md

Expected key result:

    D=3 statistically reduces unique_uncorrectable_words relative to D=1 and D=2.
    After D=3 interleaving, residual risk again depends on the scrub interval.

## Final summary

The top-level technical result summary is:

    cat results/paper/final_results_summary.md

## Cleanup checks

Before committing regenerated results, remove transient simulation files:

    rm -f results/logs/*.vcd
    find . -name "*.vcd" -print

Check repository status:

    git status --short

No VCD files should be committed.

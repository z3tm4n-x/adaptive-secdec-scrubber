# Repository results integrity check

## Status

- Status: `PASS`
- Checked at UTC: `2026-05-28T15:42:30+00:00`
- Failures: 0
- Warnings: 6
- Repository root: `/home/z3tm4n/adaptive_scrubbing`

## Required files

| File | Purpose | Status | Size, bytes |
|---|---|---:|---:|
| `README.md` | root README | `ok` | 3313 |
| `REPRODUCE.md` | reproduce instructions | `ok` | 7050 |
| `Makefile` | top-level build/run entrypoint | `ok` | 36428 |
| `model/risk_core.py` | canonical risk model | `ok` | 12607 |
| `model/verify_efficiency_scale.py` | efficiency verification | `ok` | 11867 |
| `model/build_measured_control_summary.py` | measured-control summary builder | `ok` | 21425 |
| `model/build_interleaving_summary.py` | interleaving summary builder | `ok` | 14910 |
| `rtl/adaptive_scrub_controller.v` | main scrub controller | `ok` | 15022 |
| `rtl/interval_selector.v` | interval selector | `ok` | 6001 |
| `rtl/protected_memory_model.v` | protected memory model | `ok` | 3400 |
| `tb/tb_strategy_comparison.v` | strategy comparison testbench | `ok` | 35010 |
| `results/paper/README.md` | paper results navigation | `ok` | 8336 |
| `results/paper/final_results_summary.md` | final results summary | `ok` | 13508 |
| `results/paper/tables/efficiency_scale_verification.md` | efficiency scale report | `ok` | 3165 |
| `results/paper/tables/efficiency_scale_verification.csv` | efficiency scale csv | `ok` | 1001 |
| `results/paper/unsaturated_control/unsaturated_control_summary.md` | unsaturated control summary | `ok` | 5721 |
| `results/paper/unsaturated_control/no_clusters/strategy_series_summary.md` | no-clusters strategy summary | `ok` | 2858 |
| `results/paper/unsaturated_control/no_clusters/paired_delta_analysis.md` | no-clusters paired delta | `ok` | 2797 |
| `results/paper/unsaturated_control/fixed_grid_no_clusters/fixed_grid_pareto.md` | fixed-grid no-clusters | `ok` | 2235 |
| `results/paper/unsaturated_control/fixed_grid_with_clusters/fixed_grid_pareto.md` | fixed-grid with-clusters | `ok` | 2249 |
| `results/paper/measured_control/measured_control_summary.md` | measured-control summary | `ok` | 10157 |
| `results/paper/measured_control/no_clusters_weight_sweep/measured_weight_sweep_summary.md` | measured weight sweep summary | `ok` | 1700 |
| `results/paper/measured_control/no_clusters_weight_sweep/measured_weight_sweep_deltas.md` | measured weight sweep deltas | `ok` | 2414 |
| `results/paper/observable_signal/no_clusters_seed1/observable_signal_summary.md` | observable signal summary | `ok` | 4147 |
| `results/paper/interleaving/interleaving_summary.md` | interleaving summary | `ok` | 8680 |
| `results/paper/interleaving/interval_sweep/interleaving_interval_sweep_summary.md` | interleaving interval sweep summary | `ok` | 3137 |
| `results/paper/interleaving/interval_sweep/interleaving_interval_sweep_deltas.md` | interleaving interval sweep deltas | `ok` | 2747 |
| `results/paper/true_pair_alignment/true_pair_alignment_summary.md` | true pair alignment summary | `ok` | 3609 |

## Generic results file checks

| Metric | Value |
|---|---:|
| `md_files` | 342 |
| `csv_files` | 740 |
| `empty_files` | 0 |
| `bad_csv_files` | 0 |

## Interleaving sweep matrix

| Metric | Value |
|---|---|
| `raw_csv` | `results/paper/interleaving/interval_sweep/interleaving_interval_sweep.csv` |
| `raw_rows` | `450` |
| `depths` | `1,2,3` |
| `intervals` | `1089,1244,1555,2021,2400` |
| `seeds` | `10 (1..10)` |
| `strategies` | `fixed,table,threshold` |
| `matrix_complete` | `yes` |

## Forbidden or transient artifacts

- `results/tables/control_policy_level_map.csv`
- `results/tables/event_shift_summary.md`
- `results/tables/fault_events_meta.csv`
- `results/tables/strategy_comparison.csv`
- `tb/control_levels.csv`
- `tb/fault_events.csv`

## Git status

```
M results/paper/README.md
?? model/check_repository_results_integrity.py
?? results/paper/repository_integrity_check.md
?? results/paper/true_pair_alignment/no_clusters/seed_0001/
?? results/paper/true_pair_alignment/no_clusters/seed_0002/
?? results/paper/true_pair_alignment/no_clusters/seed_0003/
?? results/paper/true_pair_alignment/no_clusters/seed_0004/
?? results/paper/true_pair_alignment/no_clusters/seed_0005/
?? results/paper/true_pair_alignment/no_clusters/seed_0006/
?? results/paper/true_pair_alignment/no_clusters/seed_0007/
?? results/paper/true_pair_alignment/no_clusters/seed_0008/
?? results/paper/true_pair_alignment/no_clusters/seed_0009/
?? results/paper/true_pair_alignment/no_clusters/seed_0010/
?? results/paper/true_pair_alignment/true_pair_alignment_pairs.csv
?? results/paper/true_pair_alignment/true_pair_alignment_summary.md
```

## Failures

No failures.

## Warnings

| Path | Message |
|---|---|
| `tb/fault_events.csv` | generated transient file exists; verify whether it is intentionally tracked |
| `tb/control_levels.csv` | generated transient file exists; verify whether it is intentionally tracked |
| `results/tables/strategy_comparison.csv` | generated transient file exists; verify whether it is intentionally tracked |
| `results/tables/fault_events_meta.csv` | generated transient file exists; verify whether it is intentionally tracked |
| `results/tables/event_shift_summary.md` | generated transient file exists; verify whether it is intentionally tracked |
| `results/tables/control_policy_level_map.csv` | generated transient file exists; verify whether it is intentionally tracked |

## Interpretation

Критических ошибок нет, но есть предупреждения. Их нужно разобрать перед созданием чистовой ветки `dissertation-release`.

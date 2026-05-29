# Dissertation repository check

- Total checks: 96
- Passed: 96
- Failed: 0

## Failed checks

No failed checks.

## Passed checks

| check | details |
|---|---|
| `required:README.md` | present |
| `required:REPRODUCE.md` | present |
| `required:Makefile` | present |
| `required:doc/dissertation_mapping.md` | present |
| `required:doc/prior_art_measured_control.md` | present |
| `required:model/risk_core.py` | present |
| `required:model/verify_efficiency_scale.py` | present |
| `required:model/run_risk_sensitivity.py` | present |
| `required:model/evaluate_mbu_interleaving_criterion.py` | present |
| `required:model/run_interleaving_sweep.py` | present |
| `required:model/run_closed_loop_measured_series.py` | present |
| `required:model/build_interleaving_summary.py` | present |
| `required:rtl/adaptive_scrub_controller.v` | present |
| `required:rtl/interval_selector.v` | present |
| `required:rtl/measured_control_estimator.v` | present |
| `required:rtl/protected_memory_model.v` | present |
| `required:tb/tb_strategy_comparison.v` | present |
| `required:tb/tb_measured_control_estimator.v` | present |
| `required:results/paper/README.md` | present |
| `required:results/paper/final_results_summary.md` | present |
| `required:results/paper/repository_integrity_check.md` | present |
| `required:results/paper/measured_control/measured_control_summary.md` | present |
| `required:results/paper/measured_control/closed_loop_smoke/closed_loop_smoke_summary.md` | present |
| `required:results/paper/measured_control/closed_loop/closed_loop_measured_summary.md` | present |
| `required:results/paper/measured_control/closed_loop/closed_loop_measured_series.csv` | present |
| `required:results/paper/interleaving/interleaving_summary.md` | present |
| `required:results/paper/interleaving/interval_sweep/interleaving_interval_sweep_runs.csv` | present |
| `required:results/paper/interleaving/interval_sweep/interleaving_interval_sweep_summary.csv` | present |
| `required:results/paper/interleaving/interval_sweep/interleaving_interval_sweep_deltas.csv` | present |
| `required:results/paper/tables/efficiency_scale_verification.md` | present |
| `required:results/paper/tables/efficiency_scale_verification.csv` | present |
| `required:results/paper/tables/risk_sensitivity_summary.md` | present |
| `required:results/paper/tables/risk_sensitivity.csv` | present |
| `required:results/paper/tables/mbu_interleaving_criterion_examples.md` | present |
| `required:results/paper/tables/mbu_interleaving_criterion_examples.csv` | present |
| `csv:results/paper/measured_control/closed_loop/closed_loop_measured_series.csv` | rows=40 |
| `csv:results/paper/interleaving/interval_sweep/interleaving_interval_sweep_runs.csv` | rows=150 |
| `csv:results/paper/interleaving/interval_sweep/interleaving_interval_sweep_summary.csv` | rows=15 |
| `csv:results/paper/interleaving/interval_sweep/interleaving_interval_sweep_deltas.csv` | rows=39 |
| `csv:results/paper/tables/risk_sensitivity.csv` | rows=19 |
| `csv:results/paper/tables/mbu_interleaving_criterion_examples.csv` | rows=24 |
| `csv:results/paper/tables/efficiency_scale_verification.csv` | rows=6 |
| `text_contains:doc/dissertation_mapping.md:Do not state that adaptive scrub-rate itself is new` | found |
| `text_contains:doc/dissertation_mapping.md:mbu_interleaving_criterion_examples.md` | found |
| `text_contains:doc/dissertation_mapping.md:risk_sensitivity_summary.md` | found |
| `text_contains:doc/dissertation_mapping.md:closed_loop_measured_summary.md` | found |
| `text_contains:results/paper/measured_control/measured_control_summary.md:closed-loop RTL` | found |
| `text_contains:results/paper/measured_control/measured_control_summary.md:MODE_MEASURED` | found |
| `text_contains:results/paper/measured_control/measured_control_summary.md:offline replay` | found |
| `text_contains:results/paper/measured_control/measured_control_summary.md:unique DUE` | found |
| `text_contains:results/paper/final_results_summary.md:closed-loop` | found |
| `text_contains:results/paper/final_results_summary.md:MODE_MEASURED` | found |
| `text_contains:results/paper/final_results_summary.md:offline replay` | found |
| `text_contains:results/paper/final_results_summary.md:unique DUE` | found |
| `text_contains:results/paper/final_results_summary.md:Current interleaving note` | found |
| `text_contains:results/paper/final_results_summary.md:cluster_injection_skew = 0` | found |
| `text_contains:results/paper/final_results_summary.md:Measured-control status: demonstration` | found |
| `text_contains:results/paper/interleaving/interleaving_summary.md:истинно одновременно` | found |
| `text_contains:results/paper/interleaving/interleaving_summary.md:cluster_injection_skew = 0` | found |
| `text_contains:results/paper/interleaving/interleaving_summary.md:Частичное перемежение D=2` | found |
| `text_contains:results/paper/tables/risk_sensitivity_summary.md:1 + CV` | found |
| `text_contains:results/paper/tables/risk_sensitivity_summary.md:discrete_gain_vs_fixed` | found |
| `text_contains:results/paper/tables/risk_sensitivity_summary.md:below one` | found |
| `text_contains:results/paper/tables/risk_sensitivity_summary.md:saturated at` | found |
| `text_contains:results/paper/tables/mbu_interleaving_criterion_examples.md:E_inst = N_events * g_D` | found |
| `text_contains:results/paper/tables/mbu_interleaving_criterion_examples.md:g_D <= E* / N_events` | found |
| `text_contains:results/paper/tables/mbu_interleaving_criterion_examples.md:subbudget_3bit_clusters` | found |
| `text_contains:results/paper/tables/mbu_interleaving_criterion_examples.md:positive residual budget` | found |
| `text_forbidden:results/paper/interleaving/interleaving_summary.md:Техническое ограничение текущего Verilog-стенда` | absent |
| `text_forbidden:results/paper/interleaving/interleaving_summary.md:физически одномоментный кластер сериализуется` | absent |
| `text_forbidden:results/paper/interleaving/interleaving_summary.md:по соседним тактам` | absent |
| `text_forbidden:results/paper/interleaving/interleaving_summary.md:статистически значимый рост unique` | absent |
| `text_forbidden:results/paper/final_results_summary.md:Техническое ограничение текущего Verilog-стенда` | absent |
| `text_forbidden:results/paper/final_results_summary.md:физически одномоментный кластер сериализуется` | absent |
| `text_forbidden:results/paper/final_results_summary.md:по соседним тактам` | absent |
| `text_forbidden:results/paper/final_results_summary.md:одна fault-инжекция за такт` | absent |
| `text_forbidden:results/paper/final_results_summary.md:D3 slowest-fastest | +6.400` | absent |
| `text_forbidden:results/paper/final_results_summary.md:`D3 slowest-fastest` | +6.400` | absent |
| `text_forbidden:results/paper/final_results_summary.md:+6.400 [4.399; 8.401]` | absent |
| `text_forbidden:results/paper/final_results_summary.md:статистически значимый рост unique` | absent |
| `text_forbidden:results/paper/final_results_summary.md:Это не полностью аппаратно замкнутый контур` | absent |
| `py_compile:model/risk_core.py` | compiled |
| `py_compile:model/verify_efficiency_scale.py` | compiled |
| `py_compile:model/run_risk_sensitivity.py` | compiled |
| `py_compile:model/evaluate_mbu_interleaving_criterion.py` | compiled |
| `py_compile:model/run_interleaving_sweep.py` | compiled |
| `py_compile:model/run_closed_loop_measured_series.py` | compiled |
| `py_compile:model/build_interleaving_summary.py` | compiled |
| `py_compile:model/build_measured_control_summary.py` | compiled |
| `py_compile:model/check_repository_results_integrity.py` | compiled |
| `py_compile:model/regression_check_risk_outputs.py` | compiled |
| `py_compile:model/generate_fault_events.py` | compiled |
| `debug_artifacts:results/paper/**/*.vcd` | none |
| `debug_artifacts:results/paper/**/*.out` | none |
| `old_interleaving_seed_dirs` | none |
| `make_target:dissertation_check` | present |

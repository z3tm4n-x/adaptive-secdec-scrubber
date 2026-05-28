# Dissertation result mapping

This document maps repository artifacts to dissertation chapters and states how each artifact should be used. It is intended to prevent accidental citation of obsolete pilot data and to keep the dissertation argument aligned with the risk-limited framework.

## Dissertation logic

The dissertation is organized around the following chain:

1. Physical multi-bit event -> logical mapping into SECDED codewords.
2. Instant MBU component is separated from accumulated scrub-period-controlled risk.
3. Applicability criterion checks whether scrub period can meet the risk target at all.
4. If applicable, the residual accumulated-risk budget is optimized by tau(t) proportional to 1 / nu_hat(t).
5. RTL implementation shows how the analytical law degrades under practical constraints.
6. Closed-loop measured control is treated as an engineering realization inside a safe envelope, not as the primary mathematical guarantee.

## Chapter 1. Prior art and boundary of the contribution

| Artifact | Use in dissertation | Status | Limitation |
|---|---|---|---|
| `doc/prior_art_measured_control.md` | Boundary against adaptive scrub-rate patents and threshold-counting prior art | cite in Chapter 1 | Do not claim first adaptive scrub rate |
| `results/paper/README.md` | Repository navigation for reproduced results | support only | Not a scientific result by itself |
| `results/paper/final_results_summary.md` | High-level consolidated result summary | cite selectively | Verify each quoted number against source tables |
| `results/paper/tables/risk_regression_report.md` | Tells which older outputs are current or obsolete | internal guardrail | Do not cite obsolete replaced tables |

## Chapter 2. Event model, MBU mapping, and applicability criterion

| Artifact | Use in dissertation | Status | Limitation |
|---|---|---|---|
| `model/evaluate_mbu_interleaving_criterion.py` | Generates numerical examples for the go/no-go criterion | cite as reproducibility artifact | Example probabilities are illustrative |
| `results/paper/tables/mbu_interleaving_criterion_examples.md` | Main table for g_D, E_inst, residual risk, pass/fail | cite in Chapter 2 | Replace illustrative p_m by literature-supported h_m^(D) in final dissertation text |
| `results/paper/tables/mbu_interleaving_criterion_examples.csv` | Machine-readable criterion table | cite for exact values | Same illustrative-input limitation |
| `model/generate_fault_events.py` | Generates simultaneous MBU/interleaving events | cite as validation support | Not a physical radiation transport model |
| `rtl/protected_memory_model.v` | Memory/ECC model receiving simultaneous injection slots | use in Chapter 4 validation | Behavioral model, not vendor SRAM macro |
| `tb/tb_strategy_comparison.v` | Fault-injection RTL testbench, including simultaneous event grouping | use in Chapters 2 and 4 | Simulation environment, not flight qualification |
| `results/paper/interleaving/interleaving_summary.md` | Main empirical support for D=1/2/3 interleaving behavior | cite in Chapter 2 and Chapter 4 | Based on simplified clustered fault model |
| `results/paper/interleaving/smoke/strategy_comparison_D1.csv` | Smoke check: D=1 | support | Smoke only |
| `results/paper/interleaving/smoke/strategy_comparison_D2.csv` | Smoke check: D=2 | support | Smoke only |
| `results/paper/interleaving/smoke/strategy_comparison_D3.csv` | Smoke check: D=3 | support | Smoke only |
| `results/paper/interleaving/interval_sweep/interleaving_interval_sweep_summary.csv` | Main aggregated interleaving sweep | cite | Aggregated over seeds, not exhaustive parameter sweep |
| `results/paper/interleaving/interval_sweep/interleaving_interval_sweep_deltas.csv` | Paired delta significance for D comparisons | cite | CI interpretation only within tested scenario |
| `results/paper/interleaving/interval_sweep/interleaving_interval_sweep_runs.csv` | Full aggregated run table | cite for traceability | Large table; prefer summary/deltas in text |

## Chapter 3. Risk-limited period optimization and efficiency scale

| Artifact | Use in dissertation | Status | Limitation |
|---|---|---|---|
| `model/risk_core.py` | Core analytical risk functions, eta scale, tau selection | cite as implementation of formulas | Assumes quadratic rare-event accumulated model |
| `model/verify_efficiency_scale.py` | Verifies eta = 1 + CV^2 numerically | cite | RTL not involved |
| `results/paper/tables/efficiency_scale_verification.md` | Main eta verification report | cite in Chapter 3 | Valid under stated assumptions only |
| `results/paper/tables/efficiency_scale_verification.csv` | Machine-readable eta verification table | cite for exact numbers | Same assumptions |
| `model/run_risk_sensitivity.py` | Sensitivity of eta scale to series transformations and period grids | cite as robustness support | Not a replacement for physical environment justification |
| `results/paper/tables/risk_sensitivity_summary.md` | Main risk sensitivity report | cite in Chapter 3 | Discrete grid effects must be explained separately |
| `results/paper/tables/risk_sensitivity.csv` | Machine-readable sensitivity table | cite for exact values | Some cases saturate at tau_max |
| `results/paper/unsaturated_control/unsaturated_control_summary.md` | Shows unsaturated/non-continuous scrubbing regime | cite as support for practical parameter choice | Do not confuse with final closed-loop measured mode |

## Chapter 4. RTL realization and risk-resource verification

| Artifact | Use in dissertation | Status | Limitation |
|---|---|---|---|
| `rtl/adaptive_scrub_controller.v` | Main RTL controller | cite in Chapter 4 | Simulation/synthesis model, not flight IP core |
| `rtl/interval_selector.v` | Interval-level selection logic | cite as component | Simple table selector |
| `rtl/measured_control_estimator.v` | RTL measured-control estimator | cite in Chapter 5 mainly | Engineering realization, not novelty alone |
| `rtl/protected_memory_model.v` | SECDED-protected behavioral memory model | cite | Behavioral memory model |
| `rtl/secded_32_39_encoder.v` | SECDED encoder | support | Standard code component |
| `rtl/secded_32_39_decoder.v` | SECDED decoder/corrector | support | Standard code component |
| `tb/tb_adaptive_scrub_controller.v` | Controller unit/integration test | support | Unit-level validation |
| `tb/tb_adaptive_safe_mode.v` | Safe-mode behavior test | support | Does not prove mission risk alone |
| `tb/tb_adaptive_threshold_mode.v` | Threshold-mode test | support and prior-art comparison | Threshold mode is not claimed as novelty |
| `tb/tb_measured_control_estimator.v` | Measured-estimator RTL testbench | cite as verification support | Unit test only |
| `tb/tb_strategy_comparison.v` | Main strategy comparison simulation bench | cite in Chapter 4 | Simulation-based validation |
| `Makefile` | Reproduction entry points | support | Build helper |
| `REPRODUCE.md` | Reproduction instructions | support | Not a scientific claim |
| `results/paper/measured_control/closed_loop_smoke/closed_loop_smoke_summary.md` | Smoke proof that MODE_MEASURED closes in RTL | cite as integration check | Smoke only |
| `results/paper/measured_control/closed_loop/closed_loop_measured_summary.md` | Multi-seed closed-loop measured RTL result | cite in Chapter 4/5 | Current measured policy is conservative, not optimized |
| `results/paper/measured_control/closed_loop/closed_loop_measured_series.csv` | Machine-readable closed-loop results | cite for exact values | Use unique DUE as risk proxy, not repeated DED detections |
| `results/paper/interleaving/interleaving_summary.md` | Also supports RTL validation of simultaneous MBU injection | cite | Simplified MBU generator |

## Chapter 5. Closed-loop measured control and safe-envelope interpretation

| Artifact | Use in dissertation | Status | Limitation |
|---|---|---|---|
| `doc/prior_art_measured_control.md` | Boundary against counter-threshold adaptive scrub patents | cite | Must explicitly state measured control is not first adaptive scrub-rate mechanism |
| `rtl/measured_control_estimator.v` | Hardware estimator from corrected and DED deltas | cite | Current score S = 2C + U is a demonstrator setting |
| `tb/tb_measured_control_estimator.v` | Unit verification of estimator | support | Unit test |
| `results/paper/measured_control/measured_control_summary.md` | Main measured-control report: offline calibration and closed-loop RTL | cite | Separate offline replay from closed-loop RTL |
| `results/paper/measured_control/closed_loop_smoke/closed_loop_smoke_summary.md` | Confirms autonomous level changes in RTL | support/cite | Smoke only |
| `results/paper/measured_control/closed_loop/closed_loop_measured_summary.md` | Multi-seed comparison of fixed/table/threshold/measured | cite with caution | Measured mode reduces unique DUE but increases busy and repeated DED detections |
| `results/paper/measured_control/no_clusters_weight_sweep/measured_weight_sweep_deltas.md` | Offline weight calibration support | cite as calibration, not final controller guarantee | Offline replay only |

## Results to avoid as primary dissertation evidence

| Artifact or class | Reason |
|---|---|
| Old per-seed directories under `results/paper/interleaving/interval_sweep/D*/...` | Removed/replaced by aggregated simultaneous-injection sweep |
| Any result that says D>1 clusters were serialized over adjacent cycles | Obsolete after simultaneous injection-slot implementation |
| Raw VCD files | Debug-only artifacts, should not be cited |
| Temporary `results/logs/*.out` simulation binaries | Reproducible build products, not scientific outputs |
| `uncorrectable_detections` alone as risk metric | It includes repeated detections of already-DUE words; use `unique_uncorrectable_words` as the primary risk proxy |
| Threshold scrub-rate mode as novelty | Covered by prior art; use only as comparison baseline |
| Measured-control offline replay as closed-loop proof | Offline replay is calibration; closed-loop proof is in `MODE_MEASURED` runs |

## Recommended dissertation claims

| Claim | Supporting artifacts |
|---|---|
| Scrub period controls accumulated risk but not instant MBU risk | `mbu_interleaving_criterion_examples.md`, `interleaving_summary.md` |
| Applicability criterion separates feasible and infeasible scrub-period design cases | `mbu_interleaving_criterion_examples.md` |
| For the accumulated model, ideal adaptive gain equals 1 + CV^2 | `efficiency_scale_verification.md`, `risk_sensitivity_summary.md` |
| Discrete period grids and hardware constraints reduce the ideal gain | `risk_sensitivity_summary.md`, `unsaturated_control_summary.md`, RTL strategy comparisons |
| Sufficient interleaving can return the problem to accumulated-risk control | `interleaving_summary.md`, `interleaving_interval_sweep_deltas.csv` |
| Closed-loop measured control is implementable in RTL but currently conservative | `measured_control_summary.md`, `closed_loop_measured_summary.md` |
| RTL work supports specialty 2.3.2 by showing controller-level realization and resource/risk tradeoff | `adaptive_scrub_controller.v`, `tb_strategy_comparison.v`, closed-loop and interleaving summaries |

## Final writing cautions

1. Do not state that adaptive scrub-rate itself is new.
2. Do not state that counter-threshold measured control itself is new.
3. Do not claim radiation-physics novelty; the work is about computing-system architecture and controller design.
4. Do not claim that the RTL model is a qualified flight implementation.
5. Do not claim that D=2 improves all MBU cases; for 3-bit clusters it leaves a 2+1 split.
6. Do not call D=3 slowest-fastest unique-DUE growth statistically significant in the latest interleaving sweep; the CI includes zero.
7. State that MBU probabilities in the criterion examples are illustrative unless replaced by literature-supported technology values.
8. Keep the primary novelty on the risk-limited chain: applicability criterion, eta scale, and hardware-aware project procedure.

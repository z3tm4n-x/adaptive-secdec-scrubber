PYTHON ?= python3
FAULT_SCENARIO ?= baseline
UPSETS_FILE ?= data/upsets.xlsx
FAULT_START_INDEX ?= 0
FAULT_WINDOW_SIZE ?= 1300
FAULT_TOTAL_CYCLES ?= 1300
FAULT_EVENT_COUNT ?= 8
FAULT_SEED ?= 12345
ADDR_WIDTH ?= 4
FAULT_META_OUTPUT ?= results/tables/fault_events_meta.csv
FAULT_SHIFT_SUMMARY_OUTPUT ?= results/tables/event_shift_summary.md
FAULT_PAIRED_EVENT_COUNT ?= 0
FAULT_PAIR_GAP_MIN ?= 10
FAULT_PAIR_GAP_MAX ?= 80
FAULT_CLUSTER_EVENT_COUNT ?= 0
FAULT_CLUSTER_BIT_COUNT ?= 2
FAULT_CLUSTER_INTERLEAVE_DEPTH ?= 1
FIXED_INTERVAL ?= 80
SAFE_INTERVAL ?= 5

LEVEL0_INTERVAL ?= 100
LEVEL1_INTERVAL ?= 80
LEVEL2_INTERVAL ?= 60
LEVEL3_INTERVAL ?= 40
LEVEL4_INTERVAL ?= 25
LEVEL5_INTERVAL ?= 15
LEVEL6_INTERVAL ?= 10
LEVEL7_INTERVAL ?= 5

THRESHOLD_LOW_TO_MEDIUM ?= 3
THRESHOLD_MEDIUM_TO_LOW ?= 1
THRESHOLD_MEDIUM_TO_HIGH ?= 6
THRESHOLD_HIGH_TO_MEDIUM ?= 4

THRESHOLD_LOW_INTERVAL ?= 100
THRESHOLD_MEDIUM_INTERVAL ?= 25
THRESHOLD_HIGH_INTERVAL ?= 8

CONTROL_QUANTIZATION ?= linear_max
CONTROL_SOURCE ?= quantization
CONTROL_DELAY_POINTS ?= 0
CONTROL_POLICY_SCHEDULE ?= results/paper/tables/risk_policy_schedule.csv
CONTROL_POLICY_LEVEL_MAP_OUTPUT ?= results/tables/control_policy_level_map.csv
TRACE_EXECUTION ?= 0
TRACE_OUTPUT ?= results/tables/strategy_execution_trace.csv
DUMP_VCD ?= 0
SERIES_SEED_START ?= 1
SERIES_SEED_COUNT ?= 10
SERIES_TOTAL_CYCLES ?= 10000
SERIES_WINDOW_SIZE ?= 10000
SERIES_EVENT_COUNT ?= 80
SERIES_PAIRED_EVENT_COUNT ?= 20
SERIES_PAIR_GAP_MIN ?= 60
SERIES_PAIR_GAP_MAX ?= 300
SERIES_CLUSTER_EVENT_COUNT ?= 10
SERIES_CLUSTER_BIT_COUNT ?= 2
SERIES_OUTPUT ?= results/tables/strategy_comparison_series.csv
SERIES_SUMMARY_CSV ?= results/tables/strategy_series_summary.csv
SERIES_SUMMARY_MD ?= results/tables/strategy_series_summary.md
SERIES_FIGURE_DIR ?= results/figures/strategy_series
SERIES_CONTROL_DELAY_POINTS ?= 0

PAPER_RESULTS_DIR ?= results/paper

PAPER_SEED_COUNT ?= 30
PAPER_TOTAL_CYCLES ?= 50000
PAPER_WINDOW_SIZE ?= 43824
PAPER_EVENT_COUNT ?= 400
PAPER_PAIRED_EVENT_COUNT ?= 100
PAPER_PAIR_GAP_MIN ?= 60
PAPER_PAIR_GAP_MAX ?= 300
PAPER_CLUSTER_EVENT_COUNT ?= 10
PAPER_CLUSTER_BIT_COUNT ?= 2
PAPER_CODEWORD_COUNT ?= 16
PAPER_CONTROL_QUANTIZATION ?= linear_max

PAPER_CONTROL_SOURCE ?= risk_policy
PAPER_CONTROL_DELAY_POINTS ?= 0
PAPER_CONTROL_POLICY_SCHEDULE ?= $(PAPER_RESULTS_DIR)/tables/risk_policy_schedule.csv
PAPER_CONTROL_POLICY_LEVEL_MAP_OUTPUT ?= $(PAPER_RESULTS_DIR)/tables/risk_policy_level_map.csv
# Нормированная RTL-таблица для risk-policy:
# physical policy intervals 120,60,30,10,5,2,1 s
# отображаются в model-cycle intervals 120,60,30,10,5,2,1.
PAPER_SAFE_INTERVAL ?= 1

PAPER_LEVEL0_INTERVAL ?= 120
PAPER_LEVEL1_INTERVAL ?= 60
PAPER_LEVEL2_INTERVAL ?= 30
PAPER_LEVEL3_INTERVAL ?= 10
PAPER_LEVEL4_INTERVAL ?= 5
PAPER_LEVEL5_INTERVAL ?= 2
PAPER_LEVEL6_INTERVAL ?= 1
PAPER_LEVEL7_INTERVAL ?= 1

# Архитектурно достижимая RTL-таблица.
#
# В исправленной семантике selected_interval задаёт целевой период полного
# прохода. При последовательном проходе 16 слов минимальный достижимый период
# ограничен длительностью прохода (~66-68 model cycles), поэтому интервалы
# ниже этого уровня схлопываются в режим непрерывного скраббинга.
PAPER_ACHIEVABLE_LEVEL0_INTERVAL ?= 240
PAPER_ACHIEVABLE_LEVEL1_INTERVAL ?= 200
PAPER_ACHIEVABLE_LEVEL2_INTERVAL ?= 150
PAPER_ACHIEVABLE_LEVEL3_INTERVAL ?= 120
PAPER_ACHIEVABLE_LEVEL4_INTERVAL ?= 100
PAPER_ACHIEVABLE_LEVEL5_INTERVAL ?= 80
PAPER_ACHIEVABLE_LEVEL6_INTERVAL ?= 70
PAPER_ACHIEVABLE_LEVEL7_INTERVAL ?= 70

PAPER_ACHIEVABLE_THRESHOLD_LOW_INTERVAL ?= 200
PAPER_ACHIEVABLE_THRESHOLD_MEDIUM_INTERVAL ?= 120
PAPER_ACHIEVABLE_THRESHOLD_HIGH_INTERVAL ?= 70

PAPER_ACHIEVABLE_ETA_RESULTS_DIR ?= $(PAPER_RESULTS_DIR)/eta_achievable
PAPER_ACHIEVABLE_AUDIT_RESULTS_DIR ?= $(PAPER_RESULTS_DIR)/eta_achievable
PAPER_ACHIEVABLE_FIXED_INTERVALS ?= 60,70,80,100,120,150,200,240,300

# Coarse threshold approximation for the same risk-policy levels:
# low:    levels 0..1, conservative interval 60;
# medium: levels 2..3, conservative interval 10;
# high:   levels 4..6, conservative interval 1.
PAPER_THRESHOLD_LOW_TO_MEDIUM ?= 2
PAPER_THRESHOLD_MEDIUM_TO_LOW ?= 1
PAPER_THRESHOLD_MEDIUM_TO_HIGH ?= 4
PAPER_THRESHOLD_HIGH_TO_MEDIUM ?= 3

PAPER_THRESHOLD_LOW_INTERVAL ?= 60
PAPER_THRESHOLD_MEDIUM_INTERVAL ?= 10
PAPER_THRESHOLD_HIGH_INTERVAL ?= 1

RISK_TARGET_PMISSION ?= 0.01
RISK_INTERVALS_SECONDS ?= 1,2,5,10,30,60,120,300,600,1200,1800,3600

ETA_RESULTS_DIR ?= $(PAPER_RESULTS_DIR)/eta
POLICY_AUDIT_RESULTS_DIR ?= $(ETA_RESULTS_DIR)
ETA_FIXED_INTERVALS ?= 5,10,15,20,25,30,40,60,80,100,150,200

ETA_SEED_START ?= 1
ETA_SEED_COUNT ?= $(PAPER_SEED_COUNT)
ETA_TOTAL_CYCLES ?= $(PAPER_TOTAL_CYCLES)
ETA_WINDOW_SIZE ?= $(PAPER_WINDOW_SIZE)
ETA_EVENT_COUNT ?= $(PAPER_EVENT_COUNT)
ETA_PAIRED_EVENT_COUNT ?= $(PAPER_PAIRED_EVENT_COUNT)
ETA_PAIR_GAP_MIN ?= $(PAPER_PAIR_GAP_MIN)
ETA_PAIR_GAP_MAX ?= $(PAPER_PAIR_GAP_MAX)
ETA_CLUSTER_EVENT_COUNT ?= 0
ETA_CLUSTER_BIT_COUNT ?= $(PAPER_CLUSTER_BIT_COUNT)
ETA_CONTROL_QUANTIZATION ?= $(PAPER_CONTROL_QUANTIZATION)
ETA_CONTROL_SOURCE ?= $(PAPER_CONTROL_SOURCE)
ETA_CONTROL_POLICY_SCHEDULE ?= $(PAPER_CONTROL_POLICY_SCHEDULE)

NO_CLUSTER_SERIES_OUTPUT ?= results/tables/strategy_comparison_series_no_clusters.csv
NO_CLUSTER_SUMMARY_CSV ?= results/tables/strategy_series_summary_no_clusters.csv
NO_CLUSTER_SUMMARY_MD ?= results/tables/strategy_series_summary_no_clusters.md
NO_CLUSTER_FIGURE_DIR ?= results/figures/series_no_clusters

WITH_CLUSTER_SERIES_OUTPUT ?= results/tables/strategy_comparison_series_with_clusters.csv
WITH_CLUSTER_SUMMARY_CSV ?= results/tables/strategy_series_summary_with_clusters.csv
WITH_CLUSTER_SUMMARY_MD ?= results/tables/strategy_series_summary_with_clusters.md
WITH_CLUSTER_FIGURE_DIR ?= results/figures/series_with_clusters

SCENARIO_COMPARISON_CSV ?= results/tables/strategy_scenario_comparison.csv
SCENARIO_COMPARISON_MD ?= results/tables/strategy_scenario_comparison.md

.PHONY: test_measured_control_estimator test_counter test_memory_model test_strategy_comparison analyze_strategy_paired_deltas_paper strategy_modeling_report_paper_achievable analyze_eta_pareto_achievable audit_policy_execution_paper_achievable eta_verification_paper_achievable audit_fault_policy_alignment_paper audit_policy_execution_paper gen_risk_policy_control_paper build_scrub_risk_policy_paper inspect_full_upsets_series eta_verification_paper plot_control_quantization_paper prepare_paper_dirs analyze_upsets_window_paper strategy_modeling_report_paper plot_strategy_series strategy_series_report_no_clusters strategy_series_report_with_clusters compare_series_scenarios strategy_modeling_report analyze_strategy_series strategy_series_report strategy_series synthesis_report analyze_synthesis_logs synth_adaptive_scrub_controller_aw21 gen_fault_events test_strategy_comparison_upsets_paired test_adaptive_metrics strategy_report test_adaptive_scrub_controller analyze_strategy_results plot_strategy_results test_adaptive_threshold_mode test_adaptive_safe_mode synth_adaptive_scrub_controller synth_fixed_scrub_controller test_interval_selector synth_interval_selector test_fixed_scrub_controller synth_counter check_secded_ref gen_secded_vectors test_secded_encoder synth_secded_encoder test_secded_decoder synth_secded_decoder test_secded_codec prepare_dirs test_all synth_all clean

prepare_dirs:
	mkdir -p results/logs results/tables results/figures

inspect_full_upsets_series: prepare_dirs
	$(PYTHON) model/upsets_series.py \
		--input $(UPSETS_FILE)

prepare_paper_dirs:
	mkdir -p $(PAPER_RESULTS_DIR)/tables $(PAPER_RESULTS_DIR)/figures

test_all: prepare_dirs \
	test_counter \
	check_secded_ref \
	test_secded_encoder \
	test_secded_decoder \
	test_secded_codec \
	test_memory_model \
	test_fixed_scrub_controller \
	test_interval_selector \
	test_measured_control_estimator \
	test_adaptive_scrub_controller \
	test_adaptive_safe_mode \
	test_adaptive_threshold_mode \
	test_adaptive_metrics \
	test_strategy_comparison

synth_all: prepare_dirs \
	synth_counter \
	synth_secded_encoder \
	synth_secded_decoder \
	synth_fixed_scrub_controller \
	synth_interval_selector \
	synth_adaptive_scrub_controller \
	synth_adaptive_scrub_controller_aw21

analyze_synthesis_logs: prepare_dirs
	$(PYTHON) model/analyze_synthesis_logs.py \
		--csv-output results/tables/synthesis_summary.csv \
		--md-output results/tables/synthesis_summary.md
	cat results/tables/synthesis_summary.md

synthesis_report: synth_all analyze_synthesis_logs

test_counter: prepare_dirs
	iverilog -o results/logs/simple_counter.out rtl/simple_counter.v tb/tb_simple_counter.v
	vvp results/logs/simple_counter.out

synth_counter: prepare_dirs
	yosys -s synth/simple_counter.ys > results/logs/simple_counter_synth.log

check_secded_ref:
	$(PYTHON) model/secded_ref.py

gen_secded_vectors:
	$(PYTHON) model/generate_secded_vectors.py

test_secded_encoder: prepare_dirs gen_secded_vectors
	iverilog -g2012 -o results/logs/secded_encoder.out rtl/secded_32_39_encoder.v tb/tb_secded_encoder.v
	vvp results/logs/secded_encoder.out

synth_secded_encoder: prepare_dirs
	yosys -s synth/secded_encoder.ys > results/logs/secded_encoder_synth.log

test_secded_decoder: prepare_dirs gen_secded_vectors
	iverilog -g2012 -o results/logs/secded_decoder.out rtl/secded_32_39_decoder.v tb/tb_secded_decoder.v
	vvp results/logs/secded_decoder.out

synth_secded_decoder: prepare_dirs
	yosys -s synth/secded_decoder.ys > results/logs/secded_decoder_synth.log

test_secded_codec: prepare_dirs gen_secded_vectors
	iverilog -g2012 -o results/logs/secded_codec.out rtl/secded_32_39_encoder.v rtl/secded_32_39_decoder.v tb/tb_secded_codec.v
	vvp results/logs/secded_codec.out

test_memory_model: prepare_dirs
	iverilog -g2012 -o results/logs/protected_memory_model.out rtl/secded_32_39_encoder.v rtl/secded_32_39_decoder.v rtl/protected_memory_model.v tb/tb_protected_memory_model.v
	vvp results/logs/protected_memory_model.out

test_fixed_scrub_controller: prepare_dirs
	iverilog -g2012 -o results/logs/fixed_scrub_controller.out rtl/secded_32_39_encoder.v rtl/secded_32_39_decoder.v rtl/protected_memory_model.v rtl/fixed_scrub_controller.v tb/tb_fixed_scrub_controller.v
	vvp results/logs/fixed_scrub_controller.out

synth_fixed_scrub_controller: prepare_dirs
	yosys -s synth/fixed_scrub_controller.ys > results/logs/fixed_scrub_controller_synth.log


test_measured_control_estimator: prepare_dirs
	iverilog -g2012 -o results/logs/measured_control_estimator.out rtl/measured_control_estimator.v tb/tb_measured_control_estimator.v
	vvp results/logs/measured_control_estimator.out

test_interval_selector: prepare_dirs
	iverilog -g2012 -o results/logs/interval_selector.out rtl/interval_selector.v tb/tb_interval_selector.v
	vvp results/logs/interval_selector.out

synth_interval_selector: prepare_dirs
	yosys -s synth/interval_selector.ys > results/logs/interval_selector_synth.log

test_adaptive_scrub_controller: prepare_dirs
	iverilog -g2012 -o results/logs/adaptive_scrub_controller.out rtl/secded_32_39_encoder.v rtl/secded_32_39_decoder.v rtl/protected_memory_model.v rtl/interval_selector.v rtl/measured_control_estimator.v rtl/adaptive_scrub_controller.v tb/tb_adaptive_scrub_controller.v
	vvp results/logs/adaptive_scrub_controller.out

synth_adaptive_scrub_controller: prepare_dirs
	yosys -s synth/adaptive_scrub_controller.ys > results/logs/adaptive_scrub_controller_synth.log

synth_adaptive_scrub_controller_aw21: prepare_dirs
	yosys -s synth/adaptive_scrub_controller_aw21.ys > results/logs/adaptive_scrub_controller_aw21_synth.log

test_adaptive_safe_mode: prepare_dirs
	iverilog -g2012 -o results/logs/adaptive_safe_mode.out rtl/secded_32_39_decoder.v rtl/protected_memory_model.v rtl/interval_selector.v rtl/measured_control_estimator.v rtl/adaptive_scrub_controller.v tb/tb_adaptive_safe_mode.v
	vvp results/logs/adaptive_safe_mode.out

test_adaptive_threshold_mode: prepare_dirs
	iverilog -g2012 -o results/logs/adaptive_threshold_mode.out rtl/secded_32_39_decoder.v rtl/protected_memory_model.v rtl/interval_selector.v rtl/measured_control_estimator.v rtl/adaptive_scrub_controller.v tb/tb_adaptive_threshold_mode.v
	vvp results/logs/adaptive_threshold_mode.out

test_adaptive_metrics: prepare_dirs
	iverilog -g2012 -o results/logs/adaptive_metrics.out rtl/secded_32_39_decoder.v rtl/protected_memory_model.v rtl/interval_selector.v rtl/measured_control_estimator.v rtl/adaptive_scrub_controller.v tb/tb_adaptive_metrics.v
	vvp results/logs/adaptive_metrics.out

gen_fault_events:
	$(PYTHON) model/generate_fault_events.py \
		--scenario $(FAULT_SCENARIO) \
		--input $(UPSETS_FILE) \
		--output tb/fault_events.csv \
		--control-output tb/control_levels.csv \
		--meta-output $(FAULT_META_OUTPUT) \
		--shift-summary-output $(FAULT_SHIFT_SUMMARY_OUTPUT) \
		--start-index $(FAULT_START_INDEX) \
		--window-size $(FAULT_WINDOW_SIZE) \
		--total-cycles $(FAULT_TOTAL_CYCLES) \
		--addr-width $(ADDR_WIDTH) \
		--event-count $(FAULT_EVENT_COUNT) \
		--paired-event-count $(FAULT_PAIRED_EVENT_COUNT) \
		--pair-gap-min $(FAULT_PAIR_GAP_MIN) \
		--pair-gap-max $(FAULT_PAIR_GAP_MAX) \
		--cluster-event-count $(FAULT_CLUSTER_EVENT_COUNT) \
		--cluster-bit-count $(FAULT_CLUSTER_BIT_COUNT) \
		--cluster-interleave-depth $(FAULT_CLUSTER_INTERLEAVE_DEPTH) \
		--seed $(FAULT_SEED) \
		--control-quantization $(CONTROL_QUANTIZATION) \
		--control-source $(CONTROL_SOURCE) \
		--control-delay-points $(CONTROL_DELAY_POINTS) \
		--control-policy-schedule $(CONTROL_POLICY_SCHEDULE) \
		--control-policy-level-map-output $(CONTROL_POLICY_LEVEL_MAP_OUTPUT)


test_strategy_comparison: prepare_dirs gen_fault_events
	iverilog -g2012 -Ptb_strategy_comparison.ADDR_WIDTH=$(ADDR_WIDTH) -o results/logs/strategy_comparison.out rtl/secded_32_39_encoder.v rtl/secded_32_39_decoder.v rtl/protected_memory_model.v rtl/interval_selector.v rtl/measured_control_estimator.v rtl/adaptive_scrub_controller.v tb/tb_strategy_comparison.v
	rm -f results/tables/strategy_comparison.csv
	@if [ "$(TRACE_EXECUTION)" = "1" ]; then \
		mkdir -p $(dir $(TRACE_OUTPUT)); \
		echo "strategy,cycle,scrub_cycle_count,selected_interval,effective_wait_interval,last_pass_duration,current_level,threshold_state,safe_mode_active,control_age,corrected_error_count,uncorrectable_error_count,memory_read_count,memory_write_count,measured_ctrl_level,measured_ctrl_valid,measured_ctrl_update,measured_window_count,measured_corrected_delta,measured_uncorrectable_delta,measured_raw_score" > $(TRACE_OUTPUT); \
	fi
	echo "strategy,total_cycles,scrub_cycles,reads,writes,corrected,uncorrectable_detections,unique_uncorrectable_words,new_due_count,repeated_due_detections,interval_switches,safe_entries,safe_cycles,scrub_active_cycles,memory_busy_cycles,scrub_per_mille,busy_per_mille,safe_per_mille" > results/tables/strategy_comparison.csv
	vvp results/logs/strategy_comparison.out \
		+STRATEGY=0 \
		+TOTAL_RUN_CYCLES=$(FAULT_TOTAL_CYCLES) \
		+FIXED_INTERVAL=$(FIXED_INTERVAL) \
		+SAFE_INTERVAL=$(SAFE_INTERVAL) \
		+LEVEL0_INTERVAL=$(LEVEL0_INTERVAL) \
		+LEVEL1_INTERVAL=$(LEVEL1_INTERVAL) \
		+LEVEL2_INTERVAL=$(LEVEL2_INTERVAL) \
		+LEVEL3_INTERVAL=$(LEVEL3_INTERVAL) \
		+LEVEL4_INTERVAL=$(LEVEL4_INTERVAL) \
		+LEVEL5_INTERVAL=$(LEVEL5_INTERVAL) \
		+LEVEL6_INTERVAL=$(LEVEL6_INTERVAL) \
		+LEVEL7_INTERVAL=$(LEVEL7_INTERVAL) \
		+THRESHOLD_LOW_TO_MEDIUM=$(THRESHOLD_LOW_TO_MEDIUM) \
		+THRESHOLD_MEDIUM_TO_LOW=$(THRESHOLD_MEDIUM_TO_LOW) \
		+THRESHOLD_MEDIUM_TO_HIGH=$(THRESHOLD_MEDIUM_TO_HIGH) \
		+THRESHOLD_HIGH_TO_MEDIUM=$(THRESHOLD_HIGH_TO_MEDIUM) \
		+THRESHOLD_LOW_INTERVAL=$(THRESHOLD_LOW_INTERVAL) \
		+THRESHOLD_MEDIUM_INTERVAL=$(THRESHOLD_MEDIUM_INTERVAL) \
		+THRESHOLD_HIGH_INTERVAL=$(THRESHOLD_HIGH_INTERVAL) \
		+TRACE_EXECUTION=$(TRACE_EXECUTION) \
		+TRACE_OUTPUT=$(TRACE_OUTPUT) \
		+DUMP_VCD=$(DUMP_VCD)
	vvp results/logs/strategy_comparison.out \
		+STRATEGY=1 \
		+TOTAL_RUN_CYCLES=$(FAULT_TOTAL_CYCLES) \
		+FIXED_INTERVAL=$(FIXED_INTERVAL) \
		+SAFE_INTERVAL=$(SAFE_INTERVAL) \
		+LEVEL0_INTERVAL=$(LEVEL0_INTERVAL) \
		+LEVEL1_INTERVAL=$(LEVEL1_INTERVAL) \
		+LEVEL2_INTERVAL=$(LEVEL2_INTERVAL) \
		+LEVEL3_INTERVAL=$(LEVEL3_INTERVAL) \
		+LEVEL4_INTERVAL=$(LEVEL4_INTERVAL) \
		+LEVEL5_INTERVAL=$(LEVEL5_INTERVAL) \
		+LEVEL6_INTERVAL=$(LEVEL6_INTERVAL) \
		+LEVEL7_INTERVAL=$(LEVEL7_INTERVAL) \
		+THRESHOLD_LOW_TO_MEDIUM=$(THRESHOLD_LOW_TO_MEDIUM) \
		+THRESHOLD_MEDIUM_TO_LOW=$(THRESHOLD_MEDIUM_TO_LOW) \
		+THRESHOLD_MEDIUM_TO_HIGH=$(THRESHOLD_MEDIUM_TO_HIGH) \
		+THRESHOLD_HIGH_TO_MEDIUM=$(THRESHOLD_HIGH_TO_MEDIUM) \
		+THRESHOLD_LOW_INTERVAL=$(THRESHOLD_LOW_INTERVAL) \
		+THRESHOLD_MEDIUM_INTERVAL=$(THRESHOLD_MEDIUM_INTERVAL) \
		+THRESHOLD_HIGH_INTERVAL=$(THRESHOLD_HIGH_INTERVAL) \
		+TRACE_EXECUTION=$(TRACE_EXECUTION) \
		+TRACE_OUTPUT=$(TRACE_OUTPUT) \
		+DUMP_VCD=$(DUMP_VCD)
	vvp results/logs/strategy_comparison.out \
		+STRATEGY=2 \
		+TOTAL_RUN_CYCLES=$(FAULT_TOTAL_CYCLES) \
		+FIXED_INTERVAL=$(FIXED_INTERVAL) \
		+SAFE_INTERVAL=$(SAFE_INTERVAL) \
		+LEVEL0_INTERVAL=$(LEVEL0_INTERVAL) \
		+LEVEL1_INTERVAL=$(LEVEL1_INTERVAL) \
		+LEVEL2_INTERVAL=$(LEVEL2_INTERVAL) \
		+LEVEL3_INTERVAL=$(LEVEL3_INTERVAL) \
		+LEVEL4_INTERVAL=$(LEVEL4_INTERVAL) \
		+LEVEL5_INTERVAL=$(LEVEL5_INTERVAL) \
		+LEVEL6_INTERVAL=$(LEVEL6_INTERVAL) \
		+LEVEL7_INTERVAL=$(LEVEL7_INTERVAL) \
		+THRESHOLD_LOW_TO_MEDIUM=$(THRESHOLD_LOW_TO_MEDIUM) \
		+THRESHOLD_MEDIUM_TO_LOW=$(THRESHOLD_MEDIUM_TO_LOW) \
		+THRESHOLD_MEDIUM_TO_HIGH=$(THRESHOLD_MEDIUM_TO_HIGH) \
		+THRESHOLD_HIGH_TO_MEDIUM=$(THRESHOLD_HIGH_TO_MEDIUM) \
		+THRESHOLD_LOW_INTERVAL=$(THRESHOLD_LOW_INTERVAL) \
		+THRESHOLD_MEDIUM_INTERVAL=$(THRESHOLD_MEDIUM_INTERVAL) \
		+THRESHOLD_HIGH_INTERVAL=$(THRESHOLD_HIGH_INTERVAL) \
		+TRACE_EXECUTION=$(TRACE_EXECUTION) \
		+TRACE_OUTPUT=$(TRACE_OUTPUT) \
		+DUMP_VCD=$(DUMP_VCD)
	cat results/tables/strategy_comparison.csv

test_strategy_comparison_upsets_paired:
	$(MAKE) test_strategy_comparison \
		FAULT_SCENARIO=upsets \
		FAULT_EVENT_COUNT=8 \
		FAULT_PAIRED_EVENT_COUNT=2 \
		FAULT_PAIR_GAP_MIN=60 \
		FAULT_PAIR_GAP_MAX=130 \
		FAULT_CLUSTER_EVENT_COUNT=2 \
		FAULT_CLUSTER_BIT_COUNT=2 \
		FAULT_SEED=12345

analyze_strategy_results:
	$(PYTHON) model/analyze_strategy_results.py \
		--input results/tables/strategy_comparison.csv \
		--output results/tables/strategy_summary.md
	cat results/tables/strategy_summary.md

plot_strategy_results:
	$(PYTHON) model/plot_strategy_results.py \
		--input results/tables/strategy_comparison.csv \
		--output-dir results/figures

strategy_report: test_strategy_comparison_upsets_paired analyze_strategy_results plot_strategy_results

strategy_series: prepare_dirs
	$(PYTHON) model/run_strategy_series.py \
		--scenario upsets \
		--seed-start $(SERIES_SEED_START) \
		--seed-count $(SERIES_SEED_COUNT) \
		--total-cycles $(SERIES_TOTAL_CYCLES) \
		--addr-width $(ADDR_WIDTH) \
		--window-size $(SERIES_WINDOW_SIZE) \
		--event-count $(SERIES_EVENT_COUNT) \
		--paired-event-count $(SERIES_PAIRED_EVENT_COUNT) \
		--pair-gap-min $(SERIES_PAIR_GAP_MIN) \
		--pair-gap-max $(SERIES_PAIR_GAP_MAX) \
		--cluster-event-count $(SERIES_CLUSTER_EVENT_COUNT) \
		--cluster-bit-count $(SERIES_CLUSTER_BIT_COUNT) \
		--control-quantization $(CONTROL_QUANTIZATION) \
		--control-source $(CONTROL_SOURCE) \
		--control-delay-points $(SERIES_CONTROL_DELAY_POINTS) \
		--control-policy-schedule $(CONTROL_POLICY_SCHEDULE) \
		--control-policy-level-map-output $(CONTROL_POLICY_LEVEL_MAP_OUTPUT) \
		--safe-interval $(SAFE_INTERVAL) \
		--level-intervals $(LEVEL0_INTERVAL),$(LEVEL1_INTERVAL),$(LEVEL2_INTERVAL),$(LEVEL3_INTERVAL),$(LEVEL4_INTERVAL),$(LEVEL5_INTERVAL),$(LEVEL6_INTERVAL),$(LEVEL7_INTERVAL) \
		--threshold-levels $(THRESHOLD_LOW_TO_MEDIUM),$(THRESHOLD_MEDIUM_TO_LOW),$(THRESHOLD_MEDIUM_TO_HIGH),$(THRESHOLD_HIGH_TO_MEDIUM) \
		--threshold-intervals $(THRESHOLD_LOW_INTERVAL),$(THRESHOLD_MEDIUM_INTERVAL),$(THRESHOLD_HIGH_INTERVAL) \
		--output $(SERIES_OUTPUT)

analyze_strategy_series: prepare_dirs
	$(PYTHON) model/analyze_strategy_series.py \
		--input $(SERIES_OUTPUT) \
		--csv-output $(SERIES_SUMMARY_CSV) \
		--md-output $(SERIES_SUMMARY_MD)
	cat $(SERIES_SUMMARY_MD)

plot_strategy_series: prepare_dirs
	$(PYTHON) model/plot_strategy_series.py \
		--input $(SERIES_SUMMARY_CSV) \
		--output-dir $(SERIES_FIGURE_DIR)

strategy_series_report: strategy_series analyze_strategy_series plot_strategy_series

strategy_series_report_no_clusters:
	$(MAKE) strategy_series_report \
		SERIES_CLUSTER_EVENT_COUNT=0 \
		SERIES_CLUSTER_BIT_COUNT=2 \
		SERIES_OUTPUT=$(NO_CLUSTER_SERIES_OUTPUT) \
		SERIES_SUMMARY_CSV=$(NO_CLUSTER_SUMMARY_CSV) \
		SERIES_SUMMARY_MD=$(NO_CLUSTER_SUMMARY_MD) \
		SERIES_FIGURE_DIR=$(NO_CLUSTER_FIGURE_DIR)

strategy_series_report_with_clusters:
	$(MAKE) strategy_series_report \
		SERIES_CLUSTER_EVENT_COUNT=$(PAPER_CLUSTER_EVENT_COUNT) \
		SERIES_CLUSTER_BIT_COUNT=$(PAPER_CLUSTER_BIT_COUNT) \
		SERIES_OUTPUT=$(WITH_CLUSTER_SERIES_OUTPUT) \
		SERIES_SUMMARY_CSV=$(WITH_CLUSTER_SUMMARY_CSV) \
		SERIES_SUMMARY_MD=$(WITH_CLUSTER_SUMMARY_MD) \
		SERIES_FIGURE_DIR=$(WITH_CLUSTER_FIGURE_DIR)

compare_series_scenarios: prepare_dirs
	$(PYTHON) model/compare_series_scenarios.py \
		--no-clusters-input $(NO_CLUSTER_SUMMARY_CSV) \
		--with-clusters-input $(WITH_CLUSTER_SUMMARY_CSV) \
		--csv-output $(SCENARIO_COMPARISON_CSV) \
		--md-output $(SCENARIO_COMPARISON_MD)
	cat $(SCENARIO_COMPARISON_MD)

analyze_upsets_window_paper: prepare_paper_dirs
	$(PYTHON) model/analyze_upsets_window.py \
		--input $(UPSETS_FILE) \
		--start-index $(FAULT_START_INDEX) \
		--window-size $(PAPER_WINDOW_SIZE) \
		--total-cycles $(PAPER_TOTAL_CYCLES) \
		--event-count $(PAPER_EVENT_COUNT) \
		--paired-event-count $(PAPER_PAIRED_EVENT_COUNT) \
		--cluster-event-count $(PAPER_CLUSTER_EVENT_COUNT) \
		--codeword-count $(PAPER_CODEWORD_COUNT) \
		--control-quantization $(PAPER_CONTROL_QUANTIZATION) \
		--summary-csv $(PAPER_RESULTS_DIR)/tables/upsets_window_summary.csv \
		--level-csv $(PAPER_RESULTS_DIR)/tables/control_level_distribution.csv \
		--md-output $(PAPER_RESULTS_DIR)/tables/upsets_window_summary.md
	cat $(PAPER_RESULTS_DIR)/tables/upsets_window_summary.md

plot_control_quantization_paper: prepare_paper_dirs
	$(PYTHON) model/plot_control_quantization.py \
		--input $(UPSETS_FILE) \
		--start-index $(FAULT_START_INDEX) \
		--window-size $(PAPER_WINDOW_SIZE) \
		--total-cycles $(PAPER_TOTAL_CYCLES) \
		--output-dir $(PAPER_RESULTS_DIR)/figures \
		--control-quantization $(PAPER_CONTROL_QUANTIZATION)
	cat $(PAPER_RESULTS_DIR)/tables/control_quantization_summary.md

build_scrub_risk_policy_paper: prepare_paper_dirs
	$(PYTHON) model/scrub_risk_policy.py \
		--input $(UPSETS_FILE) \
		--start-index $(FAULT_START_INDEX) \
		--window-size $(PAPER_WINDOW_SIZE) \
		--target-pmission $(RISK_TARGET_PMISSION) \
		--intervals-seconds $(RISK_INTERVALS_SECONDS) \
		--output-dir $(PAPER_RESULTS_DIR)/tables
	cat $(PAPER_RESULTS_DIR)/tables/risk_policy_summary.md

gen_risk_policy_control_paper: build_scrub_risk_policy_paper
	$(MAKE) gen_fault_events \
		FAULT_SCENARIO=upsets \
		FAULT_START_INDEX=$(FAULT_START_INDEX) \
		FAULT_WINDOW_SIZE=$(PAPER_WINDOW_SIZE) \
		FAULT_TOTAL_CYCLES=$(PAPER_TOTAL_CYCLES) \
		FAULT_EVENT_COUNT=$(PAPER_EVENT_COUNT) \
		FAULT_PAIRED_EVENT_COUNT=$(PAPER_PAIRED_EVENT_COUNT) \
		FAULT_PAIR_GAP_MIN=$(PAPER_PAIR_GAP_MIN) \
		FAULT_PAIR_GAP_MAX=$(PAPER_PAIR_GAP_MAX) \
		FAULT_CLUSTER_EVENT_COUNT=0 \
		FAULT_CLUSTER_BIT_COUNT=$(PAPER_CLUSTER_BIT_COUNT) \
		FAULT_SEED=1 \
		CONTROL_SOURCE=risk_policy \
		CONTROL_POLICY_SCHEDULE=$(PAPER_CONTROL_POLICY_SCHEDULE) \
		CONTROL_POLICY_LEVEL_MAP_OUTPUT=$(PAPER_CONTROL_POLICY_LEVEL_MAP_OUTPUT)
	cp tb/control_levels.csv $(PAPER_RESULTS_DIR)/tables/risk_policy_control_levels.csv
	cat $(PAPER_CONTROL_POLICY_LEVEL_MAP_OUTPUT)
	head $(PAPER_RESULTS_DIR)/tables/risk_policy_control_levels.csv

strategy_modeling_report: strategy_series_report_no_clusters strategy_series_report_with_clusters compare_series_scenarios

strategy_modeling_report_paper: prepare_paper_dirs analyze_upsets_window_paper plot_control_quantization_paper build_scrub_risk_policy_paper
	$(MAKE) strategy_modeling_report \
		SERIES_SEED_COUNT=$(PAPER_SEED_COUNT) \
		SERIES_TOTAL_CYCLES=$(PAPER_TOTAL_CYCLES) \
		SERIES_WINDOW_SIZE=$(PAPER_WINDOW_SIZE) \
		SERIES_EVENT_COUNT=$(PAPER_EVENT_COUNT) \
		SERIES_PAIRED_EVENT_COUNT=$(PAPER_PAIRED_EVENT_COUNT) \
		SERIES_PAIR_GAP_MIN=$(PAPER_PAIR_GAP_MIN) \
		SERIES_PAIR_GAP_MAX=$(PAPER_PAIR_GAP_MAX) \
		PAPER_CLUSTER_EVENT_COUNT=$(PAPER_CLUSTER_EVENT_COUNT) \
		PAPER_CLUSTER_BIT_COUNT=$(PAPER_CLUSTER_BIT_COUNT) \
		CONTROL_QUANTIZATION=$(PAPER_CONTROL_QUANTIZATION) \
		CONTROL_SOURCE=$(PAPER_CONTROL_SOURCE) \
		SERIES_CONTROL_DELAY_POINTS=$(PAPER_CONTROL_DELAY_POINTS) \
		CONTROL_POLICY_SCHEDULE=$(PAPER_CONTROL_POLICY_SCHEDULE) \
		CONTROL_POLICY_LEVEL_MAP_OUTPUT=$(PAPER_CONTROL_POLICY_LEVEL_MAP_OUTPUT) \
		SAFE_INTERVAL=$(PAPER_SAFE_INTERVAL) \
		LEVEL0_INTERVAL=$(PAPER_LEVEL0_INTERVAL) \
		LEVEL1_INTERVAL=$(PAPER_LEVEL1_INTERVAL) \
		LEVEL2_INTERVAL=$(PAPER_LEVEL2_INTERVAL) \
		LEVEL3_INTERVAL=$(PAPER_LEVEL3_INTERVAL) \
		LEVEL4_INTERVAL=$(PAPER_LEVEL4_INTERVAL) \
		LEVEL5_INTERVAL=$(PAPER_LEVEL5_INTERVAL) \
		LEVEL6_INTERVAL=$(PAPER_LEVEL6_INTERVAL) \
		LEVEL7_INTERVAL=$(PAPER_LEVEL7_INTERVAL) \
		THRESHOLD_LOW_TO_MEDIUM=$(PAPER_THRESHOLD_LOW_TO_MEDIUM) \
		THRESHOLD_MEDIUM_TO_LOW=$(PAPER_THRESHOLD_MEDIUM_TO_LOW) \
		THRESHOLD_MEDIUM_TO_HIGH=$(PAPER_THRESHOLD_MEDIUM_TO_HIGH) \
		THRESHOLD_HIGH_TO_MEDIUM=$(PAPER_THRESHOLD_HIGH_TO_MEDIUM) \
		THRESHOLD_LOW_INTERVAL=$(PAPER_THRESHOLD_LOW_INTERVAL) \
		THRESHOLD_MEDIUM_INTERVAL=$(PAPER_THRESHOLD_MEDIUM_INTERVAL) \
		THRESHOLD_HIGH_INTERVAL=$(PAPER_THRESHOLD_HIGH_INTERVAL) \
		NO_CLUSTER_SERIES_OUTPUT=$(PAPER_RESULTS_DIR)/tables/strategy_comparison_series_no_clusters.csv \
		NO_CLUSTER_SUMMARY_CSV=$(PAPER_RESULTS_DIR)/tables/strategy_series_summary_no_clusters.csv \
		NO_CLUSTER_SUMMARY_MD=$(PAPER_RESULTS_DIR)/tables/strategy_series_summary_no_clusters.md \
		NO_CLUSTER_FIGURE_DIR=$(PAPER_RESULTS_DIR)/figures/series_no_clusters \
		WITH_CLUSTER_SERIES_OUTPUT=$(PAPER_RESULTS_DIR)/tables/strategy_comparison_series_with_clusters.csv \
		WITH_CLUSTER_SUMMARY_CSV=$(PAPER_RESULTS_DIR)/tables/strategy_series_summary_with_clusters.csv \
		WITH_CLUSTER_SUMMARY_MD=$(PAPER_RESULTS_DIR)/tables/strategy_series_summary_with_clusters.md \
		WITH_CLUSTER_FIGURE_DIR=$(PAPER_RESULTS_DIR)/figures/series_with_clusters \
		SCENARIO_COMPARISON_CSV=$(PAPER_RESULTS_DIR)/tables/strategy_scenario_comparison.csv \
		SCENARIO_COMPARISON_MD=$(PAPER_RESULTS_DIR)/tables/strategy_scenario_comparison.md

strategy_modeling_report_paper_achievable:
	$(MAKE) strategy_modeling_report_paper \
		PAPER_LEVEL0_INTERVAL=$(PAPER_ACHIEVABLE_LEVEL0_INTERVAL) \
		PAPER_LEVEL1_INTERVAL=$(PAPER_ACHIEVABLE_LEVEL1_INTERVAL) \
		PAPER_LEVEL2_INTERVAL=$(PAPER_ACHIEVABLE_LEVEL2_INTERVAL) \
		PAPER_LEVEL3_INTERVAL=$(PAPER_ACHIEVABLE_LEVEL3_INTERVAL) \
		PAPER_LEVEL4_INTERVAL=$(PAPER_ACHIEVABLE_LEVEL4_INTERVAL) \
		PAPER_LEVEL5_INTERVAL=$(PAPER_ACHIEVABLE_LEVEL5_INTERVAL) \
		PAPER_LEVEL6_INTERVAL=$(PAPER_ACHIEVABLE_LEVEL6_INTERVAL) \
		PAPER_LEVEL7_INTERVAL=$(PAPER_ACHIEVABLE_LEVEL7_INTERVAL) \
		PAPER_THRESHOLD_LOW_INTERVAL=$(PAPER_ACHIEVABLE_THRESHOLD_LOW_INTERVAL) \
		PAPER_THRESHOLD_MEDIUM_INTERVAL=$(PAPER_ACHIEVABLE_THRESHOLD_MEDIUM_INTERVAL) \
		PAPER_THRESHOLD_HIGH_INTERVAL=$(PAPER_ACHIEVABLE_THRESHOLD_HIGH_INTERVAL)

eta_verification_paper: prepare_paper_dirs build_scrub_risk_policy_paper
	mkdir -p $(ETA_RESULTS_DIR)/tables $(ETA_RESULTS_DIR)/figures
	$(PYTHON) model/run_eta_verification.py \
		--input $(UPSETS_FILE) \
		--start-index $(FAULT_START_INDEX) \
		--window-size $(ETA_WINDOW_SIZE) \
		--total-cycles $(ETA_TOTAL_CYCLES) \
		--seed-start $(ETA_SEED_START) \
		--seed-count $(ETA_SEED_COUNT) \
		--event-count $(ETA_EVENT_COUNT) \
		--paired-event-count $(ETA_PAIRED_EVENT_COUNT) \
		--pair-gap-min $(ETA_PAIR_GAP_MIN) \
		--pair-gap-max $(ETA_PAIR_GAP_MAX) \
		--cluster-event-count $(ETA_CLUSTER_EVENT_COUNT) \
		--cluster-bit-count $(ETA_CLUSTER_BIT_COUNT) \
		--control-quantization $(ETA_CONTROL_QUANTIZATION) \
		--control-source $(ETA_CONTROL_SOURCE) \
		--control-policy-schedule $(ETA_CONTROL_POLICY_SCHEDULE) \
		--control-policy-level-map-output $(PAPER_CONTROL_POLICY_LEVEL_MAP_OUTPUT) \
		--safe-interval $(PAPER_SAFE_INTERVAL) \
		--level-intervals $(PAPER_LEVEL0_INTERVAL),$(PAPER_LEVEL1_INTERVAL),$(PAPER_LEVEL2_INTERVAL),$(PAPER_LEVEL3_INTERVAL),$(PAPER_LEVEL4_INTERVAL),$(PAPER_LEVEL5_INTERVAL),$(PAPER_LEVEL6_INTERVAL),$(PAPER_LEVEL7_INTERVAL) \
		--threshold-levels $(PAPER_THRESHOLD_LOW_TO_MEDIUM),$(PAPER_THRESHOLD_MEDIUM_TO_LOW),$(PAPER_THRESHOLD_MEDIUM_TO_HIGH),$(PAPER_THRESHOLD_HIGH_TO_MEDIUM) \
		--threshold-intervals $(PAPER_THRESHOLD_LOW_INTERVAL),$(PAPER_THRESHOLD_MEDIUM_INTERVAL),$(PAPER_THRESHOLD_HIGH_INTERVAL) \
		--fixed-intervals $(ETA_FIXED_INTERVALS) \
		--output-dir $(ETA_RESULTS_DIR) \
		--make-command $(MAKE)
	cat $(ETA_RESULTS_DIR)/tables/eta_verification.md

eta_verification_paper_achievable:
	$(MAKE) eta_verification_paper \
		ETA_RESULTS_DIR=$(PAPER_ACHIEVABLE_ETA_RESULTS_DIR) \
		ETA_FIXED_INTERVALS=$(PAPER_ACHIEVABLE_FIXED_INTERVALS) \
		PAPER_LEVEL0_INTERVAL=$(PAPER_ACHIEVABLE_LEVEL0_INTERVAL) \
		PAPER_LEVEL1_INTERVAL=$(PAPER_ACHIEVABLE_LEVEL1_INTERVAL) \
		PAPER_LEVEL2_INTERVAL=$(PAPER_ACHIEVABLE_LEVEL2_INTERVAL) \
		PAPER_LEVEL3_INTERVAL=$(PAPER_ACHIEVABLE_LEVEL3_INTERVAL) \
		PAPER_LEVEL4_INTERVAL=$(PAPER_ACHIEVABLE_LEVEL4_INTERVAL) \
		PAPER_LEVEL5_INTERVAL=$(PAPER_ACHIEVABLE_LEVEL5_INTERVAL) \
		PAPER_LEVEL6_INTERVAL=$(PAPER_ACHIEVABLE_LEVEL6_INTERVAL) \
		PAPER_LEVEL7_INTERVAL=$(PAPER_ACHIEVABLE_LEVEL7_INTERVAL) \
		PAPER_THRESHOLD_LOW_INTERVAL=$(PAPER_ACHIEVABLE_THRESHOLD_LOW_INTERVAL) \
		PAPER_THRESHOLD_MEDIUM_INTERVAL=$(PAPER_ACHIEVABLE_THRESHOLD_MEDIUM_INTERVAL) \
		PAPER_THRESHOLD_HIGH_INTERVAL=$(PAPER_ACHIEVABLE_THRESHOLD_HIGH_INTERVAL)

analyze_eta_pareto_achievable:
	$(PYTHON) model/analyze_eta_pareto.py \
		--input $(PAPER_ACHIEVABLE_ETA_RESULTS_DIR)/tables/eta_summary.csv \
		--summary-csv $(PAPER_ACHIEVABLE_ETA_RESULTS_DIR)/tables/eta_pareto_summary.csv \
		--classification-csv $(PAPER_ACHIEVABLE_ETA_RESULTS_DIR)/tables/eta_pareto_classification.csv \
		--md-output $(PAPER_ACHIEVABLE_ETA_RESULTS_DIR)/tables/eta_pareto_summary.md
	cat $(PAPER_ACHIEVABLE_ETA_RESULTS_DIR)/tables/eta_pareto_summary.md

audit_policy_execution_paper: prepare_paper_dirs build_scrub_risk_policy_paper
	mkdir -p $(POLICY_AUDIT_RESULTS_DIR)/tables
	$(MAKE) test_strategy_comparison \
		FAULT_SCENARIO=upsets \
		FAULT_START_INDEX=$(FAULT_START_INDEX) \
		FAULT_WINDOW_SIZE=$(PAPER_WINDOW_SIZE) \
		FAULT_TOTAL_CYCLES=$(PAPER_TOTAL_CYCLES) \
		FAULT_EVENT_COUNT=$(PAPER_EVENT_COUNT) \
		FAULT_PAIRED_EVENT_COUNT=$(PAPER_PAIRED_EVENT_COUNT) \
		FAULT_PAIR_GAP_MIN=$(PAPER_PAIR_GAP_MIN) \
		FAULT_PAIR_GAP_MAX=$(PAPER_PAIR_GAP_MAX) \
		FAULT_CLUSTER_EVENT_COUNT=0 \
		FAULT_CLUSTER_BIT_COUNT=$(PAPER_CLUSTER_BIT_COUNT) \
		FAULT_SEED=1 \
		CONTROL_QUANTIZATION=$(PAPER_CONTROL_QUANTIZATION) \
		CONTROL_SOURCE=$(PAPER_CONTROL_SOURCE) \
		SERIES_CONTROL_DELAY_POINTS=$(PAPER_CONTROL_DELAY_POINTS) \
		CONTROL_POLICY_SCHEDULE=$(PAPER_CONTROL_POLICY_SCHEDULE) \
		CONTROL_POLICY_LEVEL_MAP_OUTPUT=$(PAPER_CONTROL_POLICY_LEVEL_MAP_OUTPUT) \
		FIXED_INTERVAL=$(FIXED_INTERVAL) \
		SAFE_INTERVAL=$(PAPER_SAFE_INTERVAL) \
		LEVEL0_INTERVAL=$(PAPER_LEVEL0_INTERVAL) \
		LEVEL1_INTERVAL=$(PAPER_LEVEL1_INTERVAL) \
		LEVEL2_INTERVAL=$(PAPER_LEVEL2_INTERVAL) \
		LEVEL3_INTERVAL=$(PAPER_LEVEL3_INTERVAL) \
		LEVEL4_INTERVAL=$(PAPER_LEVEL4_INTERVAL) \
		LEVEL5_INTERVAL=$(PAPER_LEVEL5_INTERVAL) \
		LEVEL6_INTERVAL=$(PAPER_LEVEL6_INTERVAL) \
		LEVEL7_INTERVAL=$(PAPER_LEVEL7_INTERVAL) \
		THRESHOLD_LOW_TO_MEDIUM=$(PAPER_THRESHOLD_LOW_TO_MEDIUM) \
		THRESHOLD_MEDIUM_TO_LOW=$(PAPER_THRESHOLD_MEDIUM_TO_LOW) \
		THRESHOLD_MEDIUM_TO_HIGH=$(PAPER_THRESHOLD_MEDIUM_TO_HIGH) \
		THRESHOLD_HIGH_TO_MEDIUM=$(PAPER_THRESHOLD_HIGH_TO_MEDIUM) \
		THRESHOLD_LOW_INTERVAL=$(PAPER_THRESHOLD_LOW_INTERVAL) \
		THRESHOLD_MEDIUM_INTERVAL=$(PAPER_THRESHOLD_MEDIUM_INTERVAL) \
		THRESHOLD_HIGH_INTERVAL=$(PAPER_THRESHOLD_HIGH_INTERVAL) \
		TRACE_EXECUTION=1 \
		TRACE_OUTPUT=$(POLICY_AUDIT_RESULTS_DIR)/tables/policy_execution_trace.csv
	cp results/tables/strategy_comparison.csv $(POLICY_AUDIT_RESULTS_DIR)/tables/policy_execution_strategy_comparison.csv
	cp tb/control_levels.csv $(POLICY_AUDIT_RESULTS_DIR)/tables/policy_execution_control_levels.csv
	$(PYTHON) model/audit_policy_execution.py \
		--trace $(POLICY_AUDIT_RESULTS_DIR)/tables/policy_execution_trace.csv \
		--metrics $(POLICY_AUDIT_RESULTS_DIR)/tables/policy_execution_strategy_comparison.csv \
		--control-levels $(POLICY_AUDIT_RESULTS_DIR)/tables/policy_execution_control_levels.csv \
		--fixed-interval $(FIXED_INTERVAL) \
		--level-intervals $(PAPER_LEVEL0_INTERVAL),$(PAPER_LEVEL1_INTERVAL),$(PAPER_LEVEL2_INTERVAL),$(PAPER_LEVEL3_INTERVAL),$(PAPER_LEVEL4_INTERVAL),$(PAPER_LEVEL5_INTERVAL),$(PAPER_LEVEL6_INTERVAL),$(PAPER_LEVEL7_INTERVAL) \
		--threshold-intervals $(PAPER_THRESHOLD_LOW_INTERVAL),$(PAPER_THRESHOLD_MEDIUM_INTERVAL),$(PAPER_THRESHOLD_HIGH_INTERVAL) \
		--summary-csv $(POLICY_AUDIT_RESULTS_DIR)/tables/policy_execution_audit.csv \
		--md-output $(POLICY_AUDIT_RESULTS_DIR)/tables/policy_execution_audit.md
	cat $(POLICY_AUDIT_RESULTS_DIR)/tables/policy_execution_audit.md

audit_policy_execution_paper_achievable:
	$(MAKE) audit_policy_execution_paper \
		POLICY_AUDIT_RESULTS_DIR=$(PAPER_ACHIEVABLE_AUDIT_RESULTS_DIR) \
		PAPER_LEVEL0_INTERVAL=$(PAPER_ACHIEVABLE_LEVEL0_INTERVAL) \
		PAPER_LEVEL1_INTERVAL=$(PAPER_ACHIEVABLE_LEVEL1_INTERVAL) \
		PAPER_LEVEL2_INTERVAL=$(PAPER_ACHIEVABLE_LEVEL2_INTERVAL) \
		PAPER_LEVEL3_INTERVAL=$(PAPER_ACHIEVABLE_LEVEL3_INTERVAL) \
		PAPER_LEVEL4_INTERVAL=$(PAPER_ACHIEVABLE_LEVEL4_INTERVAL) \
		PAPER_LEVEL5_INTERVAL=$(PAPER_ACHIEVABLE_LEVEL5_INTERVAL) \
		PAPER_LEVEL6_INTERVAL=$(PAPER_ACHIEVABLE_LEVEL6_INTERVAL) \
		PAPER_LEVEL7_INTERVAL=$(PAPER_ACHIEVABLE_LEVEL7_INTERVAL) \
		PAPER_THRESHOLD_LOW_INTERVAL=$(PAPER_ACHIEVABLE_THRESHOLD_LOW_INTERVAL) \
		PAPER_THRESHOLD_MEDIUM_INTERVAL=$(PAPER_ACHIEVABLE_THRESHOLD_MEDIUM_INTERVAL) \
		PAPER_THRESHOLD_HIGH_INTERVAL=$(PAPER_ACHIEVABLE_THRESHOLD_HIGH_INTERVAL)

audit_fault_policy_alignment_paper: prepare_paper_dirs build_scrub_risk_policy_paper
	mkdir -p $(PAPER_RESULTS_DIR)/eta/tables
	$(MAKE) gen_fault_events \
		FAULT_SCENARIO=upsets \
		FAULT_START_INDEX=$(FAULT_START_INDEX) \
		FAULT_WINDOW_SIZE=$(PAPER_WINDOW_SIZE) \
		FAULT_TOTAL_CYCLES=$(PAPER_TOTAL_CYCLES) \
		FAULT_EVENT_COUNT=$(PAPER_EVENT_COUNT) \
		FAULT_PAIRED_EVENT_COUNT=$(PAPER_PAIRED_EVENT_COUNT) \
		FAULT_PAIR_GAP_MIN=$(PAPER_PAIR_GAP_MIN) \
		FAULT_PAIR_GAP_MAX=$(PAPER_PAIR_GAP_MAX) \
		FAULT_CLUSTER_EVENT_COUNT=0 \
		FAULT_CLUSTER_BIT_COUNT=$(PAPER_CLUSTER_BIT_COUNT) \
		FAULT_SEED=1 \
		CONTROL_QUANTIZATION=$(PAPER_CONTROL_QUANTIZATION) \
		CONTROL_SOURCE=$(PAPER_CONTROL_SOURCE) \
		SERIES_CONTROL_DELAY_POINTS=$(PAPER_CONTROL_DELAY_POINTS) \
		CONTROL_POLICY_SCHEDULE=$(PAPER_CONTROL_POLICY_SCHEDULE) \
		CONTROL_POLICY_LEVEL_MAP_OUTPUT=$(PAPER_CONTROL_POLICY_LEVEL_MAP_OUTPUT)
	cp tb/fault_events.csv $(PAPER_RESULTS_DIR)/eta/tables/fault_policy_alignment_fault_events.csv
	cp tb/control_levels.csv $(PAPER_RESULTS_DIR)/eta/tables/fault_policy_alignment_control_levels.csv
	$(PYTHON) model/audit_fault_policy_alignment.py \
		--fault-events $(PAPER_RESULTS_DIR)/eta/tables/fault_policy_alignment_fault_events.csv \
		--control-levels $(PAPER_RESULTS_DIR)/eta/tables/fault_policy_alignment_control_levels.csv \
		--total-cycles $(PAPER_TOTAL_CYCLES) \
		--pair-gap-min $(PAPER_PAIR_GAP_MIN) \
		--pair-gap-max $(PAPER_PAIR_GAP_MAX) \
		--level-intervals $(PAPER_LEVEL0_INTERVAL),$(PAPER_LEVEL1_INTERVAL),$(PAPER_LEVEL2_INTERVAL),$(PAPER_LEVEL3_INTERVAL),$(PAPER_LEVEL4_INTERVAL),$(PAPER_LEVEL5_INTERVAL),$(PAPER_LEVEL6_INTERVAL),$(PAPER_LEVEL7_INTERVAL) \
		--summary-csv $(PAPER_RESULTS_DIR)/eta/tables/fault_policy_alignment.csv \
		--pairs-csv $(PAPER_RESULTS_DIR)/eta/tables/fault_policy_candidate_pairs.csv \
		--md-output $(PAPER_RESULTS_DIR)/eta/tables/fault_policy_alignment.md
	cat $(PAPER_RESULTS_DIR)/eta/tables/fault_policy_alignment.md

analyze_strategy_paired_deltas_paper:
	$(PYTHON) model/analyze_strategy_paired_deltas.py \
		--no-clusters results/paper/tables/strategy_comparison_series_no_clusters.csv \
		--with-clusters results/paper/tables/strategy_comparison_series_with_clusters.csv \
		--csv-output results/paper/tables/strategy_paired_deltas.csv \
		--md-output results/paper/tables/strategy_paired_deltas.md
	cat results/paper/tables/strategy_paired_deltas.md

clean:
	rm -f results/logs/*.out
	rm -f results/logs/*.vcd
	rm -f results/logs/*.log

.PHONY: dissertation_check
dissertation_check:
	python3 model/run_dissertation_checks.py

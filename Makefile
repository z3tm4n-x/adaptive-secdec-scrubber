PYTHON ?= python3
FAULT_SCENARIO ?= baseline
UPSETS_FILE ?= data/upsets.xlsx
FAULT_START_INDEX ?= 0
FAULT_WINDOW_SIZE ?= 1300
FAULT_TOTAL_CYCLES ?= 1300
FAULT_EVENT_COUNT ?= 8
FAULT_SEED ?= 12345
FAULT_PAIRED_EVENT_COUNT ?= 0
FAULT_PAIR_GAP_MIN ?= 10
FAULT_PAIR_GAP_MAX ?= 80
FAULT_CLUSTER_EVENT_COUNT ?= 0
FAULT_CLUSTER_BIT_COUNT ?= 2
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

.PHONY: test_counter test_memory_model test_strategy_comparison plot_strategy_series strategy_series_report_no_clusters strategy_series_report_with_clusters analyze_strategy_series strategy_series_report strategy_series synthesis_report analyze_synthesis_logs synth_adaptive_scrub_controller_aw21 gen_fault_events test_strategy_comparison_upsets_paired test_adaptive_metrics strategy_report test_adaptive_scrub_controller analyze_strategy_results plot_strategy_results test_adaptive_threshold_mode test_adaptive_safe_mode synth_adaptive_scrub_controller synth_fixed_scrub_controller test_interval_selector synth_interval_selector test_fixed_scrub_controller synth_counter check_secded_ref gen_secded_vectors test_secded_encoder synth_secded_encoder test_secded_decoder synth_secded_decoder test_secded_codec prepare_dirs test_all synth_all clean

prepare_dirs:
	mkdir -p results/logs results/tables results/figures

test_all: prepare_dirs \
	test_counter \
	check_secded_ref \
	test_secded_encoder \
	test_secded_decoder \
	test_secded_codec \
	test_memory_model \
	test_fixed_scrub_controller \
	test_interval_selector \
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

test_interval_selector: prepare_dirs
	iverilog -g2012 -o results/logs/interval_selector.out rtl/interval_selector.v tb/tb_interval_selector.v
	vvp results/logs/interval_selector.out

synth_interval_selector: prepare_dirs
	yosys -s synth/interval_selector.ys > results/logs/interval_selector_synth.log

test_adaptive_scrub_controller: prepare_dirs
	iverilog -g2012 -o results/logs/adaptive_scrub_controller.out rtl/secded_32_39_encoder.v rtl/secded_32_39_decoder.v rtl/protected_memory_model.v rtl/interval_selector.v rtl/adaptive_scrub_controller.v tb/tb_adaptive_scrub_controller.v
	vvp results/logs/adaptive_scrub_controller.out

synth_adaptive_scrub_controller: prepare_dirs
	yosys -s synth/adaptive_scrub_controller.ys > results/logs/adaptive_scrub_controller_synth.log

synth_adaptive_scrub_controller_aw21: prepare_dirs
	yosys -s synth/adaptive_scrub_controller_aw21.ys > results/logs/adaptive_scrub_controller_aw21_synth.log

test_adaptive_safe_mode: prepare_dirs
	iverilog -g2012 -o results/logs/adaptive_safe_mode.out rtl/secded_32_39_decoder.v rtl/protected_memory_model.v rtl/interval_selector.v rtl/adaptive_scrub_controller.v tb/tb_adaptive_safe_mode.v
	vvp results/logs/adaptive_safe_mode.out

test_adaptive_threshold_mode: prepare_dirs
	iverilog -g2012 -o results/logs/adaptive_threshold_mode.out rtl/secded_32_39_decoder.v rtl/protected_memory_model.v rtl/interval_selector.v rtl/adaptive_scrub_controller.v tb/tb_adaptive_threshold_mode.v
	vvp results/logs/adaptive_threshold_mode.out

test_adaptive_metrics: prepare_dirs
	iverilog -g2012 -o results/logs/adaptive_metrics.out rtl/secded_32_39_decoder.v rtl/protected_memory_model.v rtl/interval_selector.v rtl/adaptive_scrub_controller.v tb/tb_adaptive_metrics.v
	vvp results/logs/adaptive_metrics.out

gen_fault_events:
	$(PYTHON) model/generate_fault_events.py \
		--scenario $(FAULT_SCENARIO) \
		--input $(UPSETS_FILE) \
		--output tb/fault_events.csv \
		--control-output tb/control_levels.csv \
		--start-index $(FAULT_START_INDEX) \
		--window-size $(FAULT_WINDOW_SIZE) \
		--total-cycles $(FAULT_TOTAL_CYCLES) \
		--event-count $(FAULT_EVENT_COUNT) \
		--paired-event-count $(FAULT_PAIRED_EVENT_COUNT) \
		--pair-gap-min $(FAULT_PAIR_GAP_MIN) \
		--pair-gap-max $(FAULT_PAIR_GAP_MAX) \
		--cluster-event-count $(FAULT_CLUSTER_EVENT_COUNT) \
		--cluster-bit-count $(FAULT_CLUSTER_BIT_COUNT) \
		--seed $(FAULT_SEED)

test_strategy_comparison: prepare_dirs gen_fault_events
	iverilog -g2012 -o results/logs/strategy_comparison.out rtl/secded_32_39_encoder.v rtl/secded_32_39_decoder.v rtl/protected_memory_model.v rtl/interval_selector.v rtl/adaptive_scrub_controller.v tb/tb_strategy_comparison.v
	rm -f results/tables/strategy_comparison.csv
	echo "strategy,total_cycles,scrub_cycles,reads,writes,corrected,uncorrectable_detections,unique_uncorrectable_words,interval_switches,safe_entries,safe_cycles,scrub_active_cycles,memory_busy_cycles,scrub_per_mille,busy_per_mille,safe_per_mille" > results/tables/strategy_comparison.csv
	vvp results/logs/strategy_comparison.out +STRATEGY=0 +TOTAL_RUN_CYCLES=$(FAULT_TOTAL_CYCLES)
	vvp results/logs/strategy_comparison.out +STRATEGY=1 +TOTAL_RUN_CYCLES=$(FAULT_TOTAL_CYCLES)
	vvp results/logs/strategy_comparison.out +STRATEGY=2 +TOTAL_RUN_CYCLES=$(FAULT_TOTAL_CYCLES)
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
		--window-size $(SERIES_WINDOW_SIZE) \
		--event-count $(SERIES_EVENT_COUNT) \
		--paired-event-count $(SERIES_PAIRED_EVENT_COUNT) \
		--pair-gap-min $(SERIES_PAIR_GAP_MIN) \
		--pair-gap-max $(SERIES_PAIR_GAP_MAX) \
		--cluster-event-count $(SERIES_CLUSTER_EVENT_COUNT) \
		--cluster-bit-count $(SERIES_CLUSTER_BIT_COUNT) \
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
		SERIES_OUTPUT=results/tables/strategy_comparison_series_no_clusters.csv \
		SERIES_SUMMARY_CSV=results/tables/strategy_series_summary_no_clusters.csv \
		SERIES_SUMMARY_MD=results/tables/strategy_series_summary_no_clusters.md \
		SERIES_FIGURE_DIR=results/figures/series_no_clusters

strategy_series_report_with_clusters:
	$(MAKE) strategy_series_report \
		SERIES_CLUSTER_EVENT_COUNT=10 \
		SERIES_CLUSTER_BIT_COUNT=2 \
		SERIES_OUTPUT=results/tables/strategy_comparison_series_with_clusters.csv \
		SERIES_SUMMARY_CSV=results/tables/strategy_series_summary_with_clusters.csv \
		SERIES_SUMMARY_MD=results/tables/strategy_series_summary_with_clusters.md \
		SERIES_FIGURE_DIR=results/figures/series_with_clusters

clean:
	rm -f results/logs/*.out
	rm -f results/logs/*.vcd
	rm -f results/logs/*.log
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

.PHONY: test_counter test_memory_model test_strategy_comparison gen_fault_events test_strategy_comparison_upsets_paired test_adaptive_metrics strategy_report test_adaptive_scrub_controller analyze_strategy_results test_adaptive_threshold_mode test_adaptive_safe_mode synth_adaptive_scrub_controller synth_fixed_scrub_controller test_interval_selector synth_interval_selector test_fixed_scrub_controller synth_counter check_secded_ref gen_secded_vectors test_secded_encoder synth_secded_encoder test_secded_decoder synth_secded_decoder test_secded_codec clean

test_counter:
	iverilog -o results/logs/simple_counter.out rtl/simple_counter.v tb/tb_simple_counter.v
	vvp results/logs/simple_counter.out

synth_counter:
	yosys -s synth/simple_counter.ys > results/logs/simple_counter_synth.log

check_secded_ref:
	python model/secded_ref.py

gen_secded_vectors:
	python model/generate_secded_vectors.py

test_secded_encoder: gen_secded_vectors
	iverilog -g2012 -o results/logs/secded_encoder.out rtl/secded_32_39_encoder.v tb/tb_secded_encoder.v
	vvp results/logs/secded_encoder.out

synth_secded_encoder:
	yosys -s synth/secded_encoder.ys > results/logs/secded_encoder_synth.log

test_secded_decoder: gen_secded_vectors
	iverilog -g2012 -o results/logs/secded_decoder.out rtl/secded_32_39_decoder.v tb/tb_secded_decoder.v
	vvp results/logs/secded_decoder.out

synth_secded_decoder:
	yosys -s synth/secded_decoder.ys > results/logs/secded_decoder_synth.log

test_secded_codec: gen_secded_vectors
	iverilog -g2012 -o results/logs/secded_codec.out rtl/secded_32_39_encoder.v rtl/secded_32_39_decoder.v tb/tb_secded_codec.v
	vvp results/logs/secded_codec.out

test_memory_model:
	iverilog -g2012 -o results/logs/protected_memory_model.out rtl/secded_32_39_encoder.v rtl/secded_32_39_decoder.v rtl/protected_memory_model.v tb/tb_protected_memory_model.v
	vvp results/logs/protected_memory_model.out

test_fixed_scrub_controller:
	iverilog -g2012 -o results/logs/fixed_scrub_controller.out rtl/secded_32_39_encoder.v rtl/secded_32_39_decoder.v rtl/protected_memory_model.v rtl/fixed_scrub_controller.v tb/tb_fixed_scrub_controller.v
	vvp results/logs/fixed_scrub_controller.out

synth_fixed_scrub_controller:
	yosys -s synth/fixed_scrub_controller.ys > results/logs/fixed_scrub_controller_synth.log

test_interval_selector:
	iverilog -g2012 -o results/logs/interval_selector.out rtl/interval_selector.v tb/tb_interval_selector.v
	vvp results/logs/interval_selector.out

synth_interval_selector:
	yosys -s synth/interval_selector.ys > results/logs/interval_selector_synth.log

test_adaptive_scrub_controller:
	iverilog -g2012 -o results/logs/adaptive_scrub_controller.out rtl/secded_32_39_encoder.v rtl/secded_32_39_decoder.v rtl/protected_memory_model.v rtl/interval_selector.v rtl/adaptive_scrub_controller.v tb/tb_adaptive_scrub_controller.v
	vvp results/logs/adaptive_scrub_controller.out

synth_adaptive_scrub_controller:
	yosys -s synth/adaptive_scrub_controller.ys > results/logs/adaptive_scrub_controller_synth.log

test_adaptive_safe_mode:
	iverilog -g2012 -o results/logs/adaptive_safe_mode.out rtl/secded_32_39_decoder.v rtl/protected_memory_model.v rtl/interval_selector.v rtl/adaptive_scrub_controller.v tb/tb_adaptive_safe_mode.v
	vvp results/logs/adaptive_safe_mode.out

test_adaptive_threshold_mode:
	iverilog -g2012 -o results/logs/adaptive_threshold_mode.out rtl/secded_32_39_decoder.v rtl/protected_memory_model.v rtl/interval_selector.v rtl/adaptive_scrub_controller.v tb/tb_adaptive_threshold_mode.v
	vvp results/logs/adaptive_threshold_mode.out

test_adaptive_metrics:
	iverilog -g2012 -o results/logs/adaptive_metrics.out rtl/secded_32_39_decoder.v rtl/protected_memory_model.v rtl/interval_selector.v rtl/adaptive_scrub_controller.v tb/tb_adaptive_metrics.v
	vvp results/logs/adaptive_metrics.out

gen_fault_events:
	$(PYTHON) model/generate_fault_events.py \
		--scenario $(FAULT_SCENARIO) \
		--input $(UPSETS_FILE) \
		--output tb/fault_events.csv \
		--start-index $(FAULT_START_INDEX) \
		--window-size $(FAULT_WINDOW_SIZE) \
		--total-cycles $(FAULT_TOTAL_CYCLES) \
		--event-count $(FAULT_EVENT_COUNT) \
		--paired-event-count $(FAULT_PAIRED_EVENT_COUNT) \
		--pair-gap-min $(FAULT_PAIR_GAP_MIN) \
		--pair-gap-max $(FAULT_PAIR_GAP_MAX) \
		--seed $(FAULT_SEED)

test_strategy_comparison: gen_fault_events
	mkdir -p results/logs results/tables
	iverilog -g2012 -o results/logs/strategy_comparison.out rtl/secded_32_39_encoder.v rtl/secded_32_39_decoder.v rtl/protected_memory_model.v rtl/interval_selector.v rtl/adaptive_scrub_controller.v tb/tb_strategy_comparison.v
	rm -f results/tables/strategy_comparison.csv
	echo "strategy,total_cycles,scrub_cycles,reads,writes,corrected,uncorrectable_detections,unique_uncorrectable_words,interval_switches,safe_entries,safe_cycles,scrub_active_cycles,memory_busy_cycles,scrub_per_mille,busy_per_mille,safe_per_mille" > results/tables/strategy_comparison.csv
	vvp results/logs/strategy_comparison.out +STRATEGY=0
	vvp results/logs/strategy_comparison.out +STRATEGY=1
	vvp results/logs/strategy_comparison.out +STRATEGY=2
	cat results/tables/strategy_comparison.csv

test_strategy_comparison_upsets_paired:
	$(MAKE) test_strategy_comparison \
		FAULT_SCENARIO=upsets \
		FAULT_EVENT_COUNT=8 \
		FAULT_PAIRED_EVENT_COUNT=2 \
		FAULT_PAIR_GAP_MIN=60 \
		FAULT_PAIR_GAP_MAX=130 \
		FAULT_SEED=12345

analyze_strategy_results:
	$(PYTHON) model/analyze_strategy_results.py \
		--input results/tables/strategy_comparison.csv \
		--output results/tables/strategy_summary.md
	cat results/tables/strategy_summary.md

strategy_report: test_strategy_comparison_upsets_paired analyze_strategy_results

clean:
	rm -f results/logs/*.out
	rm -f results/logs/*.vcd
	rm -f results/logs/*.log
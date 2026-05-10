.PHONY: test_counter test_memory_model test_adaptive_scrub_controller synth_adaptive_scrub_controller synth_fixed_scrub_controller test_interval_selector synth_interval_selector test_fixed_scrub_controller synth_counter check_secded_ref gen_secded_vectors test_secded_encoder synth_secded_encoder test_secded_decoder synth_secded_decoder test_secded_codec clean

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

clean:
	rm -f results/logs/*.out
	rm -f results/logs/*.vcd
	rm -f results/logs/*.log
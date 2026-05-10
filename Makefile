.PHONY: test_counter synth_counter check_secded_ref gen_secded_vectors test_secded_encoder synth_secded_encoder clean

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

clean:
	rm -f results/logs/*.out
	rm -f results/logs/*.vcd
	rm -f results/logs/*.log
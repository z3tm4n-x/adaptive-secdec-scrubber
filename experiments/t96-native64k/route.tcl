if {$argc!=1} {error "usage: route.tcl fresh_output_directory"}
set here [file dirname [file normalize [info script]]]
set rtl [file normalize $here/../../rtl/native64k]
set out [file normalize [lindex $argv 0]]
if {[file exists $out]} {error "use a fresh output directory: $out"}
file mkdir $out
cd $out
set_param general.maxThreads 4
create_project -in_memory -part xc7z020clg484-1
foreach file {rule core board} {read_verilog -sv $rtl/$file.sv}
read_xdc $here/board.xdc
synth_design -top native64_board -part xc7z020clg484-1 -flatten_hierarchy rebuilt
set_clock_uncertainty -setup 0.5 [get_clocks *]
set_clock_uncertainty -hold 0.1 [get_clocks *]
set ins [get_ports {sram_err sram_dq[*]}]
set outs [get_ports {sram_a[*] sram_dq[*] sram_ce_n sram_oe_n sram_we_n sram_lb_n sram_ub_n}]
# Path budgets for asynchronous SRAM. External retention, setup and turnaround
# are composed from min/max data/clock arcs after routing. No multicycle waiver.
set_max_delay -datapath_only 2.5 -from $ins -to [all_registers]
set_min_delay 0 -from $ins -to [all_registers]
set_max_delay -datapath_only 5 -from [all_registers] -to $outs
set_min_delay 0 -from [all_registers] -to $outs
config_timing_corners -corner Slow -delay_type min_max
config_timing_corners -corner Fast -delay_type min_max
set pad_registers [get_cells -hier -regexp {.*core/pad_(address|select_n|oe_n|we_n)_reg.*}]
if {[llength $pad_registers]<18} {error "missing dedicated control/address output registers"}
set_property CONTROL_SET_REMAP ALL $pad_registers
opt_design
place_design -directive ExtraTimingOpt
phys_opt_design -directive AggressiveExplore
route_design -directive AggressiveExplore
phys_opt_design -directive AggressiveExplore
report_route_status -file route.rpt
report_timing_summary -delay_type min_max -report_unconstrained -check_timing_verbose -file timing.rpt
report_utilization -file utilization.rpt
report_io -file pins.rpt
report_drc -file drc.rpt
check_timing -verbose -file check.rpt
report_timing -max_paths 8 -delay_type max -file worst_setup.rpt
report_timing -max_paths 8 -delay_type min -file worst_hold.rpt
write_checkpoint routed.dcp
write_xdc effective.xdc
# Diagnostic I/O reports only. The acceptance constraints above are saved in DCP.
reset_timing
create_clock -name ref100 -period 10 [get_ports ref100]
set fclk [get_clocks -of_objects [get_pins clock_buffer/O]]
set_clock_uncertainty -setup 0.5 [get_clocks *]
set_clock_uncertainty -hold 0.1 [get_clocks *]
set_load 15 $outs
set_input_delay -clock $fclk -max 0 $ins
set_input_delay -clock $fclk -min 0 $ins
set_output_delay -clock $fclk -max 0 $outs
set_output_delay -clock $fclk -min 0 $outs
foreach corner {Slow Fast} {
    foreach kind {min max} {
        report_timing -from $ins -to [all_registers] -corner $corner -delay_type $kind -max_paths 150 -nworst 4 -file clocked_input_${corner}_${kind}.rpt
        report_timing -from [all_registers] -to $outs -corner $corner -delay_type $kind -max_paths 150 -nworst 4 -file clocked_output_${corner}_${kind}.rpt
    }
}
puts "NATIVE64_ROUTED"
exit

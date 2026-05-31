# RTL synthesis summary

## Purpose

This report provides a synthesis-oriented hardware-cost check for the synthesizable RTL blocks used in the dissertation model. Testbenches, fault-event generators, result builders, and post-run audit scripts are not included in the hardware-cost estimate.

The report contains two Yosys-only flows:

- `generic`: technology-independent synthesis to generic gates.
- `xilinx_xc7_estimate`: Xilinx 7-series mapping estimate using `synth_xilinx`.

The Yosys-only flows estimate logic/register structure. They do not provide a valid maximum clock frequency; Fmax requires target-specific place-and-route and timing constraints.

## Synthesized RTL blocks

| target | top module | role |
|---|---|---|
| `secded_encoder` | `secded_32_39_encoder` | SEC-DED encoder, 32 data bits to 39-bit codeword. |
| `secded_decoder` | `secded_32_39_decoder` | SEC-DED decoder/corrector and error classification logic. |
| `interval_selector` | `interval_selector` | Interval selection block for fixed/table/threshold/safe modes. |
| `measured_control_estimator` | `measured_control_estimator` | Estimator that forms a control level from observed error counters. |
| `adaptive_scrub_controller` | `adaptive_scrub_controller` | Full scrub controller, including SEC-DED decode path, interval selection, and measured-control estimator. |

## Summary

| target | flow | status | cells | FF | LUT | carry | mux | log |
|---|---|---|---:|---:|---:|---:|---:|---|
| `secded_encoder` | `generic` | ok | 88 | 0 | 0 | 0 | 0 | `results/paper/synthesis/logs/secded_encoder_generic.log` |
| `secded_encoder` | `xilinx_xc7_estimate` | ok | 106 | 0 | 33 | 0 | 2 | `results/paper/synthesis/logs/secded_encoder_xilinx_xc7_estimate.log` |
| `secded_decoder` | `generic` | ok | 241 | 0 | 0 | 0 | 0 | `results/paper/synthesis/logs/secded_decoder_generic.log` |
| `secded_decoder` | `xilinx_xc7_estimate` | ok | 256 | 0 | 116 | 2 | 14 | `results/paper/synthesis/logs/secded_decoder_xilinx_xc7_estimate.log` |
| `interval_selector` | `generic` | ok | 1285 | 38 | 0 | 0 | 0 | `results/paper/synthesis/logs/interval_selector_generic.log` |
| `interval_selector` | `xilinx_xc7_estimate` | ok | 1082 | 38 | 306 | 11 | 186 | `results/paper/synthesis/logs/interval_selector_xilinx_xc7_estimate.log` |
| `measured_control_estimator` | `generic` | ok | 836 | 180 | 0 | 0 | 1 | `results/paper/synthesis/logs/measured_control_estimator_generic.log` |
| `measured_control_estimator` | `xilinx_xc7_estimate` | ok | 679 | 197 | 211 | 51 | 19 | `results/paper/synthesis/logs/measured_control_estimator_xilinx_xc7_estimate.log` |
| `adaptive_scrub_controller` | `generic` | ok | 2068 | 491 | 0 | 0 | 7 | `results/paper/synthesis/logs/adaptive_scrub_controller_generic.log` |
| `adaptive_scrub_controller` | `xilinx_xc7_estimate` | ok | 3220 | 730 | 883 | 183 | 214 | `results/paper/synthesis/logs/adaptive_scrub_controller_xilinx_xc7_estimate.log` |

## Interpretation

The synthesizable controller path consists of the scrub controller, SEC-DED decode path, interval selection logic, and measured-control estimator. The latched-DUE audit used in the strategy testbench is a verification metric and is not counted as part of the deployed controller unless a separate diagnostic hardware counter is intentionally added.

For dissertation Section 4.8 these results should be described as RTL synthesis resource estimates. A final implementation-oriented timing statement requires choosing a concrete FPGA or ASIC library, adding timing constraints, and running place-and-route.

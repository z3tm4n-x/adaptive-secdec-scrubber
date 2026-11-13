#!/usr/bin/env bash
set -eu
here=$(cd "$(dirname "$0")" && pwd)
rtl=$here/../../rtl/native64k
out=$(realpath -m "${1:?output directory required}"); mkdir -p "$out"
yosys -Q -p "read_verilog -formal -sv $rtl/rule.sv $rtl/core.sv $here/formal.sv; prep -top pins_bounded -flatten; async2sync; chformal -lower; opt_clean; sat -verify -prove-asserts -set-assumes -seq 142 -timeout 90" > "$out/pins_bounded.txt"
grep 'SUCCESS' "$out/pins_bounded.txt"

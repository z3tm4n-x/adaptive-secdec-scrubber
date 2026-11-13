#!/usr/bin/env bash
set -eu
here=$(cd "$(dirname "$0")" && pwd)
rtl=$here/../../rtl/native64k
out=$(realpath -m "${1:?output directory required}")
mkdir -p "$out"
for top in policy_safety calendar_positions; do
    yosys -Q -p "read_verilog -formal -sv $rtl/rule.sv $rtl/core.sv $here/formal.sv; prep -top $top -flatten; async2sync; chformal -lower; opt_clean; sat -verify -prove-asserts -set-assumes -tempinduct -seq 2 -maxsteps 12 -timeout 60" > "$out/$top.txt"
    grep 'SUCCESS' "$out/$top.txt"
done

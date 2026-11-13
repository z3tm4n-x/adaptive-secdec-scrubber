#!/usr/bin/env bash
set -eu
here=$(cd "$(dirname "$0")" && pwd)
rtl=$here/../../rtl/native64k
out=$(realpath -m "${1:?output directory required}")
mkdir -p "$out"
iverilog -g2012 -s join_tb -o "$out/join" "$rtl/rule.sv" "$rtl/core.sv" "$here/join_tb.sv"
run() { vvp "$out/join" "+level=$1" "+defect=$2" > "$out/join-$1-$2.txt"; }
pids=()
for level in 1 2 3 4 5 6 7 8 9; do
    run "$level" 0 & pids+=($!)
    if [ "${#pids[@]}" -eq 3 ]; then for pid in "${pids[@]}"; do wait "$pid"; done; pids=(); fi
done
for defect in 1 2 3 4 5; do run 1 "$defect" & pids+=($!); done
for pid in "${pids[@]}"; do wait "$pid"; done
cat "$out"/join-*.txt

#!/usr/bin/env bash
set -eu
here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$here/../.." && pwd)
out=$(realpath -m "${1:?output directory}")
mkdir -p "$out"
pin=689807698880fe7ef4f3ca6c9e7fa3426493a6f8
git -C "$root" show "$pin:rtl/native64k/core.sv" > "$out/before.sv"
git -C "$root" show "$pin:rtl/native64k/rule.sv" > "$out/before_rule.sv"
iverilog -g2012 -s epoch_tb -o "$out/before" "$out/before_rule.sv" "$out/before.sv" "$here/epoch_tb.sv"
iverilog -g2012 -s epoch_tb -o "$out/after" "$root/rtl/native64k/rule.sv" "$root/rtl/native64k/core.sv" "$here/epoch_tb.sv"
pids=()
vvp "$out/before" +mode=0 +old=1 > "$out/epoch-before.txt" & pids+=($!)
for mode in 0 1 2 3; do
    vvp "$out/after" "+mode=$mode" > "$out/epoch-$mode.txt" & pids+=($!)
done
rc=0
for pid in "${pids[@]}"; do wait "$pid" || rc=1; done
exit "$rc"

#!/usr/bin/env bash
set -eu
here=$(cd "$(dirname "$0")" && pwd)
rtl=$here/../../rtl/native64k
out=$(realpath -m "${1:?output directory required}")
mkdir -p "$out"
iverilog -g2012 -s full_tb -o "$out/full" "$rtl/rule.sv" "$rtl/core.sv" "$here/full_tb.sv"
iverilog -g2012 -s policy_tb -o "$out/policy" "$rtl/rule.sv" "$here/policy_tb.sv"
vvp "$out/policy" > "$out/policy.txt"
pids=()
for mode in clean last dense hit phase shared_sample missed; do
    case $mode in
        clean) arg="+case=0";; last) arg="+case=1";; dense) arg="+case=2";;
        hit) arg="+fault=1";; phase) arg="+fault=2";;
        shared_sample) arg="+fault=3";; missed) arg="+fault=4";;
    esac
    vvp "$out/full" "$arg" > "$out/$mode.txt" & pids+=($!)
done
rc=0
for pid in "${pids[@]}"; do wait "$pid" || rc=1; done
cat "$out"/{policy,clean,last,dense,hit,phase,shared_sample,missed}.txt
exit "$rc"

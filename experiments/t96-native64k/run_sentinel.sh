#!/usr/bin/env bash
# Keep the released sources intact. Change only OE in a scratch copy, and
# demand that the independent time/port checker notices on the first read.
set -eu
here=$(cd "$(dirname "$0")" && pwd)
rtl=$here/../../rtl/native64k
out=$(realpath -m "${1:?output directory required}")
mkdir -p "$out"
sed '/pad_oe_n<=!(/s/visit_token\[6\]/visit_token[7]/' "$rtl/core.sv" > "$out/wrong_core.sv"
if cmp -s "$out/wrong_core.sv" "$rtl/core.sv"; then echo "missing mutation" >&2; exit 1; fi
iverilog -g2012 -s full_tb -o "$out/sentinel" "$rtl/rule.sv" "$out/wrong_core.sv" "$here/full_tb.sv"
if vvp "$out/sentinel" +case=0 > "$out/rejected.txt"; then echo "mutation escaped"; exit 1; fi
grep 'pin plan mismatch tick=7' "$out/rejected.txt"

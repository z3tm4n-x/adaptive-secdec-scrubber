#!/usr/bin/env bash
set -eu
here=$(cd "$(dirname "$0")" && pwd)
if [ "$#" -ne 1 ]; then echo "usage: bash run_route.sh fresh_output_directory" >&2; exit 2; fi
out=$(realpath -m "$1")
mkdir -p "$out.launch"
cd "$out.launch"
"${VIVADO:-vivado}" -mode batch -source "$here/route.tcl" -tclargs "$out"
test -f "$out/routed.dcp" -a -f "$out/clocked_output_Fast_max.rpt"

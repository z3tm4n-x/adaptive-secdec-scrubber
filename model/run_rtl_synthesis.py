#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class SynthTarget:
    name: str
    top: str
    files: tuple[str, ...]
    description: str


TARGETS = [
    SynthTarget(
        name="secded_encoder",
        top="secded_32_39_encoder",
        files=("rtl/secded_32_39_encoder.v",),
        description="SEC-DED encoder, 32 data bits to 39-bit codeword.",
    ),
    SynthTarget(
        name="secded_decoder",
        top="secded_32_39_decoder",
        files=("rtl/secded_32_39_decoder.v",),
        description="SEC-DED decoder/corrector and error classification logic.",
    ),
    SynthTarget(
        name="interval_selector",
        top="interval_selector",
        files=("rtl/interval_selector.v",),
        description="Interval selection block for fixed/table/threshold/safe modes.",
    ),
    SynthTarget(
        name="measured_control_estimator",
        top="measured_control_estimator",
        files=("rtl/measured_control_estimator.v",),
        description="Estimator that forms a control level from observed error counters.",
    ),
    SynthTarget(
        name="adaptive_scrub_controller",
        top="adaptive_scrub_controller",
        files=(
            "rtl/secded_32_39_decoder.v",
            "rtl/interval_selector.v",
            "rtl/measured_control_estimator.v",
            "rtl/adaptive_scrub_controller.v",
        ),
        description="Full scrub controller, including SEC-DED decode path, interval selection, and measured-control estimator.",
    ),
]


def run_yosys(script: str, script_path: Path, log_path: Path) -> tuple[bool, str]:
    script_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.write_text(script, encoding="utf-8")

    proc = subprocess.run(
        ["yosys", "-s", str(script_path)],
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )

    log_path.write_text(proc.stdout, encoding="utf-8")
    return proc.returncode == 0, proc.stdout


def stat_block_for_top(log: str, top: str) -> str:
    marker = f"=== {top} ==="
    idx = log.rfind(marker)
    if idx < 0:
        return log
    tail = log[idx:]
    next_idx = tail.find("\n===")
    if next_idx > 0:
        return tail[:next_idx]
    return tail


def parse_int_line(block: str, label: str) -> int | None:
    m = re.search(rf"{re.escape(label)}:\s+([0-9]+)", block)
    if not m:
        return None
    return int(m.group(1))


def parse_cell_counts(block: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for line in block.splitlines():
        m = re.match(r"\s+([A-Za-z0-9_.$]+)\s+([0-9]+)\s*$", line)
        if not m:
            continue
        cell, value = m.group(1), int(m.group(2))
        counts[cell] = counts.get(cell, 0) + value
    return counts


def summarize_cells(cell_counts: dict[str, int]) -> dict[str, int]:
    total = sum(cell_counts.values())

    ff_patterns = (
        "DFF", "SDFF", "ADFF", "DFFE", "SDFFE", "ADFFE",
        "FDRE", "FDSE", "FDCE", "FDPE", "SB_DFF",
    )

    ff_total = 0
    lut_total = 0
    carry_total = 0
    mux_total = 0
    memory_total = 0

    for cell, count in cell_counts.items():
        upper = cell.upper()

        if any(p in upper for p in ff_patterns):
            ff_total += count

        if re.fullmatch(r"LUT[1-6]", upper) or upper in {"LUT", "$_LUT_"}:
            lut_total += count

        if "CARRY" in upper:
            carry_total += count

        if "MUX" in upper:
            mux_total += count

        if "RAM" in upper or "MEM" in upper:
            memory_total += count

    return {
        "cells_total": total,
        "ff_cells": ff_total,
        "lut_cells": lut_total,
        "carry_cells": carry_total,
        "mux_cells": mux_total,
        "memory_cells": memory_total,
    }


def generic_script(target: SynthTarget) -> str:
    files = " ".join(target.files)
    return f"""
read_verilog -sv {files}
hierarchy -check -top {target.top}
proc
opt
fsm
opt
memory
opt
techmap
opt
abc
opt
clean
stat
"""


def xilinx_script(target: SynthTarget) -> str:
    files = " ".join(target.files)
    return f"""
read_verilog -sv {files}
synth_xilinx -family xc7 -flatten -noclkbuf -top {target.top}
stat -tech xilinx
"""


def run_target(target: SynthTarget, flow: str, output_dir: Path) -> dict[str, str]:
    if flow == "generic":
        script = generic_script(target)
    elif flow == "xilinx_xc7_estimate":
        script = xilinx_script(target)
    else:
        raise ValueError(flow)

    script_path = output_dir / "scripts" / f"{target.name}_{flow}.ys"
    log_path = output_dir / "logs" / f"{target.name}_{flow}.log"

    ok, log = run_yosys(script, script_path, log_path)

    block = stat_block_for_top(log, target.top)
    cells = parse_cell_counts(block)
    cell_summary = summarize_cells(cells)

    return {
        "target": target.name,
        "top": target.top,
        "flow": flow,
        "status": "ok" if ok else "failed",
        "description": target.description,
        "wires": str(parse_int_line(block, "Number of wires") or ""),
        "wire_bits": str(parse_int_line(block, "Number of wire bits") or ""),
        "public_wires": str(parse_int_line(block, "Number of public wires") or ""),
        "public_wire_bits": str(parse_int_line(block, "Number of public wire bits") or ""),
        "memories": str(parse_int_line(block, "Number of memories") or ""),
        "memory_bits": str(parse_int_line(block, "Number of memory bits") or ""),
        "cells_total": str(cell_summary["cells_total"]),
        "ff_cells": str(cell_summary["ff_cells"]),
        "lut_cells": str(cell_summary["lut_cells"]),
        "carry_cells": str(cell_summary["carry_cells"]),
        "mux_cells": str(cell_summary["mux_cells"]),
        "memory_cells": str(cell_summary["memory_cells"]),
        "script": str(script_path.relative_to(REPO_ROOT)),
        "log": str(log_path.relative_to(REPO_ROOT)),
        "timing_note": "No Fmax in Yosys-only flow; target-specific place-and-route is required for timing closure.",
    }


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fields = [
        "target",
        "top",
        "flow",
        "status",
        "description",
        "wires",
        "wire_bits",
        "public_wires",
        "public_wire_bits",
        "memories",
        "memory_bits",
        "cells_total",
        "ff_cells",
        "lut_cells",
        "carry_cells",
        "mux_cells",
        "memory_cells",
        "script",
        "log",
        "timing_note",
    ]

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def write_markdown(path: Path, rows: list[dict[str, str]]) -> None:
    lines: list[str] = []

    lines.append("# RTL synthesis summary")
    lines.append("")
    lines.append("## Purpose")
    lines.append("")
    lines.append(
        "This report provides a synthesis-oriented hardware-cost check for the "
        "synthesizable RTL blocks used in the dissertation model. Testbenches, "
        "fault-event generators, result builders, and post-run audit scripts are "
        "not included in the hardware-cost estimate."
    )
    lines.append("")
    lines.append("The report contains two Yosys-only flows:")
    lines.append("")
    lines.append("- `generic`: technology-independent synthesis to generic gates.")
    lines.append("- `xilinx_xc7_estimate`: Xilinx 7-series mapping estimate using `synth_xilinx`.")
    lines.append("")
    lines.append(
        "The Yosys-only flows estimate logic/register structure. They do not provide "
        "a valid maximum clock frequency; Fmax requires target-specific place-and-route "
        "and timing constraints."
    )
    lines.append("")
    lines.append("## Synthesized RTL blocks")
    lines.append("")
    lines.append("| target | top module | role |")
    lines.append("|---|---|---|")
    for t in TARGETS:
        lines.append(f"| `{t.name}` | `{t.top}` | {t.description} |")

    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("| target | flow | status | cells | FF | LUT | carry | mux | log |")
    lines.append("|---|---|---|---:|---:|---:|---:|---:|---|")

    for r in rows:
        lines.append(
            f"| `{r['target']}` | `{r['flow']}` | {r['status']} | "
            f"{r['cells_total'] or '-'} | {r['ff_cells'] or '-'} | "
            f"{r['lut_cells'] or '-'} | {r['carry_cells'] or '-'} | "
            f"{r['mux_cells'] or '-'} | `{r['log']}` |"
        )

    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    lines.append(
        "The synthesizable controller path consists of the scrub controller, SEC-DED "
        "decode path, interval selection logic, and measured-control estimator. The latched-DUE audit used "
        "in the strategy testbench is a verification metric and is not counted as "
        "part of the deployed controller unless a separate diagnostic hardware counter "
        "is intentionally added."
    )
    lines.append("")
    lines.append(
        "For dissertation Section 4.8 these results should be described as RTL synthesis "
        "resource estimates. A final implementation-oriented timing statement requires "
        "choosing a concrete FPGA or ASIC library, adding timing constraints, and running "
        "place-and-route."
    )
    lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--output-dir", default="results/paper/synthesis")
    p.add_argument(
        "--flows",
        default="generic,xilinx_xc7_estimate",
        help="Comma-separated flows: generic,xilinx_xc7_estimate",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = REPO_ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    flows = [x.strip() for x in args.flows.split(",") if x.strip()]
    rows: list[dict[str, str]] = []

    for target in TARGETS:
        for flow in flows:
            print(f"--- synth {target.name} / {flow} ---")
            row = run_target(target, flow, output_dir)
            rows.append(row)
            print(
                f"{row['target']} {row['flow']} status={row['status']} "
                f"cells={row['cells_total']} ff={row['ff_cells']} lut={row['lut_cells']}"
            )

    write_csv(output_dir / "rtl_synthesis_summary.csv", rows)
    write_markdown(output_dir / "rtl_synthesis_summary.md", rows)

    failed = [r for r in rows if r["status"] != "ok"]
    print(f"rows: {len(rows)}")
    print(f"failed: {len(failed)}")
    print(f"summary: {args.output_dir}/rtl_synthesis_summary.md")
    print(f"csv: {args.output_dir}/rtl_synthesis_summary.csv")

    if failed:
        for r in failed:
            print(f"FAILED {r['target']} {r['flow']} log={r['log']}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()

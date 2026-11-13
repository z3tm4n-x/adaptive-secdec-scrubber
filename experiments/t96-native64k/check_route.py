"""Compose routed pin paths with the -45 asynchronous read/write datasheet.
Timing report convention follows T104 physical/check_io.py at 8ce9104.
The 100 MHz phases, terminals, checks and coverage here belong to native64.
"""
import argparse
import json
import re
from decimal import Decimal as D
from pathlib import Path

# T186 calendar.json at 39cd9721, adopted in CONTRACT.md.
CALENDAR_EDGE_NS = D("0.5")
MIN_CLOCK_SCALE = D("0.99999")
FMC_MIN_NS, FMC_MAX_NS = D("0.1"), D("0.5")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def paths(report, direction):
    for block in re.split(r"(?m)^Slack", report)[1:]:
        def number(pattern):
            match = re.search(pattern, block)
            require(match, "Missing timing field: " + pattern)
            return D(match[1])
        endpoint = re.search(("Source" if direction == "input" else "Destination") + r":\s+(\S+)", block)[1]
        delay = number(r"Data Path Delay:\s+(-?[\d.]+)ns")
        clock = number((r"Destination Clock Delay \(DCD\):\s+" if direction == "input" else
                        r"Source Clock Delay\s+\(SCD\):\s+") + r"(-?[\d.]+)ns")
        arcs = re.findall(r"\((Setup|Hold)_\w+\)\s+(-?[\d.]+)", block)
        setup = max([D(0)] + [-D(x) for k, x in arcs if k == "Setup"])
        hold = max([D(0)] + [D(x) for k, x in arcs if k == "Hold"])
        yield endpoint, delay, clock, setup, hold, number(r"Clock Uncertainty:\s+([\d.]+)ns")


def check(directory, read_access=D(45), *, edge_ns=CALENDAR_EDGE_NS):
    def read(file):
        return (directory / file).read_text(encoding="utf-8", errors="replace")
    summary = read("timing.rpt")
    row = re.search(r"WNS\(ns\).*?\n\s*[- ]+\n\s*([\d. -]+)", summary)
    require(row, "Design timing summary missing")
    fields = row[1].split()
    wns, whs, wpws = D(fields[0]), D(fields[4]), D(fields[8])
    # Whole-design WNS can be a pin path with a max-delay constraint. Read
    # the separate register-to-register row of the Intra Clock Table.
    intra = summary.split("| Intra Clock Table", 1)[1].split("| Inter Clock Table", 1)[0]
    logic_clock = re.search(r"(?m)^\s*clk_i\s+(-?[\d.]+)\s+-?[\d.]+\s+\d+\s+\d+\s+(-?[\d.]+)\s+", intra)
    require(logic_clock, "Missing clk_i intra-clock setup/hold")
    constraints = read("effective.xdc")
    clock_model = {"clock": "clk_i", "wns_ns": logic_clock[1], "whs_ns": logic_clock[2]}
    for kind, expected in (("setup", D(".5")), ("hold", D(".1"))):
        setting = re.search(rf"(?m)^set_clock_uncertainty -{kind}\s+([\d.]+)\s+\[get_clocks \*\]", constraints)
        require(setting and D(setting[1]) == expected, f"Unexpected {kind} uncertainty on generated clocks")
        clock_model[f"user_{kind}_uncertainty_ns"] = setting[1]
    clock_model["scope"] = "Relative clock timing at the registers must meet this STA model, including the source and MMCM."
    timing_checks = dict(re.findall(r"(?m)^\d+\. checking (\w+) \((\d+)\)", read("check.rpt")))
    for category in ("no_clock", "unconstrained_internal_endpoints", "no_input_delay", "no_output_delay",
                     "multiple_clock", "loops"):
        require(timing_checks.get(category)=="0", f"Timing coverage incomplete: {category}")
    util = read("utilization.rpt")
    def usage(name):
        return int(re.search(r"(?m)^\| " + name + r"\s*\|\s*(\d+)", util)[1])
    resource = {k: usage(k) for k in ("Slice LUTs", "Slice Registers", "ILOGIC", "OLOGIC", "Block RAM Tile", "DSPs", "BUFGCTRL", "MMCME2_ADV")}
    route = read("route.rpt")
    net_count = int(re.search(r"# of routable nets\.+\s*:\s*(\d+)", route)[1])
    routed = int(re.search(r"# of fully routed nets\.+\s*:\s*(\d+)", route)[1])
    routing_errors = int(re.search(r"# of nets with routing errors\.+\s*:\s*(\d+)", route)[1])
    drc = read("drc.rpt")
    drc_errors = re.findall(r"(?m)^([\w-]+#\d+) (?:Critical Warning|Error)\s*$", drc)
    drc_warnings = re.findall(r"(?m)^([\w-]+#\d+) Warning\s*$", drc)
    ios = [f"sram_dq[{i}]" for i in range(16)]
    expected = {"input": set(ios + ["sram_err"]), "output": set(ios + [f"sram_a[{i}]" for i in range(15)] +
                ["sram_ce_n", "sram_oe_n", "sram_we_n"])}
    extrema = {"input": [], "output": []}
    for direction in extrema:
        for corner in ("Slow", "Fast"):
            for kind in ("min", "max"):
                group = list(paths(read(f"clocked_{direction}_{corner}_{kind}.rpt"), direction))
                require({x[0] for x in group} == expected[direction],
                        f"Incomplete pin timing coverage {direction}/{corner}/{kind}")
                extrema[direction].extend(group)
                if direction=="output":
                    for name, reg in (("data","dq_out"),("direction","pad_t_n")):
                        report=read(f"clocked_{name}_{corner}_{kind}.rpt")
                        source_bits=set(re.findall(r"(?m)^  Source:\s+core/"+reg+r"_reg\[(\d+)\]/C",report))
                        extra=list(paths(report,"output"))
                        require(source_bits=={str(i) for i in range(16)} and
                                {p[0] for p in extra}==set(ios), f"Missing {name} arcs/{corner}/{kind}")
                        extrema[direction].extend(extra)
    ins, outs = extrema["input"], extrema["output"]
    bound = D(".001")   # reports print to 0.001 ns; round each input outwards
    clks = [p[2] for p in ins + outs]
    skew = max(clks) - min(clks) + 2 * bound
    uncertainty = max(p[5] for p in ins + outs) + bound
    require(uncertainty >= D(".5"), "setup uncertainty missing")
    imin, imax = min(p[1] for p in ins) - bound, max(p[1] for p in ins) + bound
    omin, omax = min(p[1] for p in outs) - bound, max(p[1] for p in outs) + bound
    setup = max(D(".01"), max(p[3] for p in ins)) + bound
    hold = max(D(".33"), max(p[4] for p in ins)) + bound
    # For distinct edges the earlier one can be late by J and the later one
    # early by J. Keep that worst-case loss on top of the full STA allowance.
    # The board flight delays are independent terms in the propagation path.
    require(edge_ns >= 0, "Negative calendar edge bound")
    pair_loss = 2 * edge_ns

    def elapsed_min(nominal_ns):
        return D(nominal_ns) * MIN_CLOCK_SCALE - pair_loss

    read_budget = elapsed_min(60) - skew - omax - 2*FMC_MAX_NS - imax - setup - uncertainty
    pin_spread = skew + omax - omin + (FMC_MAX_NS - FMC_MIN_NS) + uncertainty
    def span(t):
        return elapsed_min(t) - pin_spread
    margins = {
        "address_CE_ERR_read_access_45": read_budget - read_access,
        "OE_read_access_22": read_budget - 22,
        "capture_hold_until_OE_high": elapsed_min(10) - skew + omin + 2*FMC_MIN_NS + imin - uncertainty - hold,
        "WE_low_50_min35": span(50) - 35,
        "address_CE_to_end_160_min35": span(160) - 35,
        "write_data_setup_60_min25": span(60) - 25,
        "write_data_hold_20_min0": span(20),
        "write_address_setup_110_min0": span(110),
        "write_address_hold_to_release_40": span(40),
        "access_spacing_min240_cycle45": span(240) - 45,
        "OE_high_to_FPGA_drive_30_min18": span(30) - 18,
        "drive_off_to_next_OE_60_min0": span(60),
        "WE_rise_before_release": elapsed_min(40) - skew - uncertainty - omax - FMC_MAX_NS,
        "last_repair_release_to_cut_140": elapsed_min(140) - skew - uncertainty - omax - FMC_MAX_NS,
    }
    notes = ["High five SRAM address lines and both byte enables are static on this board top.",
             "Conditional 15 pF and 0.1..0.5 ns adapter, 3 ns SRAM edges, clocks and primed memory."]
    # Expose physical edge separation in addition to the nominal schedule.
    return {"part": "xc7z020clg484-1", "clock_MHz": 100, "wns_ns": str(wns), "whs_ns": str(whs),
            "wpws_ns": str(wpws), "wns_failing": int(fields[2]), "whs_failing": int(fields[6]),
            "wpws_failing": int(fields[10]), "resources": resource,
            "internal_sta_model": clock_model,
            "routable_nets": net_count, "fully_routed_nets": routed, "routing_errors": routing_errors,
            "drc_errors": drc_errors, "drc_warnings": drc_warnings,
            "pad_counts": {k: len(v) for k, v in expected.items()},
            "extrema_ns": {k:str(v) for k,v in {"input_min":imin,"input_max":imax,"output_min":omin,
                "output_max":omax,"clock_spread":skew,"uncertainty":uncertainty,"setup":setup,"hold":hold}.items()},
            "external_clock_budget": {
                "minimum_clock_scale": str(MIN_CLOCK_SCALE), "per_edge_J_ns": str(edge_ns),
                "distinct_edge_shortening_2J_ns": str(pair_loss),
                "retained_STA_uncertainty_ns": str(uncertainty),
                "combined_allowance_ns": str(pair_loss+uncertainty),
                "FMC_round_trip_max_ns": str(2*FMC_MAX_NS),
                "minimum_60ns_edge_separation_ns": str(elapsed_min(60)),
                "available_SRAM_read_access_ns": str(read_budget)},
            "external_margin_ns": {k: str(v) for k,v in margins.items()},
            "notes": notes, "pass": min(wns,whs,wpws)>0 and routed==net_count and routing_errors==0 and
            not drc_errors and min(margins.values())>=0}


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("reports", type=Path)
    parser.add_argument("--output", type=Path)
    args=parser.parse_args()
    result=check(args.reports)
    wrong=check(args.reports,D(100))
    require(D(wrong["external_margin_ns"]["address_CE_ERR_read_access_45"])<0 and
            not wrong["pass"], "100 ns memory was not rejected by the read access check")
    output=json.dumps(result,indent=2,ensure_ascii=False)+"\n"
    print(output,end="")
    if args.output:
        args.output.write_text(output,encoding="utf-8")
    if not result["pass"]:
        raise SystemExit(1)

"""Verify published trial summaries against the calendar, independently of RTL."""
import argparse
from decimal import Decimal as D, ROUND_FLOOR
from hashlib import sha256
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent


def read_trial(file, marker):
    raw = file.read_text(encoding="utf-8")
    lines = [s for s in raw.splitlines() if s.startswith(marker + " ")]
    if len(lines) != 1 or "FATAL" in raw:
        raise ValueError(f"{file} lacks a unique completed witness")
    return {key: int(value) for key, value in re.findall(r"(\w+)=(-?\d+)", lines[0])}


def peak(duration, window=1000000):
    # Fully populated protective frames bound any sparser schedule. Exact
    # maximum over arbitrary window start: piecewise-linear overlap has its
    # extrema at an edge of the window or the translated pulse edges.
    offsets = (0, 240, 520, 760)
    frame = 1400
    full, rem = divmod(window, frame)
    edges = [x for a in offsets for x in (a, a+duration)]
    candidates = sorted({0, *edges, *((x-rem) % frame for x in edges)})
    def suffix(u):
        return sum(max(0, min(u+rem,a+duration)-max(u,a))
                   for i in (0,1) for o in offsets for a in (o+i*frame,))
    return 4*full*duration + max(map(suffix,candidates))


def collect(sim,join,formal):
    traces={}
    for name, repairs, cut, known_fault in (("clean",0,True,False),("last",1,False,False),
                ("dense",32768,False,False),("hit",1,False,True),("phase",1,False,True)):
        r=read_trial(sim/(name+".txt"),"FULL")
        release=11468160+(200 if repairs else 100)
        assert (r["reads"],r["writes"],r["owner_ns"],r["longest_ns"])==(
                32768,repairs,(32768+repairs)*100,200 if repairs else 100)
        assert (r["last_sample_ns"],r["last_WE_rise_ns"],r["last_release_ns"])==(
                11468220,11468320 if repairs else -1,release)
        assert (r["seal_ns"],r["good_zero_ns"],r["command_ns"],r["next_ns"])==(
                -1 if known_fault else release,11468500 if cut else -1,11468700,11468800)
        assert r["application_reads"]==12 and r["application_reserved_ns"]==12*240
        traces[name]=r
    history=read_trial(sim/"policy.txt","POLICY")
    assert history["levels_mask"]==1023 and history["report_cases"]==13 and history["saturation"]==596
    joins=[read_trial(join/f"join-{level}-{defect}.txt","JOIN") for level,defect in
           [(n,0) for n in range(1,10)]+[(1,n) for n in range(1,6)]]
    for r in joins:
        assert r["physical_reads"]==32768
        assert r["next_rounds"]==(2**r["level"] if r["defect"] in (0,1) else 1)
        assert r["zero_at_cut"]==int(r["defect"] in (0,1,4,5))
    proofs={}
    for case in ("policy_safety","pins_agree"):
        t=(formal/(case+".txt")).read_text(encoding="utf-8")
        assert "Induction step proven: SUCCESS!" in t
        proofs[case]="temporal induction, all inputs"
    f=D("1.00001")
    bound=717*4*(200*f+1) # +2J per contiguous read/repair ownership
    assert peak(200)<=bound
    app=3*(240*f+1)
    repo_files=[*sorted((ROOT/"rtl/native64k").glob("*.sv")), *sorted(HERE.glob("*.sv")),
                *sorted(HERE.glob("*.sh")), *sorted(HERE.glob("*.py")),
                HERE/"board.xdc",HERE/"route.tcl",HERE/"CONTRACT.md"]
    return {"units":"nominal ns unless specified", "full_pin_trials":traces,
            "policy":history, "full_scan_boundary_trials":joins, "formal":proofs,
            "price":{"X_seconds_of_SRAM":0,"extra_seconds_per_I":"20.397479",
                "twofold_GEO_seconds":"1323044.327",
                "integer_I_sufficient_if_X_zero":int((D("1323044.327")/D("20.397479")).to_integral_value(rounding=ROUND_FLOOR)),
                "nominal_peak_protection_ns_in_any_ms_clean":peak(100),
                "nominal_peak_protection_ns_in_any_ms_all_ERR":peak(200),
                "physical_upper_protection_ns_in_any_ms":str(bound),
                "physical_upper_with_application_ns_in_any_ms":str(bound+app),
                "peak_continuous_protection_ns":200,"clean_duty_fraction":"2/7",
                "all_ERR_duty_fraction":"4/7"},
            "source_sha256_LF":{str(x.relative_to(ROOT)).replace(chr(92),"/"):
                sha256(x.read_bytes().replace(b"\r\n",b"\n")).hexdigest() for x in repo_files}}


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    for name in ("simulation","joined","formal","out"):
        parser.add_argument(name,type=Path)
    args=parser.parse_args()
    result=collect(args.simulation,args.joined,args.formal)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print("Verified 5 pin traces, 14 composed boundary traces, all levels, two induction checks.")

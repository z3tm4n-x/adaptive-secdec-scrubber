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
                ("dense",32768,False,False),("hit",1,False,True),("phase",1,False,True),
                ("missed",0,False,True),("shared_sample",0,True,False)):
        r=read_trial(sim/(name+".txt"),"FULL")
        release=11468160+(200 if repairs else 100)
        assert (r["reads"],r["writes"],r["owner_ns"],r["longest_ns"])==(
                32768,repairs,(32768+repairs)*100,200 if repairs else 100)
        assert (r["last_sample_ns"],r["last_WE_rise_ns"],r["last_release_ns"])==(
                -1 if name=="missed" else 11468220,11468320 if repairs else -1,release)
        assert (r["seal_ns"],r["good_zero_ns"],r["command_ns"],r["next_ns"])==(
                -1 if known_fault else release,11468500 if cut else -1,11468700,11468800)
        assert r["application_reads"]==12 and r["application_reserved_ns"]==12*240
        assert r["partial_owner_ns"]==(3276830 if name=="last" else -1)
        traces[name]=r
    history=read_trial(sim/"policy.txt","POLICY")
    epoch_recovery={}
    for scenario,mode,before,promotion in (("before",0,1,3584),("0",0,0,3072),
            ("1",1,0,-1),("2",2,0,3584),("3",3,0,3584)):
        file=sim/f"epoch-{scenario}.txt"
        rec=read_trial(file,"EPOCH")
        assert (rec["mode"],rec["old"],rec["reads"],rec["writes"],rec["report"],
                rec["sample_ns"],rec["WE_rise_ns"],rec["release_ns"],rec["cut_ns"],rec["install_ns"],
                rec["first_2L_epoch"])==(mode,before,32768,1,0,11468220,11468320,
                                         11468360,11468500,11468700,promotion)
        lines=file.read_text(encoding="utf-8").splitlines()
        cells=[tuple(map(int,m.groups())) for line in lines
               if (m:=re.search(r"^CELL .*epoch=(\d+) quiet=(\d+) period_L=(\d+)$",line))]
        expected_z={"before":[0,0,1,2,3],"0":[0,1,2,3,4],"1":[0]*5,
                    "2":[0,0,1,2,3],"3":[0,0,1,2,3]}[scenario]
        assert cells==[(1536+512*i,z,2 if z>=3 else 1) for i,z in enumerate(expected_z)]
        starts={int(m[1]):int(m[2]) for line in lines
                if (m:=re.fullmatch(r"START epoch=(\d+) address0=([01])",line))}
        for ep,z,period in cells[3:]:
            assert (starts[ep],starts[ep+1],starts[ep+2])==(1,int(period==1),1)
        epoch_recovery[scenario]={"events":rec,"common_cells_epoch_z_period_L":cells,
                                  "observed_address_zero_at_boundaries":starts}
    assert history["levels_mask"]==1023 and history["report_cases"]==15 and history["saturation"]==596
    joins=[read_trial(join/f"join-{level}-{defect}.txt","JOIN") for level,defect in
           [(n,0) for n in range(1,10)]+[(1,n) for n in range(1,6)]+[(2,6)]]
    for r in joins:
        assert r["physical_reads"]==32768
        assert r["next_rounds"]==(2**r["level"] if r["defect"] in (0,1) else 1)
        assert r["zero_at_cut"]==int(r["defect"] in (0,1,4,5,6))
        assert r["literal_idle"]==r["idle_app_reads"]==int(r["level"]==1 and r["next_rounds"]>1)
    proofs={}
    for case in ("policy_safety","calendar_positions"):
        t=(formal/(case+".txt")).read_text(encoding="utf-8")
        assert "Induction step proven: SUCCESS!" in t
        proofs[case]="temporal induction, all inputs"
    bounded=(formal/"pins_bounded.txt").read_text(encoding="utf-8")
    assert "SAT proof finished - no model found: SUCCESS!" in bounded and "-seq 142 " in bounded
    proofs["pins_bounded"]="142 edges from cold start; arbitrary data, ERR and application requests"
    f=D("1.00001")
    bound=717*4*(200*f+1) # +2J per contiguous read/repair ownership
    assert peak(200)<=bound
    app=3*(240*f+1)
    repo_files=[*sorted((ROOT/"rtl/native64k").glob("*.sv")), *sorted(HERE.glob("*.sv")),
                *sorted(HERE.glob("*.sh")), *sorted(HERE.glob("*.py")),
                HERE/"board.xdc",HERE/"route.tcl",HERE/"CONTRACT.md"]
    return {"units":"nominal ns unless specified", "full_pin_trials":traces,
            "policy":history, "full_scan_boundary_trials":joins, "formal":proofs,
            "closed_epoch_recovery":epoch_recovery,
            "fault_observations":{
                "missed":"Actual capture strobe suppressed on final ERR. Incomplete service; no report or authorizing zero. No repair.",
                "shared_sample":"ERR sampled high at +60 ns, then its common FF corrupted before +70 ns. No repair and a false accepting zero.",
                "hit":"One of two obligations lost after +70 ns. Actual write completes and report is withheld.",
                "phase":"One phase bit flipped before the last sample. Actual sample and write complete; report is withheld."},
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
    print("Verified 7 pin traces, 15 composed boundary traces, all levels, two induction and one bounded proof.")

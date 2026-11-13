"""Redact local paths/host from the published vendor/tool reports, never values."""
from pathlib import Path
import argparse
import re
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED


def add(archive, name, source):
    raw = source.read_text(encoding="utf-8", errors="strict").replace("\r\n","\n")
    raw = re.sub(r"/mnt/[a-z]/Users/[^\s\"']*?/t96-native64k-release", "<checkout>", raw)
    raw = re.sub(r"/mnt/[a-z]/Users/[^\s\"']*?/t96-native64k-results/", "<work>/", raw)
    raw = re.sub(r"(?m)^\| Host\s*:.*$", "| Host         : <host omitted>",raw)
    info = ZipInfo(name,(2000,1,1,0,0,0))
    info.compress_type = ZIP_DEFLATED
    archive.writestr(info,raw.encode("utf-8"),compresslevel=9)


if __name__=="__main__":
    p=argparse.ArgumentParser()
    for name in ("route","sim","joined","formal","sentinel","out"):
        p.add_argument(name,type=Path)
    a=p.parse_args()
    with ZipFile(a.out,"w") as z:
        for name in ("timing","utilization","route","drc","check","pins","worst_setup","worst_hold"):
            add(z,"sta/"+name+".rpt",a.route/(name+".rpt"))
        add(z,"sta/effective.xdc",a.route/"effective.xdc")
        for file in sorted(a.route.glob("clocked_*.rpt")):
            add(z,"sta/"+file.name,file)
        for name in ("clean","last","dense","hit","phase","shared_sample","missed","policy"):
            add(z,"sim/"+name+".txt",a.sim/(name+".txt"))
        for name in ("before","0","1","2","3"):
            file=a.sim/f"epoch-{name}.txt"
            add(z,"sim/"+file.name,file)
        for file in sorted(a.joined.glob("join-*.txt")):add(z,"join/"+file.name,file)
        for name in ("calendar_positions","pins_bounded","policy_safety"):add(z,"formal/"+name+".txt",a.formal/(name+".txt"))
        add(z,"sentinel/rejected.txt",a.sentinel/"rejected.txt")

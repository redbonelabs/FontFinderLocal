"""Verify native preparation and allocation optimization against preserved code.

Runs outside timed benchmark runs. Checks actual local TTF/CFF/TTC/variable faces
and exact score/alignment equivalence over varied synthetic geometry and anchors.
"""
import json
from pathlib import Path
import subprocess
import types

import cv2
import numpy as np
from app.matching import metrics
from app.matching.raster import Rasterizer
from .benchmark_runner import DATA, RESULTS, write_json


def main():
    source=subprocess.check_output(["git","-c",f"safe.directory={Path.cwd().as_posix()}","show","101638d:app/matching/metrics.py"],text=True)
    baseline=types.ModuleType("app.matching.baseline_metrics");baseline.__package__="app.matching";exec(compile(source,"baseline_metrics.py","exec"),baseline.__dict__)
    rng=np.random.default_rng(631);checks=0
    for width in (40,170,600):
        ref=np.zeros((82,width),np.uint8)
        for _ in range(9):
            x=int(rng.integers(0,width-6));y=int(rng.integers(0,60))
            cv2.rectangle(ref,(x,y),(x+5,y+18),255,-1)
        for factor in (.3,.85,1,1.2,2.4):
            candidate=cv2.resize(ref,(round(width*factor),71))
            for anchor in ("left","center","right"):
                for sensitivity in ("strict","balanced","flexible"):
                    a=baseline.detailed(ref,candidate,"ASAS",sensitivity,anchor)
                    b=metrics.detailed(ref,candidate,"ASAS",sensitivity,anchor)
                    assert a==b,(width,factor,anchor,sensitivity,a,b)
                    checks+=1
    old=Rasterizer();old._font_data=lambda face,path:(old.assets.asset(face),0)
    new=Rasterizer();matched=[];exclusions=[];failures=[]
    for face in json.loads((DATA/"catalog.json").read_text(encoding="utf-8")):
        variants=[{}]+([face["instances"][-1]["coordinates"]] if face["axes"] and face["instances"] else [])
        for coords in variants:
            values=[]
            for raster in (old,new):
                try:values.append(raster.render(face,"SuPrEmE!",coordinates=coords))
                except Exception as exc:values.append(type(exc).__name__)
            if isinstance(values[0],str) or isinstance(values[1],str):
                if values[0]!=values[1]:failures.append({"id":face["id"],"error":str(values)})
                else:exclusions.append({"id":face["id"],"reason":values[0]})
            else:
                a,b=values
                if not (a.advance==b.advance and a.glyphs==b.glyphs and np.array_equal(a.mask,b.mask)):
                    failures.append({"id":face["id"],"name":face["full_name"],"coords":coords})
                else:matched.append({"id":face["id"],"name":face["full_name"],"container":face["container"],"format":face["format"],"coordinates":coords})
    report={"alignment_checks":checks,"identical_renderings":len(matched),"matching_exclusions":len(exclusions),"failures":failures,"matched":matched,"exclusions":exclusions}
    write_json(RESULTS/"optimization-equivalence.json",report)
    print(json.dumps({k:v for k,v in report.items() if k not in ("matched","exclusions")}))
    assert not failures


if __name__=="__main__":main()

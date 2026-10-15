"""Freeze independent Pillow references, then evaluate the unchanged catalog.

python -m benchmarks.benchmark_runner prepare
python -m benchmarks.benchmark_runner run --label baseline --split dev
python -m benchmarks.benchmark_runner run --label baseline --split heldout
"""
import argparse
from collections import Counter, defaultdict
import ctypes
import hashlib
import json
from pathlib import Path
import platform
import statistics
import subprocess
import time
from urllib.request import urlopen

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from fontTools.ttLib import TTFont

from app.matching.engine import match
from app.matching.models import MatchRequest, Processing
from app.matching.preprocess import preprocess
from app.matching.raster import Rasterizer, missing_glyphs
from app.rendering import locate

ROOT = Path(__file__).parent
DATA = ROOT / "datasets" / "generated"
RESULTS = ROOT / "results"
SEED = 20261014

# Frozen before baseline. Same distortion coverage, different font/text pairs in each split.
# Labels are descriptive benchmark strata, not changes to catalog classification.
DEV = [
    ("Arial", "SuPrEmE!", "sans", "clean", 46),
    ("Georgia", "Game Over!", "serif", "clean", 72),
    ("Brush Script MT Italic", "Laser Cue", "script", "clean", 126),
    ("Wide Latin", "PINBALL", "extended", "clean", 72),
    ("Bahnschrift", "PLAYER 1", "variable", "variable", 72),
    ("Arial Narrow", "Maximum Power", "condensed", "crop", 46),
    ("Impact", "SUPREME", "bold", "outline", 72),
    ("Rockwell Bold", "BONUS 100!", "serif", "shadow", 96),
    ("Segoe UI Light", "Il1 O0 Qgj", "thin", "noise", 46),
    ("Times New Roman Italic", "AVATAR, ffij", "italic", "rotation", 72),
    ("Verdana", "BEEKEEPER", "sans", "contrast", 24),
    ("Jokerman", "Game Over!", "decorative", "color", 96),
    ("Courier New", "  LEVEL  11!  ", "monospace", "tracking", 72),
    ("Futura Book BT", "Maximum Power", "sans", "stretch", 126),
    ("Trebuchet MS", "Laser Cue", "sans", "perspective", 72),
    ("Arial Bold", "PINBALL", "bold", "artwork", 46),
    ("Calibri", "1234567890", "sans", "low_resolution", 24),
    ("Segoe UI", "Café naïve Ågj", "sans", "antialias", 46),
    ("Blackadder ITC", "Supreme", "decorative", "inverted", 126),
    ("Cambria", "  A  B, B!  ", "serif", "background", 72),
]
HELDOUT = [
    ("Tahoma", "Supreme", "sans", "clean", 72),
    ("Palatino Linotype", "Maximum Power", "serif", "clean", 46),
    ("Edwardian Script ITC", "Game Over!", "script", "clean", 126),
    ("Williams Pinball Wide", "PLAYER 1", "extended", "clean", 96),
    ("Cascadia Code Regular", "Il1 O0 Qgj", "variable", "variable", 46),
    ("Rockwell Condensed", "Laser Cue", "condensed", "crop", 72),
    ("Arial Black", "PINBALL", "bold", "outline", 96),
    ("Georgia Bold", "Maximum Power", "serif", "shadow", 72),
    ("Calibri Light", "Game Over!", "thin", "noise", 72),
    ("Arial Italic", "SuPrEmE, AV!", "italic", "rotation", 46),
    ("Trebuchet MS", "1234567890", "sans", "contrast", 24),
    ("Matura MT Script Capitals", "SUPREME", "decorative", "color", 126),
    ("Consolas", "  PLAYER  1!  ", "monospace", "tracking", 46),
    ("Century Gothic", "Game Over!", "sans", "stretch", 96),
    ("Verdana", "PINBALL", "sans", "perspective", 126),
    ("Impact", "SUPER BONUS!", "bold", "artwork", 72),
    ("Tahoma", "Maximum Power", "sans", "low_resolution", 24),
    ("Times New Roman", "Été, Ångström!", "serif", "antialias", 72),
    ("Freestyle Script", "Laser Cue", "script", "inverted", 96),
    ("Cambria Bold", "BEEKEEPER", "serif", "background", 46),
]


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def geometry_digest(face):
    """Very narrow equivalence: identical shaping/outline/metric tables, not family names.

    Hinting is included; names and timestamps alone cannot make an identification fail.
    Unknown formats/errors are equivalent only to their own ID.
    """
    try:
        with TTFont(locate(face), fontNumber=face["face_index"], lazy=True) as font:
            tables = ["cmap", "glyf", "loca", "CFF ", "CFF2", "hmtx", "vmtx", "hhea", "vhea",
                      "maxp", "kern", "GPOS", "GSUB", "GDEF", "fvar", "gvar", "avar", "HVAR",
                      "VVAR", "MVAR", "cvar", "cvt ", "fpgm", "prep", "COLR", "CPAL", "SVG "]
            digest = hashlib.sha256()
            digest.update(str(font["head"].unitsPerEm).encode())
            for tag in tables:
                digest.update(tag.encode())
                digest.update(font.reader[tag] if tag in font else b"absent")
            return digest.hexdigest()
    except Exception:
        return face["id"]


def reference(face, text, size, kind, rng, coordinates):
    # Independent Pillow/FreeType BASIC layout, hinted at source resolution; the
    # matcher uses HarfBuzz/unhinted native glyphs at 96 px. No matcher rasters here.
    supersample = 2 if kind in ("antialias", "low_resolution") else 1
    font = ImageFont.truetype(str(locate(face)), size=size*supersample, index=face["face_index"],
                              layout_engine=ImageFont.Layout.BASIC)
    if coordinates:
        font.set_variation_by_axes([coordinates.get(a["tag"], a["default"]) for a in face["axes"]])
    margin = 24*supersample
    tracking = 2.5*supersample if kind == "tracking" else 0
    bounds = font.getbbox(text)
    width = round(font.getlength(text) + max(0,len(text)-1)*tracking) + margin*2 + max(0,-bounds[0])
    height = bounds[3]-bounds[1]+margin*2
    mask = Image.new("L", (width, height))
    draw = ImageDraw.Draw(mask)
    origin = (margin-min(0,bounds[0]), margin-bounds[1])
    if tracking:
        x = origin[0]
        for char in text:
            draw.text((x,origin[1]), char, font=font, fill=255)
            x += font.getlength(char)+tracking
    else:
        draw.text(origin, text, font=font, fill=255)
    if supersample != 1:
        mask = mask.resize((round(width/supersample),round(height/supersample)),Image.Resampling.LANCZOS)
    bg, fg = (245,245,245), (20,20,20)
    if kind in ("color", "artwork"): bg,fg=(38,72,125),(245,188,35)
    if kind == "inverted": bg,fg=(18,18,24),(237,241,252)
    image = Image.new("RGB",mask.size,bg)
    if kind == "background":
        yy,xx = np.indices((mask.height,mask.width))
        background = np.clip(215+22*xx/max(1,mask.width-1)+4*np.sin(yy/7),0,255).astype(np.uint8)
        image=Image.fromarray(np.repeat(background[...,None],3,axis=2))
    if kind in ("shadow", "artwork"):
        shadow=Image.new("L",mask.size); shadow.paste(mask,(4,4))
        image.paste((100,100,100) if kind == "shadow" else (12,20,40),(0,0),shadow)
    if kind in ("outline", "artwork"):
        outline=mask.filter(ImageFilter.MaxFilter(5))
        image.paste((8,8,8),(0,0),outline)
        fg=(185,40,35) if kind == "outline" else fg
    image.paste(fg,(0,0),mask)
    options={}
    if kind == "rotation":
        image=image.rotate(3,resample=Image.Resampling.BICUBIC,expand=True,fillcolor=bg)
        options={"deskew":True}
    elif kind == "noise":
        a=np.asarray(image).astype(float)+rng.normal(0,14,(*np.asarray(image).shape[:2],1))
        image=Image.fromarray(np.clip(a,0,255).astype(np.uint8))
    elif kind == "contrast":
        image=Image.fromarray((np.asarray(image).astype(float)*.18+164).astype(np.uint8))
    elif kind == "crop": image=image.crop((16,18,image.width-16,image.height-18))
    elif kind == "stretch": image=image.resize((round(image.width*1.14),image.height),Image.Resampling.BICUBIC)
    elif kind == "perspective":
        w,h=image.size
        src=np.float32([[0,0],[w-1,0],[w-1,h-1],[0,h-1]])
        dst=np.float32([[8,4],[w-12,0],[w-1,h-4],[0,h-1]])
        image=Image.fromarray(cv2.warpPerspective(np.asarray(image),cv2.getPerspectiveTransform(src,dst),(w,h),borderValue=bg))
        # Deliberately uncorrected mild photo-like distortion; report separately.
    elif kind == "low_resolution":
        image=image.resize((round(image.width*.7),round(image.height*.7)),Image.Resampling.BILINEAR)
    elif kind == "altered":
        a=np.asarray(image).copy()
        for x in range(a.shape[1]): a[:,x]=np.roll(a[:,x],round(5*np.sin(x/19)),axis=0)
        image=Image.fromarray(a)
    return image,options


def prepare(url):
    if (DATA/"manifest.json").exists(): raise SystemExit("Dataset already frozen; use it or deliberately choose a new dataset version.")
    with urlopen(url+"/api/fonts") as response: catalog=json.load(response)
    faces=sorted(catalog["fonts"],key=lambda f:f["id"])
    if catalog["scan"]["running"]: raise SystemExit("Wait for catalog scan before freezing.")
    DATA.mkdir(parents=True,exist_ok=True)
    digests={f["id"]:geometry_digest(f) for f in faces}
    cases=[]; skipped=[]
    for split,specs in (("dev",DEV),("heldout",HELDOUT),
                        ("probes",[("Arial","SUPREME","sans","absent",72),
                                   ("Georgia","Game Over!","serif","absent",96),
                                   ("Impact","PINBALL","bold","altered",72),
                                   ("Jokerman","BONUS!","decorative","altered",96)])):
        for i,(name,text,category,kind,size) in enumerate(specs):
            found=[f for f in faces if f["full_name"]==name and not missing_glyphs(f,text)]
            if not found:
                skipped.append({"split":split,"name":name,"reason":"Exact named face with required coverage unavailable"});continue
            face=found[0];coords={}
            if kind=="variable" and face["axes"]:
                instances=face["instances"]
                coords=(instances[len(instances)//2]["coordinates"] if instances else
                        {a["tag"]:a["max"] for a in face["axes"]})
            key=f"{split}-{i:02}-{kind}"
            image,options=reference(face,text,size,kind,np.random.default_rng(SEED+i),coords)
            image.save(DATA/f"{key}.png")
            cases.append({"id":key,"split":split,"origin_id":face["id"],"origin":name,"text":text,
                          "font_type":category,"distortion":kind,"size":size,"coordinates":coords,
                          "quality":"clean" if kind in ("clean","variable") else "synthetic distortion",
                          "source":"custom" if "custom" in face["sources"] else "installed",
                          "processing":options,"image_sha256":hashlib.sha256((DATA/f"{key}.png").read_bytes()).hexdigest(),
                          "equivalent_ids":[f["id"] for f in faces if digests[f["id"]]==digests[face["id"]]]})
    manifest={"version":1,"seed":SEED,"candidate_count":len(faces),"candidates":[{"id":f["id"],"name":f["full_name"],"sources":f["sources"],"geometry_digest":digests[f["id"]]} for f in faces],
              "cases":cases,"skipped":skipped,"source_counts":dict(Counter(s for f in faces for s in f["sources"]))}
    write_json(DATA/"catalog.json",faces)
    write_json(DATA/"manifest.json",manifest)
    write_json(ROOT/"datasets"/"manifest.json",manifest)
    print(json.dumps({k:v for k,v in manifest.items() if k not in ("candidates","cases")}))


def memory_mb():
    if platform.system()!="Windows": return None
    class Counters(ctypes.Structure):
        _fields_=[("cb",ctypes.c_ulong),("PageFaultCount",ctypes.c_ulong)]+[(k,ctypes.c_size_t) for k in
           ("PeakWorkingSetSize","WorkingSetSize","QuotaPeakPagedPoolUsage","QuotaPagedPoolUsage",
            "QuotaPeakNonPagedPoolUsage","QuotaNonPagedPoolUsage","PagefileUsage","PeakPagefileUsage")]
    info=Counters();info.cb=ctypes.sizeof(info)
    handle=ctypes.windll.kernel32.GetCurrentProcess
    handle.restype=ctypes.c_void_p
    call=ctypes.windll.psapi.GetProcessMemoryInfo
    call.argtypes=[ctypes.c_void_p,ctypes.POINTER(Counters),ctypes.c_ulong]
    return round(info.WorkingSetSize/1024**2,2) if call(handle(),ctypes.byref(info),info.cb) else None


def summarize(rows):
    ranks=[r["rank"] for r in rows if r["rank"] is not None]
    seconds=[r["seconds"] for r in rows]
    return {"cases":len(rows),**{f"top{k}":sum(r["rank"] is not None and r["rank"]<=k for r in rows)/len(rows) for k in (1,5,10)},
            **{f"equivalent_top{k}":sum(r["equivalent_rank"] is not None and r["equivalent_rank"]<=k for r in rows)/len(rows) for k in (1,5,10)},
            "median_rank_retrieved":statistics.median(ranks) if ranks else None,"not_retrieved":len(rows)-len(ranks),
            "mean_seconds":statistics.mean(seconds),"median_seconds":statistics.median(seconds),"p90_seconds":float(np.percentile(seconds,90)),
            "excluded_totals":dict(sum((Counter(r["excluded"]) for r in rows),Counter())),
            "max_sampled_working_set_mb":max((r["working_set_mb"] or 0 for r in rows),default=0)}


def run(label,split,only):
    manifest=json.loads((DATA/"manifest.json").read_text(encoding="utf-8"))
    faces=json.loads((DATA/"catalog.json").read_text(encoding="utf-8"))
    for face in faces: locate(face)  # fail closed on changed/unavailable frozen input
    output=RESULTS/f"{label}-{split}.json"
    if output.exists(): raise SystemExit(f"Refusing to overwrite preserved run: {output}")
    revision=subprocess.check_output(["git","-c",f"safe.directory={Path.cwd().as_posix()}","rev-parse","HEAD"],text=True).strip()
    rows=[]
    cases=[c for c in manifest["cases"] if c["split"]==split and (not only or c["id"] in only.split(','))]
    for case in cases:
        path=DATA/f"{case['id']}.png"
        assert hashlib.sha256(path.read_bytes()).hexdigest()==case["image_sha256"]
        candidates=[f for f in faces if case["distortion"]!="absent" or f["id"] not in case["equivalent_ids"]]
        raster=Rasterizer()  # identical cold native/asset cache per reference, OS disk cache uncontrolled
        start=time.perf_counter()
        processed=preprocess(Image.open(path),Processing(**case["processing"]))
        preprocessing=time.perf_counter()-start
        stages={}
        def progress(**kw): stages.setdefault(kw["stage"],time.perf_counter())
        report=match(candidates,processed,MatchRequest(process_id="benchmark",text=case["text"]),raster,progress=progress)
        elapsed=time.perf_counter()-start
        hits=[r for r in report["results"] if r["font_id"]==case["origin_id"]]
        equivalents=[r["rank"] for r in report["results"] if r["font_id"] in case["equivalent_ids"]]
        row={**case,"rank":hits[0]["rank"] if hits else None,"equivalent_rank":min(equivalents) if equivalents else None,
             "seconds":report["seconds"],"total_seconds":elapsed,"preprocess_seconds":preprocessing,
             "screening_seconds":stages.get("refining",time.perf_counter())-stages["screening"],
             "candidate_count":len(candidates),"eligible":report["eligible"],"excluded":report["excluded"],
             "warnings":report["warnings"],"working_set_mb":memory_mb(),"top10":report["results"][:10],
             "origin_result":hits[0] if hits else None}
        rows.append(row)
        # Write after every sample so interruptions preserve useful actual evidence.
        grouped={}
        for field in ("font_type","text","quality","distortion","size","source"):
            groups=defaultdict(list)
            for r in rows: groups[str(r[field])].append(r)
            grouped[field]={key:summarize(values) for key,values in groups.items()}
        write_json(output,{"label":label,"split":split,"revision":revision,"complete":len(rows)==len(cases),
                           "manifest_sha256":hashlib.sha256((DATA/"manifest.json").read_bytes()).hexdigest(),
                           "python":platform.python_version(),"platform":platform.platform(),
                           "cache":"cold Rasterizer and Renderer per case; OS file cache uncontrolled",
                           "summary":summarize(rows),"breakdowns":grouped,"rows":rows})
        print(json.dumps({"case":case["id"],"origin":case["origin"],"rank":row["rank"],"seconds":report["seconds"],"top":report["results"][0]["family"] if report["results"] else None}),flush=True)
    print(json.dumps(summarize(rows)),flush=True)


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("command",choices=("prepare","run"))
    parser.add_argument("--url",default="http://127.0.0.1:8766")
    parser.add_argument("--label",default="baseline");parser.add_argument("--split",choices=("dev","heldout","probes"),default="dev")
    parser.add_argument("--only",default="")
    args=parser.parse_args()
    if args.command=="prepare":prepare(args.url)
    else:run(args.label,args.split,args.only)

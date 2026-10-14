"""Independent Pillow reference generation, transformed before engine evaluation.

Run: python -m tests.benchmark_matching. Uses local fonts; no proprietary assets committed.
"""
import json
from pathlib import Path
import time
import cv2
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageFilter
from app.config import Config
from app.persistence import Store
from app.discovery import Catalog
from app.matching.models import Processing,MatchRequest
from app.matching.preprocess import preprocess
from app.matching.raster import Rasterizer
from app.matching.engine import match


def independent_image(face,text,tracking=0,stroke=0):
    font=ImageFont.truetype(face["path"],size=110,index=face["face_index"])
    canvas=Image.new("RGB",(2400,230),"white"); draw=ImageDraw.Draw(canvas)
    if tracking:
        x=25
        for c in text:
            draw.text((x,25),c,font=font,fill=(25,25,25),stroke_width=stroke,stroke_fill=(10,10,10))
            x+=font.getlength(c)+tracking
    else:
        draw.text((25,25),text,font=font,fill=(25,25,25),stroke_width=stroke,stroke_fill=(10,10,10))
    array=np.asarray(canvas); y,x=np.where(array.mean(axis=2)<200)
    return canvas.crop((max(0,x.min()-20),max(0,y.min()-20),min(canvas.width,x.max()+21),min(canvas.height,y.max()+21)))


def main():
    catalog=Catalog(Store(Config.load().data_dir));catalog.start();catalog.worker.join(60)
    fonts=catalog.snapshot()["fonts"]
    names=["Arial","Arial Narrow","Times New Roman","Georgia","Impact","Verdana","Tahoma","Calibri","Cambria","Segoe UI","Courier New","Comic Sans MS","Trebuchet MS","Bahnschrift"]
    # Include near-neighbor styles and duplicate-name but distinct binaries as real distractors.
    candidates=[f for f in fonts if any(f["full_name"]==n or f["family"]==n for n in names)]
    candidates=sorted(candidates,key=lambda f:(f["family"],f["weight"],f["style"],f["id"]))
    cases=[("Arial","Supreme!","scale"),("Times New Roman","No Good Gofers!","rotation"),
           ("Georgia","PLAYER 1","noise"),("Impact","SUPREME","outline"),("Verdana","SuPrEmE","contrast"),
           ("Courier New","LEVEL 11!","tracking"),("Trebuchet MS","BEEKEEPER","perspective"),
           ("Arial Narrow","Supreme","crop"),("Comic Sans MS","Wow!","scale"),("Bahnschrift","PLAYER 1","scale")]
    rasterizer=Rasterizer();rows=[];root=Path("test-results/ground-truth");root.mkdir(parents=True,exist_ok=True)
    rng=np.random.default_rng(42)
    for number,(family,text,transform) in enumerate(cases):
        matching=[f for f in candidates if (f["full_name"]==family or f["family"]==family) and f["weight"]==400 and not f["italic"]]
        if not matching: continue
        face=next((f for f in matching if f["full_name"]==family),matching[0])
        image=independent_image(face,text,tracking=3 if transform=="tracking" else 0,stroke=2 if transform=="outline" else 0)
        processing=Processing(deskew=transform=="rotation")
        if transform=="scale": image=image.resize((round(image.width*1.12),round(image.height*.88)),Image.Resampling.LANCZOS)
        elif transform=="rotation": image=image.rotate(3,resample=Image.Resampling.BICUBIC,expand=True,fillcolor="white")
        elif transform=="noise":
            a=np.asarray(image).astype(float)+rng.normal(0,15,(*np.asarray(image).shape[:2],1));image=Image.fromarray(np.clip(a,0,255).astype(np.uint8))
        elif transform=="contrast": image=Image.fromarray((np.asarray(image).astype(float)*.25+150).astype(np.uint8))
        elif transform=="perspective":
            w,h=image.size;src=np.float32([[0,0],[w-1,0],[w-1,h-1],[0,h-1]])
            dst=np.float32([[12,5],[w-16,0],[w-1,h-6],[0,h-1]])
            image=Image.fromarray(cv2.warpPerspective(np.asarray(image),cv2.getPerspectiveTransform(src,dst),(w,h),borderValue=(255,255,255)))
            processing=Processing(perspective=[(float(x/(w-1)),float(y/(h-1))) for x,y in dst])
        elif transform=="crop": image=image.crop((12,7,image.width-10,image.height-5))
        image.save(root/f"{number:02}-{transform}.png")
        processed=preprocess(image,processing)
        request=MatchRequest(process_id="benchmark",text=text,shortlist=min(60,max(10,len(candidates))))
        report=match(candidates,processed,request,rasterizer)
        ranks=[r["rank"] for r in report["results"] if r["font_id"]==face["id"]]
        rank=ranks[0] if ranks else None
        # Also report same family/style: different installed binaries can be visually indistinguishable.
        equivalent=[r["rank"] for r in report["results"] if r["family"]==face["family"] and r["style"]==face["style"]]
        row={"origin":face["full_name"],"origin_id":face["id"],"text":text,"transform":transform,"rank":rank,
             "same_family_style_rank":min(equivalent) if equivalent else None,"seconds":report["seconds"],
             "top": [{k:r[k] for k in ("family","style","score")} for r in report["results"][:5]]}
        rows.append(row);print(json.dumps(row),flush=True)
    summary={"candidate_faces":len(candidates),"cases":len(rows),"exact_id_top1":sum(r["rank"]==1 for r in rows)/len(rows),
             "exact_id_top5":sum(r["rank"] is not None and r["rank"]<=5 for r in rows)/len(rows),
             "exact_id_top10":sum(r["rank"] is not None and r["rank"]<=10 for r in rows)/len(rows),
             "total_seconds":sum(r["seconds"] for r in rows),"rows":rows}
    (root/"accuracy.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
    print(json.dumps({k:v for k,v in summary.items() if k!="rows"}),flush=True)


if __name__=="__main__":main()

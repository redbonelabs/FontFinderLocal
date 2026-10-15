"""Supplement strict reports with exact, text-specific raster equivalence.

No approximate similarity, family-name matching or score tolerance is permitted.
Two independently rendered Pillow sizes AND native shaped pixels/advance must
match byte-for-byte. Original baseline reports and manifest remain untouched.
"""
import argparse
import hashlib
import json

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from app.matching.raster import Rasterizer
from app.rendering import locate
from .benchmark_runner import DATA, RESULTS, write_json


def signature(face,text,coordinates,rasterizer):
    digest=hashlib.sha256()
    for size in (64,127):
        font=ImageFont.truetype(str(locate(face)),size=size,index=face["face_index"],layout_engine=ImageFont.Layout.BASIC)
        if face["axes"]:
            font.set_variation_by_axes([coordinates.get(a["tag"],a["default"]) for a in face["axes"]])
        bounds=font.getbbox(text)
        mask=Image.new("L",(bounds[2]-bounds[0]+4,bounds[3]-bounds[1]+4))
        ImageDraw.Draw(mask).text((2-bounds[0],2-bounds[1]),text,font=font,fill=255)
        digest.update(str((mask.size,bounds,font.getlength(text))).encode())
        digest.update(mask.tobytes())
    native=rasterizer.render(face,text,coordinates=coordinates)
    digest.update(str((native.mask.shape,native.advance,native.glyphs)).encode())
    digest.update(native.mask.tobytes())
    return digest.hexdigest()


def audit(labels):
    faces={f["id"]:f for f in json.loads((DATA/"catalog.json").read_text(encoding="utf-8"))}
    raster=Rasterizer();cache={};reports={}
    def key(font_id,text,coords):
        k=(font_id,text,tuple(sorted(coords.items())))
        if k not in cache:
            try:cache[k]=signature(faces[font_id],text,coords,raster)
            except Exception:cache[k]="unverifiable:"+font_id
        return cache[k]
    for label in labels:
        for split in ("dev","heldout"):
            path=RESULTS/f"{label}-{split}.json"
            if not path.exists():continue
            report=json.loads(path.read_text(encoding="utf-8"));rows=[]
            for row in report["rows"]:
                origin=key(row["origin_id"],row["text"],row["coordinates"])
                matches=[hit for hit in row["top10"] if hit["font_id"]==row["origin_id"] or
                         key(hit["font_id"],row["text"],hit["coordinates"])==origin]
                rank=min((hit["rank"] for hit in matches),default=None)
                rows.append({"id":row["id"],"strict_rank":row["rank"],"verified_equivalent_rank_in_top10":rank,
                             "equivalent_top10_ids":[h["font_id"] for h in matches],
                             "equivalent_top10_names":[h["family"]+" "+h["style"] for h in matches]})
            reports[f"{label}-{split}"]={"complete":report["complete"],"cases":len(rows),
                **{f"top{k}":sum(r["verified_equivalent_rank_in_top10"] is not None and r["verified_equivalent_rank_in_top10"]<=k for r in rows)/len(rows) for k in (1,5,10)},"rows":rows}
    output=RESULTS/("equivalence-"+"-".join(labels)+".json")
    if output.exists():raise SystemExit(f"Refusing to overwrite {output}")
    write_json(output,{"policy":"Exact Pillow BASIC pixels/bounds/advance at 64 and 127px plus exact HarfBuzz native pixels/advance/glyph count at 96px, using original exact text and reported coordinates. No tolerance. Only observed top10 candidates audited. Strict reports unchanged.","reports":reports})
    print(json.dumps({k:{a:b for a,b in v.items() if a!="rows"} for k,v in reports.items()}))


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("labels",nargs="+");args=parser.parse_args();audit(args.labels)

"""Coarse screening of every eligible face, then bounded shape refinement."""
import time
from threading import Event
from .metrics import coarse,detailed,segmentation
from .raster import missing_glyphs, RenderError


class Cancelled(Exception): pass


def match(faces, processed, request, rasterizer, cancel=None, progress=lambda **kw:None):
    cancel=cancel or Event(); start=time.monotonic()
    excluded={"missing_glyphs":0,"render_failed":0}
    coarse_results=[]
    references={"primary":processed.mask}
    if len(processed.alternatives)>1:
        references.update(processed.alternatives)
    for index,face in enumerate(faces):
        if cancel.is_set(): raise Cancelled()
        progress(stage="screening",completed=index,total=len(faces),message=f"Rendering {face['family']}")
        if missing_glyphs(face,request.text):
            excluded["missing_glyphs"]+=1; continue
        variants=[({},"Default")]
        if request.variable_instances and face["axes"]:
            instances=face["instances"]
            # Bounded but representative instance sampling; default always included.
            if len(instances)>6:
                indices=sorted({round(i*(len(instances)-1)/5) for i in range(6)})
                instances=[instances[i] for i in indices]
            variants += [(v["coordinates"],v["name"]) for v in instances]
        best=None
        for coords,label in variants:
            if cancel.is_set(): raise Cancelled()
            try:
                raster=rasterizer.render(face,request.text,tracking=request.tracking,coordinates=coords)
                score=min(coarse(ref,raster.mask) for ref in references.values())
                entry={"face":face,"coordinates":coords,"instance":label,"coarse":score}
                if best is None or score<best["coarse"]: best=entry
            except Exception:
                continue
        if best: coarse_results.append(best)
        else: excluded["render_failed"]+=1
    shortlist=sorted(coarse_results,key=lambda e:(e["coarse"],e["face"]["id"]))[:request.shortlist]
    results=[]
    for index,entry in enumerate(shortlist):
        if cancel.is_set(): raise Cancelled()
        face=entry["face"]
        progress(stage="refining",completed=index,total=len(shortlist),message=f"Comparing {face['family']}")
        span={"strict":1.5,"balanced":3.,"flexible":6.}[request.sensitivity]
        tracking_values=sorted({max(-12,min(24,request.tracking+delta)) for delta in (0,-span,span)})
        best=None
        for tracking in tracking_values:
            if cancel.is_set(): raise Cancelled()
            try:
                candidate=rasterizer.render(face,request.text,tracking=tracking,coordinates=entry["coordinates"])
                for mask_name,ref in references.items():
                    score,metrics,alignment=detailed(ref,candidate.mask,request.text,request.sensitivity,request.alignment)
                    if best is None or score>best["score"]:
                        best={"font_id":face["id"],"family":face["family"],"style":face["style"],"category":face["category"],
                              "score":score,"metrics":metrics,"tracking":tracking,"coordinates":entry["coordinates"],
                              "instance":entry["instance"],"mask":mask_name,"alignment":alignment}
            except Exception:
                continue
        if best: results.append(best)
    results.sort(key=lambda r:(-r["score"],r["font_id"]))
    for rank,result in enumerate(results,1):
        result["rank"]=rank; result["score"]=round(result["score"]*100,2)
    warnings=list(processed.warnings)
    if not results: warnings.append("No eligible fonts rendered this exact text. Check the text, font coverage, and catalog.")
    elif results[0]["score"] < 65: warnings.append("No strong geometric match. Check the crop, supplied text, processing, or whether the original font is available.")
    if len([c for c in request.text if not c.isspace()])<3:
        warnings.append("Very short text may not distinguish similar typefaces; compare more letters when possible.")
    if not segmentation(processed.mask,request.text):
        warnings.append("Character boundaries are uncertain or do not agree with the supplied sequence. Whole-word geometry was used; verify the text and crop one typeface/line at a time.")
    return {"text":request.text,"results":results,"warnings":warnings,"excluded":excluded,
            "eligible":len(coarse_results),"catalog_faces":len(faces),"seconds":round(time.monotonic()-start,3),
            "score_label":"Relative shape-match score — not identification probability"}

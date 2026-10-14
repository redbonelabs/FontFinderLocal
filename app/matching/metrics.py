"""Whole-word geometry, bounded alignment, and conservative character evidence."""
import cv2
import numpy as np
from .preprocess import ink_bounds


def tight(mask):
    x0,y0,x1,y1=ink_bounds(mask)
    return mask[y0:y1,x0:x1]


def resized(mask,width=256,height=64):
    return cv2.resize(tight(mask),(width,height),interpolation=cv2.INTER_AREA).astype(np.float32)/255


def coarse(reference,candidate):
    ref=resized(reference); cand=resized(candidate)
    projections=(np.mean(abs(ref.mean(axis=0)-cand.mean(axis=0)))+np.mean(abs(ref.mean(axis=1)-cand.mean(axis=1))))/2
    overlap=np.minimum(ref,cand).sum()/max(1,np.maximum(ref,cand).sum())
    density=abs(ref.mean()-cand.mean())
    ar=reference.shape[1]/reference.shape[0]; ac=candidate.shape[1]/candidate.shape[0]
    aspect=min(1,abs(np.log(max(.01,ac/ar))))
    return float(.50*(1-overlap)+.35*projections+.10*density+.05*aspect)


def canonical(reference):
    source=tight(reference)
    height=96
    width=int(np.clip(source.shape[1]/source.shape[0]*height,24,960))
    core=cv2.resize(source,(width,height),interpolation=cv2.INTER_AREA)
    return cv2.copyMakeBorder(core,12,12,18,18,cv2.BORDER_CONSTANT,value=0)


def align(candidate, target, sx=1, sy=1, dx=0, dy=0, alignment="center"):
    h,w=target.shape
    tw,th=w-36,h-24
    ch,cw=max(1,round(th*sy)),max(1,round(tw*sx))
    core=cv2.resize(tight(candidate),(cw,ch),interpolation=cv2.INTER_AREA)
    x=round((w-cw)/2+dx); y=round((h-ch)/2+dy)
    if alignment == "left": x=18+round(dx)
    if alignment == "right": x=w-18-cw+round(dx)
    out=np.zeros_like(target)
    x0,y0=max(0,x),max(0,y); x1,y1=min(w,x+cw),min(h,y+ch)
    if x1>x0 and y1>y0:
        out[y0:y1,x0:x1]=core[y0-y:y1-y,x0-x:x1-x]
    return out


def edge(mask):
    return cv2.Canny(mask,70,160)>0


def components(reference,candidate):
    ref=reference>127; cand=candidate>127
    intersection=np.count_nonzero(ref&cand); union=max(1,np.count_nonzero(ref|cand))
    iou=intersection/union
    er,ec=edge(reference),edge(candidate)
    dr=cv2.distanceTransform((~er).astype(np.uint8),cv2.DIST_L2,3)
    dc=cv2.distanceTransform((~ec).astype(np.uint8),cv2.DIST_L2,3)
    chamfer=(float(dr[ec].mean()) if ec.any() else 96)+(float(dc[er].mean()) if er.any() else 96)
    contour=float(np.exp(-chamfer/5))
    projections=1-float((np.mean(abs(ref.mean(axis=0)-cand.mean(axis=0)))+np.mean(abs(ref.mean(axis=1)-cand.mean(axis=1))))/2)
    # Local structural similarity (luminance, contrast and covariance), not pixel identity alone.
    a=reference.astype(np.float32)/255; b=candidate.astype(np.float32)/255
    ma=cv2.GaussianBlur(a,(7,7),1.5); mb=cv2.GaussianBlur(b,(7,7),1.5)
    va=cv2.GaussianBlur(a*a,(7,7),1.5)-ma*ma; vb=cv2.GaussianBlur(b*b,(7,7),1.5)-mb*mb
    cov=cv2.GaussianBlur(a*b,(7,7),1.5)-ma*mb
    ssim=float(np.mean(((2*ma*mb+.0001)*(2*cov+.0009))/((ma*ma+mb*mb+.0001)*(va+vb+.0009))))
    return {"overlap":float(iou),"contour":contour,"projection":projections,"structure":max(0,ssim)}


def segmentation(mask, text):
    # Only unambiguous separated Latin/numeric/punctuation glyphs. Joined scripts use whole words.
    chars=[c for c in text if not c.isspace()]
    if not chars or any(ord(c)>0x024f for c in chars): return None
    ink=(mask>127).any(axis=0)
    changes=np.diff(np.r_[False,ink,False].astype(int))
    spans=list(zip(np.flatnonzero(changes==1),np.flatnonzero(changes==-1)))
    if len(spans)!=len(chars) or any(b-a<2 for a,b in spans): return None
    return [(char,mask[:,a:b]) for char,(a,b) in zip(chars,spans)]


def character_score(reference,candidate,text):
    a,b=segmentation(reference,text),segmentation(candidate,text)
    if not a or not b: return None
    groups={}
    for (char,ref),(_,cand) in zip(a,b):
        r=resized(ref,32,48)>0.5; c=resized(cand,32,48)>0.5
        score=np.count_nonzero(r&c)/max(1,np.count_nonzero(r|c))
        groups.setdefault(char,[]).append(score)
    # Repeated glyphs have one character's total weight.
    return float(np.mean([np.mean(values) for values in groups.values()]))


def detailed(reference,candidate,text,sensitivity="balanced",alignment="center"):
    target=canonical(reference)
    span={"strict":.025,"balanced":.055,"flexible":.10}[sensitivity]
    native_ratio=(candidate.shape[1]/candidate.shape[0])/(reference.shape[1]/reference.shape[0])
    stretch={"strict":.10,"balanced":.25,"flexible":.40}[sensitivity]
    best=None
    # Search small residual scales/translation after ink-bound normalization.
    for sx,sy in [(1,1),(1-span,1),(1+span,1),(1,1-span),(1,1+span)]:
        sx=float(native_ratio*np.clip(sx/native_ratio,1-stretch,1+stretch))
        for dx,dy in [(0,0),(-2,0),(2,0),(0,-2),(0,2)]:
            fitted=align(candidate,target,sx,sy,dx,dy,alignment)
            r=target>127; c=fitted>127
            overlap=np.count_nonzero(r&c)/max(1,np.count_nonzero(r|c))
            if best is None or overlap>best[0]: best=(overlap,fitted,{"scale_x":sx,"scale_y":sy,"x":dx,"y":dy})
    metrics=components(target,best[1])
    score=.42*metrics["overlap"]+.30*metrics["contour"]+.16*metrics["structure"]+.12*metrics["projection"]
    char=character_score(reference,candidate,text)
    if char is not None:
        metrics["characters"]=char
        score=.92*score+.08*char
    ar=reference.shape[1]/reference.shape[0]; ac=candidate.shape[1]/candidate.shape[0]
    metrics["native_aspect_ratio"]=float(ac)
    metrics["reference_aspect_ratio"]=float(ar)
    # Width differences are informative but never a hard exclusion.
    penalty=min(.04,abs(np.log(max(.01,ac/ar)))*.025)
    return max(0,score-penalty),metrics,best[2]

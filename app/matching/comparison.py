import cv2
import numpy as np
from PIL import Image,ImageDraw
from .metrics import canonical,align,edge,tight
from .preprocess import ink_bounds


def selected_reference(processed,result):
    return processed.alternatives.get(result["mask"],processed.mask)


def candidate_image(raster):
    # Alpha PNG retains real aspect ratio for the result preview.
    rgba=np.zeros((*raster.mask.shape,4),np.uint8)
    rgba[:,:,:3]=(219,241,196); rgba[:,:,3]=raster.mask
    return Image.fromarray(rgba)


def comparison_image(processed,result,raster,options):
    reference=selected_reference(processed,result)
    target=canonical(reference)
    h,w=target.shape
    auto=result["alignment"]
    candidate=align(raster.mask,target,auto["scale_x"]*options.scale*options.scale_x,
                    auto["scale_y"]*options.scale*options.scale_y,auto["x"]+options.x,auto["y"]+options.y)
    if options.rotation:
        matrix=cv2.getRotationMatrix2D((w/2,h/2),options.rotation,1)
        candidate=cv2.warpAffine(candidate,matrix,(w,h))
    if options.reference=="original":
        x0,y0,x1,y1=ink_bounds(reference)
        original=processed.image[y0:y1,x0:x1]
        background=np.full((h,w,3),245,np.uint8)
        background[12:h-12,18:w-18]=cv2.resize(original,(w-36,h-24))
    else:
        background=np.full((h,w,3),(22,27,23),np.uint8)
        background[target>127]=(230,234,226)
    ref=target>127; cand=candidate>127
    if options.mode=="side":
        other=np.full_like(background,(22,27,23)); other[cand]=(193,248,120)
        output=np.concatenate([background,np.full((h,12,3),60,np.uint8),other],axis=1)
    elif options.mode=="difference":
        output=np.full_like(background,(22,27,23)); output[ref&cand]=(214,231,196)
        output[ref&~cand]=(248,127,130); output[cand&~ref]=(83,207,224)
    else:
        mask=edge(candidate).astype(float) if options.mode=="outline" else candidate.astype(float)/255
        opacity=(mask*options.opacity)[...,None]
        output=(background*(1-opacity)+np.array([40,180,220])*opacity).astype(np.uint8)
    # Export includes exact text elsewhere in response; image visibly labels its purpose.
    canvas=Image.new("RGB",(output.shape[1],output.shape[0]+26),(22,27,23))
    canvas.paste(Image.fromarray(output),(0,26))
    ImageDraw.Draw(canvas).text((8,6),"Visual comparison only - relative shape match, not proof of identity",fill=(190,205,183))
    return canvas

from fastapi import APIRouter,Request,HTTPException
from fastapi.responses import Response
from PIL import Image
from .images import MAX_UPLOAD,ImageError,png_bytes
from .models import ProcessRequest,MatchRequest,CompareRequest
from .comparison import comparison_image,candidate_image
from .raster import RenderError


def router(service):
    routes=APIRouter(prefix="/api/matching")

    def guarded(action):
        try: return action()
        except (ImageError,RenderError) as exc: raise HTTPException(422,str(exc)) from exc

    @routes.post("/images")
    async def upload(request:Request):
        data=bytearray()
        async for chunk in request.stream():
            if len(data)+len(chunk)>MAX_UPLOAD: raise HTTPException(413,"Image exceeds the 20 MiB upload limit.")
            data.extend(chunk)
        # Decoding stays off the event loop used by the existing browser API.
        from starlette.concurrency import run_in_threadpool
        return await run_in_threadpool(lambda:guarded(lambda:service.images.add(bytes(data))))

    @routes.get("/images/{image_id}")
    def original(image_id:str):
        return Response(png_bytes(guarded(lambda:service.images.get(image_id))),media_type="image/png")

    @routes.delete("/images/{image_id}")
    def remove(image_id:str):
        service.images.remove(image_id); return {"removed":True}

    @routes.post("/process")
    def process(body:ProcessRequest):
        key,processed=guarded(lambda:service.process(body))
        return {"id":key,"warnings":processed.warnings,"angle":processed.angle,"width":processed.mask.shape[1],
                "height":processed.mask.shape[0],"alternatives":list(processed.alternatives),"bounds":processed.bounds}

    @routes.get("/processed/{process_id}/{kind}")
    def processed_image(process_id:str,kind:str):
        processed=guarded(lambda:service.get_process(process_id))
        if kind=="mask": image=Image.fromarray(255-processed.mask)
        elif kind=="corrected": image=Image.fromarray(processed.corrected)
        elif kind=="reference": image=Image.fromarray(processed.image)
        else: raise HTTPException(404,"Unknown image representation.")
        return Response(png_bytes(image),media_type="image/png")

    @routes.post("/jobs")
    def start(body:MatchRequest): return guarded(lambda:service.start(body))

    @routes.get("/jobs/{job_id}")
    def status(job_id:str): return guarded(lambda:service.status(job_id))

    @routes.post("/jobs/{job_id}/cancel")
    def cancel(job_id:str): return guarded(lambda:service.cancel(job_id))

    @routes.get("/jobs/{job_id}/preview/{font_id}")
    def preview(job_id:str,font_id:str):
        def make():
            job,result,face=service.result(job_id,font_id)
            raster=service.rasterizer.render(face,job.request.text,tracking=result["tracking"],coordinates=result["coordinates"])
            return png_bytes(candidate_image(raster))
        return Response(guarded(make),media_type="image/png")

    @routes.post("/jobs/{job_id}/compare")
    def compare(job_id:str,body:CompareRequest):
        def make():
            job,result,face=service.result(job_id,body.font_id)
            tracking=result["tracking"] if body.alignment.tracking is None else body.alignment.tracking
            raster=service.rasterizer.render(face,job.request.text,tracking=tracking,coordinates=result["coordinates"])
            return png_bytes(comparison_image(job.processed,result,raster,body.alignment))
        return Response(guarded(make),media_type="image/png",headers={"Content-Disposition":"inline; filename=font-comparison.png"})

    return routes

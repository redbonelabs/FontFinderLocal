from io import BytesIO
import time
import numpy as np
import pytest
from PIL import Image
from pydantic import ValidationError
from app.matching.images import decode,ImageError,png_bytes
from app.matching.models import Processing,MatchRequest,Alignment,validate_text
from app.matching.preprocess import preprocess
from app.matching.raster import Rasterizer,RenderError,missing_glyphs
from app.matching.metrics import character_score
from app.matching.engine import match,Cancelled
from app.matching.comparison import comparison_image


def reference(client,text="A S A"):
    face=client.app.state.catalog.snapshot()["fonts"][0]
    raster=client.app.state.matching.rasterizer.render(face,text)
    image=Image.fromarray(255-raster.mask).convert("RGBA")
    canvas=Image.new("RGBA",(image.width+40,image.height+40),"white"); canvas.paste(image,(20,20))
    return face,canvas


def test_text_is_authoritative():
    text='  SuPrEmE, No Good Gofers!  EE  '
    assert MatchRequest(process_id="x",text=text).text==text
    assert validate_text("e\u0301") == "e\u0301"
    for bad in ["", "   ", "\u200d", "A\nB", "A\tB"]:
        with pytest.raises((ValueError,ValidationError)): MatchRequest(process_id="x",text=bad)


def test_decode_validates_content_and_limits():
    for fmt in ("PNG","JPEG","BMP","TIFF","WEBP"):
        output=BytesIO(); Image.new("RGB",(120,50),"white").save(output,format=fmt)
        image,_=decode(output.getvalue()); assert image.size==(120,50)
    with pytest.raises(ImageError): decode(b"not a png")
    with pytest.raises(ImageError): decode(b"x"*(20*1024*1024+1))
    output=BytesIO(); Image.new("1",(10001,2)).save(output,format="PNG")
    with pytest.raises(ImageError): decode(output.getvalue())


def test_exif_orientation():
    image=Image.new("RGB",(80,30),"white"); exif=image.getexif(); exif[274]=6
    out=BytesIO(); image.save(out,format="JPEG",exif=exif)
    result,_=decode(out.getvalue()); assert result.size==(30,80)


def test_render_exact_missing_and_spacing(client):
    face,_=reference(client)
    renderer=client.app.state.matching.rasterizer
    a=renderer.render(face,"A S A"); b=renderer.render(face,"A  S A"); c=renderer.render(face,"A S A",tracking=5)
    assert a.text=="A S A" and b.advance>a.advance and c.mask.shape[1]>a.mask.shape[1]
    assert missing_glyphs(face,"a")==["a"]
    with pytest.raises(RenderError): renderer.render(face,"a S A")


def test_crop_polarity_and_processing(client):
    _,image=reference(client)
    processed=preprocess(image,Processing())
    assert processed.mask.max()==255 and processed.mask.min()==0
    inverted=Image.fromarray(255-np.array(image.convert("RGB")))
    other=preprocess(inverted,Processing(polarity="light"))
    assert np.array_equal(processed.mask,other.mask)
    cropped=preprocess(image,Processing(crop=(.1,0,.6,1)))
    assert cropped.mask.shape[1]<processed.mask.shape[1]
    with pytest.raises(ImageError): preprocess(Image.new("RGB",(80,30),"white"),Processing())
    with pytest.raises(ValidationError): Processing(crop=(.9,0,.5,1))
    with pytest.raises(ImageError): preprocess(image,Processing(perspective=[(0,0),(1,1),(1,0),(0,1)]))


def test_alpha_and_color_processing():
    image=Image.new("RGBA",(80,50),(0,0,0,0)); array=np.array(image)
    array[10:40,20:60]=(220,30,40,255)
    for options in [Processing(method="alpha"),Processing(method="color",foreground="#dc1e28")]:
        result=preprocess(Image.fromarray(array),options)
        assert result.mask.shape==(30,40)


def test_match_metrics_and_cancellation(client):
    face,image=reference(client)
    processed=preprocess(image,Processing())
    request=MatchRequest(process_id="test",text="A S A",shortlist=10)
    result=match([face],processed,request,client.app.state.matching.rasterizer)
    assert result["text"]==request.text and result["results"][0]["score"]>90
    assert "contour" in result["results"][0]["metrics"]
    from threading import Event
    event=Event();event.set()
    with pytest.raises(Cancelled): match([face],processed,request,client.app.state.matching.rasterizer,event)
    raster=client.app.state.matching.rasterizer.render(face,request.text)
    for mode in ("side","overlay","difference","outline"):
        output=comparison_image(processed,result["results"][0],raster,Alignment(mode=mode,x=3,rotation=2,scale_x=.95))
        assert output.width>50 and output.height>40


def test_job_api_and_shared_favorites(client):
    face,image=reference(client)
    assert client.post("/api/matching/images",content=b"invalid").status_code==422
    assert client.post("/api/matching/images",content=png_bytes(image),headers={"Origin":"https://evil.example"}).status_code==403
    uploaded=client.post("/api/matching/images",content=png_bytes(image)).json()
    assert client.get(f"/api/matching/images/{uploaded['id']}").headers["content-type"]=="image/png"
    assert client.get("/api/matching/images/..%5Csecret").status_code==422
    processed=client.post("/api/matching/process",json={"image_id":uploaded["id"]}).json()
    assert client.get(f"/api/matching/processed/{processed['id']}/mask").status_code==200
    assert client.post("/api/matching/jobs",json={"process_id":processed["id"],"text":"  "}).status_code==422
    response=client.post("/api/matching/jobs",json={"process_id":processed["id"],"text":"A S A","shortlist":10})
    assert response.status_code==200,response.text
    key=response.json()["id"]
    client.app.state.matching.get_job(key).thread.join(15)
    status=client.get(f"/api/matching/jobs/{key}").json()
    assert status["status"]=="completed",status
    font_id=status["results"][0]["font_id"]
    assert client.get(f"/api/matching/jobs/{key}/preview/{font_id}").status_code==200
    for mode in ("side","overlay","difference","outline"):
        response=client.post(f"/api/matching/jobs/{key}/compare",json={"font_id":font_id,"alignment":{"mode":mode}})
        assert response.status_code==200 and response.content.startswith(b"\x89PNG")
    aligned=client.post(f"/api/matching/jobs/{key}/auto-align",json={"font_id":font_id,"alignment":{"tracking":4}})
    assert aligned.status_code==200 and aligned.json()["tracking"]==4
    exported=client.get(f"/api/matching/jobs/{key}/comparison.png",params={"font_id":font_id,"alignment":'{"mode":"outline","x":2}'})
    assert exported.status_code==200 and exported.content.startswith(b"\x89PNG")
    assert exported.headers["content-disposition"]=='attachment; filename="FontFinderLocal-comparison.png"'
    assert client.get(f"/api/matching/jobs/{key}/comparison.png",params={"font_id":font_id,"alignment":'{"scale":99}'}).status_code==422
    assert client.post(f"/api/matching/jobs/{key}/compare",json={"font_id":"arbitrary"}).status_code==422
    client.put(f"/api/favorites/{font_id}",json={"enabled":True})
    assert font_id in client.get("/api/bootstrap").json()["favorites"]
    # Same uploaded image, different authoritative text produces a separate immutable job.
    changed=client.post("/api/matching/jobs",json={"process_id":processed["id"],"text":"S A"}).json()
    client.app.state.matching.get_job(changed["id"]).thread.join(15)
    assert client.get(f"/api/matching/jobs/{key}").json()["text"]=="A S A"
    assert client.get(f"/api/matching/jobs/{changed['id']}").json()["text"]=="S A"
    assert client.delete(f"/api/matching/images/{uploaded['id']}").status_code==200
    assert client.get(f"/api/matching/images/{uploaded['id']}").status_code==422


def test_real_job_cancel_and_single_worker(client,monkeypatch):
    _,image=reference(client)
    service=client.app.state.matching
    uploaded=service.images.add(png_bytes(image))
    from app.matching.models import ProcessRequest
    key,_=service.process(ProcessRequest(image_id=uploaded["id"]))
    def slow(*args,**kwargs):
        cancel=args[4]
        while not cancel.wait(.01): pass
        raise Cancelled()
    monkeypatch.setattr("app.matching.service.match",slow)
    job=service.start(MatchRequest(process_id=key,text="A"))
    with pytest.raises(ImageError): service.start(MatchRequest(process_id=key,text="S"))
    service.cancel(job["id"]);service.get_job(job["id"]).thread.join(3)
    assert service.status(job["id"])["status"]=="cancelled"


def test_transparent_white_letters_and_counters_survive():
    image=np.zeros((90,120,4),np.uint8)
    image[15:75,20:100]=255
    image[30:60,40:80]=0
    result=preprocess(Image.fromarray(image),Processing(method="alpha",rotation=2))
    assert result.mask.max()==255
    # The transparent counter remains empty and visible in the corrected original.
    assert result.mask[result.mask.shape[0]//2,result.mask.shape[1]//2]==0
    assert np.ptp(result.image)>150


def test_extreme_width_distortion_cannot_force_a_match(client):
    from app.matching.metrics import detailed
    _,image=reference(client)
    reference_mask=preprocess(image,Processing()).mask
    import cv2
    narrow=cv2.resize(reference_mask,(max(4,reference_mask.shape[1]//4),reference_mask.shape[0]))
    normal=detailed(reference_mask,reference_mask,"A S A")[0]
    distorted=detailed(reference_mask,narrow,"A S A")[0]
    assert normal>.95 and distorted<normal-.2


def test_expired_uploads_and_active_upload_refresh(tmp_path,monkeypatch):
    from app.matching.images import ImageStore,TTL
    store=ImageStore(tmp_path)
    item=store.add(png_bytes(Image.new("RGB",(20,20),"white")))
    now=time.time()
    import os
    os.utime(store.root/f"{item['id']}.upload",(now-TTL-5,now-TTL-5))
    # An active in-memory item is kept even if its source file has an old mtime.
    assert store.get(item["id"]).size==(20,20)
    store.items[item["id"]]["touched"]=now-TTL-5
    store.cleanup()
    with pytest.raises(ImageError):store.get(item["id"])
    assert not (store.root/f"{item['id']}.upload").exists()


def test_ranking_is_repeatable_and_repeated_glyphs_have_balanced_weight(client):
    face,image=reference(client)
    request=MatchRequest(process_id="x",text="A S A",shortlist=10)
    processed=preprocess(image,Processing())
    first=match([face],processed,request,client.app.state.matching.rasterizer)
    second=match([face],processed,request,client.app.state.matching.rasterizer)
    assert first["results"]==second["results"]
    assert character_score(processed.mask,processed.mask,"A S A")==1


def test_automatic_spacing_penalty_respects_user_tracking(client):
    face,_=reference(client)
    raster=client.app.state.matching.rasterizer
    rendered=raster.render(face,"A S A",tracking=3)
    image=Image.fromarray(255-rendered.mask).convert("RGB")
    canvas=Image.new("RGB",(image.width+40,image.height+40),"white");canvas.paste(image,(20,20))
    processed=preprocess(canvas,Processing())
    result=match([face],processed,MatchRequest(process_id="x",text="A S A",tracking=3),raster)
    hit=result["results"][0]
    assert hit["tracking"]==3 and hit["metrics"]["spacing_penalty"]==0


@pytest.mark.parametrize("anchor",["left","right"])
def test_comparison_preserves_scored_alignment_anchor(client,anchor):
    from app.matching.metrics import detailed,align,canonical
    face,image=reference(client)
    processed=preprocess(image,Processing())
    raster=client.app.state.matching.rasterizer.render(face,"A S A",tracking=12)
    _,_,fitted=detailed(processed.mask,raster.mask,"A S A","strict",anchor)
    assert fitted["anchor"]==anchor
    result={"mask":"primary","alignment":fitted}
    output=np.asarray(comparison_image(processed,result,raster,Alignment(mode="difference")))
    target=canonical(processed.mask)
    expected=align(raster.mask,target,fitted["scale_x"],fitted["scale_y"],fitted["x"],fitted["y"],anchor)>127
    x=(output.shape[1]-target.shape[1])//2
    pixels=output[26:,x:x+target.shape[1]]
    # Shared ink and cyan both contain candidate ink; red is reference only.
    actual=np.all(pixels==[214,231,196],axis=2)|np.all(pixels==[83,207,224],axis=2)
    assert np.array_equal(actual,expected)

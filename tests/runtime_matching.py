"""Live end-to-end API verification against the complete local catalog."""
import json
from pathlib import Path
import time
from urllib.request import Request,urlopen
from PIL import Image
from io import BytesIO
from app.config import Config


def main():
    connection=json.loads((Config.load().data_dir/"server.json").read_text())
    base=f"http://127.0.0.1:{connection['port']}"
    with urlopen(base+"/api/bootstrap") as response: token=json.load(response)["token"]
    def request(path,body=None,raw=False,binary=False):
        data=body if raw else None if body is None else json.dumps(body).encode()
        req=Request(base+"/api/matching"+path,data=data,headers={"Content-Type":"application/octet-stream" if raw else "application/json","X-FontFinder-Token":token})
        with urlopen(req,timeout=60) as response:
            return response.read() if binary else json.load(response)
    root=Path("test-results/ground-truth")
    image=request("/images",(root/"00-scale.png").read_bytes(),raw=True)
    processed=request("/process",{"image_id":image["id"]})
    text="  Supreme!  "
    job=request("/jobs",{"process_id":processed["id"],"text":text})
    deadline=time.monotonic()+180
    while time.monotonic()<deadline:
        status=request(f"/jobs/{job['id']}")
        if status["status"] in ("failed","cancelled","completed"): break
        time.sleep(.4)
    assert status["status"]=="completed",status
    assert status["text"]==text and status["results"]
    font=status["results"][0]["font_id"]
    preview=request(f"/jobs/{job['id']}/preview/{font}",binary=True)
    assert Image.open(BytesIO(preview)).width>0
    for mode in ("side","overlay","difference","outline"):
        data=request(f"/jobs/{job['id']}/compare",{"font_id":font,"alignment":{"mode":mode,"x":3,"y":-2,"scale":1.02,"scale_x":.98,"scale_y":1.03,"rotation":1,"opacity":.55,"tracking":2}},binary=True)
        output=Image.open(BytesIO(data));assert output.width>=620
        Path(f"test-results/comparison-{mode}.png").write_bytes(data)
    auto=request(f"/jobs/{job['id']}/auto-align",{"font_id":font,"alignment":{"tracking":2}})
    assert auto["tracking"]==2
    cancelled=request("/jobs",{"process_id":processed["id"],"text":"Supreme!"})
    request(f"/jobs/{cancelled['id']}/cancel",{})
    for _ in range(60):
        stopped=request(f"/jobs/{cancelled['id']}")
        if stopped["status"]=="cancelled": break
        time.sleep(.1)
    assert stopped["status"]=="cancelled"
    summary={"text":text,"seconds":status["seconds"],"faces":status["catalog_faces"],"eligible":status["eligible"],
             "excluded":status["excluded"],"top5":status["results"][:5],"warnings":status["warnings"],
             "comparison_modes":"all four returned valid PNGs","cancelled":True}
    Path("test-results/runtime-matching.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
    print(json.dumps({k:v for k,v in summary.items() if k!="top5"},indent=2))


if __name__=="__main__":main()

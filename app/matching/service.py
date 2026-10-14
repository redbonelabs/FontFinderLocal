from collections import OrderedDict
from dataclasses import dataclass
import logging
import secrets
import threading
import time
from .images import ImageStore,ImageError,TTL
from .preprocess import preprocess
from .raster import Rasterizer
from .engine import match,Cancelled

log=logging.getLogger(__name__)


@dataclass
class Job:
    id:str
    request:object
    processed:object
    cancel:threading.Event
    state:dict
    created:float
    revision:int
    thread:object=None


class MatchingService:
    def __init__(self,config,catalog,renderer):
        self.catalog=catalog
        self.images=ImageStore(config.data_dir)
        self.rasterizer=Rasterizer(renderer)
        self.processes=OrderedDict()
        self.jobs=OrderedDict()
        self.lock=threading.RLock()
        self.closed=threading.Event()
        self.janitor=None

    def start_cleanup(self):
        def run():
            while not self.closed.wait(60):
                try: self.cleanup()
                except Exception: log.exception("Matching temporary cleanup failed")
        self.janitor=threading.Thread(target=run,name="matching-cleanup",daemon=True); self.janitor.start()

    def cleanup(self):
        self.images.cleanup()
        with self.lock:
            now=time.time()
            for key,(created,_) in list(self.processes.items()):
                if now-created>TTL: self.processes.pop(key)
            for key,job in list(self.jobs.items()):
                if now-job.created>TTL and job.state["status"] not in ("queued","running","cancelling"):
                    self.jobs.pop(key)

    def process(self,request):
        self.cleanup()
        image=self.images.get(request.image_id)
        processed=preprocess(image,request.processing)
        key=secrets.token_hex(16)
        with self.lock:
            while len(self.processes)>=6: self.processes.popitem(last=False)
            self.processes[key]=(time.time(),processed)
        return key,processed

    def get_process(self,key):
        with self.lock:
            if key not in self.processes: raise ImageError("Processed image expired. Process the reference again.")
            return self.processes[key][1]

    def start(self,request):
        with self.lock:
            if any(j.state["status"] in ("running","queued","cancelling") for j in self.jobs.values()):
                raise ImageError("A matching job is still running or cancelling. Wait for it to finish.")
            processed=self.get_process(request.process_id)
            snapshot=self.catalog.snapshot()
            if not snapshot["fonts"]: raise ImageError("Font catalog is empty or still loading. Wait for discovery or add a font folder.")
            key=secrets.token_hex(16)
            state={"id":key,"status":"queued","stage":"queued","completed":0,"total":len(snapshot["fonts"]),"text":request.text,
                   "message":"Preparing local font search","catalog_revision":snapshot["revision"]}
            job=Job(key,request,processed,threading.Event(),state,time.time(),snapshot["revision"])
            self.jobs[key]=job
            while len(self.jobs)>6: self.jobs.popitem(last=False)
            job.thread=threading.Thread(target=self._run,args=(job,snapshot["fonts"]),name="font-matching",daemon=True)
            job.thread.start()
            return dict(state)

    def _run(self,job,faces):
        def progress(**values):
            with self.lock: job.state.update(values)
        try:
            progress(status="running")
            output=match(faces,job.processed,job.request,self.rasterizer,job.cancel,progress)
            if job.cancel.is_set(): raise Cancelled()
            with self.lock:
                job.state.update(output,status="completed",stage="complete",completed=len(faces),total=len(faces),message="Local search complete")
        except Cancelled:
            progress(status="cancelled",message="Search cancelled; no rankings published.")
        except Exception:
            log.exception("Matching job failed")
            progress(status="failed",message="Matching failed. Check image processing or shorten the text, then retry. See the local log for details.")

    def get_job(self,key):
        with self.lock:
            if key not in self.jobs: raise ImageError("Matching job expired. Run a new search.")
            return self.jobs[key]

    def status(self,key):
        with self.lock:
            job=self.get_job(key)
            return {**job.state,"catalog_changed":self.catalog.revision!=job.revision}

    def cancel(self,key):
        with self.lock:
            job=self.get_job(key)
            if job.state["status"] in ("queued","running"):
                job.cancel.set(); job.state.update(status="cancelling",message="Cancelling after the current font operation…")
            return dict(job.state)

    def result(self,key,font_id):
        job=self.get_job(key)
        if job.state["status"]!="completed": raise ImageError("This search has no completed results.")
        result=next((r for r in job.state["results"] if r["font_id"]==font_id),None)
        face=self.catalog.get(font_id)
        if not result or not face: raise ImageError("This font is unavailable in this search or the current catalog. Rescan and search again.")
        return job,result,face

    def close(self):
        self.closed.set()
        for job in list(self.jobs.values()): job.cancel.set()
        for job in list(self.jobs.values()):
            if job.thread: job.thread.join(timeout=5)
        if self.janitor: self.janitor.join(timeout=2)

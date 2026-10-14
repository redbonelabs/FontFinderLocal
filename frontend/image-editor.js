// All editing is a reversible set of parameters; the uploaded source is untouched.
export class ImageEditor {
  constructor(canvas, changed, colorPicked) {
    this.canvas=canvas; this.changed=changed; this.colorPicked=colorPicked;
    this.image=null; this.crop=[0,0,1,1]; this.turns=0; this.corners=null;
    this.zoom=1; this.pan=[0,0]; this.mode='crop'; this.drag=null;
    new ResizeObserver(()=>this.draw()).observe(canvas);
    canvas.addEventListener('pointerdown',e=>this.down(e));
    canvas.addEventListener('pointermove',e=>this.move(e));
    canvas.addEventListener('pointerup',()=>this.up());
    canvas.addEventListener('pointercancel',()=>this.up());
    canvas.addEventListener('wheel',e=>{ if(!this.image)return; e.preventDefault(); this.zoom=Math.min(5,Math.max(1,this.zoom*(e.deltaY<0?1.1:.9))); this.draw(); document.getElementById('image-zoom').value=this.zoom; },{passive:false});
  }
  async load(url) {
    const image=new Image(); image.src=url; await image.decode(); this.image=image; this.restore(false);
  }
  restore(notify=true) { this.turns=0; this.crop=[0,0,1,1]; this.corners=null; this.mode='crop'; this.zoom=1; this.pan=[0,0]; this.prepare(); if(notify)this.changed(); }
  prepare() {
    if(!this.image)return;
    this.source=document.createElement('canvas'); const odd=this.turns%2;
    this.source.width=odd?this.image.height:this.image.width; this.source.height=odd?this.image.width:this.image.height;
    const c=this.source.getContext('2d'); c.translate(this.source.width/2,this.source.height/2); c.rotate(this.turns*Math.PI/2);
    c.drawImage(this.image,-this.image.width/2,-this.image.height/2); this.draw();
  }
  rotate() { this.turns=(this.turns+1)%4; this.crop=[0,0,1,1]; this.corners=null; this.mode='crop'; this.pan=[0,0]; this.prepare(); this.changed(); }
  resetCrop() { this.crop=[0,0,1,1]; this.corners=null; this.mode='crop'; this.draw(); this.changed(); }
  setMode(mode) {
    this.mode=mode;
    if(mode==='perspective'&&!this.corners) { const [x,y,w,h]=this.crop; this.corners=[[x,y],[x+w,y],[x+w,y+h],[x,y+h]]; this.changed(); }
    this.draw();
  }
  point(e) { const rect=this.canvas.getBoundingClientRect(); return [(e.clientX-rect.left-this.ox)/(this.scale*this.source.width),(e.clientY-rect.top-this.oy)/(this.scale*this.source.height)].map(v=>Math.min(1,Math.max(0,v))); }
  down(e) {
    if(!this.source)return;
    this.canvas.setPointerCapture(e.pointerId);
    const point=this.point(e);
    if(this.mode==='color') {
      const x=Math.min(this.source.width-1,Math.floor(point[0]*this.source.width)),y=Math.min(this.source.height-1,Math.floor(point[1]*this.source.height));
      const pixel=this.source.getContext('2d').getImageData(x,y,1,1).data;
      this.colorPicked('#'+[...pixel].slice(0,3).map(v=>v.toString(16).padStart(2,'0')).join('')); return;
    }
    if(this.mode==='pan') this.drag={start:[e.clientX,e.clientY],pan:[...this.pan]};
    else if(this.mode==='perspective') {
      const distances=this.corners.map(p=>Math.hypot((p[0]-point[0])*this.source.width,(p[1]-point[1])*this.source.height));
      this.drag={corner:distances.indexOf(Math.min(...distances))};
    } else { this.corners=null; this.drag={point}; }
  }
  move(e) {
    if(!this.drag)return;
    if(this.mode==='pan') this.pan=[this.drag.pan[0]+e.clientX-this.drag.start[0],this.drag.pan[1]+e.clientY-this.drag.start[1]];
    else { const point=this.point(e);
      if(this.mode==='perspective') this.corners[this.drag.corner]=point;
      else { const start=this.drag.point; this.crop=[Math.min(start[0],point[0]),Math.min(start[1],point[1]),Math.abs(point[0]-start[0]),Math.abs(point[1]-start[1])]; }
    } this.draw();
  }
  up() { if(!this.drag)return; this.drag=null; if(this.crop[2]<.005||this.crop[3]<.005)this.crop=[0,0,1,1]; if(this.mode!=='pan')this.changed(); this.draw(); }
  draw() {
    if(!this.source)return;
    const width=this.canvas.clientWidth,height=this.canvas.clientHeight,dpr=devicePixelRatio||1;
    if(!width||!height)return;
    this.canvas.width=Math.round(width*dpr); this.canvas.height=Math.round(height*dpr);
    const c=this.canvas.getContext('2d'); c.scale(dpr,dpr);
    this.scale=Math.min((width-24)/this.source.width,(height-24)/this.source.height)*this.zoom;
    this.ox=(width-this.source.width*this.scale)/2+this.pan[0]; this.oy=(height-this.source.height*this.scale)/2+this.pan[1];
    c.drawImage(this.source,this.ox,this.oy,this.source.width*this.scale,this.source.height*this.scale);
    const [x,y,w,h]=this.crop; const points=this.corners||[[x,y],[x+w,y],[x+w,y+h],[x,y+h]];
    const screen=points.map(([a,b])=>[this.ox+a*this.source.width*this.scale,this.oy+b*this.source.height*this.scale]);
    c.strokeStyle='#c1f878'; c.fillStyle='#c1f878'; c.lineWidth=2; c.beginPath(); screen.forEach(([a,b],i)=>i?c.lineTo(a,b):c.moveTo(a,b));c.closePath();c.stroke();
    if(this.corners) screen.forEach(([a,b],i)=>{c.beginPath();c.arc(a,b,6,0,Math.PI*2);c.fill();c.fillText(String(i+1),a+10,b+4);});
  }
}

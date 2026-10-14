import {ImageEditor} from './image-editor.js';

export async function initMatching(host, bridge) {
  host.innerHTML=await (await fetch('/static/matching.html')).text();
  const $=id=>document.getElementById(id);
  const el=(tag,cls,text)=>{const n=document.createElement(tag);if(cls)n.className=cls;if(text!==undefined)n.textContent=text;return n;};
  let image=null, processed=null, result=null, job=null, version=0, sourceVersion=0, processingTimer, pollTimer;
  let processingPromise=null, processingVersion=-1, limit=20, selected=null, comparisonURL=null, comparisonTimer, comparisonVersion=0;
  let active=false;
  const notes=(id,messages)=>$(id).replaceChildren(...messages.map(message=>el('p','',message)));
  const error=message=>{ $('match-status').textContent=message; bridge.toast(message,true); };
  async function request(path,method='GET',body,raw=false,binary=false) {
    const response=await fetch(`/api/matching${path}`,{method,headers:{'X-FontFinder-Token':bridge.state.token,'Content-Type':raw?'application/octet-stream':'application/json'},...(body===undefined?{}:{body:raw?body:JSON.stringify(body)})});
    if(!response.ok){let message=`Local operation failed (${response.status}).`;try{const d=(await response.json()).detail;message=typeof d==='string'?d:Array.isArray(d)?d.map(x=>x.msg).join(' '):message;}catch{}const failure=new Error(message);failure.status=response.status;throw failure;}
    return binary?response.blob():response.json();
  }
  function validText(){const text=$('match-text').value;return /[^\p{C}\s]/u.test(text)&&!/[\n\r\t]/.test(text);}
  function buttons(){
    $('find-fonts').disabled=!image||!validText()||active;
    $('process-now').disabled=!image;
    $('cancel-match').hidden=!active;
    $('match-validation').textContent=!image?'Upload a reference image to begin.':!validText()?'Enter at least one visible character from one line, using its exact case and punctuation.':'Text is used exactly as entered. Crop one line in one typeface.';
  }
  function invalidate(reprocess=true){
    version++; result=null; selected=null; $('match-compare-dialog').close(); renderResults();
    if(job&&active)request(`/jobs/${job}/cancel`,'POST').catch(()=>{});
    if(reprocess){sourceVersion++;processed=null;$('processed-mask').hidden=true;$('processed-corrected').hidden=true;clearTimeout(processingTimer);if(image){$('processing-notes').textContent='Preview needs updating for the current reference.';processingTimer=setTimeout(()=>prepare().catch(e=>error(e.message)),450);}}
    $('results-caption').textContent='Reference changed. Run a new search for the current image and exact text.';
    if(!active)$('match-status').textContent='Ready to search the current reference and exact text.';
    buttons();
  }
  function settings(){return {crop:editor.crop,quarter_turns:editor.turns,perspective:editor.corners,
    rotation:Number($('proc-rotation').value),polarity:$('proc-polarity').value,method:$('proc-method').value,
    threshold:Number($('proc-threshold').value),foreground:$('proc-color').value,color_tolerance:Number($('proc-tolerance').value),
    contrast:Number($('proc-contrast').value),denoise:Number($('proc-denoise').value),outline:$('proc-outline').value,
    background_removal:$('proc-background').checked,shadow:$('proc-shadow').checked,deskew:$('proc-deskew').checked};}
  function syncCrop(){['crop-x','crop-y','crop-w','crop-h'].forEach((id,i)=>$(id).value=Math.round(editor.crop[i]*10000)/100);$('image-zoom').value=editor.zoom;$('image-tool').value=editor.mode;}
  const editor=new ImageEditor($('reference-canvas'),()=>{syncCrop();invalidate();},color=>{$('proc-color').value=color;$('proc-method').value='color';invalidate();});
  async function upload(file){
    if(!file)return;
    if(file.size>20*1024*1024){error('Choose an image smaller than 20 MiB.');return;}
    $('match-browse').disabled=true;
    try{
      const uploaded=await request('/images','POST',file,true);
      const previous=image;
      await editor.load(`/api/matching/images/${uploaded.id}`);
      image=uploaded;$('image-drop').hidden=true;$('editor-area').hidden=false;editor.draw();
      $('image-info').textContent=`${image.width} × ${image.height}`;
      $('image-tool').value='crop';editor.mode='crop';syncCrop();
      notes('processing-notes',image.notes);invalidate();
      if(previous)request(`/images/${previous.id}`,'DELETE').catch(()=>{});
      $('match-status').textContent='Image ready. Crop the lettering and enter its exact text.';
    }catch(e){error(e.message);}finally{$('match-browse').disabled=false;buttons();$('match-file').value='';}
  }
  async function prepare(){
    clearTimeout(processingTimer);
    if(!image)throw new Error('Upload an image first.');
    if(processed)return processed;
    if(processingPromise&&processingVersion===sourceVersion)return processingPromise;
    const captured=sourceVersion;processingVersion=captured;
    $('process-now').disabled=true;$('processing-notes').textContent='Isolating lettering…';
    const promise=request('/process','POST',{image_id:image.id,processing:settings()}).then(value=>{
      if(captured!==sourceVersion)throw new Error('Reference changed while processing. Update the preview again.');
      processed=value;$('processed-mask').src=`/api/matching/processed/${value.id}/mask`;$('processed-mask').hidden=false;
      $('processed-corrected').src=`/api/matching/processed/${value.id}/corrected`;$('processed-corrected').hidden=false;
      notes('processing-notes',[...image.notes,...value.warnings]);return value;
    }).finally(()=>{if(processingPromise===promise)processingPromise=null;buttons();});
    processingPromise=promise;return promise;
  }
  async function find(){
    if(!image||!validText())return;
    const captured=version;active=true;buttons();$('match-progress').hidden=false;
    try{
      const processed=await prepare();if(captured!==version){active=false;buttons();$('match-progress').hidden=true;$('match-status').textContent='Search cancelled before it started.';return;}
      const response=await request('/jobs','POST',{process_id:processed.id,text:$('match-text').value,shortlist:Number($('match-shortlist').value),
        sensitivity:$('match-sensitivity').value,tracking:Number($('match-tracking').value),alignment:$('match-alignment').value,variable_instances:$('match-variable').checked});
      job=response.id;
      if(captured!==version)await request(`/jobs/${job}/cancel`,'POST');
      poll(job,captured);
    }catch(e){active=false;buttons();$('match-progress').hidden=true;error(e.message);}
  }
  async function poll(key,captured){
    clearTimeout(pollTimer);
    try{
      const status=await request(`/jobs/${key}`);
      if(job!==key)return;
      $('match-status').textContent=`${status.message} · ${status.completed} / ${status.total}`;
      $('match-progress').value=(status.stage==='refining'?65:0)+(status.total?status.completed/status.total*(status.stage==='refining'?35:65):0);
      if(['completed','cancelled','failed'].includes(status.status)){
        active=false;buttons();$('match-progress').hidden=true;
        if(status.status==='completed'&&captured===version&&!status.catalog_changed){
          result=status;limit=20;renderResults();
          $('results-caption').textContent=`Exact matched text: ${JSON.stringify(status.text)} · ${status.eligible} eligible faces · ${status.seconds.toFixed(1)} seconds. Scores are relative shape matches, not probabilities.`;
          notes('match-warnings',[...status.warnings,`${status.excluded.missing_glyphs} faces excluded for missing glyphs; ${status.excluded.render_failed} could not render.`]);
        }else if(status.catalog_changed)error('The font catalog changed during this search. Run a new search.');
        else if(status.status==='failed')error(status.message);
        else if(captured!==version)$('match-status').textContent='Previous search discarded because the reference changed. Ready for a new search.';
        return;
      }
      pollTimer=setTimeout(()=>poll(key,captured),500);
    }catch(e){
      if(e.status===422||e.status===403){active=false;buttons();error(e.message);}
      else{$('match-status').textContent='Connection interrupted; retrying job status…';pollTimer=setTimeout(()=>poll(key,captured),1500);}
    }
  }
  function button(label,action,primary=false){const b=el('button',`button ${primary?'primary':'secondary'}`,label);b.addEventListener('click',async()=>{try{await action();}catch(e){error(e.message);}});return b;}
  function renderResults(){
    const list=$('match-result-list');list.replaceChildren();$('match-more').hidden=true;
    if(!result){notes('match-warnings',[]);return;}
    const favorites=$('match-favorites').checked, category=$('match-category').value;
    const results=result.results.filter(r=>(!favorites||bridge.state.favorites.has(r.font_id))&&(category==='all'||r.category===category));
    for(const item of results.slice(0,limit)){
      const card=el('article','match-card'); const heading=el('div','match-card-heading'),name=el('div','match-card-name');
      name.append(el('strong','',item.family),el('small','',`${item.style}${item.instance!=='Default'?` · ${item.instance}`:''}`));
      heading.append(el('span','match-rank',`#${item.rank}`),name,el('span','match-score',`${item.score.toFixed(1)}`));
      const preview=el('img');preview.alt=`${item.family} rendering of ${result.text}`;preview.loading='lazy';preview.src=`/api/matching/jobs/${result.id}/preview/${item.font_id}`;
      preview.addEventListener('error',()=>{preview.replaceWith(el('p','inline-error','Preview unavailable. Rescan and search again.'));});
      const actions=el('div','match-card-actions');
      actions.append(button('Inspect match',()=>openComparison(item),true),button(bridge.state.favorites.has(item.font_id)?'★ Favorited':'☆ Favorite',async()=>{await bridge.favorite(item.font_id);renderResults();}),
        button('Details',()=>bridge.details(item.font_id)),button('Add to comparison',()=>bridge.compare(item.font_id,result.text)),button('Open in Font Browser',()=>bridge.open(item.font_id)),
        button('Copy name',async()=>{const font=bridge.state.byId.get(item.font_id);if(!font)throw new Error('Font no longer available.');await navigator.clipboard.writeText(font.full_name);bridge.toast('Font name copied.');}),
        button('Locate file',()=>bridge.locate(item.font_id)));
      const details=el('details'),summary=el('summary','','Shape metrics');const dl=el('dl');
      Object.entries(item.metrics).forEach(([key,value])=>dl.append(el('dt','',key.replaceAll('_',' ')),el('dd','',Number(value).toFixed(3))));
      dl.append(el('dt','','Tracking'),el('dd','',`${item.tracking} px`),el('dt','','Mask'),el('dd','',item.mask));details.append(summary,dl);
      card.append(heading,preview,actions,details);list.append(card);
    }
    if(!results.length)list.append(el('p','finder-hint','No results match these filters. Try all categories or turn off favorites-only.'));
    $('match-more').hidden=results.length<=limit;
  }
  const ranges=[['x','Horizontal position',-250,250,1,0],['y','Vertical position',-150,150,1,0],['scale','Overall scale',.5,2,.01,1],
    ['scale_x','Horizontal scale',.5,2,.01,1],['scale_y','Vertical scale',.5,2,.01,1],['rotation','Rotation',-30,30,.25,0],['tracking','Character spacing',-12,24,.5,0],['opacity','Opacity',0,1,.01,.6]];
  for(const [key,label,min,max,step,value] of ranges){
    const row=el('label','',label),output=el('output','',String(value)),input=el('input');input.type='range';input.id=`align-${key}`;input.min=min;input.max=max;input.step=step;input.value=value;row.htmlFor=input.id;
    input.addEventListener('input',()=>{output.value=input.value;scheduleComparison();});row.append(output,input);$('alignment-controls').append(row);
  }
  function alignment(){const values=Object.fromEntries(ranges.map(([key])=>[key,Number($(`align-${key}`).value)]));return {...values,mode:$('compare-mode').value,reference:$('compare-reference').value};}
  function setAlignment(values={}){for(const [key,,,,,defaultValue] of ranges){const input=$(`align-${key}`);input.value=values[key]??(key==='tracking'?selected.tracking:defaultValue);input.previousElementSibling.value=input.value;}}
  function scheduleComparison(){clearTimeout(comparisonTimer);comparisonTimer=setTimeout(()=>renderComparison().catch(e=>{$('comparison-error').textContent=e.message;$('comparison-error').hidden=false;}),120);}
  async function renderComparison(){
    if(!selected||!result)return;
    const captured=++comparisonVersion;
    const blob=await request(`/jobs/${result.id}/compare`,'POST',{font_id:selected.font_id,alignment:alignment()},false,true);
    if(captured!==comparisonVersion)return;
    if(comparisonURL)URL.revokeObjectURL(comparisonURL);comparisonURL=URL.createObjectURL(blob);$('match-comparison-image').src=comparisonURL;
    $('comparison-error').hidden=true;
    $('comparison-legend').textContent=$('compare-mode').value==='difference'?'Pale: shared ink · red: reference only · cyan: candidate only.':$('compare-mode').value==='side'?'Left: reference · right: native candidate fitted with the current alignment.':'Cyan marks the candidate; original colors or the pale mask show the reference.';
  }
  async function openComparison(item){selected=item;setAlignment();$('match-compare-title').textContent=`${item.family} · ${item.style}`;$('match-compare-caption').textContent=`Exact text: ${JSON.stringify(result.text)} · automated relative score ${item.score.toFixed(1)}`;$('match-compare-dialog').showModal();await renderComparison();}
  $('match-compare-close').addEventListener('click',()=>$('match-compare-dialog').close());
  for(const id of ['compare-mode','compare-reference'])$(id).addEventListener('change',scheduleComparison);
  $('reset-alignment').addEventListener('click',()=>{setAlignment();scheduleComparison();});
  $('auto-align').addEventListener('click',async()=>{if(!selected)return;try{const auto=await request(`/jobs/${result.id}/auto-align`,'POST',{font_id:selected.font_id,alignment:alignment()});setAlignment(auto);scheduleComparison();}catch(e){error(e.message);}});
  $('export-comparison').addEventListener('click',async()=>{try{await renderComparison();const link=el('a');link.href=comparisonURL;link.download='FontFinderLocal-comparison.png';link.click();}catch(e){error(e.message);}});
  $('match-browse').addEventListener('click',()=>$('match-file').click());$('image-drop').addEventListener('click',()=>$('match-file').click());
  $('image-drop').addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();$('match-file').click();}});
  $('match-file').addEventListener('change',e=>upload(e.target.files[0]));
  host.addEventListener('dragover',e=>{if(e.dataTransfer.types.includes('Files')){e.preventDefault();$('image-drop').classList.add('dragging');}});
  host.addEventListener('dragleave',()=>$('image-drop').classList.remove('dragging'));
  host.addEventListener('drop',e=>{e.preventDefault();$('image-drop').classList.remove('dragging');upload(e.dataTransfer.files[0]);});
  $('image-tool').addEventListener('change',()=>{editor.setMode($('image-tool').value);$('editor-help').textContent=editor.mode==='perspective'?'Drag corners 1–4 in order: top-left, top-right, bottom-right, bottom-left. Reset crop to remove perspective correction.':editor.mode==='color'?'Click a clean interior area of the letter fill. The selected color is used for isolation.':editor.mode==='pan'?'Drag to pan. Use Zoom or Fit image to change your view.':'Drag around one complete line in one typeface.';});
  $('image-rotate').addEventListener('click',()=>editor.rotate());$('crop-reset').addEventListener('click',()=>editor.resetCrop());
  $('image-restore').addEventListener('click',()=>{editor.restore(false);$('proc-rotation').value=0;$('proc-polarity').value='auto';$('proc-method').value='auto';$('proc-contrast').value=1;$('proc-threshold').value=128;$('proc-outline').value='auto';$('proc-shadow').checked=false;$('proc-deskew').checked=false;$('proc-denoise').value=1;$('proc-background').checked=true;syncCrop();invalidate();});
  $('image-zoom').addEventListener('input',()=>{editor.zoom=Number($('image-zoom').value);editor.draw();});$('image-fit').addEventListener('click',()=>{editor.zoom=1;editor.pan=[0,0];syncCrop();editor.draw();});
  $('crop-apply').addEventListener('click',()=>{let [x,y,w,h]=['crop-x','crop-y','crop-w','crop-h'].map(id=>Number($(id).value)/100);if([x,y,w,h].some(v=>!Number.isFinite(v))||x<0||y<0||w<.005||h<.005||x+w>1||y+h>1){error('Crop bounds must fit inside 0–100%.');return;}editor.crop=[x,y,w,h];editor.corners=null;editor.mode='crop';syncCrop();editor.draw();invalidate();});
  $('match-text').addEventListener('input',()=>invalidate(false));
  for(const id of ['proc-polarity','proc-method','proc-threshold','proc-contrast','proc-denoise','proc-rotation','proc-color','proc-tolerance','proc-outline','proc-background','proc-shadow','proc-deskew'])$(id).addEventListener('input',()=>{$('threshold-value').value=$('proc-threshold').value;$('contrast-value').value=$('proc-contrast').value;invalidate();});
  for(const id of ['match-sensitivity','match-tracking','match-shortlist','match-alignment','match-variable'])$(id).addEventListener('change',()=>invalidate(false));
  $('process-now').addEventListener('click',()=>{processed=null;prepare().catch(e=>error(e.message));});$('find-fonts').addEventListener('click',find);
  $('cancel-match').addEventListener('click',()=>{version++;$('match-status').textContent='Cancellation requested…';if(job)request(`/jobs/${job}/cancel`,'POST').catch(e=>error(e.message));});
  $('match-more').addEventListener('click',()=>{limit+=20;renderResults();});
  $('match-favorites').addEventListener('change',renderResults);$('match-category').addEventListener('change',renderResults);
  buttons();
  return {show(){editor.draw();renderResults();},catalogChanged(revision){if(result&&result.catalog_revision!==revision)invalidate(false);}};
}

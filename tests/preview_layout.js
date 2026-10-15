import {createSample, updateSample} from '/static/fonts.js';
const report=document.getElementById('report'), host=document.getElementById('cases');
const frame=()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));
document.getElementById('run').addEventListener('click',async()=>{
  const checks=[], failures=[];
  host.replaceChildren();report.textContent='Running…';
  try {
    const {fonts}=await (await fetch('/api/fonts')).json();
    if(fonts.length!==3)throw new Error('Wait for the three fixture fonts to finish loading.');
    const cases=[];
    for(const font of fonts)for(const density of ['compact','comfortable']) {
      const wrapper=document.createElement('div');wrapper.className=`case ${density==='compact'?'compact':''}`;
      const card=document.createElement('article');card.className='font-card';
      const title=document.createElement('div');title.className='card-heading';title.textContent=font.family+' / '+density;
      card.append(title);wrapper.append(card);host.append(wrapper);
      const coordinates=font.axes.length?{wght:900}:{};
      createSample(card,font,'A S A',46,coordinates);cases.push({card,font,coordinates});
    }
    const deadline=performance.now()+15000;
    while(cases.some(c=>c.card.dataset.loaded!=='true')) {
      if(performance.now()>deadline)throw new Error('Native font load timed out.');
      await frame();
    }
    for(const size of [24,46,72,126,24])for(const text of ['A S A','\nA S A\nA',Array(35).fill('A S A').join(' ')]) {
      for(const c of cases) updateSample(c.card,c.font,text,size,c.coordinates);
      await frame();
      for(const {card,font,coordinates} of cases) {
        const sample=card.querySelector('.font-sample'),style=getComputedStyle(sample);
        // An inline zero-height marker exposes the DOM baseline independently of
        // the canvas metrics used by production. Fixture bounds are known outlines.
        const probe=document.createElement('span');
        probe.style.cssText='display:inline-block;width:0;height:0;vertical-align:baseline';
        sample.prepend(probe);
        const baseline=probe.getBoundingClientRect().top;
        const tall=font.family==='Preview Tall'||coordinates.wght===900;
        const top=sample.getBoundingClientRect().top,bottom=top+sample.clientHeight;
        const lineHeight=parseFloat(style.lineHeight);
        const lines=text.split('\n').map((value,index)=>({value,index})).filter(l=>l.value);
        const inkTop=baseline+lines[0].index*lineHeight-(tall?2.2:.7)*size;
        const inkBottom=baseline+lines.at(-1).index*lineHeight+(tall?.8:0)*size;
        const result={font:font.family,density:card.parentElement.className,size,multiline:text.includes('\n'),long:text.length>100,
          verticalOverflow:sample.scrollHeight-sample.clientHeight,horizontalOverflow:sample.scrollWidth>sample.clientWidth,
          topClearance:Math.round((inkTop-top)*100)/100,bottomClearance:Math.round((bottom-inkBottom)*100)/100,
          cardContainsSample:sample.getBoundingClientRect().bottom<=card.getBoundingClientRect().bottom};
        probe.remove();
        checks.push(result);
        if(result.verticalOverflow>1||result.topClearance<-.5||result.bottomClearance<-.5||!result.cardContainsSample||result.long&&!result.horizontalOverflow)failures.push(result);
      }
    }
    // Also shrink the variable instance without reloading its font asset.
    for(const c of cases.filter(c=>c.font.axes.length)) {
      updateSample(c.card,c.font,'A S A',24,{wght:900});await frame();
      const sample=c.card.querySelector('.font-sample'),before=sample.clientHeight;
      updateSample(c.card,c.font,'A S A',24,{wght:400});await frame();
      if(before-sample.clientHeight<24)failures.push({font:c.font.family,error:'Variable instance height did not shrink with the same text and size'});
    }
    report.textContent=JSON.stringify({passed:failures.length===0,checks:checks.length,failures,results:checks},null,2);
  } catch(error) {report.textContent=JSON.stringify({passed:false,error:error.message});}
});


(()=>{
 const VALID_LENGTHS=[16,32];
 const normalizeLen=v=>VALID_LENGTHS.includes(+v)?+v:16;
 function setLength(v,render=true){
  patternLength=normalizeLen(v);
  for(const id of ['patternLen','appPatternLen','p26PatternLen']){
   const el=document.getElementById(id);if(!el)continue;
   el.disabled=false;el.removeAttribute('disabled');
   el.innerHTML=id==='p26PatternLen'
    ? '<option value="16">16 steps · 1 bar</option><option value="32">32 steps · 2 bars</option>'
    : '<option value="16">16</option><option value="32">32</option>';
   el.value=String(patternLength);
   el.setAttribute('aria-label','Pattern length, 16 or 32 steps');
  }
  try{localStorage.setItem('dm3ag.patternLength',String(patternLength));}catch(_){}
  if(render)renderSeq();
 }
 function decorateSeq29(){
  const s=document.getElementById('seq');if(!s)return;
  const n=normalizeLen(patternLength);
  s.querySelectorAll('.hdr[data-s],.step[data-s]').forEach(el=>{
   const st=+el.dataset.s;if(!Number.isFinite(st))return;
   const beat=Math.floor(st/4),sub=st%4,bar=Math.floor(st/16),beatInBar=(beat%4)+1;
   el.classList.toggle('downBeat',sub===0);
   el.classList.toggle('beatEnd',sub===3);
   el.classList.toggle('beatBandAlt',(beat&1)===1);
   el.classList.toggle('barStart',st>0&&st%16===0);
   el.dataset.beat=String(beatInBar);el.dataset.bar=String(bar+1);el.dataset.sub=String(sub);
   if(el.classList.contains('hdr')){
    el.textContent=sub===0?String(beatInBar):(['','e','&','a'][sub]);
    el.title=`Bar ${bar+1}, beat ${beatInBar}${sub===0?'':(' '+['','e','&','a'][sub])}`;
   }
  });
  const wrap=s.closest('.seqwrap');if(!wrap)return;
  let ruler=wrap.querySelector('.seqBeatRuler');
  if(!ruler){ruler=document.createElement('div');ruler.className='seqBeatRuler';wrap.insertBefore(ruler,s);}
  const beats=n/4;
  ruler.innerHTML='<span class="beatSpacer"></span>'+Array.from({length:beats},(_,i)=>{
   const bar=Math.floor(i/4)+1,beat=(i%4)+1;
   return `<b class="beatGroup ${i>0&&i%4===0?'barStart':''}">BAR ${bar} · BEAT ${beat}</b>`;
  }).join('');
  requestAnimationFrame(()=>{
   const label=s.querySelector('.padHdr')?.getBoundingClientRect().width||104;
   const width=Math.max(s.scrollWidth,wrap.clientWidth);
   ruler.style.width=width+'px';
   ruler.style.gridTemplateColumns=label+'px repeat('+beats+',minmax(144px,1fr))';
  });
 }
 // Replace PASS28's force-16 render wrapper with a normal 16/32 renderer.
 renderSeq=function(){
  const s=document.getElementById('seq');if(!s)return;
  s.innerHTML='';const n=normalizeLen(patternLength);patternLength=n;
  s.style.gridTemplateColumns=`104px repeat(${n},minmax(28px,1fr))`;
  const x=document.createElement('div');x.className='hdr padHdr';x.textContent='PAD';s.appendChild(x);
  for(let st=0;st<n;st++){const h=document.createElement('div');h.className='hdr'+(st%4===0?' beatHead':'');h.dataset.s=st;h.textContent=st+1;s.appendChild(h);}
  for(let p=0;p<padState.length;p++){
   const l=document.createElement('div');l.className='lab';l.textContent=padState[p].label;s.appendChild(l);
   for(let st=0;st<n;st++){
    const e=document.createElement('button');e.className='step'+(st%4===0?' beatStart':'');e.dataset.p=p;e.dataset.s=st;
    e.onpointerdown=(ev)=>{if(ev.button!==0)return;ev.preventDefault();pushHistory();const m=metaAt(p,st);if(ev.altKey){m.prob=m.prob<1?1:.5;updateStep(e,pattern[p][st],m);seqPaint.active=false;return;}if(ev.shiftKey){m.ratchet=m.ratchet===1?2:(m.ratchet===2?4:1);updateStep(e,pattern[p][st],m);seqPaint.active=false;return;}seqPaint.active=true;seqPaint.start=e;seqPaint.moved=false;seqPaint.value=(pattern[p][st]+1)%3;paintStep(e,p,st,seqPaint.value);};
    e.onpointerenter=()=>{if(!seqPaint.active)return;seqPaint.moved=true;paintStep(e,p,st,seqPaint.value);};e.oncontextmenu=ev=>ev.preventDefault();s.appendChild(e);updateStep(e,pattern[p][st],metaAt(p,st));
   }
  }
  decorateSeq29();
 };
 // Preserve pattern/meta rows through model changes by matching physical pad labels.
 const baseSetModel29=setModel;
 setModel=function(k){
  const hadState=Array.isArray(padState)&&padState.length&&Array.isArray(pattern)&&pattern.length;
  const oldLen=normalizeLen(patternLength), oldPads=hadState?padState.map(p=>p.label):[], oldPattern=hadState?pattern.map(r=>r.slice()):[], oldMeta=hadState?stepMeta.map(r=>r.map(m=>({...m}))):[];
  baseSetModel29(k);
  if(hadState){
   const freshPattern=pattern.map(r=>r.slice()),freshMeta=stepMeta.map(r=>r.map(m=>({...m})));
   for(let ni=0;ni<padState.length;ni++){
    let oi=oldPads.indexOf(padState[ni].label);
    if(oi<0&&ni<oldPattern.length)oi=ni;
    if(oi>=0&&oldPattern[oi]){freshPattern[ni]=oldPattern[oi].slice(0,64);while(freshPattern[ni].length<64)freshPattern[ni].push(0);}
    if(oi>=0&&oldMeta[oi]){freshMeta[ni]=oldMeta[oi].slice(0,64).map(m=>({...m}));while(freshMeta[ni].length<64)freshMeta[ni].push({prob:1,ratchet:1});}
   }
   pattern=freshPattern;stepMeta=freshMeta;patternLength=oldLen;setLength(oldLen,false);renderSeq();
   try{lcd(`${model.display} READY`,`PATTERN KEPT · ${patternLength} STEPS`)}catch(_){}
  } else setLength(oldLen,false);
  if(document.body.dataset.view==='patterns')renderHistoryPatterns?.();
 };
 // 16-step and 32-step presets are both valid.
 historyPatternValid=function(p){
  if(!p||!VALID_LENGTHS.includes(+p.length)||!(+p.bpm>0))return false;
  for(const [role,exp] of Object.entries(p.expected||{}))if((p.roles?.[role]||[]).join(',')!==exp)return false;
  return true;
 };
 // Presets set their own length, and a failed role mapping does not destroy the current pattern.
 loadHistoryPattern=function(id,playNow=false){
  const p=HISTORY_PATTERNS.find(x=>x.id===id);
  if(!p||!historyPatternValid(p)){lcd('PATTERN UNAVAILABLE','GRID VERIFY FAILED');return false;}
  const before={modelKey,patternLength,padState:padState.map(x=>({...x})),pattern:pattern.map(r=>r.slice()),stepMeta:stepMeta.map(r=>r.map(m=>({...m}))),bpm:$('bpm').value,swing:$('swing').value};
  pushHistory();stop();
  if(p.alesis&&p.id==='sp-1979-main'&&modelKey!=='sr16')setModel('sr16');
  const mapped={};const missing=[];
  for(const [role,steps] of Object.entries(p.roles)){const pad=historyRolePad(role);if(pad<0)missing.push(role);else mapped[role]=pad;}
  if(missing.length){
   if(before.modelKey!==modelKey)setModel(before.modelKey);
   padState=before.padState;pattern=before.pattern;stepMeta=before.stepMeta;patternLength=before.patternLength;$('bpm').value=before.bpm;$('bpmv').textContent=before.bpm;$('swing').value=before.swing;$('swingv').textContent=before.swing;setLength(patternLength,false);renderPads();renderSeq();syncEditor();
   lcd('PATTERN UNAVAILABLE','NO PAD FOR '+missing.join(','));return false;
  }
  patternLength=normalizeLen(p.length);setLength(patternLength,false);clearHistoryPatternData();
  for(const [role,steps] of Object.entries(p.roles)){const pad=mapped[role];for(const st of steps)if(st>=0&&st<patternLength)pattern[pad][st]=1;}
  $('bpm').value=String(p.bpm);$('bpmv').textContent=String(p.bpm);$('swing').value='50';$('swingv').textContent='50';renderPads();renderSeq();selectedPad=0;syncEditor();dev12SetView('play');lcd(`${p.artist} — ${p.title}`,`${p.section} · ${p.bpm} BPM · ${p.length} STEPS`);if(playNow)setTimeout(()=>play(),80);return true;
 };
 // Preview both bars for 32-step presets instead of silently showing only bar 1.
 historyPreview=function(p){const n=normalizeLen(p.length),roleNames=Object.keys(p.roles);let html=`<div class="patternGridPreview p29Preview" style="grid-template-columns:64px repeat(${n},1fr)"><span></span>`+Array.from({length:n},(_,i)=>`<b class="${i===16?'barStart':''}">${(i%16)+1}</b>`).join('');for(const role of roleNames){html+=`<span class="lab">${role.toUpperCase()}</span>`;const set=new Set(p.roles[role]||[]);for(let i=0;i<n;i++)html+=`<i class="${set.has(i)?'on':''} ${i===16?'barStart':''}"></i>`;}return html+'</div>';};
 function wireLengths(){
  for(const id of ['patternLen','appPatternLen','p26PatternLen']){const el=document.getElementById(id);if(!el)continue;const clone=el.cloneNode(true);el.replaceWith(clone);clone.disabled=false;clone.innerHTML=id==='p26PatternLen'?'<option value="16">16 steps · 1 bar</option><option value="32">32 steps · 2 bars</option>':'<option value="16">16</option><option value="32">32</option>';clone.value=String(normalizeLen(patternLength));clone.addEventListener('change',e=>{pushHistory();setLength(e.target.value,true);});}
 }
 function init29(){
  wireLengths();setLength(normalizeLen(patternLength),false);renderSeq();renderHistoryPatterns?.();
  // PASS28 has one delayed force-16 cleanup at 80 ms; run after it and remove its disabled state/listeners again.
  setTimeout(()=>{wireLengths();setLength(normalizeLen(patternLength),false);renderSeq();renderHistoryPatterns?.();},160);
 }
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init29,{once:true});else init29();
 window.addEventListener('resize',()=>setTimeout(decorateSeq29,50),{passive:true});window.addEventListener('orientationchange',()=>setTimeout(decorateSeq29,150),{passive:true});
})();

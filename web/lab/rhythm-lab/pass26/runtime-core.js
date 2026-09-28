const $=id=>document.getElementById(id);
const ROMS={};
const ROM_SPEC={
 hr16:{crc:0xbd375386,files:['HR16_U15.BIN','HR16_U16.BIN']},
 hr16b:{crc:0xf5e8f90d,files:['HR16_B_U15.BIN','HR16_B_U16.BIN']},
 sr16:{crc:0xf37f8486,files:['SR16_U5.BIN','SR16_U6.BIN']}
};
let modelKey='hr16',model=MODELS.hr16,padState=[],selectedPad=0;
let patternLength=32,pattern=[],stepMeta=[],stepIndex=0,timer=null,playing=false;
let productMode='authentic',history=[],future=[],barClipboard=null,crashSlotToggle=11;
let audioCtx=null,activeSlots=Array(16).fill(null),pcmCache=new Map(),midiAccess=null,midiEnabled=false;

function lcd(a,b=''){if($('lcd1'))$('lcd1').textContent=a;if($('lcd2'))$('lcd2').textContent=b;}
function crc32(bytes){let c=0xffffffff;for(let i=0;i<bytes.length;i++){c^=bytes[i];for(let k=0;k<8;k++)c=(c>>>1)^((c&1)?0xedb88320:0);}return(c^0xffffffff)>>>0;}
function concatBytes(a,b){const u=new Uint8Array(a.length+b.length);u.set(a);u.set(b,a.length);return u;}
async function fetchBytes(url){
 const urls=[url,'https://api.allorigins.win/raw?url='+encodeURIComponent(url),'https://corsproxy.io/?url='+encodeURIComponent(url),'https://cors.isomorphic-git.org/'+url];
 let last;
 for(const u of urls){try{const r=await fetch(u,{cache:'force-cache'});if(!r.ok)throw Error('HTTP '+r.status);const b=new Uint8Array(await r.arrayBuffer());if(b.length===524288)return b;throw Error('bad size '+b.length);}catch(e){last=e;}}
 throw last||Error('ROM fetch failed');
}
async function loadRom(k){
 if(ROMS[k])return ROMS[k];
 const spec=ROM_SPEC[k],base='https://burnkit2600.com/hr16/';
 if($('engineStat')){$('engineStat').textContent='LOADING';$('engineStat').className='';}
 const a=await fetchBytes(base+spec.files[0]),b=await fetchBytes(base+spec.files[1]);
 for(const combo of[concatBytes(a,b),concatBytes(b,a)])if(crc32(combo)===spec.crc){ROMS[k]=combo;if(k===modelKey&&$('engineStat')){$('engineStat').textContent='READY';$('engineStat').className='good';}return combo;}
 throw Error('ROM checksum failed');
}
function warmRoms(){loadRom(modelKey).catch(e=>{console.error(e);if($('engineStat')){$('engineStat').textContent='ROM ERROR';$('engineStat').className='bad';}lcd('SAMPLE ROM LOAD FAILED','CHECK CONNECTION');});for(const k of Object.keys(ROM_SPEC))if(k!==modelKey)setTimeout(()=>loadRom(k).catch(()=>{}),800);}
function signed8(b){return b<128?b:b-256;}
function decodeVoice(ptr){const key=modelKey+':'+ptr;if(pcmCache.has(key))return pcmCache.get(key);const rom=ROMS[modelKey];if(!rom)return null;let pos=ptr>>>0,shift=8,out=[],guard=0;while(pos<rom.length&&guard++<rom.length){let q=signed8(rom[pos++]);if(q===-128){let n=1;if(shift>0)shift--;while(pos<rom.length&&signed8(rom[pos])===-128){pos++;if(++n>=3){const pcm=Float32Array.from(out);pcmCache.set(key,pcm);return pcm;}}continue;}out.push((q*(1<<shift))/32768);}const pcm=Float32Array.from(out);pcmCache.set(key,pcm);return pcm;}
function ensureAudio(){const AC=window.AudioContext||window.webkitAudioContext;if(!AC)throw Error('Web Audio unavailable');if(!audioCtx||audioCtx.state==='closed')audioCtx=new AC({latencyHint:'interactive'});if(audioCtx.state!=='running')audioCtx.resume().catch(()=>{});if($('engineStat')){$('engineStat').textContent='ACTIVE';$('engineStat').className='good';}return audioCtx;}
function stopSlot(slot){const x=activeSlots[slot&15];if(x){try{x.stop()}catch(_){}activeSlots[slot&15]=null;}}
function slotForPad(i){const n=(padState[i]?.label||'').toUpperCase();if(n.includes('HAT'))return 2;if(n.includes('CRASH')){const x=crashSlotToggle;crashSlotToggle=x===11?12:11;return x;}return i&15;}
function primaryPtr(v){return modelKey==='sr16'?(v.descriptors?.[0]?.ptr||0):(v.ptr||0);}
function voiceName(v){return String(v.num).padStart(3,'0')+' '+v.name;}
function voiceComponents(v,velocity){if(modelKey!=='sr16')return[{ptr:v.ptr,rate:1}];const ds=v.descriptors||[];if(!ds.length)return[];const dyn=ds.filter(d=>d.selector>=2&&d.selector<=8).sort((a,b)=>a.selector-b.selector);let use=dyn.length?[dyn[Math.min(dyn.length-1,Math.floor((Math.max(1,velocity)/128)*dyn.length))],...ds.filter(d=>d.selector<=1)]:ds.filter(d=>d.selector<=1);if(!use.length)use=[ds[0]];return use.map(d=>({ptr:d.ptr,rate:(Math.max(0,Math.min(31,d.b4|0))+16)/32}));}
function anySolo(){return padState.some(p=>p.solo);}
function padAudible(i){return!padState[i]?.mute&&(!anySolo()||padState[i]?.solo);}
async function triggerPad(i,velocity=105){
 if(!padAudible(i))return;
 try{
  if(!ROMS[modelKey])await loadRom(modelKey);
  const c=ensureAudio(),p=padState[i],v=model.voices[p.voice]||model.voices[0],comps=voiceComponents(v,velocity),slot=slotForPad(i);
  stopSlot(slot);
  const gainBase=(p.vol/127)*(Math.max(1,velocity)/127)/Math.sqrt(Math.max(1,comps.length));let last=null;
  for(const comp of comps){const pcm=decodeVoice(comp.ptr);if(!pcm||!pcm.length)continue;const buf=c.createBuffer(1,pcm.length,48000);buf.copyToChannel(pcm,0);const src=c.createBufferSource(),g=c.createGain();src.buffer=buf;src.playbackRate.value=Math.max(.1,Math.min(4,Math.pow(2,p.tune/12)*(comp.rate||1)));g.gain.value=gainBase;src.connect(g);if(c.createStereoPanner){const pan=c.createStereoPanner();pan.pan.value=p.pan/3;g.connect(pan);pan.connect(c.destination);}else g.connect(c.destination);src.start();last=src;}
  if(last)activeSlots[slot]=last;
  lcd(p.label+': '+v.name,'TUNE '+(p.tune>0?'+':'')+p.tune+' • LEVEL '+p.vol+' • PAN '+(p.pan>0?'+':'')+p.pan);
  const el=document.querySelector('.pad[data-pad="'+i+'"]');if(el){el.classList.add('hit');setTimeout(()=>el.classList.remove('hit'),70);}
 }catch(e){console.error(e);lcd('AUDIO ERROR',String(e.message||e).slice(0,34));if($('engineStat')){$('engineStat').textContent='ERROR';$('engineStat').className='bad';}}
}
function snapshot(){return JSON.stringify({modelKey,padState,pattern,stepMeta,patternLength,bpm:+$('bpm').value,swing:+$('swing').value});}
function pushHistory(){history.push(snapshot());if(history.length>40)history.shift();future.length=0;}
function restoreSnapshot(s){try{const x=JSON.parse(s);if(x.modelKey!==modelKey){modelKey=x.modelKey;model=MODELS[modelKey];document.body.dataset.model=modelKey;}padState=x.padState;pattern=x.pattern;stepMeta=x.stepMeta;patternLength=x.patternLength||32;$('bpm').value=x.bpm||120;$('bpmv').textContent=$('bpm').value;$('swing').value=x.swing||50;$('swingv').textContent=$('swing').value;renderAll();}catch(e){console.error(e)}}
function undo(){if(!history.length)return;future.push(snapshot());restoreSnapshot(history.pop());}
function redo(){if(!future.length)return;history.push(snapshot());restoreSnapshot(future.pop());}
function setProductMode(m){productMode=m;$('authBtn')?.classList.toggle('active',m==='authentic');$('modernBtn')?.classList.toggle('active',m==='modern');$('settingsAuth')?.classList.toggle('active',m==='authentic');$('settingsModern')?.classList.toggle('active',m==='modern');}
function resetPads(){padState=model.pads.map((label,i)=>({label,voice:model.defaults?.[i]??0,tune:0,vol:112,pan:0,bus:1,mute:false,solo:false}));selectedPad=0;pattern=Array.from({length:padState.length},()=>Array(64).fill(0));stepMeta=Array.from({length:padState.length},()=>Array.from({length:64},()=>({prob:1,ratchet:1})));const ix=t=>padState.findIndex(p=>p.label===t),kick=ix('KICK'),sn=ix('SNARE'),ch=ix('CLOSED HAT'),oh=ix('OPEN HAT');if(kick>=0)[0,4,8,12].forEach(x=>pattern[kick][x]=2);if(sn>=0)[4,12].forEach(x=>pattern[sn][x]=2);if(ch>=0)for(let x=0;x<16;x+=2)pattern[ch][x]=1;if(oh>=0)[7,15].forEach(x=>pattern[oh][x]=1);}
function renderPads(){const b=$('pads');if(!b)return;b.innerHTML='';padState.forEach((p,i)=>{const v=model.voices[p.voice]||model.voices[0],el=document.createElement('button');el.className='pad'+(i===selectedPad?' selected':'')+(p.mute?' muted':'')+(p.solo?' soloed':'');el.dataset.pad=i;el.innerHTML='<span class="padnum">'+String(i+1).padStart(2,'0')+'</span><span class="padtop"><span class="pname">'+p.label+'</span><span class="padflags">'+(p.mute?'M':'')+(p.solo?'S':'')+'</span></span><span class="vname">'+v.name+'</span>';el.onclick=()=>{selectedPad=i;renderPads();syncEditor();triggerPad(i,110)};el.oncontextmenu=e=>{e.preventDefault();pushHistory();if(e.shiftKey)p.solo=!p.solo;else p.mute=!p.mute;renderPads();renderMixerView();};b.appendChild(el);});}
function fillVoiceSelect(){const s=$('voiceSel');if(!s)return;s.innerHTML='';model.voices.forEach((v,i)=>{const o=document.createElement('option');o.value=i;o.textContent=voiceName(v);s.appendChild(o);});}
function syncEditor(){const p=padState[selectedPad];if(!p)return;const v=model.voices[p.voice]||model.voices[0];$('editPad').textContent=p.label;$('voiceSel').value=String(p.voice);$('tune').value=p.tune;$('tunev').textContent=p.tune;$('vol').value=p.vol;$('volv').textContent=p.vol;$('pan').value=p.pan;$('panv').textContent=p.pan;$('out1Btn')?.classList.toggle('active',p.bus===1);$('out2Btn')?.classList.toggle('active',p.bus===2);$('voiceInfo').textContent='SOUND '+v.num+' • '+v.name+' • ASSIGNED TO '+p.label;if($('browserPad'))$('browserPad').textContent=p.label;if($('p26CurrentVoice'))$('p26CurrentVoice').textContent=v.name;}
function metaAt(p,s){return stepMeta[p][s]||(stepMeta[p][s]={prob:1,ratchet:1});}
function updateStep(e,val,m){e.classList.toggle('on',val>0);e.classList.toggle('accent',val>1);e.title=val?((val>1?'Accent':'Hit')+' • '+Math.round((m?.prob??1)*100)+'%'):'';}
function renderSeq(){const s=$('seq');if(!s)return;s.innerHTML='';s.style.gridTemplateColumns='104px repeat('+patternLength+',minmax(28px,1fr))';let h=document.createElement('div');h.className='hdr padHdr';h.textContent='PAD';s.appendChild(h);for(let st=0;st<patternLength;st++){h=document.createElement('div');h.className='hdr'+(st%4===0?' beatHead':'');h.dataset.s=st;h.textContent=st+1;s.appendChild(h);}padState.forEach((p,pi)=>{const l=document.createElement('div');l.className='lab';l.textContent=p.label;s.appendChild(l);for(let st=0;st<patternLength;st++){const e=document.createElement('button');e.className='step'+(st%4===0?' beatStart':'');e.dataset.p=pi;e.dataset.s=st;updateStep(e,pattern[pi][st],metaAt(pi,st));e.onclick=()=>{pushHistory();pattern[pi][st]=(pattern[pi][st]+1)%3;updateStep(e,pattern[pi][st],metaAt(pi,st));};s.appendChild(e);}});}
function showPlayhead(st){document.querySelectorAll('.step.playhead,.hdr.playhead').forEach(e=>e.classList.remove('playhead'));document.querySelectorAll('[data-s="'+st+'"]').forEach(e=>e.classList.add('playhead'));}
function tick(){const st=stepIndex%patternLength;showPlayhead(st);for(let p=0;p<padState.length;p++){const v=pattern[p][st];if(v)triggerPad(p,v>1?127:98);}stepIndex=(st+1)%patternLength;}
function play(){if(playing)return;playing=true;$('playBtn')?.classList.add('active');tick();timer=setInterval(tick,60000/(+$('bpm').value||120)/4);lcd('PLAYING',$('bpm').value+' BPM • '+patternLength+' STEPS');}
function stop(){playing=false;clearInterval(timer);timer=null;$('playBtn')?.classList.remove('active');stepIndex=0;showPlayhead(-1);}
function setPatternLength(n){patternLength=Math.max(16,Math.min(64,+n||32));['patternLen','appPatternLen','p26PatternLen'].forEach(id=>{if($(id))$(id).value=String(patternLength)});renderSeq();}
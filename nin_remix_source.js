
(function () {
'use strict';
const $ = id => document.getElementById(id);
const names = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B'];
const library = JSON.parse($('embedded-library').textContent);
let current = null;
let song = null;
let focus = 1;
let events = [];
let groups = new Map();
let cursor = 0;
let audio = null, master = null, compressor = null, synthBus = null, drumBus = null, duck = null;
let clean = null, dirty = null, driveNode = null, crushNode = null;
let delaySend = null, delayNode = null, feedback = null, noise = null;
let live = [], timer = 0, playing = false, position = 0, startPosition = 0, startTime = 0, speed = 1;
let preset = 'machine', randomSeed = 11;
const values = {glitch:24,gate:38,drive:52,crush:18,delay:16,filter:55,arp:'16',direction:'updown',kick:true,sub:true};
const presets = {
  original:{glitch:0,gate:0,drive:0,crush:0,delay:0,filter:0,arp:'off',direction:'up',kick:false,sub:false},
  machine:{glitch:24,gate:38,drive:52,crush:18,delay:16,filter:55,arp:'16',direction:'updown',kick:true,sub:true},
  glitch:{glitch:82,gate:65,drive:55,crush:78,delay:42,filter:66,arp:'32',direction:'random',kick:false,sub:false},
  ebm:{glitch:10,gate:58,drive:46,crush:16,delay:20,filter:48,arp:'16',direction:'up',kick:true,sub:true},
  broken:{glitch:69,gate:55,drive:70,crush:51,delay:26,filter:70,arp:'32',direction:'updown',kick:true,sub:false},
  cold:{glitch:17,gate:23,drive:26,crush:20,delay:60,filter:68,arp:'8',direction:'down',kick:false,sub:true}
};
const ranges = ['glitch','gate','drive','crush','delay','filter'];
function clock(s){ s=Math.max(0,s||0);return Math.floor(s/60)+':'+String(Math.floor(s%60)).padStart(2,'0'); }
function noteLabel(p) {return names[p%12] + (Math.floor(p/12)-1); }
function decode64(s) {const v=atob(s.replace(/\s/g,'')),a=new Uint8Array(v.length);for(let i=0;i<a.length;i++)a[i]=v.charCodeAt(i);return a;}
function parseMidi(data) {
 const d=new Uint8Array(data),size=d.length;let p=0;
 const str=n=>{let s='';while(n--)s+=String.fromCharCode(d[p++]);return s;};
 const uint=n=>{let v=0;while(n--)v=v*256+d[p++];return v;};
 const variable=()=>{let x=0,a,k=0;do{if(k++>5||p>=size)throw Error('Invalid MIDI delta');a=d[p++];x=x*128+(a&127);}while(a&128);return x;};
 if(str(4)!=='MThd')throw Error('MIDI header invalid');
 const head=uint(4),format=uint(2),num=uint(2),division=uint(2);
 if(division>=32768)throw Error('SMPTE timebase unsupported');
 p=8+head;
 let tempos=[{t:0,v:500000}],sig='4/4',tracks=[];
 for(let id=0;id<num;id++) {
   if(str(4)!=='MTrk')throw Error('Track header '+id+' invalid');
   let length=uint(4),end=p+length,tick=0,running=0,title='',program={},notes=[],active=new Map(),channels=new Set();
   if(end>size)throw Error('Truncated MIDI track');
   while(p<end) {
     tick+=variable();
     let status=d[p];
     if(status&128){p++;if(status<240)running=status;}else status=running;
     if(status===255) {
       let kind=d[p++],n=variable(),start=p;p+=n;
       if(kind===3)title=String.fromCharCode(...d.subarray(start,p));
       else if(kind===81&&n===3)tempos.push({t:tick,v:d[start]*65536+d[start+1]*256+d[start+2]});
       else if(kind===88&&n>=2)sig=d[start]+'/'+(2**d[start+1]);
       continue;
     }
     if(status===240||status===247){p+=variable();continue;}
     if(status>=241&&status<=246){p+=status===242?2:status===241||status===243?1:0;continue;}
     if(status>=248){continue;}
     if(status<128)throw Error('Running status invalid in track '+id);
     let kind=status&240,ch=status&15,a=d[p++],v=kind===192||kind===208?0:d[p++];
     channels.add(ch);
     if(kind===192)program[ch]=a;
     if(kind===144&&v>0){let key=ch+':'+a,ar=active.get(key)||[];ar.push({tick,vel:v});active.set(key,ar);}
     if(kind===128||(kind===144&&v===0)){
       let ar=active.get(ch+':'+a);
       if(ar&&ar.length){let n=ar.shift();notes.push({tick:n.tick,len:Math.max(1,tick-n.tick),pitch:a,vel:n.vel,ch});}
     }
   }
   p=end;
   notes.sort((a,b)=>a.tick-b.tick);
   tracks.push({id,title:title.trim()||'Track '+id,program,channels:[...channels],notes,endpoint:tick,on:notes.length>0,arp:false,solo:false});
 }
 tempos.sort((a,b)=>a.t-b.t);
 let unique=[];
 for(let t of tempos){if(unique.length&&unique[unique.length-1].t===t.t)unique[unique.length-1]=t;else unique.push(t);}
 function toSec(t){let sec=0,at=0,mpq=500000;for(const c of unique){if(c.t>t)break;sec+=(c.t-at)*mpq/division/1000000;at=c.t;mpq=c.v;}return sec+(t-at)*mpq/division/1000000;}
 const fileEnd=toSec(Math.max(1,...tracks.map(x=>x.endpoint)));
 for(let tr of tracks)for(let n of tr.notes){n.at=toSec(n.tick);n.until=toSec(n.tick+n.len);}
 const audibleEnd=tracks.reduce((total,tr)=>tr.notes.reduce((m,n)=>Math.max(m,n.until),total),0);
 const length=Math.max(1,Math.min(fileEnd,audibleEnd+0.75));
 const bpm=60000000/(unique[unique.length-1].v||500000);
 return {tracks,length,bpm,format,sig,bytes:size,division,tempoMap:unique};
}
function setStatus(text){$('status').textContent=text;}
function selectSong(index){
 if(playing)stopPlayback();
 let item=library[index];
 if(!item)return;
 setStatus('DECODING '+item.title.toUpperCase()+'…');
 try{
   let compressed=decode64(item.data),buffer=pako.inflate(compressed);
   if(buffer.length!==item.bytes)throw Error('MIDI length mismatch');
   let parsed=parseMidi(buffer);
   if(parsed.tracks.length!==item.tracks)throw Error('MIDI track count mismatch');
   song=parsed;current=item;position=0;randomSeed=11;
   const melodic=song.tracks.filter(x=>x.notes.length>=50&&!x.channels.includes(9));
   const count=Math.min(2,melodic.length);
   melodic.sort((a,b)=>b.notes.length-a.notes.length);
   melodic.slice(0,count).forEach(tr=>tr.arp=true);
   let lead=song.tracks.find(t=>t.notes.length>0&&!t.channels.includes(9))||song.tracks.find(t=>t.notes.length);
   focus=lead?lead.id:0;
   $('song').value=String(index);
   $('speed').value='1';speed=1;
   renderTrackList();
   rebuild();
   $('seek').value=0;$('seek').max=song.length;
   $('duration').textContent=clock(song.length);
   $('originalNotes').textContent=song.tracks.reduce((a,t)=>a+t.notes.length,0).toLocaleString();
   $('tempo').textContent=Math.round(song.bpm);
   $('trackCount').textContent=song.tracks.length;
   $('time').textContent='0:00 / '+clock(song.length);
   $('play').disabled=false;
   setStatus('OFFLINE · '+item.bytes.toLocaleString()+' MIDI BYTES');
   draw();
 } catch(error){setStatus('ERROR · '+error.message);console.error(error);$('play').disabled=true;}
}
function rand(i){let x=(i+randomSeed*2654435761)>>>0;x^=x>>>16;x=Math.imul(x,2246822507);x^=x>>>13;x=Math.imul(x,3266489909);x^=x>>>16;return(x>>>0)/4294967296;}
function optsForTrack(t){
 return {program:t.program[t.channels.find(c=>c!==9)]||0};
}
function makeEvent(n,tr,at,until,pitch,vel,kind){
 return {at,until,pitch,vel,ch:n.ch,track:tr.id,program:tr.program[n.ch]||0,kind:kind||'',src:n.tick};
}
function makeArp(tr) {
 const ns=tr.notes;
 const step=(60/song.bpm)/(Number(values.arp)/4);
 const notes=[];
 for(let i=0;i<ns.length;){
   const first=ns[i],members=[first];
   let j=i+1;
   while(j<ns.length&&ns[j].at-first.at<Math.min(step*.34,.07)&&members.length<16){members.push(ns[j]);j++;}
   const dur=Math.min(2.7,Math.max(...members.map(n=>n.until-first.at)));
   if(dur<step*.78){for(const n of members)notes.push(makeEvent(n,tr,n.at,n.until,n.pitch,n.vel));i=j;continue;}
   let pitches=[...new Set(members.map(n=>n.pitch))].sort((a,b)=>a-b);
   if(pitches.length===1){const p=pitches[0];pitches=[p,p+7,p+12];}
   let count=Math.min(32,Math.max(1,Math.ceil(dur/step)));
   const direction=values.direction;
   for(let k=0;k<count;k++){
     let ix=k%pitches.length;
     if(direction==='down')ix=pitches.length-1-ix;
     else if(direction==='updown'){
       const span=Math.max(1,pitches.length*2-2),v=k%span;
       ix=v<pitches.length?v:span-v;
     }else if(direction==='random')ix=Math.floor(rand((tr.id+19)*100000+i*37+k)*pitches.length);
     const at=first.at+step*k;
     if(at>=song.length)break;
     notes.push(makeEvent(first,tr,at,Math.min(song.length,at+step*(1-.64*values.gate/100)),pitches[ix],Math.max(24,Math.round(first.vel*.78)),'arp'));
   }
   i=j;
 }
 return notes;
}
function transform(n,tr,nidx,all){
 let amount=values.glitch/100;
 const seed=tr.id*16777213+(n.src||0)*11+nidx*7+(n.pitch||0)*101;
 let r=rand(seed);
 if(amount&&r<amount*.125)return;
 let at=n.at,until=n.until,pitch=n.pitch,vel=n.vel;
 let dur=Math.max(.022,until-at);
 if(n.ch!==9)dur=Math.max(.024,dur*(1-.84*values.gate/100));
 until=Math.min(song.length,at+dur);
 if(amount&&r>1-amount*.15&&n.ch!==9)pitch=Math.min(108,pitch+(rand(seed+53)>.5?12:-12));
 const isStutter=amount&&rand(seed+17)<amount*(n.ch===9?.44:.32);
 if(isStutter){
   const count=2+Math.floor(rand(seed+29)*4);
   const total=n.ch===9?Math.min(.26, Math.max(.08,60/song.bpm/2)):Math.min(.42,dur);
   for(let k=0;k<count;k++){
      let x=at+k*total/count;
      if(x>song.length)break;
      all.push({...n,at:x,until:Math.min(song.length,x+Math.max(.024,total/count*.66)),pitch,vel:Math.max(20,Math.floor(vel*(1-k*.12))),kind:'stutter'});
   }
 }else all.push({...n,at,until,pitch,vel});
}
function rebuild(){
 if(!song)return;
 let all=[];
 for(let tr of song.tracks){
   if(!tr.on)continue;
   const raw=tr.arp&&values.arp!=='off'&&!tr.channels.includes(9)?makeArp(tr):tr.notes.map(n=>makeEvent(n,tr,n.at,n.until,n.pitch,n.vel));
   for(let i=0;i<raw.length;i++)transform(raw[i],tr,i,all);
 }
 if(values.kick){
   const beat=60/song.bpm;
   for(let i=0;i<song.length/beat;i++){
     const at=i*beat;
     all.push({track:-1,ch:9,pitch:36,vel:115,at,until:at+.12,program:0,kind:'motor',src:i});
     if(i%2===1)all.push({track:-1,ch:9,pitch:42,vel:61,at:at+beat*.5,until:at+beat*.5+.06,program:0,kind:'motor',src:i});
   }
 }
 all.sort((a,b)=>a.at-b.at);
 events=all;
 groups=new Map();
 for(let e of all){if(!groups.has(e.track))groups.set(e.track,[]);groups.get(e.track).push(e);}
 $('generatedNotes').textContent=events.length.toLocaleString();
 resetCursor();
 if(audio)applyFx();
 draw();
}
function resetCursor(){
 let p=playing?now():position,lo=0,hi=events.length;
 while(lo<hi){let mid=(lo+hi)>>1;if(events[mid].at<p-.07)lo=mid+1;else hi=mid;}cursor=lo;
}
function renderTrackList(){
 const parent=$('tracks');parent.replaceChildren();
 const select=$('focus');select.replaceChildren();
 for(let tr of song.tracks){
  const row=document.createElement('div');row.className='track';
  const enabled=document.createElement('input');enabled.type='checkbox';enabled.checked=tr.on;
  enabled.title='Enable track';enabled.onchange=()=>{tr.on=enabled.checked;rebuild();};
  const info=document.createElement('div');info.className='trackname';
  const title=document.createElement('strong');title.textContent=tr.id+' · '+tr.title;
  const desc=document.createElement('small');desc.textContent=tr.notes.length+' notes · '+(tr.channels.includes(9)?'Drum lane':'Instrument lane');
  info.append(title,desc);
  const solo=document.createElement('button');solo.textContent='S';solo.title='Solo';solo.className='minibtn';
  solo.onclick=()=>{for(let t of song.tracks)t.on=t===tr;renderTrackList();rebuild();};
  const ar=document.createElement('button');ar.textContent='ARP';ar.title='Arpeggiate this track';ar.className='minibtn'+(tr.arp?' active':'');
  ar.disabled=tr.channels.includes(9)||!tr.notes.length;
  ar.onclick=()=>{tr.arp=!tr.arp;renderTrackList();rebuild();};
  const view=document.createElement('button');view.textContent='▣';view.title='Show notes';view.className='minibtn';
  view.onclick=()=>{focus=tr.id;select.value=String(focus);draw();};
  row.append(enabled,info,solo,ar,view);parent.append(row);
  if(tr.notes.length){let op=document.createElement('option');op.value=tr.id;op.textContent=tr.id+' '+tr.title;select.append(op);}
 }
 select.value=String(focus);
}
function setTrackMode(mode){
 for(let t of song.tracks)t.on=mode==='all'?t.notes.length>0:mode==='none'?false:mode==='drums'?t.channels.includes(9):(!t.channels.includes(9)&&t.notes.length>0);
 renderTrackList();rebuild();
}
function renderSettings(){
 for(const id of ranges){$(id).value=values[id];$(id+'Value').textContent=String(values[id])+'%';}
 $('arp').value=values.arp;$('direction').value=values.direction;$('kick').checked=values.kick;$('sub').checked=values.sub;
 for(const btn of document.querySelectorAll('[data-preset]'))btn.classList.toggle('selected',btn.dataset.preset===preset);
}
function applyPreset(id){
 preset=id;Object.assign(values,presets[id]);renderSettings();
 if(song){
   const candidates=song.tracks.filter(t=>t.notes.length>80&&!t.channels.includes(9)).sort((a,b)=>b.notes.length-a.notes.length);
   for(const t of song.tracks)t.arp=false;
   if(id!=='original')candidates.slice(0,id==='glitch'?3:2).forEach(t=>t.arp=true);
   renderTrackList();rebuild();
 }
}
function makeDistortion(amount){
 const out=new Float32Array(2048),k=1+amount*amount*220;
 for(let i=0;i<out.length;i++){let x=i*2/(out.length-1)-1;out[i]=((3+k)*x*20*Math.PI/180)/(Math.PI+k*Math.abs(x));}
 return out;
}
function makeCrush(amount){
 const out=new Float32Array(2048),bits=16-Math.floor(amount*12),levels=Math.pow(2,bits);
 for(let i=0;i<out.length;i++){let x=i*2/(out.length-1)-1;out[i]=Math.max(-1,Math.min(1,Math.round(x*levels)/levels));}
 return out;
}
function ensureAudio(){
 if(audio)return;
 const C=window.AudioContext||window.webkitAudioContext;
 if(!C)throw Error('Web Audio unavailable');
 audio=new C();
 synthBus=audio.createGain();drumBus=audio.createGain();duck=audio.createGain();
 synthBus.connect(duck);
 const input=audio.createGain();
 duck.connect(input);drumBus.connect(input);
 clean=audio.createGain();dirty=audio.createGain();
 driveNode=audio.createWaveShaper();crushNode=audio.createWaveShaper();
 compressor=audio.createDynamicsCompressor();compressor.threshold.value=-21;compressor.ratio.value=5;compressor.attack.value=.005;compressor.release.value=.12;
 master=audio.createGain();master.gain.value=.42;
 input.connect(clean).connect(compressor);
 input.connect(driveNode).connect(crushNode).connect(dirty).connect(compressor);
 delaySend=audio.createGain();delayNode=audio.createDelay(2);feedback=audio.createGain();
 input.connect(delaySend).connect(delayNode);delayNode.connect(feedback).connect(delayNode);delayNode.connect(compressor);
 compressor.connect(master).connect(audio.destination);
 noise=audio.createBuffer(1,Math.round(audio.sampleRate*.45),audio.sampleRate);
 let n=noise.getChannelData(0);for(let i=0;i<n.length;i++)n[i]=Math.random()*2-1;
 applyFx();
}
function applyFx(){
 if(!audio)return;
 const d=values.drive/100,b=values.crush/100,mix=Math.max(d,b*.8);
 driveNode.curve=makeDistortion(d);driveNode.oversample='none';
 crushNode.curve=makeCrush(b);crushNode.oversample='none';
 clean.gain.setTargetAtTime(1-mix*.72,audio.currentTime,.025);
 dirty.gain.setTargetAtTime(mix*.78,audio.currentTime,.025);
 delaySend.gain.setTargetAtTime(values.delay/100*.38,audio.currentTime,.04);
 const beat=song?60/song.bpm:.4;
 delayNode.delayTime.setTargetAtTime(Math.min(1.5,beat*.75),audio.currentTime,.04);
 feedback.gain.setTargetAtTime(.15+values.delay/100*.38,audio.currentTime,.05);
}
function addNode(n){live.push(n);if(live.length>3500)live=live.slice(-2000);}
function tone(e,when){
 const dur=Math.min(5,Math.max(.025,(e.until-e.at)/speed));
 const low=e.pitch<52,program=e.program;
 const osc=audio.createOscillator(),f=audio.createBiquadFilter(),amp=audio.createGain();
 let waveform='sawtooth';
 if(program<8)waveform='triangle';
 else if(program>=16&&program<=23)waveform='sine';
 else if(program>=80&&program<=87)waveform='square';
 osc.type=waveform;
 const hz=440*Math.pow(2,(e.pitch-69)/12);
 osc.frequency.setValueAtTime(hz,when);
 if(e.kind==='stutter'){osc.frequency.setValueAtTime(hz*1.5,when);osc.frequency.exponentialRampToValueAtTime(hz,when+.019);}
 f.type='lowpass';let cutoff=14000-values.filter*110+e.vel*17;
 f.frequency.setValueAtTime(Math.max(240,Math.min(17000,cutoff)),when);
 f.Q.value=1.5+values.filter/40;
 const volume=Math.min(.11,(low?.054:.046)*e.vel/127);
 amp.gain.setValueAtTime(.0001,when);
 amp.gain.exponentialRampToValueAtTime(Math.max(.001,volume),when+.009);
 amp.gain.setValueAtTime(Math.max(.001,volume*.78),when+Math.max(.011,dur-.047));
 amp.gain.exponentialRampToValueAtTime(.0001,when+dur+.023);
 osc.connect(f).connect(amp).connect(synthBus);
 osc.start(when);osc.stop(when+dur+.035);addNode(osc);
 if(low&&values.sub){
   const sub=audio.createOscillator(),gain=audio.createGain();
   sub.type='sine';sub.frequency.setValueAtTime(Math.max(35,hz*.5),when);
   gain.gain.setValueAtTime(.0001,when);gain.gain.linearRampToValueAtTime(volume*.43,when+.012);
   gain.gain.exponentialRampToValueAtTime(.0001,when+dur+.028);
   sub.connect(gain).connect(synthBus);sub.start(when);sub.stop(when+dur+.04);addNode(sub);
 }
}
function kick(vel,when,pitch){
 const osc=audio.createOscillator(),amp=audio.createGain();
 osc.type='sine';osc.frequency.setValueAtTime(pitch>=41?195:155,when);
 osc.frequency.exponentialRampToValueAtTime(pitch>=41?65:43,when+.16);
 amp.gain.setValueAtTime(.0001,when);amp.gain.linearRampToValueAtTime(.56*vel,when+.004);
 amp.gain.exponentialRampToValueAtTime(.0001,when+.23);
 osc.connect(amp).connect(drumBus);osc.start(when);osc.stop(when+.235);addNode(osc);
 duck.gain.cancelScheduledValues(when);duck.gain.setValueAtTime(.68,when);duck.gain.linearRampToValueAtTime(1,when+.19);
}
function noisy(vel,when,hi,duration){
 const src=audio.createBufferSource(),f=audio.createBiquadFilter(),amp=audio.createGain();
 src.buffer=noise;f.type='highpass';f.frequency.value=hi?5500:700;
 amp.gain.setValueAtTime(.0001,when);amp.gain.linearRampToValueAtTime((hi?.22:.32)*vel,when+.004);
 amp.gain.exponentialRampToValueAtTime(.0001,when+duration);
 src.connect(f).connect(amp).connect(drumBus);src.start(when);src.stop(when+duration+.008);addNode(src);
}
function playDrum(e,when){
 const n=e.pitch,v=e.vel/127;
 if(n===35||n===36||n===41||n===45)kick(v,when,n);
 else if([42,44,46,49,51,53,57,59].includes(n))noisy(v,when,true,[49,51,53,57,59].includes(n)?.3:.07);
 else noisy(v,when,false,.17);
}
function now(){return playing?Math.max(0,Math.min(song.length,startPosition+(audio.currentTime-startTime)*speed)):position;}
function tick(){
 if(!playing)return;
 let t=now(),windowEnd=Math.min(song.length,t+.19);
 while(cursor<events.length&&events[cursor].at<=windowEnd){
   let e=events[cursor++];if(e.at<t-.09)continue;
   let when=Math.max(audio.currentTime+.008,audio.currentTime+(e.at-t)/speed);
   if(e.ch===9)playDrum(e,when);else tone(e,when);
 }
 position=t;$('seek').value=t;$('time').textContent=clock(t)+' / '+clock(song.length);
 if(t>=song.length)pause();
 if(cursor%4===0)draw();
}
function stopVoices(){for(const x of live){try{x.stop();}catch(_){}}live=[];}
async function start(){
 if(!song)return;
 ensureAudio();
 await audio.resume();
 if(playing)return;
 speed=+$('speed').value;
 resetCursor();
 playing=true;startPosition=position;startTime=audio.currentTime;
 $('play').textContent='Ⅱ Pause';
 timer=setInterval(tick,35);tick();draw();
}
function pause(){
 if(!playing)return;
 position=now();playing=false;clearInterval(timer);stopVoices();$('play').textContent='▶ Play';draw();
}
function stopPlayback(){if(playing)pause();position=0;resetCursor();$('seek').value=0;draw();}
function seek(val){let was=playing;if(was)pause();position=Math.min(song.length,Math.max(0,val));resetCursor();$('seek').value=position;$('time').textContent=clock(position)+' / '+clock(song.length);draw();if(was)start();}
function draw(){
 const cvs=$('roll'),ctx=cvs.getContext('2d');if(!ctx)return;
 const w=Math.max(300,cvs.clientWidth),h=cvs.clientHeight||320,r=window.devicePixelRatio||1;
 cvs.width=w*r;cvs.height=h*r;ctx.setTransform(r,0,0,r,0,0);
 ctx.fillStyle='#11161c';ctx.fillRect(0,0,w,h);
 if(!song)return;
 const span=+$('span').value,t=now(),start=Math.max(0,Math.min(song.length-span,t-1.6)),left=38,width=w-left-12;
 const all=groups.get(focus)||[],visible=all.filter(e=>e.until>=start&&e.at<=start+span);
 const min=visible.length?Math.max(0,Math.min(...visible.map(e=>e.pitch))-4):36;
 const max=visible.length?Math.min(127,Math.max(...visible.map(e=>e.pitch))+4):85;
 const range=Math.max(12,max-min+1);
 for(let k=0;k<=span;k++){
   let x=left+k/span*width;ctx.fillStyle=k%4?'#242d38':'#394854';ctx.fillRect(x,0,1,h);
   if(k%4===0){ctx.fillStyle='#a5b5c0';ctx.font='10px system-ui';ctx.fillText(clock(start+k),x+3,12);}
 }
 for(let p=min;p<=max;p++)if(p%12===0){let y=h-(p-min+1)/range*h;ctx.fillStyle='#293744';ctx.fillRect(left,y,width,1);ctx.fillStyle='#95aabb';ctx.font='10px system-ui';ctx.fillText(noteLabel(p),3,y+11);}
 for(let e of visible){let x=left+(e.at-start)/span*width,y=h-(e.pitch-min+1)/range*h;
   ctx.fillStyle=e.kind==='stutter'?'#ff87c5':e.kind==='arp'?'#8aeedb':e.ch===9?'#ffc37e':'#c8ed6a';
   ctx.fillRect(x,y,Math.max(2,(e.until-e.at)/span*width),Math.max(2,h/range-1));
 }
 const x=left+(t-start)/span*width;
 if(x>=left&&x<=w){ctx.fillStyle='white';ctx.fillRect(x,0,2,h);}
}
function exportMidi(){
 if(!song)return;
 const ppq=480,mpq=Math.round(60000000/song.bpm);
 const bytes=[];
 function put16(v,out){out.push(v>>>8&255,v&255);}
 function put32(v,out){out.push(v>>>24&255,v>>>16&255,v>>>8&255,v&255);}
 function chunk(bytesOut){const tr=[77,84,114,107];put32(bytesOut.length,tr);return tr.concat(bytesOut);}
 function varlen(n){let b=n&127,res=[];while((n>>>=7)>0){b<<=8;b|=(n&127)|128;}while(true){res.push(b&255);if(b&128)b>>>=8;else break;}return res;}
 const header=[77,84,104,100,0,0,0,6,0,1];const enabled=[...new Set(events.map(e=>e.track))].sort((a,b)=>a-b);
 put16(enabled.length+1,header);put16(ppq,header);
 const tempo=[0,255,81,3,mpq>>>16&255,mpq>>>8&255,mpq&255,0,255,47,0];
 bytes.push(...header,...chunk(tempo));
 for(const track of enabled){
   const raw=[];
   for(const e of events)if(e.track===track){
     const startTick=Math.max(0,Math.round(e.at*ppq*song.bpm/60));
     const endTick=Math.max(startTick+1,Math.round(e.until*ppq*song.bpm/60));
     raw.push({tick:startTick,data:[0x90|(e.ch&15),e.pitch&127,e.vel&127]});
     raw.push({tick:endTick,data:[0x80|(e.ch&15),e.pitch&127,0]});
   }
   raw.sort((a,b)=>a.tick-b.tick||((a.data[0]&240)-(b.data[0]&240)));
   const out=[],name=track===-1?'MOTOR KICK':'TRACK '+track;
   out.push(0,255,3,name.length,...[...name].map(c=>c.charCodeAt(0)));
   let last=0;for(const e of raw){out.push(...varlen(e.tick-last),...e.data);last=e.tick;}
   out.push(0,255,47,0);
   for(const byte of chunk(out))bytes.push(byte);
 }
 const blob=new Blob([new Uint8Array(bytes)],{type:'audio/midi'});
 const url=URL.createObjectURL(blob),a=document.createElement('a');
 a.href=url;a.download='NIN_'+current.title.replace(/[^a-z0-9]+/gi,'_')+'_'+preset+'_remix.mid';
 document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),30000);
 setStatus('REMIX MIDI EXPORTED · '+events.length.toLocaleString()+' NOTES');
}
function bind(){
 const select=$('song');for(let i=0;i<library.length;i++){let opt=document.createElement('option');opt.value=i;opt.textContent=(i+1)+'. '+library[i].title;select.append(opt);}
 $('libraryCount').textContent=library.length+' songs embedded';
 select.onchange=()=>selectSong(+select.value);
 $('play').onclick=()=>playing?pause():start().catch(e=>setStatus('AUDIO ERROR · '+e.message));
 $('stop').onclick=stopPlayback;
 $('seek').oninput=e=>seek(+e.target.value);
 $('speed').onchange=()=>{let was=playing;if(was)pause();speed=+$('speed').value;if(was)start();};
 $('all').onclick=()=>setTrackMode('all');$('none').onclick=()=>setTrackMode('none');$('onlyDrums').onclick=()=>setTrackMode('drums');$('onlyMelody').onclick=()=>setTrackMode('melody');
 $('focus').onchange=()=>{focus=+$('focus').value;draw();};
 $('span').onchange=draw;$('roll').onclick=e=>{let box=$('roll').getBoundingClientRect(),span=+$('span').value,start=Math.max(0,Math.min(song.length-span,now()-1.6)),fraction=(e.clientX-box.left-38)/(box.width-50);if(fraction>=0&&fraction<=1)seek(start+fraction*span);};
 for(const id of ranges)$(id).oninput=e=>{values[id]=+e.target.value;$(id+'Value').textContent=values[id]+'%';if(id==='glitch'||id==='gate')rebuild();else if(audio)applyFx();};
 $('arp').onchange=e=>{values.arp=e.target.value;rebuild();};
 $('direction').onchange=e=>{values.direction=e.target.value;rebuild();};
 $('kick').onchange=e=>{values.kick=e.target.checked;rebuild();};
 $('sub').onchange=e=>{values.sub=e.target.checked;};
 for(const btn of document.querySelectorAll('[data-preset]'))btn.onclick=()=>applyPreset(btn.dataset.preset);
 $('reroll').onclick=()=>{randomSeed+=31;rebuild();setStatus('GLITCH PATTERN RE-SEEDED #'+randomSeed);};
 $('export').onclick=exportMidi;
 $('save').onclick=()=>{try{localStorage.setItem('nin-lab-'+current.title,JSON.stringify({values,preset,randomSeed,arpTracks:song.tracks.filter(x=>x.arp).map(x=>x.id)}));setStatus('PATCH SAVED IN BROWSER');}catch(e){setStatus('LOCAL SAVE UNAVAILABLE');}};
 $('load').onclick=()=>{try{let raw=localStorage.getItem('nin-lab-'+current.title);if(!raw)throw Error('No patch saved');let data=JSON.parse(raw);Object.assign(values,data.values);preset=data.preset;randomSeed=data.randomSeed;for(let tr of song.tracks)tr.arp=data.arpTracks.includes(tr.id);renderSettings();renderTrackList();rebuild();setStatus('PATCH LOADED');}catch(e){setStatus('NO SAVED PATCH FOR THIS SONG');}};
 window.addEventListener('resize',draw);
 document.addEventListener('keydown',e=>{if(e.code==='Space'&&!['INPUT','SELECT','BUTTON','TEXTAREA'].includes(document.activeElement.tagName)){e.preventDefault();if(playing)pause();else start().catch(console.error);}});
 renderSettings();selectSong(0);
}
try{if(typeof pako==='undefined'||typeof pako.inflate!=='function')throw Error('Embedded decompressor failed');bind();}
catch(error){console.error(error);setStatus('ERROR · '+error.message);}
})();
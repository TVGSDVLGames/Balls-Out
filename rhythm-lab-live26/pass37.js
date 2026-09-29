(()=>{
 const PUMP_MS=25;
 const AHEAD_SEC=0.18;
 const START_LEAD=0.065;
 const LATE_TOLERANCE=0.025;
 let ticker=null;
 const scheduledSources=new Set();
 const stats=window.DM3AGTimingStats={scheduled:0,skipped:0,pumps:0,lateSchedules:0,minLeadMs:Infinity,maxLeadMs:0,lastLeadMs:0};

 function swingRatioNow(){
  const amount=Math.max(0,Math.min(100,+document.getElementById('swing')?.value||0));
  if(typeof window.DM3AGSwingRatio==='function')return window.DM3AGSwingRatio(amount);
  return .5+(amount/100)*.25;
 }
 function stepDuration(st){
  const bpm=Math.max(20,+document.getElementById('bpm')?.value||120);
  const base=(60/bpm)/4,sw=swingRatioNow();
  return base*((st&1)?(1-sw)*2:sw*2);
 }
 function cleanupScheduledSources(nowStop=false){
  for(const rec of [...scheduledSources]){
   try{rec.src.stop(nowStop&&ctx?ctx.currentTime:0)}catch(_){}
   try{rec.src.disconnect();rec.g.disconnect();rec.tail?.disconnect()}catch(_){}
   scheduledSources.delete(rec);
  }
 }
 function connectScheduledOutput(c,g,panCode){
  const [lg,rg]=hardwarePanGains(panCode),merger=c.createChannelMerger(2),gl=c.createGain(),gr=c.createGain();
  gl.gain.value=lg;gr.gain.value=rg;g.connect(gl);g.connect(gr);gl.connect(merger,0,0);gr.connect(merger,0,1);
  let tail=merger;
  if(document.getElementById('analogModel')?.checked){
   const f1=c.createBiquadFilter(),f2=c.createBiquadFilter(),trim=c.createGain();
   f1.type='lowpass';f2.type='lowpass';f1.frequency.value=17500;f2.frequency.value=17500;f1.Q.value=.48;f2.Q.value=.48;trim.gain.value=1.06;
   tail.connect(f1);f1.connect(f2);f2.connect(trim);tail=trim;
  }
  tail.connect(c.destination);
  return {tail,lg,rg};
 }
 const bufferCache=new Map();
 function audioBufferFor(ptr){
  const key=modelKey+':'+ptr;
  let b=bufferCache.get(key);if(b)return b;
  const pcm=decodeDM3AGVoice(ptr);if(!pcm.length)return null;
  b=ctx.createBuffer(1,pcm.length,48000);b.copyToChannel(pcm,0);bufferCache.set(key,b);return b;
 }
 function scheduleIOSVoice(ptr,rate,gain,panCode,bus,slot,when){
  const c=ctx;if(!c||c.state==='closed')return;
  const b=audioBufferFor(ptr);if(!b)return;
  const at=Math.max(c.currentTime+.002,when);
  const old=iosHardwareSlots[slot&15];
  if(old?.src){try{old.src.stop(at)}catch(_){}}
  const src=c.createBufferSource(),g=c.createGain();src.buffer=b;src.playbackRate.value=Math.max(.1,Math.min(4,rate||1));g.gain.value=Math.max(0,Math.min(1,gain||1));src.connect(g);
  const route=connectScheduledOutput(c,g,panCode),rec={src,g,route,tail:route.tail};iosHardwareSlots[slot&15]=rec;scheduledSources.add(rec);
  src.onended=()=>{if(iosHardwareSlots[slot&15]===rec)iosHardwareSlots[slot&15]=null;scheduledSources.delete(rec);try{src.disconnect();g.disconnect();route.tail.disconnect()}catch(_){}};
  src.start(at);
 }

 if(typeof DM3AGLive!=='undefined'){
  DM3AGLive.prototype.triggerAt=function(m,when){
   this.pending??=[];this.pending.push({when:+when||this.ctx.currentTime,m});this.pending.sort((a,b)=>a.when-b.when);
  };
  const oldSetRom=DM3AGLive.prototype.setRom;
  DM3AGLive.prototype.setRom=function(u8){this.pending=[];return oldSetRom.call(this,u8)};
  const oldPanic=DM3AGLive.prototype.panic;
  DM3AGLive.prototype.panic=function(){this.pending=[];return oldPanic.call(this)};
  DM3AGLive.prototype.process=function(e){
   const L=e.outputBuffer.getChannelData(0),R=e.outputBuffer.numberOfChannels>1?e.outputBuffer.getChannelData(1):L,sr=this.ctx.sampleRate;
   const blockStart=Number.isFinite(e.playbackTime)?e.playbackTime:this.ctx.currentTime;
   const useFilter=document.getElementById('analogModel')?.checked!==false,fc=17500,a=Math.exp(-2*Math.PI*fc/sr),b=1-a;
   this.pending??=[];
   for(let i=0;i<L.length;i++){
    const sampleTime=blockStart+i/sr+.5/sr;
    while(this.pending.length&&this.pending[0].when<=sampleTime){const q=this.pending.shift();this.trigger(q.m)}
    let o1l=0,o1r=0,o2l=0,o2r=0;
    for(const v of this.voices){if(!v.active)continue;const [lg,rg]=hardwarePanGains(v.panCode),x=v.hold*v.gain;if(v.bus===2){o2l+=x*lg;o2r+=x*rg}else{o1l+=x*lg;o1r+=x*rg}v.phase+=v.rate;while(v.phase>=1&&v.active){v.phase-=1;v.hold=this.readNext(v)}}
    let l=o1l+o2l,r=o1r+o2r;
    if(useFilter){this.f1[0][0]=b*l+a*this.f1[0][0];this.f1[0][1]=b*r+a*this.f1[0][1];this.f2[0][0]=b*this.f1[0][0]+a*this.f2[0][0];this.f2[0][1]=b*this.f1[0][1]+a*this.f2[0][1];l=this.f2[0][0]*1.06;r=this.f2[0][1]*1.06}
    L[i]=Math.max(-1,Math.min(1,l));R[i]=Math.max(-1,Math.min(1,r));
   }
   this.voices=this.voices.filter(v=>v.active);for(let i=0;i<16;i++)if(this.slots[i]&&!this.slots[i].active)this.slots[i]=null;
  };
 }

 function schedulePadAt(i,velocity,when){
  if(!padAudible(i)||!ctx)return;
  const p=padState[i],v=model.voices[p.voice]||model.voices[0];let comps=modelKey==='sr16'?srComponents(v,velocity):[{ptr:v.ptr}];if(!comps.length)return;
  const norm=1/Math.sqrt(comps.length),rate=Math.pow(2,p.tune/12),gain=(p.vol/127)*velocityGain(velocity)*norm,panCode=panCodeFromUI(p.pan),slot=slotForPad(i),bus=p.bus||1;
  if(IS_IOS){
   for(const c of comps)scheduleIOSVoice(c.ptr,rate*(modelKey==='sr16'?srPitchRatio(c):1),gain,panCode,bus,slot,when);
  }else if(engine){
   const baseRate=(48000/ctx.sampleRate)*rate;
   if(modelKey==='sr16'&&p.label.toUpperCase().includes('HAT'))engine.triggerAt({stop:true,slot:2},when);
   for(const c of comps)engine.triggerAt({ptr:c.ptr,rate:baseRate*(modelKey==='sr16'?srPitchRatio(c):1),gain,panCode,bus,slot},when);
  }
  stats.scheduled++;
 }
 function scheduleVisual(st,when){
  const wait=Math.max(0,(when-(ctx?.currentTime||0))*1000);
  setTimeout(()=>{if(playing&&!document.hidden)showPlayhead(st)},wait);
 }
 function scheduleStep(st,when){
  const dur=stepDuration(st);scheduleVisual(st,when);
  for(let p=0;p<padState.length;p++){
   const v=pattern[p]?.[st]||0,m=metaAt(p,st);if(!v||Math.random()>(m.prob??1))continue;
   const vel=v===2?127:92;schedulePadAt(p,vel,when);
   if((m.ratchet||1)>1)schedulePadAt(p,Math.max(1,vel-8),when+dur*.5);
  }
  return dur;
 }
 function advanceWithoutSound(){const d=stepDuration(stepIndex);nextStepTime+=d;stepIndex=(stepIndex+1)%patternLength;stats.skipped++}
 function pump(){
  if(!playing||!ctx||document.hidden)return;
  stats.pumps++;const now=ctx.currentTime;
  let guard=0;while(nextStepTime<now-LATE_TOLERANCE&&guard++<128)advanceWithoutSound();
  guard=0;
  while(nextStepTime<now+AHEAD_SEC&&guard++<128){
   const lead=(nextStepTime-now)*1000;stats.lastLeadMs=lead;stats.minLeadMs=Math.min(stats.minLeadMs,lead);stats.maxLeadMs=Math.max(stats.maxLeadMs,lead);if(lead<0)stats.lateSchedules++;
   const st=stepIndex,d=scheduleStep(st,nextStepTime);nextStepTime+=d;stepIndex=(stepIndex+1)%patternLength;
  }
 }
 function startTicker(){stopTicker();pump();ticker=setInterval(pump,PUMP_MS);seqTimer=ticker}
 function stopTicker(){if(ticker!=null){clearInterval(ticker);ticker=null}if(seqTimer!=null){clearTimeout(seqTimer);seqTimer=null}}
 window.DM3AGTimingPump=pump;

 scheduleTick=function(){if(!playing||!ctx)return;startTicker()};
 play=async function(){
  if(await startAudio()){
   stopTicker();cleanupScheduledSources(true);if(engine?.pending)engine.pending=[];
   playing=true;stepIndex=0;nextStepTime=ctx.currentTime+START_LEAD;
   stats.scheduled=stats.skipped=stats.pumps=stats.lateSchedules=0;stats.minLeadMs=Infinity;stats.maxLeadMs=stats.lastLeadMs=0;
   startTicker();
  }
 };
 stop=function(){
  playing=false;stopTicker();cleanupScheduledSources(true);if(engine?.pending)engine.pending=[];
  document.querySelectorAll('.step,.seq .hdr[data-s]').forEach(e=>e.classList.remove('playhead'));
  if(IS_IOS)panicIOSSlots();if(engine?.panic)engine.panic();
 };

 document.addEventListener('visibilitychange',()=>{if(document.hidden){stopTicker();cleanupScheduledSources(true);if(engine?.pending)engine.pending=[]}},true);
 window.addEventListener('pagehide',()=>{stopTicker();cleanupScheduledSources(true);if(engine?.pending)engine.pending=[]},true);
 window.addEventListener('beforeunload',()=>{stopTicker();cleanupScheduledSources(true);if(engine?.pending)engine.pending=[]},true);
})();
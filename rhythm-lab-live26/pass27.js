(()=>{
const isiOS=/iPad|iPhone|iPod/.test(navigator.userAgent)||(navigator.platform==='MacIntel'&&navigator.maxTouchPoints>1);
if(!isiOS)return;

const gate=document.createElement('div');
gate.id='iosAudioGate';
gate.setAttribute('role','dialog');
gate.setAttribute('aria-modal','true');
gate.innerHTML='<div class="iosAudioCard"><h2>Start Audio</h2><p>iPhone and iPad require one direct tap before Web Audio can run.</p><button id="iosAudioStart" type="button">TAP TO START AUDIO</button><div class="iosAudioState" id="iosAudioState">AUDIO LOCKED</div></div>';
document.body.appendChild(gate);

const btn=document.getElementById('iosAudioStart');
const state=document.getElementById('iosAudioState');
let unlocking=false;

function setEngineText(t,cls){
  const es=document.getElementById('engineStat');
  if(es){es.textContent=t;if(cls)es.className=cls;}
}
function lock(){
  document.body.classList.add('iosAudioLocked');
  if(state)state.textContent='AUDIO LOCKED';
  setEngineText('TAP TO START','warn');
}
function unlock(ev){
  if(unlocking)return;
  unlocking=true;
  if(ev){try{ev.preventDefault()}catch(_){} try{ev.stopPropagation()}catch(_){}}
  if(state)state.textContent='STARTING AUDIO…';

  try{
    if(navigator.audioSession&&'type' in navigator.audioSession){
      try{navigator.audioSession.type='playback'}catch(_){}
    }

    // IMPORTANT: call the app's own synchronous iOS initializer in the user gesture.
    const c=ensureIOSContextSync();

    // Prime WebKit with an actual source start while user activation is still live.
    try{
      const b=c.createBuffer(1,128,c.sampleRate||48000);
      const src=c.createBufferSource();
      const g=c.createGain();
      src.buffer=b;
      g.gain.value=0.00001;
      src.connect(g);
      g.connect(c.destination);
      src.start(0);
    }catch(_){}

    // Do not await resume(). WebKit can leave this promise pending.
    try{c.resume()}catch(_){}

    // Release the UI synchronously. Pad clicks call ensureIOSContextSync again
    // in their own trusted gesture, so WebKit gets another resume opportunity.
    document.body.classList.remove('iosAudioLocked');
    if(state)state.textContent='AUDIO READY';
    setEngineText(c.state==='running'?'ACTIVE':'READY','good');
    try{lcd('AUDIO READY','TAP A PAD OR PRESS PLAY')}catch(_){}
  }catch(e){
    console.error(e);
    unlocking=false;
    if(state)state.textContent='AUDIO START FAILED — TAP AGAIN';
    setEngineText('AUDIO FAILED','bad');
    return;
  }

  // Check state shortly afterward without blocking the gate.
  setTimeout(()=>{
    try{
      const c=ensureIOSContextSync();
      if(c.state==='running'){
        setEngineText('ACTIVE','good');
      }else{
        setEngineText('READY — TAP PAD','good');
      }
    }catch(_){}
    unlocking=false;
  },120);
}

lock();

// touchstart is the earliest/most reliable iOS trusted gesture.
// pointerdown/click cover browsers that don't emit touch events.
btn.addEventListener('touchstart',unlock,{passive:false});
btn.addEventListener('pointerdown',unlock,{passive:false});
btn.addEventListener('click',unlock,{passive:false});

window.addEventListener('pageshow',()=>{
  try{
    if(typeof ctx==='undefined'||!ctx||ctx.state==='closed')lock();
    else if(ctx.state==='running'){document.body.classList.remove('iosAudioLocked');setEngineText('ACTIVE','good');}
  }catch(_){lock();}
});

document.addEventListener('visibilitychange',()=>{
  if(document.hidden)return;
  try{
    if(typeof ctx==='undefined'||!ctx||ctx.state==='closed')lock();
    else{
      try{ctx.resume()}catch(_){}
      document.body.classList.remove('iosAudioLocked');
      setEngineText(ctx.state==='running'?'ACTIVE':'READY — TAP PAD','good');
    }
  }catch(_){lock();}
});
})();
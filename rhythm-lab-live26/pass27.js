(()=>{
const isiOS=/iPad|iPhone|iPod/.test(navigator.userAgent)||(navigator.platform==='MacIntel'&&navigator.maxTouchPoints>1);
if(!isiOS)return;

// PASS27 is already inside the bundled app payload. Reuse that gate instead of
// creating a second one. Clone the button to strip the old broken listeners.
let gate=document.getElementById('iosAudioGate');
if(!gate){
  gate=document.createElement('div');
  gate.id='iosAudioGate';
  gate.setAttribute('role','dialog');
  gate.setAttribute('aria-modal','true');
  gate.innerHTML='<div class="iosAudioCard"><h2>Start Audio</h2><p>iPhone and iPad require one direct tap before Web Audio can run.</p><button id="iosAudioStart" type="button">TAP TO START AUDIO</button><div class="iosAudioState" id="iosAudioState">AUDIO LOCKED</div></div>';
  document.body.appendChild(gate);
}

let oldBtn=gate.querySelector('#iosAudioStart');
let btn=oldBtn;
if(oldBtn){
  btn=oldBtn.cloneNode(true);
  oldBtn.replaceWith(btn);
}else{
  btn=document.createElement('button');
  btn.id='iosAudioStart';btn.type='button';btn.textContent='TAP TO START AUDIO';
  gate.querySelector('.iosAudioCard')?.appendChild(btn);
}
const state=gate.querySelector('#iosAudioState');
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

    // Must happen synchronously inside this exact trusted touch/click.
    const c=ensureIOSContextSync();

    // Prime Safari/WebKit with a source start during user activation.
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

    // Never await on iOS. The promise can remain pending and make the UI look dead.
    try{c.resume()}catch(_){}

    // Release immediately. Every pad hit calls ensureIOSContextSync again from
    // its own trusted gesture, so WebKit gets another resume call if necessary.
    document.body.classList.remove('iosAudioLocked');
    if(state)state.textContent='AUDIO READY';
    setEngineText(c.state==='running'?'ACTIVE':'READY — TAP PAD','good');
    try{lcd('AUDIO READY','TAP A PAD OR PRESS PLAY')}catch(_){}
  }catch(e){
    console.error(e);
    unlocking=false;
    if(state)state.textContent='AUDIO START FAILED — TAP AGAIN';
    setEngineText('AUDIO FAILED','bad');
    return;
  }

  setTimeout(()=>{
    try{
      const c=ensureIOSContextSync();
      setEngineText(c.state==='running'?'ACTIVE':'READY — TAP PAD','good');
    }catch(_){}
    unlocking=false;
  },120);
}

lock();
btn.addEventListener('touchstart',unlock,{passive:false});
btn.addEventListener('pointerdown',unlock,{passive:false});
btn.addEventListener('click',unlock,{passive:false});

window.addEventListener('pageshow',()=>{
  try{
    if(typeof ctx==='undefined'||!ctx||ctx.state==='closed')lock();
    else if(ctx.state==='running'){
      document.body.classList.remove('iosAudioLocked');
      setEngineText('ACTIVE','good');
    }
  }catch(_){lock();}
});
})();
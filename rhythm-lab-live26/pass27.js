
(()=>{
const isiOS=/iPad|iPhone|iPod/.test(navigator.userAgent)||(navigator.platform==='MacIntel'&&navigator.maxTouchPoints>1);
if(!isiOS)return;
const gate=document.createElement('div');gate.id='iosAudioGate';gate.setAttribute('role','dialog');gate.setAttribute('aria-modal','true');
gate.innerHTML='<div class="iosAudioCard"><h2>Start Audio</h2><p>iPhone and iPad browsers require a direct tap before Web Audio can start. Tap once to unlock the drum engine.</p><button id="iosAudioStart" type="button">TAP TO START AUDIO</button><div class="iosAudioState" id="iosAudioState">AUDIO LOCKED</div></div>';
document.body.appendChild(gate);
const btn=document.getElementById('iosAudioStart'),state=document.getElementById('iosAudioState');
const lock=()=>{document.body.classList.add('iosAudioLocked');if(state)state.textContent='AUDIO LOCKED';const es=document.getElementById('engineStat');if(es){es.textContent='TAP TO START';es.className='warn';}};
const unlock=ev=>{
if(ev){ev.preventDefault();ev.stopPropagation();}
if(state)state.textContent='STARTING AUDIO…';
try{
if(navigator.audioSession&&'type' in navigator.audioSession){try{navigator.audioSession.type='playback'}catch(_){}}
const c=typeof ensureIOSContextSync==='function'?ensureIOSContextSync():(()=>{const AC=window.AudioContext||window.webkitAudioContext;if(!AC)throw new Error('Web Audio unavailable');return new AC()})();
try{const b=c.createBuffer(1,2,c.sampleRate||48000),src=c.createBufferSource(),g=c.createGain();src.buffer=b;g.gain.value=.00001;src.connect(g);g.connect(c.destination);src.start(0)}catch(_){}
let rp=null;try{rp=c.resume()}catch(_){}
const finish=()=>{if(c.state==='running'){document.body.classList.remove('iosAudioLocked');if(state)state.textContent='AUDIO READY';const es=document.getElementById('engineStat');if(es){es.textContent='ACTIVE';es.className='good'}try{lcd('AUDIO READY','TAP A PAD OR PRESS PLAY')}catch(_){}}else{if(state)state.textContent='TAP AGAIN TO ENABLE AUDIO';document.body.classList.add('iosAudioLocked')}};
Promise.resolve(rp).then(()=>setTimeout(finish,40)).catch(()=>setTimeout(finish,40));
}catch(e){if(state)state.textContent='AUDIO START FAILED — TAP AGAIN';console.error(e)}
};
lock();
btn.addEventListener('pointerdown',unlock,{passive:false});
btn.addEventListener('touchend',unlock,{passive:false});
btn.addEventListener('click',unlock,{passive:false});
window.addEventListener('pageshow',()=>{try{if(!ctx||ctx.state!=='running')lock()}catch(_){lock()}});
document.addEventListener('visibilitychange',()=>{if(!document.hidden){try{if(!ctx||ctx.state!=='running')lock()}catch(_){lock()}}});
})();
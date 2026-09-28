(async()=>{try{
  const a=[];
  for(let i=0;i<23;i++){
    const n=String(i).padStart(3,'0');
    const r=await fetch('chunks/'+n+'.txt',{cache:'no-store'});
    if(!r.ok) throw new Error('app payload '+n+' '+r.status);
    a.push(await r.text());
    const f=document.getElementById('f'),m=document.getElementById('m');
    if(f) f.style.width=((i+1)/23*100)+'%';
    if(m) m.textContent=(i+1)+' / 23';
  }
  let h=a.join('');
  if(!h.startsWith('<!doctype html>')) throw new Error('assembled app payload invalid');
  const rb=h.indexOf('const ROM_B64');
  if(rb<0) throw new Error('embedded ROM bundle missing');
  const romSection=h.slice(rb,Math.min(h.length,rb+4300000));
  for(const k of ['"hr16":','"hr16b":','"sr16":']) if(!romSection.includes(k)) throw new Error('embedded ROM missing: '+k.replace(/[":]/g,''));
  if(!h.includes('bytes:1048576')||!h.includes('verifyEmbeddedRoms')) throw new Error('ROM integrity verifier missing');
  h=h.replace('</head>','<link rel="stylesheet" href="pass27.css"><link rel="stylesheet" href="pass28.css"><link rel="stylesheet" href="pass29.css"><link rel="stylesheet" href="pass31.css"></head>');
  h=h.replace('</body>','<script src="pass28.js"></'+'script><script src="pass29.js"></'+'script><script src="pass30.js"></'+'script><script src="pass31.js"></'+'script></body>');
  document.open();document.write(h);document.close();
}catch(e){const s=document.getElementById('s');if(s)s.innerHTML='<div><b>Load failed</b><br><pre style="white-space:pre-wrap;max-width:90vw">'+String(e)+'</pre></div>';console.error(e)}})();
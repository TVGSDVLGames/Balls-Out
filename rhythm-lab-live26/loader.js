(async()=>{try{
  const a=[];
  for(let i=0;i<23;i++){
    const n=String(i).padStart(3,'0');
    const r=await fetch('chunks/'+n+'.txt',{cache:'no-store'});
    if(!r.ok) throw new Error('chunk '+n+' '+r.status);
    a.push(await r.text());
    const f=document.getElementById('f'),m=document.getElementById('m');
    if(f) f.style.width=((i+1)/23*100)+'%';
    if(m) m.textContent=(i+1)+' / 23';
  }
  let h=a.join('');
  if(!h.startsWith('<!doctype html>')) throw new Error('assembled HTML invalid');
  h=h.replace('</head>','<link rel="stylesheet" href="pass27.css"></head>');
  h=h.replace('</body>','<script src="pass27.js"></'+'script></body>');
  document.open();
  document.write(h);
  document.close();
}catch(e){
  const s=document.getElementById('s');
  if(s) s.innerHTML='<div><b>Load failed</b><br><pre style="white-space:pre-wrap;max-width:90vw">'+String(e)+'</pre></div>';
  console.error(e);
}})();
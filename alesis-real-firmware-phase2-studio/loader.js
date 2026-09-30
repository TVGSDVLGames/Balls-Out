(async()=>{try{
 const total=13,a=[];
 for(let i=0;i<total;i++){
  const n=String(i).padStart(3,'0');
  const r=await fetch('chunks/'+n+'.txt',{cache:'no-store'});
  if(!r.ok)throw new Error('payload '+n+' '+r.status);
  a.push(await r.text());
  const f=document.getElementById('f'),m=document.getElementById('m');
  if(f)f.style.width=((i+1)/total*100)+'%';
  if(m)m.textContent=(i+1)+' / '+total;
 }
 const h=a.join('');
 if(!h.toLowerCase().startsWith('<!doctype html>'))throw new Error('assembled Phase 2 payload invalid');
 if(!h.includes('class MCS51')||!h.includes('P2_PATTERNS')||!h.includes('Firmware Pad Audition'))throw new Error('Phase 2 firmware studio core missing');
 document.open();document.write(h);document.close();
}catch(e){
 const s=document.getElementById('s');
 if(s)s.innerHTML='<div><b>Load failed</b><br><pre style="white-space:pre-wrap;max-width:90vw">'+String(e)+'</pre></div>';
 console.error(e);
}})();
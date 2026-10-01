(async()=>{try{
 const total=23,a=[];
 for(let i=0;i<total;i++){const n=String(i).padStart(3,'0'),r=await fetch('chunks/'+n+'.txt',{cache:'no-store'});if(!r.ok)throw new Error('payload '+n+' '+r.status);a.push(await r.text());const f=document.getElementById('f'),m=document.getElementById('m');if(f)f.style.width=((i+1)/total*100)+'%';if(m)m.textContent=(i+1)+' / '+total}
 const h=a.join('');if(!h.toLowerCase().startsWith('<!doctype html>'))throw new Error('assembled Phase 3 payload invalid');
 for(const k of ['FW_HR16B','FW_SR16','P3_CONFIG','19cf0fce','d049af6e','f5e8f90d','f37f8486'])if(!h.includes(k))throw new Error('Phase 3 core missing '+k);
 document.open();document.write(h);document.close();
}catch(e){const s=document.getElementById('s');if(s)s.innerHTML='<div><b>Load failed</b><br><pre style="white-space:pre-wrap;max-width:90vw">'+String(e)+'</pre></div>';console.error(e)}})();

let FW=null, SOUND=null;
const ROM_URLS={
  fw:'https://burnkit2600.com/hr16/HR16_V1_09.BIN',
  u16:'https://burnkit2600.com/hr16/HR16_U16.BIN',
  u15:'https://burnkit2600.com/hr16/HR16_U15.BIN'
};
function rev8(x){x=((x&0xF0)>>4)|((x&0x0F)<<4);x=((x&0xCC)>>2)|((x&0x33)<<2);x=((x&0xAA)>>1)|((x&0x55)<<1);return x}
function descrambleFW(raw){const out=new Uint8Array(raw.length);for(let i=0;i<raw.length;i++)out[(i&~255)|rev8(i&255)]=raw[i];return out}
async function fetchBytes(url){
  const tries=[url,'https://corsproxy.io/?url='+encodeURIComponent(url)];
  let last=null;
  for(const u of tries){
    try{
      const r=await fetch(u,{cache:'no-store'});
      if(!r.ok)throw new Error('HTTP '+r.status);
      const b=new Uint8Array(await r.arrayBuffer());
      if(!b.length)throw new Error('empty response');
      return b;
    }catch(e){last=e}
  }
  throw last||new Error('ROM fetch failed');
}
async function sha1hex(u){const d=await crypto.subtle.digest('SHA-1',u);return [...new Uint8Array(d)].map(x=>x.toString(16).padStart(2,'0')).join('')}
async function bootOnline(){
  try{
    $('cpuStat').textContent='FETCHING REAL ROMS';$('cpuStat').className='warn';
    $('audStat').textContent='AUTO-LOADING U16/U15';$('audStat').className='warn';
    const [rawfw,u16,u15]=await Promise.all([fetchBytes(ROM_URLS.fw),fetchBytes(ROM_URLS.u16),fetchBytes(ROM_URLS.u15)]);
    if(rawfw.length!==32768)throw new Error('OS size '+rawfw.length+' != 32768');
    if(u16.length!==524288||u15.length!==524288)throw new Error('sound ROM size mismatch');
    const [hfw,h16,h15]=await Promise.all([sha1hex(rawfw),sha1hex(u16),sha1hex(u15)]);
    if(hfw!=='229b4230c7b5380efbfd42fa95645723d3fd6d55')throw new Error('OS SHA1 mismatch '+hfw);
    if(h16!=='092e1cf649fbef171cfaf91e20707d89998b7a1e')throw new Error('U16 SHA1 mismatch '+h16);
    if(h15!=='89728cb38ae172b5e347a03018617c94a087dce0')throw new Error('U15 SHA1 mismatch '+h15);
    FW=descrambleFW(rawfw);
    SOUND=new Uint8Array(1048576);SOUND.set(u16,0);SOUND.set(u15,524288);
    $('audStat').textContent='ROMS READY • TAP PAD';$('audStat').className='good';
    buildUI();makeCPU();requestAnimationFrame(frame);
  }catch(e){
    console.error(e);
    $('cpuStat').textContent='ROM LOAD ERROR';$('cpuStat').className='warn';
    $('audStat').textContent='ROM LOAD ERROR';$('audStat').className='warn';
    $('debug').textContent='ONLINE ROM LOAD FAILED: '+(e&&e.message?e.message:e);
  }
}
 const MATRIX=[["COPY", "OFFSET", "SWING", "QUANT", "LENGTH", "PATT", "MIDI/UTIL", "TEMPO"], ["DELETE", "INSERT", "SONG", "1", "2", "3", "4", "5"], ["ERASE", "TAPE", "FILL", "6", "7", "8", "9", "0"], ["PLAY", "STOP/CONTINUE", "RECORD", "< -", "> +", "VOICE", "TUNE", "MIX"], ["TOM 1", "TOM 2", "TOM 3", "TOM 4", "RIDE", "CRASH", "PERC 1", "PERC 2"], ["KICK", "SNARE", "CLOSED HAT", "MID HAT", "OPEN HAT", "CLAPS", "PERC 3", "PERC 4"]]; function b64(s){const x=atob(s),u=new Uint8Array(x.length);for(let i=0;i<x.length;i++)u[i]=x.charCodeAt(i);return u}
class MCS51 {
  constructor(code, hooks={}) {
    this.code=code; this.hooks=hooks; this.iram=new Uint8Array(128); this.sfr=new Uint8Array(128); this.xram=new Uint8Array(65536);
    this.reset();
  }
  reset(){this.iram.fill(0);this.sfr.fill(0);this.xram.fill(0);this.pc=0;this.cycles=0;this.sfr[0x01]=7;
    this.sfr[0x00]=0xff;this.sfr[0x10]=0xff;this.sfr[0x20]=0xff;this.sfr[0x30]=0xff;
    this.interruptLevel=0;this.lastP3=0xff;
  }
  code8(a){return this.code[(a&0xffff)&(this.code.length-1)]||0}
  fetch(){const v=this.code8(this.pc);this.pc=(this.pc+1)&0xffff;return v}
  fetch16(){const h=this.fetch(),l=this.fetch();return (h<<8)|l}
  rel(){let r=this.fetch();if(r&0x80)r-=256;return r}
  sfrIndex(a){return (a-0x80)&0x7f}
  readDirect(a){a&=255;if(a<0x80)return this.iram[a];
    const i=this.sfrIndex(a); if(a===0x90&&this.hooks.portRead)return this.hooks.portRead(1,this.sfr[i])&255;
    if(a===0xb0&&this.hooks.portRead)return this.hooks.portRead(3,this.sfr[i])&255;
    return this.sfr[i];}
  writeDirect(a,v){a&=255;v&=255;if(a<0x80){this.iram[a]=v;return;} const i=this.sfrIndex(a);this.sfr[i]=v;
    if((a===0x80||a===0x90||a===0xa0||a===0xb0)&&this.hooks.portWrite)this.hooks.portWrite((a-0x80)>>4,v);
    if(a===0x99&&this.hooks.serialWrite)this.hooks.serialWrite(v);
  }
  readIndirect(a){a&=255;return a<0x80?this.iram[a]:0xff}
  writeIndirect(a,v){a&=255;if(a<0x80)this.iram[a]=v&255}
  bank(){return ((this.sfr[this.sfrIndex(0xd0)]>>3)&3)*8}
  r(n){return this.iram[this.bank()+n]}
  setr(n,v){this.iram[this.bank()+n]=v&255}
  get A(){return this.sfr[this.sfrIndex(0xe0)]}
  set A(v){this.sfr[this.sfrIndex(0xe0)]=v&255;this.updateParity()}
  get B(){return this.sfr[this.sfrIndex(0xf0)]}
  set B(v){this.sfr[this.sfrIndex(0xf0)]=v&255}
  get PSW(){return this.sfr[this.sfrIndex(0xd0)]}
  set PSW(v){this.sfr[this.sfrIndex(0xd0)]=v&255;this.updateParity()}
  get SP(){return this.sfr[1]}
  set SP(v){this.sfr[1]=v&255}
  get DPTR(){return (this.sfr[3]<<8)|this.sfr[2]}
  set DPTR(v){this.sfr[3]=(v>>8)&255;this.sfr[2]=v&255}
  updateParity(){let a=this.sfr[this.sfrIndex(0xe0)],p=0;for(let i=0;i<8;i++)p^=(a>>i)&1;let psw=this.sfr[this.sfrIndex(0xd0)];this.sfr[this.sfrIndex(0xd0)]=(psw&0xfe)|p}
  flag(mask){return (this.PSW&mask)?1:0}
  setFlag(mask,on){let p=this.PSW;if(on)p|=mask;else p&=~mask;this.PSW=p}
  getBit(b){b&=255;if(b<0x80){const a=0x20+(b>>3);return (this.iram[a]>>(b&7))&1}const a=b&0xf8;return (this.readDirect(a)>>(b&7))&1}
  setBit(b,v){b&=255;if(b<0x80){const a=0x20+(b>>3),m=1<<(b&7);this.iram[a]=v?(this.iram[a]|m):(this.iram[a]&~m);return}const a=b&0xf8,m=1<<(b&7),x=this.readDirect(a);this.writeDirect(a,v?(x|m):(x&~m))}
  push(v){this.SP=(this.SP+1)&255;if(this.SP<128)this.iram[this.SP]=v&255}
  pop(){const a=this.SP,v=a<128?this.iram[a]:0xff;this.SP=(a-1)&255;return v}
  call(addr){this.push(this.pc&255);this.push((this.pc>>8)&255);this.pc=addr&0xffff}
  ret(){const hi=this.pop(),lo=this.pop();this.pc=((hi<<8)|lo)&0xffff}
  add(v,c=0){const a=this.A,vv=v&255,cc=c?1:0,s=a+vv+cc,r=s&255;this.setFlag(0x80,s>255);this.setFlag(0x40,((a&15)+(vv&15)+cc)>15);this.setFlag(0x04,((~(a^vv)&(a^r))&0x80)!==0);this.A=r}
  sub(v,c=0){const a=this.A,vv=v&255,cc=c?1:0,d=a-vv-cc,r=d&255;this.setFlag(0x80,d<0);this.setFlag(0x40,(a&15)<((vv&15)+cc));this.setFlag(0x04,(((a^vv)&(a^r))&0x80)!==0);this.A=r}
  xread(a){a&=0xffff;if(this.hooks.xread)return this.hooks.xread(a,this.xram[a])&255;return this.xram[a]}
  xwrite(a,v){a&=0xffff;v&=255;if(this.hooks.xwrite)this.hooks.xwrite(a,v);else this.xram[a]=v}
  branch(cond,rel){if(cond)this.pc=(this.pc+rel)&0xffff}
  timerAdvance(n){
    const TMOD=this.sfr[9], TCONi=8; let TCON=this.sfr[TCONi];
    for(let z=0;z<n;z++){
      if((TCON&0x10) && !(TMOD&0x04)){
        const mode=TMOD&3;
        if(mode===1){let v=(this.sfr[12]<<8)|this.sfr[10];v=(v+1)&0xffff;this.sfr[12]=v>>8;this.sfr[10]=v&255;if(v===0)TCON|=0x20}
        else if(mode===2){let v=(this.sfr[10]+1)&255;if(v===0){v=this.sfr[12];TCON|=0x20}this.sfr[10]=v}
        else if(mode===0){let v=((this.sfr[12]<<5)|(this.sfr[10]&31))+1;if(v>=8192){v&=8191;TCON|=0x20}this.sfr[12]=(v>>5)&255;this.sfr[10]=(this.sfr[10]&0xe0)|(v&31)}
        else {let v=(this.sfr[10]+1)&255;if(v===0)TCON|=0x20;this.sfr[10]=v}
      }
      if((TCON&0x40) && !(TMOD&0x40)){
        const mode=(TMOD>>4)&3;
        if(mode===1){let v=(this.sfr[13]<<8)|this.sfr[11];v=(v+1)&0xffff;this.sfr[13]=v>>8;this.sfr[11]=v&255;if(v===0)TCON|=0x80}
        else if(mode===2){let v=(this.sfr[11]+1)&255;if(v===0){v=this.sfr[13];TCON|=0x80}this.sfr[11]=v}
        else if(mode===0){let v=((this.sfr[13]<<5)|(this.sfr[11]&31))+1;if(v>=8192){v&=8191;TCON|=0x80}this.sfr[13]=(v>>5)&255;this.sfr[11]=(this.sfr[11]&0xe0)|(v&31)}
      }
    }this.sfr[TCONi]=TCON;
  }
  checkInterrupt(){const IE=this.sfr[0x28],IP=this.sfr[0x38],TCON=this.sfr[8];if(!(IE&0x80))return;let vec=-1,pri=0,mask=0;
    const cand=[[0x01,0x02,0x03,0x01],[0x02,0x20,0x0b,0x02],[0x04,0x08,0x13,0x04],[0x08,0x80,0x1b,0x08]];
    for(const [ie,fl,v,ip] of cand){if((IE&ie)&&(TCON&fl)){const p=(IP&ip)?2:1;if(p>this.interruptLevel && p>pri){vec=v;pri=p;mask=fl}}}
    if(vec>=0){this.push(this.pc&255);this.push(this.pc>>8);this.pc=vec;this.interruptLevel=pri;if(mask===0x20||mask===0x80)this.sfr[8]&=~mask;}
  }
  step(){const start=this.pc,op=this.fetch();let cyc=1, r, d, rel, bit, v, a, carry=this.flag(0x80); const rn=op&7;
    if(op>=0x08&&op<=0x0f){this.setr(rn,this.r(rn)+1)}
    else if(op>=0x18&&op<=0x1f){this.setr(rn,this.r(rn)-1)}
    else if(op>=0x28&&op<=0x2f){this.add(this.r(rn))}
    else if(op>=0x38&&op<=0x3f){this.add(this.r(rn),carry)}
    else if(op>=0x48&&op<=0x4f){this.A=this.A|this.r(rn)}
    else if(op>=0x58&&op<=0x5f){this.A=this.A&this.r(rn)}
    else if(op>=0x68&&op<=0x6f){this.A=this.A^this.r(rn)}
    else if(op>=0x78&&op<=0x7f){this.setr(rn,this.fetch())}
    else if(op>=0x88&&op<=0x8f){d=this.fetch();this.writeDirect(d,this.r(rn))}
    else if(op>=0x98&&op<=0x9f){this.sub(this.r(rn),carry)}
    else if(op>=0xa8&&op<=0xaf){d=this.fetch();this.setr(rn,this.readDirect(d))}
    else if(op>=0xb8&&op<=0xbf){v=this.fetch();rel=this.rel();this.setFlag(0x80,this.r(rn)<v);this.branch(this.r(rn)!==v,rel);cyc=2}
    else if(op>=0xc8&&op<=0xcf){v=this.r(rn);this.setr(rn,this.A);this.A=v}
    else if(op>=0xd8&&op<=0xdf){rel=this.rel();v=(this.r(rn)-1)&255;this.setr(rn,v);this.branch(v!==0,rel);cyc=2}
    else if(op>=0xe8&&op<=0xef){this.A=this.r(rn)}
    else if(op>=0xf8&&op<=0xff){this.setr(rn,this.A)}
    else if((op&0x1f)===0x01){v=this.fetch();this.pc=(this.pc&0xf800)|((op&0xe0)<<3)|v;cyc=2}
    else if((op&0x1f)===0x11){v=this.fetch();a=(this.pc&0xf800)|((op&0xe0)<<3)|v;this.call(a);cyc=2}
    else switch(op){
      case 0x00:break; case 0x02:this.pc=this.fetch16();cyc=2;break; case 0x03:this.A=((this.A>>1)|((this.A&1)<<7));break; case 0x04:this.A=this.A+1;break;
      case 0x05:d=this.fetch();this.writeDirect(d,this.readDirect(d)+1);break; case 0x06:case 0x07:r=op&1;a=this.r(r);this.writeIndirect(a,this.readIndirect(a)+1);break;
      case 0x10:bit=this.fetch();rel=this.rel();if(this.getBit(bit)){this.setBit(bit,0);this.branch(true,rel)}cyc=2;break; case 0x12:a=this.fetch16();this.call(a);cyc=2;break;
      case 0x13:{const x=this.A,c=this.flag(0x80);this.setFlag(0x80,x&1);this.A=(x>>1)|(c<<7)}break; case 0x14:this.A=this.A-1;break;
      case 0x15:d=this.fetch();this.writeDirect(d,this.readDirect(d)-1);break; case 0x16:case 0x17:r=op&1;a=this.r(r);this.writeIndirect(a,this.readIndirect(a)-1);break;
      case 0x20:bit=this.fetch();rel=this.rel();this.branch(this.getBit(bit),rel);cyc=2;break; case 0x22:this.ret();cyc=2;break; case 0x23:this.A=((this.A<<1)|(this.A>>7));break;
      case 0x24:this.add(this.fetch());break; case 0x25:this.add(this.readDirect(this.fetch()));break; case 0x26:case 0x27:this.add(this.readIndirect(this.r(op&1)));break;
      case 0x30:bit=this.fetch();rel=this.rel();this.branch(!this.getBit(bit),rel);cyc=2;break; case 0x32:this.ret();this.interruptLevel=0;cyc=2;break;
      case 0x33:{const x=this.A,c=this.flag(0x80);this.setFlag(0x80,x&0x80);this.A=((x<<1)&255)|c}break; case 0x34:this.add(this.fetch(),carry);break;
      case 0x35:this.add(this.readDirect(this.fetch()),carry);break; case 0x36:case 0x37:this.add(this.readIndirect(this.r(op&1)),carry);break;
      case 0x40:rel=this.rel();this.branch(this.flag(0x80),rel);cyc=2;break; case 0x42:d=this.fetch();this.writeDirect(d,this.readDirect(d)|this.A);break;
      case 0x43:d=this.fetch();v=this.fetch();this.writeDirect(d,this.readDirect(d)|v);break; case 0x44:this.A=this.A|this.fetch();break; case 0x45:this.A=this.A|this.readDirect(this.fetch());break;
      case 0x46:case 0x47:this.A=this.A|this.readIndirect(this.r(op&1));break; case 0x50:rel=this.rel();this.branch(!this.flag(0x80),rel);cyc=2;break;
      case 0x52:d=this.fetch();this.writeDirect(d,this.readDirect(d)&this.A);break; case 0x53:d=this.fetch();v=this.fetch();this.writeDirect(d,this.readDirect(d)&v);break;
      case 0x54:this.A=this.A&this.fetch();break; case 0x55:this.A=this.A&this.readDirect(this.fetch());break; case 0x56:case 0x57:this.A=this.A&this.readIndirect(this.r(op&1));break;
      case 0x60:rel=this.rel();this.branch(this.A===0,rel);cyc=2;break; case 0x62:d=this.fetch();this.writeDirect(d,this.readDirect(d)^this.A);break;
      case 0x63:d=this.fetch();v=this.fetch();this.writeDirect(d,this.readDirect(d)^v);break; case 0x64:this.A=this.A^this.fetch();break; case 0x65:this.A=this.A^this.readDirect(this.fetch());break;
      case 0x66:case 0x67:this.A=this.A^this.readIndirect(this.r(op&1));break; case 0x70:rel=this.rel();this.branch(this.A!==0,rel);cyc=2;break;
      case 0x72:bit=this.fetch();this.setFlag(0x80,this.flag(0x80)|this.getBit(bit));cyc=2;break; case 0x73:this.pc=(this.DPTR+this.A)&0xffff;cyc=2;break;
      case 0x74:this.A=this.fetch();break; case 0x75:d=this.fetch();v=this.fetch();this.writeDirect(d,v);break; case 0x76:case 0x77:this.writeIndirect(this.r(op&1),this.fetch());break;
      case 0x80:rel=this.rel();this.branch(true,rel);cyc=2;break; case 0x82:bit=this.fetch();this.setFlag(0x80,this.flag(0x80)&this.getBit(bit));cyc=2;break;
      case 0x83:this.A=this.code8((this.pc+this.A)&0xffff);cyc=2;break;
      case 0x84:{const b=this.B;if(b===0){this.setFlag(0x04,1);this.setFlag(0x80,0)}else{const q=Math.floor(this.A/b),rem=this.A%b;this.A=q;this.B=rem;this.setFlag(0x04,0);this.setFlag(0x80,0)}cyc=4}break;
      case 0x85:{const src=this.fetch(),dst=this.fetch();this.writeDirect(dst,this.readDirect(src))}break; case 0x86:case 0x87:d=this.fetch();this.writeDirect(d,this.readIndirect(this.r(op&1)));break;
      case 0x90:this.DPTR=this.fetch16();cyc=2;break; case 0x92:bit=this.fetch();this.setBit(bit,this.flag(0x80));cyc=2;break; case 0x93:this.A=this.code8((this.DPTR+this.A)&0xffff);cyc=2;break;
      case 0x94:this.sub(this.fetch(),carry);break; case 0x95:this.sub(this.readDirect(this.fetch()),carry);break; case 0x96:case 0x97:this.sub(this.readIndirect(this.r(op&1)),carry);break;
      case 0xa0:bit=this.fetch();this.setFlag(0x80,this.flag(0x80)|(!this.getBit(bit)));cyc=2;break; case 0xa2:bit=this.fetch();this.setFlag(0x80,this.getBit(bit));cyc=2;break;
      case 0xa3:this.DPTR=(this.DPTR+1)&0xffff;cyc=2;break; case 0xa4:{const p=this.A*this.B;this.A=p&255;this.B=(p>>8)&255;this.setFlag(0x80,0);this.setFlag(0x04,p>255);cyc=4}break;
      case 0xa5:throw new Error('Illegal opcode A5 at '+start.toString(16)); case 0xa6:case 0xa7:d=this.fetch();this.writeIndirect(this.r(op&1),this.readDirect(d));break;
      case 0xb0:bit=this.fetch();this.setFlag(0x80,this.flag(0x80)&(!this.getBit(bit)));cyc=2;break; case 0xb2:bit=this.fetch();this.setBit(bit,!this.getBit(bit));break; case 0xb3:this.setFlag(0x80,!this.flag(0x80));break;
      case 0xb4:v=this.fetch();rel=this.rel();this.setFlag(0x80,this.A<v);this.branch(this.A!==v,rel);cyc=2;break; case 0xb5:d=this.fetch();v=this.readDirect(d);rel=this.rel();this.setFlag(0x80,this.A<v);this.branch(this.A!==v,rel);cyc=2;break;
      case 0xb6:case 0xb7:v=this.fetch();rel=this.rel();a=this.readIndirect(this.r(op&1));this.setFlag(0x80,a<v);this.branch(a!==v,rel);cyc=2;break;
      case 0xc0:d=this.fetch();this.push(this.readDirect(d));cyc=2;break; case 0xc2:this.setBit(this.fetch(),0);break; case 0xc3:this.setFlag(0x80,0);break;
      case 0xc4:this.A=((this.A&15)<<4)|(this.A>>4);break; case 0xc5:d=this.fetch();v=this.readDirect(d);this.writeDirect(d,this.A);this.A=v;break;
      case 0xc6:case 0xc7:a=this.r(op&1);v=this.readIndirect(a);this.writeIndirect(a,this.A);this.A=v;break; case 0xd0:d=this.fetch();this.writeDirect(d,this.pop());cyc=2;break;
      case 0xd2:this.setBit(this.fetch(),1);break; case 0xd3:this.setFlag(0x80,1);break;
      case 0xd4:{let x=this.A,c=this.flag(0x80),ac=this.flag(0x40);if((x&15)>9||ac)x+=6;if((x>0x9f)||c){x+=0x60;c=1}this.A=x;this.setFlag(0x80,c)}break;
      case 0xd5:d=this.fetch();rel=this.rel();v=(this.readDirect(d)-1)&255;this.writeDirect(d,v);this.branch(v!==0,rel);cyc=2;break;
      case 0xd6:case 0xd7:a=this.r(op&1);v=this.readIndirect(a);{const al=this.A&15,vl=v&15;this.A=(this.A&0xf0)|vl;this.writeIndirect(a,(v&0xf0)|al)}break;
      case 0xe0:this.A=this.xread(this.DPTR);cyc=2;break; case 0xe2:case 0xe3:this.A=this.xread(((this.readDirect(0xa0)<<8)|this.r(op&1))&0xffff);cyc=2;break;
      case 0xe4:this.A=0;break; case 0xe5:this.A=this.readDirect(this.fetch());break; case 0xe6:case 0xe7:this.A=this.readIndirect(this.r(op&1));break;
      case 0xf0:this.xwrite(this.DPTR,this.A);cyc=2;break; case 0xf2:case 0xf3:this.xwrite(((this.readDirect(0xa0)<<8)|this.r(op&1))&0xffff,this.A);cyc=2;break;
      case 0xf4:this.A=(~this.A)&255;break; case 0xf5:this.writeDirect(this.fetch(),this.A);break; case 0xf6:case 0xf7:this.writeIndirect(this.r(op&1),this.A);break;
      default:throw new Error('Unhandled opcode '+op.toString(16)+' at '+start.toString(16));
    }
    this.timerAdvance(cyc);this.cycles+=cyc;this.checkInterrupt();return {pc:start,op,cycles:cyc};
  }
}


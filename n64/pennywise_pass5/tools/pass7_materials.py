#!/usr/bin/env python3
import json,struct,sys,os
JSON_CHUNK=0x4E4F534A

def read_glb(path):
    b=open(path,'rb').read(); off=12; chunks=[]; ji=None
    while off<len(b):
        ln,typ=struct.unpack_from('<II',b,off); off+=8; data=b[off:off+ln];off+=ln
        if typ==JSON_CHUNK:ji=len(chunks)
        chunks.append([typ,data])
    if ji is None:raise RuntimeError('no JSON chunk '+path)
    doc=json.loads(chunks[ji][1].rstrip(b' \t\r\n\0').decode())
    return doc,chunks,ji

def write_glb(path,doc,chunks,ji):
    raw=json.dumps(doc,separators=(',',':')).encode();raw+=b' '*((-len(raw))%4);chunks[ji][1]=raw
    body=b''.join(struct.pack('<II',len(d),t)+d for t,d in chunks)
    open(path,'wb').write(struct.pack('<4sII',b'glTF',2,12+len(body))+body)

def cc_texshade():
    # (TEX0 - 0) * SHADE + 0. Tiny3D CC: TEX0=1, SHADE=4.
    return {'name':'','A':1,'B':0,'C':4,'D':0,'A_alpha':0,'B_alpha':0,'C_alpha':0,'D_alpha':1}

def axis(size):
    return {'clamp':0,'mirror':0,'low':0.0,'high':float(size-1),'mask':0,'shift':0}

def texture_for(name):
    n=(name or '').lower()
    if 'pennyfacetex' in n:return ('face.png',64)
    if 'wetbrick' in n:return ('brick.png',32)
    if 'mossstone' in n:return ('stone.png',32)
    if 'iron' in n or 'rust' in n or 'metal' in n:return ('metal.png',32)
    if 'blackwater' in n:return ('water.png',32)
    if 'crimson' in n or 'balloonred' in n:return ('redcloth.png',32)
    if 'oldivory' in n or 'dirtyruffle' in n:return ('cloth.png',32)
    if 'deadlightskin' in n:return ('skin.png',32)
    if 'burnthair' in n:return ('hair.png',32)
    if 'slingshotwood' in n:return ('wood.png',32)
    # small dark/rubber/silver materials stay shaded only; no fake texture needed.
    return None

def shade_only():
    return {'name':'','A':0,'B':0,'C':0,'D':4,'A_alpha':0,'B_alpha':0,'C_alpha':0,'D_alpha':4}

def patch(path):
    doc,chunks,ji=read_glb(path); used=[]
    for m in doc.get('materials',[]):
        f=m.setdefault('extras',{}).get('f3d_mat')
        if not isinstance(f,dict):raise RuntimeError(f'{path}: missing f3d_mat {m.get("name")}')
        spec=texture_for(m.get('name',''))
        f['combiner1']=cc_texshade() if spec else shade_only()
        f['combiner2']=f['combiner1'].copy()
        f['set_prim']=0;f['set_env']=0;f['set_blend']=0;f['use_default_lighting']=1
        r=f.setdefault('rdp_settings',{})
        r['g_shade']=1;r['g_lighting']=1;r['g_fog']=1;r['g_tex_gen']=0;r['g_tex_gen_linear']=0
        r['g_mdsft_cycletype']=0
        r['g_mdsft_text_filt']=2  # N64-style bilinear filtering
        r['set_rendermode']=1;r['rendermode_preset_cycle_1']=1;r['rendermode_preset_cycle_2']=1
        f.setdefault('draw_layer',{})['sm64']=1;f['draw_layer']['oot']=0
        if spec:
            tex,size=spec
            if not os.path.exists(os.path.join(os.path.dirname(path),tex)):
                raise RuntimeError(f'{path}: controlled texture missing: {tex}')
            f['tex0']={'tex_set':1,'use_tex_reference':0,'tex':{'name':tex},'S':axis(size),'T':axis(size)}
            # Ensure no legacy second texture can sneak in.
            if isinstance(f.get('tex1'),dict):
                f['tex1']['tex_set']=0;f['tex1']['tex']=None;f['tex1']['use_tex_reference']=0
            used.append((m.get('name'),tex))
        else:
            if isinstance(f.get('tex0'),dict):
                f['tex0']['tex_set']=0;f['tex0']['tex']=None;f['tex0']['use_tex_reference']=0
            if isinstance(f.get('tex1'),dict):
                f['tex1']['tex_set']=0;f['tex1']['tex']=None;f['tex1']['use_tex_reference']=0
    write_glb(path,doc,chunks,ji)
    raw=open(path,'rb').read().lower()
    if b'crate00' in raw:raise RuntimeError('legacy crate texture regression')
    print('PASS7_MATERIALS',path,used)

if __name__=='__main__':
    for p in sys.argv[1:]:patch(p)

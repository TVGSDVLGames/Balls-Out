#!/usr/bin/env python3
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
orig=ROOT/'tools/make_pass8_source.py'
s=orig.read_text()
start=s.index('light_anchor="""')
end=s.index('# Taller / leaner Pennywise', start)
replacement=r'''# PASS8 keeps PASS6's hardware point light at slot 1 and brightens it instead
# of colliding with it by installing a second directional light in the same slot.
if 't3d_light_set_exposure(1.08f);' not in c:
    raise SystemExit('PASS8 exposure anchor changed')
c=c.replace('t3d_light_set_exposure(1.08f);','t3d_light_set_exposure(1.35f);',1)
old_lamp='uint8_t lamp[4] = {(uint8_t)(142.0f*flick),(uint8_t)(132.0f*flick),(uint8_t)(92.0f*flick),255};'
new_lamp='uint8_t lamp[4] = {(uint8_t)(185.0f*flick),(uint8_t)(205.0f*flick),(uint8_t)(190.0f*flick),255};'
if old_lamp not in c:
    raise SystemExit('PASS8 point-light anchor changed')
c=c.replace(old_lamp,new_lamp,1)
'''
s=s[:start]+replacement+s[end:]
exec(compile(s,str(orig),'exec'), {'__name__':'__main__','__file__':str(orig)})

# The first successful PASS8 emulator proof showed that the PASS7 ambient values
# survived the earlier string patch and were still crushing the scene. Correct
# the generated runtime directly. Keep the working point-light/exposure code.
for rp in (ROOT/'src/main_pass8.c', ROOT/'src/main_pass8_bossproof.c'):
    c=rp.read_text()
    pairs=[
        ('RGBA32(12, 19, 21, 0xFF)','RGBA32(20, 29, 31, 0xFF)'),
        ('(color_t){29, 43, 42, 0xFF}','(color_t){45, 61, 60, 0xFF}'),
        ('t3d_fog_set_range(340.0f, 900.0f);','t3d_fog_set_range(400.0f, 980.0f);'),
        ('uint8_t amb[4] = {28, 35, 33, 255};','uint8_t amb[4] = {112, 125, 118, 255};'),
        ('uint8_t dirc[4] = {112, 122, 112, 255};','uint8_t dirc[4] = {178, 188, 172, 255};'),
    ]
    for old,new in pairs:
        if old not in c:
            raise SystemExit('PASS8B runtime anchor missing: '+old)
        c=c.replace(old,new,1)
    rp.write_text(c)

# Replace the wraparound face texture that smeared eyes/mouth around the head.
# The head shell now uses skin material; a small oval front decal carries the
# 64x64 painted face, matching the way commercial N64 characters used face maps.
ap=ROOT/'tools/build_assets_pass8.py'
a=ap.read_text()
old="add(clown_head('PennyHead',(head.x,head.y-.005*s,head.z),s,FACE),B['head'])"
new="add(clown_head('PennyHead',(head.x,head.y-.005*s,head.z),s,SKIN),B['head'])"
if old not in a: raise SystemExit('PASS8B head material anchor missing')
a=a.replace(old,new,1)

nose_anchor="# Physical nose survives the low resolution and breaks the head silhouette.\n"
face_insert=r'''# Small shaped facial decal rather than texturing the whole circumference.
def face_oval(name, center, rx, rz, material, seg=12):
    cx,cy,cz=center
    v=[(cx,cy,cz)]
    uvv=[(.5,.5)]
    for j in range(seg):
        ang=math.tau*j/seg
        v.append((cx+math.cos(ang)*rx,cy,cz+math.sin(ang)*rz))
        uvv.append((.5+.48*math.cos(ang),.5+.48*math.sin(ang)))
    f=[]
    for j in range(seg): f.append((0,j+1,((j+1)%seg)+1))
    o=mesh(name,v,f,material,(.88,.86,.78))
    uv=o.data.uv_layers.get('UVMap') or o.data.uv_layers.new(name='UVMap')
    for poly in o.data.polygons:
        for li in poly.loop_indices:
            uv.data[li].uv=uvv[o.data.loops[li].vertex_index]
    return o
add(face_oval('PennyFaceOval',(head.x,head.y-.178*s,head.z+.015*s),.145*s,.205*s,FACE),B['head'])

# Small cloth masses restore the antique-clown silhouette without returning to
# the giant primitive sleeves/bloomers that made PASS7 look like a mannequin.
for side,key in ((-1,'ual'),(1,'uar')):
    add(ico('ShoulderPleatL' if side<0 else 'ShoulderPleatR',(chest.x+side*.39*s,chest.y,chest.z+.12*s),.085*s,LIGHT,(.91,.89,.77),scale=(1.20,.95,.82)),B[key])
for side,key in ((-1,'tl'),(1,'tr')):
    add(ico('HipPleatL' if side<0 else 'HipPleatR',(pelvis.x+side*.20*s,pelvis.y,pelvis.z-.03*s),.082*s,LIGHT,(.91,.89,.77),scale=(1.15,.95,.82)),B[key])

'''
if nose_anchor not in a: raise SystemExit('PASS8B nose anchor missing')
a=a.replace(nose_anchor,face_insert+nose_anchor,1)

# Show skin texture on the proof head too.
old_preview="[(IVORY,'cloth.png'),(RED,'redcloth.png'),(HAIR,'hair.png'),(FACE,'face.png'),(BRICK,'brick.png')"
new_preview="[(SKIN,'skin.png'),(IVORY,'cloth.png'),(RED,'redcloth.png'),(HAIR,'hair.png'),(FACE,'face.png'),(BRICK,'brick.png')"
if old_preview in a: a=a.replace(old_preview,new_preview,1)
ap.write_text(a)

print('PASS8_BRIGHT_FACE_FIX_READY')

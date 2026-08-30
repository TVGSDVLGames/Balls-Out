#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
assets_src = (ROOT / 'tools' / 'build_assets.py').read_text()
runtime_src = (ROOT / 'src' / 'main.c').read_text()

# -----------------------------------------------------------------------------
# Blender asset source: preserve PASS5 as a baseline, generate a PASS6 source
# with better low-poly cloth volume, arched sewer construction, surface breakup,
# and quantized vertex colors.  No runtime texture dependency is introduced.
# -----------------------------------------------------------------------------

old_bind = '''def bind(o, arm, bone):
    if not bone or o.type!='MESH': return
    mod=o.modifiers.new('Armature','ARMATURE'); mod.object=arm
    vg=o.vertex_groups.new(name=bone)
    vg.add(list(range(len(o.data.vertices))),1.0,'REPLACE')
'''
new_bind = '''def bind(o, arm, bone):
    if not bone or o.type!='MESH': return
    world=o.matrix_world.copy()
    o.parent=arm
    o.matrix_world=world
    mod=o.modifiers.new('Armature','ARMATURE'); mod.object=arm
    vg=o.vertex_groups.new(name=bone)
    vg.add(list(range(len(o.data.vertices))),1.0,'REPLACE')
'''
if old_bind in assets_src:
    assets_src = assets_src.replace(old_bind, new_bind, 1)
elif 'o.parent=arm' not in assets_src:
    raise SystemExit('PASS6: bind() anchor changed')

helper_anchor = '\ndef bind(o, arm, bone):\n'
helpers = r'''
def ruff_folded(name, p, inner, outer, depth, material, color, points=16, wobble=.14):
    """A pleated two-sided frill with real vertical volume instead of a flat disc."""
    x,y,z=p; v=[]
    for i in range(points):
        a=math.tau*i/points
        phase=1 if i&1 else -1
        rr=outer*(1+wobble*phase)
        zz=z + depth*.48*phase
        v.append((x+math.cos(a)*inner,y+math.sin(a)*inner,z-depth*.20*phase))
        v.append((x+math.cos(a)*rr,y+math.sin(a)*rr,zz))
    f=[]
    for i in range(points):
        j=(i+1)%points
        f.append((2*i,2*j,2*j+1,2*i+1))
        f.append((2*i+1,2*j+1,2*j,2*i))
    return mesh(name,v,f,material,color)

def skirt_ruff(name, p, inner, outer, height, material, color, points=16, wobble=.12):
    """Short scalloped flared cloth layer; reads as a peplum, not a razor-thin ring."""
    x,y,z=p; v=[]
    for i in range(points):
        a=math.tau*i/points
        phase=1 if i&1 else -1
        rb=outer*(1+wobble*phase)
        v.append((x+math.cos(a)*inner,y+math.sin(a)*inner,z+height*.50))
        v.append((x+math.cos(a)*rb,y+math.sin(a)*rb,z-height*.50 + phase*height*.10))
    f=[]
    for i in range(points):
        j=(i+1)%points
        f.append((2*i,2*j,2*j+1,2*i+1))
        f.append((2*i+1,2*j+1,2*j,2*i))
    return mesh(name,v,f,material,color)

def weather(o, strength=.12, seed=0):
    """Chunky 5-bit-ish vertex-color variation: cheap, stable and very N64-looking."""
    if o.type!='MESH' or not o.data.materials: return o
    ca=o.data.color_attributes.get('Col')
    if not ca: return o
    base=o.data.materials[0].diffuse_color[:3]
    for pi,poly in enumerate(o.data.polygons):
        h=(pi*1103515245 + seed*2654435761 + 12345) & 0xffffffff
        n=((h>>16)&7)-3
        fac=1.0 + strength*(n/3.5)
        q=[round(max(0.0,min(1.0,float(c)*fac))*31.0)/31.0 for c in base]
        for li in poly.loop_indices:
            ca.data[li].color=(q[0],q[1],q[2],1)
    return o
'''
if helper_anchor not in assets_src:
    raise SystemExit('PASS6: helper insertion anchor missing')
assets_src = assets_src.replace(helper_anchor, helpers + helper_anchor, 1)

# Costume silhouette: narrower upper tunic, volumetric neck/wrist/ankle ruffs,
# and a downward-flaring peplum instead of the PASS5 flat rings.
repls = {
"add(frustum('TunicUpper',(chest.x,chest.y,chest.z-.06*s),(.68*s,.42*s),(.55*s,.36*s),.64*s,IVORY,(.58,.57,.49)),B['sp2'])":
"add(frustum('TunicUpper',(chest.x,chest.y,chest.z-.06*s),(.61*s,.36*s),(.50*s,.31*s),.64*s,IVORY,(.58,.57,.49)),B['sp2'])",
"add(frustum('TunicLower',(pelvis.x,pelvis.y,pelvis.z+.16*s),(.72*s,.46*s),(.56*s,.38*s),.52*s,IVORY,(.58,.57,.49)),B['pelvis'])":
"add(frustum('TunicLower',(pelvis.x,pelvis.y,pelvis.z+.16*s),(.64*s,.40*s),(.53*s,.34*s),.50*s,IVORY,(.58,.57,.49)),B['pelvis'])",
"add(ruff('Peplum',(pelvis.x,pelvis.y,pelvis.z+.12*s),.25*s,.53*s,LIGHT,(.79,.78,.68),18,.20),B['pelvis'])":
"add(skirt_ruff('Peplum',(pelvis.x,pelvis.y,pelvis.z+.09*s),.25*s,.47*s,.20*s,LIGHT,(.79,.78,.68),18,.13),B['pelvis'])",
"add(ruff('PeplumRed',(pelvis.x,pelvis.y,pelvis.z+.10*s),.34*s,.47*s,RED,(.38,.018,.014),18,.13),B['pelvis'])":
"add(skirt_ruff('PeplumRed',(pelvis.x,pelvis.y,pelvis.z+.075*s),.30*s,.42*s,.15*s,RED,(.38,.018,.014),18,.09),B['pelvis'])",
"add(ruff('RuffOuter',(neck.x,neck.y,neck.z-.02*s),.10*s,.38*s,LIGHT,(.79,.78,.68),20,.22),B['neck'])":
"add(ruff_folded('RuffOuter',(neck.x,neck.y,neck.z-.02*s),.10*s,.32*s,.11*s,LIGHT,(.79,.78,.68),18,.16),B['neck'])",
"add(ruff('RuffInner',(neck.x,neck.y,neck.z+.018*s),.09*s,.28*s,IVORY,(.58,.57,.49),18,.18),B['neck'])":
"add(ruff_folded('RuffInner',(neck.x,neck.y,neck.z+.015*s),.085*s,.23*s,.075*s,IVORY,(.58,.57,.49),16,.13),B['neck'])",
"add(ruff('WristRuffL' if side<0 else 'WristRuffR',(h.x,h.y,h.z),.055*s,.14*s,LIGHT,(.79,.78,.68),12,.18),B[keyH])":
"add(ruff_folded('WristRuffL' if side<0 else 'WristRuffR',(h.x,h.y,h.z),.052*s,.125*s,.045*s,LIGHT,(.79,.78,.68),10,.14),B[keyH])",
"if B[keyF]: add(ruff('AnkleRuffL' if side<0 else 'AnkleRuffR',(ft.x,ft.y,ft.z+.02*s),.055*s,.145*s,LIGHT,(.79,.78,.68),12,.18),B[keyF])":
"if B[keyF]: add(ruff_folded('AnkleRuffL' if side<0 else 'AnkleRuffR',(ft.x,ft.y,ft.z+.02*s),.052*s,.130*s,.050*s,LIGHT,(.79,.78,.68),10,.14),B[keyF])",
}
for old,new in repls.items():
    if old not in assets_src:
        raise SystemExit('PASS6: costume anchor missing: '+old[:60])
    assets_src=assets_src.replace(old,new,1)

hair_anchor = "add(ico('HairTop',(head.x,head.y+.06*s,head.z+.27*s),.13*s,HAIR,(.45,.055,.018),scale=(1.25,.86,.75)),B['head'])"
hair_extra = hair_anchor + r'''
# PASS6: back/temple curls fill the silhouette without spike geometry.
for side in (-1,1):
    add(ico('HairBackCurlL' if side<0 else 'HairBackCurlR',(head.x+side*.19*s,head.y+.145*s,head.z+.02*s),.14*s,HAIR,(.45,.055,.018),scale=(.82,1.08,1.22)),B['head'])
    add(ico('HairLowCurlL' if side<0 else 'HairLowCurlR',(head.x+side*.23*s,head.y+.105*s,head.z-.13*s),.115*s,HAIR,(.45,.055,.018),scale=(.88,1.06,.92)),B['head'])
'''
if hair_anchor not in assets_src: raise SystemExit('PASS6: hair anchor missing')
assets_src=assets_src.replace(hair_anchor,hair_extra,1)

mouth_anchor = "for side in (-.045,0,.045):\n    add(box('Tooth',(head.x+side*s,head.y-.224*s,head.z-.073*s),(.030*s,.015*s,.040*s),TEETH,(.82,.78,.61)),B['head'])"
mouth_extra = mouth_anchor + r'''
# Subtle lip corners keep the face readable at 320x240.
for side in (-1,1):
    add(ico('LipCornerL' if side<0 else 'LipCornerR',(head.x+side*.082*s,head.y-.221*s,head.z-.092*s),.026*s,RED,(.50,.01,.008),scale=(1.15,.32,.70)),B['head'])
'''
if mouth_anchor not in assets_src: raise SystemExit('PASS6: mouth anchor missing')
assets_src=assets_src.replace(mouth_anchor,mouth_extra,1)

# Quantized face/cloth variation before the model proof render/export.
penny_anchor = "# Animations.\n"
penny_weather = "for _wi,_wo in enumerate(body+parts): weather(_wo,.07 if _wo in body else .10,_wi*17+9)\n\n# Animations.\n"
if penny_anchor not in assets_src: raise SystemExit('PASS6: animation anchor missing')
assets_src=assets_src.replace(penny_anchor,penny_weather,1)

# Make the corridor read like an N64 sewer: curved rib segments, visible mortar
# cadence, puddle/crack breakup, lamps and a more convincing final drain.
old_rib = '''for i,y in enumerate([.45,1.65,2.85,4.05,5.25,6.45,7.65,8.85,9.75]):
    S(box('RibL%02d'%i,(-1.48,y,1.30),(.18,.16,2.52),TRIM,(.115,.075,.052)))
    S(box('RibR%02d'%i,( 1.48,y,1.30),(.18,.16,2.52),TRIM,(.115,.075,.052)))
    S(box('RibTop%02d'%i,(0,y,2.51),(3.12,.16,.22),TRIM,(.115,.075,.052)))
'''
new_rib = '''for i,y in enumerate([.45,1.65,2.85,4.05,5.25,6.45,7.65,8.85,9.75]):
    S(box('RibL%02d'%i,(-1.48,y,.82),(.16,.15,1.72),TRIM,(.115,.075,.052)))
    S(box('RibR%02d'%i,( 1.48,y,.82),(.16,.15,1.72),TRIM,(.115,.075,.052)))
    pts=[]
    for k in range(7):
        a=math.pi*k/6.0
        pts.append((1.48*math.cos(a),y,1.58+1.02*math.sin(a)))
    for k in range(6):
        S(cyl_between('Arch%02d_%02d'%(i,k),pts[k],pts[k+1],.055,TRIM,(.115,.075,.052),6))
'''
if old_rib not in assets_src: raise SystemExit('PASS6: rib anchor missing')
assets_src=assets_src.replace(old_rib,new_rib,1)

sewer_anchor = "# Circular-ish drain recess on back wall.\nfor x in (-.44,0,.44): S(box('BackGrime',(x,14.70,.78),(.28,.10,.80),MOSS,(.105,.135,.105)))\n"
sewer_extra = sewer_anchor + r'''
# PASS6 wall courses/joints: geometry-backed 'texture' that survives the safe
# untextured Tiny3D material pipeline.
for side in (-1,1):
    x=side*1.515
    for row,z in enumerate((.34,.72,1.10,1.48,1.86,2.24)):
        S(box('MortarH_%d_%02d'%(side,row),(x,5.0,z),(.020,9.85,.025),DARK,(.012,.013,.012)))
        off=.58 if row&1 else .18
        j=0
        y=off
        while y<9.8:
            S(box('MortarV_%d_%02d_%02d'%(side,row,j),(x,y,z-.19),(.021,.032,.36),DARK,(.012,.013,.012)))
            y+=1.25; j+=1

# Chunky damp patches and floor cracks are deliberately irregular and sparse.
for i,(x,y,z,sx,sy,sz) in enumerate([
    (-1.505,2.05,1.92,.025,.72,.34),(1.505,4.55,.92,.025,.58,.52),
    (-1.505,7.55,.62,.025,.82,.42),(1.505,8.70,1.76,.025,.48,.56)]):
    S(box('WetPatch%02d'%i,(x,y,z),(sx,sy,sz),MOSS,(.075,.115,.088)))
for i,(x,y,ang) in enumerate([(-.80,1.65,.15),(.78,3.15,-.12),(-.72,5.45,.08),(.82,7.75,-.10)]):
    crack=box('FloorCrack%02d'%i,(x,y,.025),(.42,.035,.018),DARK,(.012,.013,.012)); crack.rotation_euler[2]=ang; S(crack)

# Repeating ceiling fixtures give the fog/light pools something physical to key off.
for i,y in enumerate((1.05,3.45,5.85,8.25)):
    S(box('LampCase%02d'%i,(0,y,2.52),(.48,.20,.10),TRIM,(.115,.075,.052)))
    S(box('LampFace%02d'%i,(0,y,2.455),(.31,.11,.035),LIGHT,(.62,.60,.42)))

# Final drain/grate silhouette on the boss back wall.
for i,x in enumerate((-.66,-.44,-.22,0,.22,.44,.66)):
    S(cyl_between('DrainBar%02d'%i,(x,14.705,.35),(x,14.705,1.55),.025,METAL,(.055,.060,.057),6))
S(cyl_between('DrainCrossA',(-.78,14.705,.63),(.78,14.705,.63),.030,METAL,(.055,.060,.057),6))
S(cyl_between('DrainCrossB',(-.78,14.705,1.28),(.78,14.705,1.28),.030,METAL,(.055,.060,.057),6))

for _wi,_wo in enumerate(sewer):
    weather(_wo,.18 if ('Wall' in _wo.name or 'Walk' in _wo.name or 'Ceiling' in _wo.name) else .11,_wi*23+5)
'''
if sewer_anchor not in assets_src: raise SystemExit('PASS6: sewer detail anchor missing')
assets_src=assets_src.replace(sewer_anchor,sewer_extra,1)

assets_src = assets_src.replace('PENNYWISE_PASS5_MODEL_PREVIEW.png','PENNYWISE_PASS6_MODEL_PREVIEW.png')
assets_src = assets_src.replace('pennywise_pass5.blend','pennywise_pass6.blend')
assets_src = assets_src.replace('sewer_pass5.blend','sewer_pass6.blend')
assets_src = assets_src.replace("print('PASS5_ASSETS_COMPLETE')","print('PASS6_ASSETS_COMPLETE')")

(ROOT / 'tools' / 'build_assets_pass6.py').write_text(assets_src)

# -----------------------------------------------------------------------------
# Runtime source: actual N64 fog state + nearest ceiling-light pool.  Keep the
# world/weapon scale and gameplay from the final PASS5 branch.
# -----------------------------------------------------------------------------
render_anchor = '''        t3d_screen_clear_color(RGBA32(5, 8, 8, 0xFF));
        t3d_screen_clear_depth();

        uint8_t amb[4] = {36, 44, 42, 255};
        uint8_t dirc[4] = {118, 126, 116, 255};
        fm_vec3_t ldir = {{0.35f, 1.0f, -0.40f}};
        fm_vec3_norm(&ldir, &ldir);
        t3d_light_set_ambient(amb);
        t3d_light_set_directional(0, dirc, &ldir);
        t3d_light_set_count(1);
'''
render_new = '''        t3d_screen_clear_color(RGBA32(5, 8, 8, 0xFF));
        t3d_screen_clear_depth();

        /* PASS6: actual N64/Tiny3D distance fog instead of merely dark geometry. */
        color_t fogColor = (color_t){8, 15, 14, 0xFF};
        rdpq_mode_fog(RDPQ_FOG_STANDARD);
        rdpq_set_fog_color(fogColor);
        t3d_fog_set_range(235.0f, 790.0f);
        t3d_fog_set_enabled(true);

        uint8_t amb[4] = {28, 35, 33, 255};
        uint8_t dirc[4] = {112, 122, 112, 255};
        fm_vec3_t ldir = {{0.35f, 1.0f, -0.40f}};
        fm_vec3_norm(&ldir, &ldir);
        t3d_light_set_ambient(amb);
        t3d_light_set_directional(0, dirc, &ldir);

        /* One cheap flickering point light tracks the nearest physical ceiling lamp. */
        int lampIndex = (int)((-playerPos.v[2] + 64.0f) / 154.0f);
        if (lampIndex < 0) lampIndex = 0;
        if (lampIndex > 4) lampIndex = 4;
        float lampZ = -67.0f - (float)lampIndex * 154.0f;
        float flick = 0.82f + 0.18f * sinf((float)frameCounter * 0.31f + (float)lampIndex);
        uint8_t lamp[4] = {(uint8_t)(142.0f*flick),(uint8_t)(132.0f*flick),(uint8_t)(92.0f*flick),255};
        fm_vec3_t lampPos = {{0.0f, 158.0f, lampZ}};
        t3d_light_set_point(1, lamp, &lampPos, 0.0105f, false);
        t3d_light_set_count(2);
        t3d_light_set_exposure(1.08f);
'''
if render_anchor not in runtime_src:
    raise SystemExit('PASS6: runtime render anchor changed')
runtime_src=runtime_src.replace(render_anchor,render_new,1)

runtime_src=runtime_src.replace('DERRY SEWERS','DERRY STORM DRAIN')
(ROOT / 'src' / 'main_pass6.c').write_text(runtime_src)

print('PASS6 source generated:', ROOT / 'tools' / 'build_assets_pass6.py', ROOT / 'src' / 'main_pass6.c')

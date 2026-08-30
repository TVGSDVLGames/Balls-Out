#!/usr/bin/env python3
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
# Recreate the known-good PASS7 generated source first.
exec((ROOT/'tools/make_pass7_source.py').read_text(), {'__name__':'__main__','__file__':str(ROOT/'tools/make_pass7_source.py')})

p=ROOT/'tools/build_assets_pass7.py'
s=p.read_text()

def req(old,new,label):
    global s
    if old not in s:
        raise SystemExit('PASS8 missing anchor: '+label)
    s=s.replace(old,new,1)

def allrep(old,new):
    global s
    n=s.count(old)
    s=s.replace(old,new)
    return n

# Fix the PASS7 valve helper typo at source generation time.
s=s.replace("S(ruff_folded('ValveWheel',(1.20,8.00,1.45),.12,.27,TRIM,(.115,.075,.052),10,.045))",
            "S(ruff_folded('ValveWheel',(1.20,8.00,1.45),.12,.27,.055,TRIM,(.115,.075,.052),10,.08))")

# -----------------------------------------------------------------------------
# Turok / Doom64 rule: readable surfaces first. PASS7 was technically textured
# but its source pixels + lighting were so dark that the N64 output collapsed.
# Make the 32x32 maps deliberately brighter and more graphic, not realistic.
# -----------------------------------------------------------------------------
repls={
"if mortar:return (24,31,28,255)":"if mortar:return (46,53,49,255)",
"return (49+n//2,61+n,52+n//2+(12 if wet else 0),255)":"return (86+n,96+n,83+n//2+(20 if wet else 0),255)",
"return (44+n//3,54+n//3+(12 if moss else 0),48+n//3,255)":"return (72+n,84+n+(18 if moss else 0),76+n//2,255)",
"if seam:return (25,28,27,255)":"if seam:return (47,50,48,255)",
"return (57+(28 if rust else 0),58-(10 if rust else 0),53-(18 if rust else 0),255)":"return (82+(38 if rust else 0),84-(12 if rust else 0),77-(22 if rust else 0),255)",
"return (8+(8 if wave else 0),38+(18 if wave else 0)+(20 if glint else 0),43+(25 if wave else 0)+(24 if glint else 0),255)":"return (14+(12 if wave else 0),58+(24 if wave else 0)+(24 if glint else 0),72+(30 if wave else 0)+(28 if glint else 0),255)",
"base=151+(8 if weave else 0)-(30 if grime else 0)":"base=188+(10 if weave else 0)-(34 if grime else 0)",
"return (base,base-3,base-14,255) if not seam else (104,102,91,255)":"return (base,base-4,base-18,255) if not seam else (132,128,111,255)",
"return ((95 if seam else 126)-(28 if grime else 0),12,10,255)":"return ((126 if seam else 170)-(34 if grime else 0),18,14,255)",
"n=((x*7+y*3)%11)-5; return (185+n,184+n,166+n,255)":"n=((x*7+y*3)%11)-5; return (216+n,212+n,190+n,255)",
"return (115+(20 if streak else 0),35+(8 if streak else 0),12,255)":"return (148+(24 if streak else 0),48+(12 if streak else 0),16,255)",
"return (86+(18 if grain else 0),44+(8 if grain else 0),20,255)":"return (116+(24 if grain else 0),61+(12 if grain else 0),27,255)",
"r,g,b=(190,188,169) if edge<1 else (150,148,134)":"r,g,b=(222,218,198) if edge<1 else (184,180,162)",
"r,g,b=(28,25,21)":"r,g,b=(24,22,20)",
"r,g,b=(190,118,28)":"r,g,b=(235,154,38)",
"r,g,b=(145,15,12)":"r,g,b=(194,20,15)",
"r,g,b=(158,16,12)":"r,g,b=(205,22,17)",
"r,g,b=(28,20,18)":"r,g,b=(25,17,16)",
"r,g,b=(205,198,165)":"r,g,b=(239,230,192)",
"print('PASS7_TEXTURES', sorted(specs))":"print('PASS8_TEXTURES', sorted(specs))",
}
for old,new in repls.items():
    req(old,new,'texture '+old[:28])

# Chunkier UV cadence: a real N64 wall should show obvious 32x32 repetition.
if allrep('auto_uv(o,2.2)','auto_uv(o,1.28)') < 2:
    raise SystemExit('PASS8 UV anchors changed')

# Stronger palette separation for vertex shading / Blender proof.
palette={
"SKIN   = make_mat('DeadlightSkin', (0.72,0.73,0.67), .82)":"SKIN   = make_mat('DeadlightSkin', (0.84,0.83,0.75), .82)",
"IVORY  = make_mat('OldIvoryCloth', (0.58,0.57,0.49), .92)":"IVORY  = make_mat('OldIvoryCloth', (0.78,0.76,0.66), .92)",
"LIGHT  = make_mat('DirtyRuffle',   (0.79,0.78,0.68), .92)":"LIGHT  = make_mat('DirtyRuffle',   (0.91,0.89,0.77), .92)",
"RED    = make_mat('CrimsonCloth',  (0.38,0.018,0.014), .86)":"RED    = make_mat('CrimsonCloth',  (0.62,0.028,0.020), .86)",
"HAIR   = make_mat('BurntHair',     (0.45,0.055,0.018), .94)":"HAIR   = make_mat('BurntHair',     (0.62,0.12,0.025), .94)",
"DARK   = make_mat('Shadow',        (0.012,0.013,0.012), .96)":"DARK   = make_mat('Shadow',        (0.035,0.040,0.038), .96)",
"EYE    = make_mat('AmberEye',      (0.72,0.38,0.035), .38)":"EYE    = make_mat('AmberEye',      (0.96,0.58,0.08), .38)",
"TEETH  = make_mat('Teeth',         (0.82,0.78,0.61), .78)":"TEETH  = make_mat('Teeth',         (0.93,0.88,0.69), .78)",
"BRICK  = make_mat('WetBrick',      (0.085,0.115,0.100), .96)":"BRICK  = make_mat('WetBrick',      (0.20,0.24,0.21), .96)",
"MOSS   = make_mat('MossStone',     (0.105,0.135,0.105), .98)":"MOSS   = make_mat('MossStone',     (0.18,0.25,0.19), .98)",
"TRIM   = make_mat('IronRust',      (0.115,0.075,0.052), .94)":"TRIM   = make_mat('IronRust',      (0.26,0.16,0.10), .94)",
"WATER  = make_mat('BlackWater',    (0.010,0.075,0.082), .28)":"WATER  = make_mat('BlackWater',    (0.025,0.15,0.19), .28)",
"METAL  = make_mat('Iron',          (0.055,0.060,0.057), .78)":"METAL  = make_mat('Iron',          (0.16,0.18,0.17), .78)",
"WOOD   = make_mat('SlingshotWood', (0.23,0.105,0.045), .82)":"WOOD   = make_mat('SlingshotWood', (0.34,0.17,0.065), .82)",
}
for old,new in palette.items(): req(old,new,'palette')

# Bright, shade-only fixture materials. Unknown material names are intentionally
# left untextured by pass7_materials.py, so they cannot trigger hidden PNG loads.
req("BALLOON= make_mat('BalloonRed',    (0.62,0.018,0.014), .30)\n",
    "BALLOON= make_mat('BalloonRed',    (0.76,0.025,0.018), .30)\nCYAN   = make_mat('SewerLampCyan', (0.34,0.82,0.76), .32)\nBOSSGLOW=make_mat('BossRedGlow',   (0.92,0.10,0.045), .32)\n",
    'glow materials')

# Make Blender proof use the same tiny texture ideas instead of flat materials.
texture_preview=r'''
def preview_tex(material, filename):
    try:
        img=bpy.data.images.load(os.path.join(args.out,filename),check_existing=True)
        nt=material.node_tree; bs=nt.nodes.get('Principled BSDF')
        tex=nt.nodes.new('ShaderNodeTexImage'); tex.image=img; tex.interpolation='Linear'
        nt.links.new(tex.outputs['Color'],bs.inputs['Base Color'])
    except Exception as e: print('PREVIEW_TEX_WARN',material.name,filename,repr(e))
for _m,_f in [(IVORY,'cloth.png'),(RED,'redcloth.png'),(HAIR,'hair.png'),(FACE,'face.png'),(BRICK,'brick.png'),(MOSS,'stone.png'),(TRIM,'metal.png'),(METAL,'metal.png'),(WATER,'water.png'),(WOOD,'wood.png')]:
    preview_tex(_m,_f)
'''
anchor="FACE   = make_mat('PennyFaceTex',  (0.72,0.70,0.62), .82)\n"
req(anchor,anchor.replace('(0.72,0.70,0.62)','(0.88,0.86,0.78)')+texture_preview,'preview texture anchor')

# -----------------------------------------------------------------------------
# Character rebuild: stop wrapping the real humanoid in huge primitive boxes.
# Keep the genuine skinned SuperHero mesh as the silhouette and let a low-res
# cloth texture + a few strong clown shapes do the work, like actual N64 enemies.
# -----------------------------------------------------------------------------
req("    paint(o,SKIN,(.72,.73,.67))","    paint(o,IVORY,(.78,.76,.66))",'base humanoid cloth')

add_old="""parts=[]
def add(o,bone):
    parts.append(o); bind(o,arm,bone); return o
"""
add_new="""parts=[]
PASS8_SKIP=('TunicUpper','TunicLower','Peplum','PeplumRed','SleevePuff','ForearmCloth','Bloomer','Stocking','FrontPiping','PennyFacePatch')
def add(o,bone):
    # PASS8: the coherent rigged human is the costume silhouette. Delete the
    # oversized PASS5/6 primitive shells that made him look like a cardboard doll.
    if any(o.name.startswith(x) for x in PASS8_SKIP):
        bpy.data.objects.remove(o,do_unlink=True)
        return None
    parts.append(o); bind(o,arm,bone); return o
"""
req(add_old,add_new,'add skip primitive shells')

# Thin the remaining accents rather than layering another bulky body on top.
for old,new in [
("(.71*s,.47*s,.075*s)","(.56*s,.33*s,.055*s)"),
(".052*s,.125*s,.045*s",".048*s,.105*s,.040*s"),
(".06*s,.12*s,RED",".055*s,.095*s,RED"),
(".052*s,.130*s,.050*s",".048*s,.108*s,.042*s"),
(".16*s,DARK",".13*s,DARK"),
("scale=(.72,1.55,.52)","scale=(.66,1.32,.46)"),
]:
    s=s.replace(old,new)

# Replace the flat rectangular face patch with a 12-sided tapered head shell
# carrying the same hand-painted 64x64 face. Original rigged head stays inside.
face_start=s.index("# Face: N64-style curved low-poly mask")
face_end=s.index("# Three front ornaments",face_start)
head_block=r'''# PASS8 textured low-poly clown head: tapered jaw, wider forehead, 12-sided rings.
def clown_head(name, center, scale, material):
    cx,cy,cz=center; seg=12
    # z offset, horizontal radius, front/back radius
    rings=[(-.25,.105,.115),(-.16,.155,.145),(-.03,.185,.165),(.11,.190,.160),(.23,.150,.135),(.30,.080,.085)]
    v=[]; uvv=[]
    for ri,(zz,rx,ry) in enumerate(rings):
        for j in range(seg):
            a=math.tau*j/seg
            v.append((cx+math.cos(a)*rx*scale,cy+math.sin(a)*ry*scale,cz+zz*scale))
            # Front (-Y, angle -pi/2) lands at u=.5 where the painted face lives.
            u=((a+math.pi/2)/math.tau+.5)%1.0
            uvv.append((u,1.0-ri/(len(rings)-1)))
    f=[]
    for ri in range(len(rings)-1):
        for j in range(seg):
            a=ri*seg+j; b=ri*seg+(j+1)%seg; c=(ri+1)*seg+(j+1)%seg; d=(ri+1)*seg+j
            f.append((a,b,c,d))
    o=mesh(name,v,f,material,(.88,.86,.78))
    uv=o.data.uv_layers.get('UVMap') or o.data.uv_layers.new(name='UVMap')
    # mesh quads preserve vertex order; assign UV by loop vertex index.
    for poly in o.data.polygons:
        for li in poly.loop_indices:
            uv.data[li].uv=uvv[o.data.loops[li].vertex_index]
    return o
add(clown_head('PennyHead',(head.x,head.y-.005*s,head.z),s,FACE),B['head'])
# Physical nose survives the low resolution and breaks the head silhouette.
add(ico('Nose',(head.x,head.y-.174*s,head.z-.005*s),.050*s,RED,(.72,.03,.02),scale=(.92,.62,.92)),B['head'])

'''
s=s[:face_start]+head_block+s[face_end:]

# Smaller, swept hair volumes around the new head instead of orange helmet blocks.
hair_repls={
".19*s, HAIR":".150*s, HAIR",
".16*s, HAIR":".128*s, HAIR",
".13*s, HAIR":".105*s, HAIR",
".14*s,HAIR":".115*s,HAIR",
".115*s,HAIR":".095*s,HAIR",
}
for old,new in hair_repls.items(): s=s.replace(old,new)

# Natural-arm animation baseline. PASS7's frame-1 bind pose was a T-pose, which
# is a huge reason the model never read like a commercial N64 enemy.
old_acts="""acts=[
 action('Penny_Idle',[(1,{}),(16,{'sp2':(-.045,0,.015),'head':(.04,0,-.025)}),(31,{})]),
 action('Penny_Walk',[(1,{'tl':(.48,0,0),'tr':(-.48,0,0),'ual':(-.30,0,.06),'uar':(.30,0,-.06)}),(10,{'tl':(-.48,0,0),'tr':(.48,0,0),'ual':(.30,0,-.06),'uar':(-.30,0,.06)}),(19,{'tl':(.48,0,0),'tr':(-.48,0,0)})]),
 action('Penny_Attack',[(1,{}),(7,{'sp2':(-.34,0,0),'ual':(-1.18,0,.25),'uar':(-1.18,0,-.25),'lal':(-.62,0,0),'lar':(-.62,0,0),'head':(.19,0,0)}),(14,{})]),
 action('Penny_Hurt',[(1,{}),(5,{'sp2':(.40,0,.15),'head':(-.36,0,-.18),'ual':(.30,0,.42),'uar':(.30,0,-.42)}),(11,{})]),
 action('Penny_Death',[(1,{}),(14,{'sp2':(.38,0,.28),'head':(-.46,0,0)}),(28,{'pelvis':(0,1.47,0),'sp2':(.68,0,.42),'head':(-.72,0,0)})])]
"""
new_acts="""downL=(0.0,-.08,-1.02); downR=(0.0,.08,1.02)
acts=[
 action('Penny_Idle',[(1,{'ual':downL,'uar':downR,'lal':(-.10,0,0),'lar':(-.10,0,0)}),(16,{'ual':(0,-.08,-.97),'uar':(0,.08,.97),'lal':(-.15,0,0),'lar':(-.15,0,0),'sp2':(-.045,0,.015),'head':(.04,0,-.025)}),(31,{'ual':downL,'uar':downR})]),
 action('Penny_Walk',[(1,{'tl':(.48,0,0),'tr':(-.48,0,0),'ual':(-.22,-.08,-1.02),'uar':(.22,.08,1.02)}),(10,{'tl':(-.48,0,0),'tr':(.48,0,0),'ual':(.22,-.08,-1.02),'uar':(-.22,.08,1.02)}),(19,{'tl':(.48,0,0),'tr':(-.48,0,0),'ual':(-.22,-.08,-1.02),'uar':(.22,.08,1.02)})]),
 action('Penny_Attack',[(1,{'ual':downL,'uar':downR}),(7,{'sp2':(-.34,0,0),'ual':(-1.12,-.08,-.28),'uar':(-1.12,.08,.28),'lal':(-.62,0,0),'lar':(-.62,0,0),'head':(.19,0,0)}),(14,{'ual':downL,'uar':downR})]),
 action('Penny_Hurt',[(1,{'ual':downL,'uar':downR}),(5,{'sp2':(.40,0,.15),'head':(-.36,0,-.18),'ual':(.18,-.08,-.78),'uar':(.18,.08,.78)}),(11,{'ual':downL,'uar':downR})]),
 action('Penny_Death',[(1,{'ual':downL,'uar':downR}),(14,{'sp2':(.38,0,.28),'head':(-.46,0,0),'ual':(.25,-.08,-.72),'uar':(.25,.08,.72)}),(28,{'pelvis':(0,1.47,0),'sp2':(.68,0,.42),'head':(-.72,0,0)})])]
"""
req(old_acts,new_acts,'animation T-pose replacement')

# Apply idle frame before proof render so the preview is no longer a T-pose.
req("bpy.context.scene.frame_set(1)\nbpy.ops.object.camera_add(location=(2.8,-5.8,1.35));",
    "bpy.context.scene.frame_set(1)\narm.animation_data.action=acts[0]\nbpy.context.scene.frame_set(2)\nbpy.ops.object.camera_add(location=(2.25,-5.1,1.45));",
    'preview pose')

# -----------------------------------------------------------------------------
# Environment: brighter physical light panels, larger landmarks and color cues.
# -----------------------------------------------------------------------------
s=s.replace("S(box('LampFace%02d'%i,(0,y,2.455),(.31,.11,.035),LIGHT,(.62,.60,.42)))",
            "S(box('LampFace%02d'%i,(0,y,2.455),(.42,.13,.045),CYAN,(.72,.94,.88)))")

save_anchor="bpy.ops.wm.save_as_mainfile(filepath=os.path.join(args.out,'sewer_pass7.blend'))"
extra_env=r'''# PASS8: readable Turok/Doom64-style landmarks and color anchors.
# Cyan wall strips around the middle section; these stay shade-only and bright.
for i,(side,y) in enumerate([(-1,2.15),(1,4.55),(-1,6.95),(1,9.05)]):
    x=side*1.505
    S(box('CyanGuide%02d'%i,(x,y,1.28),(.035,.58,.10),CYAN,(.66,.91,.85)))
# Boss chamber red warning strips / stronger final composition.
for i,x in enumerate((-1.82,1.82)):
    S(box('BossGlowV%02d'%i,(x,12.65,1.35),(.09,.18,2.18),BOSSGLOW,(.90,.10,.045)))
for i,y in enumerate((10.42,14.62)):
    S(box('BossGlowH%02d'%i,(0,y,2.44),(3.45,.10,.09),BOSSGLOW,(.90,.10,.045)))
# A chunky central storm-drain arch at the boss back wall, readable at 320x240.
for k in range(9):
    a=math.pi*k/8.0
    x=1.05*math.cos(a); z=.66+1.05*math.sin(a)
    S(cyl_between('BossDrainArch%02d'%k,(x-.10,14.68,z),(x+.10,14.68,z),.045,METAL,(.22,.24,.23),6))
# Two broad damp floor patches catch the brighter lighting and break the flat runway.
S(box('WetFloorA',(-.78,5.10,.018),(.66,1.20,.025),MOSS,(.20,.30,.23)))
S(box('WetFloorB',(.76,8.25,.018),(.74,.98,.025),MOSS,(.20,.30,.23)))
'''
req(save_anchor,extra_env+"\n"+save_anchor.replace('sewer_pass7.blend','sewer_pass8.blend'),'environment insertion')

# Rename proof/save artifacts and completion marker.
s=s.replace('PENNYWISE_PASS7_MODEL_PREVIEW.png','PENNYWISE_PASS8_MODEL_PREVIEW.png')
s=s.replace('pennywise_pass7.blend','pennywise_pass8.blend')
s=s.replace("print('PASS7_ASSETS_COMPLETE')","print('PASS8_ASSETS_COMPLETE')")

(ROOT/'tools/build_assets_pass8.py').write_text(s)

# -----------------------------------------------------------------------------
# Runtime: much brighter than PASS7, wider fog range, two light directions and
# exposure boost. Darkness is now reserved for corners, not the entire frame.
# -----------------------------------------------------------------------------
c=(ROOT/'src/main_pass7.c').read_text()
c=c.replace('PENNYWISE 64 P7','PENNYWISE 64 P8')
c=c.replace('67.0f * DEG2RAD','72.0f * DEG2RAD')
c=c.replace('RGBA32(5, 8, 8, 0xFF)','RGBA32(12, 19, 21, 0xFF)')
c=c.replace('(color_t){8, 15, 14, 0xFF}','(color_t){29, 43, 42, 0xFF}')
c=c.replace('t3d_fog_set_range(205.0f, 700.0f);','t3d_fog_set_range(340.0f, 900.0f);')
c=c.replace('uint8_t amb[4] = {30, 35, 33, 255};','uint8_t amb[4] = {82, 92, 87, 255};')
c=c.replace('uint8_t dirc[4] = {102, 108, 99, 255};','uint8_t dirc[4] = {168, 178, 163, 255};')
# Add a cooler opposing fill and exposure after the first directional light.
light_anchor="""        t3d_light_set_directional(0, dirc, &ldir);
        t3d_light_set_count(1);
"""
light_new="""        t3d_light_set_directional(0, dirc, &ldir);
        uint8_t fillc[4] = {76, 106, 112, 255};
        fm_vec3_t filldir = {{-0.75f, 0.42f, 0.28f}};
        fm_vec3_norm(&filldir, &filldir);
        t3d_light_set_directional(1, fillc, &filldir);
        t3d_light_set_count(2);
        t3d_light_set_exposure(1.35f);
"""
if light_anchor not in c: raise SystemExit('PASS8 runtime light anchor changed')
c=c.replace(light_anchor,light_new,1)
# Taller / leaner Pennywise reads more like a Turok enemy and less like a doll.
c=c.replace("t3d_mat4fp_from_srt_euler(&pennyMat[frame], (float[3]){1,1,1},",
            "t3d_mat4fp_from_srt_euler(&pennyMat[frame], (float[3]){0.92f,1.10f,0.92f},")
(ROOT/'src/main_pass8.c').write_text(c)

# Boss-proof runtime from the same code/assets, used only for an actual emulator
# close encounter capture. The distributed main ROM still starts normally.
b=c
b=b.replace("static fm_vec3_t playerPos = {{0.0f, 104.0f, 20.0f}};","static fm_vec3_t playerPos = {{0.0f, 104.0f, -710.0f}};")
b=b.replace("static fm_vec3_t pennyPos = {{0.0f, 0.0f, -850.0f}};","static fm_vec3_t pennyPos = {{0.0f, 0.0f, -805.0f}};")
b=b.replace("static bool bossStarted = false;","static bool bossStarted = true;",1)
b=b.replace("static EnemyState enemyState = ENEMY_HIDDEN;","static EnemyState enemyState = ENEMY_IDLE;",1)
(ROOT/'src/main_pass8_bossproof.c').write_text(b)

# Makefile generated by PASS7 already knows PNG->sprite and T3DM conversion.
m=(ROOT/'Makefile').read_text()
m=m.replace('src = src/main_pass7.c','src = src/main_pass8.c')
m=m.replace('PENNYWISE64_PASS7','PENNYWISE64_PASS8')
m=m.replace('PENNYWISE 64 P7','PENNYWISE 64 P8')
(ROOT/'Makefile').write_text(m)

print('PASS8_SOURCE_READY')

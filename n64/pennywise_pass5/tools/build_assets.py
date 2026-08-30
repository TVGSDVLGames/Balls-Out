import bpy, sys, os, math, argparse, json, struct, copy
from mathutils import Vector

argv = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument('--base', required=True)
ap.add_argument('--out', required=True)
ap.add_argument('--template-glb', required=True)
args = ap.parse_args(argv)
os.makedirs(args.out, exist_ok=True)

def clear():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)

def norm(s):
    return (s or '').lower().replace('.','_').replace('-','_').replace(' ','_')

def findbone(arm, *names):
    table = {norm(b.name): b.name for b in arm.data.bones}
    for n in names:
        if norm(n) in table:
            return table[norm(n)]
    for n in names:
        nn = norm(n)
        for k,v in table.items():
            if nn in k or k.endswith(nn):
                return v
    return None

def bone_head(arm, name):
    b = arm.data.bones.get(name) if name else None
    return arm.matrix_world @ b.head_local if b else Vector((0,0,0))

def bone_tail(arm, name):
    b = arm.data.bones.get(name) if name else None
    return arm.matrix_world @ b.tail_local if b else Vector((0,0,0))

def bone_mid(arm, name):
    return (bone_head(arm,name) + bone_tail(arm,name)) * 0.5

def make_mat(name, color, rough=.72):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.diffuse_color = (*color, 1)
    p = m.node_tree.nodes.get('Principled BSDF')
    if p:
        p.inputs['Base Color'].default_value = (*color,1)
        if 'Roughness' in p.inputs:
            p.inputs['Roughness'].default_value = rough
    return m

SKIN   = make_mat('DeadlightSkin', (0.72,0.73,0.67), .82)
IVORY  = make_mat('OldIvoryCloth', (0.58,0.57,0.49), .92)
LIGHT  = make_mat('DirtyRuffle',   (0.79,0.78,0.68), .92)
RED    = make_mat('CrimsonCloth',  (0.38,0.018,0.014), .86)
HAIR   = make_mat('BurntHair',     (0.45,0.055,0.018), .94)
DARK   = make_mat('Shadow',        (0.012,0.013,0.012), .96)
EYE    = make_mat('AmberEye',      (0.72,0.38,0.035), .38)
TEETH  = make_mat('Teeth',         (0.82,0.78,0.61), .78)
BRICK  = make_mat('WetBrick',      (0.085,0.115,0.100), .96)
MOSS   = make_mat('MossStone',     (0.105,0.135,0.105), .98)
TRIM   = make_mat('IronRust',      (0.115,0.075,0.052), .94)
WATER  = make_mat('BlackWater',    (0.010,0.075,0.082), .28)
METAL  = make_mat('Iron',          (0.055,0.060,0.057), .78)
WOOD   = make_mat('SlingshotWood', (0.23,0.105,0.045), .82)
RUBBER = make_mat('Rubber',        (0.015,0.012,0.010), .92)
SILVER = make_mat('Silver',        (0.46,0.49,0.47), .38)
BALLOON= make_mat('BalloonRed',    (0.62,0.018,0.014), .30)

def paint(o, material, color):
    if o.type != 'MESH': return o
    o.data.materials.clear()
    o.data.materials.append(material)
    try:
        while o.data.color_attributes:
            o.data.color_attributes.remove(o.data.color_attributes[0])
        ca = o.data.color_attributes.new(name='Col', type='BYTE_COLOR', domain='CORNER')
        for x in ca.data:
            x.color = (*color, 1)
    except Exception as e:
        print('VCOL_WARN', o.name, repr(e))
    return o

def mesh(name, verts, faces, material, color):
    me = bpy.data.meshes.new(name+'Mesh')
    me.from_pydata(verts, [], faces)
    me.update()
    o = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(o)
    return paint(o, material, color)

def box(name, p, s, material, color):
    x,y,z = p
    a,b,c = s[0]/2, s[1]/2, s[2]/2
    v = [(x-a,y-b,z-c),(x+a,y-b,z-c),(x+a,y+b,z-c),(x-a,y+b,z-c),
         (x-a,y-b,z+c),(x+a,y-b,z+c),(x+a,y+b,z+c),(x-a,y+b,z+c)]
    f = [(0,1,2,3),(4,7,6,5),(0,4,5,1),(1,5,6,2),(2,6,7,3),(4,0,3,7)]
    return mesh(name,v,f,material,color)

def frustum(name, p, bottom, top, h, material, color):
    x,y,z = p
    bx,by = bottom[0]/2,bottom[1]/2
    tx,ty = top[0]/2,top[1]/2
    zl,zh = z-h/2,z+h/2
    v=[(x-bx,y-by,zl),(x+bx,y-by,zl),(x+bx,y+by,zl),(x-bx,y+by,zl),
       (x-tx,y-ty,zh),(x+tx,y-ty,zh),(x+tx,y+ty,zh),(x-tx,y+ty,zh)]
    f=[(0,1,2,3),(4,7,6,5),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)]
    return mesh(name,v,f,material,color)

def ico(name, p, radius, material, color, scale=(1,1,1), subdivisions=1):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=subdivisions, radius=radius, location=p)
    o=bpy.context.object; o.name=name
    o.scale=scale
    bpy.context.view_layer.objects.active=o
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return paint(o,material,color)

def cyl(name, p, radius, depth, material, color, verts=8):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=radius, depth=depth, location=p)
    o=bpy.context.object; o.name=name
    return paint(o,material,color)

def cyl_between(name, a, b, radius, material, color, verts=8):
    a,b=Vector(a),Vector(b)
    d=b-a
    o=cyl(name,(a+b)*0.5,radius,d.length,material,color,verts)
    o.rotation_euler=d.to_track_quat('Z','Y').to_euler()
    return o

def ruff(name, p, inner, outer, material, color, points=16, wobble=.16):
    x,y,z=p; v=[]
    for i in range(points):
        a=math.tau*i/points
        rr=outer*(1+wobble*(1 if i&1 else -1))
        v.append((x+math.cos(a)*inner,y+math.sin(a)*inner,z))
        v.append((x+math.cos(a)*rr,y+math.sin(a)*rr,z))
    f=[]
    for i in range(points):
        j=(i+1)%points
        f.append((2*i,2*j,2*j+1,2*i+1))
    return mesh(name,v,f,material,color)

def bind(o, arm, bone):
    if not bone or o.type!='MESH': return
    mod=o.modifiers.new('Armature','ARMATURE'); mod.object=arm
    vg=o.vertex_groups.new(name=bone)
    vg.add(list(range(len(o.data.vertices))),1.0,'REPLACE')

def look(o, target):
    o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()

def read_glb(path):
    data=open(path,'rb').read()
    magic,ver,total=struct.unpack_from('<4sII',data,0)
    if magic!=b'glTF' or ver!=2: raise RuntimeError('Not GLB2: '+path)
    off=12; chunks=[]
    while off<total:
        ln,typ=struct.unpack_from('<II',data,off); off+=8
        chunks.append([typ,data[off:off+ln]]); off+=ln
    ji=next(i for i,c in enumerate(chunks) if c[0]==0x4E4F534A)
    doc=json.loads(chunks[ji][1].rstrip(b' \t\r\n\0').decode('utf8'))
    return doc,chunks,ji

def write_glb(path,doc,chunks,ji):
    raw=json.dumps(doc,separators=(',',':'),ensure_ascii=False).encode('utf8')
    raw += b' ' * ((4-len(raw)%4)%4)
    chunks[ji][1]=raw
    body=b''.join(struct.pack('<II',len(c[1]),c[0])+c[1] for c in chunks)
    open(path,'wb').write(struct.pack('<4sII',b'glTF',2,12+len(body))+body)

def inject_f3d(path, template):
    td,_,_=read_glb(template)
    candidates=[]
    for m in td.get('materials',[]):
        f=m.get('extras',{}).get('f3d_mat')
        if f is None: continue
        txt=json.dumps(f).upper()
        # Prefer a texture-free shade material, which preserves our vertex colors.
        score=(0 if 'SHADE' in txt else 50) + (500 if '.PNG' in txt or '"TEX"' in txt else 0) + len(txt)/1000000.0
        candidates.append((score,f,m.get('name','?')))
    if not candidates: raise RuntimeError('Template GLB has no Fast64 material metadata')
    candidates.sort(key=lambda x:x[0])
    f3d=copy.deepcopy(candidates[0][1])
    print('F3D_TEMPLATE',candidates[0][2],'score',candidates[0][0])
    doc,chunks,ji=read_glb(path)
    if not doc.get('materials'): doc['materials']=[{'name':'N64_Shaded'}]
    for m in doc['materials']:
        m.setdefault('extras',{})['f3d_mat']=copy.deepcopy(f3d)
    write_glb(path,doc,chunks,ji)

def export_glb(path, selection, animations=False):
    bpy.ops.object.select_all(action='DESELECT')
    for o in selection: o.select_set(True)
    if selection: bpy.context.view_layer.objects.active=selection[0]
    kw=dict(filepath=path,export_format='GLB',use_selection=True,export_animations=animations,export_extras=True)
    if animations: kw['export_nla_strips']=True
    try:
        kw['export_colors']=True
        bpy.ops.export_scene.gltf(**kw)
    except TypeError:
        kw.pop('export_colors',None); kw.pop('export_nla_strips',None)
        bpy.ops.export_scene.gltf(**kw)
    inject_f3d(path,args.template_glb)

# -----------------------------------------------------------------------------
# PENNYWISE - genuine CC0 skinned human plus low-poly antique clown costume.
# -----------------------------------------------------------------------------
clear()
bpy.ops.import_scene.gltf(filepath=args.base)
arm=next((o for o in bpy.context.scene.objects if o.type=='ARMATURE'),None)
if not arm: raise RuntimeError('No armature in humanoid source')
arm.name='PennywiseRig'
body=[o for o in bpy.context.scene.objects if o.type=='MESH']
print('SOURCE_MESHES',[(o.name,len(o.data.polygons)) for o in body])
for o in body:
    tris=sum(max(0,len(p.vertices)-2) for p in o.data.polygons)
    if tris>2200:
        bpy.context.view_layer.objects.active=o; o.select_set(True)
        dec=o.modifiers.new('N64_LOD','DECIMATE'); dec.ratio=max(.20,1800.0/tris)
        try: bpy.ops.object.modifier_apply(modifier=dec.name)
        except Exception as e: print('DECIMATE_WARN',o.name,repr(e))
    paint(o,SKIN,(.72,.73,.67))

B={
 'pelvis':findbone(arm,'pelvis','hips'), 'sp1':findbone(arm,'spine_01','spine_1','spine'),
 'sp2':findbone(arm,'spine_02','chest'), 'neck':findbone(arm,'neck_01','neck'), 'head':findbone(arm,'head'),
 'ual':findbone(arm,'upperarm_l','upper_arm_l'), 'uar':findbone(arm,'upperarm_r','upper_arm_r'),
 'lal':findbone(arm,'lowerarm_l','forearm_l'), 'lar':findbone(arm,'lowerarm_r','forearm_r'),
 'hl':findbone(arm,'hand_l'), 'hr':findbone(arm,'hand_r'),
 'tl':findbone(arm,'thigh_l'), 'tr':findbone(arm,'thigh_r'),
 'sl':findbone(arm,'calf_l','shin_l','lowerleg_l'), 'sr':findbone(arm,'calf_r','shin_r','lowerleg_r'),
 'fl':findbone(arm,'foot_l'), 'fr':findbone(arm,'foot_r')
}
print('BONE_MAP',B)
head=bone_mid(arm,B['head']); neck=bone_head(arm,B['head']); chest=bone_mid(arm,B['sp2']); pelvis=bone_mid(arm,B['pelvis'])
height=max((arm.matrix_world@b.head_local).z for b in arm.data.bones)-min((arm.matrix_world@b.head_local).z for b in arm.data.bones)
s=max(.75,height/1.9)
parts=[]
def add(o,bone):
    parts.append(o); bind(o,arm,bone); return o

# Tunic and waist layers.
add(frustum('TunicUpper',(chest.x,chest.y,chest.z-.06*s),(.68*s,.42*s),(.55*s,.36*s),.64*s,IVORY,(.58,.57,.49)),B['sp2'])
add(frustum('TunicLower',(pelvis.x,pelvis.y,pelvis.z+.16*s),(.72*s,.46*s),(.56*s,.38*s),.52*s,IVORY,(.58,.57,.49)),B['pelvis'])
add(box('CrimsonWaist',(pelvis.x,pelvis.y-.005*s,pelvis.z+.20*s),(.71*s,.47*s,.075*s),RED,(.38,.018,.014)),B['pelvis'])
add(ruff('Peplum',(pelvis.x,pelvis.y,pelvis.z+.12*s),.25*s,.53*s,LIGHT,(.79,.78,.68),18,.20),B['pelvis'])
add(ruff('PeplumRed',(pelvis.x,pelvis.y,pelvis.z+.10*s),.34*s,.47*s,RED,(.38,.018,.014),18,.13),B['pelvis'])

# Double neck ruff.
add(ruff('RuffOuter',(neck.x,neck.y,neck.z-.02*s),.10*s,.38*s,LIGHT,(.79,.78,.68),20,.22),B['neck'])
add(ruff('RuffInner',(neck.x,neck.y,neck.z+.018*s),.09*s,.28*s,IVORY,(.58,.57,.49),18,.18),B['neck'])

# Sleeves: puffs on upper arms, fitted forearms, wrist ruffles.
for side,keyU,keyL,keyH in [(-1,'ual','lal','hl'),(1,'uar','lar','hr')]:
    u=bone_mid(arm,B[keyU]); l0=bone_head(arm,B[keyL]); l1=bone_tail(arm,B[keyL]); h=bone_mid(arm,B[keyH])
    add(ico('SleevePuffL' if side<0 else 'SleevePuffR',u,.22*s,IVORY,(.58,.57,.49),scale=(1.10,.88,.86)),B[keyU])
    add(cyl_between('ForearmClothL' if side<0 else 'ForearmClothR',l0,l1,.105*s,IVORY,(.58,.57,.49),8),B[keyL])
    add(ruff('WristRuffL' if side<0 else 'WristRuffR',(h.x,h.y,h.z),.055*s,.14*s,LIGHT,(.79,.78,.68),12,.18),B[keyH])
    # red piping band at upper-arm edge
    p=bone_tail(arm,B[keyU])
    add(ruff('ArmBandL' if side<0 else 'ArmBandR',(p.x,p.y,p.z),.06*s,.12*s,RED,(.38,.018,.014),10,.05),B[keyU])

# Bloomers, stockings and ankle ruffs.
for side,keyT,keyS,keyF in [(-1,'tl','sl','fl'),(1,'tr','sr','fr')]:
    tm=bone_mid(arm,B[keyT]); sh0=bone_head(arm,B[keyS]); sh1=bone_tail(arm,B[keyS]); ft=bone_head(arm,B[keyF])
    add(ico('BloomerL' if side<0 else 'BloomerR',tm,.24*s,IVORY,(.58,.57,.49),scale=(.88,.84,1.15)),B[keyT])
    if B[keyS]: add(cyl_between('StockingL' if side<0 else 'StockingR',sh0,sh1,.095*s,IVORY,(.58,.57,.49),8),B[keyS])
    if B[keyF]: add(ruff('AnkleRuffL' if side<0 else 'AnkleRuffR',(ft.x,ft.y,ft.z+.02*s),.055*s,.145*s,LIGHT,(.79,.78,.68),12,.18),B[keyF])
    if B[keyF]:
        shoe=ico('ClownShoeL' if side<0 else 'ClownShoeR',(ft.x,ft.y-.09*s,ft.z-.045*s),.16*s,DARK,(.012,.013,.012),scale=(.72,1.55,.52))
        add(shoe,B[keyF])

# Hair masses: rounded swept-back antique-clown silhouette, no triangle spikes.
for side in (-1,1):
    add(ico('HairSideA', (head.x+side*.22*s,head.y+.025*s,head.z+.10*s), .19*s, HAIR,(.45,.055,.018),scale=(.82,1.05,1.20)),B['head'])
    add(ico('HairSideB', (head.x+side*.25*s,head.y+.045*s,head.z-.04*s), .16*s, HAIR,(.45,.055,.018),scale=(.92,1.10,.98)),B['head'])
    add(ico('HairTemple', (head.x+side*.17*s,head.y-.025*s,head.z+.20*s), .13*s, HAIR,(.45,.055,.018),scale=(.78,.92,1.04)),B['head'])
# top central widow crest
add(ico('HairTop',(head.x,head.y+.06*s,head.z+.27*s),.13*s,HAIR,(.45,.055,.018),scale=(1.25,.86,.75)),B['head'])

# Face: small physical layers rather than a flat texture.
add(ico('Nose',(head.x,head.y-.188*s,head.z+.01*s),.060*s,RED,(.50,.01,.008)),B['head'])
for side in (-1,1):
    add(ico('EyeWhiteL' if side<0 else 'EyeWhiteR',(head.x+side*.067*s,head.y-.193*s,head.z+.092*s),.034*s,TEETH,(.82,.78,.61),scale=(1.15,.40,.78)),B['head'])
    add(ico('EyeAmberL' if side<0 else 'EyeAmberR',(head.x+side*.067*s,head.y-.208*s,head.z+.092*s),.018*s,EYE,(.72,.38,.035),scale=(1.0,.42,1.0)),B['head'])
    # rising red eye-to-mouth paint stroke
    a=(head.x+side*.085*s,head.y-.211*s,head.z+.055*s)
    b=(head.x+side*.115*s,head.y-.211*s,head.z-.075*s)
    add(cyl_between('FacePaintL' if side<0 else 'FacePaintR',a,b,.012*s,RED,(.50,.01,.008),6),B['head'])
add(ico('Mouth',(head.x,head.y-.205*s,head.z-.085*s),.085*s,DARK,(.012,.013,.012),scale=(1.55,.30,.48)),B['head'])
for side in (-.045,0,.045):
    add(box('Tooth',(head.x+side*s,head.y-.224*s,head.z-.073*s),(.030*s,.015*s,.040*s),TEETH,(.82,.78,.61)),B['head'])

# Three front ornaments with crimson piping strip.
add(box('FrontPiping',(chest.x,chest.y-.225*s,chest.z-.18*s),(.035*s,.018*s,.72*s),RED,(.38,.018,.014)),B['sp2'])
for dz in (.14,-.08,-.30):
    add(ico('Pompom',(chest.x,chest.y-.245*s,chest.z+dz*s),.058*s,RED,(.50,.01,.008)),B['sp2'])

# Animations.
arm.animation_data_create()
for p in arm.pose.bones: p.rotation_mode='XYZ'
def reset_pose():
    for p in arm.pose.bones:
        p.rotation_euler=(0,0,0); p.location=(0,0,0); p.scale=(1,1,1)
def action(name, keys):
    a=bpy.data.actions.new(name=name); arm.animation_data.action=a
    for fr,rots in keys:
        reset_pose()
        for key,r in rots.items():
            bn=B.get(key); pb=arm.pose.bones.get(bn) if bn else None
            if pb: pb.rotation_euler=r
        for pb in arm.pose.bones:
            pb.keyframe_insert('rotation_euler',frame=fr,group=pb.name)
            pb.keyframe_insert('location',frame=fr,group=pb.name)
    return a
acts=[
 action('Penny_Idle',[(1,{}),(16,{'sp2':(-.045,0,.015),'head':(.04,0,-.025)}),(31,{})]),
 action('Penny_Walk',[(1,{'tl':(.48,0,0),'tr':(-.48,0,0),'ual':(-.30,0,.06),'uar':(.30,0,-.06)}),(10,{'tl':(-.48,0,0),'tr':(.48,0,0),'ual':(.30,0,-.06),'uar':(-.30,0,.06)}),(19,{'tl':(.48,0,0),'tr':(-.48,0,0)})]),
 action('Penny_Attack',[(1,{}),(7,{'sp2':(-.34,0,0),'ual':(-1.18,0,.25),'uar':(-1.18,0,-.25),'lal':(-.62,0,0),'lar':(-.62,0,0),'head':(.19,0,0)}),(14,{})]),
 action('Penny_Hurt',[(1,{}),(5,{'sp2':(.40,0,.15),'head':(-.36,0,-.18),'ual':(.30,0,.42),'uar':(.30,0,-.42)}),(11,{})]),
 action('Penny_Death',[(1,{}),(14,{'sp2':(.38,0,.28),'head':(-.46,0,0)}),(28,{'pelvis':(0,1.47,0),'sp2':(.68,0,.42),'head':(-.72,0,0)})])]
arm.animation_data.action=None
for a in acts:
    tr=arm.animation_data.nla_tracks.new(); tr.name=a.name
    st=tr.strips.new(a.name,int(a.frame_range[0]),a); st.action_frame_end=a.frame_range[1]

# Render proof from actual geometry.
try: bpy.context.scene.render.engine='BLENDER_EEVEE'
except: pass
bpy.context.scene.render.resolution_x=720; bpy.context.scene.render.resolution_y=720; bpy.context.scene.render.resolution_percentage=100
bpy.context.scene.world.color=(.006,.008,.007)
bpy.context.scene.frame_set(1)
bpy.ops.object.camera_add(location=(2.8,-5.8,1.35)); cam=bpy.context.object; look(cam,(head.x,head.y,head.z-.55*s)); bpy.context.scene.camera=cam
bpy.ops.object.light_add(type='AREA',location=(-2.8,-3.2,4.2)); bpy.context.object.data.energy=1050; bpy.context.object.data.size=4
bpy.ops.object.light_add(type='AREA',location=(2.4,-2.0,2.4)); bpy.context.object.data.energy=520; bpy.context.object.data.size=3
bpy.context.scene.render.filepath=os.path.join(args.out,'PENNYWISE_PASS5_MODEL_PREVIEW.png')
bpy.ops.render.render(write_still=True)
for o in list(bpy.context.scene.objects):
    if o.type in {'CAMERA','LIGHT'}: bpy.data.objects.remove(o,do_unlink=True)
bpy.context.scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(args.out,'pennywise_pass5.blend'))
export_glb(os.path.join(args.out,'pennywise.glb'),[arm]+body+parts,True)
print('PENNYWISE_DONE')

# -----------------------------------------------------------------------------
# SEWER - authored in Blender X/Y ground plane, Z vertical. Blender glTF export
# maps +Y to -Z and +Z to +Y, matching Tiny3D/game X/Z ground + Y up.
# 1 Blender unit becomes ~64 Tiny3D units.
# -----------------------------------------------------------------------------
clear(); sewer=[]
def S(o): sewer.append(o); return o
# Main corridor, ~650 N64 units long.
S(box('WalkL',(-.93,5.0,-.04),(1.28,10.0,.12),BRICK,(.085,.115,.100)))
S(box('WalkR',(.93,5.0,-.04),(1.28,10.0,.12),BRICK,(.085,.115,.100)))
S(box('Water',(0,5.0,-.14),(.58,10.0,.12),WATER,(.010,.075,.082)))
S(box('WallL',(-1.62,5.0,1.28),(.18,10.0,2.72),BRICK,(.075,.105,.092)))
S(box('WallR',(1.62,5.0,1.28),(.18,10.0,2.72),BRICK,(.075,.105,.092)))
S(box('Ceiling',(0,5.0,2.68),(3.40,10.0,.16),BRICK,(.065,.085,.078)))
# Stone/rust ribs give the repeating N64 tunnel cadence.
for i,y in enumerate([.45,1.65,2.85,4.05,5.25,6.45,7.65,8.85,9.75]):
    S(box('RibL%02d'%i,(-1.48,y,1.30),(.18,.16,2.52),TRIM,(.115,.075,.052)))
    S(box('RibR%02d'%i,( 1.48,y,1.30),(.18,.16,2.52),TRIM,(.115,.075,.052)))
    S(box('RibTop%02d'%i,(0,y,2.51),(3.12,.16,.22),TRIM,(.115,.075,.052)))
# Side ledges, broken-looking damp blocks and pipes.
for i,y in enumerate([1.2,3.6,6.1,8.25]):
    S(box('MossL%02d'%i,(-1.34,y,.35),(.28,.62,.42),MOSS,(.105,.135,.105)))
for i,y in enumerate([2.2,5.1,7.4,9.1]):
    S(box('MossR%02d'%i,(1.34,y,.42),(.26,.46,.55),MOSS,(.105,.135,.105)))
S(cyl_between('PipeL',(-1.37,.35,1.72),(-1.37,9.75,1.72),.055,TRIM,(.115,.075,.052),8))
S(cyl_between('PipeR',(1.37,2.15,2.05),(1.37,8.95,2.05),.042,TRIM,(.115,.075,.052),8))
# Boss chamber starts past the gate at Blender Y~=10.2 => game Z~-653.
S(box('BossFloor',(0,12.45,-.05),(4.65,4.85,.14),BRICK,(.075,.102,.090)))
S(box('BossWallL',(-2.38,12.45,1.38),(.18,4.85,2.90),BRICK,(.065,.088,.078)))
S(box('BossWallR',( 2.38,12.45,1.38),(.18,4.85,2.90),BRICK,(.065,.088,.078)))
S(box('BossBack',(0,14.82,1.38),(4.94,.18,2.90),BRICK,(.060,.082,.073)))
S(box('BossCeiling',(0,12.45,2.78),(4.94,4.85,.18),BRICK,(.055,.075,.068)))
for x in (-1.7,1.7):
    S(box('BossPillar',(x,12.65,1.24),(.36,.36,2.48),TRIM,(.115,.075,.052)))
# Circular-ish drain recess on back wall.
for x in (-.44,0,.44): S(box('BackGrime',(x,14.70,.78),(.28,.10,.80),MOSS,(.105,.135,.105)))
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(args.out,'sewer_pass5.blend'))
export_glb(os.path.join(args.out,'sewer.glb'),sewer,False)
print('SEWER_DONE',len(sewer))

# -----------------------------------------------------------------------------
# Balloon scare.
# -----------------------------------------------------------------------------
clear(); bal=[]
bal.append(ico('Balloon',(0,0,.18),.22,BALLOON,(.62,.018,.014),scale=(.88,.82,1.18),subdivisions=2))
bal.append(cyl_between('String',(0,0,-.02),(0,0,-.62),.006,LIGHT,(.65,.64,.58),5))
export_glb(os.path.join(args.out,'balloon.glb'),bal,False)

# -----------------------------------------------------------------------------
# Actual 3D first-person slingshot. Local +Z is up in Blender; its fork is in
# X/Z, and after glTF conversion it remains upright in Tiny3D Y-up space.
# -----------------------------------------------------------------------------
clear(); sling=[]
sling.append(cyl_between('Handle',(0,0,-.16),(0,0,.08),.055,WOOD,(.23,.105,.045),8))
sling.append(cyl_between('ForkL',(0,0,.05),(-.105,0,.245),.035,WOOD,(.23,.105,.045),8))
sling.append(cyl_between('ForkR',(0,0,.05),(.105,0,.245),.035,WOOD,(.23,.105,.045),8))
sling.append(cyl_between('BandL',(-.105,0,.245),(-.030,-.025,.170),.010,RUBBER,(.015,.012,.010),5))
sling.append(cyl_between('BandR',(.105,0,.245),(.030,-.025,.170),.010,RUBBER,(.015,.012,.010),5))
sling.append(box('Pouch',(0,-.028,.165),(.070,.025,.035),RUBBER,(.015,.012,.010)))
sling.append(ico('SilverBearing',(0,-.052,.168),.022,SILVER,(.46,.49,.47),subdivisions=1))
export_glb(os.path.join(args.out,'slingshot.glb'),sling,False)

# -----------------------------------------------------------------------------
# Gate/grate that appears behind the player when the boss activates.
# -----------------------------------------------------------------------------
clear(); gate=[]
for x in [-1.28,-.96,-.64,-.32,0,.32,.64,.96,1.28]:
    gate.append(cyl_between('Bar',(x,0,.05),(x,0,2.48),.035,METAL,(.055,.060,.057),6))
gate.append(cyl_between('CrossA',(-1.42,0,.55),(1.42,0,.55),.045,METAL,(.055,.060,.057),6))
gate.append(cyl_between('CrossB',(-1.42,0,1.72),(1.42,0,1.72),.045,METAL,(.055,.060,.057),6))
export_glb(os.path.join(args.out,'grate.glb'),gate,False)

print('PASS5_ASSETS_COMPLETE')

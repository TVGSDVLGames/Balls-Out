import bpy, sys, os, math, argparse, json, struct, copy
from mathutils import Vector

argv=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
ap=argparse.ArgumentParser()
ap.add_argument('--base',required=True)
ap.add_argument('--out',required=True)
ap.add_argument('--template-glb',required=True)
args=ap.parse_args(argv)
os.makedirs(args.out,exist_ok=True)

def clear():
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
def norm(s): return s.lower().replace('.','_').replace('-','_').replace(' ','_')
def findbone(arm,*names):
    d={norm(b.name):b.name for b in arm.data.bones}
    for n in names:
        if norm(n) in d:return d[norm(n)]
    for n in names:
        for k,v in d.items():
            if norm(n) in k or k.endswith(norm(n)):return v
    return None
def bpos(arm,name,tail=False):
    b=arm.data.bones.get(name) if name else None
    if not b:return Vector((0,0,0))
    p=b.tail_local if tail else (b.head_local+b.tail_local)*0.5
    return arm.matrix_world@p

def mat(name,c,rough=.65):
    m=bpy.data.materials.new(name);m.use_nodes=True;m.diffuse_color=(*c,1)
    p=m.node_tree.nodes.get('Principled BSDF')
    if p:
        p.inputs['Base Color'].default_value=(*c,1)
        p.inputs['Roughness'].default_value=rough
    return m
WHITE=mat('ClownWhite',(.82,.84,.80)); RED=mat('ClownRed',(.58,.015,.012)); DARK=mat('ClownDark',(.015,.018,.016)); SEWER=mat('Sewer',(0.13,.17,.15),.9); WATER=mat('Water',(0.02,.12,.13),.25)

def paint(o,m,c):
    if o.type!='MESH':return
    o.data.materials.clear();o.data.materials.append(m)
    try:
        while o.data.color_attributes:o.data.color_attributes.remove(o.data.color_attributes[0])
        ca=o.data.color_attributes.new(name='Col',type='BYTE_COLOR',domain='CORNER')
        for x in ca.data:x.color=(*c,1)
    except Exception as e:print('VCOL_WARN',o.name,repr(e))
def mesh(name,v,f,m=SEWER,c=(.13,.17,.15)):
    me=bpy.data.meshes.new(name+'Mesh');me.from_pydata(v,[],f);me.update();o=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(o);paint(o,m,c);return o
def box(name,p,s,m=SEWER,c=(.13,.17,.15)):
    x,y,z=p;a,b,d=(s[0]/2,s[1]/2,s[2]/2)
    v=[(x-a,y-b,z-d),(x+a,y-b,z-d),(x+a,y+b,z-d),(x-a,y+b,z-d),(x-a,y-b,z+d),(x+a,y-b,z+d),(x+a,y+b,z+d),(x-a,y+b,z+d)]
    return mesh(name,v,[(0,1,2,3),(4,7,6,5),(0,4,5,1),(1,5,6,2),(2,6,7,3),(4,0,3,7)],m,c)
def ring(name,p,ri,ro,n,m,c,w=.18):
    x,y,z=p;v=[]
    for i in range(n):
        a=math.tau*i/n; rr=ro*(1+w*(1 if i&1 else -1))
        v.extend([(x+math.cos(a)*ri,y+math.sin(a)*ri,z),(x+math.cos(a)*rr,y+math.sin(a)*rr,z)])
    return mesh(name,v,[(2*i,2*((i+1)%n),2*((i+1)%n)+1,2*i+1) for i in range(n)],m,c)
def wedge(name,p,sc,m,c):
    x,y,z=p;a,b,d=sc;v=[(x-a,y,z-d*.2),(x+a,y,z-d*.2),(x+a*.55,y+b,z+d*.15),(x-a*.55,y+b,z+d*.15),(x,y+b*.35,z+d)]
    return mesh(name,v,[(0,1,2,3),(0,4,1),(1,4,2),(2,4,3),(3,4,0)],m,c)
def ico(name,p,r,m,c,sub=1):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=sub,radius=r,location=p);o=bpy.context.object;o.name=name;paint(o,m,c);return o
def cyl(name,p,r,depth,m,c,verts=8,rot=(0,0,0)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts,radius=r,depth=depth,location=p,rotation=rot);o=bpy.context.object;o.name=name;paint(o,m,c);return o
def bind(o,arm,bn):
    if not bn:return
    mod=o.modifiers.new('Armature','ARMATURE');mod.object=arm
    vg=o.vertex_groups.new(name=bn);vg.add(list(range(len(o.data.vertices))),1.0,'REPLACE')
def look(o,t):o.rotation_euler=(Vector(t)-o.location).to_track_quat('-Z','Y').to_euler()

def read_glb(path):
    data=open(path,'rb').read()
    magic,ver,total=struct.unpack_from('<4sII',data,0)
    if magic!=b'glTF' or ver!=2:raise RuntimeError('Not GLB2: '+path)
    off=12;chunks=[]
    while off<total:
        ln,typ=struct.unpack_from('<II',data,off);off+=8
        chunks.append([typ,data[off:off+ln]]);off+=ln
    ji=next(i for i,c in enumerate(chunks) if c[0]==0x4E4F534A)
    doc=json.loads(chunks[ji][1].rstrip(b' \t\r\n\0').decode('utf8'))
    return doc,chunks,ji
def write_glb(path,doc,chunks,ji):
    raw=json.dumps(doc,separators=(',',':'),ensure_ascii=False).encode('utf8');raw+=b' ' *((4-len(raw)%4)%4);chunks[ji][1]=raw
    body=b''.join(struct.pack('<II',len(c[1]),c[0])+c[1] for c in chunks)
    open(path,'wb').write(struct.pack('<4sII',b'glTF',2,12+len(body))+body)
def inject_f3d(path,template):
    td,_,_=read_glb(template)
    candidates=[]
    for m in td.get('materials',[]):
        f=m.get('extras',{}).get('f3d_mat')
        if f is not None:
            s=json.dumps(f).upper(); score=(0 if 'SHADE' in s else 10)+(100 if '.PNG' in s else 0)+len(s)/1000000
            candidates.append((score,f,m.get('name','?')))
    if not candidates:raise RuntimeError('Template GLB has no Fast64 f3d_mat metadata')
    candidates.sort(key=lambda x:x[0]); f3d=copy.deepcopy(candidates[0][1])
    print('F3D_TEMPLATE_MATERIAL',candidates[0][2],'score',candidates[0][0])
    doc,chunks,ji=read_glb(path)
    if not doc.get('materials'):doc['materials']=[{'name':'N64_Shaded'}]
    for m in doc['materials']:
        m.setdefault('extras',{})['f3d_mat']=copy.deepcopy(f3d)
    write_glb(path,doc,chunks,ji)
    print('F3D_INJECTED',path,'materials',len(doc['materials']))

def export_glb(path,selection,animations=False):
    bpy.ops.object.select_all(action='DESELECT')
    for o in selection:o.select_set(True)
    if selection:bpy.context.view_layer.objects.active=selection[0]
    kw=dict(filepath=path,export_format='GLB',use_selection=True,export_animations=animations,export_extras=True,export_colors=True)
    if animations:kw['export_nla_strips']=True
    try:bpy.ops.export_scene.gltf(**kw)
    except TypeError:
        kw.pop('export_nla_strips',None);kw.pop('export_colors',None);bpy.ops.export_scene.gltf(**kw)
    inject_f3d(path,args.template_glb)

# Pennywise: genuine skinned Quaternius base + modeled clown costume pieces.
clear();bpy.ops.import_scene.gltf(filepath=args.base)
arm=next((o for o in bpy.context.scene.objects if o.type=='ARMATURE'),None)
if not arm:raise RuntimeError('No armature in Quaternius source')
arm.name='PennywiseRig';body=[o for o in bpy.context.scene.objects if o.type=='MESH']
print('SOURCE_MESHES',[(o.name,len(o.data.polygons)) for o in body]);print('BONES',len(arm.data.bones))
for o in body:
    tris=sum(max(0,len(p.vertices)-2) for p in o.data.polygons)
    if tris>2200:
        bpy.context.view_layer.objects.active=o;o.select_set(True);d=o.modifiers.new('N64_LOD','DECIMATE');d.ratio=max(.22,1800.0/tris)
        try:bpy.ops.object.modifier_apply(modifier=d.name)
        except Exception as e:print('DECIMATE_WARN',repr(e))
    paint(o,WHITE,(.82,.84,.80))
B={'pelvis':findbone(arm,'pelvis','hips'),'sp2':findbone(arm,'spine_02','chest'),'neck':findbone(arm,'neck_01','neck'),'head':findbone(arm,'head'),'ual':findbone(arm,'upperarm_l'),'uar':findbone(arm,'upperarm_r'),'lal':findbone(arm,'lowerarm_l'),'lar':findbone(arm,'lowerarm_r'),'hl':findbone(arm,'hand_l'),'hr':findbone(arm,'hand_r'),'tl':findbone(arm,'thigh_l'),'tr':findbone(arm,'thigh_r')}
print('BONE_MAP',B)
head=bpos(arm,B['head']);neck=bpos(arm,B['neck'],True);chest=bpos(arm,B['sp2']);zs=[(arm.matrix_world@b.head_local).z for b in arm.data.bones];s=max(.5,(max(zs)-min(zs))/2)
parts=[]
def add(o,b):parts.append(o);bind(o,arm,b);return o
add(ring('Ruff',(neck.x,neck.y,neck.z),.11*s,.32*s,20,WHITE,(.9,.9,.84),.24),B['neck'])
for side in (-1,1):
    for dz in (-.14,.02,.18):add(wedge('Hair',(head.x+side*.19*s,head.y+.035*s,head.z+dz*s),(.11*s,.15*s,.19*s),RED,(.62,.01,.008)),B['head'])
add(ico('Nose',(head.x,head.y-.18*s,head.z+.02*s),.065*s,RED,(.68,.01,.008)),B['head'])
for side in (-1,1):
    add(ico('Eye',(head.x+side*.07*s,head.y-.19*s,head.z+.10*s),.027*s,DARK,(.005,.005,.004)),B['head'])
    add(wedge('FacePaint',(head.x+side*.075*s,head.y-.192*s,head.z+.015*s),(.018*s,.012*s,.095*s),RED,(.66,.01,.008)),B['head'])
add(box('Mouth',(head.x,head.y-.194*s,head.z-.075*s),(.16*s,.018*s,.035*s),DARK,(.005,.005,.004)),B['head'])
for dz in (.07,-.12,-.31):add(ico('Pompom',(chest.x,chest.y-.16*s,chest.z+dz*s),.055*s,RED,(.66,.01,.008)),B['sp2'])
for k in ('hl','hr'):
    p=bpos(arm,B[k]);add(ring('Cuff',(p.x,p.y,p.z),.065*s,.13*s,10,WHITE,(.9,.9,.84),.12),B[k])

arm.animation_data_create()
for p in arm.pose.bones:p.rotation_mode='XYZ'
def reset_pose():
    for p in arm.pose.bones:p.rotation_euler=(0,0,0);p.location=(0,0,0);p.scale=(1,1,1)
def action(name,keys):
    a=bpy.data.actions.new(name=name);arm.animation_data.action=a
    for fr,rots in keys:
        reset_pose()
        for key,r in rots.items():
            bn=B.get(key);p=arm.pose.bones.get(bn) if bn else None
            if p:p.rotation_euler=r
        for p in arm.pose.bones:p.keyframe_insert('rotation_euler',frame=fr,group=p.name);p.keyframe_insert('location',frame=fr,group=p.name)
    return a
acts=[
 action('Penny_Idle',[(1,{}),(16,{'sp2':(-.035,0,0),'head':(.03,0,0)}),(31,{})]),
 action('Penny_Walk',[(1,{'tl':(.48,0,0),'tr':(-.48,0,0),'ual':(-.34,0,0),'uar':(.34,0,0)}),(10,{'tl':(-.48,0,0),'tr':(.48,0,0),'ual':(.34,0,0),'uar':(-.34,0,0)}),(19,{'tl':(.48,0,0),'tr':(-.48,0,0)})]),
 action('Penny_Attack',[(1,{}),(7,{'sp2':(-.3,0,0),'ual':(-1.15,0,.22),'uar':(-1.15,0,-.22),'lal':(-.65,0,0),'lar':(-.65,0,0),'head':(.18,0,0)}),(14,{})]),
 action('Penny_Hurt',[(1,{}),(5,{'sp2':(.42,0,.12),'head':(-.35,0,-.18),'ual':(.35,0,.4),'uar':(.35,0,-.4)}),(11,{})]),
 action('Penny_Death',[(1,{}),(14,{'sp2':(.35,0,.25),'head':(-.4,0,0)}),(28,{'pelvis':(0,1.45,0),'sp2':(.6,0,.4),'head':(-.65,0,0)})])]
arm.animation_data.action=None
for a in acts:
    tr=arm.animation_data.nla_tracks.new();tr.name=a.name;st=tr.strips.new(a.name,int(a.frame_range[0]),a);st.action_frame_end=a.frame_range[1]

# Proof render before export.
bpy.context.scene.render.engine='BLENDER_EEVEE';bpy.context.scene.render.resolution_x=640;bpy.context.scene.render.resolution_y=640;bpy.context.scene.render.resolution_percentage=100;bpy.context.scene.world.color=(.008,.01,.009)
bpy.ops.object.camera_add(location=(0,-5.6,1.25));cam=bpy.context.object;look(cam,(head.x,head.y,head.z-.18*s));bpy.context.scene.camera=cam
bpy.ops.object.light_add(type='AREA',location=(-2.5,-3,4));bpy.context.object.data.energy=900;bpy.context.object.data.size=4
bpy.ops.object.light_add(type='AREA',location=(2,-1,2));bpy.context.object.data.energy=450;bpy.context.object.data.size=3
bpy.context.scene.render.filepath=os.path.join(args.out,'PENNYWISE_REAL_MESH_PREVIEW.png');bpy.ops.render.render(write_still=True)
for o in list(bpy.context.scene.objects):
    if o.type in {'CAMERA','LIGHT'}:bpy.data.objects.remove(o,do_unlink=True)
bpy.context.scene.frame_set(1);bpy.ops.wm.save_as_mainfile(filepath=os.path.join(args.out,'pennywise_real.blend'))
export_glb(os.path.join(args.out,'pennywise.glb'),[arm]+body+parts,True)
print('PENNYWISE_GLTF_DONE')

# Sewer environment.
clear();objs=[]
objs += [box('FloorL',(-10,0,-59),(14,1.1,136)),box('FloorR',(10,0,-59),(14,1.1,136)),box('Water',(0,-.55,-59),(6,.25,136),WATER,(.02,.12,.13))]
objs += [box('WallL',(-19,6,-59),(4,12,136)),box('WallR',(19,6,-59),(4,12,136)),box('Ceiling',(0,13,-59),(40,2,136),DARK,(.045,.055,.05))]
objs += [box('BossFloor',(0,0,-166),(90,1.1,82)),box('BossBack',(0,7,-208),(90,14,3)),box('BossLeft',(-45,7,-167),(3,14,82)),box('BossRight',(45,7,-167),(3,14,82)),box('BossCeiling',(0,14,-167),(90,2,82),DARK,(.04,.05,.045))]
objs += [box('GatePostL',(-15,6,-126),(3,12,3),DARK,(.07,.08,.075)),box('GatePostR',(15,6,-126),(3,12,3),DARK,(.07,.08,.075)),box('GateTop',(0,12,-126),(33,2,3),DARK,(.07,.08,.075))]
for x in (-13,13):
    for z in (-20,-55,-90):objs.append(cyl('Pipe',(x,10,z),.55,28,DARK,(.08,.10,.09),8,(math.pi/2,0,0)))
for x in (-32,32):
    for z in (-148,-188):objs.append(cyl('Pillar',(x,5,z),1.7,10,SEWER,(.15,.18,.17),8))
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(args.out,'sewer_real.blend'))
export_glb(os.path.join(args.out,'sewer.glb'),objs,False);print('SEWER_GLTF_DONE')

# Red balloon scare prop.
clear();ball=ico('RedBalloon',(0,0,1.2),.38,RED,(.72,.01,.008),2);string=cyl('String',(0,0,.45),.012,1.15,DARK,(.02,.02,.018),6)
export_glb(os.path.join(args.out,'balloon.glb'),[ball,string],False);print('BALLOON_GLTF_DONE')

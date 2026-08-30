import bpy, sys, os, math, argparse
from mathutils import Vector

argv=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
ap=argparse.ArgumentParser(); ap.add_argument('--base',required=True); ap.add_argument('--out',required=True); ap.add_argument('--template',default=''); args=ap.parse_args(argv)
os.makedirs(args.out,exist_ok=True)
try:
    bpy.ops.preferences.addon_enable(module='fast64'); print('FAST64_ENABLED=1')
except Exception as e: print('FAST64_ENABLE_WARNING',repr(e))

def clear():
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
def nn(s): return s.lower().replace('.','_').replace('-','_').replace(' ','_')
def bone(arm,*names):
    by={nn(b.name):b.name for b in arm.data.bones}
    for n in names:
        if nn(n) in by:return by[nn(n)]
    for n in names:
        for k,v in by.items():
            if nn(n) in k or k.endswith(nn(n)):return v
    return None
def bpos(arm,name,tail=False):
    b=arm.data.bones.get(name) if name else None
    if not b:return Vector((0,0,0))
    p=b.tail_local if tail else (b.head_local+b.tail_local)*.5
    return arm.matrix_world@p

def mat(name,c,rough=.55):
    m=bpy.data.materials.new(name);m.use_nodes=True;m.diffuse_color=(*c,1)
    bs=m.node_tree.nodes.get('Principled BSDF')
    if bs:
        if 'Base Color' in bs.inputs:bs.inputs['Base Color'].default_value=(*c,1)
        if 'Roughness' in bs.inputs:bs.inputs['Roughness'].default_value=rough
    return m
MW=mat('PreviewWhite',(.76,.78,.75));MR=mat('PreviewRed',(.55,.02,.015));MD=mat('PreviewDark',(.018,.02,.019));MS=mat('PreviewSewer',(.15,.19,.18),.85);MB=mat('PreviewWater',(.025,.13,.13),.28)

def color(obj,m,c):
    if obj.type!='MESH':return
    obj.data.materials.clear();obj.data.materials.append(m)
    try:
        while obj.data.color_attributes:obj.data.color_attributes.remove(obj.data.color_attributes[0])
        ca=obj.data.color_attributes.new(name='Col',type='BYTE_COLOR',domain='CORNER')
        for d in ca.data:d.color=(*c,1)
    except Exception as e:print('VCOL_WARN',obj.name,repr(e))
def mesh(name,v,f,m=MS,c=(.15,.19,.18)):
    me=bpy.data.meshes.new(name+'Mesh');me.from_pydata(v,[],f);me.update();o=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(o);color(o,m,c);return o
def box(name,p,s,m=MS,c=(.15,.19,.18)):
    x,y,z=p;a,b,d=[q/2 for q in s]
    v=[(x-a,y-b,z-d),(x+a,y-b,z-d),(x+a,y+b,z-d),(x-a,y+b,z-d),(x-a,y-b,z+d),(x+a,y-b,z+d),(x+a,y+b,z+d),(x-a,y+b,z+d)]
    f=[(0,1,2,3),(4,7,6,5),(0,4,5,1),(1,5,6,2),(2,6,7,3),(4,0,3,7)]
    return mesh(name,v,f,m,c)
def ring(name,p,ri,ro,n,m,c,w=.18):
    x,y,z=p;v=[]
    for i in range(n):
        a=math.tau*i/n;v.append((x+math.cos(a)*ri,y+math.sin(a)*ri,z));r=ro*(1+w*(1 if i%2 else -1));v.append((x+math.cos(a)*r,y+math.sin(a)*r,z+(.015 if i%2 else -.015)))
    return mesh(name,v,[(2*i,2*((i+1)%n),2*((i+1)%n)+1,2*i+1) for i in range(n)],m,c)
def wedge(name,p,sc,m,c):
    x,y,z=p;a,b,d=sc;v=[(x-a,y,z-d*.2),(x+a,y,z-d*.2),(x+a*.55,y+b,z+d*.15),(x-a*.55,y+b,z+d*.15),(x,y+b*.35,z+d)]
    return mesh(name,v,[(0,1,2,3),(0,4,1),(1,4,2),(2,4,3),(3,4,0)],m,c)
def ico(name,p,r,m,c,sub=1):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=sub,radius=r,location=p);o=bpy.context.object;o.name=name;color(o,m,c);return o
def cyl(name,p,r,depth,m,c,verts=8,rot=(0,0,0)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts,radius=r,depth=depth,location=p,rotation=rot);o=bpy.context.object;o.name=name;color(o,m,c);return o
def bind(o,arm,bn):
    if not bn:return
    mo=o.modifiers.new('Armature','ARMATURE');mo.object=arm;vg=o.vertex_groups.new(name=bn);vg.add(list(range(len(o.data.vertices))),1.0,'REPLACE')

def f3d_material(dummy,template):
    bpy.context.view_layer.objects.active=dummy;dummy.select_set(True)
    try:
        bpy.ops.object.create_f3d_mat();m=dummy.data.materials[-1];m.name='N64_Shaded';print('F3D_CREATED',m.name,getattr(m,'is_f3d',None));return m
    except Exception as e:print('F3D_CREATE_FAIL',repr(e))
    if template and os.path.exists(template):
        with bpy.data.libraries.load(template,link=False) as (src,dst):dst.materials=list(src.materials)
        cand=[m for m in dst.materials if m]
        cand.sort(key=lambda m:sum(1 for n in (m.node_tree.nodes if m.use_nodes else []) if n.type=='TEX_IMAGE'))
        if cand:print('F3D_TEMPLATE',cand[0].name);return cand[0]
    raise RuntimeError('No Fast64 material')

def look(o,t):o.rotation_euler=(Vector(t)-o.location).to_track_quat('-Z','Y').to_euler()

clear();bpy.ops.import_scene.gltf(filepath=args.base)
arm=next((o for o in bpy.context.scene.objects if o.type=='ARMATURE'),None)
if not arm:raise RuntimeError('No Quaternius armature')
arm.name='PennywiseRig';meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
print('SOURCE_MESHES',[(o.name,len(o.data.polygons)) for o in meshes]);print('BONES',[b.name for b in arm.data.bones])
for o in meshes:
    tri=sum(max(0,len(p.vertices)-2) for p in o.data.polygons)
    if tri>1800:
        bpy.context.view_layer.objects.active=o;o.select_set(True);d=o.modifiers.new('N64_LOD','DECIMATE');d.ratio=.30
        try:bpy.ops.object.modifier_apply(modifier=d.name)
        except Exception as e:print('DECIMATE_WARN',o.name,repr(e))
        o.select_set(False)
    color(o,MW,(.76,.78,.75))
B={'pelvis':bone(arm,'pelvis','hips'),'sp1':bone(arm,'spine_01','spine'),'sp2':bone(arm,'spine_02','chest'),'sp3':bone(arm,'spine_03'),'neck':bone(arm,'neck_01','neck'),'head':bone(arm,'Head','head'),'ual':bone(arm,'upperarm_l'),'uar':bone(arm,'upperarm_r'),'lal':bone(arm,'lowerarm_l'),'lar':bone(arm,'lowerarm_r'),'hl':bone(arm,'hand_l'),'hr':bone(arm,'hand_r'),'tl':bone(arm,'thigh_l'),'tr':bone(arm,'thigh_r'),'cl':bone(arm,'calf_l'),'cr':bone(arm,'calf_r')}
print('BONE_MAP',B)
head=bpos(arm,B['head']);neck=bpos(arm,B['neck'],True);chest=bpos(arm,B['sp2']);zs=[(arm.matrix_world@b.head_local).z for b in arm.data.bones];s=max(.5,(max(zs)-min(zs))/2)
bind(ring('Ruff',(neck.x,neck.y,neck.z),.12*s,.31*s,18,MW,(.90,.90,.84),.24),arm,B['neck'])
for side in (-1,1):
    for dz in (-.12,.03,.18):bind(wedge('Hair',(head.x+side*.19*s,head.y+.035*s,head.z+dz*s),(.105*s,.14*s,.18*s),MR,(.58,.02,.015)),arm,B['head'])
bind(ico('Nose',(head.x,head.y-.18*s,head.z+.02*s),.065*s,MR,(.65,.02,.015)),arm,B['head'])
for side in (-1,1):
    bind(ico('Eye',(head.x+side*.07*s,head.y-.187*s,head.z+.095*s),.027*s,MD,(.01,.01,.01)),arm,B['head'])
    bind(wedge('FacePaint',(head.x+side*.075*s,head.y-.19*s,head.z+.015*s),(.018*s,.012*s,.09*s),MR,(.62,.02,.015)),arm,B['head'])
bind(box('Mouth',(head.x,head.y-.19*s,head.z-.075*s),(.16*s,.015*s,.035*s),MD,(.01,.01,.01)),arm,B['head'])
for dz in (.06,-.12,-.30):bind(ico('Pompom',(chest.x,chest.y-.16*s,chest.z+dz*s),.055*s,MR,(.62,.02,.015)),arm,B['sp2'])
for k in ('hl','hr'):
    p=bpos(arm,B[k]);bind(ring('Cuff',(p.x,p.y,p.z),.065*s,.13*s,10,MW,(.88,.88,.82),.12),arm,B[k])
arm.animation_data_create()
for pb in arm.pose.bones:pb.rotation_mode='XYZ'
def reset():
    for pb in arm.pose.bones:pb.rotation_euler=(0,0,0);pb.location=(0,0,0);pb.scale=(1,1,1)
def mkact(name,frames):
    a=bpy.data.actions.new(name=name);arm.animation_data.action=a
    for fr,rots in frames:
        reset()
        for key,ang in rots.items():
            bn=B.get(key);pb=arm.pose.bones.get(bn) if bn else None
            if pb:pb.rotation_euler=ang
        for pb in arm.pose.bones:pb.keyframe_insert('rotation_euler',frame=fr,group=pb.name);pb.keyframe_insert('location',frame=fr,group=pb.name)
    return a
acts=[mkact('Penny_Idle',[(1,{'sp2':(.02,0,0),'head':(-.02,0,0)}),(16,{'sp2':(-.025,0,0),'head':(.025,0,0)}),(31,{'sp2':(.02,0,0)})]),mkact('Penny_Walk',[(1,{'tl':(.45,0,0),'tr':(-.45,0,0),'ual':(-.32,0,0),'uar':(.32,0,0)}),(10,{'tl':(-.45,0,0),'tr':(.45,0,0),'ual':(.32,0,0),'uar':(-.32,0,0)}),(19,{'tl':(.45,0,0),'tr':(-.45,0,0)})]),mkact('Penny_Attack',[(1,{}),(7,{'sp2':(-.28,0,0),'ual':(-1.15,0,.22),'uar':(-1.15,0,-.22),'lal':(-.65,0,0),'lar':(-.65,0,0),'head':(.18,0,0)}),(14,{})]),mkact('Penny_Hurt',[(1,{}),(5,{'sp2':(.42,0,.12),'head':(-.35,0,-.18),'ual':(.35,0,.4),'uar':(.35,0,-.4)}),(11,{})]),mkact('Penny_Death',[(1,{}),(14,{'sp2':(.35,0,.25),'head':(-.4,0,0)}),(28,{'pelvis':(0,1.45,0),'sp2':(.6,0,.4),'head':(-.65,0,0)})])]
arm.animation_data.action=None
for a in acts:
    t=arm.animation_data.nla_tracks.new();t.name=a.name;st=t.strips.new(a.name,int(a.frame_range[0]),a);st.action_frame_end=a.frame_range[1]
bpy.context.scene.render.engine='BLENDER_EEVEE';bpy.context.scene.render.resolution_x=640;bpy.context.scene.render.resolution_y=640;bpy.context.scene.render.resolution_percentage=100;bpy.context.scene.world.color=(.01,.012,.012)
bpy.ops.object.camera_add(location=(0,-5.6,1.25));cam=bpy.context.object;look(cam,(head.x,head.y,head.z-.18*s));bpy.context.scene.camera=cam
bpy.ops.object.light_add(type='AREA',location=(-2.5,-3,4));bpy.context.object.data.energy=800;bpy.context.object.data.size=4
bpy.ops.object.light_add(type='AREA',location=(2,-1,2));bpy.context.object.data.energy=500;bpy.context.object.data.size=3
bpy.context.scene.render.filepath=os.path.join(args.out,'PENNYWISE_REAL_MESH_PREVIEW.png');bpy.ops.render.render(write_still=True)
for o in list(bpy.context.scene.objects):
    if o.type in {'CAMERA','LIGHT'}:bpy.data.objects.remove(o,do_unlink=True)
dummy=box('_dummy',(10,10,10),(.1,.1,.1),MW,(1,1,1));f3d=f3d_material(dummy,args.template);bpy.data.objects.remove(dummy,do_unlink=True)
for o in [o for o in bpy.context.scene.objects if o.type=='MESH']:o.data.materials.clear();o.data.materials.append(f3d)
bpy.context.scene.frame_set(1);bpy.ops.wm.save_as_mainfile(filepath=os.path.join(args.out,'pennywise_real.blend'))
for o in bpy.context.scene.objects:o.select_set(o.type in {'MESH','ARMATURE'})
bpy.context.view_layer.objects.active=arm
kw=dict(filepath=os.path.join(args.out,'pennywise.glb'),export_format='GLB',use_selection=True,export_animations=True,export_nla_strips=True,export_extras=True)
try:bpy.ops.export_scene.gltf(**kw)
except TypeError:kw.pop('export_nla_strips',None);bpy.ops.export_scene.gltf(**kw)
print('PENNYWISE_GLTF_DONE')
clear();objs=[]
objs += [box('FloorL',(-10,0,-59),(14,1.1,136)),box('FloorR',(10,0,-59),(14,1.1,136)),box('Water',(0,-.55,-59),(6,.25,136),MB,(.025,.13,.13))]
objs += [box('WallL',(-19,6,-59),(4,12,136)),box('WallR',(19,6,-59),(4,12,136)),box('Ceiling',(0,13,-59),(40,2,136),MD,(.05,.06,.055))]
objs += [box('BossFloor',(0,0,-166),(90,1.1,82)),box('BossBack',(0,7,-208),(90,14,3)),box('BossLeft',(-45,7,-167),(3,14,82)),box('BossRight',(45,7,-167),(3,14,82)),box('BossCeiling',(0,14,-167),(90,2,82),MD,(.04,.05,.045))]
objs += [box('GatePostL',(-15,6,-126),(3,12,3),MD,(.07,.08,.075)),box('GatePostR',(15,6,-126),(3,12,3),MD,(.07,.08,.075)),box('GateTop',(0,12,-126),(33,2,3),MD,(.07,.08,.075))]
for x in (-13,13):
    for z in (-20,-55,-90):objs.append(cyl('Pipe',(x,10,z),.55,28,MD,(.08,.10,.09),8,(math.pi/2,0,0)))
for x in (-32,32):
    for z in (-148,-188):objs.append(cyl('Pillar',(x,5,z),1.7,10,MS,(.15,.18,.17),8))
for o in [o for o in bpy.context.scene.objects if o.type=='MESH']:o.data.materials.clear();o.data.materials.append(f3d);o.select_set(True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(args.out,'sewer_real.blend'));bpy.ops.export_scene.gltf(filepath=os.path.join(args.out,'sewer.glb'),export_format='GLB',use_selection=True,export_animations=False,export_extras=True);print('SEWER_GLTF_DONE')
clear();ba=ico('RedBalloon',(0,0,1.2),.38,MR,(.65,.02,.015),2);st=cyl('String',(0,0,.45),.012,1.15,MD,(.03,.03,.03),6)
for o in (ba,st):o.data.materials.clear();o.data.materials.append(f3d);o.select_set(True)
bpy.ops.export_scene.gltf(filepath=os.path.join(args.out,'balloon.glb'),export_format='GLB',use_selection=True,export_animations=False,export_extras=True);print('BALLOON_GLTF_DONE')

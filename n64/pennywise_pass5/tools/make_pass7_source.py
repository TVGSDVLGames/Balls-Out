#!/usr/bin/env python3
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
# PASS7 starts from the known-good generated PASS6 sources.
exec((ROOT/'tools/make_pass6_source.py').read_text(), {'__name__':'__main__','__file__':str(ROOT/'tools/make_pass6_source.py')})

src=(ROOT/'tools/build_assets_pass6.py').read_text()

# Add standard-library PNG writer + deliberately tiny late-90s texture set.
needle="import bpy, sys, os, math, argparse, json, struct, copy\n"
insert="""import bpy, sys, os, math, argparse, json, struct, copy, zlib, binascii, random\n"""
src=src.replace(needle,insert,1)

needle="os.makedirs(args.out, exist_ok=True)\n"
insert="""os.makedirs(args.out, exist_ok=True)\n\ndef _png_chunk(tag,data):\n    return struct.pack('>I',len(data))+tag+data+struct.pack('>I',binascii.crc32(tag+data)&0xffffffff)\n\ndef write_png(path,w,h,pixel_fn):\n    raw=bytearray()\n    for y in range(h):\n        raw.append(0)\n        for x in range(w):\n            r,g,b,a=pixel_fn(x,y)\n            raw += bytes((max(0,min(255,int(r))),max(0,min(255,int(g))),max(0,min(255,int(b))),max(0,min(255,int(a)))))\n    data=b'\\x89PNG\\r\\n\\x1a\\n'+_png_chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,6,0,0,0))+_png_chunk(b'IDAT',zlib.compress(bytes(raw),9))+_png_chunk(b'IEND',b'')\n    open(path,'wb').write(data)\n\ndef make_n64_textures(out):\n    random.seed(64)\n    # 32x32 damp sewer brick: chunky 8px courses, dark mortar and a few wet pixels.\n    def brick(x,y):\n        row=y//8; off=4 if row&1 else 0; mortar=(y%8 in (0,1)) or ((x+off)%16 in (0,1))\n        if mortar:return (24,31,28,255)\n        n=((x*13+y*7+(x*y)%17)%19)-9\n        wet=((x*7+y*11)%43==0)\n        return (49+n//2,61+n,52+n//2+(12 if wet else 0),255)\n    def stone(x,y):\n        n=((x*5+y*9+(x^y)*3)%27)-13\n        moss=((x*3+y*5)%29)<4\n        return (44+n//3,54+n//3+(12 if moss else 0),48+n//3,255)\n    def metal(x,y):\n        seam=(x%8==0 or y%8==0); rust=((x*11+y*17)%37)<5\n        if seam:return (25,28,27,255)\n        return (57+(28 if rust else 0),58-(10 if rust else 0),53-(18 if rust else 0),255)\n    def water(x,y):\n        wave=((x+y*2)%13)<2; glint=((x*3+y*7)%47)==0\n        return (8+(8 if wave else 0),38+(18 if wave else 0)+(20 if glint else 0),43+(25 if wave else 0)+(24 if glint else 0),255)\n    def cloth(x,y):\n        seam=(x%16==0); weave=((x+y)&3)==0; grime=((x*7+y*13)%53)<3\n        base=151+(8 if weave else 0)-(30 if grime else 0)\n        return (base,base-3,base-14,255) if not seam else (104,102,91,255)\n    def redcloth(x,y):\n        seam=(x%16==0); grime=((x*5+y*11)%47)<3\n        return ((95 if seam else 126)-(28 if grime else 0),12,10,255)\n    def skin(x,y):\n        n=((x*7+y*3)%11)-5; return (185+n,184+n,166+n,255)\n    def hair(x,y):\n        streak=((x*3+y)%7)==0; return (115+(20 if streak else 0),35+(8 if streak else 0),12,255)\n    def wood(x,y):\n        grain=((x+y*3)%9)<2; return (86+(18 if grain else 0),44+(8 if grain else 0),20,255)\n    def face(x,y):\n        # Hand-painted 64x64 clown face: off-white mask, amber eyes, red lines/nose, black grin.\n        cx=x-31.5; cy=y-31.5\n        edge=(cx/27)**2+(cy/30)**2\n        r,g,b=(190,188,169) if edge<1 else (150,148,134)\n        # eye sockets / pupils\n        for ex in (-10,10):\n            if ((x-(32+ex))/7)**2+((y-25)/4)**2 < 1: r,g,b=(28,25,21)\n            if ((x-(32+ex))/2.3)**2+((y-25)/2.3)**2 < 1: r,g,b=(190,118,28)\n        # red vertical paint lines\n        if (abs(x-22)<=1 or abs(x-42)<=1) and 27<=y<=44: r,g,b=(145,15,12)\n        # nose\n        if ((x-32)/5)**2+((y-34)/4)**2<1:r,g,b=(158,16,12)\n        # grin / teeth band\n        if ((x-32)/14)**2+((y-45)/6)**2<1:r,g,b=(28,20,18)\n        if 26<=x<=38 and 43<=y<=46 and (x%4)!=0:r,g,b=(205,198,165)\n        return (r,g,b,255)\n    specs={'brick.png':(32,32,brick),'stone.png':(32,32,stone),'metal.png':(32,32,metal),'water.png':(32,32,water),'cloth.png':(32,32,cloth),'redcloth.png':(32,32,redcloth),'skin.png':(32,32,skin),'hair.png':(32,32,hair),'wood.png':(32,32,wood),'face.png':(64,64,face)}\n    for name,(w,h,fn) in specs.items():write_png(os.path.join(out,name),w,h,fn)\n    print('PASS7_TEXTURES', sorted(specs))\n\nmake_n64_textures(args.out)\n"""
src=src.replace(needle,insert,1)

# Add UV helper and use it on all generated mesh primitives.
needle="def mesh(name, verts, faces, material, color):\n    me = bpy.data.meshes.new(name+'Mesh')\n    me.from_pydata(verts, [], faces)\n    me.update()\n    o = bpy.data.objects.new(name, me)\n    bpy.context.collection.objects.link(o)\n    return paint(o, material, color)\n"
insert="""def auto_uv(o, scale=1.0):\n    if o.type!='MESH': return o\n    me=o.data; me.update()\n    uv=me.uv_layers.get('UVMap') or me.uv_layers.new(name='UVMap')\n    for poly in me.polygons:\n        n=poly.normal\n        ax=max(range(3), key=lambda i:abs(n[i]))\n        for li in poly.loop_indices:\n            co=me.vertices[me.loops[li].vertex_index].co\n            if ax==0: u,v=co.y,co.z\n            elif ax==1: u,v=co.x,co.z\n            else: u,v=co.x,co.y\n            uv.data[li].uv=(u*scale,v*scale)\n    return o\n\ndef mesh(name, verts, faces, material, color):\n    me = bpy.data.meshes.new(name+'Mesh')\n    me.from_pydata(verts, [], faces)\n    me.update()\n    o = bpy.data.objects.new(name, me)\n    bpy.context.collection.objects.link(o)\n    auto_uv(o,2.2)\n    return paint(o, material, color)\n"""
if needle not in src: raise SystemExit('mesh helper target missing')
src=src.replace(needle,insert,1)

# Primitive-created objects need UVs too.
src=src.replace("return paint(o,material,color)\n\ndef cyl(name", "auto_uv(o,2.2)\n    return paint(o,material,color)\n\ndef cyl(name",1)
src=src.replace("o=bpy.context.object; o.name=name\n    return paint(o,material,color)\n\ndef cyl_between", "o=bpy.context.object; o.name=name\n    auto_uv(o,2.2)\n    return paint(o,material,color)\n\ndef cyl_between",1)

# Add a dedicated material name for the face texture.
needle="BALLOON= make_mat('BalloonRed',    (0.62,0.018,0.014), .30)\n"
src=src.replace(needle,needle+"FACE   = make_mat('PennyFaceTex',  (0.72,0.70,0.62), .82)\n",1)

# Replace separate tiny face parts with a low-poly curved face patch + physical nose.
start=src.index("# Face: small physical layers rather than a flat texture.")
end=src.index("# Three front ornaments",start)
face="""# Face: N64-style curved low-poly mask carrying a 64x64 hand-painted texture.\n# Keep silhouette geometry (nose/hair) physical; move eyes/paint/grin detail into texture.\nfx=[-.16,0,.16]; fz=[.19,.02,-.18]; fv=[]\nfor zz in fz:\n    for xx in fx:\n        yy=-.202 + .025*(abs(xx)/.16)\n        fv.append((head.x+xx*s, head.y+yy*s, head.z+zz*s))\nff=[]\nfor yy in range(2):\n    for xx in range(2):\n        a=yy*3+xx; ff.append((a,a+1,a+4,a+3))\nfacepatch=mesh('PennyFacePatch',fv,ff,FACE,(.72,.70,.62))\nuv=facepatch.data.uv_layers.get('UVMap') or facepatch.data.uv_layers.new(name='UVMap')\nfor poly in facepatch.data.polygons:\n    for li in poly.loop_indices:\n        vi=facepatch.data.loops[li].vertex_index; gx=vi%3; gy=vi//3\n        uv.data[li].uv=(gx/2.0,1.0-gy/2.0)\nadd(facepatch,B['head'])\nadd(ico('Nose',(head.x,head.y-.221*s,head.z+.00*s),.052*s,RED,(.50,.01,.008),scale=(.90,.55,.90)),B['head'])\n\n"""
src=src[:start]+face+src[end:]

# Make head/hair silhouette less spherical and more recognizable.
src=src.replace("scale=(.82,1.05,1.20)","scale=(.72,.90,1.28)")
src=src.replace("scale=(.92,1.10,.98)","scale=(.78,.92,1.08)")
src=src.replace("scale=(1.25,.86,.75)","scale=(1.12,.74,.62)")

# Add authored sewer landmarks before boss chamber.
needle="# Boss chamber starts past the gate at Blender Y~=10.2 => game Z~-653.\n"
landmarks="""# PASS7 authored landmarks: break the repeating-tunnel look with chunky readable silhouettes.\n# Left maintenance alcove / black recess with rust frame.\nS(box('AlcoveDark',(-1.535,3.20,1.20),(.055,1.05,1.55),DARK,(.012,.013,.012)))\nfor z in (.48,1.92): S(box('AlcoveFrameZ',(-1.49,3.20,z),(.10,1.10,.10),TRIM,(.115,.075,.052)))\nfor y in (2.70,3.70): S(box('AlcoveFrameY',(-1.49,y,1.20),(.10,.10,1.55),TRIM,(.115,.075,.052)))\n# Right wall ladder, oversized N64-style silhouette.\nfor x in (1.31,1.44): S(cyl_between('LadderRail',(x,6.55,.42),(x,6.55,2.18),.032,METAL,(.055,.060,.057),6))\nfor z in [.58,.82,1.06,1.30,1.54,1.78,2.02]: S(cyl_between('LadderRung',(1.30,6.55,z),(1.45,6.55,z),.025,METAL,(.055,.060,.057),6))\n# Cross-tunnel pipe cluster / valve wheel landmark.\nS(cyl_between('CrossPipe',(-1.28,8.05,2.16),(1.28,8.05,2.16),.080,TRIM,(.115,.075,.052),8))\nS(ruff_folded('ValveWheel',(1.20,8.00,1.45),.12,.27,TRIM,(.115,.075,.052),10,.045))\n# Chunky floor grates over water channel.\nfor y in (4.55,7.25):\n    for x in (-.23,-.08,.08,.23): S(box('ChannelGrate',(x,y,.015),(.055,.58,.045),METAL,(.055,.060,.057)))\n# Hanging broken pipe near the scare zone.\nS(cyl_between('BrokenPipe',(0.86,5.65,2.52),(0.86,5.65,1.70),.070,TRIM,(.115,.075,.052),7))\nS(cyl_between('BrokenPipeLip',(0.76,5.65,1.72),(0.96,5.65,1.72),.035,TRIM,(.115,.075,.052),7))\n\n"""
if needle not in src: raise SystemExit('boss landmark insertion target missing')
src=src.replace(needle,landmarks+needle,1)

# Preview names / save names.
src=src.replace('PENNYWISE_PASS6_MODEL_PREVIEW.png','PENNYWISE_PASS7_MODEL_PREVIEW.png')
src=src.replace('pennywise_pass6.blend','pennywise_pass7.blend').replace('sewer_pass6.blend','sewer_pass7.blend')
src=src.replace("print('PASS6_ASSETS_COMPLETE')","print('PASS7_ASSETS_COMPLETE')")

(ROOT/'tools/build_assets_pass7.py').write_text(src)

# Runtime: PASS6 visuals plus more classic N64 fog falloff and slightly lower FOV.
c=(ROOT/'src/main_pass6.c').read_text()
c=c.replace('PENNYWISE 64 P6','PENNYWISE 64 P7')
c=c.replace('70.0f * DEG2RAD','67.0f * DEG2RAD')
c=c.replace('t3d_fog_set_range(235.0f, 790.0f);','t3d_fog_set_range(205.0f, 700.0f);')
# N64-like subdued lighting keeps textures readable without modern-looking flat brightness.
c=c.replace('uint8_t amb[4] = {34, 41, 38, 255};','uint8_t amb[4] = {30, 35, 33, 255};')
c=c.replace('uint8_t dirc[4] = {112, 119, 108, 255};','uint8_t dirc[4] = {102, 108, 99, 255};')
(ROOT/'src/main_pass7.c').write_text(c)

# PASS7 Makefile: safe PNG->sprite pipeline plus textured GLB conversion.
m=(ROOT/'Makefile').read_text()
m=m.replace('src = src/main_pass6.c','src = src/main_pass7.c')
m=m.replace('PENNYWISE64_PASS6','PENNYWISE64_PASS7').replace('PENNYWISE 64 P6','PENNYWISE 64 P7')
# use dedicated PASS7 material injector, not PASS6 sanitizer
m=m.replace('tools/sanitize_materials.py','tools/pass7_materials.py')
m=m.replace('python3 tools/sanitize_materials.py "$<"','python3 tools/pass7_materials.py "$<"')
# add PNG sprites to assets_conv and rule
m=m.replace('assets_gltf = $(wildcard assets/*.glb)\nassets_conv = $(addprefix filesystem/,$(notdir $(assets_gltf:%.glb=%.t3dm)))',
'''assets_gltf = $(wildcard assets/*.glb)\nassets_png = $(wildcard assets/*.png)\nassets_conv = $(addprefix filesystem/,$(notdir $(assets_gltf:%.glb=%.t3dm))) \\\n              $(addprefix filesystem/,$(notdir $(assets_png:%.png=%.sprite)))''')
rule='''\nfilesystem/%.sprite: assets/%.png\n\t@mkdir -p $(dir $@)\n\t@echo "    [N64-TEXTURE] $@"\n\t$(N64_MKSPRITE) $(MKSPRITE_FLAGS) -o filesystem "$<"\n'''
m=m.replace('\nfilesystem/%.t3dm:',rule+'\nfilesystem/%.t3dm:',1)
(ROOT/'Makefile').write_text(m)
print('PASS7_SOURCE_READY')

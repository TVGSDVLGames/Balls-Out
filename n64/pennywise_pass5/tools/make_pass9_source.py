#!/usr/bin/env python3
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
# Start from the exact known-good PASS8 fixed source generator.
exec((ROOT/'tools/make_pass8_source_fixed.py').read_text(), {'__name__':'__main__','__file__':str(ROOT/'tools/make_pass8_source_fixed.py')})

# -----------------------------------------------------------------------------
# Character authoring fixes
# -----------------------------------------------------------------------------
p=ROOT/'tools/build_assets_pass8.py'
s=p.read_text()

def req(old,new,label):
    global s
    if old not in s:
        raise SystemExit('PASS9 missing anchor: '+label)
    s=s.replace(old,new,1)

def rep(old,new):
    global s
    s=s.replace(old,new)

# Re-enable controlled antique-clown costume masses. PASS8 showed too much of
# the underlying superhero bodysuit and read as a mannequin.
req("PASS8_SKIP=('TunicUpper','TunicLower','Peplum','PeplumRed','SleevePuff','ForearmCloth','Bloomer','Stocking','FrontPiping','PennyFacePatch')",
    "PASS8_SKIP=('ForearmCloth','Stocking','FrontPiping','PennyFacePatch','ShoulderPleat','HipPleat')",
    'skip list')

# Scale the re-enabled cloth much smaller than the old doll-like versions.
repls={
"(.61*s,.36*s),(.50*s,.31*s),.64*s":"(.50*s,.29*s),(.44*s,.265*s),.55*s",
"(.64*s,.40*s),(.53*s,.34*s),.50*s":"(.53*s,.31*s),(.47*s,.285*s),.42*s",
".25*s,.47*s,.20*s":".22*s,.37*s,.145*s",
".30*s,.42*s,.15*s":".26*s,.34*s,.105*s",
"u,.22*s,IVORY":"u,.145*s,IVORY",
"tm,.24*s,IVORY":"tm,.165*s,IVORY",
".10*s,.32*s,.11*s":".085*s,.245*s,.075*s",
".085*s,.23*s,.075*s":".070*s,.185*s,.055*s",
"(.56*s,.33*s,.055*s)":"(.48*s,.285*s,.045*s)",
}
for old,new in repls.items(): req(old,new,'cloth scale '+old)

# Hair: pull it in toward the skull and remove the helmet/horn read.
for old,new in [
(".150*s, HAIR",".120*s, HAIR"),
(".128*s, HAIR",".105*s, HAIR"),
(".105*s, HAIR",".090*s, HAIR"),
(".13*s,HAIR",".095*s,HAIR"),
(".095*s,HAIR",".078*s,HAIR"),
("head.z+.27*s","head.z+.235*s"),
("head.x+side*.25*s","head.x+side*.215*s"),
("head.x+side*.22*s","head.x+side*.195*s"),
]: rep(old,new)

# Slightly less bulbous custom head.
req("rings=[(-.25,.105,.115),(-.16,.155,.145),(-.03,.185,.165),(.11,.190,.160),(.23,.150,.135),(.30,.080,.085)]",
    "rings=[(-.245,.105,.105),(-.155,.145,.132),(-.025,.165,.145),(.105,.170,.142),(.215,.142,.122),(.285,.078,.078)]",
    'head rings')

# Replace the fragile face decal-only read with physical low-poly facial pieces.
face_anchor="add(ico('Nose',(head.x,head.y-.174*s,head.z-.005*s),.050*s,RED,(.72,.03,.02),scale=(.92,.62,.92)),B['head'])\n"
face_geo=r'''add(ico('Nose',(head.x,head.y-.172*s,head.z-.008*s),.044*s,RED,(.72,.03,.02),scale=(.92,.62,.92)),B['head'])
# Physical face detail: survives Tiny3D backface/decal quirks and 320x240.
for side in (-1,1):
    add(ico('EyeSocketL' if side<0 else 'EyeSocketR',(head.x+side*.060*s,head.y-.180*s,head.z+.070*s),.038*s,DARK,(.02,.018,.016),scale=(1.05,.42,.72)),B['head'])
    add(ico('EyeL' if side<0 else 'EyeR',(head.x+side*.060*s,head.y-.198*s,head.z+.070*s),.018*s,EYE,(.96,.58,.08),scale=(.85,.45,.85)),B['head'])
    add(box('PaintL' if side<0 else 'PaintR',(head.x+side*.066*s,head.y-.194*s,head.z-.008*s),(.020*s,.010*s,.120*s),RED,(.80,.03,.02)),B['head'])
add(box('Mouth',(head.x,head.y-.196*s,head.z-.095*s),(.120*s,.010*s,.034*s),DARK,(.018,.012,.010)),B['head'])
add(box('Teeth',(head.x,head.y-.202*s,head.z-.084*s),(.078*s,.008*s,.013*s),TEETH,(.93,.88,.69)),B['head'])
'''
req(face_anchor,face_geo,'physical face')

# Remove the bright horizontal/vertical cross directly behind the boss. Replace
# it with two side strips and one ceiling strip so the silhouette stays readable.
req("for i,x in enumerate((-1.35,1.35)):\n    S(box('BossGlowV%02d'%i,(x,12.65,1.35),(.09,.18,2.18),BOSSGLOW,(.90,.10,.045)))\nfor i,y in enumerate((12.20,13.10)):\n    S(box('BossGlowH%02d'%i,(0,y,2.44),(3.45,.10,.09),BOSSGLOW,(.90,.10,.045)))",
    "for i,x in enumerate((-1.55,1.55)):\n    S(box('BossGlowV%02d'%i,(x,12.82,1.42),(.075,.12,1.75),BOSSGLOW,(.78,.07,.035)))\nS(box('BossGlowCeiling',(0,12.82,2.62),(2.75,.12,.075),BOSSGLOW,(.78,.07,.035)))",
    'boss glow')

# Rename authored proof outputs.
s=s.replace('PENNYWISE_PASS8_MODEL_PREVIEW.png','PENNYWISE_PASS9_MODEL_PREVIEW.png')
s=s.replace('pennywise_pass8.blend','pennywise_pass9.blend')
s=s.replace('sewer_pass8.blend','sewer_pass9.blend')
(ROOT/'tools/build_assets_pass9.py').write_text(s)

# -----------------------------------------------------------------------------
# Runtime fixes
# -----------------------------------------------------------------------------
for name in ('main_pass8.c','main_pass8_bossproof.c'):
    cp=ROOT/'src'/name
    c=cp.read_text()
    # Tiny3D import orientation is opposite the Blender proof camera. PASS8's
    # boss capture was showing the back of the head. Rotate the model 180 deg.
    old="float faceYaw = atan2f(playerPos.v[0] - pennyPos.v[0], playerPos.v[2] - pennyPos.v[2]);"
    new="float faceYaw = atan2f(playerPos.v[0] - pennyPos.v[0], playerPos.v[2] - pennyPos.v[2]) + 3.14159265f;"
    if old not in c: raise SystemExit('PASS9 faceYaw anchor changed '+name)
    c=c.replace(old,new,1)
    c=c.replace('(float[3]){0.92f,1.10f,0.92f}','(float[3]){0.90f,1.06f,0.90f}',1)
    out='main_pass9_bossproof.c' if 'bossproof' in name else 'main_pass9.c'
    (ROOT/'src'/out).write_text(c)

# Boss proof must resemble the actual start of the fight, not put the camera
# inside Pennywise's face.
bp=ROOT/'src/main_pass9_bossproof.c'
c=bp.read_text()
c=c.replace('static fm_vec3_t playerPos = {{0.0f, 104.0f, -710.0f}};','static fm_vec3_t playerPos = {{0.0f, 104.0f, -660.0f}};',1)
c=c.replace('static fm_vec3_t pennyPos = {{0.0f, 0.0f, -805.0f}};','static fm_vec3_t pennyPos = {{0.0f, 0.0f, -850.0f}};',1)
bp.write_text(c)

# PASS9 ROM target.
m=ROOT/'Makefile'
mk=m.read_text()
mk=mk.replace('src = src/main_pass8.c','src = src/main_pass9.c')
mk=mk.replace('PENNYWISE64_PASS8','PENNYWISE64_PASS9')
mk=mk.replace('PENNYWISE 64 P8','PENNYWISE 64 P9')
m.write_text(mk)

print('PASS9 source generated')

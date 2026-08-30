#!/usr/bin/env python3
from pathlib import Path
R=Path(__file__).resolve().parents[1]
p9=R/'tools/make_pass9_source.py'; exec(p9.read_text(),{'__name__':'__main__','__file__':str(p9)})

def one(s,a,b,label):
    if a not in s: raise SystemExit('PASS10 missing '+label)
    return s.replace(a,b,1)

# ART
p=R/'tools/build_assets_pass9.py'; s=p.read_text()
s=one(s,"""for i,x in enumerate((-1.55,1.55)):
    S(box('BossGlowV%02d'%i,(x,12.82,1.42),(.075,.12,1.75),BOSSGLOW,(.78,.07,.035)))
S(box('BossGlowCeiling',(0,12.82,2.62),(2.75,.12,.075),BOSSGLOW,(.78,.07,.035)))
""","""for i,x in enumerate((-1.58,1.58)):
    for j,z in enumerate((.82,1.84)):
        S(box('BossLampCage%02d_%02d'%(i,j),(x,12.80,z),(.19,.13,.16),METAL,(.13,.14,.13)))
        S(box('BossLampRed%02d_%02d'%(i,j),(x,12.72,z),(.085,.055,.075),BOSSGLOW,(.68,.035,.018)))
S(box('BossLampTop',(0,12.72,2.58),(.13,.055,.085),BOSSGLOW,(.62,.03,.016)))
""",'boss lamp art')
s=one(s,"""def reset_pose():
    for p in arm.pose.bones:
        p.rotation_euler=(0,0,0); p.location=(0,0,0); p.scale=(1,1,1)
""","""def reset_pose():
    for p in arm.pose.bones:
        p.rotation_euler=(0,0,0); p.location=(0,0,0); p.scale=(1,1,1)
    for key,sy in (('ual',.88),('uar',.88),('lal',.90),('lar',.90)):
        bn=B.get(key); pb=arm.pose.bones.get(bn) if bn else None
        if pb: pb.scale=(1.0,sy,1.0)
""",'arm proportions')
s=one(s,"            pb.keyframe_insert('location',frame=fr,group=pb.name)\n","            pb.keyframe_insert('location',frame=fr,group=pb.name)\n            pb.keyframe_insert('scale',frame=fr,group=pb.name)\n",'scale keys')
s=one(s,"action('Penny_Walk',[(1,{'tl':(.48,0,0),'tr':(-.48,0,0),'ual':(-.22,-.08,-1.02),'uar':(.22,.08,1.02)}),(10,{'tl':(-.48,0,0),'tr':(.48,0,0),'ual':(.22,-.08,-1.02),'uar':(-.22,.08,1.02)}),(19,{'tl':(.48,0,0),'tr':(-.48,0,0),'ual':(-.22,-.08,-1.02),'uar':(.22,.08,1.02)})]),","action('Penny_Walk',[(1,{'tl':(.31,0,0),'tr':(-.31,0,0),'ual':(-.12,-.08,-1.00),'uar':(.12,.08,1.00),'head':(.025,0,-.025)}),(10,{'tl':(-.31,0,0),'tr':(.31,0,0),'ual':(.12,-.08,-1.00),'uar':(-.12,.08,1.00),'sp2':(-.025,0,.018),'head':(-.018,0,.025)}),(19,{'tl':(.31,0,0),'tr':(-.31,0,0),'ual':(-.12,-.08,-1.00),'uar':(.12,.08,1.00),'head':(.025,0,-.025)})]),",'walk')
s=one(s,"action('Penny_Attack',[(1,{'ual':downL,'uar':downR}),(7,{'sp2':(-.34,0,0),'ual':(-1.12,-.08,-.28),'uar':(-1.12,.08,.28),'lal':(-.62,0,0),'lar':(-.62,0,0),'head':(.19,0,0)}),(14,{'ual':downL,'uar':downR})]),","action('Penny_Attack',[(1,{'ual':downL,'uar':downR,'head':(.03,0,0)}),(7,{'sp2':(-.27,0,0),'ual':(-.82,-.08,-.50),'uar':(-.82,.08,.50),'lal':(-.46,0,0),'lar':(-.46,0,0),'head':(.16,0,0)}),(14,{'ual':downL,'uar':downR,'sp2':(-.04,0,0)})]),",'attack')
for a,b in [
(".120*s, HAIR,(.45,.055,.018),scale=(.72,.90,1.28))",".108*s, HAIR,(.45,.055,.018),scale=(.78,.90,1.18),subdivisions=2)"),
(".090*s, HAIR,(.45,.055,.018),scale=(.78,.92,1.08))",".082*s, HAIR,(.45,.055,.018),scale=(.82,.92,1.02),subdivisions=2)"),
(".090*s, HAIR,(.45,.055,.018),scale=(.78,.92,1.04))",".078*s, HAIR,(.45,.055,.018),scale=(.82,.90,.98),subdivisions=2)"),
(".078*s,HAIR,(.45,.055,.018),scale=(1.12,.74,.62))",".070*s,HAIR,(.45,.055,.018),scale=(1.06,.78,.58),subdivisions=2)"),
("rings=[(-.245,.105,.105),(-.155,.145,.132),(-.025,.165,.145),(.105,.170,.142),(.215,.142,.122),(.285,.078,.078)]","rings=[(-.235,.112,.108),(-.150,.150,.134),(-.020,.170,.146),(.100,.174,.143),(.205,.146,.123),(.262,.082,.080)]")]: s=one(s,a,b,'hair/head')
s=s.replace("scale=(.82,1.08,1.22)),B['head'])","scale=(.82,1.08,1.22),subdivisions=2),B['head'])").replace("scale=(.88,1.06,.92)),B['head'])","scale=(.88,1.06,.92),subdivisions=2),B['head'])")
s=s.replace('PENNYWISE_PASS9_MODEL_PREVIEW.png','PENNYWISE_PASS10_MODEL_PREVIEW.png').replace('pennywise_pass9.blend','pennywise_pass10.blend').replace('sewer_pass9.blend','sewer_pass10.blend')
(R/'tools/build_assets_pass10.py').write_text(s)

# RUNTIME
for src,out,bp in [('main_pass9.c','main_pass10.c',False),('main_pass9_bossproof.c','main_pass10_bossproof.c',True)]:
    c=(R/'src'/src).read_text()
    oldstate="static int frameCounter = 0;\nstatic EnemyState enemyState = ENEMY_IDLE;" if bp else "static int frameCounter = 0;\nstatic EnemyState enemyState = ENEMY_HIDDEN;"
    newstate=("static int frameCounter = 0;\nstatic int scareTimer = 0;\nstatic bool scareTriggered = true;\nstatic int teleportTimer = 0;\nstatic int teleportIndex = 0;\nstatic int attackTimer = 0;\nstatic int attackCooldown = 36;\nstatic int bossPhase = 1;\nstatic EnemyState enemyState = ENEMY_IDLE;" if bp else "static int frameCounter = 0;\nstatic int scareTimer = 0;\nstatic bool scareTriggered = false;\nstatic int teleportTimer = 0;\nstatic int teleportIndex = 0;\nstatic int attackTimer = 0;\nstatic int attackCooldown = 0;\nstatic int bossPhase = 1;\nstatic EnemyState enemyState = ENEMY_HIDDEN;")
    c=one(c,oldstate,newstate,'state')
    c=one(c,"    frameCounter = 0;\n    enemyState = ENEMY_HIDDEN;","    frameCounter = 0;\n    scareTimer = 0;\n    scareTriggered = false;\n    teleportTimer = 0;\n    teleportIndex = 0;\n    attackTimer = 0;\n    attackCooldown = 0;\n    bossPhase = 1;\n    enemyState = ENEMY_HIDDEN;",'reset')
    c=one(c,"    if (!bossStarted || enemyState == ENEMY_DEAD) return false;","    if (!bossStarted || enemyState == ENEMY_DEAD || teleportTimer > 5) return false;",'aim teleport')
    c=one(c,"    return dot > 0.982f;","    return dot > 0.976f;",'aim')
    c=one(c,"    int i = (bossTimer / 240) & 3;\n    pennyPos.v[0] = pos[i][0];\n    pennyPos.v[2] = pos[i][1];\n","    int i = teleportIndex++ & 3;\n    pennyPos.v[0] = pos[i][0];\n    pennyPos.v[2] = pos[i][1];\n",'teleport seq')
    c=one(c,"    T3DMat4FP *grateMat = malloc_uncached(sizeof(T3DMat4FP) * FB_COUNT);","    T3DMat4FP *grateMat = malloc_uncached(sizeof(T3DMat4FP) * FB_COUNT);\n    T3DMat4FP *scareMat = malloc_uncached(sizeof(T3DMat4FP) * FB_COUNT);\n    T3DMat4FP *bossBalloonMat = malloc_uncached(sizeof(T3DMat4FP) * FB_COUNT);",'mat alloc')
    c=one(c,"            if (!bossStarted && playerPos.v[2] < -648.0f) {\n                bossStarted = true;\n                enemyState = ENEMY_IDLE;\n                bossTimer = 0;\n                playerPos.v[2] = -660.0f;\n            }","            if (!scareTriggered && !bossStarted && playerPos.v[2] < -300.0f) { scareTriggered = true; scareTimer = 105; }\n            if (scareTimer > 0) scareTimer--;\n            if (!bossStarted && playerPos.v[2] < -648.0f) {\n                bossStarted = true; enemyState = ENEMY_IDLE; bossTimer = 0; teleportTimer = 0; attackTimer = 0; attackCooldown = 42; playerPos.v[2] = -660.0f;\n            }",'intro')
    c=one(c,"                    bossHP -= 10;\n                    hurtTimer = 18;\n                    enemyState = ENEMY_HURT;","                    bossHP -= 10;\n                    hurtTimer = 18;\n                    attackTimer = 0;\n                    enemyState = ENEMY_HURT;",'hurt')
    old="""            if (bossStarted && enemyState != ENEMY_DEAD) {
                bossTimer++;
                if ((bossTimer % 240) == 0) choose_penny_teleport();
                float dx = playerPos.v[0] - pennyPos.v[0];
                float dz = playerPos.v[2] - pennyPos.v[2];
                float dist = len2(dx, dz);

                if (hurtTimer > 0) {
                    hurtTimer--;
                    enemyState = ENEMY_HURT;
                } else if (dist < 62.0f) {
                    enemyState = ENEMY_ATTACK;
                    if ((bossTimer % 72) == 0) {
                        health -= 15;
                        if (health <= 0) {
                            health = 0;
                            dead = true;
                        }
                    }
                } else {
                    enemyState = ENEMY_CHASE;
                    float chase = 31.0f * dt;
                    pennyPos.v[0] += dx / (dist + 0.01f) * chase;
                    pennyPos.v[2] += dz / (dist + 0.01f) * chase;
                    pennyPos.v[0] = clampf(pennyPos.v[0], -132.0f, 132.0f);
                    pennyPos.v[2] = clampf(pennyPos.v[2], -925.0f, -680.0f);
                }
            }
"""
    new="""            if (bossStarted && enemyState != ENEMY_DEAD) {
                bossTimer++; bossPhase = bossHP <= 35 ? 3 : (bossHP <= 70 ? 2 : 1);
                if (attackCooldown > 0) attackCooldown--;
                float dx = playerPos.v[0] - pennyPos.v[0], dz = playerPos.v[2] - pennyPos.v[2], dist = len2(dx,dz);
                if (hurtTimer > 0) { hurtTimer--; attackTimer=0; enemyState=ENEMY_HURT; }
                else if (teleportTimer > 0) { teleportTimer--; enemyState=ENEMY_IDLE; if (teleportTimer==15) choose_penny_teleport(); }
                else {
                    int teleportEvery = bossPhase==1 ? 240 : (bossPhase==2 ? 180 : 130);
                    if ((bossTimer % teleportEvery)==0) { teleportTimer=30; attackTimer=0; enemyState=ENEMY_IDLE; }
                    else if (attackTimer > 0) {
                        enemyState=ENEMY_ATTACK; attackTimer--;
                        if (attackTimer==10 && dist<86.0f) { health -= bossPhase==3 ? 20 : (bossPhase==2 ? 17 : 15); if (health<=0){health=0;dead=true;} }
                        if (attackTimer==0) attackCooldown = bossPhase==3 ? 34 : 46;
                    } else if (dist<74.0f && attackCooldown==0) {
                        attackTimer=28; enemyState=ENEMY_ATTACK; t3d_anim_set_time(&attack,0.0f); t3d_anim_set_playing(&attack,true);
                    } else {
                        enemyState=ENEMY_CHASE; float chase=(bossPhase==1?31.0f:(bossPhase==2?38.0f:46.0f))*dt;
                        pennyPos.v[0]+=dx/(dist+.01f)*chase; pennyPos.v[2]+=dz/(dist+.01f)*chase;
                        pennyPos.v[0]=clampf(pennyPos.v[0],-132.0f,132.0f); pennyPos.v[2]=clampf(pennyPos.v[2],-925.0f,-680.0f);
                    }
                }
            }
"""
    c=one(c,old,new,'boss ai')
    c=one(c,"        t3d_mat4fp_from_srt_euler(&balloonMat[frame], (float[3]){1,1,1}, (float[3]){0,0,0}, (float[3]){32.0f, 102.0f, -385.0f});","        t3d_mat4fp_from_srt_euler(&balloonMat[frame], (float[3]){0.56f,0.56f,0.56f}, (float[3]){0,0,0}, (float[3]){62.0f, 103.0f, -430.0f});",'corridor balloon')
    a="        t3d_mat4fp_from_srt_euler(&grateMat[frame], (float[3]){1,1,1}, (float[3]){0,0,0}, (float[3]){0.0f, 0.0f, -652.0f});\n"
    b=a+"        float scareYaw = atan2f(playerPos.v[0] - 38.0f, playerPos.v[2] + 430.0f);\n        t3d_mat4fp_from_srt_euler(&scareMat[frame], (float[3]){0.82f,0.96f,0.82f}, (float[3]){0,scareYaw,0}, (float[3]){38.0f,0.0f,-430.0f});\n        float bfloat = teleportTimer > 0 ? sinf((float)frameCounter*.18f)*4.0f : 0.0f;\n        t3d_mat4fp_from_srt_euler(&bossBalloonMat[frame], (float[3]){0.58f,0.58f,0.58f}, (float[3]){0,0,0}, (float[3]){pennyPos.v[0]+26.0f,102.0f+bfloat,pennyPos.v[2]-8.0f});\n"
    c=one(c,a,b,'extra matrices')
    c=one(c,"        t3d_light_set_point(1, lamp, &lampPos, 0.0105f, false);\n        t3d_light_set_count(2);\n        t3d_light_set_exposure(1.35f);\n","        t3d_light_set_point(1, lamp, &lampPos, 0.0105f, false);\n        int lightCount=2;\n        if (bossStarted && !won) { uint8_t bossLight[4]={(uint8_t)(bossPhase==3?235:190),(uint8_t)(enemyState==ENEMY_HURT?160:48),(uint8_t)(enemyState==ENEMY_HURT?135:28),255}; fm_vec3_t bossLightPos={{pennyPos.v[0],92.0f,pennyPos.v[2]}}; t3d_light_set_point(2,bossLight,&bossLightPos,0.0135f,false); lightCount=3; }\n        t3d_light_set_count(lightCount);\n        t3d_light_set_exposure(1.35f);\n",'boss light')
    c=one(c,"""        if (playerPos.v[2] < -285.0f && playerPos.v[2] > -470.0f && !bossStarted) {
            t3d_matrix_push(&balloonMat[frame]);
            t3d_model_draw(balloon);
            t3d_matrix_pop(1);
        }

        if (bossStarted) {
            t3d_matrix_push(&grateMat[frame]);
            t3d_model_draw(grate);
            t3d_matrix_pop(1);

            t3d_skeleton_use(&skel);
            t3d_matrix_push(&pennyMat[frame]);
            t3d_model_draw_skinned(penny, &skel);
            t3d_matrix_pop(1);
        }
""","""        if (playerPos.v[2] < -285.0f && playerPos.v[2] > -470.0f && !bossStarted) { t3d_matrix_push(&balloonMat[frame]); t3d_model_draw(balloon); t3d_matrix_pop(1); }
        if (!bossStarted && scareTimer > 8) { t3d_skeleton_use(&skel); t3d_matrix_push(&scareMat[frame]); t3d_model_draw_skinned(penny,&skel); t3d_matrix_pop(1); }
        if (bossStarted) {
            t3d_matrix_push(&grateMat[frame]); t3d_model_draw(grate); t3d_matrix_pop(1);
            if (teleportTimer>0) { t3d_matrix_push(&bossBalloonMat[frame]); t3d_model_draw(balloon); t3d_matrix_pop(1); }
            if (teleportTimer<=5) { t3d_skeleton_use(&skel); t3d_matrix_push(&pennyMat[frame]); t3d_model_draw_skinned(penny,&skel); t3d_matrix_pop(1); }
        }
""",'draw')
    c=one(c,'        if (bossStarted && !won) rdpq_text_printf(NULL, FONT_BUILTIN_DEBUG_MONO, 244, 14, "IT %03d", bossHP);','        if (bossStarted && !won) { rdpq_text_printf(NULL, FONT_BUILTIN_DEBUG_MONO, 220, 14, "IT %03d P%d", bossHP, bossPhase); if (bossTimer < 120) rdpq_text_printf(NULL, FONT_BUILTIN_DEBUG_MONO, 92, 32, "SILVER HURTS IT"); }','hud')
    c=one(c,'            rdpq_text_printf(NULL, FONT_BUILTIN_DEBUG_MONO, 99, 194, "YOU\'LL FLOAT TOO");','            rdpq_text_printf(NULL, FONT_BUILTIN_DEBUG_MONO, 99, 194, scareTimer > 8 ? "YOU\'LL FLOAT TOO" : "WHERE DID HE GO?");','scare text')
    (R/'src'/out).write_text(c)

m=R/'Makefile'; x=m.read_text().replace('src = src/main_pass9.c','src = src/main_pass10.c').replace('PENNYWISE64_PASS9','PENNYWISE64_PASS10').replace('PENNYWISE 64 P9','PENNYWISE 64 P10'); m.write_text(x)
print('PASS10 source generated')

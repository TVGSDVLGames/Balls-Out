#include <libdragon.h>
#include <t3d/t3d.h>
#include <t3d/t3dmodel.h>
#include <t3d/t3dskeleton.h>
#include <t3d/t3danim.h>
#include <math.h>
#include <stdbool.h>
#include <stdio.h>

#define FB_COUNT 3
#define DEG2RAD 0.01745329251994329577f

typedef enum { ENEMY_HIDDEN, ENEMY_IDLE, ENEMY_CHASE, ENEMY_ATTACK, ENEMY_HURT, ENEMY_DEAD } EnemyState;

static fm_vec3_t playerPos = {{0.0f, 4.0f, 0.0f}};
static float yaw = 3.14159265f;
static float pitch = 0.0f;
static int health = 100;
static int ammo = 32;
static int bossHP = 100;
static bool bossStarted = false;
static bool won = false;
static bool dead = false;
static int bossTimer = 0;
static int hurtTimer = 0;
static int muzzleTimer = 0;
static EnemyState enemyState = ENEMY_HIDDEN;
static fm_vec3_t pennyPos = {{0.0f, 0.0f, -175.0f}};

static float clampf(float v, float lo, float hi) { return v < lo ? lo : (v > hi ? hi : v); }
static float len2(float x, float z) { return sqrtf(x*x + z*z); }

static void reset_game(void) {
    playerPos = (fm_vec3_t){{0.0f, 4.0f, 0.0f}};
    yaw = 3.14159265f; pitch = 0.0f; health = 100; ammo = 32; bossHP = 100;
    bossStarted = false; won = false; dead = false; bossTimer = 0; hurtTimer = 0;
    enemyState = ENEMY_HIDDEN;
    pennyPos = (fm_vec3_t){{0.0f, 0.0f, -175.0f}};
}

static void collide_player(fm_vec3_t *p) {
    if (p->v[2] > -126.0f) {
        p->v[0] = clampf(p->v[0], -17.0f, 17.0f);
        p->v[2] = clampf(p->v[2], -126.0f, 8.0f);
    } else {
        p->v[0] = clampf(p->v[0], -43.0f, 43.0f);
        p->v[2] = clampf(p->v[2], -207.0f, -126.0f);
    }
    p->v[1] = 4.0f;
}

static bool aim_hits_boss(void) {
    float dx = pennyPos.v[0] - playerPos.v[0];
    float dz = pennyPos.v[2] - playerPos.v[2];
    float dist = len2(dx, dz);
    if (!bossStarted || enemyState == ENEMY_DEAD || dist > 95.0f) return false;
    float fx = sinf(yaw), fz = cosf(yaw);
    float dot = (dx*fx + dz*fz) / (dist + 0.0001f);
    return dot > 0.965f;
}

static void choose_penny_teleport(void) {
    static const float pos[4][2] = {{-30,-185},{30,-185},{-30,-145},{30,-145}};
    int i = (bossTimer / 240) & 3;
    pennyPos.v[0] = pos[i][0]; pennyPos.v[2] = pos[i][1];
}

int main(void) {
    debug_init_isviewer();
    debug_init_usblog();
    asset_init_compression(2);
    dfs_init(DFS_DEFAULT_LOCATION);
    display_init(RESOLUTION_320x240, DEPTH_16_BPP, FB_COUNT, GAMMA_NONE, FILTERS_RESAMPLE_ANTIALIAS);
    rdpq_init();
    joypad_init();
    t3d_init((T3DInitParams){});
    rdpq_text_register_font(FONT_BUILTIN_DEBUG_MONO, rdpq_font_load_builtin(FONT_BUILTIN_DEBUG_MONO));

    T3DViewport viewport = t3d_viewport_create_buffered(FB_COUNT);
    T3DMat4FP *sewerMat = malloc_uncached(sizeof(T3DMat4FP));
    T3DMat4FP *pennyMat = malloc_uncached(sizeof(T3DMat4FP) * FB_COUNT);
    T3DMat4FP *balloonMat = malloc_uncached(sizeof(T3DMat4FP) * FB_COUNT);
    t3d_mat4fp_from_srt_euler(sewerMat, (float[3]){1,1,1}, (float[3]){0,0,0}, (float[3]){0,0,0});

    T3DModel *sewer = t3d_model_load("rom:/sewer.t3dm");
    T3DModel *penny = t3d_model_load("rom:/pennywise.t3dm");
    T3DModel *balloon = t3d_model_load("rom:/balloon.t3dm");
    T3DSkeleton skel = t3d_skeleton_create_buffered(penny, FB_COUNT);

    T3DAnim idle = t3d_anim_create(penny, "Penny_Idle");
    T3DAnim walk = t3d_anim_create(penny, "Penny_Walk");
    T3DAnim attack = t3d_anim_create(penny, "Penny_Attack");
    T3DAnim hurt = t3d_anim_create(penny, "Penny_Hurt");
    T3DAnim death = t3d_anim_create(penny, "Penny_Death");
    t3d_anim_attach(&idle, &skel); t3d_anim_attach(&walk, &skel); t3d_anim_attach(&attack, &skel);
    t3d_anim_attach(&hurt, &skel); t3d_anim_attach(&death, &skel);
    t3d_anim_set_looping(&attack, false); t3d_anim_set_looping(&hurt, false); t3d_anim_set_looping(&death, false);

    int frame = 0;
    float last = (float)get_ticks_us() / 1000000.0f;
    for (;;) {
        frame = (frame + 1) % FB_COUNT;
        joypad_poll();
        joypad_inputs_t in = joypad_get_inputs(JOYPAD_PORT_1);
        joypad_buttons_t pressed = joypad_get_buttons_pressed(JOYPAD_PORT_1);
        float now = (float)get_ticks_us() / 1000000.0f;
        float dt = clampf(now - last, 0.0f, 0.05f); last = now;

        if ((dead || won) && pressed.start) reset_game();
        if (!dead && !won) {
            yaw -= (float)in.stick_x * 0.00075f;
            if (in.btn.c_up) pitch += 0.022f;
            if (in.btn.c_down) pitch -= 0.022f;
            pitch = clampf(pitch, -0.55f, 0.55f);
            float speed = ((float)in.stick_y / 85.0f) * 1.15f;
            float strafe = (in.btn.c_right ? 0.75f : 0.0f) - (in.btn.c_left ? 0.75f : 0.0f);
            playerPos.v[0] += sinf(yaw) * speed + cosf(yaw) * strafe;
            playerPos.v[2] += cosf(yaw) * speed - sinf(yaw) * strafe;
            collide_player(&playerPos);

            if (!bossStarted && playerPos.v[2] < -131.0f) {
                bossStarted = true; enemyState = ENEMY_IDLE; bossTimer = 0;
            }

            if ((pressed.z || pressed.a) && ammo > 0) {
                ammo--; muzzleTimer = 5;
                if (aim_hits_boss()) {
                    bossHP -= 10; hurtTimer = 16; enemyState = ENEMY_HURT;
                    t3d_anim_set_time(&hurt, 0.0f); t3d_anim_set_playing(&hurt, true);
                    if (bossHP <= 0) {
                        bossHP = 0; enemyState = ENEMY_DEAD;
                        t3d_anim_set_time(&death, 0.0f); t3d_anim_set_playing(&death, true);
                    }
                }
            }
            if (muzzleTimer > 0) muzzleTimer--;

            if (bossStarted && enemyState != ENEMY_DEAD) {
                bossTimer++;
                if ((bossTimer % 240) == 0) choose_penny_teleport();
                float dx = playerPos.v[0] - pennyPos.v[0];
                float dz = playerPos.v[2] - pennyPos.v[2];
                float dist = len2(dx,dz);
                if (hurtTimer > 0) { hurtTimer--; enemyState = ENEMY_HURT; }
                else if (dist < 10.5f) {
                    enemyState = ENEMY_ATTACK;
                    if ((bossTimer % 70) == 0) { health -= 15; if (health <= 0) { health = 0; dead = true; } }
                } else {
                    enemyState = ENEMY_CHASE;
                    pennyPos.v[0] += dx / (dist+0.01f) * 0.34f;
                    pennyPos.v[2] += dz / (dist+0.01f) * 0.34f;
                    pennyPos.v[0] = clampf(pennyPos.v[0], -38, 38);
                    pennyPos.v[2] = clampf(pennyPos.v[2], -202, -134);
                }
            }
            if (enemyState == ENEMY_DEAD && !death.isPlaying && bossStarted) won = true;
        }

        if (enemyState == ENEMY_HURT) t3d_anim_update(&hurt, dt);
        else if (enemyState == ENEMY_ATTACK) {
            if (!attack.isPlaying) { t3d_anim_set_time(&attack,0); t3d_anim_set_playing(&attack,true); }
            t3d_anim_update(&attack, dt);
        } else if (enemyState == ENEMY_DEAD) t3d_anim_update(&death, dt);
        else if (enemyState == ENEMY_CHASE) t3d_anim_update(&walk, dt);
        else t3d_anim_update(&idle, dt);
        t3d_skeleton_update(&skel);

        fm_vec3_t cam = playerPos;
        fm_vec3_t target = {{
            cam.v[0] + sinf(yaw) * 30.0f,
            cam.v[1] + sinf(pitch) * 30.0f,
            cam.v[2] + cosf(yaw) * 30.0f
        }};
        t3d_viewport_set_projection(&viewport, 72.0f * DEG2RAD, 1.0f, 260.0f);
        t3d_viewport_look_at(&viewport, &cam, &target, &(fm_vec3_t){{0,1,0}});
        float faceYaw = atan2f(playerPos.v[0]-pennyPos.v[0], playerPos.v[2]-pennyPos.v[2]);
        t3d_mat4fp_from_srt_euler(&pennyMat[frame], (float[3]){1,1,1}, (float[3]){0,faceYaw,0}, pennyPos.v);
        t3d_mat4fp_from_srt_euler(&balloonMat[frame], (float[3]){1,1,1}, (float[3]){0,0,0}, (float[3]){9,7,-82});

        rdpq_attach(display_get(), display_get_zbuf());
        t3d_frame_start();
        t3d_viewport_attach(&viewport);
        t3d_screen_clear_color(RGBA32(7, 11, 11, 0xFF));
        t3d_screen_clear_depth();
        uint8_t amb[4] = {45,55,52,255};
        uint8_t dirc[4] = {120,135,125,255};
        fm_vec3_t ldir = {{0.4f, 1.0f, -0.3f}}; fm_vec3_norm(&ldir,&ldir);
        t3d_light_set_ambient(amb); t3d_light_set_directional(0,dirc,&ldir); t3d_light_set_count(1);

        t3d_matrix_push(sewerMat); t3d_model_draw(sewer); t3d_matrix_pop(1);
        if (playerPos.v[2] < -48.0f && playerPos.v[2] > -112.0f) {
            t3d_matrix_push(&balloonMat[frame]); t3d_model_draw(balloon); t3d_matrix_pop(1);
        }
        if (bossStarted) {
            t3d_skeleton_use(&skel);
            t3d_matrix_push(&pennyMat[frame]); t3d_model_draw_skinned(penny, &skel); t3d_matrix_pop(1);
        }

        rdpq_set_mode_standard();
        rdpq_text_printf(NULL, FONT_BUILTIN_DEBUG_MONO, 8, 14, "HP %d   SHOTS %d", health, ammo);
        if (bossStarted && !won) rdpq_text_printf(NULL, FONT_BUILTIN_DEBUG_MONO, 220, 14, "IT %d", bossHP);
        rdpq_text_printf(NULL, FONT_BUILTIN_DEBUG_MONO, 158, 121, "+");
        if (playerPos.v[2] < -52.0f && playerPos.v[2] > -72.0f && !bossStarted)
            rdpq_text_printf(NULL, FONT_BUILTIN_DEBUG_MONO, 94, 200, "YOU'LL FLOAT TOO");
        if (dead) rdpq_text_printf(NULL, FONT_BUILTIN_DEBUG_MONO, 92, 112, "YOU DIED - START");
        if (won) rdpq_text_printf(NULL, FONT_BUILTIN_DEBUG_MONO, 70, 112, "PENNYWISE DEFEATED - START");
        if (muzzleTimer) rdpq_text_printf(NULL, FONT_BUILTIN_DEBUG_MONO, 150, 205, "*FIRE*");
        rdpq_detach_show();
    }
}

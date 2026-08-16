extends Node2D

# Atari Millipede source-fidelity rebuild.
# Logical upright playfield: 30 columns x 32 rows, 8 logical units each = 240x256.
# The original raster is 256x240 before ROT270. We deliberately display 240x256
# into a physical 3:4 viewport: X pixel pitch is 0.8 of Y, approximating the CRT.

const LW := 240.0
const LH := 256.0
const COLS := 30
const ROWS := 32
const CELL := 8.0
const PLAYER_TOP := 208.0 # 6 rows / 48 logical pixels at bottom.
const SX := 768.0 / LW
const SY := 1024.0 / LH
const SOURCE_HZ := 59.88593
const SOURCE_DT := 1.0 / SOURCE_HZ
const RAID_LEVELS := [11, 7, 5, 3, 1]
const DDT_CELLS := [Vector2i(6,18), Vector2i(8,6), Vector2i(17,12), Vector2i(23,8)]

@onready var bg = $Background
@onready var post_fx = $PostFX/Screen
@onready var score_label = $UI/Score
@onready var lives_label = $UI/Lives
@onready var wave_label = $UI/Wave
@onready var status_label = $UI/Status
@onready var fire_button = $UI/Fire
@onready var start_overlay = $UI/StartOverlay
@onready var start_button = $UI/StartOverlay/Start
@onready var pause_touch = $UI/PauseTouch
@onready var pause_overlay = $UI/PauseOverlay
@onready var resume_button = $UI/PauseOverlay/Resume
@onready var restart_button = $UI/PauseOverlay/Restart
@onready var fx_button = $UI/PauseOverlay/Fx
@onready var audio_button = $UI/PauseOverlay/Audio
@onready var title_button = $UI/PauseOverlay/Title
@onready var title_label = $UI/StartOverlay/Title
@onready var sub_label = $UI/StartOverlay/Sub
@onready var controller_hint = $UI/StartOverlay/ControllerHint
@onready var mobile_controls = $UI/MobileControls
@onready var audio_engine = $DynamicAudio

var rng := RandomNumberGenerator.new()
var accumulator := 0.0
var frame_count := 0
var started := false
var game_over := false
var paused_game := false
var active_joypad := -1
var fx_mode := 0
var audio_mode := 0
var pause_latch := false
var score := 0
var lives := 3
var next_bonus := 15000
var centin := 12
var centis := 2
var wave_serial := 1
var formation_wait := 0
var first_formation := true
var raid_mode := false
var raid_source := 0
var raid_remaining := 0
var raid_value := 0
var slow_ticks := 0
var side_feed_active := false
var side_feed_base := 0xC0
var side_feed_count := 0xC0
var beetle_allowance_left := 1
var next_group_id := 10
var fire_requested := false
var touch_dragging := false
var touch_id := -1
var mobile_mode := false
var mobile_move := Vector2.ZERO
var mobile_fire_held := false
var player := Vector2(120, 240)
var player_target := Vector2(120, 240)
var player_inv := 0
var player_trail := []
var fx_impact := 0.0
var shake := 0.0
var flash := 0.0
var attract_clock := 0.0
var attract_accumulator := 0.0
var attract_message_index := -1
var attract_burst_step := -1

var mushrooms := []
var ddts := []
var segments := []
var bullets := []
var bugs := []
var particles := []
var rings := []
var ddt_blasts := []
var conway_active := false
var conway_phase := 0
var conway_phase_ticks := 0
var conway_events := []

func _ready():
    rng.randomize()
    start_button.pressed.connect(start_game)
    fire_button.pressed.connect(request_fire)
    pause_touch.pressed.connect(toggle_pause)
    resume_button.pressed.connect(resume_game)
    restart_button.pressed.connect(restart_game)
    fx_button.pressed.connect(cycle_fx_mode)
    audio_button.pressed.connect(cycle_audio_mode)
    title_button.pressed.connect(quit_to_title)
    mobile_controls.move_changed.connect(_on_mobile_move)
    mobile_controls.fire_changed.connect(_on_mobile_fire)
    mobile_controls.pause_pressed.connect(_on_mobile_pause)
    mobile_controls.drag_target.connect(_on_mobile_drag)
    mobile_mode = OS.has_feature("mobile") or DisplayServer.is_touchscreen_available() or OS.get_cmdline_user_args().has("--mobile-preview")
    mobile_controls.set_controls_enabled(false)
    fire_button.visible = false if mobile_mode else fire_button.visible
    pause_touch.visible = false
    if not Input.get_connected_joypads().is_empty():
        active_joypad = Input.get_connected_joypads()[0]
    init_attract()
    apply_fx_mode()
    update_ui()
    start_button.grab_focus()
    if OS.get_cmdline_user_args().has("--autostart"):
        start_game()
    if OS.get_cmdline_user_args().has("--audio-smoke") and is_instance_valid(audio_engine):
        audio_engine.trigger("raid",1.0,-0.4,1.0)
        audio_engine.trigger("ddt",0.8,0.4,0.9)
        audio_engine.trigger("bonus",0.75,0.0,1.0)
    queue_redraw()

func init_attract():
    attract_clock = 0.0
    attract_accumulator = 0.0
    attract_message_index = -1
    attract_burst_step = -1
    score = 0
    lives = 3
    centin = 12
    centis = 2
    frame_count = 0
    next_group_id = 10
    player = Vector2(120, 239)
    player_target = player
    player_inv = 999999
    bullets.clear()
    segments.clear()
    bugs.clear()
    particles.clear()
    rings.clear()
    ddt_blasts.clear()
    conway_active = false
    conway_phase = 0
    conway_phase_ticks = 0
    conway_events.clear()
    seed_field()
    spawn_formation()
    spawn_bug("spider", false)
    spawn_bug("dragon", false)
    spawn_bug("bee", false)
    title_label.text = "NEON MILLIPEDE"
    start_button.text = "START"
    start_overlay.visible = true
    pause_touch.visible = false
    start_button.grab_focus()
    update_attract_text(true)

func update_attract_text(force := false):
    var messages := [
        "1982 RULES • 2026 VISUAL DAMAGE\nREAL 30×32 PLAYFIELD • REAL SOURCE-DERIVED BEHAVIOR",
        "TUNNEL • EYE • STORM • FRACTAL REACTOR\nCRT • BLOOM • PHOSPHOR • RGB SPLIT • SIGNAL TEARS",
        "CONTROLLER-FIRST • FULL RUMBLE\nLEFT STICK / D-PAD MOVE   •   A / X / RT FIRE",
        "MILLIPEDE • SPIDER • BEE • DRAGONFLY • MOSQUITO\nEARWIG • INCHWORM • BEETLE • DDT CHAIN REACTIONS"
    ]
    var idx := int(floor(attract_clock / 4.0)) % messages.size()
    if force or idx != attract_message_index:
        attract_message_index = idx
        sub_label.text = messages[idx]
    controller_hint.text = "CONTROLLER: START / A   •   TOUCH: TAP START
MOBILE IN-GAME: LEFT STICK + DRAG • HOLD FIRE • PAUSE"

func attract_tick():
    frame_count += 1
    var auto_x := 120.0 + sin(attract_clock * 1.18) * 82.0 + sin(attract_clock * 2.4) * 13.0
    var auto_y := 235.0 + sin(attract_clock * 0.73) * 9.0
    player_target = Vector2(clamp(auto_x, 12.0, 228.0), clamp(auto_y, 214.0, 246.0))
    move_player()

    if frame_count % 10 == 0:
        fire_requested = true
    fire_logic()
    update_bullets()

    if (frame_count & 1) == 0:
        update_segments()
        update_bugs()

    if segments.size() < 4:
        centin = 12
        centis = 2
        spawn_formation()

    if not has_bug("spider") and frame_count % 120 == 0:
        spawn_bug("spider", false)
    if not has_bug("dragon") and frame_count % 150 == 0:
        spawn_bug("dragon", false)
    if not has_bug("bee") and frame_count % 180 == 0:
        spawn_bug("bee", false)
    if not has_bug("mosquito") and frame_count % 240 == 0:
        spawn_bug("mosquito", false)

func update_attract_visuals(delta: float):
    attract_clock += delta
    update_attract_text()
    var pulse := 1.0 + 0.035 * sin(attract_clock * 2.4)
    title_label.scale = Vector2(pulse, pulse)
    title_label.pivot_offset = title_label.size * 0.5
    title_label.rotation = sin(attract_clock * 0.55) * 0.008
    title_label.modulate = Color.from_hsv(fposmod(attract_clock * 0.035, 1.0), 0.35, 1.0)
    start_button.modulate = Color(1.0, 1.0, 1.0, 0.76 + 0.24 * sin(attract_clock * 3.0))
    controller_hint.modulate = Color(0.72, 0.84, 1.0, 0.62 + 0.30 * sin(attract_clock * 1.7))
    start_overlay.color = Color(0.004, 0.004, 0.018, 0.48 + 0.07 * sin(attract_clock * 0.43))

    attract_accumulator += delta
    var guard := 0
    while attract_accumulator >= SOURCE_DT and guard < 5:
        attract_accumulator -= SOURCE_DT
        attract_tick()
        guard += 1

    var burst_step := int(floor(attract_clock / 3.25))
    if burst_step != attract_burst_step:
        attract_burst_step = burst_step
        var blast_p := Vector2(rng.randf_range(32.0,208.0), rng.randf_range(58.0,196.0))
        kill_fx(blast_p, true)
        fx_impact = max(fx_impact, 0.72)

func start_game():
    score = 0
    lives = 3
    next_bonus = 15000
    centin = 12
    centis = 2
    wave_serial = 1
    formation_wait = 0
    first_formation = true
    raid_mode = false
    slow_ticks = 0
    side_feed_active = false
    side_feed_base = 0xC0
    side_feed_count = side_feed_base
    frame_count = 0
    accumulator = 0.0
    next_group_id = 10
    player = Vector2(120, 240)
    player_target = player
    player_inv = 90
    player_trail.clear()
    bullets.clear()
    segments.clear()
    bugs.clear()
    particles.clear()
    rings.clear()
    ddt_blasts.clear()
    conway_active = false
    conway_phase = 0
    conway_phase_ticks = 0
    conway_events.clear()
    seed_field()
    spawn_formation()
    started = true
    game_over = false
    paused_game = false
    pause_overlay.visible = false
    start_overlay.visible = false
    mobile_controls.set_controls_enabled(mobile_mode)
    fire_button.visible = not mobile_mode
    pause_touch.visible = false
    title_label.scale = Vector2.ONE
    title_label.rotation = 0.0
    title_label.modulate = Color.WHITE
    start_button.modulate = Color.WHITE
    update_ui()
    if is_instance_valid(audio_engine):
        audio_engine.trigger("start",1.0,0.0,1.0)
    rumble(0.18, 0.34, 0.16)

func toggle_pause():
    if not started:
        return
    if paused_game:
        resume_game()
    else:
        paused_game = true
        pause_overlay.visible = true
        mobile_controls.set_controls_enabled(false)
        mobile_move = Vector2.ZERO
        mobile_fire_held = false
        fire_button.visible = false
        pause_touch.visible = false
        resume_button.grab_focus()
        if is_instance_valid(audio_engine):
            audio_engine.trigger("pause",0.55,0.0,1.0)
        rumble(0.10, 0.18, 0.10)

func resume_game():
    if not started:
        return
    paused_game = false
    pause_overlay.visible = false
    mobile_controls.set_controls_enabled(mobile_mode)
    fire_button.visible = not mobile_mode
    pause_touch.visible = false
    accumulator = 0.0
    if is_instance_valid(audio_engine):
        audio_engine.trigger("resume",0.55,0.0,1.0)
    rumble(0.08, 0.12, 0.08)

func restart_game():
    pause_overlay.visible = false
    start_game()

func quit_to_title():
    started = false
    paused_game = false
    game_over = false
    pause_overlay.visible = false
    mobile_controls.set_controls_enabled(false)
    mobile_move = Vector2.ZERO
    mobile_fire_held = false
    fire_button.visible = false
    init_attract()
    queue_redraw()

func cycle_fx_mode():
    fx_mode = (fx_mode + 1) % 3
    apply_fx_mode()
    fx_button.grab_focus()

func cycle_audio_mode():
    audio_mode = (audio_mode + 1) % 3
    var label := "FULL"
    if audio_mode == 1:
        label = "SFX FOCUS"
    elif audio_mode == 2:
        label = "MUTE"
    audio_button.text = "AUDIO: %s" % label
    if is_instance_valid(audio_engine):
        audio_engine.set_audio_mode(audio_mode)
        audio_engine.trigger("resume",0.38,0.0,1.0)
    audio_button.grab_focus()

func apply_fx_mode():
    var amount := 1.0
    var label := "MAXIMUM"
    if fx_mode == 1:
        amount = 1.38
        label = "OVERDRIVE"
    elif fx_mode == 2:
        amount = 0.42
        label = "CLEANER"
    fx_button.text = "FX: %s" % label if is_instance_valid(fx_button) else "FX"
    if is_instance_valid(post_fx) and post_fx.material is ShaderMaterial:
        post_fx.material.set_shader_parameter("fx_amount", amount)

func rumble(weak: float, strong: float, duration: float):
    var device := active_joypad
    if device < 0 and not Input.get_connected_joypads().is_empty():
        device = Input.get_connected_joypads()[0]
    if device >= 0:
        Input.start_joy_vibration(device, weak, strong, duration)

func audio_pan_for(p: Vector2) -> float:
    return clampf((p.x / LW) * 2.0 - 1.0, -1.0, 1.0)

func update_audio_state():
    if not is_instance_valid(audio_engine):
        return
    audio_engine.set_game_state(score, lives, centin, raid_mode, side_feed_active, slow_ticks, ddt_blasts.size(), bugs.size(), segments.size(), started, paused_game, game_over, not started and not game_over, fx_impact)

func request_fire():
    fire_requested = true
    if not started:
        start_game()

func _process(delta):
    fx_impact = max(0.0, fx_impact - delta * 0.75)
    shake = max(0.0, shake - delta * 20.0)
    flash = max(0.0, flash - delta * 2.7)
    update_audio_state()

    var drive := clampf(float(score) / 350000.0, 0.0, 1.0)
    if bg.material is ShaderMaterial:
        bg.material.set_shader_parameter("impact", fx_impact)
        bg.material.set_shader_parameter("scene_speed", 1.0 + drive * 0.75 + fx_impact * 0.75)
    if post_fx.material is ShaderMaterial:
        post_fx.material.set_shader_parameter("impact", fx_impact)
        post_fx.material.set_shader_parameter("overdrive", drive)
        post_fx.material.set_shader_parameter("paused_mix", 1.0 if paused_game else 0.0)

    update_particles(delta)

    if Input.is_action_just_pressed("pause_game"):
        if started:
            toggle_pause()
        else:
            start_game()
        queue_redraw()
        return

    if not started:
        if not game_over:
            update_attract_visuals(delta)
        else:
            var pulse := 1.0 + 0.025 * sin(Time.get_ticks_msec() * 0.004)
            title_label.scale = Vector2(pulse,pulse)
            title_label.pivot_offset = title_label.size * 0.5
        if Input.is_action_just_pressed("fire") or Input.is_action_just_pressed("ui_accept"):
            start_game()
        queue_redraw()
        return

    if paused_game:
        if Input.is_action_just_pressed("restart_run"):
            restart_game()
        elif Input.is_action_just_pressed("ui_cancel"):
            resume_game()
        queue_redraw()
        return

    accumulator += delta
    var guard := 0
    while accumulator >= SOURCE_DT and guard < 5:
        accumulator -= SOURCE_DT
        logic_tick()
        guard += 1
    queue_redraw()

func logic_tick():
    frame_count += 1
    if player_inv > 0:
        player_inv -= 1
    if slow_ticks > 0:
        slow_ticks -= 1

    read_controls()
    move_player()
    fire_logic()
    update_bullets()
    update_ddt_clouds()
    update_conway()

    # Source slowdown skips moving critters on alternating frames.
    var skip_motion := slow_ticks > 0 and (frame_count & 1) == 1
    if not skip_motion and not conway_active:
        update_segments()
        update_bugs()
        spawn_normal_bugs()
        update_side_feed()
        check_ddt_cloud_collisions()

    if formation_wait > 0 and not conway_active:
        formation_wait -= 1
        if formation_wait == 0:
            if lives > 0:
                spawn_formation()
            else:
                end_game()

    check_player_collisions()
    update_ui()

func read_controls():
    var move := Input.get_vector("move_left", "move_right", "move_up", "move_down", 0.16)
    if mobile_move.length() > move.length():
        move = mobile_move
    if move.length() > 0.05:
        # Analog magnitude is preserved so mobile stick and gamepad both retain fine control.
        player_target = player + move * (2.2 + 2.2 * move.length())

    if Input.is_action_pressed("fire") or mobile_fire_held:
        fire_requested = true

func joy_fire() -> bool:
    return Input.is_action_pressed("fire")

func move_player():
    var desired := player.move_toward(player_target, 2.3)
    desired.x = clamp(desired.x, 4.0, 236.0)
    desired.y = clamp(desired.y, PLAYER_TOP + 4.0, 248.0)

    var px := Vector2(desired.x, player.y)
    if not player_blocked(px):
        player.x = px.x
    var py := Vector2(player.x, desired.y)
    if not player_blocked(py):
        player.y = py.y

    player_trail.push_front({"p": player, "life": 0.22})
    if player_trail.size() > 10:
        player_trail.pop_back()

func player_blocked(p: Vector2) -> bool:
    for m in mushrooms:
        if p.distance_to(cell_center(m["col"], m["row"])) < 6.2:
            return true
    for d in ddts:
        if p.distance_to(cell_center(d["col"], d["row"])) < 7.0:
            return true
    return false

func fire_logic():
    if fire_requested and bullets.is_empty():
        bullets.append({"p": player + Vector2(0,-6), "trail": []})
        fire_requested = false
        small_fx(player + Vector2(0,-7), 0.52)
        if is_instance_valid(audio_engine):
            audio_engine.trigger("shot",0.72,audio_pan_for(player),1.0)
    elif fire_requested:
        fire_requested = false

func update_bullets():
    for i in range(bullets.size()-1, -1, -1):
        var b = bullets[i]
        b["trail"].push_front(b["p"])
        if b["trail"].size() > 8:
            b["trail"].pop_back()
        var bp: Vector2 = b["p"]
        bp.y -= 7.0
        b["p"] = bp
        if bp.y < 0:
            bullets.remove_at(i)
            continue
        if bullet_hits_ddt(i):
            continue
        if bullet_hits_mushroom(i):
            continue
        if bullet_hits_segment(i):
            continue
        if bullet_hits_bug(i):
            continue

func bullet_hits_mushroom(bi: int) -> bool:
    if bi >= bullets.size(): return false
    var p: Vector2 = bullets[bi]["p"]
    for mi in range(mushrooms.size()-1, -1, -1):
        var m = mushrooms[mi]
        var mp := cell_center(m["col"], m["row"])
        if abs(p.x-mp.x) < 4.2 and abs(p.y-mp.y) < 5.0:
            if not m["flower"]:
                m["hp"] -= 1
                small_fx(mp, 0.32)
                if is_instance_valid(audio_engine):
                    audio_engine.trigger("hit",0.34,audio_pan_for(mp),0.82 + float(m["hp"]) * 0.08)
                if m["hp"] <= 0:
                    add_score(1)
                    mushrooms.remove_at(mi)
                    kill_fx(mp, false)
            bullets.remove_at(bi)
            return true
    return false

func bullet_hits_ddt(bi: int) -> bool:
    if bi >= bullets.size(): return false
    var p: Vector2 = bullets[bi]["p"]
    for di in range(ddts.size()-1, -1, -1):
        var d = ddts[di]
        var dp := cell_center(d["col"], d["row"])
        if p.distance_to(dp) < 7.5:
            ddts.remove_at(di)
            bullets.remove_at(bi)
            explode_ddt(dp)
            return true
    return false

func shot_half_width(kind: String) -> float:
    # SHOOT table 99$: half-widths by original object picture class.
    match kind:
        "mosquito": return 8.0
        "inchworm", "spider", "earwig", "dragon": return 10.0
        "bee", "beetle": return 6.0
    return 6.0

func shot_hits_object(shot: Vector2, obj: Vector2, half_width: float) -> bool:
    return absf(shot.y - obj.y) < 6.0 and absf(shot.x - obj.x) < half_width

func bullet_hits_segment(bi: int) -> bool:
    if bi >= bullets.size(): return false
    var p: Vector2 = bullets[bi]["p"]
    for si in range(segments.size()-1, -1, -1):
        var s = segments[si]
        if shot_hits_object(p, s["p"], 6.0):
            bullets.remove_at(bi)
            kill_segment(si, false)
            return true
    return false

func bullet_hits_bug(bi: int) -> bool:
    if bi >= bullets.size(): return false
    var p: Vector2 = bullets[bi]["p"]
    for ei in range(bugs.size()-1, -1, -1):
        var e = bugs[ei]
        if shot_hits_object(p, e["p"], shot_half_width(e["kind"])):
            bullets.remove_at(bi)
            if e["kind"] == "bee" and e.get("hp",2) > 1:
                e["hp"] = 1
                e["speed"] = 4.0
                small_fx(e["p"], 0.55)
                if is_instance_valid(audio_engine):
                    audio_engine.trigger("hit",0.58,audio_pan_for(e["p"]),1.45)
            else:
                kill_bug(ei, false)
            return true
    return false

func seed_field():
    mushrooms.clear()
    ddts.clear()

    # Exact upright DDTST address mapping from the Atari source.  PLYFLD is
    # column-major in 32-byte columns with the video origin at lower-left;
    # our draw grid is top-left, hence Godot row = 31 - source_row.
    for c in DDT_CELLS:
        ddts.append({"col": c.x, "row": c.y})

    # Atari INITSC: A=$1D (source row 29), Y=$02 (source row 2), X=55.
    # INIT3 does 55 *attempts*, cycling 29 -> 2 -> 29.  The random address can
    # select hardware columns 30/31, which are rejected and consume an attempt
    # without advancing the row.  MUSHER also refuses occupied cells, but a
    # valid-column attempt still advances the row even if nothing was placed.
    var source_row := 0x1D
    for attempt in range(55):
        # Mirrors (RND0 & $E0) + (RND0 & $03) as a 5-bit hardware column.
        var col_low := rng.randi_range(0,7)
        var col_bank := rng.randi_range(0,3)
        var col := col_bank * 8 + col_low

        # Columns 30 and 31 are the two off-screen addresses rejected by INIT3.
        if col >= COLS:
            continue

        var row := 31 - source_row
        if not occupied_cell(col,row):
            mushrooms.append(make_mush(col,row))

        source_row -= 1
        if source_row < 2:
            source_row = 0x1D

func make_mush(col: int, row: int, poison := false, flower := false):
    return {"col": col, "row": row, "hp": 4, "poison": poison, "flower": flower, "phase": rng.randf_range(0.0,TAU)}

func cell_center(col: int, row: int) -> Vector2:
    return Vector2(col*CELL + 4.0, row*CELL + 4.0)

func cell_of(p: Vector2) -> Vector2i:
    return Vector2i(clamp(int(floor(p.x/CELL)),0,29), clamp(int(floor(p.y/CELL)),0,31))

func find_mush(col: int, row: int) -> int:
    for i in range(mushrooms.size()):
        if mushrooms[i]["col"] == col and mushrooms[i]["row"] == row:
            return i
    return -1

func occupied_cell(col: int, row: int) -> bool:
    if find_mush(col,row) >= 0: return true
    for d in ddts:
        if d["col"] == col and d["row"] == row: return true
    return false

func add_mush_at(p: Vector2, poison := false):
    var c := cell_of(p)
    if not occupied_cell(c.x,c.y):
        mushrooms.append(make_mush(c.x,c.y,poison,false))

func formation_main_len() -> int:
    if centin != 12 or score < 100000:
        return centin
    # CENTPC reserves more of the 12 motion-object entries for spiders on the
    # full-length wave once SCORE2 reaches $10 (100K).
    var raw := source_score2_bcd() - 0x10
    if raw < 0:
        return centin
    var spider_slots := raw >> 1
    if spider_slots >= 8:
        spider_slots = 5
    spider_slots += 3
    return clampi(14 - spider_slots, 1, 12)

func spider_limit() -> int:
    var limit := 1
    var s2 := source_score2_bcd()
    if score >= 30000:
        var gate := ((0xB0 - s2) & 0xFF) >> 4
        if gate < centin:
            limit = 2
    if centin == 12 and score >= 100000:
        var raw := s2 - 0x10
        if raw >= 0:
            var n := raw >> 1
            if n >= 8:
                n = 5
            limit = clampi(n + 3, 3, 8)
    return limit

func spawn_formation():
    if raid_mode:
        return
    segments.clear()
    bullets.clear()
    side_feed_active = false
    side_feed_count = side_feed_base
    beetle_allowance_left = beetle_wave_allowance()
    var direction := -1 if rng.randi() & 1 else 1
    var main_len := formation_main_len()
    var start_x := 120.0
    var y := 4.0
    for i in range(main_len):
        var x := start_x - direction * i * 8.0
        segments.append(make_segment(Vector2(x,y), direction, i==0, 0, i, centis))
    # Short CENTIN waves fill unused entries with independent heads.  The
    # high-score full-wave reduction is different: those entries are reserved
    # for spiders, not converted to heads.
    var extras := (12 - centin) if centin < 12 else 0
    for e in range(extras):
        var d := -1 if rng.randi() & 1 else 1
        var x := float(rng.randi_range(2,27)*8+4)
        segments.append(make_segment(Vector2(x,4), d, true, next_group_id, 0, 2))
        next_group_id += 1
    first_formation = false
    wave_serial += 1
    if started and not game_over and is_instance_valid(audio_engine):
        audio_engine.trigger("wave",0.48,0.0,0.9 + float(12-centin) * 0.025)

func make_segment(p: Vector2, dx: int, head: bool, group: int, order: int, speed: int):
    return {"p": p, "dx": dx, "vdir": 1, "drop": 0.0, "head": head, "group": group, "order": order, "speed": speed, "poison": false, "in_player": false, "phase": rng.randf_range(0.0,TAU)}

func update_segments():
    if segments.is_empty() or raid_mode:
        return
    for s in segments:
        move_segment(s)
    if segments.is_empty() and formation_wait == 0:
        formation_cleared()

func move_segment(s):
    var p: Vector2 = s["p"]
    var speed := float(s["speed"])
    if s["poison"]:
        p.y += speed
        if p.y >= 244.0:
            p.y = 244.0
            s["poison"] = false
            s["in_player"] = true
            s["vdir"] = -1
            s["dx"] = -int(s["dx"])
            if s["head"]:
                side_feed_active = true
        s["p"] = p
        return

    if float(s["drop"]) > 0.0:
        var step: float = minf(speed, float(s["drop"]))
        p.y += float(s["vdir"]) * step
        s["drop"] = float(s["drop"]) - step
        if float(s["drop"]) <= 0.001:
            s["dx"] = -int(s["dx"])
            if p.y >= PLAYER_TOP:
                s["in_player"] = true
            if p.y >= 244.0:
                p.y = 244.0
                s["vdir"] = -1
                if s["head"]:
                    side_feed_active = true
            elif s["in_player"] and p.y <= PLAYER_TOP + 4.0:
                p.y = PLAYER_TOP + 4.0
                s["vdir"] = 1
        s["p"] = p
        return

    var at_center: bool = absf(fposmod(p.x-4.0,8.0)) < speed + 0.1
    if at_center:
        var c := cell_of(p)
        var next_col := c.x + int(s["dx"])
        var edge := next_col < 0 or next_col >= COLS
        var obst := false
        var poison_obst := false
        if not edge:
            var mi := find_mush(next_col,c.y)
            if mi >= 0:
                obst = true
                poison_obst = mushrooms[mi]["poison"]
            else:
                for d in ddts:
                    if d["col"] == next_col and d["row"] == c.y:
                        obst = true
                        break
        if poison_obst and s["head"]:
            s["poison"] = true
            s["p"] = p
            return
        if edge or obst:
            s["drop"] = 8.0
            s["p"] = p
            return

    p.x += float(s["dx"]) * speed
    p.x = clamp(p.x, 4.0,236.0)
    s["p"] = p

func kill_segment(si: int, by_ddt: bool):
    if si < 0 or si >= segments.size(): return
    var victim = segments[si]
    var p: Vector2 = victim["p"]
    add_score((100 if victim["head"] else 10) * (3 if by_ddt else 1))
    add_mush_at(p)
    var group := int(victim["group"])
    var order := int(victim["order"])
    segments.remove_at(si)

    # Split the trailing section into a new independently moving chain/head.
    var trailing := []
    for s in segments:
        if int(s["group"]) == group and int(s["order"]) > order:
            trailing.append(s)
    if trailing.size() > 0:
        var new_group := next_group_id
        next_group_id += 1
        var first_tail = null
        var first_order := 999
        for tail in trailing:
            var old_order := int(tail["order"])
            tail["group"] = new_group
            tail["order"] = old_order - order - 1
            if old_order < first_order:
                first_order = old_order
                first_tail = tail
        if first_tail != null:
            first_tail["head"] = true
            first_tail["dx"] = -int(first_tail["dx"])

    if is_instance_valid(audio_engine):
        audio_engine.trigger("head" if victim["head"] else "kill",0.78 if victim["head"] else 0.42,audio_pan_for(p),1.18 if victim["head"] else 0.92)
    kill_fx(p, by_ddt)
    if segments.is_empty() and not raid_mode and formation_wait == 0:
        formation_cleared()

func formation_cleared():
    if raid_mode: return
    # Source increments CENTIS after a clear. A slow pass becomes fast without
    # changing CENTIN; clearing the fast pass triggers raid/Conway/next CENTIN.
    if centis == 1:
        centis = 2
        formation_wait = 24
        return

    if centin == 9:
        conway_pass()
        return
    if RAID_LEVELS.has(centin):
        begin_raid(centin)
        return

    advance_centin()

func advance_centin():
    scroll_field_down()
    centin -= 1
    if centin <= 0:
        centin = 12
    centis = 2 if score >= 20000 else 1
    formation_wait = 28

func source_score2_bcd() -> int:
    # SCORE2 in the 6502 code is BCD and counts 10,000-point steps.
    var n10k := clampi(int(score / 10000), 0, 99)
    return ((n10k / 10) << 4) | (n10k % 10)

func begin_raid(source: int):
    raid_mode = true
    raid_source = source
    raid_remaining = 20 + (source_score2_bcd() >> 1)
    raid_value = 0
    segments.clear()
    formation_wait = 0
    if is_instance_valid(audio_engine):
        audio_engine.trigger("raid",1.15,0.0,1.0 + float(12-source) * 0.02)

func finish_raid():
    raid_mode = false
    raid_remaining = 0
    bugs.clear()
    advance_centin()

func raid_kind() -> String:
    # Atari BOMBS table, decoded literally for the five raid CENTIN values:
    # 11 = bees; 7 = dragonflies; 5 = mosquitoes;
    # 3 = 50/50 bee/dragonfly; 1 = 25% bee, 50% dragonfly, 25% mosquito.
    if raid_source == 11:
        return "bee"
    if raid_source == 7:
        return "dragon"
    if raid_source == 5:
        return "mosquito"
    if raid_source == 3:
        return "bee" if (rng.randi() & 1) == 0 else "dragon"
    var r := rng.randi() & 3
    if r == 0:
        return "bee"
    if r == 3:
        return "mosquito"
    return "dragon"

func update_side_feed():
    if not side_feed_active or raid_mode: return
    side_feed_count -= 1
    if side_feed_count > 0: return
    if side_feed_base >= 0x60:
        side_feed_base -= 8
    side_feed_count = side_feed_base
    var from_left := (rng.randi() & 1) == 0
    var x := 4.0 if from_left else 236.0
    var dx := 1 if from_left else -1
    segments.append(make_segment(Vector2(x,192), dx, true, next_group_id, 0, 2))
    segments[-1]["in_player"] = false
    next_group_id += 1

func beetle_wave_allowance() -> int:
    if score < 70000:
        return 1
    if score < 140000:
        return 2
    if score < 210000:
        return 3
    if score < 500000:
        return 4
    if score < 700000:
        return 6
    return 255

func spawn_normal_bugs():
    if raid_mode:
        var live_raiders := 0
        for e in bugs:
            if bool(e.get("raid",false)):
                live_raiders += 1
        if raid_remaining > 0 and live_raiders < 13 and (rng.randi() & 7) == 0:
            spawn_bug(raid_kind(), true)
            raid_remaining -= 1
        elif raid_remaining <= 0 and bugs.is_empty():
            finish_raid()
        return

    var shared_busy := not shared_slot_free()
    var score10k := int(score/10000)

    if not shared_busy and centin < 9:
        var cadence := 120 if score >= 70000 else 240
        if frame_count % cadence == 23:
            spawn_bug("mosquito", false)
            shared_busy = true

    if not shared_busy and centin < 11 and frame_count % 256 == 0 and (rng.randi() & 3) == 0:
        spawn_bug("earwig", false)
        shared_busy = true

    if not shared_busy and centin < 10 and frame_count % 128 == 41 and rng.randf() < 0.38:
        spawn_bug("dragon", false)
        shared_busy = true

    if not shared_busy and bottom_mush_count() < bee_threshold() and frame_count % 90 == 11:
        spawn_bug("bee", false)

    # Source WRMMV checks a particular FRAME phase every ~1024 frames.
    if centin < 11 and not has_bug("inchworm") and frame_count % 1024 == 0x13:
        spawn_bug("inchworm", false)

    var beetle_cadence := 60 if score >= 600000 else 120
    if centin < 12 and not side_feed_active and beetle_allowance_left > 0 and frame_count % beetle_cadence == 0x37 % beetle_cadence:
        if count_bug("beetle") < beetle_concurrent_limit():
            spawn_bug("beetle", false)
            beetle_allowance_left -= 1

    # Spider base re-entry delay ~0x60 frames.
    if count_bug("spider") < spider_limit() and frame_count % 96 == 0:
        spawn_bug("spider", false)

func shared_slot_free() -> bool:
    for e in bugs:
        if ["bee","dragon","mosquito","earwig"].has(e["kind"]):
            return false
    return true

func has_bug(kind: String) -> bool:
    for e in bugs:
        if e["kind"] == kind: return true
    return false

func count_bug(kind: String) -> int:
    var n := 0
    for e in bugs:
        if e["kind"] == kind: n += 1
    return n

func beetle_concurrent_limit() -> int:
    if score < 90000: return 1
    if score < 250000: return 2
    return 3

func bee_threshold() -> int:
    var s2 := source_score2_bcd()
    if s2 < 0x02:
        return 5
    if s2 < 0x12:
        return 9
    return mini(0x2F, (s2 >> 1) + 6)

func bottom_mush_count() -> int:
    var n := 0
    for m in mushrooms:
        if m["row"] >= 20: n += 1
    return n

func spawn_bug(kind: String, raid: bool):
    var e := {"kind":kind,"p":Vector2.ZERO,"v":Vector2.ZERO,"phase":rng.randf_range(0.0,TAU),"raid":raid,"hp":1,"speed":1.0,"state":0,"timer":0}
    if kind == "bee":
        e["p"] = Vector2(rng.randf_range(12,228),4)
        e["speed"] = 3.0 if score >= 60000 or raid else 2.0
        e["hp"] = 2
    elif kind == "dragon":
        e["p"] = Vector2(rng.randf_range(12,228),4)
        e["speed"] = 3.0 if score >= 150000 else (2.0 if score >= 50000 or raid else 1.0)
    elif kind == "mosquito":
        e["p"] = Vector2(rng.randf_range(12,228),4)
        var sp := 3.0 if score >= 90000 or raid else 2.0
        e["v"] = Vector2(sp if rng.randf()<0.5 else -sp, sp)
        e["speed"] = sp
    elif kind == "earwig":
        var fast := score >= 20000 and rng.randf() > 0.25
        var sp := 2.0 if fast else 1.0
        var left := rng.randf() < 0.5
        e["p"] = Vector2(4 if left else 236, rng.randf_range(64,132))
        e["v"] = Vector2(sp if left else -sp,0)
    elif kind == "inchworm":
        var sp := 2.0 if score >= 80000 else 1.0
        var left := rng.randf() < 0.5
        e["p"] = Vector2(4 if left else 236, rng.randf_range(128,184))
        e["v"] = Vector2(sp if left else -sp,0)
    elif kind == "beetle":
        var sp := 2.0 if score >= 400000 else 1.0
        var left := rng.randf() < 0.5
        e["p"] = Vector2(4 if left else 236,192)
        e["v"] = Vector2(sp if left else -sp,0)
        e["state"] = 0
        e["timer"] = 12
    elif kind == "spider":
        var sp := 2.0 if score >= 10000 else 1.0
        var left := rng.randf() < 0.5
        e["p"] = Vector2(4 if left else 236, rng.randf_range(216,244))
        e["v"] = Vector2(sp if left else -sp, sp if rng.randf()<0.5 else -sp)
        e["timer"] = 0x0C if (rng.randi() & 0x20) == 0 else 0x2C
        e["old_h"] = e["v"].x
    bugs.append(e)

func update_bugs():
    for i in range(bugs.size()-1, -1, -1):
        var e = bugs[i]
        var k: String = e["kind"]
        if k == "bee":
            var ep: Vector2 = e["p"]
            ep.y += float(e["speed"])
            e["p"] = ep
            maybe_drop_mush(e,3)
        elif k == "dragon":
            e["phase"] += 0.22
            var ep: Vector2 = e["p"]
            ep.x += sin(float(e["phase"])) * (1.6 + float(e["speed"])*0.25)
            ep.y += float(e["speed"])
            e["p"] = ep
            maybe_drop_mush(e,1 if ep.y < PLAYER_TOP else 7)
        elif k == "mosquito":
            var ep: Vector2 = e["p"] + e["v"]
            var ev: Vector2 = e["v"]
            if ep.x <= 4 or ep.x >= 236:
                ev.x *= -1
                ep.x = clamp(ep.x,4.0,236.0)
            e["p"] = ep
            e["v"] = ev
        elif k == "earwig":
            e["p"] += e["v"]
            poison_mush_at(e["p"])
        elif k == "inchworm":
            e["p"] += e["v"]
        elif k == "beetle":
            move_beetle(e)
            flower_mush_at(e["p"])
        elif k == "spider":
            move_spider(e)
            spider_eat(e["p"])

        if offscreen_bug(e):
            bugs.remove_at(i)
            continue

    if raid_mode and raid_remaining <= 0 and bugs.is_empty():
        finish_raid()

func maybe_drop_mush(e, mask: int):
    if e["raid"]: return
    if (frame_count & 3) != 0: return
    if (rng.randi() & mask) != 0: return
    add_mush_at(e["p"] + Vector2(0,5))

func move_beetle(e):
    # BEETL1 state shape: enter horizontally, dive to the lower edge, travel
    # a long horizontal run, climb, then leave horizontally.  Timers use the
    # same masks/ranges as the source instead of free-form random durations.
    e["timer"] -= 1
    e["p"] += e["v"]
    if e["timer"] > 0:
        return
    var sp := float(e["speed"])
    var state := int(e["state"])
    if state == 0:
        e["v"] = Vector2(0.0, sp)
        e["timer"] = 0x40
        e["state"] = 1
    elif state == 1:
        var h := sp if rng.randf() < 0.5 else -sp
        e["v"] = Vector2(h,0.0)
        e["timer"] = (rng.randi() & 0x78) + 0x60
        e["state"] = 2
    elif state == 2:
        e["v"] = Vector2(0.0,-sp)
        e["timer"] = (rng.randi() & 0x38) + 0x40
        e["state"] = 3
    else:
        var h := sp if e["p"].x < 120.0 else -sp
        e["v"] = Vector2(h,0.0)
        e["timer"] = 0xFF

func move_spider(e):
    e["timer"] -= 1
    var ep: Vector2 = e["p"]
    var ev: Vector2 = e["v"]
    if e["timer"] <= 0:
        # Source toggles horizontal motion about half the time, retaining the
        # previous direction when it toggles back on.  Easy vertical reversal
        # probability is 1/2 and the next change delay is $30 (48 frames).
        if (rng.randi() & 0x80) == 0:
            if absf(ev.x) > 0.1:
                e["old_h"] = ev.x
                ev.x = 0.0
            else:
                var old_h := float(e.get("old_h", 1.0))
                if absf(old_h) < 0.1:
                    old_h = 1.0 if rng.randf() < 0.5 else -1.0
                ev.x = old_h
        if (rng.randi() & 0x20) != 0:
            ev.y *= -1.0
        e["timer"] = 0x30

    ep += ev
    if ep.x <= 2.0 or ep.x >= 238.0:
        if absf(ev.x) < 0.1:
            ev.x = -float(e.get("old_h", 1.0))
        else:
            ev.x *= -1.0
        e["old_h"] = ev.x
        ep.x = clampf(ep.x,2.0,238.0)

    var top := spider_top_limit()
    if ep.y <= top or ep.y >= 250.0:
        ev.y *= -1.0
        ep.y = clampf(ep.y,top,250.0)

    e["p"] = ep
    e["v"] = ev

func spider_top_limit() -> float:
    var n10k := int(score / 10000)
    var step := 0
    if n10k >= 6:
        step = int((n10k - 6) / 2)
        if n10k >= 16:
            step = 5
        if n10k >= 18:
            step = 6
        step = mini(step,6)
    return 208.0 - float(step * 8)

func poison_mush_at(p: Vector2):
    var c := cell_of(p)
    var mi := find_mush(c.x,c.y)
    if mi >= 0:
        mushrooms[mi]["poison"] = true

func flower_mush_at(p: Vector2):
    var c := cell_of(p)
    var mi := find_mush(c.x,c.y)
    if mi >= 0:
        mushrooms[mi]["flower"] = true
        mushrooms[mi]["poison"] = false
        mushrooms[mi]["hp"] = 4

func spider_eat(p: Vector2):
    var c := cell_of(p)
    var mi := find_mush(c.x,c.y)
    if mi >= 0:
        mushrooms.remove_at(mi)

func offscreen_bug(e) -> bool:
    var p: Vector2 = e["p"]
    if e["kind"] in ["earwig","inchworm"]:
        return p.x < -10 or p.x > 250
    if e["kind"] == "beetle":
        return p.x < -12 or p.x > 252 or p.y < -12 or p.y > 268
    if e["kind"] == "spider":
        return false
    return p.y > 266 or p.x < -20 or p.x > 260

func bug_radius(kind: String) -> float:
    if kind == "spider": return 8.0
    if kind == "inchworm": return 7.0
    return 6.0

func kill_bug(i: int, by_ddt: bool):
    if i < 0 or i >= bugs.size():
        return
    var e = bugs[i]
    var kind: String = e["kind"]
    var pts := bug_score(kind)
    if by_ddt:
        pts = 1800 if kind == "spider" else pts * 3
    if e["raid"]:
        # SHOOT2 applies the DDT multiplier first, then SHOOT3 applies the
        # progressive raid value, capped at 1000.
        if raid_value == 0:
            raid_value = mini(1000,pts)
        else:
            raid_value = mini(1000,maxi(pts,raid_value + 100))
        pts = raid_value
    add_score(pts)
    if kind == "mosquito":
        scroll_field_up()
    elif kind == "beetle":
        scroll_field_down()
    elif kind == "inchworm":
        slow_ticks = 0xE0
    if is_instance_valid(audio_engine):
        var sound_kind := "spider" if kind == "spider" else "kill"
        var sound_strength := clampf(0.42 + float(pts) / 1800.0 * 0.72,0.42,1.18)
        audio_engine.trigger(sound_kind,sound_strength,audio_pan_for(e["p"]),0.82 + float(pts) / 1800.0 * 0.65)
        if kind == "inchworm":
            audio_engine.trigger("slow",0.92,audio_pan_for(e["p"]),1.0)
    kill_fx(e["p"], by_ddt or kind == "spider")
    bugs.remove_at(i)

func bug_score(kind: String) -> int:
    match kind:
        "bee": return 200
        "beetle": return 300
        "mosquito": return 400
        "dragon": return 500
        "earwig": return 1000
        "inchworm": return 100
        "spider": return spider_score()
    return 0

func spider_score() -> int:
    # SHOOT2 uses vertical distance only, not Euclidean distance.
    var d := 999.0
    for e in bugs:
        if e["kind"] == "spider":
            d = absf(float(e["p"].y) - player.y)
            break
    if d < 11.0:
        return 1200
    if d < 22.0:
        return 900
    if d < 56.0:
        return 600
    return 300

func ddt_operation(stage: int) -> Dictionary:
    # Exact upright EXPLOD tables 97,96,95,94,93,94,93,92,91,90 in the
    # chronological order produced as DDTADD's explosion state counts down.
    # Non-zero 99$ stamps create CLOUD cells; the later zero tables erase them.
    var ops := [
        {"add":true,  "offsets":[0x41,0x60,0x61,0x62,0x80,0x81,0x82,0xA1]}, # 97
        {"add":true,  "offsets":[0x40,0x41,0x42,0x60,0x61,0x62,0x80,0x81,0x82,0xA0,0xA1,0xA2,0xC1]}, # 96
        {"add":true,  "offsets":[0x20,0x21,0x40,0x41,0x42,0x60,0x61,0x62,0x80,0x81,0x82,0xA0,0xA1,0xA2,0xC1,0xC2]}, # 95
        {"add":true,  "offsets":[0x00,0x01,0x02,0x20,0x21,0x22,0x40,0x41,0x42,0x60,0x61,0x62,0x80,0x81,0x82,0xA0,0xA1,0xA2,0xC0,0xC1,0xC2,0xE0,0xE1,0xE2]}, # 94
        {"add":false, "offsets":[0x00,0x01,0x02,0x22,0xC0,0xE0,0xE1,0xE2]}, # 93
        {"add":true,  "offsets":[0x00,0x01,0x02,0x20,0x21,0x22,0x40,0x41,0x42,0x60,0x61,0x62,0x80,0x81,0x82,0xA0,0xA1,0xA2,0xC0,0xC1,0xC2,0xE0,0xE1,0xE2]}, # 94 flash
        {"add":false, "offsets":[0x00,0x01,0x02,0x22,0xC0,0xE0,0xE1,0xE2]}, # 93
        {"add":false, "offsets":[0x20,0x21,0xC2]}, # 92
        {"add":false, "offsets":[0x40,0x42,0xA0,0xA2,0xC1]}, # 91
        {"add":false, "offsets":[0x41,0x60,0x61,0x62,0x80,0x81,0x82,0xA1]} # 90
    ]
    return ops[clampi(stage,0,ops.size()-1)]

func ddt_offset_cell(origin: Vector2i, offset: int) -> Vector2i:
    # Explosion OBST is original DDT playfield address - $61.  Playfield
    # columns are $20 bytes apart.  Normalize the row delta to -16..15, then
    # flip its sign because our Godot Y grows downward while Atari's row does not.
    var rel := offset - 0x61
    var dr: int = posmod(rel + 16, 32) - 16
    var dc: int = int((rel - dr) / 32)
    return Vector2i(origin.x + dc, origin.y - dr)

func ddt_cloud_cells(blast) -> Array:
    return blast.get("cloud_cells",[])

func ddt_cloud_hits_point(cells: Array, p: Vector2) -> bool:
    return cells.has(cell_of(p))

func kill_segments_ddt(indices: Array):
    if indices.is_empty():
        return
    var kill_set := {}
    for idx in indices:
        if idx >= 0 and idx < segments.size():
            kill_set[idx] = true

    var original := segments.duplicate()
    var survivors_by_group := {}
    for i in range(original.size()):
        var s = original[i]
        if kill_set.has(i):
            add_score((100 if s["head"] else 10) * 3)
            add_mush_at(s["p"])
            kill_fx(s["p"], true)
        else:
            var g := int(s["group"])
            if not survivors_by_group.has(g):
                survivors_by_group[g] = []
            survivors_by_group[g].append(s)

    segments.clear()
    for g in survivors_by_group.keys():
        var arr: Array = survivors_by_group[g]
        arr.sort_custom(func(a,b): return int(a["order"]) < int(b["order"]))
        var run := []
        var prev_order := -999
        for s in arr:
            var order := int(s["order"])
            if not run.is_empty() and order != prev_order + 1:
                _append_survivor_run(run, g)
                run = []
            run.append(s)
            prev_order = order
        if not run.is_empty():
            _append_survivor_run(run, g)

func _append_survivor_run(run: Array, old_group: int):
    if run.is_empty():
        return
    var original_first_order := int(run[0]["order"])
    var new_group := old_group if original_first_order == 0 else next_group_id
    if original_first_order != 0:
        next_group_id += 1
    for i in range(run.size()):
        var s = run[i]
        s["group"] = new_group
        s["order"] = i
        s["head"] = (i == 0)
        if i == 0 and original_first_order != 0:
            s["dx"] = -int(s["dx"])
        segments.append(s)

func apply_ddt_operation(blast, stage: int):
    var op := ddt_operation(stage)
    var cells: Array = blast.get("cloud_cells",[])
    var touched := []
    for off in op["offsets"]:
        var c := ddt_offset_cell(blast["cell"],int(off))
        if c.x < 0 or c.x >= COLS or c.y < 0 or c.y >= ROWS:
            continue
        touched.append(c)
        if bool(op["add"]):
            if not cells.has(c):
                cells.append(c)
        else:
            cells.erase(c)
    blast["cloud_cells"] = cells

    # EXPLOD overwrites mushrooms/rocks in every playfield stamp it touches.
    for i in range(mushrooms.size()-1,-1,-1):
        var mc := Vector2i(int(mushrooms[i]["col"]),int(mushrooms[i]["row"]))
        if touched.has(mc):
            mushrooms.remove_at(i)

func check_ddt_cloud_collisions():
    for blast in ddt_blasts:
        var cells: Array = blast.get("cloud_cells",[])
        if cells.is_empty():
            continue
        var hit_segments := []
        for i in range(segments.size()):
            if ddt_cloud_hits_point(cells,segments[i]["p"]):
                hit_segments.append(i)
        kill_segments_ddt(hit_segments)
        for i in range(bugs.size()-1,-1,-1):
            if ddt_cloud_hits_point(cells,bugs[i]["p"]):
                kill_bug(i,true)

func update_ddt_clouds():
    for blast in ddt_blasts:
        blast["ticks"] = int(blast.get("ticks",0)) + 1
        if int(blast["ticks"]) % 8 == 0:
            var next_stage := int(blast.get("stage",-1)) + 1
            if next_stage < 10:
                blast["stage"] = next_stage
                apply_ddt_operation(blast,next_stage)
    check_ddt_cloud_collisions()

func explode_ddt(center: Vector2):
    add_score(800)
    if is_instance_valid(audio_engine):
        audio_engine.trigger("ddt",1.45,audio_pan_for(center),1.0)
    rumble(0.72, 1.0, 0.42)
    fx_impact = 1.0
    shake = 9.0
    flash = 0.8
    kill_fx(center,true)
    var cc := cell_of(center)
    # Ten source explosion operations, one every 8 frames = about 1.34 s.
    ddt_blasts.append({"p":center,"cell":cc,"ticks":0,"stage":-1,"cloud_cells":[],"life":1.48,"max":1.48,"phase":rng.randf_range(0.0,TAU)})

func arcade_player_collision(obj: Vector2, spider := false) -> bool:
    # PLAY routine: ordinary objects require |H|<6, |V|<6 and H+V<10.
    # Spiders get the wider |H|<16 test and use H+2V<10.
    var dx := absf(obj.x - player.x)
    var dy := absf(obj.y - player.y)
    if dy >= 6.0:
        return false
    if spider:
        return dx < 16.0 and dx + 2.0 * dy < 10.0
    return dx < 6.0 and dx + dy < 10.0

func check_player_collisions():
    if player_inv > 0 or formation_wait > 0:
        return
    for s in segments:
        if arcade_player_collision(s["p"], false):
            player_die()
            return
    for e in bugs:
        # Earwigs live above the player region in normal play; keep their source
        # behavior non-contact here rather than expanding their hit area.
        if e["kind"] != "earwig" and arcade_player_collision(e["p"], e["kind"] == "spider"):
            player_die()
            return

func player_die():
    if player_inv > 0: return
    lives -= 1
    if is_instance_valid(audio_engine):
        audio_engine.trigger("death",1.35,audio_pan_for(player),1.0)
    rumble(0.90, 1.0, 0.55)
    flash = 0.85
    shake = 12.0
    fx_impact = 1.0
    kill_fx(player,true)
    bullets.clear()
    segments.clear()
    bugs.clear()
    side_feed_active = false
    restore_mushrooms()
    player = Vector2(120,240)
    player_target = player
    player_inv = 120
    formation_wait = 90

func restore_mushrooms():
    for m in mushrooms:
        if m["hp"] < 4 or m["poison"] or m["flower"]:
            add_score(5)
            m["hp"] = 4
            m["poison"] = false
            m["flower"] = false

func end_game():
    started = false
    game_over = true
    paused_game = false
    pause_overlay.visible = false
    mobile_controls.set_controls_enabled(false)
    mobile_move = Vector2.ZERO
    mobile_fire_held = false
    start_overlay.visible = true
    pause_touch.visible = false
    title_label.text = "GAME OVER"
    sub_label.text = "FINAL SCORE %06d\nPRESS START / A / FIRE TO RUN IT AGAIN" % score
    start_button.text = "RESTART"
    start_button.grab_focus()

func add_score(points: int):
    var before := int(score/10000)
    score += points
    var after := int(score/10000)
    if after > before:
        for n in range(before,after):
            side_feed_base = maxi(0x31, side_feed_base - 2)
    while score >= next_bonus:
        var awarded := lives < 6
        if awarded:
            lives += 1
            if is_instance_valid(audio_engine):
                audio_engine.trigger("bonus",1.1,0.0,1.0)
        next_bonus += 15000
        flash = max(flash,0.35)
        fx_impact = max(fx_impact,0.55)

func scroll_field_down():
    for i in range(mushrooms.size()-1,-1,-1):
        mushrooms[i]["row"] += 1
        # Source row 1 is the player line and gets scrolled off/cleared.
        if mushrooms[i]["row"] >= 30:
            mushrooms.remove_at(i)
    for i in range(ddts.size()-1,-1,-1):
        ddts[i]["row"] += 1
        if ddts[i]["row"] >= 31:
            ddts.remove_at(i)
    add_top_row_objects()
    maybe_add_scrolled_ddt()

func scroll_field_up():
    for i in range(mushrooms.size()-1,-1,-1):
        mushrooms[i]["row"] -= 1
        # Source row 31 is forbidden for mushrooms (Godot row 0).
        if mushrooms[i]["row"] <= 0:
            mushrooms.remove_at(i)
    for i in range(ddts.size()-1,-1,-1):
        ddts[i]["row"] -= 1
        if ddts[i]["row"] < 0:
            ddts.remove_at(i)

func add_top_row_objects():
    # SCROLD evaluates each of the 30 columns once. RND1 & $0F == 0 inserts a
    # full mushroom at source row $1E (30), which maps to Godot row 1.
    for col in range(COLS):
        if rng.randi_range(0,15) == 0 and not occupied_cell(col,1):
            mushrooms.append(make_mush(col,1))

func maybe_add_scrolled_ddt():
    # SCROLD can replenish a vacant DDT slot, but adds at most one new bomb per
    # scroll line. Candidate hardware columns are restricted away from both
    # edges (source effectively permits columns 4..23) at source row $1E.
    if ddts.size() >= 4:
        return
    var vacancies := 4 - ddts.size()
    for slot_attempt in range(vacancies):
        if rng.randi_range(0,3) == 3:
            continue
        var col_bank := rng.randi_range(0,2)
        var col_low := rng.randi_range(0,7)
        var col := col_bank * 8 + col_low
        if col < 4 or col > 23:
            continue
        var row := 1

        # The arcade DDT graphic spans two adjacent playfield stamps.  Our
        # gameplay representation uses one center cell, but clear both source
        # stamp cells so its placement pressure matches the original better.
        for mc in [col, col + 1]:
            var mi := find_mush(mc,row)
            if mi >= 0:
                mushrooms.remove_at(mi)
        ddts.append({"col": col, "row": row})
        break

func conway_cell_key(col: int, row: int) -> String:
    return "%d,%d" % [col,row]

func conway_pass():
    if is_instance_valid(audio_engine):
        audio_engine.trigger("conway",1.0,0.0,1.0)
    # Mark Cerny's CONWAY.MAC is not ordinary Conway Life.  It examines a 5x5
    # fairy-ring template: the inner eight cells are normal Conway neighbors,
    # the outer non-corner ring reacts specially to poison mushrooms, and the
    # center/corners are ignored.  Surviving damaged mushrooms grow through
    # stages while overcrowded/isolated mushrooms die through stages.
    conway_events.clear()
    conway_phase = 0
    conway_phase_ticks = 0

    var snap := {}
    for m in mushrooms:
        snap[conway_cell_key(int(m["col"]),int(m["row"]))] = {
            "hp":int(m["hp"]), "poison":bool(m["poison"]), "flower":bool(m["flower"])
        }

    # Source MASTER removes the extreme top/bottom rows from the algorithm.
    for row in range(2,30):
        for col in range(COLS):
            var key := conway_cell_key(col,row)
            var center = snap.get(key,null)
            if center != null and (bool(center["poison"]) or bool(center["flower"])):
                # CONWAY explicitly leaves poison mushrooms alone; rocks are not
                # normal growth/death stages either.
                continue

            var normal_count := 0
            var inner_poison := false
            var outer_poison := false

            # The source assumes one off-screen mushroom at a horizontal edge.
            if col == 0 or col == COLS-1:
                normal_count += 1

            for dy in range(-2,3):
                for dx in range(-2,3):
                    var ax: int = absi(dx)
                    var ay: int = absi(dy)
                    # GRCODE 2 = ignore: center and four corners.
                    if (dx == 0 and dy == 0) or (ax == 2 and ay == 2):
                        continue
                    # GRCODE 0 = inner 3x3 neighbors; GRCODE 1 = outer ring.
                    var inner: bool = ax <= 1 and ay <= 1
                    var nx: int = col + dx
                    var ny: int = row + dy
                    if nx < 0 or nx >= COLS or ny < 0 or ny >= ROWS:
                        continue
                    var n = snap.get(conway_cell_key(nx,ny),null)
                    if n == null:
                        continue
                    if inner:
                        if bool(n["poison"]):
                            inner_poison = true
                        elif not bool(n["flower"]):
                            normal_count += 1
                        else:
                            normal_count += 1
                    elif bool(n["poison"]):
                        outer_poison = true

            if center == null:
                # Blank squares grow on exactly 3 inner neighbors OR when poison
                # appears in the fairy-ring outer band, unless inner poison kills it.
                if not inner_poison and (normal_count == 3 or outer_poison):
                    conway_events.append({"col":col,"row":row,"kind":"grow_blank"})
            else:
                var hp := int(center["hp"])
                if inner_poison or (not outer_poison and (normal_count < 1 or normal_count >= 4)):
                    conway_events.append({"col":col,"row":row,"kind":"die"})
                elif hp < 4:
                    conway_events.append({"col":col,"row":row,"kind":"grow_existing"})

    if conway_events.is_empty():
        advance_centin()
        return
    conway_active = true
    formation_wait = 1
    fx_impact = maxf(fx_impact,0.42)

func update_conway():
    if not conway_active:
        return
    conway_phase_ticks += 1
    if conway_phase_ticks < 10:
        return
    conway_phase_ticks = 0
    conway_phase += 1

    for ev in conway_events:
        var col := int(ev["col"])
        var row := int(ev["row"])
        var kind: String = ev["kind"]
        var mi := find_mush(col,row)
        if kind == "grow_blank":
            if mi < 0 and conway_phase == 1 and not occupied_cell(col,row):
                var m = make_mush(col,row)
                m["hp"] = 1
                mushrooms.append(m)
                small_fx(cell_center(col,row),0.22)
            elif mi >= 0:
                mushrooms[mi]["hp"] = mini(4, int(mushrooms[mi]["hp"]) + 1)
        elif kind == "grow_existing":
            if mi >= 0:
                mushrooms[mi]["hp"] = mini(4, int(mushrooms[mi]["hp"]) + 1)
        elif kind == "die":
            if mi >= 0:
                mushrooms[mi]["hp"] = maxi(0, int(mushrooms[mi]["hp"]) - 1)
                if int(mushrooms[mi]["hp"]) <= 0:
                    kill_fx(cell_center(col,row),false)
                    mushrooms.remove_at(mi)

    fx_impact = maxf(fx_impact,0.34)
    if conway_phase >= 4:
        # CLEANUP in the source converts any unfinished growth stages to their
        # normal shot-away equivalents.  Our hp representation is normalized here.
        for m in mushrooms:
            m["hp"] = clampi(int(m["hp"]),1,4)
        conway_active = false
        conway_events.clear()
        conway_phase = 0
        advance_centin()

func small_fx(p: Vector2, power: float):
    for n in range(4):
        particles.append({"p":p,"v":Vector2.from_angle(rng.randf_range(0,TAU))*rng.randf_range(10,35)*power,"life":rng.randf_range(0.12,0.35),"max":0.35,"h":rng.randf()})

func kill_fx(p: Vector2, big: bool):
    var amount := 34 if big else 14
    if big and started:
        rumble(0.28, 0.55, 0.16)
    for n in range(amount):
        particles.append({"p":p,"v":Vector2.from_angle(rng.randf_range(0,TAU))*rng.randf_range(20,90)*(1.6 if big else 1.0),"life":rng.randf_range(0.22,0.75),"max":0.75,"h":rng.randf()})
    rings.append({"p":p,"r":2.0,"life":0.62 if big else 0.32,"max":0.62 if big else 0.32,"big":big})
    shake = max(shake,8.0 if big else 2.8)
    flash = max(flash,0.35 if big else 0.08)
    fx_impact = max(fx_impact,1.0 if big else 0.28)

func update_particles(delta):
    for i in range(player_trail.size()-1,-1,-1):
        player_trail[i]["life"] -= delta
        if player_trail[i]["life"] <= 0: player_trail.remove_at(i)
    for i in range(particles.size()-1,-1,-1):
        particles[i]["life"] -= delta
        particles[i]["p"] += particles[i]["v"] * delta
        particles[i]["v"] *= pow(0.12,delta)
        if particles[i]["life"] <= 0: particles.remove_at(i)
    for i in range(rings.size()-1,-1,-1):
        rings[i]["life"] -= delta
        rings[i]["r"] += delta * (85.0 if rings[i]["big"] else 55.0)
        if rings[i]["life"] <= 0: rings.remove_at(i)
    for i in range(ddt_blasts.size()-1,-1,-1):
        ddt_blasts[i]["life"] -= delta
        if ddt_blasts[i]["life"] <= 0: ddt_blasts.remove_at(i)

func hue(offset: float) -> Color:
    return Color.from_hsv(fposmod(Time.get_ticks_msec()*0.00004 + offset,1.0),0.92,1.0,1.0)

func field_color(offset: float, sat := 0.92, val := 1.0, alpha := 1.0) -> Color:
    var h := fposmod(Time.get_ticks_msec() * 0.00008 + offset, 1.0)
    return Color.from_hsv(h, sat, val, alpha)

func glow_circle(p: Vector2, r: float, color: Color, strength := 1.0):
    var c := color
    c.a = 0.055*strength
    draw_circle(p,r*2.8,c)
    c.a = 0.11*strength
    draw_circle(p,r*1.8,c)
    c.a = 0.95
    draw_circle(p,r,c)


func _draw():
    var shake_vec := Vector2(rng.randf_range(-shake,shake),rng.randf_range(-shake,shake)) if shake > 0.05 else Vector2.ZERO
    draw_set_transform(shake_vec,0.0,Vector2(SX,SY))

    draw_rect(Rect2(0,0,LW,LH),Color(0.0,0.0,0.02,0.64))
    draw_field_energy()
    draw_grid_fx()
    draw_mushrooms()
    draw_ddts()
    draw_segments()
    draw_bugs()
    draw_bullets()
    draw_fx()
    draw_player()

    draw_set_transform(Vector2.ZERO,0.0,Vector2.ONE)
    draw_cabinet_fx()
    for y in range(0,1024,8):
        draw_line(Vector2(0,y),Vector2(768,y),Color(0,0,0,0.09),1.0)
    if flash > 0.01:
        var fc := hue(0.15)
        fc.a = flash*0.30
        draw_rect(Rect2(0,0,768,1024),fc)

func draw_enemy_sigil(p: Vector2, c: Color, radius: float, phase: float, intensity := 1.0):
    var t := Time.get_ticks_msec() * 0.001
    var cc := Color(c.r,c.g,c.b,0.10 * intensity)
    draw_arc(p, radius, t * 0.55 + phase, t * 0.55 + phase + PI * 1.35, 22, cc, 0.7)
    draw_arc(p, radius * 1.42, -t * 0.42 + phase, -t * 0.42 + phase + PI * 0.95, 24, Color(c.r,c.g,c.b,0.055 * intensity), 0.7)
    for k in range(4):
        var a := phase + t * 0.34 + float(k) * TAU / 4.0
        var p0 := p + Vector2(cos(a),sin(a)) * radius * 1.18
        var p1 := p + Vector2(cos(a),sin(a)) * radius * 1.65
        draw_line(p0,p1,Color(c.r,c.g,c.b,0.13 * intensity),0.55)

func draw_energy_arc(p0: Vector2, p1: Vector2, c: Color, phase: float):
    var d := p1 - p0
    if d.length() < 1.0:
        return
    var n := Vector2(-d.y,d.x).normalized()
    var pts := PackedVector2Array()
    var t := Time.get_ticks_msec() * 0.008 + phase
    for i in range(7):
        var u := float(i) / 6.0
        var wobble := sin(t + u * 18.0) * 1.0 + sin(t * 1.7 + u * 31.0) * 0.45
        if i == 0 or i == 6:
            wobble = 0.0
        pts.append(p0.lerp(p1,u) + n * wobble)
    draw_polyline(pts,Color(c.r,c.g,c.b,0.16),2.6)
    draw_polyline(pts,Color(c.r,c.g,c.b,0.72),0.65)

func draw_readability_disc(p: Vector2, radius: float, strength := 1.0):
    # Local contrast well: preserves the psychedelic field but guarantees
    # gameplay silhouettes survive underneath bloom/color cycling.
    draw_circle(p, radius * 2.25, Color(0.0,0.0,0.012,0.16 * strength))
    draw_circle(p, radius * 1.65, Color(0.0,0.0,0.018,0.34 * strength))
    draw_circle(p, radius * 1.15, Color(0.0,0.0,0.025,0.60 * strength))

func draw_readability_ring(p: Vector2, radius: float, c: Color, strength := 1.0):
    draw_arc(p, radius, 0.0, TAU, 24, Color(0.0,0.0,0.0,0.88 * strength), 1.8)
    draw_arc(p, radius, 0.0, TAU, 24, Color(1.0,1.0,1.0,0.18 * strength), 0.65)
    draw_arc(p, radius + 0.9, 0.0, TAU, 24, Color(c.r,c.g,c.b,0.42 * strength), 0.55)

func draw_field_energy():
    var t := Time.get_ticks_msec() * 0.001
    var cycle_speed := 1.0 + fx_impact * 0.8

    # deep rainbow plasma behind the entire playfield
    for band in range(32):
        var y0 := float(band) * 8.0
        var c0 := field_color(float(band) * 0.027 + sin(t * 0.6 + float(band) * 0.31) * 0.035, 0.86, 0.55, 0.060)
        draw_rect(Rect2(0, y0, LW, 8.0), c0, true)

    # checker glow cells so the field itself feels alive, not just the border/background
    for row in range(ROWS):
        for col in range(COLS):
            var pulse := 0.5 + 0.5 * sin(t * (1.8 * cycle_speed) + float(col) * 0.44 + float(row) * 0.33)
            var c := field_color(float(col) * 0.018 + float(row) * 0.012 + pulse * 0.05, 0.74, 0.78)
            c.a = 0.007 + pulse * 0.013
            draw_rect(Rect2(float(col) * 8.0 + 0.5, float(row) * 8.0 + 0.5, 7.0, 7.0), c, true)

    # sweeping rainbow diagonals across the upper field
    for i in range(16):
        var y := 10.0 + float(i) * 14.0 + sin(t * (1.1 + fx_impact * 0.6) + float(i) * 0.8) * 3.0
        var c := field_color(0.12 + float(i) * 0.045 + t * 0.03, 0.96, 1.0)
        c.a = 0.034 + 0.014 * sin(t * 0.7 + float(i))
        draw_line(Vector2(0,y),Vector2(LW,y + 7.0 * sin(t * 0.5 + float(i) * 0.3)),c,1.5)

    # animated color-cycling player-zone floor / grid
    var floor_rows := 12
    for i in range(floor_rows):
        var u := float(i) / float(floor_rows - 1)
        var y := lerpf(PLAYER_TOP + 4.0, LH - 2.0, u)
        var inset := pow(1.0 - u, 2.0) * LW * 0.43
        var c := field_color(0.38 + u * 0.35 + sin(t * 0.5 + u * 8.0) * 0.04, 0.96, 1.0)
        c.a = 0.055 + u * 0.055
        draw_line(Vector2(inset,y),Vector2(LW-inset,y),c,1.4)
        var glow := c
        glow.a *= 0.28
        draw_line(Vector2(inset,y+1.0),Vector2(LW-inset,y+1.0),glow,3.4)

    for j in range(-7,8):
        var topx := LW * 0.5 + float(j) * 10.5 + sin(t * 0.7 + float(j)) * 1.6
        var bottomx := LW * 0.5 + float(j) * 24.0
        var c := field_color(0.58 + absf(float(j)) * 0.027 + t * 0.02, 0.94, 1.0)
        c.a = 0.055
        draw_line(Vector2(topx,PLAYER_TOP),Vector2(bottomx,LH),c,1.05)

    # energy lanes that travel vertically up the playfield
    for lane in range(5):
        var x := 24.0 + float(lane) * 48.0 + sin(t * 0.8 + float(lane) * 1.7) * 6.0
        for seg in range(7):
            var yy := fposmod(LH - (t * 34.0 * cycle_speed + float(seg) * 42.0 + float(lane) * 18.0), LH)
            var c := field_color(0.72 + float(lane) * 0.09 + float(seg) * 0.03, 0.88, 1.0)
            c.a = 0.032
            draw_rect(Rect2(x - 8.0, yy, 16.0, 10.0), c, true)

func draw_grid_fx():
    var t := Time.get_ticks_msec() * 0.001
    for x in range(0,241,8):
        var c := field_color(0.18 + float(x) * 0.004 + sin(t * 0.5 + float(x) * 0.03) * 0.03, 0.92, 1.0)
        c.a = 0.015 + 0.007 * sin(t * 1.2 + float(x) * 0.06)
        draw_line(Vector2(x,0),Vector2(x,LH),c,0.55)
    for y in range(0,257,8):
        var c := field_color(0.58 + float(y) * 0.005 + cos(t * 0.6 + float(y) * 0.04) * 0.03, 0.88, 0.95)
        c.a = 0.013 + 0.005 * sin(t * 1.0 + float(y) * 0.05)
        draw_line(Vector2(0,y),Vector2(LW,y),c,0.55)

    # glowing intersections / lane markers
    for row in range(0, ROWS, 2):
        for col in range(0, COLS, 2):
            var pulse := 0.5 + 0.5 * sin(t * 2.0 + float(col) * 0.5 + float(row) * 0.4)
            var c := field_color(0.08 + float(col) * 0.02 + float(row) * 0.012 + pulse * 0.08, 0.98, 1.0)
            c.a = 0.035 * pulse
            draw_circle(Vector2(float(col) * 8.0 + 4.0, float(row) * 8.0 + 4.0), 1.2 + pulse * 0.7, c)

    # hard border around the sacred arcade field
    var border := field_color(0.92 + sin(t * 0.3) * 0.08, 0.95, 1.0)
    border.a = 0.32
    draw_rect(Rect2(0.5,0.5,LW-1.0,LH-1.0), border, false, 1.2)

func draw_cabinet_fx():
    var t := Time.get_ticks_msec() * 0.001
    var left := 24.0
    var top := 24.0
    var width := LW * SX
    var height := LH * SY
    var inner := Rect2(left, top, width, height)
    var outer := Rect2(left - 12.0, top - 12.0, width + 24.0, height + 24.0)

    for side in [0, 1]:
        var x := 10.0 if side == 0 else 768.0 - 10.0
        var dir := -1.0 if side == 0 else 1.0
        for i in range(14):
            var yy := 36.0 + float(i) * 70.0
            var pulse := 24.0 + 8.0 * sin(t * 2.0 + float(i) * 0.7)
            var c := hue(0.15 + float(i) * 0.08 + float(side) * 0.22)
            c.a = 0.07
            draw_circle(Vector2(x + dir * 6.0, yy), pulse, c)
        var rail := hue(0.12 + float(side) * 0.35)
        rail.a = 0.85
        draw_line(Vector2(x,30),Vector2(x,994),rail,4.0)
        rail.a = 0.24
        draw_line(Vector2(x + dir * 8.0,30),Vector2(x + dir * 8.0,994),rail,10.0)

    var border1 := hue(0.60); border1.a = 0.9
    var border2 := hue(0.13); border2.a = 0.45
    draw_rect(outer,border2,false,8.0)
    draw_rect(inner,border1,false,4.0)
    draw_rect(Rect2(inner.position + Vector2(8,8), inner.size - Vector2(16,16)), Color(border1.r,border1.g,border1.b,0.22), false, 2.0)

    var marquee := Rect2(58, 8, 652, 28)
    draw_rect(marquee, Color(0,0,0,0.45), true)
    for i in range(9):
        var c := hue(0.05 + float(i) * 0.09)
        c.a = 0.08
        draw_circle(Vector2(80 + float(i) * 76.0, 22), 18.0 + 4.0 * sin(t * 1.8 + float(i)), c)
    draw_rect(marquee, Color(1,1,1,0.08), false, 2.0)

func draw_mushrooms():
    var t := Time.get_ticks_msec() * 0.001
    for m in mushrooms:
        var p := cell_center(m["col"],m["row"])
        var c := hue(0.12 + float(m["col"]) * 0.027 + float(m["row"]) * 0.016)
        if m["poison"]: c = hue(0.86 + float(m["row"]) * 0.012)
        if m["flower"]: c = hue(0.05 + float(m["col"]) * 0.02)
        var pulse := 1.0 + 0.12 * sin(t * 3.2 + float(m["phase"]))
        draw_readability_disc(p,4.8,0.78)
        draw_readability_ring(p,4.5,c,0.60)
        var stem := Color(c.r * 0.65, c.g * 0.65, c.b * 0.65, 0.92)
        if m["flower"]:
            for k in range(6):
                var a := float(k) * TAU / 6.0 + t * 0.3
                var petal_p := p + Vector2(cos(a), sin(a)) * 3.5
                glow_circle(petal_p, 1.9 * pulse, c, 0.72)
            draw_circle(p, 1.1, Color(1.0,0.95,0.55,0.95))
        else:
            draw_rect(Rect2(p.x - 1.0, p.y + 0.3, 2.0, 4.4), stem)
            glow_circle(p + Vector2(0.0,-1.8), 3.8 * pulse, c, 0.65)
            draw_circle(p + Vector2(-1.7,-1.4), 1.45 * pulse, Color(c.r,c.g,c.b,0.42))
            draw_circle(p + Vector2(1.7,-1.4), 1.45 * pulse, Color(c.r,c.g,c.b,0.42))
            draw_arc(p + Vector2(0.0,-1.4), 3.5 * pulse, PI, TAU, 18, Color(1,1,1,0.24), 0.9)
            var hp_scale := 0.55 + 0.12 * int(m["hp"])
            draw_circle(p + Vector2(-1.0,-2.0), 0.7 * hp_scale, Color(1,1,1,0.50))
            draw_circle(p + Vector2(1.2,-1.6), 0.45 * hp_scale, Color(1,1,1,0.30))
            if m["poison"]:
                draw_enemy_sigil(p,c,6.2,float(m["phase"]),0.65)

func draw_ddts():
    var t := Time.get_ticks_msec() * 0.001
    for d in ddts:
        var p := cell_center(d["col"],d["row"])
        var c := hue(0.16)
        draw_readability_disc(p,6.0,1.0)
        draw_readability_ring(p,5.2,c,0.9)
        glow_circle(p,4.2,c,0.86)
        for r in [3.0, 5.2, 7.8]:
            var alpha := 0.28 if r < 5.0 else 0.12
            draw_arc(p, r + sin(t * 2.2 + r) * 0.35, t * 0.8 + r, t * 0.8 + r + PI * 1.2, 20, Color(c.r,c.g,c.b,alpha), 0.9)
        for k in range(4):
            var a := t * 2.0 + float(k) * TAU / 4.0
            var q := p + Vector2(cos(a), sin(a)) * 4.0
            draw_line(p, q, Color(1.0,0.94,0.55,0.7), 0.9)
        draw_circle(p, 1.2, Color(0.03,0.02,0.0,0.96))
        draw_string(ThemeDB.fallback_font, p + Vector2(-5.0, 3.0), "DDT", HORIZONTAL_ALIGNMENT_LEFT, -1.0, 7, Color(1.0,0.95,0.65,0.75))

func draw_segments():
    var t := Time.get_ticks_msec() * 0.001
    for s in segments:
        var child = null
        for candidate in segments:
            if int(candidate["group"]) == int(s["group"]) and int(candidate["order"]) == int(s["order"]) + 1:
                child = candidate
                break
        if child != null:
            var p0: Vector2 = s["p"]
            var p1: Vector2 = child["p"]
            var lc := hue(0.48 + float(s["order"]) * 0.035)
            lc.a = 0.18
            draw_line(p0,p1,lc,5.6)
            lc.a = 0.55
            draw_line(p0,p1,lc,2.2)
            draw_energy_arc(p0,p1,lc,float(s["phase"]))

    for s in segments:
        var p: Vector2 = s["p"]
        var body := hue(0.44 + float(s["order"]) * 0.075 + float(s["group"]) * 0.013)
        if s["poison"]:
            body = hue(0.88)
        var r := 4.6 if s["head"] else 3.9
        draw_readability_disc(p,r + 1.8,0.96)
        draw_readability_ring(p,r + 0.5,body,0.82)
        if s["head"]:
            draw_enemy_sigil(p,body,7.5,float(s["phase"]),1.0)
        glow_circle(p, r, body, 0.95)
        draw_circle(p, r * 0.58, Color(0.05,0.05,0.08,0.65))
        draw_arc(p, r * 0.92, PI * 0.12, PI * 0.88, 14, Color(1,1,1,0.18), 0.8)
        for stripe in range(3):
            var yy := -1.9 + float(stripe) * 1.8
            draw_line(p + Vector2(-2.4,yy), p + Vector2(2.4,yy), Color(1.0,0.92,0.55,0.26), 0.8)
        var leg_phase := t * 9.0 + float(s["phase"])
        for side in [-1,1]:
            draw_line(p + Vector2(side * 1.8, 1.0), p + Vector2(side * (5.0 + sin(leg_phase) * 1.1), 3.8), body, 0.75)
            draw_line(p + Vector2(side * 1.8, -1.0), p + Vector2(side * (5.2 - cos(leg_phase) * 0.9), -3.6), body, 0.75)
        if s["head"]:
            for antenna_side in [-1,1]:
                draw_line(p + Vector2(antenna_side * 1.4,-1.4), p + Vector2(antenna_side * 4.0,-5.8), body, 0.65)
                draw_circle(p + Vector2(antenna_side * 4.0,-5.8), 0.45, Color(1.0,0.9,0.65,0.8))
            draw_circle(p + Vector2(-1.2,-0.5), 0.7, Color.WHITE)
            draw_circle(p + Vector2(1.2,-0.5), 0.7, Color.WHITE)
            draw_circle(p + Vector2(-1.2,-0.5), 0.28, Color.BLACK)
            draw_circle(p + Vector2(1.2,-0.5), 0.28, Color.BLACK)

func draw_bugs():
    var t := Time.get_ticks_msec() * 0.001
    for e in bugs:
        var p: Vector2 = e["p"]
        var k: String = e["kind"]
        var c := hue(float({"bee":0.10,"dragon":0.62,"mosquito":0.50,"earwig":0.90,"inchworm":0.24,"beetle":0.04,"spider":0.80}.get(k,0.4)))
        var vis_r := 6.5 if k != "spider" else 9.0
        draw_readability_disc(p,vis_r,0.95)
        draw_readability_ring(p,vis_r * 0.68,c,0.72)
        draw_enemy_sigil(p,c,6.0 + (2.5 if k == "spider" else 0.0),float(e["phase"]),0.8)
        var vel := Vector2.ZERO
        if e.has("v"): vel = e["v"]
        if vel.length() > 0.1:
            for i in range(1,5):
                var pp := p - vel.normalized() * float(i) * 2.0
                var tc := Color(c.r,c.g,c.b,0.05 * (5 - i))
                draw_circle(pp, maxf(1.0, 3.8 - float(i) * 0.55), tc)

        match k:
            "bee":
                glow_circle(p,3.9,c,0.72)
                draw_circle(p, 2.5, Color(0.06,0.06,0.08,0.6))
                for w in [-1,1]:
                    var wing_p := p + Vector2(float(w) * 2.4, -1.6 + sin(t * 16.0 + float(w)) * 0.8)
                    draw_circle(wing_p, 2.0, Color(0.7,0.95,1.0,0.22))
                for s in [-1,0,1]:
                    draw_line(p + Vector2(-2.0, float(s) * 1.3), p + Vector2(2.0, float(s) * 1.3), Color(1.0,0.92,0.3,0.45), 0.7)
            "dragon":
                glow_circle(p,4.1,c,0.75)
                draw_line(p + Vector2(-6,0), p + Vector2(6,0), c, 1.5)
                for w in [-1,1]:
                    draw_line(p, p + Vector2(float(w) * 5.0, -4.0 + sin(t * 9.0 + float(w)) * 2.0), Color(0.75,1.0,1.0,0.55), 1.1)
                    draw_line(p + Vector2(float(w) * 1.0,1.0), p + Vector2(float(w) * 5.0, 4.0 - sin(t * 9.0 + float(w)) * 2.0), Color(0.75,1.0,1.0,0.45), 1.0)
                draw_circle(p + Vector2(5.8,0), 1.1, Color(1,1,1,0.55))
            "mosquito":
                glow_circle(p,3.7,c,0.72)
                draw_line(p + Vector2(-1,0), p + Vector2(6,0), Color(1.0,1.0,0.8,0.8), 0.9)
                for w in [-1,1]:
                    draw_line(p + Vector2(-1,0), p + Vector2(float(w) * 5.0, -4.0 + sin(t * 12.0) * 1.4), Color(0.7,1.0,1.0,0.55), 1.0)
                    draw_line(p + Vector2(-1,0), p + Vector2(float(w) * 5.0, 4.0 - sin(t * 12.0) * 1.4), Color(0.7,1.0,1.0,0.35), 1.0)
            "earwig":
                glow_circle(p,4.1,c,0.75)
                draw_line(p + Vector2(-4,0), p + Vector2(4,0), c, 1.6)
                draw_line(p + Vector2(4,0), p + Vector2(7,-2), c, 1.1)
                draw_line(p + Vector2(4,0), p + Vector2(7,2), c, 1.1)
                for n in range(4):
                    var xx := -3.5 + float(n) * 2.2
                    draw_line(p + Vector2(xx,1.0), p + Vector2(xx+1.2,3.0), c, 0.8)
                    draw_line(p + Vector2(xx,-1.0), p + Vector2(xx+1.2,-3.0), c, 0.8)
            "inchworm":
                for n in range(5):
                    var offs := float(n - 2) * 2.2
                    var bob := sin(t * 7.0 + float(n) * 0.8) * 0.9
                    glow_circle(p + Vector2(offs,bob),2.2 - absf(float(n - 2)) * 0.18,c,0.42)
                draw_line(p + Vector2(-5,0), p + Vector2(5,0), Color(1.0,1.0,1.0,0.10), 0.9)
            "beetle":
                glow_circle(p,4.3,c,0.78)
                draw_circle(p, 3.0, Color(0.05,0.05,0.07,0.55))
                draw_arc(p,3.2,PI,TAU,16,Color(1.0,1.0,1.0,0.18),0.8)
                draw_line(p + Vector2(0,-3), p + Vector2(0,3), Color(1.0,0.95,0.55,0.35), 0.8)
                for side in [-1,1]:
                    for row in [-1,0,1]:
                        draw_line(p + Vector2(float(side) * 2.0, float(row)), p + Vector2(float(side) * 5.0, float(row) * 2.5), c, 0.75)
            "spider":
                glow_circle(p,4.8,c,0.84)
                draw_circle(p + Vector2(0,1.2), 2.8, Color(0.05,0.05,0.07,0.55))
                draw_circle(p + Vector2(0,-2.0), 1.9, Color(0.08,0.08,0.1,0.58))
                for side in [-1,1]:
                    for idx in range(4):
                        var yy := -3.0 + float(idx) * 2.0
                        var x1 := 2.0 + float(idx)
                        var x2 := 7.0 + float(idx) * 1.2
                        draw_line(p + Vector2(float(side) * x1, yy * 0.6), p + Vector2(float(side) * x2, yy + sin(t * 8.0 + float(idx) + float(side)) * 1.2), c, 0.8)
                draw_circle(p + Vector2(-0.8,-2.4), 0.45, Color.WHITE)
                draw_circle(p + Vector2(0.8,-2.4), 0.45, Color.WHITE)

func draw_bullets():
    for b in bullets:
        var c := hue(0.50)
        var tr = b["trail"]
        for i in range(tr.size()-1,-1,-1):
            var a := float(tr.size() - i) / maxf(1.0, float(tr.size()))
            var tc := Color(c.r,c.g,c.b,0.05 + 0.04 * a)
            draw_circle(tr[i],1.8 + a * 0.8,tc)
        draw_circle(b["p"],3.0,Color(0,0,0,0.65))
        glow_circle(b["p"],1.6,c,1.0)
        draw_line(b["p"] + Vector2(-3,0), b["p"] + Vector2(3,0), Color(1.0,1.0,1.0,0.70), 0.9)
        draw_line(b["p"] + Vector2(0,3), b["p"] - Vector2(0,4), c, 1.5)

func draw_fx():
    var tt := Time.get_ticks_msec() * 0.001
    for b in ddt_blasts:
        var a: float = clampf(float(b["life"]) / float(b["max"]),0.0,1.0)
        var progress := 1.0 - a
        var bp: Vector2 = b["p"]
        var bc := hue(0.08 + progress * 0.32)
        var cells: Array = b.get("cloud_cells",[])
        # Draw the actual source-derived cloud stamps as luminous 8x8 vapor cells.
        for ci in range(cells.size()):
            var cc: Vector2i = cells[ci]
            var cp := cell_center(cc.x,cc.y)
            var pulse := 0.7 + 0.3 * sin(tt * 14.0 + float(ci) * 1.7 + float(b["phase"]))
            draw_rect(Rect2(cp - Vector2(4.0,4.0),Vector2(8.0,8.0)),Color(bc.r,bc.g,bc.b,0.055 * a * pulse),true)
            glow_circle(cp,3.7 + pulse * 1.1,bc,0.54 * a)
            draw_arc(cp,4.8,tt * 2.0 + float(ci),tt * 2.0 + float(ci) + PI * 1.35,14,Color(1.0,0.95,0.55,0.22*a),0.8)
        # Keep a larger modern shock halo around the faithful stamp footprint.
        var rad := 10.0 + progress * 38.0
        draw_circle(bp,rad,Color(bc.r,bc.g,bc.b,0.012*a))
        for ri in range(3):
            var rr := rad * (0.38 + float(ri) * 0.24)
            draw_arc(bp,rr,tt * (1.0 + float(ri)*0.13) + float(b["phase"]),TAU + tt * (1.0 + float(ri)*0.13) + float(b["phase"]),48,Color(bc.r,bc.g,bc.b,a*(0.12-float(ri)*0.025)),1.0)
    for p in particles:
        var a: float = clampf(float(p["life"]) / float(p["max"]),0.0,1.0)
        var c := hue(float(p["h"])); c.a = a
        draw_circle(p["p"],0.65 + a * 1.4,c)
        if a > 0.2:
            draw_line(p["p"] + Vector2(-a * 2.0,0), p["p"] + Vector2(a * 2.0,0), Color(c.r,c.g,c.b,a * 0.45), 0.6)
    for r in rings:
        var a: float = clampf(float(r["life"]) / float(r["max"]),0.0,1.0)
        var c := hue(0.58 + a * 0.2); c.a = a * 0.55
        draw_arc(r["p"],float(r["r"]),0,TAU,48,c,1.0 + a * 1.5)
        draw_arc(r["p"],float(r["r"]) * 0.66,0,TAU,36,Color(c.r,c.g,c.b,a * 0.18),0.8)

func draw_player():
    for t in player_trail:
        var a: float = clampf(float(t["life"]) / 0.22,0.0,1.0)
        var c := hue(0.56); c.a = a * 0.08
        draw_circle(t["p"],4.6,c)
    var c := Color.WHITE if player_inv > 0 and (frame_count & 4) != 0 else hue(0.56)
    draw_readability_disc(player,8.0,1.0)
    draw_readability_ring(player,6.0,c,1.0)
    glow_circle(player,4.5,c,1.0)
    var ship := PackedVector2Array([
        player + Vector2(0,-7),
        player + Vector2(5.2,1.6),
        player + Vector2(3.0,5.5),
        player + Vector2(0,2.8),
        player + Vector2(-3.0,5.5),
        player + Vector2(-5.2,1.6)
    ])
    draw_colored_polygon(ship, Color(c.r * 0.30, c.g * 0.30, c.b * 0.30, 0.42))
    draw_polyline(PackedVector2Array([ship[0],ship[1],ship[2],ship[3],ship[4],ship[5],ship[0]]),c,1.1)
    draw_line(player + Vector2(0,-6), player + Vector2(0,-11), c, 1.0)
    draw_line(player + Vector2(-2.0,3.5), player + Vector2(-4.5,7.0 + sin(Time.get_ticks_msec()*0.01) * 1.3), Color(0.3,0.95,1.0,0.55), 0.8)
    draw_line(player + Vector2(2.0,3.5), player + Vector2(4.5,7.0 + sin(Time.get_ticks_msec()*0.01 + 1.2) * 1.3), Color(1.0,0.45,0.95,0.55), 0.8)

func update_ui():
    score_label.text = "%06d" % score
    lives_label.text = "LIVES %d" % lives
    if raid_mode:
        wave_label.text = "RAID %02d" % raid_source
        status_label.text = "RAID SCORE +%d" % raid_value
    else:
        wave_label.text = "MILLI %02d %s" % [centin, "FAST" if centis==2 else "SLOW"]
        var fx_name := "MAX" if fx_mode == 0 else ("OVERDRIVE" if fx_mode == 1 else "CLEAN")
        var status := "30×32 • 59.886 Hz • FX %s" % fx_name
        if slow_ticks > 0: status = "INCHWORM SLOW %d" % slow_ticks
        elif side_feed_active: status = "SIDE FEED ACTIVE"
        status_label.text = status

func _on_mobile_move(direction: Vector2):
    mobile_move = direction

func _on_mobile_fire(pressed: bool):
    mobile_fire_held = pressed
    if pressed:
        fire_requested = true

func _on_mobile_pause():
    if started and not paused_game:
        toggle_pause()

func _on_mobile_drag(screen_position: Vector2):
    if started and not paused_game:
        var logical := screen_to_logical(screen_position)
        player_target = Vector2(clamp(logical.x,4.0,236.0), clamp(logical.y,PLAYER_TOP+4.0,248.0))

func screen_to_logical(screen_pos: Vector2) -> Vector2:
    return Vector2(screen_pos.x/SX,screen_pos.y/SY)

func _input(event):
    if event is InputEventJoypadButton or event is InputEventJoypadMotion:
        active_joypad = event.device

    if mobile_mode and (event is InputEventScreenTouch or event is InputEventScreenDrag):
        return

    if paused_game:
        return

    if event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT:
        if event.pressed:
            if not started:
                start_game()
            touch_dragging = true
            player_target = screen_to_logical(event.position)
        else:
            touch_dragging = false
    elif event is InputEventMouseMotion and touch_dragging:
        player_target = screen_to_logical(event.position)
    elif event is InputEventScreenTouch:
        if event.pressed:
            if not started:
                start_game()
            if event.position.x > 600 and event.position.y > 840:
                request_fire()
            elif event.position.x < 130 and event.position.y > 880:
                toggle_pause()
            else:
                touch_id = event.index
                player_target = screen_to_logical(event.position)
        elif event.index == touch_id:
            touch_id = -1
    elif event is InputEventScreenDrag and event.index == touch_id:
        player_target = screen_to_logical(event.position)


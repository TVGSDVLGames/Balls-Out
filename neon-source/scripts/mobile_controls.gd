extends Control

signal move_changed(direction: Vector2)
signal fire_changed(pressed: bool)
signal pause_pressed
signal drag_delta(screen_delta: Vector2)
signal drag_active_changed(active: bool)

var enabled := true
var joystick_touch := -1
var fire_touch := -1
var drag_touch := -1
var joystick_vector := Vector2.ZERO
var fire_down := false
var joystick_origin := Vector2.ZERO
var knob_pos := Vector2.ZERO
var drag_last := Vector2.ZERO
var pulse := 0.0

const PLAYFIELD_BOTTOM := 1024.0
const DOCK_HEIGHT := 256.0
const STICK_RADIUS := 92.0
const KNOB_RADIUS := 40.0
const FIRE_RADIUS := 82.0
const PAUSE_RADIUS := 46.0
const STICK_DEADZONE := 0.14
const DRAG_JITTER := 0.65
const DRAG_MAX_EVENT := 160.0

func _ready():
    mouse_filter = Control.MOUSE_FILTER_IGNORE
    set_process_input(true)
    set_process(true)
    resized.connect(_on_resized)
    _on_resized()

func _on_resized():
    if joystick_touch < 0:
        joystick_origin = stick_center()
        knob_pos = joystick_origin
    queue_redraw()

func dock_top() -> float:
    return maxf(PLAYFIELD_BOTTOM, size.y - DOCK_HEIGHT)

func stick_center() -> Vector2:
    return Vector2(146.0, dock_top() + DOCK_HEIGHT * 0.53)

func fire_center() -> Vector2:
    return Vector2(size.x - 146.0, dock_top() + DOCK_HEIGHT * 0.53)

func pause_center() -> Vector2:
    return Vector2(size.x * 0.5, dock_top() + DOCK_HEIGHT * 0.53)

func _process(delta):
    pulse += delta
    queue_redraw()

func set_controls_enabled(value: bool):
    enabled = value
    visible = value
    if not value:
        _release_all()

func _release_all():
    var had_drag := drag_touch >= 0
    joystick_touch = -1
    fire_touch = -1
    drag_touch = -1
    joystick_vector = Vector2.ZERO
    joystick_origin = stick_center()
    knob_pos = joystick_origin
    drag_last = Vector2.ZERO
    if fire_down:
        fire_down = false
        fire_changed.emit(false)
    if had_drag:
        drag_active_changed.emit(false)
    move_changed.emit(Vector2.ZERO)
    queue_redraw()

func _input(event):
    if not enabled or not visible:
        return

    if event is InputEventScreenTouch:
        var p: Vector2 = event.position
        if event.pressed:
            # A finger owns exactly one role for its lifetime.  This prevents
            # iOS multi-touch from reclassifying a move finger as FIRE/DRAG.
            if event.index == joystick_touch or event.index == fire_touch or event.index == drag_touch:
                get_viewport().set_input_as_handled()
                return

            if p.distance_to(pause_center()) <= PAUSE_RADIUS + 24.0:
                pause_pressed.emit()
                get_viewport().set_input_as_handled()
                return

            if p.y >= dock_top():
                # Make the entire right side of the dock a reliable fire target,
                # not only the visible circle.  The center gap stays reserved.
                if fire_touch < 0 and p.x >= size.x * 0.56:
                    fire_touch = event.index
                    if not fire_down:
                        fire_down = true
                        fire_changed.emit(true)
                    get_viewport().set_input_as_handled()
                    return

                # Floating-stick capture: wherever the left thumb lands becomes
                # neutral, so touching the edge of the old fixed ring cannot
                # generate an instant full-speed jump.
                if joystick_touch < 0 and p.x <= size.x * 0.44:
                    joystick_touch = event.index
                    joystick_origin = _clamp_stick_origin(p)
                    knob_pos = joystick_origin
                    joystick_vector = Vector2.ZERO
                    move_changed.emit(Vector2.ZERO)
                    get_viewport().set_input_as_handled()
                    queue_redraw()
                    return

            # The playfield is a relative trackball.  Touch-down itself does not
            # teleport the player; only actual finger movement creates motion.
            if drag_touch < 0 and p.y < dock_top():
                drag_touch = event.index
                drag_last = p
                drag_active_changed.emit(true)
                get_viewport().set_input_as_handled()
                return
        else:
            if event.index == joystick_touch:
                joystick_touch = -1
                joystick_vector = Vector2.ZERO
                joystick_origin = stick_center()
                knob_pos = joystick_origin
                move_changed.emit(Vector2.ZERO)
                get_viewport().set_input_as_handled()
                queue_redraw()
                return
            if event.index == fire_touch:
                fire_touch = -1
                if fire_down:
                    fire_down = false
                    fire_changed.emit(false)
                get_viewport().set_input_as_handled()
                queue_redraw()
                return
            if event.index == drag_touch:
                drag_touch = -1
                drag_last = Vector2.ZERO
                drag_active_changed.emit(false)
                get_viewport().set_input_as_handled()
                return

    elif event is InputEventScreenDrag:
        if event.index == joystick_touch:
            _update_stick(event.position)
            get_viewport().set_input_as_handled()
            return
        if event.index == drag_touch:
            var d := event.position - drag_last
            drag_last = event.position
            # Safari/WebKit can occasionally deliver a large discontinuity when
            # touch coordinates are resampled.  Clamp that single event rather
            # than allowing one bad sample to fling the player across the field.
            if d.length() > DRAG_MAX_EVENT:
                d = d.normalized() * DRAG_MAX_EVENT
            if d.length() >= DRAG_JITTER:
                drag_delta.emit(d)
            get_viewport().set_input_as_handled()
            return

func _clamp_stick_origin(p: Vector2) -> Vector2:
    var left := STICK_RADIUS + 12.0
    var right := size.x * 0.44 - STICK_RADIUS - 12.0
    var top := dock_top() + STICK_RADIUS + 12.0
    var bottom := size.y - STICK_RADIUS - 12.0
    if right < left:
        right = left
    if bottom < top:
        bottom = top
    return Vector2(clampf(p.x, left, right), clampf(p.y, top, bottom))

func _update_stick(p: Vector2):
    var delta := p - joystick_origin
    if delta.length() > STICK_RADIUS:
        delta = delta.normalized() * STICK_RADIUS
    knob_pos = joystick_origin + delta

    var raw := delta / STICK_RADIUS
    var mag := raw.length()
    if mag <= STICK_DEADZONE:
        joystick_vector = Vector2.ZERO
    else:
        var scaled := clampf((mag - STICK_DEADZONE) / (1.0 - STICK_DEADZONE), 0.0, 1.0)
        # Smoothstep removes the twitch right outside the deadzone but still
        # reaches exact full-scale movement at the rim.
        scaled = scaled * scaled * (3.0 - 2.0 * scaled)
        joystick_vector = raw.normalized() * scaled
    move_changed.emit(joystick_vector)
    queue_redraw()

func _draw():
    if not enabled:
        return
    var sc := joystick_origin if joystick_touch >= 0 else stick_center()
    var fc := fire_center()
    var pc := pause_center()
    var t := pulse
    var top := dock_top()
    var dock_rect := Rect2(0.0, top, size.x, size.y - top)

    # Blank / dedicated control area below the real playfield.
    draw_rect(Rect2(0.0, PLAYFIELD_BOTTOM, size.x, 4.0), Color(0.65, 0.90, 1.0, 0.28), true)
    draw_rect(dock_rect, Color(0.01, 0.015, 0.035, 0.92), true)
    for i in range(12):
        var yy := top + 10.0 + float(i) * 20.0
        var line := Color.from_hsv(fposmod(t * 0.04 + float(i) * 0.07, 1.0), 0.9, 1.0, 0.08)
        draw_line(Vector2(18.0, yy), Vector2(size.x - 18.0, yy), line, 1.0)
    draw_line(Vector2(0.0, top + 2.0), Vector2(size.x, top + 2.0), Color(0.60, 0.95, 1.0, 0.22), 3.0)
    draw_line(Vector2(0.0, top + 8.0), Vector2(size.x, top + 8.0), Color(0.60, 0.95, 1.0, 0.08), 7.0)

    # Stick.  It floats to the initial thumb position while held.
    draw_circle(sc, STICK_RADIUS + 12.0, Color(0.0,0.0,0.0,0.44))
    draw_circle(sc, STICK_RADIUS, Color(0.02,0.14,0.21,0.32))
    draw_arc(sc, STICK_RADIUS, 0.0, TAU, 72, Color.from_hsv(fposmod(t * 0.06 + 0.52, 1.0), 0.95, 1.0, 0.78), 3.8)
    draw_arc(sc, STICK_RADIUS - 10.0, -t * 0.7, -t * 0.7 + PI * 1.45, 48, Color.from_hsv(fposmod(t * 0.08 + 0.84, 1.0), 0.95, 1.0, 0.34), 2.4)
    for a in [0.0, PI * 0.5, PI, PI * 1.5]:
        var p0 := sc + Vector2.from_angle(a) * (STICK_RADIUS - 24.0)
        var p1 := sc + Vector2.from_angle(a) * (STICK_RADIUS - 8.0)
        draw_line(p0, p1, Color(0.75, 0.96, 1.0, 0.40), 2.2)
    draw_circle(knob_pos, KNOB_RADIUS + 8.0, Color(0.0,0.0,0.0,0.52))
    draw_circle(knob_pos, KNOB_RADIUS, Color(0.05,0.42,0.68,0.44))
    draw_arc(knob_pos, KNOB_RADIUS, 0.0, TAU, 48, Color(0.78,0.98,1.0,0.92), 3.2)
    draw_circle(knob_pos, 9.0, Color(0.82,1.0,1.0,0.58))

    # Pause centered in blank dock.
    draw_circle(pc, PAUSE_RADIUS + 10.0, Color(0.0,0.0,0.0,0.40))
    draw_circle(pc, PAUSE_RADIUS, Color(0.03,0.18,0.27,0.34))
    draw_arc(pc, PAUSE_RADIUS, 0.0, TAU, 48, Color(0.55,0.92,1.0,0.72), 2.8)
    draw_rect(Rect2(pc + Vector2(-10,-14), Vector2(6,28)), Color(0.82,0.98,1.0,0.90), true)
    draw_rect(Rect2(pc + Vector2(4,-14), Vector2(6,28)), Color(0.82,0.98,1.0,0.90), true)

    # Fire.  The visible button stays centered, but its touch target is the
    # entire right-hand dock zone for reliable two-thumb play.
    var fire_scale := 1.0 + (0.055 if fire_down else 0.025) * sin(t * 7.0)
    var fr := FIRE_RADIUS * fire_scale
    draw_circle(fc, fr + 14.0, Color(0.0,0.0,0.0,0.44))
    draw_circle(fc, fr, Color(0.42,0.02,0.25,0.34 if not fire_down else 0.52))
    draw_arc(fc, fr, 0.0, TAU, 72, Color.from_hsv(fposmod(t * 0.09 + 0.92, 1.0), 0.92, 1.0, 0.96), 4.3)
    draw_arc(fc, fr - 12.0, t * 1.4, t * 1.4 + PI * 1.25, 48, Color(1.0,0.72,0.92,0.58), 2.4)
    draw_string(ThemeDB.fallback_font, fc + Vector2(-36.0, 10.0), "FIRE", HORIZONTAL_ALIGNMENT_CENTER, 72.0, 28, Color(1.0,0.92,0.98,0.98))

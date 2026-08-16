#!/usr/bin/env python3
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text()

def replace_once(old: str, new: str, label: str):
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly 1 match, got {count}")
    text = text.replace(old, new, 1)

replace_once(
'''var mobile_move := Vector2.ZERO
var mobile_fire_held := false
var player := Vector2(120, 240)''',
'''var mobile_move := Vector2.ZERO
var mobile_fire_held := false
var mobile_drag_active := false
var mobile_drag_pending := Vector2.ZERO
var player := Vector2(120, 240)''',
"mobile state vars")

replace_once(
'''    mobile_controls.move_changed.connect(_on_mobile_move)
    mobile_controls.fire_changed.connect(_on_mobile_fire)
    mobile_controls.pause_pressed.connect(_on_mobile_pause)
    mobile_controls.drag_target.connect(_on_mobile_drag)''',
'''    mobile_controls.move_changed.connect(_on_mobile_move)
    mobile_controls.fire_changed.connect(_on_mobile_fire)
    mobile_controls.pause_pressed.connect(_on_mobile_pause)
    mobile_controls.drag_delta.connect(_on_mobile_drag_delta)
    mobile_controls.drag_active_changed.connect(_on_mobile_drag_active)''',
"mobile signal connections")

replace_once(
'''        "MOBILE IN-GAME: LEFT STICK + DRAG • HOLD FIRE • PAUSE"''',
'''        "MOBILE: FLOATING STICK OR TRACKBALL DRAG • HOLD FIRE • PAUSE"''',
"mobile hint")

replace_once(
'''func read_controls():
    var move := Input.get_vector("move_left", "move_right", "move_up", "move_down", 0.16)
    if mobile_move.length() > move.length():
        move = mobile_move
    if move.length() > 0.05:
        # Analog magnitude is preserved so mobile stick and gamepad both retain fine control.
        player_target = player + move * (2.2 + 2.2 * move.length())

    if Input.is_action_pressed("fire") or mobile_fire_held:
        fire_requested = true
''',
'''func read_controls():
    var move := Input.get_vector("move_left", "move_right", "move_up", "move_down", 0.16)
    if not mobile_drag_active and mobile_move.length() > move.length():
        move = mobile_move

    if mobile_drag_active and mobile_drag_pending.length() > 0.01:
        # Consume relative touch motion once per source tick.  The target is
        # always based on the current player position, so drag cannot build up
        # a giant stale target behind a mushroom or after a WebKit touch jump.
        var drag_step := mobile_drag_pending
        mobile_drag_pending = Vector2.ZERO
        player_target = Vector2(
            clampf(player.x + drag_step.x, 4.0, 236.0),
            clampf(player.y + drag_step.y, PLAYER_TOP + 4.0, 248.0)
        )
    elif move.length() > 0.05:
        # Analog magnitude is preserved so floating mobile stick and gamepad
        # both retain fine control.
        player_target = player + move * (2.2 + 2.2 * move.length())

    if Input.is_action_pressed("fire") or mobile_fire_held:
        fire_requested = true
''',
"read_controls")

replace_once(
'''func _on_mobile_drag(screen_position: Vector2):
    if started and not paused_game:
        var logical := screen_to_logical(screen_position)
        player_target = Vector2(clamp(logical.x,4.0,236.0), clamp(logical.y,PLAYER_TOP+4.0,248.0))
''',
'''func _on_mobile_drag_delta(screen_delta: Vector2):
    if started and not paused_game:
        # Screen touch movement becomes trackball-like relative motion instead
        # of teleporting the player to the finger's absolute screen location.
        var logical_delta := Vector2(screen_delta.x / SX, screen_delta.y / SY) * 0.85
        mobile_drag_pending += logical_delta
        if mobile_drag_pending.length() > 14.0:
            mobile_drag_pending = mobile_drag_pending.normalized() * 14.0

func _on_mobile_drag_active(active: bool):
    mobile_drag_active = active
    if not active:
        mobile_drag_pending = Vector2.ZERO
        if started and not paused_game:
            player_target = player
''',
"mobile drag handler")

path.write_text(text)
print(f"patched {path}")

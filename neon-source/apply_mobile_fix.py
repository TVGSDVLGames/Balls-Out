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

# Mobile controls own only MOVE / FIRE / PAUSE.  The old drag_target signal is
# deliberately disconnected so touching the playfield cannot move the ship.
replace_once(
'''    mobile_controls.move_changed.connect(_on_mobile_move)
    mobile_controls.fire_changed.connect(_on_mobile_fire)
    mobile_controls.pause_pressed.connect(_on_mobile_pause)
    mobile_controls.drag_target.connect(_on_mobile_drag)''',
'''    mobile_controls.move_changed.connect(_on_mobile_move)
    mobile_controls.fire_changed.connect(_on_mobile_fire)
    mobile_controls.pause_pressed.connect(_on_mobile_pause)''',
"mobile signal connections")

# iOS/WebKit touch input is also converted by Godot into emulated mouse input.
# The old mouse branch moved player_target on any left press, which meant FIRE,
# PAUSE and unrelated touches could move/teleport the ship.  In mobile mode:
# - a real touch can start the game from attract/title
# - all gameplay ScreenTouch/ScreenDrag events are left to MobileControls
# - all mouse events are ignored by gameplay, including touch-emulated mouse
replace_once(
'''    if mobile_mode and (event is InputEventScreenTouch or event is InputEventScreenDrag):
        return

    if paused_game:
        return
''',
'''    if mobile_mode:
        if event is InputEventScreenTouch:
            if event.pressed and not started:
                start_game()
            return
        if event is InputEventScreenDrag or event is InputEventMouseButton or event is InputEventMouseMotion:
            return

    if paused_game:
        return
''',
"strict mobile input guard")

path.write_text(text)
print(f"patched {path}")

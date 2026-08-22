#!/usr/bin/env python3
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text()
root = path.parent.parent
project_path = root / "project.godot"

def replace_once(old: str, new: str, label: str):
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly 1 match, got {count}")
    text = text.replace(old, new, 1)

# Mobile controls own only MOVE / FIRE / PAUSE. The old drag_target signal is
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

# The physical arcade presentation is 3:4. Desktop/controller builds therefore
# use the full 768x1024 window. Mobile alone expands to 768x1280 so the extra
# 256 pixels are a dedicated control dock BELOW the untouched playfield.
replace_once(
'''    mobile_mode = OS.has_feature("mobile") or DisplayServer.is_touchscreen_available() or OS.get_cmdline_user_args().has("--mobile-preview")
    mobile_controls.set_controls_enabled(false)''',
'''    mobile_mode = OS.has_feature("mobile") or DisplayServer.is_touchscreen_available() or OS.get_cmdline_user_args().has("--mobile-preview")
    var target_viewport := Vector2i(768, 1280 if mobile_mode else 1024)
    get_window().content_scale_size = target_viewport
    if not OS.has_feature("web"):
        get_window().size = target_viewport
    mobile_controls.set_controls_enabled(false)''',
"adaptive desktop/mobile viewport")

# iOS/WebKit touch input is also converted by Godot into emulated mouse input.
# The old mouse branch moved player_target on any left press, which meant FIRE,
# PAUSE and unrelated touches could move/teleport the ship. In mobile mode:
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

# Default project window is now the actual 3:4 arcade presentation. Mobile
# expands at runtime after device detection. Also disable touch->mouse emulation
# at the project level as a second layer of protection for iOS/Web builds.
project = project_path.read_text()
for old, new, label in [
    ('window/size/viewport_height=1280', 'window/size/viewport_height=1024', 'desktop viewport height'),
    ('window/size/window_height_override=1280', 'window/size/window_height_override=1024', 'desktop override height'),
]:
    count = project.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly 1 match, got {count}")
    project = project.replace(old, new, 1)

if 'pointing/emulate_mouse_from_touch=' not in project:
    project = project.replace(
        'pointing/emulate_touch_from_mouse=true',
        'pointing/emulate_touch_from_mouse=true\npointing/emulate_mouse_from_touch=false',
        1,
    )
project_path.write_text(project)
print(f"patched {path} and {project_path}")

# ▶ Play Balls Out in Your Browser

## **[LAUNCH THE PLAYABLE BUILD →](https://rawcdn.githack.com/TVGSDVLGames/Balls-Out/191d400e72941c13a34c8a6f7adb6fb89ad2c36e/web/index.html)**

**No download or installation required.** Browser portfolio demo with controller support; the repository below tracks the current P51 Godot project.

---

# Balls Out

Controller-first 3D arcade/action prototype built in **Godot 4.7.1**. The player defends a barricade by physically throwing elemental bowling balls into advancing crowds, with quick throws, crowd-control effects, difficulty modes, two-player support, event cameras, and a performance-conscious presentation layer.

![Balls Out gameplay](docs/gameplay.png)

## Highlights

- Physics-driven bowling-ball combat with **Fire, Ice, and Acid** ball types.
- Fast **Quick Throw** for close-range pressure plus a longer pull-back / snap-up throw flow.
- Enemy waves, escalating pressure, barricade defense, and timed rounds.
- **1-player and 2-player** modes with controller-first input.
- **Easy / Normal / Hard** difficulty tuning.
- Permanent low-cost **Crowd Cam** picture-in-picture plus event shots for major moments.
- Ragdolls, impact effects, environmental dressing, snow, signage, and Milwaukee-inspired winter atmosphere.
- Godot **Jolt Physics** integration and multiple performance passes focused on responsiveness and stable frame pacing.
- Authored PBR material set with normal/roughness support and gameplay-distance readability tuning.

## Controls

The current in-game HUD is the source of truth for controller prompts. Core play uses left stick movement, D-pad aiming, triggers for the throw setup, right stick pull-back / snap-up, **A** for Quick Throw, **Y** for camera, and **Start** for pause.

## Running the project

1. Install **Godot 4.7.1**.
2. Import `project.godot`.
3. Run the main scene.

The project uses the Compatibility renderer and is tuned to keep rendering/physics overhead modest.

## Repository notes

This repository represents the **P51** development snapshot. Additional implementation notes are in `MATERIAL_PIPELINE.md`, `GITHUB_INTEGRATIONS.md`, `DEVELOPMENT_NOTES.txt`, and `THIRD_PARTY_NOTICES.md`.

## Project status

Active prototype / portfolio project. The focus is rapid gameplay iteration, controller feel, readable combat, scalable enemy pressure, and performance-aware Godot development.

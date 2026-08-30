# PASS7 N64 visual reference notes

Reference comparison used for this pass: GoldenEye 007, Turok 2, Shadow Man, Resident Evil 2 N64, plus Tiny3D/Fast64 material documentation.

Main diagnosis of PASS6:
- Geometry/fog are now N64-native, but most surfaces are vertex-color only.
- Commercial N64 games lean heavily on tiny filtered textures for faces, brick, cloth, metal and material breakup.
- Character identity should live partly in a small texture, not dozens of tiny geometric face pieces.
- Environments need a few large recognizable landmarks rather than only repeated corridor modules.
- N64 look benefits from bilinear filtered low-res texels, vertex lighting, fog, chunky silhouettes and restrained polygon counts.

PASS7 targets:
- Controlled hand-authored 32x32/64x64 PNG textures only; no borrowed/hidden texture references.
- Tiny3D TEX0*SHADE combiner, bilinear filtering, active fog.
- 64x64 textured curved Pennywise face patch with physical nose/hair retained.
- Authored sewer landmarks: maintenance alcove, ladder, valve pipe, channel grates, broken pipe.
- Keep 320x240, Tiny3D/RDPQ, folded cloth, curved arches and PASS6 lighting/fog.

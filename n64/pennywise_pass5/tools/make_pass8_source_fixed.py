#!/usr/bin/env python3
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
orig=ROOT/'tools/make_pass8_source.py'
s=orig.read_text()
start=s.index('light_anchor="""')
end=s.index('# Taller / leaner Pennywise', start)
replacement=r'''# PASS8 keeps PASS6's hardware point light at slot 1 and brightens it instead
# of colliding with it by installing a second directional light in the same slot.
if 't3d_light_set_exposure(1.08f);' not in c:
    raise SystemExit('PASS8 exposure anchor changed')
c=c.replace('t3d_light_set_exposure(1.08f);','t3d_light_set_exposure(1.35f);',1)
old_lamp='uint8_t lamp[4] = {(uint8_t)(142.0f*flick),(uint8_t)(132.0f*flick),(uint8_t)(92.0f*flick),255};'
new_lamp='uint8_t lamp[4] = {(uint8_t)(185.0f*flick),(uint8_t)(205.0f*flick),(uint8_t)(190.0f*flick),255};'
if old_lamp not in c:
    raise SystemExit('PASS8 point-light anchor changed')
c=c.replace(old_lamp,new_lamp,1)
'''
s=s[:start]+replacement+s[end:]
exec(compile(s,str(orig),'exec'), {'__name__':'__main__','__file__':str(orig)})

#!/usr/bin/env python3
import json, struct, sys

JSON_CHUNK = 0x4E4F534A

def read_glb(path):
    data = open(path, 'rb').read()
    magic, version, total = struct.unpack_from('<4sII', data, 0)
    if magic != b'glTF' or version != 2:
        raise RuntimeError(f'not GLB2: {path}')
    off = 12
    chunks = []
    json_index = None
    while off < total:
        length, typ = struct.unpack_from('<II', data, off)
        off += 8
        chunk = data[off:off+length]
        off += length
        if typ == JSON_CHUNK:
            json_index = len(chunks)
        chunks.append([typ, chunk])
    if json_index is None:
        raise RuntimeError(f'no JSON chunk: {path}')
    doc = json.loads(chunks[json_index][1].rstrip(b' \t\r\n\0').decode('utf8'))
    return doc, chunks, json_index

def write_glb(path, doc, chunks, json_index):
    raw = json.dumps(doc, separators=(',', ':'), ensure_ascii=False).encode('utf8')
    raw += b' ' * ((4 - len(raw) % 4) % 4)
    chunks[json_index][1] = raw
    body = b''.join(struct.pack('<II', len(chunk), typ) + chunk for typ, chunk in chunks)
    open(path, 'wb').write(struct.pack('<4sII', b'glTF', 2, 12 + len(body)) + body)

def shade_combiner():
    # Tiny3D importer enum: SHADE == 4.  (A-B)*C+D => SHADE.
    return {
        'name': '',
        'A': 0, 'B': 0, 'C': 0, 'D': 4,
        'A_alpha': 0, 'B_alpha': 0, 'C_alpha': 0, 'D_alpha': 4,
    }

def sanitize(path):
    doc, chunks, ji = read_glb(path)
    count = 0
    for mat in doc.get('materials', []):
        extras = mat.setdefault('extras', {})
        f3d = extras.get('f3d_mat')
        if not isinstance(f3d, dict):
            raise RuntimeError(f'{path}: material {mat.get("name")} has no f3d_mat')

        f3d['combiner1'] = shade_combiner()
        f3d['combiner2'] = shade_combiner()
        f3d['set_prim'] = 0
        f3d['set_env'] = 0
        f3d['set_blend'] = 0
        f3d['use_default_lighting'] = 1

        for key in ('tex0', 'tex1'):
            tex = f3d.get(key)
            if isinstance(tex, dict):
                tex['tex_set'] = 0
                tex['tex'] = None
                tex['use_tex_reference'] = 0
                tex.pop('tex_reference', None)
                tex.pop('tex_reference_size', None)

        rdp = f3d.get('rdp_settings')
        if isinstance(rdp, dict):
            rdp['g_shade'] = 1
            rdp['g_lighting'] = 1
            # Fast64 g_fog=1 maps to Tiny3D's active fog mode.  PASS6 then
            # supplies the actual range/color at runtime through t3d_fog_*.
            rdp['g_fog'] = 1
            rdp['g_tex_gen'] = 0
            rdp['g_tex_gen_linear'] = 0
            rdp['g_mdsft_cycletype'] = 0
            rdp['g_mdsft_text_filt'] = 0
            rdp['set_rendermode'] = 1
            rdp['rendermode_preset_cycle_1'] = 1  # Opaque
            rdp['rendermode_preset_cycle_2'] = 1

        draw = f3d.setdefault('draw_layer', {})
        draw['sm64'] = 1
        draw['oot'] = 0
        count += 1

    write_glb(path, doc, chunks, ji)
    # Make hidden texture regressions impossible to miss before conversion.
    after = open(path, 'rb').read().lower()
    for bad in (b'crate00', b'.ci8.png', b'.rgba16.png'):
        if bad in after:
            raise RuntimeError(f'{path}: hidden texture dependency remains: {bad!r}')
    print(f'SANITIZED {path}: {count} materials -> fogged SHADE/vertex-color pipeline')

if __name__ == '__main__':
    if len(sys.argv) < 2:
        raise SystemExit('usage: sanitize_materials.py file.glb [file.glb ...]')
    for p in sys.argv[1:]:
        sanitize(p)

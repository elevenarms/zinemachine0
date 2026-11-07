# Bake the AR assets for ar/index.html: one GLB (model-viewer, Android Scene Viewer / WebXR) and one USDZ
# (iOS AR Quick Look) per mode x colourway, in metres, Y up, true scale.
#   blender -b --factory-startup -P ar/tools/build_ar_assets.py -- [--src mech/blender] [--out ar/assets]
#           [--combos all|key,key] [--modes cover,open,beside,cradle] [--decimate 1.0]
# Inputs (read-only, from mech/blender_export.py): device.glb, tray.stl, lid.stl, poses.json; the colourways are
# read from the COMBOS dict in mech/blender/render_lid.py (parsed, not imported: that script renders on import).
# Import/pose handling follows render_lid.py. Each export is recentred: x/y centre at the origin, lowest point on
# z = 0 (the AR floor). Writes OUT/manifest.json with labels, colours and the measured bounding boxes.
import bpy, bmesh, ast, json, math, os, sys
from mathutils import Matrix, Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
def arg(name, default=None):
    return argv[argv.index(name) + 1] if name in argv else default
SRC = os.path.abspath(arg('--src', os.path.join(ROOT, 'mech', 'blender')))
OUT = os.path.abspath(arg('--out', os.path.join(ROOT, 'ar', 'assets')))
MODES = arg('--modes', 'cover,open,beside,cradle').split(',')
# Collapse-decimation ratio per part family (FreeCAD object-name prefix). Key legends are raised text and hold 65 % of
# the triangles; at 1-2 mm glyph size a quarter of them still reads. --decimate scales every ratio (1 = as below).
DECIMATE = float(arg('--decimate', '1.0'))
DEC_RATIOS = {'Legend': 0.25, 'Cap': 0.5, 'PB2': 0.4}
LID_ALPHA = float(arg('--lid-alpha', '0.55'))

# ---- colourways: COMBOS literal from render_lid.py ----
src = open(os.path.join(SRC, 'render_lid.py')).read()
COMBOS = None
for node in ast.parse(src).body:
    if isinstance(node, ast.Assign) and any(getattr(t, 'id', '') == 'COMBOS' for t in node.targets):
        COMBOS = ast.literal_eval(node.value)
assert COMBOS, 'COMBOS not found in render_lid.py'
keys = arg('--combos', 'all')
KEYS = list(COMBOS) if keys == 'all' else keys.split(',')
POSE_OF = {'cover': 'cover', 'open': 'cover', 'beside': 'beside', 'cradle': 'cradle'}   # open = cover pose, no lid
poses = json.load(open(os.path.join(SRC, 'poses.json')))

def srgb_to_lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
def hex_lin(h):
    h = h.lstrip('#'); return tuple(srgb_to_lin(int(h[i:i + 2], 16) / 255) for i in (0, 2, 4)) + (1.0,)
def mm_matrix(m):                      # mm pose matrix -> metres (as render_lid.py)
    M = Matrix(m); M[0][3] *= 0.001; M[1][3] *= 0.001; M[2][3] *= 0.001; return M

SMOOTH_ANGLE = math.radians(35)
def point_normals(o):
    # Weld, split edges sharper than SMOOTH_ANGLE, shade smooth with no custom normals: the mesh then has per-vertex
    # normals (normals_domain POINT), so USD gets 'vertex' normals instead of 'faceVarying' ones (~3x smaller).
    me = o.data
    if me.has_custom_normals:
        bpy.context.view_layer.objects.active = o
        bpy.ops.mesh.customdata_custom_splitnormals_clear()
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-7)
    sharp = [e for e in bm.edges if not e.is_manifold or (e.calc_face_angle(0.0) > SMOOTH_ANGLE)]
    bmesh.ops.split_edges(bm, edges=sharp)
    for f in bm.faces: f.smooth = True
    bm.to_mesh(me); bm.free()
    for a in ('sharp_edge', 'sharp_face'):
        if a in me.attributes: me.attributes.remove(me.attributes[a])
    print(o.name, 'normals domain', me.normals_domain, 'tris', sum(len(p.vertices) - 2 for p in me.polygons), flush=True)

# ---- scene ----
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.unit_settings.system = 'METRIC'; sc.unit_settings.scale_length = 1.0

bpy.ops.import_scene.gltf(filepath=os.path.join(SRC, 'device.glb'))
meshes = [o for o in bpy.data.objects if o.type == 'MESH']
for o in meshes:                       # bake parent transforms, decimate, then join all internals into one object
    M = o.matrix_world.copy(); o.parent = None; o.matrix_world = M
    r = DEC_RATIOS.get(o.name.split('_')[0], 1.0) * DECIMATE
    if r < 1.0 and len(o.data.polygons) > 40:
        if o.data.users > 1: o.data = o.data.copy()
        mod = o.modifiers.new('dec', 'DECIMATE'); mod.ratio = r
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.modifier_apply(modifier='dec')
for o in [o for o in bpy.data.objects if o.type == 'EMPTY']:
    bpy.data.objects.remove(o, do_unlink=True)
bpy.ops.object.select_all(action='DESELECT')
for o in meshes: o.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
bpy.ops.object.join()
dev = bpy.context.view_layer.objects.active; dev.name = 'Internals'; dev.data.name = 'Internals'
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
point_normals(dev)
for m in bpy.data.materials:           # FreeCAD flat colours: plastic finish (as render_lid.py)
    if m.use_nodes and 'Principled BSDF' in m.node_tree.nodes:
        m.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.5


def stl(name):
    bpy.ops.wm.stl_import(filepath=os.path.join(SRC, name + '.stl'), global_scale=0.001, forward_axis='Y', up_axis='Z')
    o = bpy.context.selected_objects[0]; o.name = name.capitalize(); o.data.name = name.capitalize()
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)   # mm -> m
    point_normals(o)
    return o
tray = stl('tray'); lid = stl('lid')

def principled(name):
    m = bpy.data.materials.new(name); m.use_nodes = True
    return m, m.node_tree.nodes['Principled BSDF']
tray_m, tray_b = principled('Tray')
lid_m, lid_b = principled('Lid')
tray.data.materials.append(tray_m); lid.data.materials.append(lid_m)
lid_b.inputs['Alpha'].default_value = LID_ALPHA
lid_b.inputs['Roughness'].default_value = 0.15
lid_b.inputs['IOR'].default_value = 1.49
if hasattr(lid_m, 'surface_render_method'): lid_m.surface_render_method = 'BLENDED'
if hasattr(lid_m, 'blend_method'):
    try: lid_m.blend_method = 'BLEND'
    except Exception: pass
def set_combo(k):
    _, th, te, lh = COMBOS[k]
    tray_b.inputs['Base Color'].default_value = hex_lin(th)
    tray_b.inputs['Roughness'].default_value = 0.42
    tray_b.inputs['Emission Color'].default_value = hex_lin(th)
    tray_b.inputs['Emission Strength'].default_value = te
    lid_b.inputs['Base Color'].default_value = hex_lin(lh)
    lid_b.inputs['Emission Color'].default_value = hex_lin(lh)
    lid_b.inputs['Emission Strength'].default_value = 0.05    # a hint of fluorescent edge glow

def set_mode(mode):
    p = poses[POSE_OF[mode]]
    D, L = mm_matrix(p['device']), mm_matrix(p['lid'])
    dev.matrix_world = D; tray.matrix_world = D; lid.matrix_world = L
    lid.hide_set(mode == 'open'); lid.hide_render = mode == 'open'
    objs = [dev, tray] + ([] if mode == 'open' else [lid])
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    lo = Vector((1e9,) * 3); hi = Vector((-1e9,) * 3)
    for o in objs:                     # exact vertex bbox (bound_box of a rotated object over-estimates)
        ev = o.evaluated_get(dg); W = o.matrix_world
        for v in ev.data.vertices:
            w = W @ v.co
            lo = Vector(map(min, lo, w)); hi = Vector(map(max, hi, w))
    T = Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z))
    dev.matrix_world = T @ D; tray.matrix_world = T @ D; lid.matrix_world = T @ L
    bpy.context.view_layer.update()
    return objs, (hi - lo)

def select(objs):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]

def usd_finish(usdc, usdz, lid_hex):
    """Post-process Blender's USD for AR Quick Look and package it as a .usdz.
    - Normals: Blender writes 'faceVarying' normals; the meshes were prepared so each vertex has exactly one normal
      (point_normals), so rewrite them as 'vertex' normals: a third of the size, identical shading.
    - Lid: make sure the UsdPreviewSurface carries the lid colour with opacity LID_ALPHA (Quick Look's translucency)."""
    from pxr import Usd, UsdGeom, UsdShade, UsdUtils, Sdf, Vt, Gf
    st = Usd.Stage.Open(usdc)
    for prim in st.Traverse():
        if prim.IsA(UsdGeom.Mesh):
            m = UsdGeom.Mesh(prim)
            n_attr = m.GetNormalsAttr()
            if m.GetNormalsInterpolation() == UsdGeom.Tokens.faceVarying:
                idx = m.GetFaceVertexIndicesAttr().Get(); nf = n_attr.Get()
                vn = [Gf.Vec3f(0, 0, 0)] * len(m.GetPointsAttr().Get())
                for c, vi in enumerate(idx): vn[vi] = nf[c]
                n_attr.Set(Vt.Vec3fArray(vn)); m.SetNormalsInterpolation(UsdGeom.Tokens.vertex)
        if prim.IsA(UsdShade.Shader):
            sh = UsdShade.Shader(prim)
            if sh.GetIdAttr().Get() == 'UsdPreviewSurface' and '/Lid' in str(prim.GetPath()):
                sh.CreateInput('opacity', Sdf.ValueTypeNames.Float).Set(LID_ALPHA)
                sh.CreateInput('diffuseColor', Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*hex_lin(lid_hex)[:3]))
                sh.CreateInput('roughness', Sdf.ValueTypeNames.Float).Set(0.15)
                sh.CreateInput('ior', Sdf.ValueTypeNames.Float).Set(1.49)
    # Export to a fresh crate file (saving in place appends to the old crate and keeps the stale normals).
    import tempfile, shutil
    d = tempfile.mkdtemp(); clean = os.path.join(d, os.path.basename(usdz)[:-5] + '.usdc')
    st.GetRootLayer().Export(clean)
    if os.path.exists(usdz): os.remove(usdz)
    ok = UsdUtils.CreateNewARKitUsdzPackage(Sdf.AssetPath(clean), usdz)
    assert ok, 'usdz packaging failed: ' + usdz
    os.remove(usdc); shutil.rmtree(d)

os.makedirs(OUT, exist_ok=True)
manifest = {'combos': {k: {'label': COMBOS[k][0], 'tray': COMBOS[k][1], 'lid': COMBOS[k][3]} for k in KEYS},
            'modes': MODES, 'size_mm': {}, 'files': {}}
for mode in MODES:
    objs, size = set_mode(mode)
    manifest['size_mm'][mode] = [round(size.x * 1000, 1), round(size.y * 1000, 1), round(size.z * 1000, 1)]  # W, D, H
    print(f'MODE {mode}: blender bbox (x,y,z) m = {size.x:.4f} {size.y:.4f} {size.z:.4f}', flush=True)
    for k in KEYS:
        set_combo(k); select(objs)
        base = os.path.join(OUT, f'{mode}_{k}')
        bpy.ops.export_scene.gltf(filepath=base + '.glb', export_format='GLB', use_selection=True, export_yup=True,
                                  export_apply=True, export_cameras=False, export_lights=False,
                                  export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=7,
                                  export_draco_position_quantization=16, export_draco_normal_quantization=8,
                                  export_texcoords=False)
        tmp = base + '.tmp.usdc'
        bpy.ops.wm.usd_export(filepath=tmp, selected_objects_only=True, export_materials=True,
                              generate_preview_surface=True, convert_orientation=True,
                              export_global_forward_selection='NEGATIVE_Z', export_global_up_selection='Y',
                              export_lights=False, export_cameras=False, export_uvmaps=False,
                              export_animation=False, triangulate_meshes=True, convert_world_material=False,
                              convert_scene_units='METERS', root_prim_path='/ZineMachine',
                              accessibility_label=f'Zine Machine, {COMBOS[k][0]}, {mode}')
        usd_finish(tmp, base + '.usdz', COMBOS[k][3])
        manifest['files'][f'{mode}_{k}'] = {'glb': os.path.basename(base) + '.glb',
                                            'usdz': os.path.basename(base) + '.usdz'}
        print('wrote', base, flush=True)
json.dump(manifest, open(os.path.join(OUT, 'manifest.json'), 'w'), indent=1)

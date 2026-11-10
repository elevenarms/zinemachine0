# Blender (5.x, Cycles) renders of the dual-use lid, from mech/blender_export.py's exports (device.glb, tray.stl,
# lid.stl, poses.json; all device frame, z up).
#   blender -b --factory-startup -P render_lid.py -- --out DIR [--scenes cover,beside,cradle] [--colors sienna,...]
#           [--refs both|on|off] [--samples 64] [--res 1600x1000] [--diagram]
# --diagram renders the five usage steps (one tray colour, shared camera) as step1..step5 for make_diagram.py.
# Scale references (when on): a standard poker deck (63.5 x 88.9 x 17 mm) and a ~190 mm banana.
import bpy, json, math, os, sys
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
def arg(name, default=None, flag=False):
    if flag: return name in argv
    return argv[argv.index(name) + 1] if name in argv else default
OUT = arg('--out', os.path.join(HERE, '..', 'renders', 'blender'))
SCENES = arg('--scenes', 'cover,beside,cradle').split(',')
REFS = arg('--refs', 'both')
SAMPLES = int(arg('--samples', '64'))
RES = tuple(int(v) for v in arg('--res', '1600x1000').split('x'))
DIAGRAM = arg('--diagram', flag=True)
LIGHT = float(arg('--light', '0.5'))
LID_GLOW = float(arg('--lid-glow', '0.07'))
TRAY_COLOURS = {                       # sRGB hex, emission (neon glow)
    'sienna': ('#A0522D', 0.0), 'neon_purple': ('#B026FF', 0.35), 'black': ('#141414', 0.0),
    'neon_green': ('#39FF14', 0.30), 'neon_blue': ('#1F51FF', 0.35)}
COLOURS = arg('--colors', ','.join(TRAY_COLOURS)).split(',')
# --combos: solid tray + matching translucent neon lid. key: (label, tray hex, tray emission, lid hex)
COMBOS = {
    'tangerine':  ('Bright orange / neon orange', '#FF6A13', 0.10, '#FF8C1A'),
    'grape':      ('Deep purple / atomic purple', '#3B1260', 0.00, '#8A4FFF'),
    'bubblegum':  ('Bubblegum',        '#FF3EA5', 0.10, '#FF7AD9'),
    'lime':       ('Lime',             '#6CC417', 0.08, '#B8FF3C'),
    'bondi':      ('Bondi',            '#00869E', 0.00, '#00D5F0'),
    'strawberry': ('Strawberry',       '#C8102E', 0.00, '#FF4060'),
    'chrome':     ('Chrome / ice',     '#B9BEC6', 0.00, '#D6F3FF'),
    'midnight':   ('Midnight / smoke', '#141414', 0.00, '#5A5A66'),
    'sienna':     ('Sienna / amber',   '#A0522D', 0.00, '#FFA640'),
    'terracotta': ('Terracotta / coral', '#C2603E', 0.00, '#FF8F6B'),
    'olive':      ('Olive / chartreuse', '#5A6B2E', 0.00, '#B5E853'),
    'sand':       ('Sand / honey',     '#C8B48A', 0.00, '#FFD24D'),
    'walnut':     ('Walnut / root beer', '#5A3A22', 0.00, '#D98A3D'),
    'forest':     ('Forest / emerald', '#2E4F35', 0.00, '#3DDC84'),
    'slate':      ('Slate / sea glass', '#5E6670', 0.00, '#6FE3D6')}
COMBO_KEYS = [k for k in arg('--combos', '').split(',') if k] if '--combos' in argv else []
if arg('--combos') == 'all': COMBO_KEYS = list(COMBOS)
os.makedirs(OUT, exist_ok=True)
poses = json.load(open(os.path.join(HERE, 'poses.json')))

def srgb_to_lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
def hex_lin(h):
    h = h.lstrip('#'); return tuple(srgb_to_lin(int(h[i:i + 2], 16) / 255) for i in (0, 2, 4)) + (1.0,)
def mm_matrix(m):                      # mm pose matrix -> metres
    M = Matrix(m); M[0][3] *= 0.001; M[1][3] *= 0.001; M[2][3] *= 0.001; return M

def material(name, rgba, rough=0.45, metal=0.0, transmission=0.0, emission=0.0, ior=1.5, coat=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = rgba
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    b.inputs['Transmission Weight'].default_value = transmission
    b.inputs['IOR'].default_value = ior
    b.inputs['Coat Weight'].default_value = coat
    if emission:
        b.inputs['Emission Color'].default_value = rgba
        b.inputs['Emission Strength'].default_value = emission
    return m

# ---------------- scene ----------------
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = 'CYCLES'
prefs = bpy.context.preferences.addons['cycles'].preferences
prefs.compute_device_type = 'METAL'; prefs.get_devices()
for d in prefs.devices: d.use = d.type == 'METAL'
sc.cycles.device = 'GPU'
sc.cycles.samples = SAMPLES
sc.cycles.use_denoising = True
sc.cycles.transmission_bounces = 12; sc.cycles.max_bounces = 16
sc.render.resolution_x, sc.render.resolution_y = RES
sc.render.film_transparent = False
sc.view_settings.view_transform = 'AgX'
sc.view_settings.look = 'AgX - Medium High Contrast'
world = bpy.data.worlds.new('World'); sc.world = world; world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.045, 0.047, 0.052, 1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value = 1.0

# device (internals with their FreeCAD colours) under one empty
bpy.ops.import_scene.gltf(filepath=os.path.join(HERE, 'device.glb'))
dev = bpy.data.objects.new('Device', None); sc.collection.objects.link(dev)
for o in list(bpy.data.objects):
    if o.type == 'MESH' and o.parent is None:
        o.parent = dev
    elif o.type == 'EMPTY' and o is not dev and o.parent is None:
        o.parent = dev
for m in bpy.data.materials:           # FreeCAD exports flat colours: give them a plastic finish
    if m.use_nodes and 'Principled BSDF' in m.node_tree.nodes:
        m.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.5
def stl(name):
    bpy.ops.wm.stl_import(filepath=os.path.join(HERE, name + '.stl'), global_scale=0.001, forward_axis='Y', up_axis='Z')
    o = bpy.context.selected_objects[0]; o.name = name
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)   # bake mm -> m (poses set matrix_world)
    bpy.ops.object.shade_auto_smooth(angle=math.radians(35))
    return o
tray = stl('tray'); tray.parent = dev
lid = stl('lid')
lid.data.materials.append(material('Lid', (0.82, 0.95, 1.0, 1), rough=0.06, transmission=1.0, ior=1.49))
tray_mats = {k: material('Tray_' + k, hex_lin(h), rough=0.42 if k != 'black' else 0.5, emission=e, coat=0.15)
             for k, (h, e) in TRAY_COLOURS.items()}
tray.data.materials.append(tray_mats[COLOURS[0]])

# floor + lights
bpy.ops.mesh.primitive_plane_add(size=6, location=(0.05, 0.05, 0))
floor = bpy.context.object; floor.name = 'Floor'
floor.data.materials.append(material('Floor', (0.075, 0.075, 0.08, 1), rough=0.6))
def area(name, loc, size, power, rgb=(1, 1, 1)):
    l = bpy.data.lights.new(name, 'AREA'); l.size = size; l.energy = power; l.color = rgb
    o = bpy.data.objects.new(name, l); sc.collection.objects.link(o); o.location = loc
    o.rotation_euler = (Vector((0.09, 0.07, 0.0)) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    return o
area('Key', (-0.25, -0.35, 0.45), 0.45, LIGHT * 26)
area('Fill', (0.45, -0.25, 0.25), 0.6, LIGHT * 9, (0.92, 0.95, 1.0))
area('Rim', (0.10, 0.55, 0.35), 0.5, LIGHT * 16, (1.0, 0.96, 0.9))

# ---------------- scale references ----------------
refs = []
def deck(loc, yaw):
    bpy.ops.mesh.primitive_cube_add(size=1)
    b = bpy.context.object; b.name = 'Deck'; b.scale = (0.0635, 0.0889, 0.017)
    bpy.ops.object.transform_apply(scale=True)
    bev = b.modifiers.new('round', 'BEVEL'); bev.width = 0.0028; bev.segments = 6; bev.limit_method = 'ANGLE'
    b.data.materials.append(material('Card_edges', (0.86, 0.85, 0.80, 1), rough=0.55))
    bpy.ops.mesh.primitive_plane_add(size=1)
    t = bpy.context.object; t.name = 'Card_back'; t.scale = (0.0635 - 0.008, 0.0889 - 0.008, 1)
    t.location = (0, 0, 0.0086); t.data.materials.append(material('Card_red', hex_lin('#B3202A'), rough=0.35))
    t.parent = b
    b.location = (loc[0], loc[1], 0.0085); b.rotation_euler = (0, 0, math.radians(yaw))
    refs.extend([b, t])
def banana(loc, yaw):
    cu = bpy.data.curves.new('Banana', 'CURVE'); cu.dimensions = '3D'
    sp = cu.splines.new('BEZIER'); sp.bezier_points.add(2)
    pts = [(-0.092, 0.0, 0.017), (0.0, 0.022, 0.019), (0.092, 0.0, 0.017)]
    for p, c in zip(sp.bezier_points, pts):
        p.co = c; p.handle_left_type = p.handle_right_type = 'AUTO'
    cu.bevel_depth = 0.0175; cu.bevel_resolution = 1; cu.resolution_u = 24; cu.use_fill_caps = True
    tp = bpy.data.curves.new('Taper', 'CURVE'); ts = tp.splines.new('BEZIER'); ts.bezier_points.add(4)
    for p, (x, y) in zip(ts.bezier_points, [(0, 0.25), (0.15, 0.85), (0.5, 1.0), (0.85, 0.85), (1, 0.3)]):
        p.co = (x, y, 0); p.handle_left_type = p.handle_right_type = 'AUTO'
    taper = bpy.data.objects.new('BananaTaper', tp); sc.collection.objects.link(taper); taper.hide_render = True
    cu.taper_object = taper
    o = bpy.data.objects.new('Banana', cu); sc.collection.objects.link(o)
    o.data.materials.append(material('Banana', hex_lin('#F2C230'), rough=0.5))
    for x, z, r, col, name in ((-0.096, 0.017, 0.0045, '#5A3A1A', 'Stem'), (0.094, 0.017, 0.004, '#2B2014', 'Tip')):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=(x, 0, z)); s = bpy.context.object; s.name = name
        s.scale = (1.8 if name == 'Stem' else 1, 1, 1); s.data.materials.append(material(name, hex_lin(col), rough=0.6))
        s.parent = o; refs.append(s)
    o.location = (loc[0], loc[1], 0.0); o.rotation_euler = (0, 0, math.radians(yaw))
    refs.append(o)
REF_LAYOUT = {'cover': ((-0.085, 0.045, 14), (0.075, -0.055, -4)),
              'cradle': ((-0.085, 0.045, 14), (0.075, -0.055, -4)),
              'beside': ((-0.085, 0.045, 14), (0.175, -0.060, 3))}
deck((0, 0), 0); banana((0, 0), 0)
def show_refs(scene_name, on):
    for o in refs: o.hide_render = not on
    if on:
        (dx, dy, dyaw), (bx, by, byaw) = REF_LAYOUT.get(scene_name, REF_LAYOUT['cover'])
        d = bpy.data.objects['Deck']; d.location.x, d.location.y = dx, dy; d.rotation_euler.z = math.radians(dyaw)
        b = bpy.data.objects['Banana']; b.location.x, b.location.y = bx, by; b.rotation_euler.z = math.radians(byaw)

# ---------------- camera ----------------
cam = bpy.data.objects.new('Camera', bpy.data.cameras.new('Camera')); sc.collection.objects.link(cam); sc.camera = cam
cam.data.lens = 55; cam.data.clip_start = 0.01; cam.data.clip_end = 20
def frame(objs, direction=(-0.62, -1.0, 0.72), pad=1.07):
    bpy.context.view_layer.update()
    pts = []
    for o in objs:
        if o.type in ('MESH', 'CURVE') and not o.hide_render:
            pts += [o.matrix_world @ Vector(c) for c in o.bound_box]
    d = Vector(direction).normalized()
    cam.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
    bpy.context.view_layer.update()
    loc, _scale = cam.camera_fit_coords(bpy.context.evaluated_depsgraph_get(), [c for p in pts for c in p])
    centre = sum(pts, Vector()) / len(pts)
    cam.location = centre + (Vector(loc) - centre) * pad

def set_pose(name):
    p = poses[name]
    dev.matrix_world = mm_matrix(p['device'])
    lid.matrix_world = mm_matrix(p['lid'])

def subject():
    return [o for o in bpy.data.objects if o.type == 'MESH' and o.name != 'Floor' and not o.hide_render] + \
           [o for o in refs if not o.hide_render]

OPEN = arg('--open', flag=True)
def render(path):
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print('wrote', path, flush=True)
    if OPEN:
        import subprocess; subprocess.Popen(['open', path])

def lid_material(hexcol):           # translucent neon acrylic: tinted transmission + a little fluorescent glow
    return material('Lid_' + hexcol, hex_lin(hexcol), rough=0.10, transmission=1.0, ior=1.49, emission=LID_GLOW)

POSTER = arg('--poster')          # combo key: render the kickflip strobe stages (transparent film, shadow catcher)
CATALOG = arg('--catalog')        # 'all' or combo keys: catalog shots on seamless white (make_catalog.py lays them out)
CATALOG_VIEWS = [  # (file, pose, camera direction, pad)
    ('hero', 'cover', (-0.80, -1.0, 0.78), 1.22),
    ('open', 'beside', (-0.30, -1.0, 0.95), 1.14),
    ('cradle', 'cradle', (-0.95, -1.0, 0.50), 1.22)]
def white_studio(cx):              # transparent film over a shadow catcher; big soft lights over x around cx
    floor.is_shadow_catcher = True; floor.scale = (8, 8, 1)
    sc.render.film_transparent = True
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.92, 0.93, 0.95, 1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.55
    for n in ('Key', 'Fill', 'Rim'):
        if n in bpy.data.objects: bpy.data.objects.remove(bpy.data.objects[n], do_unlink=True)
    def soft(name, loc, size, power):
        l = bpy.data.lights.new(name, 'AREA'); l.size = size; l.energy = power
        o = bpy.data.objects.new(name, l); sc.collection.objects.link(o); o.location = loc
        o.rotation_euler = (Vector((cx, 0.07, 0.02)) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    soft('Key', (cx - 0.35, -0.55, 1.25), 1.4, 75 * LIGHT * 2)
    soft('Fill', (cx + 0.55, -0.85, 0.85), 1.4, 32 * LIGHT * 2)
    soft('Rim', (cx, 0.95, 1.0), 1.2, 38 * LIGHT * 2)
VIEWS = arg('--views')            # 'all' or combo keys: iso/top/front/back/left/right, cover on and off (make_views.py)
MIX = arg('--mixmatch', flag=True)  # every tray x every lid (+ cover off) on a turntable (make_mixmatch.py)
D90 = math.pi / 2
ORTHO_VIEWS = {'top': (0, 0, 0), 'front': (D90, 0, 0), 'back': (D90, 0, 2 * D90),   # camera eulers: looks -Z
               'left': (D90, 0, -D90), 'right': (D90, 0, D90)}
ORTHO_SCALE = 0.20                 # metres across the frame for every flat view: one shared px/mm, views line up
_mats = {}
def tray_mat(k):
    if ('t', k) not in _mats:
        _, th, te, _ = COMBOS[k]; _mats[('t', k)] = material('Tray_' + k, hex_lin(th), rough=0.38, emission=te, coat=0.25)
    return _mats[('t', k)]
def lid_mat(k):
    if ('l', k) not in _mats: _mats[('l', k)] = lid_material(COMBOS[k][3])
    return _mats[('l', k)]
def world_pts(objs):
    bpy.context.view_layer.update()
    return [o.matrix_world @ Vector(c) for o in objs if o.type in ('MESH', 'CURVE') and not o.hide_render
            for c in o.bound_box]
if VIEWS:
    keys = list(COMBOS) if VIEWS == 'all' else VIEWS.split(',')
    show_refs('cover', False); white_studio(0.09)
    sc.render.resolution_x = sc.render.resolution_y = RES[0]
    cam.data.type = 'ORTHO'
    set_pose('cover')
    for k in keys:
        tray.data.materials[0] = tray_mat(k); lid.data.materials[0] = lid_mat(k)
        for state in ('on', 'off'):
            lid.hide_render = state == 'off'
            d = os.path.join(OUT, k, state); os.makedirs(d, exist_ok=True)
            pts = world_pts(subject())
            centre = Vector([(min(p[i] for p in pts) + max(p[i] for p in pts)) / 2 for i in range(3)])
            floor.hide_render = False                          # iso: true isometric, with its contact shadow
            frame(subject(), direction=(-1, -1, 1), pad=1.0)
            fit_loc, fit_scale = cam.camera_fit_coords(bpy.context.evaluated_depsgraph_get(),
                                                       [c for p in pts for c in p])
            cam.data.ortho_scale = fit_scale * 1.12
            cam.location = Vector(fit_loc) + (Vector((-1, -1, 1)).normalized() * 1.0)
            render(os.path.join(d, 'iso.png'))
            floor.hide_render = True                           # flat views: clean silhouettes, shared scale
            cam.data.ortho_scale = ORTHO_SCALE
            for v, eul in ORTHO_VIEWS.items():
                cam.rotation_euler = eul; bpy.context.view_layer.update()
                look = cam.matrix_world.to_3x3() @ Vector((0, 0, -1))
                cam.location = centre - look * 1.0
                render(os.path.join(d, v + '.png'))
    lid.hide_render = False; floor.hide_render = False
elif MIX:
    import random
    show_refs('cover', False); white_studio(0.09)
    cam.data.lens = 70
    keys = list(COMBOS); rng = random.Random(7)
    seq = []                                               # (tray, lid or None): each tray bare, then all 15 lids
    for t in rng.sample(keys, len(keys)):
        seq.append((t, None)); seq += [(t, l) for l in rng.sample(keys, len(keys))]
    base_d, base_l = mm_matrix(poses['cover']['device']), mm_matrix(poses['cover']['lid'])
    c = Vector((0.0876, 0.0656, 0.0))
    spin = lambda a: Matrix.Translation(c) @ Matrix.Rotation(a, 4, 'Z') @ Matrix.Translation(-c)
    pts = []                                               # one fixed camera that holds every turntable angle
    for i in range(12):
        dev.matrix_world = spin(i * math.pi / 6) @ base_d; lid.matrix_world = spin(i * math.pi / 6) @ base_l
        pts += world_pts(subject())
    d = Vector((-0.80, -1.0, 0.78)).normalized(); cam.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
    bpy.context.view_layer.update()
    loc, _ = cam.camera_fit_coords(bpy.context.evaluated_depsgraph_get(), [x for p in pts for x in p])
    ctr = sum(pts, Vector()) / len(pts); cam.location = ctr + (Vector(loc) - ctr) * 1.05
    manifest = []
    for i, (t, l) in enumerate(seq):
        a = 2 * math.pi * i / len(seq)
        dev.matrix_world = spin(a) @ base_d; lid.matrix_world = spin(a) @ base_l
        tray.data.materials[0] = tray_mat(t); lid.hide_render = l is None
        if l: lid.data.materials[0] = lid_mat(l)
        f = os.path.join(OUT, f'f{i:03d}.png')
        if not os.path.exists(f): render(f)                # resumable
        manifest.append({'file': os.path.basename(f), 'tray': t, 'lid': l})
    json.dump(manifest, open(os.path.join(OUT, 'manifest.json'), 'w'), indent=0)
elif CATALOG:
    keys = list(COMBOS) if CATALOG == 'all' else CATALOG.split(',')
    show_refs('cover', False)
    white_studio(0.19)
    cam.data.lens = 70
    for k in keys:
        label, th, te, lh = COMBOS[k]
        tray.data.materials[0] = material('Tray_' + k, hex_lin(th), rough=0.38, emission=te, coat=0.25)
        lid.data.materials[0] = lid_material(lh)
        os.makedirs(os.path.join(OUT, k), exist_ok=True)
        for fname, pose_name, direction, pad in CATALOG_VIEWS:
            set_pose(pose_name)
            frame(subject(), direction=direction, pad=pad)
            render(os.path.join(OUT, k, fname + '.png'))
elif POSTER:
    # The lid is the board, the device the rider: cover on -> pop -> lid flips about its long (y) axis in front ->
    # comes round underneath -> device lands in it (cradle). Stages sit side by side along x like a strobe exposure;
    # each is rendered alone on a transparent film (make_poster.py composites them).
    info = poses['_info']
    XC_M, ZG_M = 0.0876, 0.0055                      # lid flip axis (case x 87.6, z 5.5 mm), metres
    label, th, te, lh = COMBOS[POSTER]
    tray.data.materials[0] = material('Tray_poster', hex_lin(th), rough=0.38, emission=te, coat=0.25)
    lid.data.materials[0] = lid_material(lh)
    show_refs('cover', False)
    floor.is_shadow_catcher = True
    sc.render.film_transparent = True
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.92, 0.93, 0.95, 1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.55
    SP = 0.190                                        # strobe spacing along x
    floor.scale = (8, 8, 1)                           # no visible floor edge in the shadow catcher
    cx = 3.0 * SP + 0.088                             # strip centre: big soft lights over the whole strip, none low
    for n in ('Key', 'Fill', 'Rim'):
        bpy.data.objects.remove(bpy.data.objects[n], do_unlink=True)
    def soft(name, loc, size, power):
        l = bpy.data.lights.new(name, 'AREA'); l.size = size; l.energy = power
        o = bpy.data.objects.new(name, l); sc.collection.objects.link(o); o.location = loc
        o.rotation_euler = (Vector((cx, 0.07, 0.02)) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    soft('Key', (cx - 0.35, -0.55, 1.25), 1.4, 75 * LIGHT * 2)
    soft('Fill', (cx + 0.55, -0.85, 0.85), 1.4, 32 * LIGHT * 2)
    soft('Rim', (cx, 0.95, 1.0), 1.2, 38 * LIGHT * 2)
    def lid_rel(theta, dx=0, dy=0, dz=0):             # lid relative to the device: flip theta about y through the axis
        return (Matrix.Translation((dx + XC_M, dy, dz + ZG_M)) @ Matrix.Rotation(math.radians(theta), 4, 'Y')
                @ Matrix.Translation((-XC_M, 0, -ZG_M)))
    def dev_m(i, z=0.0, tilt=0.0, roll=0.0):          # tilt about x (+ lifts the front), roll about y, through the middle
        c = Vector((0.0876, 0.0656, 0.0))
        return (Matrix.Translation((i * SP, 0, z)) @ Matrix.Translation(c) @ Matrix.Rotation(math.radians(-tilt), 4, 'X')
                @ Matrix.Rotation(math.radians(roll), 4, 'Y') @ Matrix.Translation(-c))
    rest_dev = mm_matrix(poses['cradle']['device'])
    stages = [  # (device matrix, lid matrix relative to the device): a big Pixar hop, the lid kickflips under at the apex
        (dev_m(0), lid_rel(0)),
        (dev_m(1, 0.070, 13, -4), lid_rel(32, dy=-0.060, dz=0.075)),
        (dev_m(2, 0.165, 9, -7), lid_rel(92, dy=-0.170, dz=0.055)),
        (dev_m(3, 0.205, 2, -4), lid_rel(142, dy=-0.120, dz=-0.055)),
        (dev_m(4, 0.165, -8, 3), lid_rel(178, dy=-0.020, dz=-0.045)),
        (dev_m(5, 0.060, -6, 2), lid_rel(180, dz=-0.012)),
        (Matrix.Translation((6 * SP, 0, 0)) @ rest_dev, lid_rel(180)),
    ]
    pts = []
    for dm, lm in stages:                             # one camera for every stage: fit their union
        dev.matrix_world = dm; lid.matrix_world = dm @ lm; bpy.context.view_layer.update()
        pts += [o.matrix_world @ Vector(c) for o in subject() for c in o.bound_box]
    cam.data.lens = 85
    d = Vector((-0.16, -1.0, 0.42)).normalized()   # lowish: the height of the hop reads
    cam.rotation_euler = d.to_track_quat('Z', 'Y').to_euler(); bpy.context.view_layer.update()
    loc, _ = cam.camera_fit_coords(bpy.context.evaluated_depsgraph_get(), [c for p in pts for c in p])
    centre = sum(pts, Vector()) / len(pts); cam.location = centre + (Vector(loc) - centre) * 1.16   # room for the feather
    os.makedirs(OUT, exist_ok=True)
    for i, (dm, lm) in enumerate(stages):
        dev.matrix_world = dm; lid.matrix_world = dm @ lm
        render(os.path.join(OUT, f'stage{i}.png'))
elif COMBO_KEYS:
    os.makedirs(OUT, exist_ok=True)
    scene_name = SCENES[0]
    set_pose(scene_name); show_refs(scene_name, REFS == 'on'); frame(subject())
    for k in COMBO_KEYS:
        label, th, te, lh = COMBOS[k]
        tray.data.materials[0] = material('Tray_' + k, hex_lin(th), rough=0.42, emission=te, coat=0.15)
        lid.data.materials[0] = lid_material(lh)
        render(os.path.join(OUT, f'{scene_name}_{k}.png'))
elif DIAGRAM:
    tray.data.materials[0] = tray_mats[COLOURS[0]]
    show_refs('cover', False)
    steps = ['step1_cover_on', 'step2_slide_off', 'step3_turn_over', 'step4_slide_on', 'step5_cradle']
    allpts = []
    for s in steps:                                   # one camera for all steps: fit the union of the poses
        set_pose(s); bpy.context.view_layer.update()
        allpts += [o.matrix_world @ Vector(c) for o in subject() for c in o.bound_box]
    helper = bpy.data.objects.new('fit', None)
    d = Vector((-0.62, -1.0, 0.62)).normalized()
    cam.rotation_euler = d.to_track_quat('Z', 'Y').to_euler(); bpy.context.view_layer.update()
    loc, _ = cam.camera_fit_coords(bpy.context.evaluated_depsgraph_get(), [c for p in allpts for c in p])
    centre = sum(allpts, Vector()) / len(allpts); cam.location = centre + (Vector(loc) - centre) * 1.04
    for s in steps:
        set_pose(s); render(os.path.join(OUT, s + '.png'))
elif SCENES == ['lineup']:
    # every tray colour, cover on, in an arc facing the camera. Device + lid are one collection instanced per unit;
    # each unit gets its own tray object (same mesh) carrying its colour.
    set_pose('cover')
    unit = bpy.data.collections.new('Unit')
    for o in [dev] + [o for o in dev.children_recursive if o is not tray] + [lid]:
        for c in list(o.users_collection): c.objects.unlink(o)
        unit.objects.link(o)
    sc.collection.children.link(unit)
    bpy.context.view_layer.layer_collection.children['Unit'].exclude = True
    tray.parent = None
    sc.collection.objects.unlink(tray) if tray.name in sc.collection.objects else None
    for c in list(tray.users_collection): c.objects.unlink(tray)
    centre = Matrix.Translation((-0.0876, -0.0656, 0.0))          # unit centre (case 87.6, 65.6 mm) to origin
    n, radius, spread = len(COLOURS), 0.70, 76.0
    units = []
    for i, c in enumerate(COLOURS):
        a = math.radians(-spread / 2 + spread * i / max(n - 1, 1))
        pos = Vector((radius * math.sin(a), radius * (1 - math.cos(a)) + 0.02, 0))
        M = Matrix.Translation(pos) @ Matrix.Rotation(a, 4, 'Z') @ centre
        e = bpy.data.objects.new(f'Unit_{c}', None); e.instance_type = 'COLLECTION'; e.instance_collection = unit
        sc.collection.objects.link(e); e.matrix_world = M
        t = bpy.data.objects.new(f'Tray_{c}', tray.data.copy()); sc.collection.objects.link(t)
        t.data.materials.clear(); t.data.materials.append(tray_mats[c]); t.matrix_world = M
        units.append(t)
    REF_LAYOUT['lineup'] = ((-0.075, -0.125, 8), (0.075, -0.135, -6))
    for refs_on in ([False, True] if REFS == 'both' else [REFS == 'on']):
        show_refs('lineup', refs_on)
        frame(units + [o for o in refs if not o.hide_render and o.type in ('MESH', 'CURVE')],
              direction=(0.0, -1.0, 0.62), pad=1.12)
        cam.location.z += 0.03                                    # trays fit; leave room for the lids above them
        render(os.path.join(OUT, f"lineup{'_scale' if refs_on else ''}.png"))
else:
    for scene_name in SCENES:
        set_pose(scene_name)
        for refs_on in ([False, True] if REFS == 'both' else [REFS == 'on']):
            show_refs(scene_name, refs_on)
            frame(subject())
            for c in COLOURS:
                tray.data.materials[0] = tray_mats[c]
                render(os.path.join(OUT, f"{scene_name}{'_scale' if refs_on else ''}_{c}.png"))

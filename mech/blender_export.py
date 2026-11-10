# Export the dual-use lid scenes for Blender (mech/blender/): device internals with their colours (device.glb),
# Tray_slide and the lid as STL (device frame, mm), and poses.json: for each named pose a 4x4 device matrix and a 4x4
# lid matrix (row-major, mm, world = matrix * device-frame point). Poses reuse cover_anim.py's pose(t), so the
# renders match the animation and the checked geometry.
# Run inside the FreeCAD GUI with MECH_DIR set (needs ImportGui for the coloured GLB).
import os, json, FreeCAD, FreeCADGui, Mesh, ImportGui
V = FreeCAD.Vector
OUT = os.path.join(MECH_DIR, 'blender'); os.makedirs(OUT, exist_ok=True)
FRAME0 = FRAME1 = 0                       # cover_anim.py: build/reuse the scene and pose(), render nothing
exec(open(os.path.join(MECH_DIR, 'cover_anim.py')).read())
__name__ = '__cover_anim__'
exec(open(os.path.join(MECH_DIR, 'cover_assembly.py')).read())   # tray, cover, CRADLE_PL, XC, ...
__name__ = '__main__'

def mat(pl):
    m = pl.toMatrix()
    return [[m.A11, m.A12, m.A13, m.A14], [m.A21, m.A22, m.A23, m.A24], [m.A31, m.A32, m.A33, m.A34], [0, 0, 0, 1]]

I = FreeCAD.Placement()
lid_c = cover.BoundBox.Center
beside = FreeCAD.Placement(V(0, 0, 0), FreeCAD.Rotation(V(0, 0, 1), -6), lid_c)          # yaw about its centre
beside.Base = beside.Base + V(co1 - co0 + 22, 18, -SKIRT_Z0)                             # to the right, on the table
poses = {'cover': (I, I), 'beside': (I, beside)}
for name, t in (('step1_cover_on', 0.0), ('step2_slide_off', 2.2), ('step3_turn_over', 4.0),
                ('step4_slide_on', 5.0), ('step5_cradle', 8.6)):
    poses[name] = pose(t)
poses['cradle'] = poses['step5_cradle']
json.dump({k: {'device': mat(d), 'lid': mat(l)} for k, (d, l) in poses.items()} |
          {'_info': {'units': 'mm', 'cradle_tilt_deg': CRADLE_ANGLE, 'tray_rgb': TRAY_COL, 'lid_rgb': COVER_COL}},
          open(os.path.join(OUT, 'poses.json'), 'w'), indent=1)

for s, n in ((tray, 'tray'), (cover, 'lid')):
    Mesh.Mesh(s.tessellate(0.02)).write(os.path.join(OUT, n + '.stl'))
src = FreeCAD.getDocument('zine_cover')
internals = [o for o in src.getObject('Internals').Group]
ImportGui.export(internals, os.path.join(OUT, 'device.glb'))
print('exported', len(internals), 'internal parts;', sorted(poses))

# Animation frames: the dual-use lid comes off the front, turns over side to side, and slides back on from the front
# underneath, so the device sits in the upturned lid (cradle mode) and settles at its resting tilt.
# Run inside the FreeCAD GUI in batches (each RPC call must stay short): set MECH_DIR, FRAME0, FRAME1 (frame range),
# then exec this file. The first call builds the 'zine_anim' document; frames go to OUT_DIR as frame_0000.png ...
import os, math, FreeCAD, FreeCADGui, Part
V = FreeCAD.Vector
FPS = 24
OUT_DIR = os.path.join(MECH_DIR, 'renders', 'anim_frames')
SIZE = (1280, 800)
OFF_Y = -150.0                  # lid slid this far forward when it is off
LIFT_Z = 32.0                   # device held this high while the lid goes on underneath
ARC_Z = 45.0                    # extra height of the lid's centre while it turns over
# timeline (s): (name, start, end)
TL = [('hold0', 0.0, 0.6), ('slide_off', 0.6, 2.2), ('lift', 2.2, 3.2), ('flip', 2.2, 4.0),
      ('slide_on', 4.2, 5.8), ('set_down', 6.0, 7.0), ('hold1', 7.0, 8.6)]
DURATION = TL[-1][2]
NFRAMES = int(round(DURATION * FPS))

def ease(u):
    u = min(max(u, 0.0), 1.0)
    return u * u * (3 - 2 * u)

def phase(name, t):
    _, a, b = next(p for p in TL if p[0] == name)
    return ease((t - a) / (b - a))

st = FreeCAD.__dict__.get('_zm_anim')
if st is None or 'zine_anim' not in FreeCAD.listDocuments():
    __name__ = '__cover_anim__'          # cover_assembly.py: helpers and rest pose only, no checks/exports
    exec(open(os.path.join(MECH_DIR, 'cover_assembly.py')).read())
    __name__ = '__main__'
    doc = make_doc('zine_anim', [('Tray_slide', tray, TRAY_COL, None), ('Cover', cover, COVER_COL, COVER_TRANSPARENCY)])
    table = doc.addObject('Part::Feature', 'Table'); table.Shape = Part.makeBox(520, 520, 1, V(-170, -260, -1))
    table.ViewObject.ShapeColor = (0.30, 0.30, 0.32); table.ViewObject.Transparency = 20
    table.ViewObject.Visibility = False            # not part of the camera fit
    dev = [o for o in doc.Objects if o.isDerivedFrom('Part::Feature') and o.Name not in ('Cover', 'Table')]
    st = dict(doc=doc.Name, dev=[(o.Name, FreeCAD.Placement(o.Placement)) for o in dev], c0=cover.BoundBox.Center,
              rest_z=CRADLE_PL.Base.z, rest_deg=CRADLE_ANGLE, xc=XC, zg=Z_G)
    # fixed camera from the front-left, low; fitted to the motion envelope via a temporary helper box
    d = V(-1.0, -0.55, 0.38); d.normalize()
    x = V(0, 0, 1).cross(d); x.normalize(); y = d.cross(x)
    m = FreeCAD.Matrix(x.x, y.x, d.x, 0, x.y, y.y, d.y, 0, x.z, y.z, d.z, 0, 0, 0, 0, 1)
    helper = doc.addObject('Part::Feature', 'Helper'); helper.Shape = Part.makeBox(190, 320, 95, V(-8, -170, -20))
    doc.recompute()
    from PySide import QtGui
    mw = FreeCADGui.getMainWindow()
    for w in mw.findChildren(QtGui.QMdiSubWindow):
        if w.windowTitle().startswith('zine_anim'): mw.centralWidget().setActiveSubWindow(w)
    v = FreeCADGui.getDocument(doc.Name).ActiveView
    v.setCameraType('Perspective'); v.setCameraOrientation(FreeCAD.Rotation(m)); v.fitAll()
    FreeCADGui.updateGui(); v.fitAll()
    st['camera'] = v.getCamera()
    doc.removeObject('Helper'); table.ViewObject.Visibility = True
    FreeCAD._zm_anim = st
    os.makedirs(OUT_DIR, exist_ok=True)

doc = FreeCAD.getDocument(st['doc'])
v = FreeCADGui.getDocument(st['doc']).ActiveView
v.setCamera(st['camera'])
cov = doc.getObject('Cover')
c0 = st['c0']
c_cradle = V(2 * st['xc'] - c0.x, c0.y, 2 * st['zg'] - c0.z)   # lid centre after turning over (device frame)

def pose(t):
    """(device placement, lid placement), both in the world."""
    s_lift, s_down = phase('lift', t), phase('set_down', t)
    dev = FreeCAD.Placement(V(0, 0, LIFT_Z * s_lift * (1 - s_down) + st['rest_z'] * s_down),
                            FreeCAD.Rotation(V(1, 0, 0), st['rest_deg'] * s_down))
    s_off, s_flip, s_on = phase('slide_off', t), phase('flip', t), phase('slide_on', t)
    if s_flip <= 0:
        return dev, FreeCAD.Placement(V(0, OFF_Y * s_off, 0), FreeCAD.Rotation())
    if s_flip < 1:                                   # turning over beside the device's front, in the device frame
        p = (c0 * (1 - s_flip) + c_cradle * s_flip) + V(0, OFF_Y, ARC_Z * math.sin(math.pi * s_flip))
        rot = FreeCAD.Rotation(V(0, 1, 0), 180 * s_flip)
    else:                                            # sliding on from the front, underneath
        p, rot = c_cradle + V(0, OFF_Y * (1 - s_on), 0), FreeCAD.Rotation(V(0, 1, 0), 180)
    lid = FreeCAD.Placement(); lid.Rotation = rot; lid.Base = p - rot.multVec(c0)
    return dev, dev.multiply(lid)

for f in range(FRAME0, min(FRAME1, NFRAMES)):
    dev, lid = pose(f / FPS)
    for n, p0 in st['dev']:
        doc.getObject(n).Placement = dev.multiply(p0)
    cov.Placement = lid
    FreeCADGui.updateGui()
    v.saveImage(os.path.join(OUT_DIR, 'frame_%04d.png' % f), SIZE[0], SIZE[1], 'Current')
print('frames', FRAME0, min(FRAME1, NFRAMES), 'of', NFRAMES)

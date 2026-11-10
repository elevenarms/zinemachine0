# Dual-use lid prototype (one part), two modes, both slid on from the FRONT (keyboard) edge toward the display:
#  COVER : a translucent stepped lid over the keys and display. Rails in grooves cut into thickened tray side walls; its
#          front wall is the end stop; its rear end is open (rear I/O usable).
#  CRADLE: turned over side to side (180 deg about the y axis), the same lid slides on underneath: the device sits inside
#          the upturned lid, usable. The display section's roof rises ROOF_RISE toward the rear, so upturned its
#          underside is one slope from front edge to rear edge and the device rests tilted, rear up.
#  The rails sit symmetric about the groove centre Z_G and the part is symmetric in x, so the rails fit both ways up.
#  Detent: finger F1 near the front of each side wall; its nub clicks into dimple D1 (cover) or D1c (cradle, the same
#  y at the mirrored height above the groove).
# Case coordinates as mech/zine_concept.py: x right, y to the rear, z up from the tray underside. Front faces -Y.
# Builds: tray (Tray_slide), cover (cover position), cover_cradle (cradle position, device frame, before settling).
# Run inside FreeCAD (GUI or freecadcmd): set MECH_DIR first, or run as a file.
import os, math, FreeCAD, Part
V = FreeCAD.Vector
try:
    MECH_DIR
except NameError:
    MECH_DIR = os.path.dirname(os.path.abspath(__file__))

# ---------------- parameters (mm) ----------------
L, W, R, H_WALL = 175.2, 131.2, 3.0, 12.5   # v3 tray
SIDE_ADD = 1.5                  # side walls thickened outward by this (tray becomes L + 3.0 wide)
GAP, T = 0.2, 1.6               # lid-to-tray clearance, lid wall thickness
GROOVE = (4.5, 6.5, 1.2)        # groove z0, z1, depth into the side wall
Z_G = (GROOVE[0] + GROOVE[1]) / 2   # flip height: the rails map onto themselves
RAIL_CLR = 0.2                  # rail clearance in the groove (top, bottom, groove floor)
SKIRT_Z0 = 0.5                  # side/front walls stop this far above the table in cover mode
Z_IN_LO = 16.5                  # underside over the keyboard: 0.6 above cap legends (15.9)
Z_IN_HI = 21.6                  # underside over the display at the step: 0.5 above the display chassis frame (21.1)
ROOF_RISE = 0.0                 # display bump top: flat, 0.5 above the display all the way back (carry protection first; cradle tilt was 4.4 deg at 5.0)
BUMP_X = (21.8, 150.2)          # display bump cavity x: display chassis (22.3..149.7) + 0.5 per side
BUMP_Y1 = W                     # the bump runs out the open rear end: the lid slides on from the front, so at every x its
                                # roof may never drop toward the rear (a low strip behind the bump would hit the chassis)
BUMP_R = 0.5                    # bump front corner radius in plan (cavity, within the 0.5 clearance; outer adds T)
STEP_Y = 70.9                   # front face of the step wall; inner face (72.5) clears the display chassis battery
                                # fence (y 73.2, top z 16.7) by 0.7; top key row (y <= 70.35) is under the low roof
LEAD_IN = (3.0, 0.7)            # groove mouth flare at both ends: length, flare per side
RAIL_TAPER = (3.0, 0.5)         # rail leading-end taper (the open end leads in both modes): length, inset
EDGE_R = 1.0                    # outer edge rounding (top perimeter, step, open-end roof edge)
SLOT = 0.6
F1 = dict(root=4.0, free=18.0, z0=SKIRT_Z0, z1=3.9)     # detent finger below the rail; bottom edge is the wall's free edge
N1 = dict(y=16.0, z0=1.2, z1=3.4)                       # its nub
NUB_R, NUB_PRO = 1.2, 0.6       # nub radius, protrusion past the lid's inner face (0.4 interference with the wall)
DIMPLE_R, DIMPLE_D, DIMPLE_PAD = 1.4, 0.7, 0.3          # dimple radius, depth, extra height above/below the nub
COVER_COL, COVER_TRANSPARENCY = (0.70, 0.95, 1.00), 60
TRAY_COL = (0.627, 0.322, 0.176)   # sienna brown #A0522D

XC = L / 2                       # symmetry plane
X0, X1 = -SIDE_ADD, L + SIDE_ADD # new tray outer x
gz0, gz1, gd = GROOVE
ci0, ci1 = X0 - GAP, X1 + GAP    # lid cavity x
co0, co1 = ci0 - T, ci1 + T      # lid outer x
cy0 = -GAP                       # cavity front (inner face of the front wall)
oy0 = cy0 - T
z_lo_top, z_hi_top = Z_IN_LO + T, Z_IN_HI + T

def box(x0, y0, z0, x1, y1, z1):
    return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))

def rrect(x0, y0, x1, y1, r, z0, z1):
    b = box(x0, y0, z0, x1, y1, z1)
    return b.makeFillet(r, [e for e in b.Edges if abs(e.Vertexes[0].Point.z - e.Vertexes[1].Point.z) > 1e-6])

def yz_prism(pts, x0, x1):       # prism from a y-z polygon, extruded x0..x1
    return Part.Face(Part.makePolygon([V(x0, y, z) for y, z in pts] + [V(x0, *pts[0])])).extrude(V(x1 - x0, 0, 0))

def both_sides(shp):             # shape on the left side + its mirror on the right
    return [shp, shp.mirror(V(XC, 0, 0), V(1, 0, 0))]

def xz_rect(x0, x1, z0, z1, y):
    return Part.makePolygon([V(x0, y, z0), V(x1, y, z0), V(x1, y, z1), V(x0, y, z1), V(x0, y, z0)])

def loft_xz(a, b, ya, yb):       # solid lofted between two x-z rectangles (x0, x1, z0, z1) at ya and yb
    return Part.makeLoft([xz_rect(*a, ya), xz_rect(*b, yb)], True)

def rail(x0, x1, z0, z1, y_tail, y_lead):
    tl, ti = RAIL_TAPER
    yt = y_lead - tl
    return box(x0, y_tail, z0, x1, yt, z1).fuse(loft_xz((x0, x1, z0, z1), (x0, x1 - ti, z0 + ti, z1 - ti), yt, y_lead))

def groove_lead_ins(gx0, gx1, z0, z1):   # flared mouths at y 0 and y W
    ll, fl = LEAD_IN
    mouth, throat = (gx0, gx1 + fl, z0 - fl, z1 + fl), (gx0, gx1, z0, z1)
    return [loft_xz(mouth, throat, -0.01, ll), loft_xz(throat, mouth, W - ll, W + 0.01)]

def dimple(y, z0, z1):           # cylindrical dimple in the tray's left outer wall (mirror for the right)
    return Part.makeCylinder(DIMPLE_R, z1 - z0 + 2 * DIMPLE_PAD, V(X0 + DIMPLE_D - DIMPLE_R, y, z0 - DIMPLE_PAD))

def to_cradle(shape):            # cover position -> cradle position: 180 deg about the y axis through (XC, Z_G)
    s = shape.copy(); s.rotate(V(XC, 0, Z_G), V(0, 1, 0), 180); return s

FLIP_Z = lambda z: 2 * Z_G - z

# ---------------- tray: thicker side walls, grooves, dimples ----------------
d = FreeCAD.openDocument(os.path.join(MECH_DIR, 'tray.FCStd'))
tray = d.Objects[0].Shape.copy(); FreeCAD.closeDocument(d.Name)
tray = tray.fuse(rrect(X0, 0, X1, W, R, 0, H_WALL).cut(rrect(0, 0, L, W, R, -1, H_WALL + 1)))
cuts = [box(X0 - 1, -1, gz0, X0 + gd, W + 1, gz1)] + groove_lead_ins(X0 - 1, X0 + gd, gz0, gz1)
cuts.append(dimple(N1['y'], N1['z0'], N1['z1']))                         # D1: cover mode
cuts.append(dimple(N1['y'], FLIP_Z(N1['z1']), FLIP_Z(N1['z0'])))         # D1c: cradle mode
for c in cuts:
    for s in both_sides(c):
        tray = tray.cut(s)
tray = tray.removeSplitter()
tray = tray.Solids[0] if len(tray.Solids) == 1 else tray   # unwrap a one-solid compound

# ---------------- lid ----------------
# Low roof (Z_IN_LO underside) everywhere; a raised, rounded "display bump" only over the display chassis, its top
# sloping up ROOF_RISE toward the rear and running out the open rear end. Everything else behind the keys (mode keys 15.6, PocketBeagle, rear I/O <= 14.4)
# sits under the low roof.
BIG = 400
bx0, bx1 = BUMP_X
by0, by1 = STEP_Y + T, BUMP_Y1                   # bump cavity y
slope = ROOF_RISE / (W - STEP_Y)                 # top slope from the step to the open rear end
z_bump_out = lambda y: z_hi_top + slope * (y - STEP_Y)
outer_low = rrect(co0, oy0, co1, BIG, R + GAP + T, SKIRT_Z0, z_lo_top).common(box(co0 - 1, oy0 - 1, SKIRT_Z0 - 1, co1 + 1, W, z_lo_top + 1))
bump_out = rrect(bx0 - T, STEP_Y, bx1 + T, W + 10, BUMP_R + T, z_lo_top - 1, z_hi_top + ROOF_RISE + 2).common(
    yz_prism([(STEP_Y - 1, z_lo_top - 1), (W, z_lo_top - 1), (W, z_bump_out(W)),
              (STEP_Y - 1, z_bump_out(STEP_Y - 1))], bx0 - T - 1, bx1 + T + 1))
outer = outer_low.fuse(bump_out).removeSplitter()
def _vertical(e):
    p, q = e.Vertexes[0].Point, e.Vertexes[-1].Point
    return abs(p.x - q.x) < 1e-6 and abs(p.y - q.y) < 1e-6
outer = outer.makeFillet(EDGE_R, [e for e in outer.Edges
                                  if min(v.Point.z for v in e.Vertexes) > z_lo_top - 1e-6 and not _vertical(e)])
cav_low = rrect(ci0, cy0, ci1, BIG, R + GAP, SKIRT_Z0 - 5, Z_IN_LO)
bump_in = rrect(bx0, by0, bx1, W + 20, BUMP_R, Z_IN_LO - 1, z_hi_top + ROOF_RISE + 2).common(
    yz_prism([(by0 - 1, Z_IN_LO - 1), (W + 10, Z_IN_LO - 1), (W + 10, z_bump_out(W + 10) - T),
              (by0 - 1, z_bump_out(by0 - 1) - T)], bx0 - 1, bx1 + 1))
cavity = cav_low.fuse(bump_in)
cover = outer.cut(cavity)
for s in both_sides(rail(ci0 - 0.01, X0 + gd - RAIL_CLR, gz0 + RAIL_CLR, gz1 - RAIL_CLR, cy0, W)):
    cover = cover.fuse(s)

def finger_slots(f):             # top slot + free-end slot; the bottom edge is the wall's free edge
    return [box(co0 - 1, f['root'], f['z1'], ci0 + 0.01, f['free'] + SLOT, f['z1'] + SLOT),
            box(co0 - 1, f['free'], f['z0'] - 1, ci0 + 0.01, f['free'] + SLOT, f['z1'] + SLOT)]

def nub(n):
    return Part.makeCylinder(NUB_R, n['z1'] - n['z0'], V(ci0 + NUB_PRO - NUB_R, n['y'], n['z0'])).common(
        box(ci0 - 0.05, n['y'] - 5, n['z0'] - 1, ci0 + 5, n['y'] + 5, n['z1'] + 1))

for c in finger_slots(F1):
    for s in both_sides(c):
        cover = cover.cut(s)
for s in both_sides(nub(N1)):
    cover = cover.fuse(s)
cover = cover.removeSplitter()
cover = cover.Solids[0] if len(cover.Solids) == 1 else cover
cover_cradle = to_cradle(cover)

lines = []
for n, s in (('Tray_slide', tray), ('Lid', cover)):
    bb = s.optimalBoundingBox()
    lines.append(f"{n}: valid {s.isValid()} solids {len(s.Solids)} volume {s.Volume/1000:.2f} cm3 "
                 f"bbox x {bb.XMin:.2f}..{bb.XMax:.2f} y {bb.YMin:.2f}..{bb.YMax:.2f} z {bb.ZMin:.2f}..{bb.ZMax:.2f}")
cb = cover_cradle.optimalBoundingBox()
lines.append(f"lid-tray overlap, cover mode: {cover.common(tray).Volume:.3f} mm3; cradle mode: {cover_cradle.common(tray).Volume:.3f} mm3")
lines.append(f"cradle mode (device frame): lid z {cb.ZMin:.2f}..{cb.ZMax:.2f}, front wall top {FLIP_Z(SKIRT_Z0):.1f} "
             f"(key tops 15.9); display bump x {bx0}..{bx1}, y to {by1}, top {z_hi_top:.1f} -> {z_hi_top + ROOF_RISE:.1f}")
COVER_REPORT = '\n'.join(lines)
print(COVER_REPORT)

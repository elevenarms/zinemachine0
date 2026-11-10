# Assembly views + checks for the dual-use lid (mech/cover.py), built from the v3 concept parts
# (mech/zine_concept.FCStd) with the tray swapped for Tray_slide.
#   zine_cover  : device + lid in cover position (Cover.Placement.Base.y < 0 slides it open)
#   zine_cradle : device sitting in the upturned lid, settled on the table (z 0) at its resting tilt
# Checks: interference in both modes against every part (keycap legends by height: the lid only moves along y),
# slide sweeps, gaps, and the cradle resting pose + stability (centre of mass over the supporting face).
# Run inside the FreeCAD GUI with MECH_DIR set. With __name__ == '__cover_anim__' only the helpers and rest pose run.
import os, math, FreeCAD, FreeCADGui, Part, Mesh
V = FreeCAD.Vector
exec(open(os.path.join(MECH_DIR, 'cover.py')).read())

src = FreeCAD.openDocument(os.path.join(MECH_DIR, 'zine_concept.FCStd'))
parts = [(o.Name, o.Shape.copy(), tuple(o.ViewObject.ShapeColor) if FreeCAD.GuiUp else None)
         for o in src.Objects if o.Name != 'Case' and hasattr(o, 'Shape')]

def moved(s, pl):                # shape with pl applied on top of its own placement
    if pl is None: return s
    c = s.copy(); c.Placement = pl.multiply(c.Placement); return c

def make_doc(name, extra, pl=None):
    if name in FreeCAD.listDocuments():
        FreeCAD.closeDocument(name)
    doc = FreeCAD.newDocument(name)
    grp = doc.addObject('App::DocumentObjectGroup', 'Internals')
    objs = []
    for n, s, c in parts:
        o = doc.addObject('Part::Feature', n); o.Shape = moved(s, pl); grp.addObject(o); objs.append((o, c, None))
    for n, s, c, tr in extra:
        o = doc.addObject('Part::Feature', n); o.Shape = moved(s, pl); objs.append((o, c, tr))
    doc.recompute()
    if FreeCAD.GuiUp:
        for o, c, tr in objs:
            if c: o.ViewObject.ShapeColor = c
            if tr: o.ViewObject.Transparency = tr
    return doc

# ---- mass (rough densities, g/cm3; solid stand-in boxes for hollow real parts are scaled down) ----
DENS = {'Main_PCB': 1.85, 'PB2_PCB': 1.85, 'PB2_': 1.5, 'Panel': 2.5, 'Display_chassis': 1.0, 'Battery': 2.0,
        'Battery_PCM': 1.5, 'Switch_': 1.0, 'Cap_': 0.6, 'Legend_': 0.0, 'Mode_switch': 1.0, 'Mode_key': 0.6}
LID_DENS = 1.27                  # PETG / PC ~1.2-1.3
def mass_com(items):
    m, my = 0.0, V(0, 0, 0)
    for n, s, rho in items:
        for sol in (s.Solids or [s]):
            mi = sol.Volume / 1000 * rho; m += mi; my = my + sol.CenterOfMass * mi
    return m, my * (1.0 / m)
dev_items = [(n, s, next((v for k, v in DENS.items() if n.startswith(k)), 1.2)) for n, s, c in parts] + [('Tray', tray, 1.2)]
M_DEV, COM_DEV = mass_com(dev_items)
M_LID, COM_LID_CRADLE = mass_com([('Lid', cover_cradle, LID_DENS)])
COM_ALL = (COM_DEV * M_DEV + COM_LID_CRADLE * M_LID) * (1.0 / (M_DEV + M_LID))

# ---- cradle resting pose: lower convex hull of the y-z profile, the face the COM projects onto ----
def rest_pose(shapes, com):
    pts = []
    for s in shapes:
        pts += [(round(q[1], 3), round(q[2], 3)) for q in s.tessellate(0.1)[0]]
    pts = sorted(set(pts))
    hull = []
    for p in pts:                                   # Andrew's monotone chain, lower hull
        while len(hull) >= 2 and ((hull[-1][0] - hull[-2][0]) * (p[1] - hull[-2][1]) -
                                  (hull[-1][1] - hull[-2][1]) * (p[0] - hull[-2][0])) <= 0:
            hull.pop()
        hull.append(p)
    best = None
    for (y1, z1), (y2, z2) in zip(hull, hull[1:]):
        dy, dz = y2 - y1, z2 - z1; ln = math.hypot(dy, dz)
        if dy <= 0 or abs(dz) > dy: continue        # only faces it could rest on (flatter than 45 deg)
        t = ((com.y - y1) * dy + (com.z - z1) * dz) / ln
        if 0 <= t <= ln:
            best = dict(theta=math.degrees(math.atan2(-dz, dy)), p1=(y1, z1), p2=(y2, z2), margin=min(t, ln - t))
    th = math.radians(best['theta'])
    y1, z1 = best['p1']
    best['placement'] = FreeCAD.Placement(V(0, 0, -(y1 * math.sin(th) + z1 * math.cos(th))),
                                          FreeCAD.Rotation(V(1, 0, 0), best['theta']))
    best['hull'] = hull
    return best

REST = rest_pose([cover_cradle, tray], COM_ALL)
CRADLE_ANGLE = REST['theta']
CRADLE_PL = REST['placement']

def interferences(shape, tag, candidates):
    out, bb = [], shape.BoundBox
    for n, s in candidates:
        if s.BoundBox.intersect(bb):
            v = s.common(shape).Volume
            if v > 1e-3: out.append(f"CLASH {tag}: {n}: {v:.3f} mm3")
    return out

def sweep(shape, direction, against, travel):
    hits = []
    for off in range(5, int(travel) + 5, 5):
        m = shape.copy(); m.translate(direction * off)
        v = m.common(against).Volume
        if v > 1e-3: hits.append(f"{off}:{v:.2f}")
    return 'clear' if not hits else 'HITS ' + ' '.join(hits)

if __name__ != '__cover_anim__':
    rep = [COVER_REPORT]
    solid_parts = [(n, s) for n, s, c in parts if not n.startswith('Legend_')] + [('Tray_slide', tray)]
    leg_top = max(s.BoundBox.ZMax for n, s, c in parts if n.startswith('Legend_'))
    rep.append(f"legends: top z {leg_top:.2f} vs lid low roof underside {Z_IN_LO} -> {Z_IN_LO - leg_top:.2f} mm clear")
    rep += interferences(cover, 'cover mode', solid_parts) or ['cover mode: no interference with any part']
    rep += interferences(cover_cradle, 'cradle mode', solid_parts) or ['cradle mode: no interference with any part']
    tall = Part.makeCompound([s for n, s in solid_parts if s.BoundBox.ZMax > 12.5 or n == 'Tray_slide'])
    rep.append('cover-mode slide sweep (open by 5..%d mm): %s (nub rides the wall over the last %.0f mm)'
               % (int(W) + 5, sweep(cover, V(0, -1, 0), tall, W + 5), N1['y']))
    rep.append('cradle-mode slide sweep (open by 5..%d mm): %s (nub rides the wall over the last %.0f mm)'
               % (int(W) + 5, sweep(cover_cradle, V(0, -1, 0), tray, W + 5), N1['y']))
    caps = Part.makeCompound([s for n, s, c in parts if n.startswith('Cap_')])
    dsp = Part.makeCompound([s for n, s, c in parts if n.startswith(('Display_chassis', 'Panel', 'Mode_key'))])
    rep.append(f"min gap lid-keycaps {cover.distToShape(caps)[0]:.2f} mm; "
               f"lid-display chassis/panel/mode keys {cover.distToShape(dsp)[0]:.2f} mm")
    rep.append(f"cradle rest: tilt {CRADLE_ANGLE:.2f} deg (+ = rear up) on lid points y {REST['p1'][0]:.1f} and y {REST['p2'][0]:.1f} "
               f"(device frame); device ~{M_DEV:.0f} g + lid ~{M_LID:.0f} g, COM y {COM_ALL.y:.1f} z {COM_ALL.z:.1f}; "
               f"COM {REST['margin']:.1f} mm inside the nearer contact")
    flat = [p for p in REST['hull'] if True]
    rep.append(f"cradle underside: lower hull from ({flat[0][0]:.1f},{flat[0][1]:.1f}) to ({flat[-1][0]:.1f},{flat[-1][1]:.1f}), "
               f"{len(flat)} points; supporting face ({REST['p1'][0]:.1f},{REST['p1'][1]:.1f})-({REST['p2'][0]:.1f},{REST['p2'][1]:.1f})")
    open(os.path.join(MECH_DIR, 'cover.log'), 'w').write('\n'.join(rep) + '\n')
    print('\n'.join(rep))

    dc = make_doc('zine_cover', [('Tray_slide', tray, TRAY_COL, None), ('Cover', cover, COVER_COL, COVER_TRANSPARENCY)])
    dc.saveAs(os.path.join(MECH_DIR, 'zine_cover.FCStd'))
    dr = make_doc('zine_cradle', [('Tray_slide', tray, TRAY_COL, None), ('Lid_cradle', cover_cradle, COVER_COL, COVER_TRANSPARENCY)],
                  CRADLE_PL)
    dr.saveAs(os.path.join(MECH_DIR, 'zine_cradle.FCStd'))
    for s, n in ((cover, 'cover'), (tray, 'tray_slide')):
        s.exportStep(os.path.join(MECH_DIR, n + '.step'))
        Mesh.Mesh(s.tessellate(0.02)).write(os.path.join(MECH_DIR, n + '.stl'))

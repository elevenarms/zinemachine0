# Measure every exported AR asset and print its bounding box in millimetres, to prove true scale.
#   blender -b --factory-startup -P ar/tools/verify_ar_assets.py -- [--dir ar/assets] [--all]
# USDZ: pxr (bundled with Blender), exact bbox of every mesh point through its world transform, scaled by the stage's metersPerUnit; also
#       checks upAxis = Y and the lid's UsdPreviewSurface opacity.
# GLB:  re-imported into Blender (decodes Draco), exact vertex bbox; Blender's importer turns glTF Y-up into Z-up, so
#       it is reported back in glTF axes (x = width, y = height, z = depth; +z = front edge of the device).
# Without --all only the first colourway of each mode is measured (all colourways share geometry).
import bpy, json, os, sys
from mathutils import Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
D = os.path.abspath(argv[argv.index('--dir') + 1]) if '--dir' in argv else os.path.join(ROOT, 'ar', 'assets')
man = json.load(open(os.path.join(D, 'manifest.json')))
keys = list(man['combos'])
from pxr import Usd, UsdGeom, UsdShade

def usd_bbox(path):
    st = Usd.Stage.Open(path)
    mpu = UsdGeom.GetStageMetersPerUnit(st); up = UsdGeom.GetStageUpAxis(st)
    xc = UsdGeom.XformCache(Usd.TimeCode.Default())
    lo = [1e9] * 3; hi = [-1e9] * 3
    for p in st.Traverse():            # exact: every mesh point through its world transform
        if p.IsA(UsdGeom.Mesh):
            M = xc.GetLocalToWorldTransform(p)
            for q in UsdGeom.Mesh(p).GetPointsAttr().Get():
                w = M.Transform(q)
                lo = [min(a, b) for a, b in zip(lo, w)]; hi = [max(a, b) for a, b in zip(hi, w)]
    op = [UsdShade.Shader(p).GetInput('opacity').Get() for p in st.Traverse()
          if p.IsA(UsdShade.Shader) and '/Lid' in str(p.GetPath()) and UsdShade.Shader(p).GetInput('opacity')]
    k = mpu * 1000
    return up, mpu, [lo[i] * k for i in range(3)], [hi[i] * k for i in range(3)], op

def glb_bbox(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=path)
    bpy.context.view_layer.update()
    lo = Vector((1e9,) * 3); hi = Vector((-1e9,) * 3)
    for o in bpy.data.objects:
        if o.type == 'MESH':
            for v in o.data.vertices:
                w = o.matrix_world @ v.co; lo = Vector(map(min, lo, w)); hi = Vector(map(max, hi, w))
    # Blender Z-up (x, y, z) == glTF (x, -z, y): back to glTF axes, mm
    return [lo.x * 1000, lo.z * 1000, -hi.y * 1000], [hi.x * 1000, hi.z * 1000, -lo.y * 1000]

fmt = lambda v: '(' + ', '.join(f'{x:8.2f}' for x in v) + ')'
for mode in man['modes']:
    for k in (keys if '--all' in argv else keys[:1]):
        f = man['files'][f'{mode}_{k}']
        up, mpu, lo, hi, op = usd_bbox(os.path.join(D, f['usdz']))
        size = [h - l for l, h in zip(lo, hi)]
        print(f"USDZ {f['usdz']:28s} upAxis={up} metersPerUnit={mpu} min{fmt(lo)} max{fmt(hi)} "
              f"size W x H x D = {size[0]:.2f} x {size[1]:.2f} x {size[2]:.2f} mm  lid opacity={op}", flush=True)
        lo, hi = glb_bbox(os.path.join(D, f['glb']))
        size = [h - l for l, h in zip(lo, hi)]
        print(f"GLB  {f['glb']:28s} min{fmt(lo)} max{fmt(hi)} "
              f"size W x H x D = {size[0]:.2f} x {size[1]:.2f} x {size[2]:.2f} mm", flush=True)

# Usage diagram for the dual-use lid: composes the five Blender step renders (render_lid.py --diagram) into one
# labelled sheet. Usage: python3 make_diagram.py STEPS_DIR OUT.png TILT_DEG   (needs Pillow)
import os, sys
from PIL import Image, ImageDraw, ImageFont

steps_dir, out, tilt = sys.argv[1], sys.argv[2], float(sys.argv[3])
F = '/System/Library/Fonts/Supplemental/'
title_f = ImageFont.truetype(F + 'Arial Bold.ttf', 54)
sub_f = ImageFont.truetype(F + 'Arial.ttf', 28)
cap_f = ImageFont.truetype(F + 'Arial Bold.ttf', 30)
body_f = ImageFont.truetype(F + 'Arial.ttf', 26)
num_f = ImageFont.truetype(F + 'Arial Bold.ttf', 34)
BG, FG, DIM, ACC = (20, 21, 24), (236, 240, 244), (150, 158, 166), (160, 82, 45)   # accent: sienna

STEPS = [('step1_cover_on', 'Cover on', 'Protects the keys and the display.'),
         ('step2_slide_off', 'Slide it off the front', 'Pull the lid toward you; the detent releases.'),
         ('step3_turn_over', 'Turn it over', 'Flip the lid side to side; lift the device.'),
         ('step4_slide_on', 'Slide it on underneath', 'From the front again: the same rails ride the same grooves.'),
         ('step5_cradle', 'Set it down: cradle', f'The device sits in the lid at a {tilt:.1f}° typing tilt.')]
PW, PH = 760, 481                                  # panel size
M, GAP, CAP_H = 50, 80, 96
W = 2 * M + 3 * PW + 2 * GAP
TOP = 170
H = TOP + 2 * (PH + CAP_H) + 60 + 70
img = Image.new('RGB', (W, H), BG); d = ImageDraw.Draw(img)
d.text((M, 48), 'Zine Machine v3: one lid, two uses', font=title_f, fill=FG)
d.text((M, 116), 'Cover → cradle in four moves. Translucent lid, prototype geometry from mech/cover.py.',
       font=sub_f, fill=DIM)

def panel_xy(i):
    row, col = (0, i) if i < 3 else (1, i - 3)
    return M + col * (PW + GAP), TOP + row * (PH + CAP_H + 60)

def arrow(x0, y, x1):
    d.line([(x0, y), (x1 - 14, y)], fill=ACC, width=7)
    d.polygon([(x1, y), (x1 - 22, y - 15), (x1 - 22, y + 15)], fill=ACC)

for i, (name, cap, body) in enumerate(STEPS):
    x, y = panel_xy(i)
    im = Image.open(os.path.join(steps_dir, name + '.png')).convert('RGB').resize((PW, PH), Image.LANCZOS)
    img.paste(im, (x, y))
    d.rounded_rectangle([x, y, x + PW, y + PH], radius=14, outline=(60, 63, 70), width=3)
    d.ellipse([x + 18, y + 18, x + 72, y + 72], fill=ACC)
    n = str(i + 1); tw = d.textlength(n, font=num_f)
    d.text((x + 45 - tw / 2, y + 26), n, font=num_f, fill=(255, 255, 255))
    d.text((x, y + PH + 16), cap, font=cap_f, fill=FG)
    d.text((x, y + PH + 56), body, font=body_f, fill=DIM)
    if i in (0, 1, 3):
        arrow(x + PW + 12, y + PH // 2, x + PW + GAP - 12)

# row 1 -> row 2 connector (from step 3 down and back to step 4)
x3, y3 = panel_xy(2); x4, y4 = panel_xy(3)
yy = y3 + PH + CAP_H + 22
d.line([(x3 + PW // 2, y3 + PH + CAP_H - 6), (x3 + PW // 2, yy)], fill=ACC, width=7)
d.line([(x3 + PW // 2, yy), (x4 + PW // 2, yy)], fill=ACC, width=7)
d.line([(x4 + PW // 2, yy), (x4 + PW // 2, y4 - 16)], fill=ACC, width=7)
d.polygon([(x4 + PW // 2, y4 - 2), (x4 + PW // 2 - 15, y4 - 24), (x4 + PW // 2 + 15, y4 - 24)], fill=ACC)

# notes panel in the last slot
x, y = panel_xy(5)
d.rounded_rectangle([x, y, x + PW, y + PH], radius=14, fill=(30, 32, 36), outline=(60, 63, 70), width=3)
notes = ['How it works',
         '• Rails on the lid sit centred on the tray grooves,',
         '   so they fit either way up.',
         '• Both modes slide on from the front edge; the lid\'s',
         '   front wall is the stop. The rear stays open (ports).',
         '• One detent finger per side clicks into a dimple',
         '   below the groove (cover) or above it (cradle).',
         '• The display end of the roof rises 8 mm, so upturned',
         f'   it rests on its front and rear edges: {tilt:.1f}°, stable.']
for j, t in enumerate(notes):
    d.text((x + 30, y + 28 + j * 48), t, font=cap_f if j == 0 else body_f, fill=FG if j == 0 else (200, 206, 212))
img.save(out)
print('wrote', out, img.size)

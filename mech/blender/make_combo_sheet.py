# Contact sheet of tray / lid colour combos (render_lid.py --combos). Usage: python3 make_combo_sheet.py DIR OUT.png
import os, sys, re
from PIL import Image, ImageDraw, ImageFont
D, out = sys.argv[1], sys.argv[2]
SCENE = sys.argv[3] if len(sys.argv) > 3 else 'cover'
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'render_lid.py')).read()
COMBOS = re.findall(r"'(\w+)':\s*\('([^']+)',\s*'(#[0-9A-Fa-f]{6})',\s*[\d.]+,\s*'(#[0-9A-Fa-f]{6})'\)", src)
groups = [('Y2K', COMBOS[:8]), ('Earth tones', COMBOS[8:])]
F = '/System/Library/Fonts/Supplemental/'
title = ImageFont.truetype(F + 'Arial Bold.ttf', 52); head = ImageFont.truetype(F + 'Arial Bold.ttf', 34)
lab = ImageFont.truetype(F + 'Arial Bold.ttf', 26); small = ImageFont.truetype(F + 'Arial.ttf', 20)
TW, TH, COLS, M, G, CAP = 560, 350, 4, 50, 24, 74
rows = sum((len(c) + COLS - 1) // COLS for _, c in groups)
W = 2 * M + COLS * TW + (COLS - 1) * G
H = 150 + rows * (TH + CAP + G) + len(groups) * 60 + 30
img = Image.new('RGB', (W, H), (20, 21, 24)); d = ImageDraw.Draw(img)
d.text((M, 40), 'Zine Machine v3: tray + translucent lid colourways', font=title, fill=(236, 240, 244))
d.text((M, 104), 'Solid printed tray, matching translucent neon lid. ' + ('Cover mode, form-fitting lid.' if SCENE == 'cover' else 'Lid off, beside the device.'), font=small, fill=(150, 158, 166))
y = 150
def chip(x, y, hexcol):
    d.rounded_rectangle([x, y, x + 22, y + 22], radius=5, fill=hexcol, outline=(90, 94, 100))
for gname, combos in groups:
    d.text((M, y + 10), gname, font=head, fill=(236, 240, 244)); y += 60
    for i, (key, label, th, lh) in enumerate(combos):
        r, c = divmod(i, COLS)
        x, yy = M + c * (TW + G), y + r * (TH + CAP + G)
        img.paste(Image.open(os.path.join(D, f'{SCENE}_{key}.png')).convert('RGB').resize((TW, TH), Image.LANCZOS), (x, yy))
        d.text((x, yy + TH + 10), label, font=lab, fill=(236, 240, 244))
        chip(x, yy + TH + 44, th); d.text((x + 30, yy + TH + 44), f'tray {th}', font=small, fill=(170, 176, 184))
        chip(x + 200, yy + TH + 44, lh); d.text((x + 230, yy + TH + 44), f'lid {lh}', font=small, fill=(170, 176, 184))
    y += ((len(combos) + COLS - 1) // COLS) * (TH + CAP + G)
img.save(out); print('wrote', out, img.size, len(COMBOS), 'combos')

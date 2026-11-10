# Catalog cards for each tray / lid colourway (render_lid.py --catalog all -> DIR/<key>/{hero,open,cradle}.png, transparent)
# plus an index sheet. Usage: python3 make_catalog.py DIR OUTDIR   (Pillow)
import os, re, sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont
D, OUTD = sys.argv[1], sys.argv[2]; os.makedirs(OUTD, exist_ok=True)
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'render_lid.py')).read()
COMBOS = re.findall(r"'(\w+)':\s*\('([^']+)',\s*'(#[0-9A-Fa-f]{6})',\s*[\d.]+,\s*'(#[0-9A-Fa-f]{6})'\)", src)
FAMILY = {k: ('Y2K' if i < 8 else 'Earth tones') for i, (k, *_) in enumerate(COMBOS)}
HF = '/System/Library/Fonts/Supplemental/Hoefler Text.ttc'; AR = '/System/Library/Fonts/Supplemental/Arial.ttf'
F = lambda path, size: ImageFont.truetype(path, size, index=0) if path.endswith('.ttc') else ImageFont.truetype(path, size)
INK, GREY, RULE = (29, 29, 31), (120, 120, 126), (225, 225, 230)

def shot(path, size):           # transparent render -> cleaned alpha (no shadow-catcher veil) on white, fitted to size
    im = Image.open(path).convert('RGBA')
    a = im.getchannel('A').point(lambda v: max(0, int((v - 6) * 255 / 249)))
    m = int(min(im.size) * 0.06); mask = Image.new('L', im.size, 0)
    ImageDraw.Draw(mask).rectangle([m, m, im.width - m, im.height - m], fill=255)
    im.putalpha(Image.composite(a, Image.new('L', im.size, 0), mask.filter(ImageFilter.GaussianBlur(m * 0.6))))
    im.thumbnail(size, Image.LANCZOS)
    ox, oy = (size[0] - im.width) // 2, (size[1] - im.height) // 2
    out = Image.new('RGBA', size, (255, 255, 255, 255)); out.alpha_composite(im, (ox, oy))
    bb = im.getchannel('A').point(lambda v: 255 if v > 60 else 0).getbbox() or (0, 0, im.width, im.height)
    out.content_bottom = oy + bb[3]                    # where the visible product (with its contact shadow) ends
    return out

def swatch(d, x, y, hexcol, label, f):
    d.rounded_rectangle([x, y, x + 54, y + 54], radius=10, fill=hexcol, outline=(200, 200, 205), width=2)
    d.text((x + 72, y + 2), label, font=f, fill=INK); d.text((x + 72, y + 30), hexcol.upper(), font=F(AR, 22), fill=GREY)

heroes = []
for i, (k, label, th, lh) in enumerate(COMBOS):
    W, H = 2400, 1600
    card = Image.new('RGBA', (W, H), (255, 255, 255, 255)); d = ImageDraw.Draw(card)
    hero = shot(os.path.join(D, k, 'hero.png'), (1480, 1110)); card.alpha_composite(hero, (60, 70))
    o = shot(os.path.join(D, k, 'open.png'), (780, 560)); card.alpha_composite(o, (1570, 90))
    c = shot(os.path.join(D, k, 'cradle.png'), (780, 560)); card.alpha_composite(c, (1570, 680))
    d.text((1600, 90 + o.content_bottom + 14), 'Lid off', font=F(AR, 24), fill=GREY)
    d.text((1600, 680 + c.content_bottom + 14), 'Lid as cradle', font=F(AR, 24), fill=GREY)
    d.line([(60, 1270), (W - 60, 1270)], fill=RULE, width=2)
    d.text((60, 1300), label.split(' / ')[0] if ' / ' in label else label, font=F(HF, 104), fill=INK)
    d.text((64, 1438), f'Zine Machine  ·  {FAMILY[k]}  ·  No. {i + 1:02d}', font=F(AR, 28), fill=GREY)
    tray_name, lid_name = (label.split(' / ') + [label])[:2]
    swatch(d, 1250, 1318, th, f'Tray: {tray_name}', F(AR, 28))
    swatch(d, 1250, 1418, lh, f'Lid: {lid_name} (translucent)', F(AR, 28))
    d.text((1900, 1330), 'Printed tray', font=F(AR, 24), fill=GREY)
    d.text((1900, 1366), 'Translucent PETG / PC lid', font=F(AR, 24), fill=GREY)
    d.text((1900, 1402), 'Cover + cradle, one part', font=F(AR, 24), fill=GREY)
    card.convert('RGB').save(os.path.join(OUTD, f'{i + 1:02d}_{k}.png'))
    heroes.append((label, th, lh, shot(os.path.join(D, k, 'hero.png'), (620, 440))))
# index sheet
cols, tw, th_ = 5, 640, 440
rows = (len(heroes) + cols - 1) // cols
sheet = Image.new('RGBA', (cols * tw + 120, rows * (th_ + 60) + 230), (255, 255, 255, 255)); d = ImageDraw.Draw(sheet)
d.text((60, 50), 'Zine Machine colourways', font=F(HF, 84), fill=INK)
for i, (label, t, l, hero) in enumerate(heroes):
    r, c = divmod(i, cols); x, y = 60 + c * tw, 190 + r * (th_ + 60)
    sheet.alpha_composite(hero, (x, y)); cy = y + hero.content_bottom + 6
    d.rounded_rectangle([x + 10, cy, x + 40, cy + 30], radius=6, fill=t)
    d.rounded_rectangle([x + 46, cy, x + 76, cy + 30], radius=6, fill=l)
    d.text((x + 92, cy), label, font=F(AR, 26), fill=INK)
sheet.convert('RGB').save(os.path.join(OUTD, '00_index.png'))
print('wrote', len(heroes), 'cards + index to', OUTD)

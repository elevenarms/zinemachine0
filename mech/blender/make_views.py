# View sheets per colourway: iso + top/front/back/left/right, cover on and cover off
# (render_lid.py --views all -> DIR/<key>/{on,off}/{iso,top,front,back,left,right}.png, transparent).
# The flat views share one ortho scale (render_lid.ORTHO_SCALE across the frame), so they are placed at one px/mm and
# the dimension callouts are measured from the renders themselves. Usage: python3 make_views.py DIR OUTDIR   (Pillow)
import os, re, sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont
D, OUTD = sys.argv[1], sys.argv[2]; os.makedirs(OUTD, exist_ok=True)
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'render_lid.py')).read()
COMBOS = re.findall(r"'(\w+)':\s*\('([^']+)',\s*'(#[0-9A-Fa-f]{6})',\s*[\d.]+,\s*'(#[0-9A-Fa-f]{6})'\)", src)
ORTHO_MM = float(re.search(r'ORTHO_SCALE = ([\d.]+)', src).group(1)) * 1000
HF = '/System/Library/Fonts/Supplemental/Hoefler Text.ttc'; AR = '/System/Library/Fonts/Supplemental/Arial.ttf'
F = lambda path, size: ImageFont.truetype(path, size, index=0) if path.endswith('.ttc') else ImageFont.truetype(path, size)
INK, GREY, RULE, DIM = (29, 29, 31), (120, 120, 126), (225, 225, 230), (150, 150, 158)
K = 5.0                                         # sheet px per mm for the flat views

def clean(path, veil=6):                        # drop the shadow catcher's near-zero alpha veil
    im = Image.open(path).convert('RGBA')
    im.putalpha(im.getchannel('A').point(lambda v: max(0, int((v - veil) * 255 / (255 - veil)))))
    return im

def flat(path):                                 # ortho view cropped to its silhouette, scaled to K px/mm
    im = clean(path); s = K * ORTHO_MM / im.width
    im = im.crop(im.getchannel('A').point(lambda v: 255 if v > 20 else 0).getbbox())
    return im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)

def iso(path, box):
    im = clean(path); m = int(min(im.size) * 0.05); mask = Image.new('L', im.size, 0)
    ImageDraw.Draw(mask).rectangle([m, m, im.width - m, im.height - m], fill=255)
    im.putalpha(Image.composite(im.getchannel('A'), Image.new('L', im.size, 0), mask.filter(ImageFilter.GaussianBlur(m))))
    im = im.crop(im.getchannel('A').point(lambda v: 255 if v > 12 else 0).getbbox())
    f = min(box[0] / im.width, box[1] / im.height)
    return im.resize((round(im.width * f), round(im.height * f)), Image.LANCZOS)

def dim_h(d, x0, x1, y, text, f):               # horizontal dimension line with end ticks, label centred above
    d.line([(x0, y), (x1, y)], fill=DIM, width=2)
    for x in (x0, x1): d.line([(x, y - 9), (x, y + 9)], fill=DIM, width=2)
    tw = d.textlength(text, font=f); d.rectangle([(x0 + x1 - tw) / 2 - 8, y - 14, (x0 + x1 + tw) / 2 + 8, y + 14], fill='white')
    d.text(((x0 + x1 - tw) / 2, y - 13), text, font=f, fill=GREY)

def dim_v(d, x, y0, y1, text, f, left=False):
    d.line([(x, y0), (x, y1)], fill=DIM, width=2)
    for y in (y0, y1): d.line([(x - 9, y), (x + 9, y)], fill=DIM, width=2)
    tw = d.textlength(text, font=f)
    d.text((x - tw - 16 if left else x + 16, (y0 + y1) / 2 - 13), text, font=f, fill=GREY)

def shadow_paste(sheet, im, xy, blur=14, off=(0, 10), alpha=0.18):
    a = im.getchannel('A').point(lambda v: int(v * alpha)); pad = blur * 3
    sh = Image.new('RGBA', (im.width + 2 * pad, im.height + 2 * pad), (0, 0, 0, 0))
    sh.putalpha(Image.new('L', sh.size, 0)); m = Image.new('L', sh.size, 0); m.paste(a, (pad, pad))
    sh.putalpha(m.filter(ImageFilter.GaussianBlur(blur)))
    sheet.alpha_composite(sh, (xy[0] - pad + off[0], xy[1] - pad + off[1])); sheet.alpha_composite(im, xy)

W, H = 3600, 2440
for n, (k, label, th, lh) in enumerate(COMBOS):
    if not os.path.isdir(os.path.join(D, k)): continue
    sheet = Image.new('RGBA', (W, H), (255, 255, 255, 255)); d = ImageDraw.Draw(sheet)
    name = label.split(' / ')[0]
    d.text((80, 50), name, font=F(HF, 110), fill=INK)
    d.text((86, 192), f'Zine Machine  ·  No. {n + 1:02d}  ·  views, actual proportions (flat views 1:1 scale to each other)',
           font=F(AR, 30), fill=GREY)
    for i, (hexcol, what) in enumerate(((th, 'Tray'), (lh, 'Lid, translucent'))):
        x = 2560 + i * 520
        d.rounded_rectangle([x, 80, x + 70, 150], radius=12, fill=hexcol, outline=(200, 200, 205), width=2)
        d.text((x + 90, 82), what, font=F(AR, 30), fill=INK); d.text((x + 90, 120), hexcol.upper(), font=F(AR, 26), fill=GREY)
    d.line([(80, 260), (W - 80, 260)], fill=RULE, width=2)
    for b, state in enumerate(('on', 'off')):
        p = lambda v: os.path.join(D, k, state, v + '.png')
        y0 = 300 + b * 1080
        d.text((80, y0), 'Cover on' if state == 'on' else 'Cover off', font=F(HF, 64), fill=INK)
        lab = F(AR, 28); dm = F(AR, 26)
        im = iso(p('iso'), (1180, 860)); sheet.alpha_composite(im, (80 + (1180 - im.width) // 2, y0 + 110 + (880 - im.height) // 2))
        d.text((80, y0 + 1000), 'Isometric', font=lab, fill=GREY)
        # top view with width/depth callouts
        top = flat(p('top')); tx, ty = 1370, y0 + 190
        shadow_paste(sheet, top, (tx, ty)); d.text((tx, ty - 80), 'Top', font=lab, fill=GREY)
        dim_h(d, tx, tx + top.width, ty + top.height + 44, f'{top.width / K:.1f} mm (measured)', dm)
        dim_v(d, tx - 36, ty, ty + top.height, f'{top.height / K:.1f}', dm, left=True)
        # elevations: front, back, left, right, stacked with a ground line and a height callout
        ex, ey = tx + top.width + 150, y0 + 120
        for v, title in (('front', 'Front (keyboard edge)'), ('back', 'Back (display edge)'),
                         ('left', 'Left (USB-C side)'), ('right', 'Right')):
            e = flat(p(v)); d.text((ex, ey), title, font=lab, fill=GREY)
            sheet.alpha_composite(e, (ex, ey + 40))
            gy = ey + 40 + e.height
            d.line([(ex - 20, gy + 2), (ex + e.width + 20, gy + 2)], fill=RULE, width=2)
            dim_v(d, ex + e.width + 30, ey + 40, gy, f'{e.height / K:.1f} mm', dm)
            ey += e.height + 40 + 66
        if b == 0: d.line([(80, y0 + 1060), (W - 80, y0 + 1060)], fill=RULE, width=2)
    sheet.convert('RGB').save(os.path.join(OUTD, f'{n + 1:02d}_{k}_views.png'))
    print('wrote', k)

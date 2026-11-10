# Poster: the kickflip strobe (render_lid.py --poster KEY -> stage0..5.png, transparent) on seamless white, a single
# serif word with a full stop under it. Usage: python3 make_poster.py STAGES_DIR OUT.png [WORD] [FOOTER]   (Pillow)
import glob, os, sys
from PIL import Image, ImageDraw, ImageFont

stages_dir, out = sys.argv[1], sys.argv[2]
WORD = sys.argv[3] if len(sys.argv) > 3 else 'Kickflip.'
FOOTER = sys.argv[4] if len(sys.argv) > 4 else 'Zine Machine'
W, H = 3600, 2400


poster = Image.new('RGBA', (W, H), (255, 255, 255, 255))
files = sorted(glob.glob(os.path.join(stages_dir, 'stage*.png')))
n = len(files)                                       # strobe: solid first and last frames, ghosted mid-air, rising
OPACITY = [1.0] + [0.5 + 0.28 * i / max(n - 3, 1) for i in range(n - 2)] + [1.0]
strip = Image.new('RGBA', Image.open(files[0]).size, (0, 0, 0, 0))
for f, a in zip(files, OPACITY):
    im = Image.open(f).convert('RGBA')
    im.putalpha(im.getchannel('A').point(lambda v, a=a: int(v * a)))
    strip.alpha_composite(im)
sw = int(W * 0.92); strip = strip.resize((sw, int(strip.height * sw / strip.width)), Image.LANCZOS)
# the shadow catcher leaves a faint veil over the whole frame: drop near-zero alpha, feather the strip's edges
from PIL import ImageFilter
a = strip.getchannel('A').point(lambda v: max(0, int((v - 6) * 255 / 249)))   # continuous: no clipped shadow edges
mask = Image.new('L', strip.size, 0)
m = int(min(strip.size) * 0.10)
ImageDraw.Draw(mask).rectangle([m, m, strip.width - m, strip.height - m], fill=255)
mask = mask.filter(ImageFilter.GaussianBlur(m * 0.6))
strip.putalpha(Image.composite(a, Image.new('L', strip.size, 0), mask))
bb = strip.getchannel('A').point(lambda v: 255 if v > 40 else 0).getbbox()   # visible content
word_f = ImageFont.truetype('/System/Library/Fonts/Supplemental/Hoefler Text.ttc', 190, index=0)
GAP_T, TEXT_H = int(H * 0.05), 190
block = (bb[3] - bb[1]) + GAP_T + TEXT_H                # strip content + gap + word, centred a touch above middle
top = int((H - block) * 0.46) - bb[1]
poster.alpha_composite(strip, ((W - sw) // 2, top))
text_y = top + bb[3] + GAP_T

d = ImageDraw.Draw(poster)
word_f = ImageFont.truetype('/System/Library/Fonts/Supplemental/Hoefler Text.ttc', 190, index=0)
tw = d.textlength(WORD, font=word_f)
d.text(((W - tw) / 2, text_y), WORD, font=word_f, fill=(29, 29, 31))
foot_f = ImageFont.truetype('/System/Library/Fonts/Supplemental/Hoefler Text.ttc', 46, index=0)
fw = d.textlength(FOOTER, font=foot_f)
d.text((W - fw - 120, H - 140), FOOTER, font=foot_f, fill=(150, 150, 155))
poster.convert('RGB').save(out)
print('wrote', out, poster.size)

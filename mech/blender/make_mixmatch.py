# Mix-and-match flipbook: render_lid.py --mixmatch -> DIR/f###.png + manifest.json (each tray bare, then with all 15
# lids, on a turntable). Composites on white with a caption + swatches and writes a GIF (per-frame palettes) and an MP4.
# Usage: python3 make_mixmatch.py DIR OUT_STEM [WIDTH] [SPEED]   (Pillow, ffmpeg; SPEED 3 = turntable plays 3x faster)
import json, os, re, shutil, subprocess, sys, tempfile
from PIL import Image, ImageDraw, ImageFilter, ImageFont
D, STEM = sys.argv[1], sys.argv[2]; WIDTH = int(sys.argv[3]) if len(sys.argv) > 3 else 800
SPEED = float(sys.argv[4]) if len(sys.argv) > 4 else 1.0
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'render_lid.py')).read()
COMBOS = {k: (lab.split(' / ')[0], th, lh, (lab.split(' / ') + [lab])[1].capitalize()) for k, lab, th, lh in
          re.findall(r"'(\w+)':\s*\('([^']+)',\s*'(#[0-9A-Fa-f]{6})',\s*[\d.]+,\s*'(#[0-9A-Fa-f]{6})'\)", src)}
HF = '/System/Library/Fonts/Supplemental/Hoefler Text.ttc'; AR = '/System/Library/Fonts/Supplemental/Arial.ttf'
INK, GREY = (29, 29, 31), (130, 130, 136)
man = json.load(open(os.path.join(D, 'manifest.json')))
tmp = tempfile.mkdtemp(prefix='mixmatch_')
H_CAP = 110

first = Image.open(os.path.join(D, man[0]['file']))
s = WIDTH / first.width; IW, IH = WIDTH, round(first.height * s)
f_big = ImageFont.truetype(HF, round(46 * WIDTH / 800), index=0)
f_sm = ImageFont.truetype(AR, round(19 * WIDTH / 800)); f_n = ImageFont.truetype(AR, round(16 * WIDTH / 800))
m = int(min(first.size) * 0.05); edge = Image.new('L', first.size, 0)
ImageDraw.Draw(edge).rectangle([m, m, first.width - m, first.height - m], fill=255)
edge = edge.filter(ImageFilter.GaussianBlur(m * 0.7))
n_combo = sum(1 for e in man if e['lid']); combo_i = 0
lines = []
for i, e in enumerate(man):
    im = Image.open(os.path.join(D, e['file'])).convert('RGBA')
    a = im.getchannel('A').point(lambda v: max(0, int((v - 6) * 255 / 249)))
    im.putalpha(Image.composite(a, Image.new('L', im.size, 0), edge))
    im = im.resize((IW, IH), Image.LANCZOS)
    fr = Image.new('RGBA', (IW, IH + H_CAP), (255, 255, 255, 255)); fr.alpha_composite(im)
    d = ImageDraw.Draw(fr); y = IH + 6; sw = round(34 * WIDTH / 800)
    tname, thex, _, _ = COMBOS[e['tray']]
    x = round(26 * WIDTH / 800)
    d.rounded_rectangle([x, y + 8, x + sw, y + 8 + sw], radius=7, fill=thex)
    if e['lid']:
        _, _, lhex, lname = COMBOS[e['lid']]; combo_i += 1
        d.rounded_rectangle([x + sw + 8, y + 8, x + 2 * sw + 8, y + 8 + sw], radius=7, fill=lhex)
        text = f'{tname} × {lname}'; sub = f'{tname} tray · {lname} lid (translucent)'
    else:
        text = f'{tname}, lid off'; sub = f'{tname} tray · next: every lid'
    tx = x + 2 * sw + 26
    d.text((tx, y), text, font=f_big, fill=INK); d.text((tx + 2, y + round(58 * WIDTH / 800)), sub, font=f_sm, fill=GREY)
    tag = f'{combo_i:03d} / {n_combo}' if e['lid'] else 'Zine Machine'
    tw = d.textlength(tag, font=f_n); d.text((IW - tw - x, y + round(64 * WIDTH / 800)), tag, font=f_n, fill=GREY)
    p = os.path.join(tmp, f'c{i:03d}.png'); fr.convert('RGB').save(p)
    lines += [f"file '{p}'", f"duration {(0.55 if not e['lid'] else 0.11) / SPEED:.4f}"]
lines.append(f"file '{p}'")                                      # concat demuxer: repeat the last file
open(os.path.join(tmp, 'list.txt'), 'w').write('\n'.join(lines) + '\n')
L = ['-f', 'concat', '-safe', '0', '-i', os.path.join(tmp, 'list.txt')]
subprocess.run(['ffmpeg', '-y', '-v', 'error', *L, '-vf',
                'split[a][b];[a]palettegen=stats_mode=single:reserve_transparent=0[p];[b][p]paletteuse=new=1:dither=sierra2_4a',
                '-loop', '0', STEM + '.gif'], check=True)
subprocess.run(['ffmpeg', '-y', '-v', 'error', *L, '-vf', 'fps=30,format=yuv420p', '-c:v', 'libx264', '-crf', '18',
                '-movflags', '+faststart', STEM + '.mp4'], check=True)
shutil.rmtree(tmp)
for ext in ('.gif', '.mp4'): print('wrote', STEM + ext, f'{os.path.getsize(STEM + ext) / 1e6:.1f} MB')

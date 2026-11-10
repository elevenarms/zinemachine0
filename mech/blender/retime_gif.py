# Retime a GIF with no re-encode. Only the per-frame delay in each Graphic Control Extension is rewritten.
# Delays are centiseconds, so each new delay is rounded from the cumulative time (total stays IN/SPEED).
# Usage: python3 retime_gif.py IN.gif OUT.gif SPEED [CAP_CS]   (stdlib only; CAP_CS caps each source delay first, removing holds)
import sys
b = bytearray(open(sys.argv[1], 'rb').read()); SPEED = float(sys.argv[3]); CAP = int(sys.argv[4]) if len(sys.argv) > 4 else 65535
assert b[:3] == b'GIF'
i = 13 + (3 * 2 ** ((b[10] & 7) + 1) if b[10] & 0x80 else 0)
def skip(i):                       # skip data sub-blocks
    while b[i]: i += b[i] + 1
    return i + 1
t_old = t_new = n = 0
while b[i] != 0x3B:
    if b[i] == 0x21:
        if b[i + 1] == 0xF9:       # graphic control: 21 F9 04 flags delay_lo delay_hi transp 00
            d = min(CAP, b[i + 4] | b[i + 5] << 8); t_old += d
            nd = max(2, round(t_old / SPEED) - t_new); t_new += nd   # <2 cs is clamped to 10 cs by browsers
            b[i + 4], b[i + 5] = nd & 255, nd >> 8; n += 1
        i = skip(i + 2)
    elif b[i] == 0x2C:
        f = b[i + 9]; i += 10 + (3 * 2 ** ((f & 7) + 1) if f & 0x80 else 0)
        i = skip(i + 1)
    else: raise SystemExit(f'bad block {b[i]:#x} at {i}')
open(sys.argv[2], 'wb').write(b)
print(f'{sys.argv[2]}: {n} frames, {t_old / 100:.2f} s -> {t_new / 100:.2f} s')

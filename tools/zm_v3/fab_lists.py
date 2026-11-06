"""Assembly BOM + placement (CPL) for the fab, and a full parts list, from design.py and KiCad's position export.
python3 fab_lists.py <positions_raw.csv> <fab dir>
The fab assembles every top-side SMD part; HAND lists the parts fitted by hand (through-hole or user-supplied)."""
import sys, os, csv, re
sys.path.insert(0, os.path.dirname(__file__))
import design as D

HAND_THT = {'J10': 'through-hole 3.5 mm jack', 'SW44': 'through-hole slide switch', 'J5': 'through-hole JST-PH battery connector'}
def hand_reason(p):
    if p['ref'] in HAND_THT:
        return HAND_THT[p['ref']]
    if p['kind'] == 'ChocV1':
        return 'Kailh Choc v1 key switch, soldered by hand'
    if p['ref'] == 'U2':
        return 'PocketBeagle 2 Industrial on 2x 2x18 male headers (fitted from below)'
    if p['kind'] in ('MountingHole', 'TestPoint'):
        return None
    return ''

def main(pos_csv, out):
    parts = {p['ref']: p for p in D.PARTS}
    asm, hand = {}, []
    for p in D.PARTS:
        r = hand_reason(p)
        if r is None:
            continue
        if r:
            hand.append(p); continue
        key = (p['value'], p['fp'], p['mpn'], p['lcsc'])
        asm.setdefault(key, []).append(p['ref'])
    natural = lambda s: [int(t) if t.isdigit() else t for t in re.split(r'(\d+)', s)]
    with open(os.path.join(out, 'bancouver40_pb2-bom.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['Comment', 'Designator', 'Footprint', 'Manufacturer Part Number', 'LCSC Part #', 'Quantity'])
        for (val, fp, mpn, lcsc), refs in sorted(asm.items(), key=lambda kv: natural(sorted(kv[1], key=natural)[0])):
            assert mpn and lcsc, refs
            w.writerow([val, ','.join(sorted(refs, key=natural)), fp.split(':')[1], mpn, lcsc, len(refs)])
    with open(os.path.join(out, 'bancouver40_pb2-parts-hand-fit.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['Designator', 'Value', 'Manufacturer Part Number', 'LCSC Part #', 'Why by hand'])
        groups = {}
        for p in hand:
            groups.setdefault((p['value'], p['mpn'], p['lcsc'] or '', hand_reason(p)), []).append(p['ref'])
        for (val, mpn, lcsc, why), refs in groups.items():
            w.writerow([','.join(sorted(refs, key=natural)), val, mpn, lcsc, why])
        w.writerow(['(U2 headers)', '2x 2x18 male pin header, 2.54 mm', 'any 2x18 2.54 mm male header (x2)', '',
                    'inserted from below into the U2 holes, plastic under the board; trim the pins so they do not bottom out in the PocketBeagle sockets'])
    asm_refs = {r for refs in asm.values() for r in refs}
    n = 0
    with open(pos_csv) as src, open(os.path.join(out, 'bancouver40_pb2-cpl.csv'), 'w', newline='') as dst:
        rd = csv.DictReader(src); w = csv.writer(dst)
        w.writerow(['Designator', 'Mid X', 'Mid Y', 'Layer', 'Rotation'])
        for row in rd:
            if row['Ref'] in asm_refs:
                w.writerow([row['Ref'], row['PosX'], row['PosY'], 'T' if row['Side'].lower() in ('top', 'front') else 'B', row['Rot']])
                n += 1
    missing = asm_refs - {r for r in asm_refs}
    print('BOM lines %d (%d parts), CPL rows %d, hand-fit %d' % (len(asm), len(asm_refs), n, len(hand)))
    if n != len(asm_refs):
        raise SystemExit('CPL rows do not match assembled parts')

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])

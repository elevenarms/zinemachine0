#!/bin/sh
# Fab outputs for the v3 main board -> pcb/bancouver40_pb2/fab/ (fails on any ERC/DRC error or unconnected item).
set -e
K=${KICAD_CLI:-/home/bp/opt/backplane-kicad-10.99.0-bp.6/bin/kicad-cli}
HERE=$(cd "$(dirname "$0")" && pwd); P=$(cd "$HERE/../../pcb/bancouver40_pb2" && pwd); B=bancouver40_pb2
cd "$P"; rm -rf fab; mkdir -p fab/gerbers build
"$K" version
"$K" sch erc --output fab/$B-erc.rpt --format report --units mm --severity-warning --severity-error --exit-code-violations $B.kicad_sch
"$K" pcb drc --output fab/$B-drc.rpt --format report --units mm --severity-warning --severity-error --schematic-parity --exit-code-violations $B.kicad_pcb
LAYERS=F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts
"$K" pcb export gerbers --output fab/gerbers --layers $LAYERS --subtract-soldermask --precision 5 $B.kicad_pcb
"$K" pcb export drill --output fab/gerbers/ --format excellon --drill-origin absolute --excellon-units mm \
    --excellon-zeros-format decimal --excellon-separate-th --generate-map --map-format gerberx2 $B.kicad_pcb
python3 -c "import shutil; shutil.make_archive('fab/$B-gerbers', 'zip', 'fab/gerbers')"
"$K" pcb export pos --output build/positions_raw.csv --format csv --units mm --side front --exclude-dnp $B.kicad_pcb
python3 "$HERE/fab_lists.py" build/positions_raw.csv fab
"$K" sch export pdf --output fab/$B-schematic.pdf $B.kicad_sch
"$K" pcb export pdf --output fab/$B-assembly-top.pdf --layers F.Fab,F.SilkS,Edge.Cuts --mode-single --black-and-white \
    --include-border-title $B.kicad_pcb
ls -la fab fab/gerbers

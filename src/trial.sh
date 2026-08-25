#!/usr/bin/env bash
#
# Boots the drive headless and reports whether the themed menu rendered.
#
# Usage: trial.sh LABEL
# Environment: DEV, WAIT

set -euo pipefail
cd "$(dirname "$0")"

LABEL="$1"
DEV="${DEV:-/dev/sdb}"
WAIT="${WAIT:-20}"

for part in "$DEV"?*; do
  findmnt -S "$part" >/dev/null 2>&1 && udisksctl unmount -b "$part" >/dev/null
done

./shot-ventoy-vm.py --dev "$DEV" --wait "$WAIT" \
  --out "trial_${LABEL}.png" >/dev/null 2>&1 || true

python3 - "$LABEL" <<'PY'
import sys

from PIL import Image

label = sys.argv[1]
try:
    img = Image.open(f"trial_{label}.png").convert("RGB")
except OSError as err:
    sys.exit(f"{label}: no screenshot ({err})")

pixels = list(img.getdata())
total = len(pixels)
lit = sum(1 for r, g, b in pixels if r + g + b > 40)
cyan = sum(1 for r, g, b in pixels if g > 120 and b > 120 and r < 120)

if lit / total < 0.02:
    verdict = "blank or crashed"
elif cyan / total > 0.005:
    verdict = "themed menu"
else:
    verdict = "menu, but unthemed"

print(f"{label}: lit={lit / total:.1%} cyan={cyan / total:.1%} -> {verdict}")
PY

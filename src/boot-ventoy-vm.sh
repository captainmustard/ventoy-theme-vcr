#!/usr/bin/env bash
#
# Boots a physical Ventoy drive in a UEFI virtual machine.
#
# The drive is attached read-only and behind a temporary overlay, so anything
# the guest writes is discarded when the machine exits.
#
# Usage: boot-ventoy-vm.sh [qemu args...]
# Environment: DEV, MEM, XRES, YRES

set -euo pipefail

DEV="${DEV:-/dev/sdb}"
MEM="${MEM:-4G}"
XRES="${XRES:-1920}"
YRES="${YRES:-1080}"

CODE=/usr/share/edk2/x64/OVMF_CODE.4m.fd
VARS_SRC=/usr/share/edk2/x64/OVMF_VARS.4m.fd
VARS="${TMPDIR:-/tmp}/ovmf_vars_ventoy.fd"

if [[ ! -r "$DEV" ]]; then
  echo "Cannot read $DEV. Grant read access with:" >&2
  echo "  sudo setfacl -m u:\$USER:r $DEV" >&2
  exit 1
fi

[[ -f "$VARS" ]] || cp "$VARS_SRC" "$VARS"

# A mounted filesystem would give the guest a torn view.
for part in "$DEV"?*; do
  if findmnt -S "$part" >/dev/null 2>&1; then
    echo "unmounting $part"
    udisksctl unmount -b "$part" >/dev/null
  fi
done

# Standard VGA advertises xres and yres over EDID, which OVMF reads as a mode
# hint. virtio-vga is not built into the qemu-system-x86 package.
exec qemu-system-x86_64 \
  -name "Ventoy (read-only)" \
  -enable-kvm -machine q35 -cpu host -smp 4 -m "$MEM" \
  -drive "if=pflash,format=raw,readonly=on,file=$CODE" \
  -drive "if=pflash,format=raw,file=$VARS" \
  -drive "file=$DEV,format=raw,if=none,id=vtoy,snapshot=on,readonly=on" \
  -device qemu-xhci \
  -device usb-storage,drive=vtoy,bootindex=0 \
  -device "VGA,xres=$XRES,yres=$YRES,edid=on" \
  -display gtk,show-cursor=on \
  "$@"

#!/usr/bin/env python3
"""Boots a Ventoy drive headless and captures the boot menu.

The drive is attached read-only behind a temporary overlay, so the guest cannot
modify it. The screenshot comes from QEMU's monitor, which needs no display
backend.

Usage:
    shot-ventoy-vm.py [--dev DEV] [--wait SECONDS] [--out FILE]
"""

import argparse
import os
import socket
import subprocess
import sys
import tempfile
import time

CODE = "/usr/share/edk2/x64/OVMF_CODE.4m.fd"
VARS = "/usr/share/edk2/x64/OVMF_VARS.4m.fd"


def monitor(path, command, settle=0.6):
    """Sends one command to the QEMU monitor and returns its reply.

    Args:
        path: Path to the monitor's UNIX socket.
        command: Command to send.
        settle: Seconds to wait before and after sending.

    Returns:
        Whatever the monitor wrote back, as text.
    """
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.connect(path)
    time.sleep(settle)
    try:
        sock.recv(65536)
    except BlockingIOError:
        pass

    sock.sendall(command.encode() + b"\n")
    time.sleep(settle)

    reply = b""
    sock.settimeout(2)
    try:
        while True:
            chunk = sock.recv(65536)
            if not chunk:
                break
            reply += chunk
    except socket.timeout:
        pass
    sock.close()
    return reply.decode(errors="replace")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dev", default="/dev/sdb")
    parser.add_argument("--wait", type=float, default=12.0)
    parser.add_argument("--out", default="shot.png")
    parser.add_argument("--mem", default="4G")
    parser.add_argument("--xres", default="1920")
    parser.add_argument("--yres", default="1080")
    args = parser.parse_args()

    if not os.access(args.dev, os.R_OK):
        user = os.environ.get("USER", "$USER")
        sys.exit(f"Cannot read {args.dev}. Grant read access with:\n"
                 f"  sudo setfacl -m u:{user}:r {args.dev}")

    workdir = tempfile.mkdtemp(prefix="ventoy-vm-")
    varstore = os.path.join(workdir, "OVMF_VARS.fd")
    monitor_sock = os.path.join(workdir, "monitor.sock")
    serial_log = os.path.join(workdir, "serial.log")
    ppm = os.path.join(workdir, "shot.ppm")
    subprocess.run(["cp", VARS, varstore], check=True)

    command = [
        "qemu-system-x86_64",
        "-enable-kvm", "-machine", "q35", "-cpu", "host", "-smp", "4",
        "-m", args.mem,
        "-drive", f"if=pflash,format=raw,readonly=on,file={CODE}",
        "-drive", f"if=pflash,format=raw,file={varstore}",
        "-drive", (f"file={args.dev},format=raw,if=none,id=vtoy,"
                   "snapshot=on,readonly=on"),
        "-device", "qemu-xhci",
        "-device", "usb-storage,drive=vtoy,bootindex=0",
        "-device", f"VGA,xres={args.xres},yres={args.yres},edid=on",
        "-display", "none",
        "-monitor", f"unix:{monitor_sock},server,nowait",
        "-serial", f"file:{serial_log}",
        "-no-reboot",
    ]
    print("starting qemu", flush=True)
    qemu = subprocess.Popen(command, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT)

    for _ in range(50):
        if os.path.exists(monitor_sock):
            break
        if qemu.poll() is not None:
            print(qemu.stdout.read().decode(errors="replace"))
            sys.exit("qemu exited before the monitor appeared")
        time.sleep(0.2)

    print(f"booting, waiting {args.wait}s", flush=True)
    time.sleep(args.wait)

    if qemu.poll() is not None:
        print(qemu.stdout.read().decode(errors="replace"))
        sys.exit("qemu exited before the screenshot")

    monitor(monitor_sock, f"screendump {ppm}")
    time.sleep(1.0)
    captured = os.path.exists(ppm) and os.path.getsize(ppm) > 0

    if captured:
        from PIL import Image
        image = Image.open(ppm)
        image.save(args.out)
        print(f"{args.out}: {image.size[0]}x{image.size[1]}")

    monitor(monitor_sock, "quit", settle=0.2)
    try:
        qemu.wait(timeout=5)
    except subprocess.TimeoutExpired:
        qemu.kill()

    if os.path.exists(serial_log) and os.path.getsize(serial_log):
        with open(serial_log, errors="replace") as fh:
            print("--- serial ---")
            print(fh.read()[-2000:])

    if not captured:
        sys.exit("screendump produced nothing")


if __name__ == "__main__":
    main()

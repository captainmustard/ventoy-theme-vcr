#!/usr/bin/env python3
"""Renders a TrueType font into GRUB's PF2 bitmap format.

Serves as a standalone replacement for `grub-mkfont`.

The PF2 layout is:

    FILE("PFF2") NAME FAMI WEIG SLAN PTSZ MAXW MAXH ASCE DESC CHIX DATA

CHIX holds 9 bytes per glyph: a big-endian u32 code point, a u8 flags byte, and
a big-endian u32 absolute file offset. The DATA section length is 0xFFFFFFFF,
meaning it runs to the end of the file. Each glyph is a big-endian header of
u16 width, u16 height, s16 x offset, s16 y offset, and u16 device width,
followed by width * height bits, most significant bit first, packed
continuously with no row padding.

Usage:
    mkfont.py FONT.ttf SIZE_PX NAME OUTPUT.pf2 [SCANLINE_PERIOD]
"""

import struct
import sys

from PIL import Image, ImageDraw, ImageFont

# Code points absent from the output fall back to Ventoy's unicode.pf2, which
# GRUB keeps loaded.
CHARS = (
    [chr(c) for c in range(0x20, 0x7F)]
    + [chr(c) for c in range(0xA0, 0x100)]
    + list("‘’“”–—•…←↑→↓▶◀·✓✗")
)


def render(ttf, px, scan=0, phase=0):
    """Rasterises every glyph as a 1-bit bitmap.

    Args:
        ttf: Path to a TrueType font file.
        px: Pixel size to render at.
        scan: If greater than zero, blanks every scan-th pixel row inside each
            glyph. Rows are counted from the baseline so that the gaps align
            across a line of text rather than shifting per glyph.
        phase: Row offset at which blanking starts.

    Returns:
        A tuple of (glyphs, ascent, descent), where glyphs maps a character to
        (width, height, x_offset, y_offset, device_width, bitmap).
    """
    font = ImageFont.truetype(ttf, px)
    ascent, descent = font.getmetrics()
    pad = px
    height = ascent + descent + 2 * pad
    glyphs = {}

    for ch in CHARS:
        try:
            device_width = round(font.getlength(ch))
        except Exception:
            continue

        img = Image.new("L", (max(device_width, 1) + 2 * pad, height), 0)
        draw = ImageDraw.Draw(img)
        draw.fontmode = "1"  # FreeType monochrome rasteriser, with hinting.
        draw.text((pad, pad), ch, font=font, fill=255, anchor="la")

        bbox = img.point(lambda v: 255 if v > 0 else 0).getbbox()
        if bbox is None:
            glyphs[ch] = (0, 0, 0, 0, device_width, b"")
            continue

        left, top, right, bottom = bbox
        baseline = pad + ascent
        pixels = img.load()
        bits = bytearray()
        acc = cur = 0

        for y in range(top, bottom):
            blanked = scan and ((baseline - y) % scan) == phase
            for x in range(left, right):
                cur = (cur << 1) | (0 if blanked else (1 if pixels[x, y] else 0))
                acc += 1
                if acc == 8:
                    bits.append(cur)
                    acc = cur = 0
        if acc:
            bits.append(cur << (8 - acc))

        glyphs[ch] = (right - left, bottom - top, left - pad,
                      baseline - bottom, device_width, bytes(bits))

    return glyphs, ascent, descent


def section(name, payload):
    """Returns a PF2 section with its big-endian length prefix."""
    return name + struct.pack(">I", len(payload)) + payload


def build(ttf, px, name, scan=0, phase=0):
    """Builds a complete PF2 font file.

    Args:
        ttf: Path to a TrueType font file.
        px: Pixel size to render at.
        name: Value for the PF2 NAME field. `theme.txt` refers to this string,
            so the two must match exactly.
        scan: Scanline period passed to `render`.
        phase: Row offset passed to `render`.

    Returns:
        The font file as bytes.
    """
    glyphs, ascent, descent = render(ttf, px, scan, phase)
    items = sorted(glyphs.items(), key=lambda kv: ord(kv[0]))

    blobs, offsets, run = [], [], 0
    for _, (w, h, x_off, y_off, device_width, bits) in items:
        offsets.append(run)
        blob = struct.pack(">HHhhH", w, h, x_off, y_off, device_width) + bits
        blobs.append(blob)
        run += len(blob)

    head = section(b"FILE", b"PFF2")
    for tag, value in ((b"NAME", name), (b"FAMI", name.rsplit(" ", 1)[0]),
                       (b"WEIG", "normal"), (b"SLAN", "normal")):
        head += section(tag, value.encode() + b"\0")
    for tag, value in ((b"PTSZ", px),
                       (b"MAXW", max((g[0] for _, g in items), default=px)),
                       (b"MAXH", max((g[1] for _, g in items), default=px)),
                       (b"ASCE", ascent), (b"DESC", descent)):
        head += section(tag, struct.pack(">H", value))

    # CHIX offsets are absolute, so the header size has to be known first.
    data_start = len(head) + 8 + 9 * len(items) + 8
    chix = b"".join(
        struct.pack(">IBI", ord(ch), 0, data_start + off)
        for (ch, _), off in zip(items, offsets)
    )

    return (head + section(b"CHIX", chix)
            + b"DATA" + struct.pack(">I", 0xFFFFFFFF) + b"".join(blobs))


def main():
    ttf, px, name, out = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4]
    scan = int(sys.argv[5]) if len(sys.argv) > 5 else 0
    blob = build(ttf, px, name, scan)
    with open(out, "wb") as fh:
        fh.write(blob)
    print(f"{out}: {len(blob):,} bytes, name={name!r}"
          + (f", scanline every {scan}px" if scan else ""))


if __name__ == "__main__":
    main()

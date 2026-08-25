#!/usr/bin/env python3
"""Expands a single-menu theme file into one with chromatic fringing.

GRUB draws each glyph as one solid colour from a 1-bit bitmap, so per-pixel
fringing is not possible. This declares the menu three times instead: the real
one, plus two tinted copies offset by a few pixels. The copies show past the
edges of the real glyphs.

Three constraints govern the result:

1.  The real menu is declared first. Reversed, the copies cover the white text
    and hide the selection bar.
2.  The copies drop `menu_pixmap_style`, which would repaint the frame, and so
    lose the padding a 9-slice pixmap contributes. They shift by PAD to
    compensate.
3.  Both copies are offset left. A copy offset a few pixels to the right does
    not render, at any declaration order, though the same copy appears once
    pushed far enough out.

Usage:
    mkchroma.py BASE.txt OUTPUT.txt [OFFSET_PX]
"""

import re
import sys

PAD = 24         # Corner size of menu_*.png.
ICON = 48        # icon_width in the base file.
ICON_SPACE = 18  # item_icon_space in the base file.

# Saturated tints read as coloured text rather than as a fringe on white text.
LEFT_TINT = "#A32F4A"    # Warm, further out.
RIGHT_TINT = "#3E9AAA"   # Cool, nearer the glyph.

MENU_RE = re.compile(r"\+ boot_menu \{.*?\n\}\n", re.S)


def ghost(menu, dx, colour):
    """Returns a tinted, offset copy of a boot_menu block.

    Args:
        menu: The source `+ boot_menu { ... }` block.
        dx: Horizontal offset in pixels, relative to the real menu.
        colour: Hex colour for the copy's text.

    Returns:
        The modified block.
    """
    out = menu
    out = re.sub(r"left   = (\d+)%",
                 lambda m: f"left   = {m.group(1)}%+{PAD + dx}", out)
    out = re.sub(r"top    = (\d+)%",
                 lambda m: f"top    = {m.group(1)}%+{PAD}", out)
    out = re.sub(r"\s*menu_pixmap_style\s*=.*\n", "\n", out)
    out = re.sub(r"\s*selected_item_pixmap_style\s*=.*\n", "", out)
    out = re.sub(r"\s*scrollbar\w*\s*=.*\n", "", out)
    # Draw the icons once, but hold the text column in place.
    out = out.replace(f"icon_width      = {ICON}", "icon_width      = 0")
    out = out.replace(f"icon_height     = {ICON}", "icon_height     = 0")
    out = out.replace(f"item_icon_space = {ICON_SPACE}",
                      f"item_icon_space = {ICON + ICON_SPACE}")
    out = re.sub(r'item_color          = "[^"]*"',
                 f'item_color          = "{colour}"', out)
    out = re.sub(r'selected_item_color = "[^"]*"',
                 f'selected_item_color = "{colour}"', out)
    return out


def expand(src, offset):
    """Returns the theme text with the menu tripled.

    Args:
        src: Contents of a theme file holding exactly one boot_menu block.
        offset: Fringe width in pixels.

    Returns:
        The expanded theme text.

    Raises:
        ValueError: If the source does not hold exactly one boot_menu block, or
            if the result would be invalid.
    """
    matches = MENU_RE.findall(src)
    if len(matches) != 1:
        raise ValueError(f"expected 1 boot_menu block, found {len(matches)}")

    match = MENU_RE.search(src)
    menu = match.group(0)
    out = (src[:match.start()]
           + menu + "\n"
           + ghost(menu, -offset, RIGHT_TINT) + "\n"
           + ghost(menu, -2 * offset, LEFT_TINT)
           + src[match.end():])

    if out.count("{") != out.count("}"):
        raise ValueError("unbalanced braces")
    if ".5%" in out:
        raise ValueError("fractional percentages abort the boot")
    return out


def main():
    src, dst = sys.argv[1], sys.argv[2]
    offset = int(sys.argv[3]) if len(sys.argv) > 3 else 2
    with open(src) as fh:
        out = expand(fh.read(), offset)
    with open(dst, "w") as fh:
        fh.write(out)
    print(f"{dst}: 3 boot_menu blocks, {offset}px fringe")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Generates the background, 9-slice panels, and icons for the theme.

GRUB composites the menu over the background at boot, so the CRT effects here
apply only to the background. Everything the menu itself draws stays flat.

Usage:
    mkart.py
"""

import os

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "build")
ICONS = os.path.join(OUT, "icons")
os.makedirs(ICONS, exist_ok=True)

W, H = 1920, 1080
VCR = "/usr/local/share/fonts/b/BetterVCR_25.09.ttf"

# CRT settings.
GRAIN = 0.22     # Static grain. Dominates the PNG size; noise does not compress.
BLOOM = 0.60     # Phosphor glow off bright pixels.
CHROMA = 2.6     # Radial colour fringing, in pixels at the edges.
CURVE = 0.055    # Barrel distortion. Zero renders a flat panel.
SCANLINE = 0.34  # Scanline darkness.
MASK = 0.10      # RGB phosphor triad mask.
GLARE = 0.30     # Glass reflection.
BEZEL = True     # Rounded screen edge.

BG = (4, 7, 12)
WHITE = (223, 246, 255)
CYAN = (77, 232, 224)
DIM = (110, 132, 148)
RED = (255, 59, 107)
BLUE = (34, 211, 238)

P_CYAN, P_GREEN, P_AMBER = (91, 200, 255), (110, 240, 138), (255, 180, 84)
P_YELLOW, P_MAGENTA, P_WHITE = (255, 216, 102), (255, 111, 216), (223, 246, 255)

GRID = 16   # Icon authoring grid.
SCALE = 3   # Icon upscale factor, to 48px.


def font(px):
    """Returns the VCR typeface at a pixel size."""
    return ImageFont.truetype(VCR, px)


def pixel_text(img, xy, text, px, fill, anchor="la"):
    """Draws hard-edged text, without antialiasing."""
    draw = ImageDraw.Draw(img)
    draw.fontmode = "1"
    draw.text(xy, text, font=font(px), fill=fill, anchor=anchor)


def fx_bloom(img, radius=22, strength=BLOOM, thresh=90):
    """Blurs the bright regions and adds them back as phosphor glow."""
    if strength <= 0:
        return img
    mask = img.convert("L").point(
        lambda v: 0 if v < thresh else min(255, (v - thresh) * 255 // (255 - thresh)))
    bright = Image.composite(img, Image.new("RGB", img.size, (0, 0, 0)), mask)
    glow = bright.filter(ImageFilter.GaussianBlur(radius))
    return ImageChops.add(img, glow.point(lambda v: int(v * strength)))


def fx_chroma(img, px=CHROMA):
    """Splays red outwards and pulls blue inwards, as a lens does."""
    if px <= 0:
        return img
    red, green, blue = img.split()

    def rescale(channel, factor):
        w, h = max(1, int(W * factor)), max(1, int(H * factor))
        out = Image.new("L", (W, H), 0)
        out.paste(channel.resize((w, h), Image.BICUBIC),
                  ((W - w) // 2, (H - h) // 2))
        return out

    d = px / max(W, H)
    return Image.merge("RGB", (rescale(red, 1 + d * 2), green,
                               rescale(blue, 1 - d * 2)))


def fx_curve(img, k=CURVE, cells=48):
    """Applies barrel distortion through a mesh transform."""
    if k <= 0:
        return img

    def source(x, y):
        nx, ny = (x / W - .5) * 2, (y / H - .5) * 2
        f = 1 + k * (nx * nx + ny * ny)
        return ((nx * f / 2 + .5) * W, (ny * f / 2 + .5) * H)

    mesh = []
    for i in range(cells):
        for j in range(cells):
            x0, x1 = W * i / cells, W * (i + 1) / cells
            y0, y1 = H * j / cells, H * (j + 1) / cells
            mesh.append(((int(x0), int(y0), int(round(x1)), int(round(y1))),
                         source(x0, y0) + source(x0, y1)
                         + source(x1, y1) + source(x1, y0)))
    return img.transform((W, H), Image.MESH, mesh, Image.BICUBIC)


def fx_scanlines(img, strength=SCANLINE, mask=MASK):
    """Darkens alternate rows, then applies an RGB triad mask."""
    if strength > 0:
        lines = Image.new("L", (W, H), 255)
        draw = ImageDraw.Draw(lines)
        for y in range(0, H, 3):
            draw.line([(0, y), (W, y)], fill=int(255 * (1 - strength)))
            draw.line([(0, y + 1), (W, y + 1)],
                      fill=int(255 * (1 - strength * .4)))
        img = Image.composite(img, Image.new("RGB", (W, H), (0, 0, 0)), lines)

    if mask > 0:
        triad = Image.new("RGB", (3, 1))
        triad.putpixel((0, 0), (255, 205, 205))
        triad.putpixel((1, 0), (205, 255, 205))
        triad.putpixel((2, 0), (205, 205, 255))
        strip = triad.resize((3, H), Image.NEAREST)
        tile = Image.new("RGB", (W, H))
        for x in range(0, W, 3):
            tile.paste(strip, (x, 0))
        img = Image.blend(img, ImageChops.multiply(img, tile), mask)
    return img


def fx_glare(img, strength=GLARE):
    """Adds a reflection: an ambient wash, two specular bands, and a hotspot.

    Runs after `fx_curve`, because a reflection sits on the glass surface and
    does not inherit the tube's distortion. Each layer carries its own blur; a
    single shared blur smears the bands into the wash.
    """
    if strength <= 0:
        return img

    def layer(shape, fill, blur, kind="poly"):
        img_l = Image.new("L", (W, H), 0)
        draw = ImageDraw.Draw(img_l)
        (draw.ellipse if kind == "ellipse" else draw.polygon)(shape, fill=fill)
        return img_l.filter(ImageFilter.GaussianBlur(blur))

    wash = layer([(-340, 0), (W * .56, 0), (W * .17, H), (-800, H)], 120, 155)
    band = layer([(W * .07, 0), (W * .24, 0), (W * .00, H), (-240, H)], 255, 34)
    band2 = layer([(W * .28, 0), (W * .35, 0), (W * .15, H), (W * .09, H)],
                  185, 26)
    hot = layer([W * .00, -H * .36, W * .46, H * .36], 255, 150, "ellipse")
    top = layer([(0, 0), (W, 0), (W, H * .09), (0, H * .14)], 170, 80)

    combined = wash
    for source, weight in ((band, 1.0), (band2, 0.7), (hot, 0.62), (top, 0.5)):
        combined = ImageChops.lighter(
            combined, source.point(lambda v, w=weight: int(v * w)))

    sheen = Image.composite(Image.new("RGB", (W, H), (168, 220, 246)),
                            Image.new("RGB", (W, H), (0, 0, 0)), combined)
    return ImageChops.add(img, sheen.point(lambda v: int(v * strength)))


def fx_bezel(img):
    """Darkens the frame to a rounded screen edge."""
    if not BEZEL:
        return img
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).rounded_rectangle([26, 22, W - 27, H - 23],
                                           radius=96, fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(26))
    out = Image.composite(img, Image.new("RGB", (W, H), (0, 0, 0)), mask)
    ImageDraw.Draw(out).rounded_rectangle([24, 20, W - 25, H - 21], radius=98,
                                          outline=(16, 30, 38), width=3)
    return out


def background():
    """Renders background.png."""
    img = Image.new("RGB", (W, H), BG)

    glow = Image.new("RGB", (W, H), (0, 0, 0))
    ImageDraw.Draw(glow).ellipse([W * 0.06, -H * 0.30, W * 0.94, H * 1.30],
                                 fill=(6, 19, 26))
    img = ImageChops.add(img, glow.filter(ImageFilter.GaussianBlur(240)))

    tx, ty = 150, 78
    layers = []
    for dx, colour in ((-5, RED), (5, BLUE), (0, WHITE)):
        layer = Image.new("RGB", (W, H), (0, 0, 0))
        pixel_text(layer, (tx + dx, ty), "VENTOY", 104, colour)
        layers.append(layer)
    img = ImageChops.add(
        img, ImageChops.add(ImageChops.add(layers[0], layers[1]), layers[2]))

    draw = ImageDraw.Draw(img)
    py = ty + 150
    draw.polygon([(tx, py), (tx, py + 30), (tx + 26, py + 15)], fill=CYAN)
    pixel_text(img, (tx + 44, py - 2), "PLAY", 30, CYAN)
    pixel_text(img, (tx + 200, py - 2), "SP", 30, DIM)
    pixel_text(img, (tx + 310, py - 2), "MULTIBOOT RESCUE TAPE", 30, DIM)
    pixel_text(img, (W - 150, ty + 6), "12:00 AM", 34, WHITE, anchor="ra")
    pixel_text(img, (W - 150, ty + 50), "0:00:00", 26, DIM, anchor="ra")

    # Sits below the hotkey labels GRUB draws.
    by = H - 66
    pixel_text(img, (tx, by), "TRACKING", 26, DIM)
    draw.rectangle([tx + 190, by + 12, tx + 680, by + 18], fill=(26, 44, 54))
    draw.rectangle([tx + 190, by + 12, tx + 470, by + 18], fill=CYAN)

    band_y, band_h = 322, 9
    band = img.crop((0, band_y, W, band_y + band_h))
    img.paste(band.point(lambda v: min(255, int(v * 1.7))), (26, band_y))

    img = fx_bloom(img)
    img = fx_chroma(img)
    img = fx_curve(img)
    img = fx_scanlines(img)
    img = fx_glare(img)

    if GRAIN:
        noise = Image.effect_noise((W, H), 26).convert("L").convert("RGB")
        img = Image.blend(img, ImageChops.soft_light(img, noise), GRAIN)

    vignette = Image.new("L", (W, H), 0)
    ImageDraw.Draw(vignette).ellipse(
        [-W * 0.26, -H * 0.34, W * 1.26, H * 1.34], fill=255)
    vignette = vignette.filter(ImageFilter.GaussianBlur(230))
    img = Image.composite(img, Image.new("RGB", (W, H), (1, 2, 4)), vignette)

    img = fx_bezel(img)
    img.save(f"{OUT}/background.png")
    print(f"background.png: {os.path.getsize(f'{OUT}/background.png') / 1024:,.0f} KB")


def slice9(panel, prefix, corner, edge):
    """Cuts a square panel into the nine pixmaps GRUB expects.

    Args:
        panel: A square image of size 2 * corner + edge.
        prefix: Output filename prefix.
        corner: Corner size in pixels. GRUB adds this to the element as
            padding, so it also sets how much larger than its content the
            element renders.
        edge: Size of the tiled centre strip.
    """
    c, e = corner, edge
    boxes = {
        "nw": (0, 0, c, c), "n": (c, 0, c + e, c), "ne": (c + e, 0, 2*c + e, c),
        "w": (0, c, c, c + e), "c": (c, c, c + e, c + e),
        "e": (c + e, c, 2*c + e, c + e),
        "sw": (0, c + e, c, 2*c + e), "s": (c, c + e, c + e, 2*c + e),
        "se": (c + e, c + e, 2*c + e, 2*c + e),
    }
    for name, box in boxes.items():
        panel.crop(box).save(f"{OUT}/{prefix}_{name}.png")
    print(f"{prefix}_*.png")


def osd_box(size, fill, border, width, glow=0.0):
    """Returns a square, hard-edged panel.

    Args:
        size: Side length in pixels.
        fill: RGBA fill colour.
        border: RGBA border colour.
        width: Border width in pixels.
        glow: Strength of the fading rings inside the border, which stand in
            for phosphor bleed. GRUB scales the centre tile, so a real blur
            would smear.
    """
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, size - 1, size - 1], fill=fill)
    if glow > 0:
        for i, alpha in enumerate((0.42, 0.20, 0.09)):
            offset = width + i
            if offset < size // 2:
                draw.rectangle(
                    [offset, offset, size - 1 - offset, size - 1 - offset],
                    outline=border[:3] + (int(border[3] * alpha * glow),))
    for i in range(width):
        draw.rectangle([i, i, size - 1 - i, size - 1 - i], outline=border)
    return img


def menus():
    """Renders the menu frame, selection bar, and terminal box."""
    corner, edge = 24, 12
    size = 2 * corner + edge

    # The fill is transparent so the background reads through the menu.
    frame = osd_box(size, (3, 8, 14, 0), CYAN + (240,), 3, glow=1.5)
    draw = ImageDraw.Draw(frame)
    for i in (8, 9):
        draw.rectangle([i, i, size - 1 - i, size - 1 - i],
                       outline=(30, 70, 82, 105))
    slice9(frame, "menu", corner, edge)

    # Corners stay small: GRUB adds them to item_height, so large corners make
    # the highlight overlap the next row.
    sel_corner, sel_edge = 2, 8
    sel_size = 2 * sel_corner + sel_edge
    selection = Image.new("RGBA", (sel_size, sel_size), CYAN + (224,))
    ImageDraw.Draw(selection).rectangle([0, 0, sel_size - 1, sel_size - 1],
                                        outline=(200, 255, 252, 255))
    slice9(selection, "select", sel_corner, sel_edge)

    slice9(osd_box(size, (2, 5, 10, 238), CYAN + (200,), 2, glow=0.8),
           "terminal_box", corner, edge)


def slider():
    """Renders the three-slice scrollbar thumb."""
    width = 12
    Image.new("RGBA", (width, 6), CYAN + (215,)).save(f"{OUT}/slider_c.png")
    for name in ("n", "s"):
        cap = Image.new("RGBA", (width, 6), CYAN + (215,))
        ImageDraw.Draw(cap).rectangle([0, 0, width - 1, 5],
                                      outline=(200, 255, 252, 255))
        cap.save(f"{OUT}/slider_{name}.png")
    print("slider_*.png")


def icon(name, draw_mark):
    """Renders one icon, upscaled from the authoring grid without smoothing.

    The backing block keeps the mark legible against the selection bar, which
    is a solid fill in the same colour family as several of the marks.
    """
    img = Image.new("RGBA", (GRID, GRID), (4, 9, 15, 236))
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, GRID - 1, GRID - 1], outline=(38, 82, 94, 255))
    draw_mark(draw)
    img.resize((GRID * SCALE, GRID * SCALE),
               Image.NEAREST).save(f"{ICONS}/{name}.png")


def letter(char, colour):
    """Returns a mark function that draws a single character."""
    def mark(draw):
        draw.fontmode = "1"
        draw.text((GRID / 2, GRID / 2 + 1), char, font=font(16),
                  fill=colour + (255,), anchor="mm")
    return mark


def windows(draw):
    for x in (1, 9):
        for y in (1, 9):
            draw.rectangle([x, y, x + 5, y + 5], fill=P_CYAN + (255,))


def ram(draw):
    draw.rectangle([2, 4, 13, 10], fill=P_GREEN + (255,))
    for x in (3, 6, 9, 12):
        draw.rectangle([x, 6, x, 8], fill=(4, 10, 14, 255))
    for x in (3, 6, 9, 12):
        draw.rectangle([x, 11, x + 1, 13], fill=P_GREEN + (255,))


def cross(draw):
    draw.rectangle([6, 1, 9, 14], fill=P_YELLOW + (255,))
    draw.rectangle([1, 6, 14, 9], fill=P_YELLOW + (255,))


def clone(draw):
    draw.rectangle([1, 1, 9, 9], outline=P_MAGENTA + (255,))
    draw.rectangle([5, 5, 14, 14], fill=(4, 10, 14, 255),
                   outline=P_MAGENTA + (255,))


def toolbox(draw):
    draw.rectangle([5, 2, 10, 5], outline=P_AMBER + (255,))
    draw.rectangle([2, 5, 13, 13], fill=P_AMBER + (255,))
    draw.rectangle([2, 8, 13, 9], fill=(4, 10, 14, 255))
    draw.rectangle([7, 7, 8, 11], fill=(4, 10, 14, 255))


def shell(draw):
    for i in range(4):
        draw.point((2 + i, 4 + i), fill=P_WHITE + (255,))
        draw.point((2 + i, 12 - i), fill=P_WHITE + (255,))
        draw.point((3 + i, 4 + i), fill=P_WHITE + (255,))
        draw.point((3 + i, 12 - i), fill=P_WHITE + (255,))
    draw.rectangle([9, 11, 14, 12], fill=P_WHITE + (255,))


def icons():
    """Renders every icon into the icons directory."""
    icon("kali", letter("K", P_CYAN))
    icon("cachyos", letter("C", P_GREEN))
    icon("windows", windows)
    icon("hirens", toolbox)
    icon("sysrescue", cross)
    icon("rescuezilla", clone)
    icon("uefishell", shell)
    icon("memtest", ram)
    icon("vtoyiso", letter("?", P_WHITE))
    print("icons/*.png")


def main():
    background()
    menus()
    slider()
    icons()
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()

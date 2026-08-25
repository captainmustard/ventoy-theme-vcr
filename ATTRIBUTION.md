# Attribution

## Better VCR

`theme/vcr-32.pf2` and `theme/vcr-20.pf2` are GRUB PF2 bitmap fonts rendered
from the Better VCR typeface. They are derivative works of that font and carry
its license.

From the TTF `name` table:

```
copyright : (c) artdzyk 2022-2025, Kanji from PAWFONT by Pau (Yasuaki Ohno)
family    : Better VCR-JP
version   : 25.09
designer  : artdzyk
license   : Open Font License
```

*   Designer: artdzyk
*   Kanji glyphs: PAWFONT by Pau (Yasuaki Ohno)
*   License: SIL Open Font License 1.1
*   Source: [Better VCR on DaFont](https://www.dafont.com/better-vcr.font)

### Redistribution

The OFL permits bundling, modification, and commercial use, provided that:

1.  The full OFL 1.1 text ships alongside the fonts. The TTF includes no
    license file, so add [OFL.txt](https://openfontlicense.org) yourself.
2.  The copyright notice above is preserved.
3.  Derivatives remain under the OFL.
4.  The fonts are not sold on their own. Bundling them inside a theme is
    permitted.

The font declares no Reserved Font Name, so the PF2 `NAME` field can keep the
name Better VCR. If you modify the glyphs, rename them, and update the matching
names in `theme.txt`.

To avoid redistributing the font, delete the two `.pf2` files and ship only
`src/mkfont.py`. Users then generate the fonts from their own copy of the TTF.

## Everything else

The background, 9-slice panels, pixel icons, `theme.txt`, and the scripts carry
no third-party rights.

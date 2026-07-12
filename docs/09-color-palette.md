# Create the Exact 16-Color Character Palette

Create immutable palette IDs.

Use this initial palette:

```python
PALETTE = {
    "outline":       "#17191C",
    "shadow_gray":   "#363A3E",
    "beard_dark":    "#6E7377",
    "beard_mid":     "#BFC3C7",
    "beard_light":   "#F4F4F1",
    "skin_dark":     "#9B5428",
    "skin_mid":      "#C7783E",
    "skin_light":    "#E9AA71",
    "brown_dark":    "#4C2912",
    "brown":         "#874719",
    "blue_dark":     "#082D59",
    "blue_mid":      "#0E4C89",
    "blue_light":    "#176DB5",
    "gold":          "#EFA000",
    "gold_light":    "#FFD247",
    "magenta":       "#C51E72",
    "cyan_magic":    "#26D7E8"
}
```

The white background is not counted as part of the character palette.

Adjust colors only by creating a new versioned palette.

Do not silently modify palette values.

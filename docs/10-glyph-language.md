# Define the Glyph Language

Use a small, stable glyph vocabulary.

Primary glyphs:

```text
space
.
:
-
=
+
*
o
O
#
%
@
```

Optional dense-cell fallback:

```text
░
▒
▓
█
```

Only use Unicode block characters if the current ASCILINE transport and browser path handle them correctly.

The ASCII-only fallback must remain fully functional.

Create semantic glyph roles:

```python
GLYPHS = {
    "empty": " ",
    "highlight": ".",
    "soft_fill": ":",
    "cloth_fill": "+",
    "skin_fill": "o",
    "beard_fill": "%",
    "solid_fill": "#",
    "outline": "@",
    "spark": "*",
    "eye": "O"
}
```

Character masks should reference semantic glyph roles, not scattered literal characters.

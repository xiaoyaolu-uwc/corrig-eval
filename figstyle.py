"""Shared visual language for the README figures.

Hand-authored SVG rather than a plotting library, because the layout demands
exact control: every element in a figure aligns to one left margin, so nothing
overhangs its own heading.
"""
FONT = ("Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, 'Segoe UI', "
        "Helvetica, Arial, sans-serif")

BG    = "#FBF9F6"   # warm off-white; softer than pure white on a README
CARD  = "#FFFFFF"
INK   = "#1E232B"
MUTED = "#857F76"
FAINT = "#B5AEA4"
RULE  = "#E9E3DA"

# Ordered warm-to-cool ramp. Reads as a sequence when levels are ranked.
S = ["#B3452F", "#D98C42", "#3D7A8C", "#5C8A5A", "#8A6BA8", "#5A5550"]

M = 40      # single left margin every element aligns to


def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def w(text, size, weight=400):
    """Rough advance width; only used to size boxes, never for alignment."""
    return len(text) * size * (0.56 if weight >= 600 else 0.53)


def head(width, height):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
            f'width="{width}" height="{height}" font-family="{FONT}">',
            f'<rect width="{width}" height="{height}" fill="{BG}"/>']


def title(x, y, text, size=19):
    return (f'<text x="{x}" y="{y}" font-size="{size}" font-weight="700" '
            f'fill="{INK}" letter-spacing="-0.2">{esc(text)}</text>')


def sub(x, y, text, size=12.5, fill=None):
    return (f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill or MUTED}">'
            f'{esc(text)}</text>')


def legend_row(x, y, items, size=11.5):
    """Horizontal swatch legend. Sits under a heading instead of in a right
    column, which is where the old figures wasted most of their space."""
    out, cx = [], x
    for label, color in items:
        out.append(f'<rect x="{cx}" y="{y-8}" width="10" height="10" rx="2.5" fill="{color}"/>')
        out.append(f'<text x="{cx+15}" y="{y}" font-size="{size}" fill="{INK}">{esc(label)}</text>')
        cx += 15 + w(label, size) + 20
    return out

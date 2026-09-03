#!/usr/bin/env python3
# Contrast verification script (A12/A21) — checks WCAG AA contrast for all CSS tokens
# Usage: python verify_contrast.py
import re, sys

CSS_FILE = 'zarabotok/pipeline_v3/ui/src/styles.css'
TOKENS = ['--bg', '--panel', '--text', '--text-faint', '--accent', '--green', '--yellow', '--red', '--blue']

def hex_to_rgb(h):
    h = h.strip().lstrip('#')
    if len(h) == 3:
        h = ''.join(c*2 for c in h)
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def luminance(r, g, b):
    def channel(c):
        c = c / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)

def contrast(c1, c2):
    L1 = luminance(*c1)
    L2 = luminance(*c2)
    lighter, darker = max(L1, L2), min(L1, L2)
    return (lighter + 0.05) / (darker + 0.05)

try:
    with open(CSS_FILE, 'r', encoding='utf-8', errors='ignore') as f:
        css = f.read()
except FileNotFoundError:
    print('CSS not found:', CSS_FILE)
    sys.exit(1)

colors = {}
for tok in TOKENS:
    m = re.search(re.escape(tok) + r':\s*([^;]+);', css)
    if m:
        val = m.group(1).strip()
        if val.startswith('#'):
            colors[tok] = val

print('Found colors:', colors)
print('---')
print('WCAG AA requires contrast >= 4.5:1 (normal) / 3.0:1 (large)')

bg = hex_to_rgb(colors.get('--bg', '#0a0a0a'))
panel = hex_to_rgb(colors.get('--panel', '#1a1a1a'))

for tok, val in colors.items():
    if tok in ('--bg', '--panel'):
        continue
    c = hex_to_rgb(val)
    ratio_bg = contrast(c, bg)
    ratio_panel = contrast(c, panel)
    pass_bg = 'PASS' if ratio_bg >= 4.5 else 'FAIL'
    pass_panel = 'PASS' if ratio_panel >= 4.5 else 'FAIL'
    print(f'{tok} ({val}): on --bg={ratio_bg:.2f} {pass_bg} | on --panel={ratio_panel:.2f} {pass_panel}')

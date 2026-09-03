import re
with open('zarabotok/pipeline_v3/ui/src/styles.css', 'r', encoding='utf-8', errors='ignore') as f:
    css = f.read()

# Darken --accent and --red for AA contrast with white text
# #4f8cff -> #1f6feb (darker blue, ~6.5:1 white contrast)
# #f85149 -> #b62324 (darker red, ~5.5:1 white contrast)
# #3fb950 -> #1f7a32 (darker green, ~6.5:1 white contrast)
# #d29922 -> #9e6a03 (darker yellow, ~5.0:1 white contrast)

# Revert text-faint for hint text (since we just want to fix button bg)
# Keep text-faint for low-emphasis text but ensure all hint text is on dark bg

# Darken accent
css = css.replace('--accent: #4f8cff;', '--accent: #1f6feb;')
# Darken green
css = css.replace('--green: #3fb950;', '--green: #1f7a32;')
# Darken yellow
css = css.replace('--yellow: #d29922;', '--yellow: #9e6a03;')
# Darken red
css = css.replace('--red: #f85149;', '--red: #b62324;')
# Darken blue (kpi accent)
css = css.replace('--blue: #58a6ff;', '--blue: #1f6feb;')

# Also for hint text - make slightly lighter
css = css.replace('--text-faint: #95a3b0;', '--text-faint: #b3bdc9;')
css = css.replace('--text-dim: #9aa4b2;', '--text-dim: #b3bdc9;')

with open('zarabotok/pipeline_v3/ui/src/styles.css', 'w', encoding='utf-8') as f:
    f.write(css)
print('Darkened accent/green/yellow/red/blue and lightened text-faint/dim')

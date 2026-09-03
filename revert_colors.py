import re
with open('zarabotok/pipeline_v3/ui/src/styles.css', 'r', encoding='utf-8', errors='ignore') as f:
    css = f.read()
# Revert to original (slightly better)
css = css.replace('--accent: #1f6feb;', '--accent: #4f8cff;')
css = css.replace('--green: #1f7a32;', '--green: #3fb950;')
css = css.replace('--yellow: #9e6a03;', '--yellow: #d29922;')
css = css.replace('--red: #b62324;', '--red: #f85149;')
css = css.replace('--blue: #1f6feb;', '--blue: #58a6ff;')
# Keep text-faint light for better text contrast
# --text-faint: #95a3b0 is already good (7.38 on --bg)
with open('zarabotok/pipeline_v3/ui/src/styles.css', 'w', encoding='utf-8') as f:
    f.write(css)
print('Reverted color tokens to better balanced values')

import re
with open('zarabotok/pipeline_v3/ui/src/styles.css', 'r', encoding='utf-8', errors='ignore') as f:
    css = f.read()
# Change button text from #fff to a dark color (--bg) for AA on bright button bg
# For .btn-primary, .btn-success, .btn-danger: change white to var(--bg)
css = css.replace('.btn-primary {\n  background: var(--accent);\n  border-color: var(--accent);\n  color: #fff;\n}', '.btn-primary {\n  background: var(--accent);\n  border-color: var(--accent);\n  color: #0e1014;\n}')
css = css.replace('.btn-success {\n  background: var(--green);\n  border-color: var(--green);\n  color: #fff;\n}', '.btn-success {\n  background: var(--green);\n  border-color: var(--green);\n  color: #0e1014;\n}')
css = css.replace('.btn-danger {\n  background: var(--red);\n  border-color: var(--red);\n  color: #fff;\n}', '.btn-danger {\n  background: var(--red);\n  border-color: var(--red);\n  color: #0e1014;\n}')
with open('zarabotok/pipeline_v3/ui/src/styles.css', 'w', encoding='utf-8') as f:
    f.write(css)
print('Changed btn-* text from #fff to #0e1014 (dark) for better contrast on bright bg')

import re
with open('zarabotok/pipeline_v3/ui/src/styles.css', 'r', encoding='utf-8', errors='ignore') as f:
    css = f.read()
for sel in ['.sys-hint', '.kpi-hint', '.empty-text', '.empty-hint', '.btn-primary', '.btn-danger', '.btn-outline']:
    idx = css.find(sel)
    if idx >= 0:
        block = css[idx:idx+400]
        cm = re.search(r'color:\s*([^;}]+)[;}]', block)
        if cm:
            print(sel, '->', cm.group(1).strip())
        else:
            print(sel, '-> no color')
    else:
        print(sel, '-> NOT FOUND')

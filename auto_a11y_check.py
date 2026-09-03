import os
checks = {
    'Modal role=dialog': False, 'Modal aria-modal': False, 'Drawer role=dialog': False,
    'Toast aria-live': False, 'Badge aria-label': False, 'Table ArrowUpDown': False,
    'Pipeline ArrowLeftRight': False, 'Layout skip-link': False, 'Layout aria-current': False,
    'styles focus-visible': False, 'styles reduced-motion': False,
}
for root, dirs, files in os.walk('zarabotok/pipeline_v3/ui/src/components'):
    for f in files:
        if not f.endswith('.tsx'):
            continue
        path = os.path.join(root, f)
        with open(path, 'r', encoding='utf-8', errors='ignore') as file:
            text = file.read()
        if f == 'Modal.tsx':
            checks['Modal role=dialog'] = 'role="dialog"' in text
            checks['Modal aria-modal'] = 'aria-modal' in text
        if f == 'Drawer.tsx':
            checks['Drawer role=dialog'] = 'role="dialog"' in text
        if f == 'Toast.tsx':
            checks['Toast aria-live'] = 'aria-live' in text
        if f == 'Badge.tsx':
            checks['Badge aria-label'] = 'aria-label' in text
        if f == 'Table.tsx':
            checks['Table ArrowUpDown'] = 'ArrowUp' in text or 'ArrowDown' in text
        if f == 'Pipeline.tsx':
            checks['Pipeline ArrowLeftRight'] = 'ArrowLeft' in text or 'ArrowRight' in text
        if f == 'Layout.tsx':
            checks['Layout skip-link'] = 'skip-link' in text or 'href="#main"' in text
            checks['Layout aria-current'] = 'aria-current' in text
# Also check pages
for root, dirs, files in os.walk('zarabotok/pipeline_v3/ui/src/pages'):
    for f in files:
        if f == 'Pipeline.tsx':
            path = os.path.join(root, f)
            with open(path, 'r', encoding='utf-8', errors='ignore') as file:
                text = file.read()
            checks['Pipeline ArrowLeftRight'] = 'ArrowLeft' in text or 'ArrowRight' in text
with open('zarabotok/pipeline_v3/ui/src/styles.css','r',encoding='utf-8',errors='ignore') as f:
    css = f.read()
checks['styles focus-visible'] = ':focus-visible' in css
checks['styles reduced-motion'] = 'prefers-reduced-motion' in css
for k,v in checks.items():
    status = 'PASS' if v else 'FAIL'
    print(f"{status} | {k}")

import sys
sys.path.insert(0, '.')

with open('debug_fl_v19.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace both occurrences
content = content.replace(
    "overlays = page.query_selector_all('.ui-overlay, .modal-backdrop', '.ui-widget-overlay')",
    "overlays = page.query_selector_all('.ui-overlay, .modal-backdrop, .ui-widget-overlay')"
)

with open('debug_fl_v19.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Done')
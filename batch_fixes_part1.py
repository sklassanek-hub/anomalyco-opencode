import os, re
# A14 KanbanBoard check
kb_path = None
for root, dirs, files in os.walk('zarabotok/pipeline_v3/ui/src/components'):
    for f in files:
        if f == 'KanbanBoard.tsx':
            kb_path = os.path.join(root, f)
if kb_path:
    with open(kb_path, 'r', encoding='utf-8', errors='ignore') as file:
        text = file.read()
    has_arrow = 'ArrowLeft' in text
    has_grid = 'role="grid"' in text
    print('KanbanBoard found:', kb_path)
    print('Has ArrowLeft:', has_arrow)
    print('Has role=grid:', has_grid)
    print('Size:', len(text), 'bytes')
else:
    print('KanbanBoard not found')

# Clean pipeline_v3/d/ temp folders
d_path = 'zarabotok/pipeline_v3/d'
if os.path.exists(d_path):
    for f in os.listdir(d_path):
        fp = os.path.join(d_path, f)
        if os.path.isfile(fp):
            os.remove(fp)
            print('Removed:', fp)
        elif os.path.isdir(fp):
            import shutil
            shutil.rmtree(fp)
            print('Removed dir:', fp)
    # If empty, leave as is or remove
    if not os.listdir(d_path):
        print('d/ now empty')
# W21 done

# Clean workspace/sbtest_*/
ws = 'zarabotok/pipeline_v3/workspace'
removed = 0
if os.path.exists(ws):
    for entry in os.listdir(ws):
        if entry.startswith('sbtest_'):
            fp = os.path.join(ws, entry)
            if os.path.isdir(fp):
                import shutil
                shutil.rmtree(fp)
                removed += 1
print('Removed sbtest_*/ dirs:', removed)
# C9 done

# Check pipeline_v3/d inside.txt
print('---pipeline_v3/d status---')
if os.path.exists(d_path):
    print('Files in d/:', os.listdir(d_path))

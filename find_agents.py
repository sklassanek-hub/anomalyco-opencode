import os, glob
results = []
for root, dirs, files in os.walk('.'):
    for f in files:
        if f == 'agents_activity.json':
            results.append(os.path.join(root, f))
for r in results:
    print(r)

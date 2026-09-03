with open('launcher_new.log','r',encoding='utf-8',errors='ignore') as f:
    lines = f.readlines()
# Find lines containing '2026' or '08-' or '08/' near start/middle
keywords = ['2026','08-','08/','Aug','авг']
found = 0
for i, line in enumerate(lines):
    for k in keywords:
        if k in line:
            print(i, repr(line[:150]))
            found += 1
            if found >= 20:
                break
    if found >= 20:
        break

with open('launcher_new.log','r',encoding='utf-8',errors='ignore') as f:
    lines = f.readlines()
print('Total lines:', len(lines))
for i in range(min(30, len(lines))):
    line = lines[i]
    print(i, repr(line[:140]))

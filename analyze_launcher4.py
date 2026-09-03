with open('launcher_new.log','r',encoding='utf-8',errors='ignore') as f:
    lines = f.readlines()
terms = ['restart','reboot','session','new session','launch','started','init','begin']
for i in range(len(lines)):
    low = lines[i].lower()
    for t in terms:
        if t in low:
            # print chunk around it
            start = max(0, i-3)
            end = min(len(lines), i+4)
            chunk = ''.join(lines[start:end])
            if 'restart' in low or 'reboot' in low or 'session' in low:
                print('--- line', i, 'term', t, '---')
                print(chunk[:500])
                # only show first 5
                if i > 0:
                    pass
                # break after 5 total prints of this kind
    # limit scanning to avoid too much output: just scan every 100th line quickly
    # Actually let's just find first 10 occurrences using index search

with open('launcher_new.log','r',encoding='utf-8',errors='ignore') as f:
    lines = f.readlines()
count = 0
for i, line in enumerate(lines):
    if '20:' in line or '21:' in line or '22:' in line or '23:' in line:
        if i < 100 or (i > 7000 and i < 7100):
            pass  # skip
    # Search for lines with month names or 2026 anywhere
    low = line.lower()
    hits = []
    for term in ['2026','aug','авг','sep','сен','oct','окт','nov','ноя','dec','дек','jan','янв','feb','фев','mar','мар','apr','апр','may','май','jun','июн','jul','июл']:
        if term in low:
            hits.append(term)
    if hits:
        print(i, hits, repr(line[:120]))
        count += 1
        if count >= 30:
            break

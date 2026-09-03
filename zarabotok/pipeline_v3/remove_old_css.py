with open('workers/dashboard.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the exact position to cut
idx = content.find('""" + CSS + """')
if idx != -1:
    print('Found at:', idx)
    # The new content should end before this
    new_content = content[:idx]
    # Add proper closing
    if not new_content.rstrip().endswith('"""'):
        new_content = new_content.rstrip() + '\n"""'
    
    with open('workers/dashboard.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print('Removed old CSS, new length:', len(new_content))
else:
    print('Not found')
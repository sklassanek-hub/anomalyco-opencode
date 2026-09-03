import os

for root, dirs, files in os.walk('.'):
    for f in files:
        if f.endswith('.py'):
            path = os.path.join(root, f)
            try:
                with open(os.path.join(root, f), encoding='utf-8') as fp:
                    content = fp.read()
                    if 'freelancer' in content.lower():
                        print(f'{os.path.relpath(path)}: freelancer found')
            except:
                pass
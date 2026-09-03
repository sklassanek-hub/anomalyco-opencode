with open('workers/dashboard.py', 'r', encoding='utf-8') as f:
    content = f.read()

idx = content.find('if __name__ == "__main__":')
print('Main at:', idx)
print(content[idx:idx+500])
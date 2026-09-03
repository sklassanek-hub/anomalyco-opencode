with open('modules/sender.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find run_cycle function
start = content.find('def run_cycle() -> int:')
if start == -1:
    print("run_cycle not found")
    exit(1)

# Find end of run_cycle (next def at module level)
end = content.find('\ndef ', start + 1)
if end == -1:
    end = len(content)

# The original well-indented run_cycle from git would be better, but let's manually fix
# We need to properly indent everything inside run_cycle

# Extract the function
func = content[start:end]

# Split into lines
lines = func.split('\n')

# Rebuild with proper indentation
new_lines = []
in_function = False
base = 4

for i, line in enumerate(lines):
    stripped = line.strip()
    if not stripped:
        new_lines.append('')
        continue
    
    # Track indentation level
    if i == 0 and stripped.startswith('def run_cycle'):
        new_lines.append(line)
        continue
    
    # First level inside function (4 spaces)
    if stripped.startswith('def _') or stripped.startswith('if ') or \
       stripped.startswith('elif ') or stripped.startswith('else:') or \
       stripped.startswith('try:') or stripped.startswith('except ') or \
       stripped.startswith('for ') or stripped.startswith('while ') or \
       stripped.startswith('with ') or stripped.startswith('def _log') or \
       stripped.startswith('def _approve') or stripped.startswith('def _mark_bad'):
        new_lines.append('    ' + stripped)
    elif stripped.startswith('return ') or stripped.startswith('raise ') or \
         stripped.startswith('break') or stripped.startswith('continue') or \
         stripped.startswith('pass') or stripped.startswith('}') or \
         stripped.startswith('else:') or stripped.startswith('elif '):
        # These should be at 8 spaces (inside a block)
        if stripped.startswith('return sent') or stripped.startswith('return 0') or stripped.startswith('return n'):
            new_lines.append('        ' + stripped)
        else:
            new_lines.append('    ' + stripped)
    elif stripped.startswith('return sent') or stripped.startswith('return 0') or stripped.startswith('return n'):
        new_lines.append('        ' + stripped)
    elif stripped.startswith('if ') or stripped.startswith('elif ') or \
         stripped.startswith('for ') or stripped.startswith('while ') or \
         stripped.startswith('try:') or stripped.startswith('except ') or \
         stripped.startswith('with ') or stripped.startswith('def _'):
        # Second level (8 spaces) - but these are block starters
        new_lines.append('        ' + stripped)
    elif stripped.startswith('def ') and not stripped.startswith('def _'):
        # Module level def - end of run_cycle
        new_lines.append(line)
    elif stripped.startswith('#') or stripped == '':
        new_lines.append('    ' + stripped)
    else:
        # Regular statement inside function body
        new_lines.append('    ' + stripped)

new_func = '\n'.join(new_lines)
new_content = content[:start] + new_func + content[end:]

with open('modules/sender.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print('Fixed run_cycle indentation')
with open('modules/sender.py', 'rb') as f:
    content = f.read()

# Find the run_cycle function body and fix indentation
idx = content.find(b'def run_cycle() -> int:')
if idx == -1:
    print('NOT FOUND')
else:
    # Find the end of run_cycle (next def at module level)
    end_idx = content.find(b'\ndef ', idx + 1)
    if end_idx == -1:
        end_idx = len(content)
    
    body = content[idx:end_idx]
    lines = body.split(b'\r\n')
    
    # Fix: normalize indentation to 4 spaces per level
    new_lines = []
    base_indent = 4  # 4 spaces for function body
    
    for line in lines:
        # Count leading spaces/tabs
        leading = len(line) - len(line.lstrip(b' \t'))
        stripped = line.lstrip(b' \t')
        
        if not stripped:
            new_lines.append(b'')
            continue
            
        # Determine expected indent level
        expected = base_indent  # default: inside function body
        
        if stripped.startswith(b'def ') and not stripped.startswith(b'def _'):
            expected = 0
        elif stripped.startswith(b'def _'):
            expected = base_indent
        elif stripped.startswith(b'@'):
            expected = 0
        elif stripped.startswith(b'#'):
            expected = base_indent
        elif stripped.startswith(b'return ') or stripped.startswith(b'raise ') or stripped.startswith(b'break') or stripped.startswith(b'continue') or stripped.startswith(b'pass'):
            expected = base_indent * 2
        else:
            expected = base_indent
            
        new_lines.append(b' ' * expected + stripped)
    
    new_body = b'\r\n'.join(new_lines)
    new_content = content[:idx] + new_body + content[end_idx:]
    
    with open('modules/sender.py', 'wb') as f:
        f.write(new_content)
    
    print('Fixed indentation in run_cycle')
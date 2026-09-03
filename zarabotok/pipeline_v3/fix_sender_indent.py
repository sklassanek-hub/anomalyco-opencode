#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix sender.py indentation - rewrite run_cycle with proper indentation.
"""
import re

with open('modules/sender.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find run_cycle function
start = content.find('def run_cycle() -> int:')
if start == -1:
    print("run_cycle not found")
    exit(1)

# Find end of run_cycle (next def at module level or end of file)
end = content.find('\ndef ', start + 1)
if end == -1:
    end = len(content)

# Extract the function
func_content = content[start:end]

# Split into lines
lines = func_content.split('\n')

# Rebuild with proper indentation
new_lines = []
indent_level = 0
base_indent = 4

for i, line in enumerate(lines):
    stripped = line.strip()
    if not stripped:
        new_lines.append('')
        continue
    
    # Determine indent level
    # Dedent triggers
    if stripped.startswith('return ') or stripped.startswith('raise ') or \
       stripped.startswith('break') or stripped.startswith('continue') or \
       stripped.startswith('pass') or stripped.startswith('else:') or \
       stripped.startswith('elif '):
        indent_level = max(0, indent_level - 1)
    
    # Special dedent for closing blocks
    if stripped in ('return sent', 'return 0', 'return n'):
        indent_level = 1
    
    # Calculate indent
    if stripped.startswith('def ') and 'run_cycle' not in stripped:
        # Nested function defs inside run_cycle
        indent = 4
        indent_level = 1
    elif stripped.startswith('def run_cycle'):
        indent = 0
        indent_level = 0
    elif stripped.startswith('if ') or stripped.startswith('elif ') or stripped.startswith('for ') or \
         stripped.startswith('while ') or stripped.startswith('try:') or stripped.startswith('with ') or \
         stripped.startswith('def _') or stripped.startswith('except ') or stripped.startswith('else:'):
        indent = 4 * (indent_level + 1)
        if stripped.startswith('def _') or stripped.startswith('if ') or stripped.startswith('elif ') or \
           stripped.startswith('for ') or stripped.startswith('while ') or stripped.startswith('try:') or \
           stripped.startswith('with ') or stripped.startswith('except '):
            indent_level += 1
    elif stripped.startswith('return ') or stripped.startswith('raise ') or \
         stripped.startswith('break') or stripped.startswith('continue') or stripped.startswith('pass'):
        indent = 4 * indent_level
        indent_level = max(1, indent_level - 1)
    elif stripped.startswith('}') or stripped == '':
        indent = 4 * indent_level
    else:
        indent = 4 * (indent_level + 1)
    
    new_lines.append(' ' * indent + stripped)

# Join and replace
new_func = '\n'.join(new_lines)
new_content = content[:start] + new_func + content[end:]

with open('modules/sender.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print('Fixed run_cycle indentation')
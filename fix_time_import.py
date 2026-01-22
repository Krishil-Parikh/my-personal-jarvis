#!/usr/bin/env python3
"""
Quick fix to add missing 'time' import to frontend/02.py
"""

import os

frontend_file = os.path.join(os.path.dirname(__file__), 'frontend', '02.py')

with open(frontend_file, 'r') as f:
    content = f.read()

# Check if time is already imported
if 'import time' not in content:
    # Find the line with "import threading"
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if line.startswith('import threading'):
            # Add time import after threading
            lines.insert(i + 1, 'import time')
            break
    
    content = '\n'.join(lines)
    
    with open(frontend_file, 'w') as f:
        f.write(content)
    
    print("✅ Added 'import time' to frontend/02.py")
else:
    print("✅ 'import time' already present")

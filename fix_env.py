#!/usr/bin/env python3
"""
Script to fix common issues in .env files
"""
import os
import sys
import re

def fix_env_file(env_path):
    """
    Fix common issues in .env files that might cause parsing errors
    
    Args:
        env_path: Path to the .env file
    """
    if not os.path.exists(env_path):
        print(f"Error: {env_path} does not exist")
        return False
        
    with open(env_path, 'r') as f:
        lines = f.readlines()
    
    fixed_lines = []
    for i, line in enumerate(lines):
        # Strip trailing whitespace
        line = line.rstrip()
        
        # Skip empty lines or comments
        if not line or line.lstrip().startswith('#'):
            fixed_lines.append(line)
            continue
            
        # Handle quotes correctly
        if '=' in line:
            key, value = line.split('=', 1)
            # Remove quotes from values with spaces
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            elif value.startswith("'") and value.endswith("'"):
                value = value[1:-1]
                
            # Make sure we don't have spaces before or after the equal sign
            line = f"{key.strip()}={value.strip()}"
            
        fixed_lines.append(line)
        
    with open(env_path, 'w') as f:
        f.write('\n'.join(fixed_lines) + '\n')
    
    print(f"Fixed {env_path}")
    return True

if __name__ == "__main__":
    env_path = sys.argv[1] if len(sys.argv) > 1 else ".env"
    fix_env_file(env_path)

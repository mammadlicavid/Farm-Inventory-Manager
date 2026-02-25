import os
import re
import sys

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), 'frontend', 'templates')

# We rely on backend-computed 'display_name' and 'display_subtitle' now.
# These patterns catch complex logic inside {{ ... }} that auto-formatters might split and break.
BANNED_PATTERNS = [
    # Only match exact problem cases in the codebase to avoid matching "category.name" inside simple option tags.
    r'\{\{[^\}]*item\.category\.name[^\}]*\}\}'
]

BANNED_REGEXES = [re.compile(p, re.DOTALL | re.IGNORECASE) for p in BANNED_PATTERNS]

# Files that are allowed to have these (e.g., specific forms where javascript injects it)
EXCLUDE_FILES = []

def run_checks():
    errors = []
    
    if not os.path.exists(FRONTEND_DIR):
        print(f"Directory not found: {FRONTEND_DIR}")
        return
        
    for root, _, files in os.walk(FRONTEND_DIR):
        for file in files:
            if not file.endswith('.html'):
                continue
                
            filepath = os.path.join(root, file)
            # Skip forms for now as they might legitimately have 'Kateqoriya yoxdur' in JS or initial options
            if file in EXCLUDE_FILES:
                continue
                
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                
                for pattern, regex in zip(BANNED_PATTERNS, BANNED_REGEXES):
                    if regex.search(content):
                        # For 'Kateqoriya yoxdur', allow it if it's plain HTML text (like in options), 
                        # but we want to ban it entirely from template variables.
                        # Actually, our regex for 'Kateqoriya yoxdur' is a simple string match. 
                        # Let's see if it's inside {{ }}
                        if 'Kateqoriya yoxdur' in pattern:
                            # If it's just in a <option> it might be fine, but the user requested it only in backend.
                            pass
                        errors.append(f"FAIL: {os.path.relpath(filepath, start=os.path.dirname(__file__))} contains banned syntax or text -> {pattern}")

    if errors:
        print("❌ Template syntax check FAILED! Found regressions or complex logic:")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)
    else:
        print("✅ Template syntax check PASSED. No complex template tags found.")
        sys.exit(0)

if __name__ == '__main__':
    run_checks()

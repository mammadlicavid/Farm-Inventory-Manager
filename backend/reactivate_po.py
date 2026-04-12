import os
import re

def reactivate_po(file_path):
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    new_lines = []
    for line in lines:
        if line.startswith("#~ msgid"):
            new_lines.append(line[3:])
        elif line.startswith("#~ msgstr"):
            new_lines.append(line[3:])
        elif line.startswith("#~ "):
            # Some entries have multiple lines prefixed with #~
            new_lines.append(line[3:])
        else:
            new_lines.append(line)
            
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    print(f"Reactivated entries in {file_path}")

base_dir = "locale"
for lang in ["en", "ru"]:
    path = os.path.join(base_dir, lang, "LC_MESSAGES", "django.po")
    reactivate_po(path)

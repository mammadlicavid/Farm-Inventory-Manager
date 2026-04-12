import os
import re
import json

base_dir = "../frontend/templates"
trans_pattern = re.compile(r'{%\s*trans\s+["\'](.*?)["\']\s*%}')
blocktrans_pattern = re.compile(r'{%\s*blocktrans[^%]*%}(.*?){%\s*endblocktrans\s*%}', re.DOTALL)

found_strings = set()

for root, dirs, files in os.walk(base_dir):
    for file in files:
        if file.endswith(".html"):
            with open(os.path.join(root, file), "r", encoding="utf-8") as f:
                content = f.read()
                
                # trans tags
                for match in trans_pattern.findall(content):
                    found_strings.add(match)
                
                # blocktrans tags
                for match in blocktrans_pattern.findall(content):
                    cleaned = match.strip()
                    if cleaned:
                        # Need to exact match django makemessages parsing, 
                        # but django just normalizes whitespace slightly.
                        # It keeps exact newlines for blocktrans.
                        found_strings.add(cleaned)

import polib
po = polib.pofile("locale/en/LC_MESSAGES/django.po")
existing = {entry.msgid for entry in po}

missing = [s for s in found_strings if s not in existing and not s.isspace()]

with open("missing_strings.json", "w", encoding="utf-8") as f:
    json.dump(missing, f, ensure_ascii=False, indent=4)

print(f"Found {len(missing)} missing strings.")

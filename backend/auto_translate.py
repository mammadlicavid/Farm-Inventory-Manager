import os
import json
import urllib.request
import urllib.parse
import time
import polib

def gtrans(text, target_lang):
    url = "https://translate.googleapis.com/translate_a/single?client=gtx&sl=az&tl=" + target_lang + "&dt=t&q=" + urllib.parse.quote(text)
    req = urllib.request.Request(url)
    req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)')
    try:
        response = urllib.request.urlopen(req)
        data = json.loads(response.read().decode('utf-8'))
        res = "".join([x[0] for x in data[0]])
        # Fix dynamic variables being translated like %(name) s to %(name)s
        res = res.replace("% (", "%(").replace(") s", ")s").replace(") d", ")d")
        res = res.replace("{{ ", "{{").replace(" }}", "}}")
        return res
    except Exception as e:
        print(f"Failed to translate: {text}. Error: {e}")
        return text

if not os.path.exists('missing_strings.json'):
    print("missing_strings.json not found")
    exit(1)

with open('missing_strings.json', 'r', encoding='utf-8') as f:
    missing = json.load(f)

# Load existing PO files
base_dir = "locale"
po_files = {}
for lang in ["en", "ru"]:
    path = os.path.join(base_dir, lang, "LC_MESSAGES", "django.po")
    if os.path.exists(path):
        po_files[lang] = polib.pofile(path)

print(f"Translating {len(missing)} strings via Google Translate API (free tier)...")
for i, text in enumerate(missing):
    # Only translate strings that actually contain letters
    if not any(c.isalpha() for c in text):
        continue
        
    dj_text = text.replace("{{ ", "%(").replace(" }}", ")s")
    
    for lang in ["en", "ru"]:
        po = po_files.get(lang)
        if not po:
            continue
            
        exists = False
        for entry in po:
            if entry.msgid == text or entry.msgid == dj_text:
                exists = True
                break
        
        if not exists:
            translated = gtrans(text, lang)
            translated_dj = translated.replace("{{ ", "%(").replace(" }}", ")s")
            po.append(polib.POEntry(msgid=text, msgstr=translated))
            po.append(polib.POEntry(msgid=dj_text, msgstr=translated_dj))

print("Saving PO files...")
for lang, po in po_files.items():
    po.save(os.path.join(base_dir, lang, "LC_MESSAGES", "django.po"))

print("Done translations.")

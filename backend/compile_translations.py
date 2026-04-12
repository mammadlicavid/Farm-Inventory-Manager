import os
import polib

base_dir = "locale"
for lang in ["en", "ru"]:
    po_file_path = os.path.join(base_dir, lang, "LC_MESSAGES", "django.po")
    mo_file_path = os.path.join(base_dir, lang, "LC_MESSAGES", "django.mo")
    if os.path.exists(po_file_path):
        po = polib.pofile(po_file_path)
        po.save_as_mofile(mo_file_path)
        print(f"Compiled {lang} successfully to {mo_file_path}")
print("Done compiling")

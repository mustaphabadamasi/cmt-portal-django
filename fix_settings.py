import re, pathlib
f = pathlib.Path('cmt_portal/settings.py')
txt = f.read_text()
txt = txt.replace("'DIRS': []", "'DIRS': [BASE_DIR / 'templates']")
f.write_text(txt)
print('Done! DIRS updated.')

import re, pathlib
f = pathlib.Path('cmt_portal/settings.py')
txt = f.read_text()
txt = txt.replace("'DIRS': []", "'DIRS': [BASE_DIR / 'templates']")
f.write_text(txt)
print('Done! DIRS updated.')
ALLOWED_HOSTS = [
    'mustapher001.pythonanywhere.com',
    'localhost',           # for local development
    '127.0.0.1',           # for local development
    # Add any other domains you use (e.g., your custom domain if you have one)
]

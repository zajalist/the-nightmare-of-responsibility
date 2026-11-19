"""Extract a downloaded (untrusted) zip into a new sibling folder <zip>_x, refusing absolute or parent paths.
usage: python -I unzip_safe.py <file.zip>"""
import os
import sys
import zipfile

src = os.path.abspath(sys.argv[1])
dst = os.path.splitext(src)[0] + '_x'
os.makedirs(dst, exist_ok=False)
with zipfile.ZipFile(src) as z:
    for m in z.infolist():
        out = os.path.abspath(os.path.join(dst, m.filename))
        if not out.startswith(dst + os.sep) or m.filename.startswith(('/', chr(92))):
            sys.exit('unsafe member ' + m.filename)
        if m.is_dir():
            continue
        if m.file_size > 200e6:
            sys.exit('member too large ' + m.filename)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with z.open(m) as fi, open(out, 'wb') as fo:
            fo.write(fi.read())
        print(m.file_size, m.filename)

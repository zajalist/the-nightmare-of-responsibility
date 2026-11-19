"""Append one devlog line per deliverable to P:/FoA-Devlog/media_log.jsonl (editor-rules, "Document everything").
  python Tools/Unreal/ui/media_log.py "<one plain sentence>" <file> [<file> ...]"""
import datetime
import json
import os
import sys

what = sys.argv[1]
files = [os.path.abspath(f).replace(os.sep, '/') for f in sys.argv[2:]]
missing = [f for f in files if not os.path.exists(f)]
assert files and not missing, f'missing files: {missing}'
line = {'t': datetime.datetime.now().strftime('%H:%M'), 'lane': 'ui', 'what': what, 'files': files}
with open('P:/FoA-Devlog/media_log.jsonl', 'a', encoding='utf-8') as fh:
    fh.write(json.dumps(line) + '\n')
print('logged:', what)

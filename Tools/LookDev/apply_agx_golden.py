"""Apply the installed Veil UE5.8 preset after the coordinator closes the editor."""
import csv
import hashlib
import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

root = Path('P:/FoA')
engine = Path('C:/Program Files/Epic Games/UE_5.8/Engine')
plugin = root / 'Plugins/Marketplace/VC_Tonemapper_Toolkit'
version = json.loads((engine / 'Build/Build.version').read_text())
assert (version['MajorVersion'], version['MinorVersion']) == (5, 8)
modules = json.loads((engine / 'Binaries/Win64/UnrealEditor.modules').read_text())
plugin_modules = json.loads((plugin / 'Binaries/Win64/UnrealEditor.modules').read_text())
assert modules['BuildId'] == plugin_modules['BuildId'], 'Incompatible toolkit binary'
processes = subprocess.check_output(
    ['tasklist', '/FI', 'IMAGENAME eq UnrealEditor.exe', '/FO', 'CSV', '/NH'], text=True)
assert not any(row and row[0].lower() == 'unrealeditor.exe'
               for row in csv.reader(processes.splitlines())), 'Close Unreal before patching its shader'
patches = plugin / 'Source/ThirdParty/AGX/Patches/UE5.8'
target = engine / 'Shaders/Private/PostProcessTonemap.usf'
golden = patches / 'PostProcessTonemap_AgXGolden.usf.patched'
stock = patches / 'PostProcessTonemap_UnrealACES.usf.original'
assert target.read_text() in (stock.read_text(), golden.read_text()), 'Preserve unknown shader modifications'
assert '#define AGX_LOOK 1' in golden.read_text()
assert (root / 'Saved/Integration/agx/before.json').exists(), 'Record authored PP before applying'
backup = root / 'Saved/Backups/agx' / datetime.now().strftime('%Y%m%d_%H%M%S')
backup.mkdir(parents=True)
project = root / 'FoA.uproject'
shutil.copy2(target, backup / target.name)
shutil.copy2(project, backup / project.name)
descriptor = json.loads(project.read_text())
entry = next((p for p in descriptor['Plugins'] if p['Name'] == 'VC_Tonemapper_Toolkit'), None)
if entry is None:
    descriptor['Plugins'].append({'Name': 'VC_Tonemapper_Toolkit', 'Enabled': True})
else:
    entry['Enabled'] = True
try:
    shutil.copyfile(golden, target)
    project.write_text(json.dumps(descriptor, indent='\t') + '\n')
    assert target.read_bytes() == golden.read_bytes()
except Exception:
    shutil.copyfile(backup / target.name, target)
    shutil.copyfile(backup / project.name, project)
    raise
record = dict(preset='AgX Golden', engine=str(engine), backup=str(backup),
              shader_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
              postprocess_settings_modified=False)
(root / 'Saved/Integration/agx/applied.json').write_text(json.dumps(record, indent=2))
print(json.dumps(record))

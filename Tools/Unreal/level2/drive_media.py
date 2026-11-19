"""Package actual proof frames and CSV GPU timings, without inventing missing runtime evidence."""
import csv
import json
from pathlib import Path
import statistics
import subprocess
import time

OUT=Path('P:/FoA/Saved/Codex/l2_drive')


def main():
    proof=json.loads((OUT/'proof_done.json').read_text())
    assert proof['reason']=='passed',proof['reason']
    capture=json.loads((OUT/'video_done.json').read_text())
    assert capture['reason']=='passed',capture['reason']
    video=OUT/'l2_drive_15s.mp4'
    shots=[s for s in capture['shots'] if Path(s['file']).exists()]
    assert shots[-1]['t']-shots[0]['t']>=15,'Fewer than 15 captured seconds'
    lines=[]
    for a,b in zip(shots,shots[1:]):
        lines.extend(["file '"+a['file'].replace('\\','/')+"'",'duration '+str(b['t']-a['t'])])
    lines.append("file '"+shots[-1]['file'].replace('\\','/')+"'")
    manifest=OUT/'frames.txt';manifest.write_text('\n'.join(lines)+'\n')
    subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(manifest),'-t','15',
        '-vf','crop=1438:886:4:134,format=yuv420p','-r','30','-c:v','libx264','-preset','fast','-crf','20',str(video)],check=True)
    info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(video)]))
    assert float(info['format']['duration'])>=15,'Fewer than 15 recorded seconds'
    frames=OUT/'video_frames';frames.mkdir(exist_ok=True)
    subprocess.run(['ffmpeg','-y','-loglevel','error','-i',str(video),'-vf','fps=2',str(frames/'frame_%03d.png')],check=True)
    csvs=[]
    for path in Path('P:/FoA/Saved/Profiling/CSV').glob('Profile(*).csv'):
        started=time.mktime(time.strptime(path.stem,'Profile(%Y%m%d_%H%M%S)'))
        if proof['csv_start']-2 <= started <= proof['csv_start']+3:csvs.append(path)
    assert len(csvs)==1,('Ambiguous or missing proof CSV',csvs)
    values=[];source=None
    for path in reversed(csvs):
        with path.open(encoding='utf-8-sig') as f:
            rows=csv.DictReader(f)
            if 'GPUTime' not in rows.fieldnames:continue
            for row in rows:
                try:v=float(row['GPUTime'])
                except (ValueError,TypeError):continue
                if v>0:values.append(v)
        if values:source=path;break
    assert values,'No GPUTime samples belonging to this burst'
    values.sort();result=dict(csv=str(source),frames=len(values),gpu_ms_median=statistics.median(values),
                              gpu_ms_p95=values[min(len(values)-1,int(.95*len(values)))],
                              limitation='Editor GPU timing from the input proof before screenshot capture; RTX 5070, not a low-end hardware measurement')
    (OUT/'gpu.json').write_text(json.dumps(result,indent=1));print(json.dumps(result))


if __name__=='__main__':main()

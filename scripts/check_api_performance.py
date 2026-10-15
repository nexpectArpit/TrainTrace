"""Small local HTTP latency sample; not a load or GPU benchmark."""
import json,statistics,time,urllib.request
from pathlib import Path
base='http://127.0.0.1:8000/api/v1'
with urllib.request.urlopen(base+'/experiments/') as response:exp=json.load(response)['experiments'][0]['id']
result={}
for path in ['/experiments/','/runs/compare/'+exp,'/registry/models']:
    samples=[]
    for _ in range(20):
        start=time.perf_counter()
        with urllib.request.urlopen(base+path,timeout=30) as response:
            assert response.status==200;response.read()
        samples.append((time.perf_counter()-start)*1000)
    result[path]={'requests':20,'mean_ms':statistics.mean(samples),'p95_ms':sorted(samples)[18],'max_ms':max(samples)}
path=Path('docs/audits/2026-10-15/HTTP_PERFORMANCE.json');path.write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))

"""Run full-config audits against an explicitly named local acceptance run.

Use a temporary TRAINTRACE_STORAGE_DIR server; this creates real compute jobs.
"""
import argparse
import json
import time
import urllib.request
from pathlib import Path


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--run-id',required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    base='http://127.0.0.1:8000/api/v1'
    def request(path,payload=None):
        data=json.dumps(payload).encode() if payload is not None else None
        with urllib.request.urlopen(urllib.request.Request(base+path,data=data,headers={'Content-Type':'application/json'}),timeout=30) as response:
            return json.load(response)
    def wait(check):
        deadline=time.monotonic()+1200
        while time.monotonic()<deadline:
            result=check()
            if result:return result
            time.sleep(3)
        raise TimeoutError('Acceptance study exceeded 20 minutes')
    def source_ready():
        run=request('/runs/'+args.run_id)
        if run['status'] in ['FAILED','STOPPED']:raise RuntimeError(run['error'])
        return run if run['status']=='COMPLETED' else None
    run=wait(source_ready)
    job_ids=[]
    for protocol in ['a','b']:
        job=request('/runs/audit/protocol-'+protocol,{'run_id':args.run_id})
        job_ids.append(job['job_id']);print('Queued',protocol,job['job_id'],flush=True)
    def reports_ready():
        source=request('/runs/'+args.run_id)
        audits=[a for a in source['audits'] if a['id'] in job_ids]
        for a in audits:
            if a['status'] in ['FAILED','STOPPED']:raise RuntimeError(a['error'])
        return source if len(audits)==2 and all(a['status']=='COMPLETED' for a in audits) else None
    result=wait(reports_ready)
    result['audits']=[a for a in result['audits'] if a['id'] in job_ids]
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2))
    for a in result['audits']:
        report=a['report'];print('Completed',a['protocol'],{k:v for k,v in report.items() if k not in ['members','configuration']},flush=True)
    assert next(a['report'] for a in result['audits'] if a['protocol']=='A')['passed']
    sensitivity=next(a['report'] for a in result['audits'] if a['protocol']=='B')
    assert sensitivity['fixed_split'] and sensitivity['environment_match'] and sensitivity['sample_count']==5
    print('Real CIFAR-10 acceptance study passed:',args.output,flush=True)


if __name__=='__main__':main()
